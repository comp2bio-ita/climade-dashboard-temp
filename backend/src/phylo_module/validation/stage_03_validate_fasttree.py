"""
Stage 03 — Infer a Newick tree from dev_validation_aligned.fasta with FastTree.

Requires stage 02 output: phylo_module/data/alignments/dev_validation_aligned.fasta

Run from backend/:
    python -m phylo_module.validation.stage_03_validate_fasttree

Previous: stage_02_validate_alignment
"""

import logging
import sys

from phylo_module.services.alignment_service import PHYLO_ALIGNMENTS_DIR
from phylo_module.services.tree_service import PHYLO_TREES_DIR, build_fasttree

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

INPUT_ALIGNMENT = PHYLO_ALIGNMENTS_DIR / "dev_validation_aligned.fasta"
OUTPUT_TREE = PHYLO_TREES_DIR / "dev_validation_tree.nwk"


def main():
    if not INPUT_ALIGNMENT.is_file():
        logging.error(
            "Missing alignment: %s — run python -m phylo_module.validation.stage_02_validate_alignment first",
            INPUT_ALIGNMENT,
        )
        sys.exit(1)

    result = build_fasttree(
        str(INPUT_ALIGNMENT),
        str(OUTPUT_TREE),
    )

    print(result)


if __name__ == "__main__":
    main()
