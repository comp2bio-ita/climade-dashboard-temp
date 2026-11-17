"""
Stage 04 — Smoke test for run_phylo_pipeline on the 7-accession dev set.

Run from backend/:
    python -m phylo_module.validation.stage_04_smoke_test_pipeline
"""

import csv
import logging
import sys
from pathlib import Path
from unittest.mock import patch

from Bio import Phylo
from dotenv import load_dotenv

from models.database_models import PhyloEntity
from models.env_models import EnvSettings
from phylo_module import config
from phylo_module.pathogens import meta_entity_for
from phylo_module.pipeline_phylo import (
    PhyloRequestTooLargeError,
    _phylo_job_hash,
    _resolve_inference_method,
    _treetime_job_inputs,
    run_phylo_pipeline,
)
from services.DatabaseService import DatabaseService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEV_ACCESSIONS_TSV = BACKEND_DIR / "data" / "dev" / "dengue_phylo_dev_accessions.tsv"

DEV_FILTER_PARAMS = {
    "serotype": "DENV2",
    "genotype": "2III",
    "country": "Brazil",
    "host": "Homo sapiens",
    "completeness": "complete_genome",
}

MAX_SEQUENCES = 200


def load_dev_accession_ids(tsv_path):
    with tsv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [row["genbank_sequence_data_id"].strip() for row in reader]


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


def tip_names_from_newick(newick_string):
    from io import StringIO
    tree = Phylo.read(StringIO(newick_string), "newick")
    return {tip.name for tip in tree.get_terminals()}


def fetch_phylo_row_by_hash(database_service, accession_set_hash):
    rows = database_service.get_record_by_filters(
        entity_class=PhyloEntity,
        and_filters=[PhyloEntity.accession_set_hash == accession_set_hash],
        all_records=False,
    )
    return rows[0] if rows else None


def assert_cap_raises_without_entrez(database_service, accession_ids):
    oversized = accession_ids + [f"FAKE{i}.1" for i in range(MAX_SEQUENCES)]
    with patch("phylo_module.pipeline_phylo.fetch_fasta_sequences") as mock_fetch:
        try:
            run_phylo_pipeline(
                database_service,
                oversized,
                DEV_FILTER_PARAMS,
                max_sequences=MAX_SEQUENCES,
            )
        except PhyloRequestTooLargeError:
            mock_fetch.assert_not_called()
            logger.info("PASS: PhyloRequestTooLargeError raised without Entrez call")
            return
    raise SystemExit("FAIL: expected PhyloRequestTooLargeError for oversized request")


def assert_small_tree_returns_warnings(database_service, accession_ids):
    small_set = accession_ids[:3]
    result = run_phylo_pipeline(
        database_service,
        small_set,
        DEV_FILTER_PARAMS,
        max_sequences=MAX_SEQUENCES,
    )
    warning_events = [event for event in result["warnings"] if event["level"] in ("warning", "error")]
    if not warning_events:
        raise SystemExit("FAIL: expected a warning event for fewer than 4 accessions")
    if result["sequence_count"] < 1:
        raise SystemExit("FAIL: small-tree run produced no sequences in tree")
    if not result["newick"].startswith("("):
        raise SystemExit("FAIL: small-tree run did not return parseable Newick")
    logger.info("PASS: small-tree request built tree with warning event: %s", warning_events)


