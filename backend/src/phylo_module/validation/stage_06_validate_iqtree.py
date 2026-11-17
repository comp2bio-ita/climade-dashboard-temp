"""
Stage 06 — IQ-TREE on stage 02 alignment (not FastTree Newick).

Run from backend/:
    python -m phylo_module.validation.stage_06_validate_iqtree
"""

import logging
import sys

from phylo_module.services.alignment_service import PHYLO_ALIGNMENTS_DIR
from phylo_module.services.iqtree_service import run_iqtree
from phylo_module.services.tree_service import PHYLO_TREES_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

INPUT_ALIGNMENT = PHYLO_ALIGNMENTS_DIR / "dev_validation_aligned.fasta"
OUTPUT_DIR = PHYLO_TREES_DIR / "dev_validation_iqtree"


def main():
    if not INPUT_ALIGNMENT.is_file():
        logging.error(
            "Missing alignment: %s — run python -m phylo_module.validation.stage_02_validate_alignment first",
            INPUT_ALIGNMENT,
        )
        sys.exit(1)

    result = run_iqtree(str(INPUT_ALIGNMENT), str(OUTPUT_DIR), {})

    print(result)

    if not result.get("selected_model"):
        logging.warning("ModelFinder-selected model could not be extracted from IQ-TREE output.")


if __name__ == "__main__":
    main()
