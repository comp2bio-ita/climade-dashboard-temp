"""TreeTime dating: substitution tree + tip dates → timetree.nexus (originals unchanged)."""

import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

# from Bio import Phylo

from phylo_module import config

from shared.utils.handlers import SeqHandler

logger = logging.getLogger(__name__)

# Format written by stage_2; other shapes treated as unusable
STORED_COLLECTION_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Sole kept TreeTime artifact
TIMETREE_FILENAME = "timetree.nexus"

DATES_FILENAME = "collection_dates.tsv"
DATES_NAME_COLUMN = "accession_id"
DATES_DATE_COLUMN = "collection_date"

# Clock-filter outlier lines on stdout
_OUTLIER_PATTERN = re.compile(
    r"(\S+), input date: (.+?), apparent date: (-?[\d.]+)"
)
_CLOCK_RATE_PATTERN = re.compile(r"--rate:\s*(-?[\d.eE+-]+)")
_CLOCK_R_SQUARED_PATTERN = re.compile(r"--r\^2:\s*(-?[\d.eE+-]+)")


def normalize_collection_dates(collection_dates):
    """Split to dated_tips (YYYY-MM-DD) and exclusions; no date repair/guessing."""
    dated_tips = {}
    excluded_tips = []

    for accession_id, stored_date in sorted(collection_dates.items()):
        if stored_date is None or not str(stored_date).strip():
            excluded_tips.append({"accession_id": accession_id, "reason": "no collection date"})
            continue
        try:
            collected_on = datetime.strptime(str(stored_date).strip(), STORED_COLLECTION_DATE_FORMAT)
        except ValueError:
            excluded_tips.append(
                {
                    "accession_id": accession_id,
                    "reason": f"collection date {stored_date!r} is not a full calendar date",
                }
            )
            continue
        dated_tips[accession_id] = collected_on.strftime("%Y-%m-%d")

    return {"dated_tips": dated_tips, "excluded_tips": excluded_tips}

# legacy function with Phylo
# def read_tree_tip_names(tree_path):
#     """Tip labels from a Newick tree."""
#     tree = Phylo.read(str(tree_path), "newick")
#     return {tip.name for tip in tree.get_terminals() if tip.name}

# New function with DendroPy
def read_tree_tip_names(tree_path):
    import dendropy

    """Tip labels from a Newick tree."""
    tree = dendropy.Tree.get(
        path=str(tree_path),
        schema="newick",
    )

    return {
        leaf.taxon.label
        for leaf in tree.leaf_node_iter()
        if leaf.taxon is not None and leaf.taxon.label
    }


def _resolve_treetime_binary(treetime_bin):
    resolved = shutil.which(treetime_bin)
    if resolved:
        return resolved
    raise FileNotFoundError(
        f"TreeTime executable not found (tried {treetime_bin!r}). Install it with "
        "pip install phylo-treetime and ensure the virtualenv is active."
    )


def _capture_version(executable):
    # Best-effort provenance; never fail the run
    try:
        completed = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    banner = (completed.stdout or "") + (completed.stderr or "")
    match = re.search(r"(\d+\.\d+\.\d+)", banner)
    return match.group(1) if match else None


def _write_dates_file(dated_tips, dates_path):
    # Keep outside --outdir (TreeTime also writes dates.tsv there)
    lines = [f"{DATES_NAME_COLUMN}\t{DATES_DATE_COLUMN}"]
    for accession_id in sorted(dated_tips):
        lines.append(f"{accession_id}\t{dated_tips[accession_id]}")
    Path(dates_path).write_text("\n".join(lines) + "\n")


def _prune_alignment(alignment_path, dated_accessions, pruned_alignment_path):
    with Path(alignment_path).open() as handle:
        kept_records = [
            record
            for record in SeqHandler.parse_fasta(handle)
            if record.id.split()[0] in dated_accessions
        ]

    # SeqIO.write(kept_records, str(pruned_alignment_path), "fasta")
    SeqHandler.write_fasta(kept_records, str(pruned_alignment_path))
    
    return len(kept_records)


