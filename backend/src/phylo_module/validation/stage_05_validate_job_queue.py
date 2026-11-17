"""
Stage 05 — Manual job-queue validation (simulates frontend insert).

Run from backend/ with watcher already running:
    python -m phylo_module.validation.stage_05_validate_job_queue
"""

import json

from dotenv import load_dotenv

from models.database_models import PhyloEntity
from models.env_models import EnvSettings
from phylo_module.pipeline_phylo import PHYLO_STATUS_PENDING, _filter_params_for_storage
from services.DatabaseService import DatabaseService

# ==========================================
# TEST CONFIGURATION (edit as needed)
# Set any variable to None to omit that filter.
# ==========================================

# Explicit selection (stands in for frontend)
ACCESSION_IDS = [
    "FJ850076.1",
    "FJ850078.1",
    "FJ850088.1",
    "GQ868550.1",
    "GQ868551.1",
    "GU131864.1",
    "GU131882.1",
]

SEROTYPE = "DENV2"
GENOTYPE = None
COUNTRY = "Brazil"
HOST = None
COMPLETENESS = "complete_genome"  # "complete_genome" or "any"
START_DATE = "2023-01-01"  # YYYY-MM-DD
END_DATE = "2026-01-01"    # YYYY-MM-DD
PATHOGEN = "DENV"


def build_filter_params():
    filter_params = {}
    if SEROTYPE is not None:
        filter_params["serotype"] = SEROTYPE
    if GENOTYPE is not None:
        filter_params["genotype"] = GENOTYPE
    if COUNTRY is not None:
        filter_params["country"] = COUNTRY
    if HOST is not None:
        filter_params["host"] = HOST
    if COMPLETENESS is not None:
        filter_params["completeness"] = COMPLETENESS
    if START_DATE is not None:
        filter_params["start_date"] = START_DATE
    if END_DATE is not None:
        filter_params["end_date"] = END_DATE
    return filter_params


def main():
    load_dotenv()
    settings = EnvSettings()
    database_service = DatabaseService(
        host=settings.DASH_HOST,
        port=settings.DASH_PORT,
        database=settings.DASH_DATABASE,
        user=settings.DASH_USER,
        password=settings.DASH_PASSWORD,
    )

    filter_params = build_filter_params()
    stored_filter_params = _filter_params_for_storage(filter_params)

    pending_job = PhyloEntity(
        pathogen=PATHOGEN,
        filter_params=stored_filter_params,
        accession_ids=sorted(ACCESSION_IDS),
        status=PHYLO_STATUS_PENDING,
    )
    database_service.add_record(pending_job)

    rows = database_service.get_record_by_filters(
        entity_class=PhyloEntity,
        and_filters=[
            PhyloEntity.status == PHYLO_STATUS_PENDING,
            PhyloEntity.filter_params == stored_filter_params,
        ],
        order_column="created_at",
        all_records=False,
    )
    if not rows:
        raise RuntimeError("Pending job was inserted but could not be read back by filter_params")

    job_id = rows[0]["id"]

    print(f"Queued phylo job id: {job_id}")
    print(f"accession_ids ({len(ACCESSION_IDS)}): {json.dumps(sorted(ACCESSION_IDS))}")
    print(f"filter_params: {json.dumps(filter_params)}")
    print("Ensure the phylo job watcher is already running (python -m phylo_module.pipeline_phylo).")


if __name__ == "__main__":
    main()
