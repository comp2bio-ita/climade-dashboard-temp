"""
Stage 01 — Fetch dev accessions from Entrez and write dev_validation.fasta.

Run from backend/:
    python -m phylo_module.validation.stage_01_validate_fasta_fetch

Next stage: stage_02_validate_alignment
"""

import csv
import logging
from pathlib import Path

from phylo_module.services.fasta_service import PHYLO_SEQUENCES_DIR, fetch_fasta_sequences

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEV_ACCESSIONS_TSV = BACKEND_DIR / "data" / "dev" / "dengue_phylo_dev_accessions.tsv"
OUTPUT_FASTA = PHYLO_SEQUENCES_DIR / "dev_validation.fasta"


def load_accession_ids(tsv_path):
    with tsv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [row["genbank_sequence_data_id"].strip() for row in reader]


def main():
    accession_ids = load_accession_ids(DEV_ACCESSIONS_TSV)
    logging.info("Loaded %d accession(s) from %s", len(accession_ids), DEV_ACCESSIONS_TSV)

    result = fetch_fasta_sequences(
        accession_ids,
        str(OUTPUT_FASTA),
        batch_size=5,
        sleep_time=0.1,
    )

    print(result)
    if result["failed_accessions"]:
        raise SystemExit(f"Fetch incomplete: {result['failed_accessions']}")


if __name__ == "__main__":
    main()