# def _prune_tree(tree_path, dated_accessions, pruned_tree_path):
#     # Copy only for TreeTime input; persisted tree untouched
#     tree = Phylo.read(str(tree_path), "newick")
#     for tip in list(tree.get_terminals()):
#         if tip.name not in dated_accessions:
#             tree.prune(tip)
#     Phylo.write(tree, str(pruned_tree_path), "newick")
#     return len(tree.get_terminals())

def _prune_tree(tree_path, dated_accessions, pruned_tree_path):
    """Prune tips not present in dated_accessions."""
    import dendropy
    # Copy only for TreeTime input; persisted tree untouched
    tree = dendropy.Tree.get(
        path=str(tree_path),
        schema="newick",
    )

    for leaf in list(tree.leaf_node_iter()):
        tip_name = leaf.taxon.label if leaf.taxon is not None else None

        if tip_name not in dated_accessions:
            tree.prune_node(leaf)

    tree.write(
        path=str(pruned_tree_path),
        schema="newick",
    )

    return sum(1 for _ in tree.leaf_node_iter())


def _build_treetime_command(executable, alignment_path, tree_path, dates_path, outdir,
                            treetime_settings):
    """Build TreeTime argv (rate estimated; no coalescent / polytomy resolve)."""
    command = [
        executable,
        "--aln", alignment_path,
        "--tree", tree_path,
        "--dates", dates_path,
        "--name-column", DATES_NAME_COLUMN,
        "--date-column", DATES_DATE_COLUMN,
        "--reroot", treetime_settings["reroot"],
        "--clock-filter", str(treetime_settings["clock_filter"]),
        "--clock-filter-method", treetime_settings["clock_filter_method"],
        "--branch-length-mode", treetime_settings["branch_length_mode"],
        "--rng-seed", str(treetime_settings["seed"]),
        "--outdir", outdir,
    ]
    if treetime_settings["keep_polytomies"]:
        command.append("--keep-polytomies")
    return command


def resolve_treetime_settings(config_dict):
    """Per-job overrides over config.py defaults."""
    return {
        "reroot": config_dict.get("reroot", config.TREETIME_REROOT),
        "clock_filter": config_dict.get("clock_filter", config.TREETIME_CLOCK_FILTER),
        "clock_filter_method": config_dict.get(
            "clock_filter_method", config.TREETIME_CLOCK_FILTER_METHOD
        ),
        "branch_length_mode": config_dict.get(
            "branch_length_mode", config.TREETIME_BRANCH_LENGTH_MODE
        ),
        "keep_polytomies": config_dict.get("keep_polytomies", config.TREETIME_KEEP_POLYTOMIES),
        "seed": config_dict.get("seed", config.TREETIME_SEED),
    }


def _parse_molecular_clock(clock_report):
    # First number after --rate / --r^2
    rate_match = _CLOCK_RATE_PATTERN.search(clock_report)
    r_squared_match = _CLOCK_R_SQUARED_PATTERN.search(clock_report)
    clock_rate = float(rate_match.group(1)) if rate_match else None
    r_squared = float(r_squared_match.group(1)) if r_squared_match else None
    return {"clock_rate": clock_rate, "r_squared": r_squared}


def _parse_clock_filter_excluded(treetime_stdout):
    # Clock-filter rejections are on stdout for this command
    excluded = []
    for accession_id, input_date, apparent_date in _OUTLIER_PATTERN.findall(treetime_stdout):
        excluded.append(
            {
                "accession_id": accession_id,
                "input_date": input_date.strip(),
                "apparent_date": float(apparent_date),
            }
        )
    return excluded


def _atomic_write_canonical(source_path, destination_path):
    # Atomic write via temp + os.replace
    temp_path = destination_path.with_name(destination_path.name + ".tmp")
    temp_path.write_text(Path(source_path).read_text())
    os.replace(temp_path, destination_path)


