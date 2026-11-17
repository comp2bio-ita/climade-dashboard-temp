#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The job-queue boundary, driven by a stand-in database client."""

import pytest

from pathogens import get_pathogen
from utils.phylo.result_provider import (
    KEY_COLUMN,
    load_phylogeny_result,
    load_phylogeny_status,
)

DENGUE = get_pathogen("denv")

NEWICK = "((PH031933.1:0.1,PX945878.1:0.2)95:0.3,(PX945876.1:0.15,PX945877.1:0.25)80:0.05);"

CLOCK = {
    "status": "done",
    "clock_rate": 0.002219,
    "r_squared": 0.25,
    "dated_tips": 25,
    "tree_tips": 25,
    "dated_fraction": 1.0,
    "excluded_tips": [],
}

METADATA = {
    "PH031933.1": {"serotype": "DENV2", "genotype": "2V", "country": "Unknown",
                   "host": "unknown", "collection_date": "2025-02-28T00:00:00Z",
                   "location": "Brazil"},
    "PX945878.1": {"serotype": "DENV2", "genotype": "2II", "country": "USA",
                   "host": "Homo sapiens", "collection_date": "2025-06-08T00:00:00Z",
                   "location": "USA: FL"},
}


class FakeClient:
    """Just enough DashDatabaseClient to exercise the provider."""

    def __init__(self, job=None, metadata=None):
        self.job = job
        self.metadata = METADATA if metadata is None else metadata
        self.status_reads = 0

    def get_phylo_job_status(self, job_id):
        self.status_reads += 1
        if not self.job or self.job["id"] != job_id:
            return None
        return {key: self.job.get(key) for key in
                ("id", "status", "warnings", "error_message",
                 "sequence_count", "inference_method")}

    def get_phylo_job_result(self, job_id):
        return self.job if self.job and self.job["id"] == job_id else None

    def get_tip_metadata(self, accession_ids, pathogen="dengue"):
        return {a: self.metadata[a] for a in accession_ids if a in self.metadata}


def job(**overrides):
    row = {
        "id": 10,
        "status": "done",
        "newick": NEWICK,
        "time_tree_nexus": None,
        "sequence_count": 4,
        "inference_method": "IQ-TREE",
        "warnings": [{"message": "Tree generated successfully", "level": "info", "ts": "x"}],
        "error_message": None,
        "run_metadata": {"treetime": CLOCK},
    }
    row.update(overrides)
    return row


@pytest.fixture
def dated_job(timetree_nexus, pipeline_newick):
    return job(newick=pipeline_newick, time_tree_nexus=timetree_nexus, sequence_count=25)


class TestStatus:
    def test_running_job_reports_its_event_log(self):
        result = load_phylogeny_status(FakeClient(job(status="processing")), 10)
        assert result["status"] == "processing"
        assert result["events"][0]["message"] == "Tree generated successfully"

    def test_missing_job_is_none(self):
        assert load_phylogeny_status(FakeClient(job()), 999) is None

    def test_no_job_id_does_not_hit_the_database(self):
        client = FakeClient(job())
        assert load_phylogeny_status(client, None) is None
        assert client.status_reads == 0

    def test_status_never_carries_tree_text(self):
        result = load_phylogeny_status(FakeClient(job()), 10)
        assert "substitution_newick" not in result
        assert "time_tree_nexus" not in result


class TestMissingAndFailedResults:
    def test_missing_job(self):
        result = load_phylogeny_result(FakeClient(None), 10, DENGUE)
        assert result["status"] == "missing"
        assert result["substitution_newick"] is None

    def test_failed_job_keeps_its_error_and_events(self):
        client = FakeClient(job(status="failed", newick=None,
                                error_message="MAFFT exited 1"))
        result = load_phylogeny_result(client, 10, DENGUE)
        assert result["status"] == "failed"
        assert result["error_message"] == "MAFFT exited 1"
        assert result["events"]

    def test_done_without_a_tree_is_treated_as_failed(self):
        result = load_phylogeny_result(FakeClient(job(newick=None)), 10, DENGUE)
        assert result["status"] == "failed"

    def test_unreadable_tree_is_reported_not_raised(self):
        result = load_phylogeny_result(FakeClient(job(newick="not a tree")), 10, DENGUE)
        assert result["status"] == "failed"
        assert "could not be read" in result["error_message"]


