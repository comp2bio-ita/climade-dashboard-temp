"""Build Newick tree from aligned FASTA with FastTree."""

import logging
import shutil
import subprocess
from pathlib import Path

# from Bio import SeqIO
from shared.utils.handlers import SeqHandler

from phylo_module import config

logger = logging.getLogger(__name__)

PHYLO_TREES_DIR = Path(__file__).resolve().parents[1] / "data" / "trees"


def _count_fasta_records(fasta_path):
    with fasta_path.open() as handle:
        fasta_seqs = SeqHandler.parse_fasta(handle)
        return sum(1 for _ in fasta_seqs)
        # return sum(1 for _ in SeqIO.parse(handle, "fasta"))


def _resolve_fasttree_binary(fasttree_bin):
    for candidate in (fasttree_bin, "FastTree", "fasttree"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError(
        f"FastTree executable not found (tried {fasttree_bin!r}, 'FastTree', 'fasttree'). "
        "Install FastTree (e.g. conda install -c bioconda fasttree) and ensure it is on PATH."
    )


def _validate_newick_file(tree_path):
    content = tree_path.read_text().strip()
    if not content:
        raise ValueError(f"Tree file is empty: {tree_path}")
    if not content.startswith("("):
        raise ValueError(
            f"Tree file does not look like Newick (expected leading '('): {tree_path}"
        )
    return len(content)


def build_fasttree(
    alignment_path,
    output_tree_path,
    *,
    fasttree_bin=config.FASTTREE_BIN,
    nt_flag=config.FASTTREE_NT_FLAG,
):
    """
    Run FastTree on a nucleotide alignment and write a Newick tree.

    Returns a dict with paths, alignment record count, and command executed.
    """
    alignment = Path(alignment_path)
    if not alignment.is_file():
        raise FileNotFoundError(f"Alignment FASTA not found: {alignment}")

    alignment_records = _count_fasta_records(alignment)
    if alignment_records == 0:
        raise ValueError(f"Alignment FASTA contains no sequences: {alignment}")

    fasttree_executable = _resolve_fasttree_binary(fasttree_bin)
    destination = Path(output_tree_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [fasttree_executable, nt_flag, str(alignment.resolve())]
    logger.info(
        "Running FastTree on %d aligned sequence(s): %s → %s",
        alignment_records,
        alignment,
        destination,
    )
    logger.info("Command: %s", " ".join(command))

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=config.FASTTREE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"FastTree timed out after {config.FASTTREE_TIMEOUT_SECONDS}s on "
            f"{alignment_records} sequence(s). Raise FASTTREE_TIMEOUT_SECONDS if expected."
        ) from exc

    if completed.stderr:
        stderr_tail = completed.stderr.strip()[-500:]
        logger.info("FastTree stderr (tail): %s", stderr_tail)

    if completed.returncode != 0:
        stderr_tail = (completed.stderr or "").strip()[-500:]
        raise RuntimeError(
            f"FastTree failed (exit {completed.returncode}). stderr: {stderr_tail or '(empty)'}"
        )

    if not completed.stdout.strip():
        raise RuntimeError("FastTree produced empty stdout; no tree written.")

    destination.write_text(completed.stdout)

    tree_characters = _validate_newick_file(destination)
    logger.info(
        "Tree written: %d character(s), %s",
        tree_characters,
        destination.resolve(),
    )

    return {
        "output_path": str(destination.resolve()),
        "alignment_path": str(alignment.resolve()),
        "alignment_records": alignment_records,
        "fasttree_command": command,
        "tree_characters": tree_characters,
    }