def run_treetime(alignment_path, tree_path, dated_tips, output_dir, config_dict):
    """Date tree → timetree.nexus in output_dir. Raises on failure (caller may treat as non-fatal)."""
    alignment = Path(alignment_path)
    tree = Path(tree_path)
    if not alignment.is_file():
        raise FileNotFoundError(f"Alignment FASTA not found: {alignment}")
    if not tree.is_file():
        raise FileNotFoundError(f"Substitution tree not found: {tree}")
    if not dated_tips:
        raise ValueError("No dated tips were provided; TreeTime has nothing to date.")

    executable = _resolve_treetime_binary(config_dict.get("executable", config.TREETIME_BIN))
    treetime_settings = resolve_treetime_settings(config_dict)
    timeout_seconds = config_dict.get("timeout", config.TREETIME_TIMEOUT_SECONDS)

    method_dir = Path(output_dir)
    method_dir.mkdir(parents=True, exist_ok=True)

    warnings = []

    with tempfile.TemporaryDirectory(prefix="treetime_") as work_dir:
        work_path = Path(work_dir)
        pruned_alignment = work_path / "aligned.fasta"
        pruned_tree = work_path / "tree.nwk"
        dates_path = work_path / DATES_FILENAME
        treetime_outdir = work_path / "outdir"

        alignment_records = _prune_alignment(alignment, dated_tips, pruned_alignment)
        tree_tips = _prune_tree(tree, dated_tips, pruned_tree)
        _write_dates_file(dated_tips, dates_path)

        if alignment_records != tree_tips or alignment_records != len(dated_tips):
            raise ValueError(
                f"TreeTime inputs disagree on taxa: {alignment_records} alignment record(s), "
                f"{tree_tips} tree tip(s), {len(dated_tips)} dated tip(s)."
            )

        command = _build_treetime_command(
            executable,
            str(pruned_alignment),
            str(pruned_tree),
            str(dates_path),
            str(treetime_outdir),
            treetime_settings,
        )
        logger.info("Running TreeTime on %d dated sequence(s)", alignment_records)
        logger.info("Command: %s", " ".join(command))

        started_at = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"TreeTime timed out after {timeout_seconds}s on {alignment_records} "
                "dated sequence(s)."
            ) from exc

        execution_time_seconds = time.monotonic() - started_at

        if completed.stderr:
            logger.info("TreeTime stderr (tail): %s", completed.stderr.strip()[-500:])

        if completed.returncode != 0:
            stderr_tail = (completed.stderr or "").strip()[-500:]
            raise RuntimeError(
                f"TreeTime failed (exit {completed.returncode}). stderr: {stderr_tail or '(empty)'}"
            )

        timetree_path = treetime_outdir / TIMETREE_FILENAME
        if not timetree_path.is_file():
            raise RuntimeError(
                f"TreeTime exited 0 but wrote no {TIMETREE_FILENAME} in {treetime_outdir}"
            )

        clock_report_path = treetime_outdir / "molecular_clock.txt"
        clock_report = clock_report_path.read_text() if clock_report_path.is_file() else ""
        molecular_clock = _parse_molecular_clock(clock_report)
        if molecular_clock["clock_rate"] is None:
            warnings.append("Could not read the estimated clock rate from TreeTime output.")

        clock_filter_excluded = _parse_clock_filter_excluded(completed.stdout or "")

        # Other TreeTime artifacts discarded with tempdir
        canonical_timetree_path = method_dir / TIMETREE_FILENAME
        _atomic_write_canonical(timetree_path, canonical_timetree_path)

        return_code = completed.returncode

    logger.info(
        "TreeTime complete in %.1fs: rate=%s, R^2=%s, %d temporal outlier(s)",
        execution_time_seconds,
        molecular_clock["clock_rate"],
        molecular_clock["r_squared"],
        len(clock_filter_excluded),
    )

    return {
        "output_path": str(canonical_timetree_path.resolve()),
        "timetree_nexus": canonical_timetree_path.read_text(),
        "alignment_records": alignment_records,
        "dated_tips": len(dated_tips),
        "clock_rate": molecular_clock["clock_rate"],
        "r_squared": molecular_clock["r_squared"],
        "clock_filter_excluded": clock_filter_excluded,
        "software": "TreeTime",
        "software_version": _capture_version(executable),
        "return_code": return_code,
        "execution_time_seconds": round(execution_time_seconds, 3),
        # Basenames only (temp paths are gone)
        "treetime_command": [Path(argument).name if os.sep in argument else argument
                             for argument in command],
        "treetime_settings": treetime_settings,
        "warnings": warnings,
    }
