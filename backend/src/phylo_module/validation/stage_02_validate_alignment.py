"""
Stage 02 — Align dev_validation.fasta with MAFFT.

Requires stage 01 output: phylo_module/data/sequences/dev_validation.fasta

Run from backend/:
    python -m phylo_module.validation.stage_02_validate_alignment

Previous: stage_01_validate_fasta_fetch
Next stage: stage_03_validate_fasttree
"""

import logging
import sys

from phylo_module.services.alignment_service import (
    PHYLO_ALIGNMENTS_DIR,
    align_fasta_sequences,
)
from phylo_module.services.fasta_service import PHYLO_SEQUENCES_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

INPUT_FASTA = PHYLO_SEQUENCES_DIR / "dev_validation.fasta"
OUTPUT_FASTA = PHYLO_ALIGNMENTS_DIR / "dev_validation_aligned.fasta"


def main():
    if not INPUT_FASTA.is_file():
        logging.error(
            "Missing input FASTA: %s — run python -m phylo_module.validation.stage_01_validate_fasta_fetch first",
            INPUT_FASTA,
        )
        sys.exit(1)

    result = align_fasta_sequences(
        str(INPUT_FASTA),
        str(OUTPUT_FASTA),
    )

    print(result)
    if result["output_records"] != result["input_records"]:
        raise SystemExit("Alignment record count mismatch.")


if __name__ == "__main__":
    main()
