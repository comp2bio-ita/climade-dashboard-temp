"""Persist phylogenetic tree runs to phylo_tb."""

from datetime import datetime

from models.database_models import PhyloEntity


def persist_phylo_run(
    database_service,
    newick,
    sequence_count,
    filter_params,
    accession_ids,
    accession_set_hash,
    inference_method,
    pathogen,
    warnings=None,
    run_metadata=None,
    time_tree_nexus=None,
):
    record = PhyloEntity(
        pathogen=pathogen,
        newick=newick,
        # None if temporal stage off/skipped/failed
        time_tree_nexus=time_tree_nexus,
        sequence_count=sequence_count,
        filter_params=filter_params,
        accession_ids=accession_ids,
        accession_set_hash=accession_set_hash,
        inference_method=inference_method,
        status="done",
        warnings=warnings,
        run_metadata=run_metadata,
        completed_at=datetime.now(),
    )
    return database_service.add_record(record)