class TestCompletedResult:
    def test_both_trees_are_returned_verbatim(self, dated_job, pipeline_newick, timetree_nexus):
        result = load_phylogeny_result(FakeClient(dated_job), 10, DENGUE)
        assert result["substitution_newick"] == pipeline_newick
        assert result["time_tree_nexus"] == timetree_nexus

    def test_result_is_json_serializable_for_a_dcc_store(self, dated_job):
        import json


        json.dumps(load_phylogeny_result(FakeClient(dated_job), 10, DENGUE))

    def test_tip_records_are_keyed_on_the_accession(self):
        result = load_phylogeny_result(FakeClient(job()), 10, DENGUE)
        assert result["key_column"] == KEY_COLUMN
        assert {r[KEY_COLUMN] for r in result["tip_records"]} == set(METADATA)

    def test_tip_records_carry_every_declared_column(self):
        result = load_phylogeny_result(FakeClient(job()), 10, DENGUE)
        record_columns = set(result["tip_records"][0])
        assert set(result["metadata_columns"]) <= record_columns
        assert "locality" in record_columns
        assert "division" in record_columns

    def test_tip_records_derive_locality_from_ncbi_location(self):
        result = load_phylogeny_result(FakeClient(job()), 10, DENGUE)
        by_accession = {row[KEY_COLUMN]: row for row in result["tip_records"]}
        assert by_accession["PH031933.1"]["locality"] == "Brazil"
        assert by_accession["PX945878.1"]["locality"] == "FL"

    def test_tip_records_derive_division_from_ncbi_location(self):
        result = load_phylogeny_result(FakeClient(job()), 10, DENGUE)
        by_accession = {row[KEY_COLUMN]: row for row in result["tip_records"]}
        assert by_accession["PH031933.1"]["division"] is None
        assert by_accession["PX945878.1"]["division"] == "FL"

    def test_clock_numbers_are_passed_through_unjudged(self, dated_job):
        clock = load_phylogeny_result(FakeClient(dated_job), 10, DENGUE)["clock"]
        assert clock["r_squared"] == 0.25
        assert clock["clock_rate"] == 0.002219

    def test_absent_run_metadata_gives_no_clock(self):
        result = load_phylogeny_result(FakeClient(job(run_metadata=None)), 10, DENGUE)
        assert result["clock"] is None


class TestMetadataReport:
    def test_tips_without_metadata_are_named(self):
        report = load_phylogeny_result(FakeClient(job()), 10, DENGUE)["metadata_report"]
        assert report["matched"] == 2
        assert sorted(report["unmatched"]) == ["PX945876.1", "PX945877.1"]

    def test_no_metadata_at_all_is_not_silently_fine(self):
        report = load_phylogeny_result(FakeClient(job(), metadata={}), 10, DENGUE)["metadata_report"]
        assert report["matched"] == 0
        assert len(report["unmatched"]) == 4

    def test_all_tips_matched_on_the_real_pipeline_tree(self, dated_job):
        real = {a: {"serotype": "DENV2"} for a in
                _tip_labels(dated_job["newick"])}
        report = load_phylogeny_result(FakeClient(dated_job, real), 10, DENGUE)["metadata_report"]
        assert report["matched"] == 25
        assert report["unmatched"] == []


class TestTipSetReport:
    def test_no_dated_tree_means_no_comparison(self):
        assert load_phylogeny_result(FakeClient(job()), 10, DENGUE)["tip_set_report"] is None

    def test_identical_tip_sets_on_the_real_run(self, dated_job):
        report = load_phylogeny_result(FakeClient(dated_job), 10, DENGUE)["tip_set_report"]
        assert report == {"only_in_substitution": [], "only_in_time_tree": []}

    def test_tips_treetime_dropped_are_listed(self, dated_job, timetree_nexus):
        extra = dated_job["newick"].replace(
            "(", "(EXCLUDED.1:0.001,", 1).replace(")", ")", 1)
        client = FakeClient(job(newick=extra, time_tree_nexus=timetree_nexus))
        report = load_phylogeny_result(client, 10, DENGUE)["tip_set_report"]
        assert report["only_in_substitution"] == ["EXCLUDED.1"]
        assert report["only_in_time_tree"] == []


def _tip_labels(newick):
    from utils.phylo.viewer.parse import parse_newick

    return parse_newick(newick).tip_labels()


class TestPathogenDrivesTheMetadataVocabulary:
    """Task D1: the columns and colour-by options come from the spec, not a constant."""

    def test_dengue_offers_its_lineages(self):
        from utils.phylo.result_provider import color_by_fields_for

        assert color_by_fields_for(get_pathogen("denv")) == [
            "serotype", "genotype", "major_lineage", "minor_lineage",
            "country", "division", "locality", "host"]

    def test_a_single_axis_pathogen_offers_only_what_it_has(self):
        from utils.phylo.result_provider import color_by_fields_for

        for key in ("chikv", "zikv"):
            assert color_by_fields_for(get_pathogen(key)) == [
                "genotype", "country", "division", "locality", "host"]

    def test_hover_columns_start_with_the_accession_then_the_classifications(self):
        from utils.phylo.result_provider import metadata_columns_for

        dengue = metadata_columns_for(get_pathogen("denv"))
        assert dengue[0] == KEY_COLUMN
        assert dengue[1:5] == ["serotype", "genotype", "major_lineage", "minor_lineage"]
        # region and location are hover-only and never offered for colouring
        assert "region" in dengue and "location" in dengue

        chik = metadata_columns_for(get_pathogen("chikv"))
        assert chik[1] == "genotype"
        assert "serotype" not in chik

    def test_the_result_reports_which_pathogen_it_came_from(self):
        result = load_phylogeny_result(FakeClient(job()), 10, get_pathogen("chikv"))
        assert result["pathogen"] == "chikv"
        assert result["color_by_fields"] == ["genotype", "country", "division", "locality", "host"]

    def test_the_client_is_asked_for_that_pathogens_metadata(self):
        class RecordingClient(FakeClient):
            asked_for = None

            def get_tip_metadata(self, accession_ids, pathogen="dengue"):
                RecordingClient.asked_for = pathogen
                return {}

        load_phylogeny_result(RecordingClient(job()), 10, get_pathogen("zikv"))
        assert RecordingClient.asked_for == "zikv"
