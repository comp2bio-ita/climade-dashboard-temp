"""IQ-TREE ML inference: alignment in, canonical tree.nwk out (under --prefix artifacts)."""

import io
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

# from Bio import Phylo

from phylo_module import config

from shared.utils.handlers import SeqHandler

logger = logging.getLogger(__name__)


def _count_fasta_records(fasta_path):
    with fasta_path.open() as handle:
        parsed_seqs = list(SeqHandler.parse_fasta(handle))

        return sum(1 for _ in parsed_seqs)
        # return sum(1 for _ in SeqIO.parse(handle, "fasta"))


def _resolve_iqtree_binary(iqtree_bin):
    # Prefer iqtree2, then iqtree
    for candidate in (iqtree_bin, "iqtree2", "iqtree"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError(
        f"IQ-TREE executable not found (tried {iqtree_bin!r}, 'iqtree2', 'iqtree'). "
        "Install IQ-TREE 2.4.0 (e.g. conda install -c bioconda iqtree=2.4.0) and ensure "
        "it is on PATH."
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
    match = re.search(r"version (\d+\.\d+\.\d+)", banner)
    return match.group(1) if match else None


def _parse_selected_model(report_path):
    # ModelFinder line from .iqtree / .log
    if not report_path.is_file():
        return None
    for line in report_path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("Best-fit model according to"):
            return stripped.split(":", 1)[1].strip()
        if stripped.startswith("Model of substitution:"):
            return stripped.split(":", 1)[1].strip()
    return None


def _parse_threads_used(report_path):
    if not report_path.is_file():
        return None
    for line in report_path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("BEST NUMBER OF THREADS:"):
            try:
                return int(stripped.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None

# new function included to bypass Phylo - hardcoded
# def _validate_newick(content):
#     """Basic structural validation of a Newick tree."""

#     if not content.endswith(";"):
#         raise ValueError("Newick tree must end with ';'")

#     # Remove the final semicolon.
#     tree = content[:-1].strip()

#     if not tree:
#         raise ValueError("Newick tree is empty")

#     depth = 0
#     expect_node = True

#     for char in tree:
#         if char == "(":
#             depth += 1
#             expect_node = True

#         elif char == ")":
#             if depth == 0:
#                 raise ValueError("Unmatched ')'")

#             depth -= 1
#             expect_node = False

#         elif char == ",":
#             if expect_node:
#                 raise ValueError("Unexpected ','")

#             expect_node = True

#         elif char == ";":
#             raise ValueError("Unexpected ';'")

#         elif not char.isspace():
#             expect_node = False

#     if depth != 0:
#         raise ValueError("Unmatched '('")

#     if expect_node:
#         raise ValueError("Incomplete Newick tree")

#     if not tree.startswith("("):
#         raise ValueError("Expected tree to start with '('")



def _validate_newick_tree(tree_path):
    import dendropy
    # Structural check + Biopython parse
    content = tree_path.read_text().strip()
    if not content:
        raise ValueError(f"Tree file is empty: {tree_path}")
    if not content.startswith("("):
        raise ValueError(
            f"Tree file does not look like Newick (expected leading '('): {tree_path}"
        )
    try:
        # Phylo.read(io.StringIO(content), "newick")
        # _validate_newick(content)
        dendropy.Tree.get(data=content, schema="newick")
    except Exception as exc:
        raise ValueError(f"Tree file is not parseable Newick ({tree_path}): {exc}") from exc
    return len(content)


def _atomic_write_canonical(source_tree_path, destination_path):
    # Atomic write via temp + os.replace
    tree_text = Path(source_tree_path).read_text()
    temp_path = destination_path.with_name(destination_path.name + ".tmp")
    temp_path.write_text(tree_text)
    os.replace(temp_path, destination_path)


_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9+._-]+$")
_MEMORY_PATTERN = re.compile(r"^\d+[KMGT]?$", re.IGNORECASE)
_ALLOWED_SUBST_TYPES = ("DNA", "AA", "CODON", "BIN", "MORPH")


def _normalize_iqtree_settings(config_dict, warnings):
    """Validate IQ-TREE settings; reject out-of-range (never silently shrink)."""
    iqtree_settings = {}

    model = config_dict.get("model", config.IQTREE_MODEL)
    if not isinstance(model, str) or model.startswith("-") or not _MODEL_PATTERN.match(model):
        raise ValueError(f"Invalid IQ-TREE model: {model!r}")
    iqtree_settings["model"] = model

    subst_type = config_dict.get("subst_type", config.IQTREE_SUBST_TYPE)
    if subst_type not in _ALLOWED_SUBST_TYPES:
        raise ValueError(
            f"Invalid IQ-TREE substitution type: {subst_type!r} "
            f"(allowed: {', '.join(_ALLOWED_SUBST_TYPES)})"
        )
    iqtree_settings["subst_type"] = subst_type

    ufboot_enabled = bool(config_dict.get("ufboot_enabled", config.IQTREE_UFBOOT_ENABLED))
    iqtree_settings["ufboot_enabled"] = ufboot_enabled
    if ufboot_enabled:
        replicates = _validate_replicates(
            config_dict.get("ufboot_replicates", config.IQTREE_UFBOOT_REPLICATES),
            config.IQTREE_MAX_UFBOOT_REPLICATES,
            "UFBoot",
        )
        iqtree_settings["ufboot_replicates"] = replicates

    shalrt_enabled = bool(config_dict.get("shalrt_enabled", config.IQTREE_SHALRT_ENABLED))
    iqtree_settings["shalrt_enabled"] = shalrt_enabled
    if shalrt_enabled:
        replicates = _validate_replicates(
            config_dict.get("shalrt_replicates", config.IQTREE_SHALRT_REPLICATES),
            config.IQTREE_MAX_SHALRT_REPLICATES,
            "SH-aLRT",
        )
        iqtree_settings["shalrt_replicates"] = replicates

    # -bnni only with UFBoot; drop + warn otherwise
    bnni_requested = bool(config_dict.get("bnni_enabled", config.IQTREE_BNNI_ENABLED))
    if bnni_requested and not ufboot_enabled:
        warnings.append(
            "BNNI (-bnni) was requested but UFBoot is disabled; -bnni was not applied."
        )
        bnni_requested = False
    iqtree_settings["bnni_enabled"] = bnni_requested

    seed = config_dict.get("seed", config.IQTREE_SEED)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError(f"Invalid IQ-TREE seed (expected non-negative int): {seed!r}")
    iqtree_settings["seed"] = seed

    ntmax = config_dict.get("ntmax", config.IQTREE_NTMAX)
    if isinstance(ntmax, bool) or not isinstance(ntmax, int) or ntmax < 1:
        raise ValueError(f"Invalid IQ-TREE ntmax (expected positive int): {ntmax!r}")
    if ntmax > config.IQTREE_MAX_NTMAX:
        raise ValueError(
            f"IQ-TREE ntmax {ntmax} exceeds server limit {config.IQTREE_MAX_NTMAX}."
        )
    iqtree_settings["ntmax"] = ntmax

    thread_mode = str(config_dict.get("thread_mode", config.IQTREE_THREAD_MODE))
    if thread_mode != "AUTO":
        if not thread_mode.isdigit() or int(thread_mode) < 1:
            raise ValueError(
                f"Invalid IQ-TREE thread mode: {thread_mode!r} (expected 'AUTO' or a "
                "positive integer)."
            )
        if int(thread_mode) > config.IQTREE_MAX_NTMAX:
            raise ValueError(
                f"IQ-TREE thread count {thread_mode} exceeds server limit "
                f"{config.IQTREE_MAX_NTMAX}."
            )
    iqtree_settings["thread_mode"] = thread_mode

    memory_limit = config_dict.get("memory_limit", config.IQTREE_MEMORY_LIMIT)
    if memory_limit:
        if not _MEMORY_PATTERN.match(str(memory_limit)):
            raise ValueError(
                f"Invalid IQ-TREE memory limit: {memory_limit!r} (expected e.g. '8G')."
            )
        iqtree_settings["memory_limit"] = str(memory_limit)
    else:
        iqtree_settings["memory_limit"] = None

    return iqtree_settings


def _validate_replicates(value, maximum, label):
    # UFBoot / SH-aLRT require >= 1000
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Invalid {label} replicate count (expected int): {value!r}")
    if value < 1000:
        raise ValueError(f"{label} replicate count must be >= 1000; got {value}.")
    if value > maximum:
        raise ValueError(
            f"{label} replicate count {value} exceeds server limit {maximum}."
        )
    return value


def _build_iqtree_command(executable, alignment_path, prefix, iqtree_settings):
    """Build IQ-TREE argv; never emits -redo (keep checkpoint)."""
    command = [
        executable,
        "-s", alignment_path,
        "-st", iqtree_settings["subst_type"],
        "-m", iqtree_settings["model"],
        "-T", iqtree_settings["thread_mode"],
        "-ntmax", str(iqtree_settings["ntmax"]),
        "-seed", str(iqtree_settings["seed"]),
        "--prefix", prefix,
    ]
    if iqtree_settings["ufboot_enabled"]:
        command += ["-B", str(iqtree_settings["ufboot_replicates"])]
    if iqtree_settings["shalrt_enabled"]:
        command += ["-alrt", str(iqtree_settings["shalrt_replicates"])]
    if iqtree_settings["ufboot_enabled"] and iqtree_settings["bnni_enabled"]:
        command += ["-bnni"]
    if iqtree_settings["memory_limit"]:
        command += ["-mem", iqtree_settings["memory_limit"]]
    return command


def run_iqtree(alignment_path, output_dir, config_dict):
    """Run IQ-TREE; write tree.nwk under output_dir. Raises on failure."""
    alignment = Path(alignment_path)
    if not alignment.is_file():
        raise FileNotFoundError(f"Alignment FASTA not found: {alignment}")

    alignment_records = _count_fasta_records(alignment)
    if alignment_records == 0:
        raise ValueError(f"Alignment FASTA contains no sequences: {alignment}")

    executable = _resolve_iqtree_binary(config_dict.get("executable", config.IQTREE_BIN))

    method_dir = Path(output_dir)
    method_dir.mkdir(parents=True, exist_ok=True)
    prefix = str(method_dir / "tree")

    warnings = []
    iqtree_settings = _normalize_iqtree_settings(config_dict, warnings)
    timeout_seconds = config_dict.get("timeout", config.IQTREE_TIMEOUT_SECONDS)

    command = _build_iqtree_command(executable, str(alignment.resolve()), prefix, iqtree_settings)
    logger.info(
        "Running IQ-TREE on %d aligned sequence(s): %s → %s",
        alignment_records,
        alignment,
        method_dir,
    )
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
        # Leave tree.ckp.gz for manual resume
        raise RuntimeError(
            f"IQ-TREE timed out after {timeout_seconds}s on {alignment_records} "
            f"sequence(s). The checkpoint {prefix}.ckp.gz was left in place so the run "
            "can be resumed manually."
        ) from exc

    execution_time_seconds = time.monotonic() - started_at

    if completed.stderr:
        logger.info("IQ-TREE stderr (tail): %s", completed.stderr.strip()[-500:])

    if completed.returncode != 0:
        stderr_tail = (completed.stderr or "").strip()[-500:]
        raise RuntimeError(
            f"IQ-TREE failed (exit {completed.returncode}). stderr: {stderr_tail or '(empty)'}"
        )

    treefile_path = Path(prefix + ".treefile")
    if not treefile_path.is_file():
        raise RuntimeError(
            f"IQ-TREE exited 0 but no tree file was written: {treefile_path}"
        )

    tree_characters = _validate_newick_tree(treefile_path)

    canonical_tree_path = method_dir / "tree.nwk"
    _atomic_write_canonical(treefile_path, canonical_tree_path)

    selected_model = _parse_selected_model(Path(prefix + ".iqtree")) or _parse_selected_model(
        Path(prefix + ".log")
    )
    if selected_model is None:
        warnings.append("Could not extract the ModelFinder-selected model from IQ-TREE output.")

    threads_used = _parse_threads_used(Path(prefix + ".log")) or _parse_threads_used(
        Path(prefix + ".iqtree")
    )

    output_files = sorted(str(path) for path in method_dir.glob("tree.*"))

    logger.info(
        "IQ-TREE complete in %.1fs: model=%s, tree written to %s",
        execution_time_seconds,
        selected_model,
        canonical_tree_path.resolve(),
    )

    return {
        "output_path": str(canonical_tree_path.resolve()),
        "treefile_path": str(treefile_path.resolve()),
        "alignment_path": str(alignment.resolve()),
        "alignment_records": alignment_records,
        "iqtree_command": command,
        "selected_model": selected_model,
        "threads_used": threads_used,
        "software": "IQ-TREE",
        "software_version": _capture_version(executable),
        "return_code": completed.returncode,
        "execution_time_seconds": round(execution_time_seconds, 3),
        "output_files": output_files,
        "tree_characters": tree_characters,
        "warnings": warnings,
    }
