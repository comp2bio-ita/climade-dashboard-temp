import unittest
from unittest.mock import MagicMock

from phylo_module import config, pipeline_phylo
from phylo_module.pathogens import meta_entity_for
from phylo_module.pipeline_phylo import _job_accession_ids, accessions_passing_completeness

# The pipeline resolves this from the job's pathogen; these cases are all dengue
DENGUE_META = meta_entity_for("DENV")

WHOLE_GENOMES = ["FJ850076.1", "FJ850078.1", "GQ868550.1"]
PARTIAL_GENOMES = ["GU131864.1", "GU131882.1"]

SEQUENCE_LENGTHS = {
    "FJ850076.1": 10723,
    "FJ850078.1": 10450,
    "GQ868550.1": 10701,
    "GU131864.1": 4200,
    "GU131882.1": 1800,
}


def meta_rows_for(accession_ids):
    return [
        {"genbank_sequence_data_id": accession_id, "length": SEQUENCE_LENGTHS[accession_id]}
        for accession_id in accession_ids
    ]


def requested_accessions(database_service):
    and_filters = database_service.get_record_by_filters.call_args.kwargs["and_filters"]
    return list(and_filters[0].right.value)


class JobAccessionIdsTest(unittest.TestCase):

    def test_row_order_and_duplicates_do_not_change_the_set(self):
        shuffled = {"accession_ids": ["GQ868550.1", "FJ850076.1", "GQ868550.1", "FJ850078.1"]}
        self.assertEqual(_job_accession_ids(shuffled), WHOLE_GENOMES)

    def test_null_and_blank_entries_are_dropped(self):
        noisy = {"accession_ids": ["FJ850076.1", None, "  ", "", "FJ850078.1", "GQ868550.1"]}
        self.assertEqual(_job_accession_ids(noisy), WHOLE_GENOMES)

    def test_accession_versions_are_preserved(self):
        # Version suffix is a distinct tip (.1 vs .2)
        revised = {"accession_ids": ["FJ850076.2", "FJ850076.1"]}
        self.assertEqual(_job_accession_ids(revised), ["FJ850076.1", "FJ850076.2"])

    def test_a_job_without_accession_ids_yields_nothing(self):
        self.assertEqual(_job_accession_ids({"accession_ids": None}), [])
        self.assertEqual(_job_accession_ids({}), [])


class AccessionsPassingCompletenessTest(unittest.TestCase):

    def database_returning(self, accession_ids):
        database_service = MagicMock()
        database_service.get_record_by_filters.return_value = meta_rows_for(accession_ids)
        return database_service

    def test_only_the_submitted_accessions_are_queried(self):
        # Continent filter is frontend-only; use submitted IDs as-is
        submitted = sorted(WHOLE_GENOMES)
        database_service = self.database_returning(submitted)

        accessions_passing_completeness(database_service, submitted, "complete_genome", DENGUE_META)

        self.assertEqual(requested_accessions(database_service), submitted)

    def test_sequences_below_the_whole_genome_threshold_are_removed(self):
        submitted = sorted(WHOLE_GENOMES + PARTIAL_GENOMES)
        database_service = self.database_returning(submitted)

        kept = accessions_passing_completeness(database_service, submitted, "complete_genome", DENGUE_META)

        self.assertEqual(sorted(kept), sorted(WHOLE_GENOMES))

    def test_any_length_keeps_sequences_above_the_usable_floor(self):
        submitted = sorted(WHOLE_GENOMES + PARTIAL_GENOMES)
        database_service = self.database_returning(submitted)

        kept = accessions_passing_completeness(database_service, submitted, "any", DENGUE_META)

        above_floor = [
            accession_id for accession_id in submitted
            if SEQUENCE_LENGTHS[accession_id] >= config.MIN_SEQUENCE_LENGTH
        ]
        self.assertEqual(sorted(kept), above_floor)

    def test_selection_is_never_widened(self):
        submitted = ["FJ850076.1"]
        database_service = self.database_returning(submitted)

        kept = accessions_passing_completeness(database_service, submitted, "complete_genome", DENGUE_META)

        self.assertEqual(kept, submitted)


class WatcherSelectionContractTest(unittest.TestCase):

    def test_the_watcher_has_no_filter_params_reconstruction(self):
        # Must not rebuild selection from filter_params
        self.assertFalse(hasattr(pipeline_phylo, "resolve_accession_ids_from_filter_params"))


if __name__ == "__main__":
    unittest.main()
