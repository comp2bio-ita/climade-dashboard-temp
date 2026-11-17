"""
Stage 07 — TreeTime on stage 02/03 outputs (needs MySQL for collection dates).

Calls the service directly; pipeline gate is covered by stage 04.

Run from backend/:
    python -m phylo_module.validation.stage_07_validate_treetime
"""

import hashlib
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from models.env_models import EnvSettings
from phylo_module.pathogens import meta_entity_for
from phylo_module.pipeline_phylo import resolve_collection_dates
from phylo_module.services.alignment_service import PHYLO_ALIGNMENTS_DIR
from phylo_module.services.tree_service import PHYLO_TREES_DIR
from phylo_module.services.treetime_service import normalize_collection_dates, run_treetime
from phylo_module.validation.stage_04_smoke_test_pipeline import (
    DEV_ACCESSIONS_TSV,
    load_dev_accession_ids,
)
from services.DatabaseService import DatabaseService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

INPUT_ALIGNMENT = PHYLO_ALIGNMENTS_DIR / "dev_validation_aligned.fasta"
INPUT_TREE = PHYLO_TREES_DIR / "dev_validation_tree.nwk"
OUTPUT_DIR = PHYLO_TREES_DIR / "dev_validation_treetime"


def build_database_service():
    load_dotenv()
    settings = EnvSettings()
    return DatabaseService(
        host=settings.DASH_HOST,
        port=settings.DASH_PORT,
        database=settings.DASH_DATABASE,
        user=settings.DASH_USER,
        password=settings.DASH_PASSWORD,
    )


def main():
    for required_input, produced_by in (
        (INPUT_ALIGNMENT, "stage_02_validate_alignment"),
        (INPUT_TREE, "stage_03_validate_fasttree"),
    ):
        if not required_input.is_file():
            logging.error(
                "Missing input: %s — run python -m phylo_module.validation.%s first",
                required_input,
                produced_by,
            )
            sys.exit(1)

    dev_accessions = load_dev_accession_ids(DEV_ACCESSIONS_TSV)
    database_service = build_database_service()
    normalized = normalize_collection_dates(
        resolve_collection_dates(database_service, dev_accessions, meta_entity_for("DENV"))
    )
    logging.info(
        "%d of %d dev accession(s) carry a usable collection date",
        len(normalized["dated_tips"]),
        len(dev_accessions),
    )
    for excluded in normalized["excluded_tips"]:
        logging.warning("%s excluded: %s", excluded["accession_id"], excluded["reason"])

    if not normalized["dated_tips"]:
        logging.error("No dev accession has a usable collection date; nothing to date.")
        sys.exit(1)

    fingerprints_before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (INPUT_ALIGNMENT, INPUT_TREE)
    }

    result = run_treetime(
        str(INPUT_ALIGNMENT), str(INPUT_TREE), normalized["dated_tips"], str(OUTPUT_DIR), {}
    )

    print(result)

    for path, fingerprint in fingerprints_before.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != fingerprint:
            raise SystemExit(f"FAIL: TreeTime modified its input {path}")
    logging.info("PASS: alignment and substitution tree are unchanged")

    retained = sorted(item.name for item in Path(OUTPUT_DIR).iterdir())
    if retained != ["timetree.nexus"]:
        raise SystemExit(f"FAIL: expected only timetree.nexus in {OUTPUT_DIR}, found {retained}")
    logging.info("PASS: only the canonical timetree.nexus was retained")

    missing_labels = [
        accession_id
        for accession_id in normalized["dated_tips"]
        if accession_id not in result["timetree_nexus"]
    ]
    if missing_labels:
        raise SystemExit(f"FAIL: accession labels missing from the timetree: {missing_labels}")
    logging.info("PASS: every dated accession label appears in the timetree")

    if result["clock_rate"] is None:
        logging.warning("TreeTime did not report a clock rate for this dataset.")
    elif result["clock_rate"] <= 0:
        logging.warning(
            "Non-positive clock rate (%s): too little temporal signal to read as a time scale.",
            result["clock_rate"],
        )
    else:
        logging.info(
            "Clock rate %s substitutions/site/year, R^2 %s",
            result["clock_rate"],
            result["r_squared"],
        )


if __name__ == "__main__":
    main()
