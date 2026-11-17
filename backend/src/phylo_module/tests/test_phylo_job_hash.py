import unittest

from phylo_module.pipeline_phylo import (
    INFERENCE_METHOD_FASTTREE,
    INFERENCE_METHOD_IQTREE,
    _phylo_job_hash,
    _treetime_enabled,
)
from phylo_module.services.treetime_service import resolve_treetime_settings

ACCESSIONS = ["FJ850076.1", "FJ850078.1", "FJ850080.1"]


def _treetime_inputs(dated_tips=None, **setting_overrides):
    if dated_tips is None:
        dated_tips = {
            "FJ850076.1": "2008-03-01",
            "FJ850078.1": "2008-04-01",
            "FJ850080.1": "2009-01-15",
        }
    return {
        "settings": dict(resolve_treetime_settings({}), **setting_overrides),
        "dated_tips": dated_tips,
        "excluded_tips": [],
    }


class TestTreetimeEnabled(unittest.TestCase):
    """The dashboard sends no TreeTime field yet; its absence must not disable the stage."""

    def test_absent_key_uses_the_backend_default(self):
        self.assertTrue(_treetime_enabled({"serotype": "DENV2"}))

    def test_explicit_false_disables(self):
        self.assertFalse(_treetime_enabled({"treetime": False}))


class TestPhyloJobHash(unittest.TestCase):
    def test_identical_inputs_give_the_same_hash(self):
        first = _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, _treetime_inputs())
        second = _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, _treetime_inputs())
        self.assertEqual(first, second)

    def test_accession_order_and_duplicates_do_not_matter(self):
        shuffled = list(reversed(ACCESSIONS)) + [ACCESSIONS[0], "  "]
        self.assertEqual(
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, None),
            _phylo_job_hash(shuffled, INFERENCE_METHOD_FASTTREE, None),
        )

    def test_different_sequence_set_gives_a_different_hash(self):
        self.assertNotEqual(
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, None),
            _phylo_job_hash(ACCESSIONS[:2], INFERENCE_METHOD_FASTTREE, None),
        )

    def test_adding_an_accession_gives_a_different_hash(self):
        self.assertNotEqual(
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, None),
            _phylo_job_hash(ACCESSIONS + ["GQ868550.1"], INFERENCE_METHOD_FASTTREE, None),
        )

    def test_a_revised_accession_version_gives_a_different_hash(self):
        # .2 must not reuse a tree cached for .1
        revised = ["FJ850076.2"] + ACCESSIONS[1:]
        self.assertNotEqual(
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, None),
            _phylo_job_hash(revised, INFERENCE_METHOD_FASTTREE, None),
        )

    def test_the_same_sequence_set_hashes_alike_however_it_was_selected(self):
        # Same IDs → same hash regardless of filter path
        selected_by_country = ["FJ850078.1", "FJ850076.1", "FJ850080.1"]
        selected_by_continent = ["FJ850080.1", "FJ850078.1", "FJ850076.1"]
        self.assertEqual(
            _phylo_job_hash(selected_by_country, INFERENCE_METHOD_FASTTREE, None),
            _phylo_job_hash(selected_by_continent, INFERENCE_METHOD_FASTTREE, None),
        )

    def test_engine_is_part_of_the_hash(self):
        self.assertNotEqual(
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, None),
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_IQTREE, None),
        )

    def test_enabled_and_disabled_treetime_never_share_a_cache_identity(self):
        self.assertNotEqual(
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, _treetime_inputs()),
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, None),
        )

    def test_corrected_collection_date_retires_the_cached_result(self):
        corrected = {
            "FJ850076.1": "2008-03-01",
            "FJ850078.1": "2008-04-01",
            "FJ850080.1": "2009-01-16",
        }
        self.assertNotEqual(
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, _treetime_inputs()),
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, _treetime_inputs(corrected)),
        )

    def test_treetime_parameters_are_part_of_the_hash(self):
        for changed_setting in ({"seed": 999}, {"clock_filter": 3}, {"reroot": "min_dev"},
                                {"keep_polytomies": False}, {"branch_length_mode": "joint"},
                                {"clock_filter_method": "local"}):
            with self.subTest(setting=changed_setting):
                self.assertNotEqual(
                    _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, _treetime_inputs()),
                    _phylo_job_hash(
                        ACCESSIONS,
                        INFERENCE_METHOD_FASTTREE,
                        _treetime_inputs(**changed_setting),
                    ),
                )

    def test_dated_tip_order_does_not_matter(self):
        reordered = dict(reversed(list(_treetime_inputs()["dated_tips"].items())))
        self.assertEqual(
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, _treetime_inputs()),
            _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, _treetime_inputs(reordered)),
        )

    def test_hash_is_a_sha256_hex_digest(self):
        job_hash = _phylo_job_hash(ACCESSIONS, INFERENCE_METHOD_FASTTREE, _treetime_inputs())
        self.assertEqual(len(job_hash), 64)
        self.assertTrue(all(character in "0123456789abcdef" for character in job_hash))


if __name__ == "__main__":
    unittest.main()