def main():
    dev_accessions = load_dev_accession_ids(DEV_ACCESSIONS_TSV)
    if len(dev_accessions) != 7:
        raise SystemExit(f"FAIL: expected 7 dev accessions, got {len(dev_accessions)}")

    database_service = build_database_service()

    assert_cap_raises_without_entrez(database_service, dev_accessions)

    # Assert against config default engine (not a hardcoded string)
    expected_method = _resolve_inference_method(config.INFERENCE_METHOD)
    treetime_inputs = _treetime_job_inputs(database_service, dev_accessions, DEV_FILTER_PARAMS,
                                     meta_entity_for("DENV"))

    shuffled = list(reversed(dev_accessions))
    expected_hash = _phylo_job_hash(dev_accessions, expected_method, treetime_inputs)
    shuffled_hash = _phylo_job_hash(shuffled, expected_method, treetime_inputs)
    if expected_hash != shuffled_hash:
        raise SystemExit("FAIL: job hash is not order-independent")
    logger.info("PASS: job hash is order-independent")

    if _phylo_job_hash(dev_accessions, expected_method, None) == expected_hash and treetime_inputs:
        raise SystemExit("FAIL: TreeTime-enabled and TreeTime-disabled jobs share a hash")

    result = run_phylo_pipeline(
        database_service,
        dev_accessions,
        DEV_FILTER_PARAMS,
        max_sequences=MAX_SEQUENCES,
    )

    # Pre-TreeTime events: no warning/error (temporal stage asserted separately)
    inference_events = result["warnings"]
    for index, event in enumerate(result["warnings"]):
        if event["message"] == "Tree generated successfully":
            inference_events = result["warnings"][: index + 1]
            break
    warning_events = [event for event in inference_events if event["level"] in ("warning", "error")]
    if warning_events:
        raise SystemExit(f"FAIL: expected no warning events for clean dev run, got {warning_events}")
    if result["failed_accessions"]:
        raise SystemExit(f"FAIL: unexpected failed accessions: {result['failed_accessions']}")

    expected_sequence_count = len(dev_accessions)
    if result["sequence_count"] != expected_sequence_count:
        raise SystemExit(
            f"FAIL: sequence_count {result['sequence_count']} != {expected_sequence_count}"
        )

    newick = result["newick"]
    if not newick.startswith("("):
        raise SystemExit("FAIL: Newick does not start with '('")

    tip_names = tip_names_from_newick(newick)
    if len(tip_names) != 7:
        raise SystemExit(f"FAIL: expected 7 tips, got {len(tip_names)}: {tip_names}")

    missing_tips = set(dev_accessions) - tip_names
    if missing_tips:
        raise SystemExit(f"FAIL: tips missing from tree: {missing_tips}")

    row = fetch_phylo_row_by_hash(database_service, expected_hash)
    if not row:
        raise SystemExit("FAIL: no phylo_tb row found by accession_set_hash")

    if row["pathogen"] != "DENV":
        raise SystemExit(
            f"FAIL: pathogen is {row['pathogen']!r}, expected 'DENV'"
        )
    if row["inference_method"] != expected_method:
        raise SystemExit(
            f"FAIL: inference_method is {row['inference_method']!r}, expected {expected_method!r}"
        )

    if row["accession_set_hash"] != expected_hash:
        raise SystemExit("FAIL: stored accession_set_hash does not match pipeline hash")

    if row["newick"].strip() != newick:
        raise SystemExit("FAIL: persisted newick does not match pipeline return value")

    if row["sequence_count"] != result["sequence_count"]:
        raise SystemExit("FAIL: persisted sequence_count does not match pipeline return")

    logger.info("PASS: 7-accession dev run — run_id=%s, tips=%d", result["run_id"], len(tip_names))
    logger.info("PASS: read-back by accession_set_hash matches persisted Newick")

    # Temporal skip/fail must keep substitution tree
    temporal_metadata = (row["run_metadata"] or {}).get("treetime")
    if treetime_inputs is not None:
        if temporal_metadata is None:
            raise SystemExit("FAIL: TreeTime was enabled but no temporal metadata was persisted")
        if temporal_metadata["status"] == "done":
            if not row["time_tree_nexus"] or not row["time_tree_nexus"].startswith("#NEXUS"):
                raise SystemExit("FAIL: temporal stage reported done but stored no NEXUS timetree")
            logger.info(
                "PASS: dated tree stored — clock rate %s, R^2 %s",
                temporal_metadata["clock_rate"],
                temporal_metadata["r_squared"],
            )
        else:
            if row["time_tree_nexus"] is not None:
                raise SystemExit("FAIL: temporal stage did not complete but stored a timetree")
            logger.info(
                "PASS: temporal stage %s without affecting the tree — %s",
                temporal_metadata["status"],
                temporal_metadata.get("reason") or temporal_metadata.get("error"),
            )

    assert_small_tree_returns_warnings(database_service, dev_accessions)

    print(
        {
            "run_id": result["run_id"],
            "sequence_count": result["sequence_count"],
            "accession_set_hash": expected_hash,
            "inference_method": row["inference_method"],
            "warnings": result["warnings"],
            "tip_count": len(tip_names),
        }
    )
    logger.info("All smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
