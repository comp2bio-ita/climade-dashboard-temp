"""Align multi-FASTA with MAFFT; write aligned FASTA to disk."""

import logging
import shutil
import subprocess
from pathlib import Path

# from Bio import SeqIO

from phylo_module import config

from shared.utils.handlers import SeqHandler

logger = logging.getLogger(__name__)

PHYLO_ALIGNMENTS_DIR = Path(__file__).resolve().parents[1] / "data" / "alignments"


def _count_fasta_records(fasta_path):
    with fasta_path.open() as handle:
        parsed_seqs = list(SeqHandler.parse_fasta(handle))
        return sum(1 for _ in parsed_seqs)
        # return sum(1 for _ in SeqIO.parse(handle, "fasta"))å


def _resolve_mafft_binary(mafft_bin):
    resolved = shutil.which(mafft_bin)
    if not resolved:
        raise FileNotFoundError(
            f"MAFFT executable not found: {mafft_bin!r}. "
            "Install MAFFT (e.g. conda install -c bioconda mafft) and ensure it is on PATH."
        )
    return resolved


def align_fasta_sequences(
    input_path,
    output_path,
    *,
    mafft_bin=config.MAFFT_BIN,
    algorithm_flag=config.MAFFT_ALGORITHM_FLAG,
):
    """
    Run MAFFT on a multi-FASTA file and write the alignment to disk.

    Returns a dict with paths, record counts, and the command executed.
    """
    source = Path(input_path)
    if not source.is_file():
        raise FileNotFoundError(f"Input FASTA not found: {source}")

    input_records = _count_fasta_records(source)
    if input_records == 0:
        raise ValueError(f"Input FASTA contains no sequences: {source}")

    mafft_executable = _resolve_mafft_binary(mafft_bin)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [mafft_executable, algorithm_flag, str(source.resolve())]
    logger.info(
        "Running MAFFT on %d sequence(s): %s → %s",
        input_records,
        source,
        destination,
    )
    logger.info("Command: %s", " ".join(command))

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=config.MAFFT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"MAFFT timed out after {config.MAFFT_TIMEOUT_SECONDS}s on {input_records} "
            f"sequence(s). Refine filters or raise MAFFT_TIMEOUT_SECONDS."
        ) from exc

    if completed.returncode != 0:
        stderr_tail = (completed.stderr or "").strip()[-500:]
        raise RuntimeError(
            f"MAFFT failed (exit {completed.returncode}). stderr: {stderr_tail or '(empty)'}"
        )

    if not completed.stdout.strip():
        raise RuntimeError("MAFFT produced empty stdout; no alignment written.")

    destination.write_text(completed.stdout)

    output_records = _count_fasta_records(destination)
    if output_records != input_records:
        raise ValueError(
            f"Aligned FASTA record count ({output_records}) "
            f"does not match input ({input_records})."
        )

    logger.info(
        "Alignment complete: %d record(s), output %s",
        output_records,
        destination.resolve(),
    )

    return {
        "output_path": str(destination.resolve()),
        "input_path": str(source.resolve()),
        "input_records": input_records,
        "output_records": output_records,
        "mafft_command": command,
    }
