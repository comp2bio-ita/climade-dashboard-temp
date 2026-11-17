#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Biological correctness, checked against the artifacts of one real run.

Run `af4d1cfe156d99c7` (job #10): 25 dengue accessions, IQ-TREE then TreeTime.
These assertions are about the science the figure claims, not about the code.
"""

import io

import pytest
from Bio import Phylo

from utils.phylo.panel import SUBSTITUTION_SCALE, TIME_SCALE, build_phylogeny_figure
from pathogens import get_pathogen
from utils.phylo.result_provider import KEY_COLUMN, color_by_fields_for, metadata_columns_for

DENGUE = get_pathogen("denv")
METADATA_COLUMNS = metadata_columns_for(DENGUE)
from utils.phylo.viewer.parse import parse_newick

# From dash_infra run_metadata["treetime"] for this run.
EXPECTED_CLOCK_RATE = 0.002219
EXPECTED_R_SQUARED = 0.25
EXPECTED_ROOT_DATE = 1910.3


@pytest.fixture
def result(pipeline_newick, timetree_nexus):
    tips = parse_newick(pipeline_newick).tip_labels()
    return {
        "job_id": 10,
        "status": "done",
        "error_message": None,
        "events": [],
        "substitution_newick": pipeline_newick,
        "time_tree_nexus": timetree_nexus,
        "inference_method": "IQ-TREE",
        "sequence_count": len(tips),
        "tip_records": [{KEY_COLUMN: tip, "serotype": "DENV2", "genotype": "2II",
                         "major_lineage": None, "minor_lineage": None, "country": "USA",
                         "region": "North America", "location": "USA: FL", "division": "FL",
                         "locality": "FL",
                         "host": "Homo sapiens",
                         "collection_date": "2025-06-08T00:00:00Z"} for tip in tips],
        "metadata_columns": METADATA_COLUMNS,
        "color_by_fields": color_by_fields_for(DENGUE),
        "key_column": KEY_COLUMN,
        "clock": {"status": "done", "clock_rate": EXPECTED_CLOCK_RATE,
                  "r_squared": EXPECTED_R_SQUARED, "dated_tips": 25, "tree_tips": 25,
                  "dated_fraction": 1.0, "excluded_tips": []},
        "metadata_report": {"matched": len(tips), "unmatched": [], "duplicated": []},
        "tip_set_report": {"only_in_substitution": [], "only_in_time_tree": []},
    }


class TestTopologyIsPreserved:
    def test_tip_count_matches_the_pipeline(self, pipeline_newick):
        assert parse_newick(pipeline_newick).n_tips == 25

    def test_topology_matches_biopython_on_the_same_file(self, pipeline_newick):
        ours = _clade_sets(parse_newick(pipeline_newick))
        theirs = _biopython_clade_sets(pipeline_newick)
        assert ours == theirs

    def test_dated_tree_topology_matches_biopython(self, timetree_nexus):
        assert _clade_sets(parse_newick(timetree_nexus)) == _biopython_clade_sets(
            timetree_nexus, fmt="nexus")

    def test_every_node_but_the_root_has_exactly_one_parent(self, pipeline_newick):
        tree = parse_newick(pipeline_newick)
        assert sum(len(node.children) for node in tree.internal_nodes) == len(tree) - 1


class TestAccessionsAreExact:
    def test_tip_labels_are_versioned_genbank_accessions(self, pipeline_newick):
        labels = parse_newick(pipeline_newick).tip_labels()
        assert all(label.count(".") == 1 for label in labels)
        assert all(label.split(".")[1].isdigit() for label in labels)

    def test_no_label_is_altered_between_the_two_artifacts(self, pipeline_newick,
                                                           timetree_nexus):
        assert (sorted(parse_newick(pipeline_newick).tip_labels())
                == sorted(parse_newick(timetree_nexus).tip_labels()))

    def test_labels_reaching_the_figure_are_the_stored_labels(self, result):
        figure = build_phylogeny_figure(result, scale=SUBSTITUTION_SCALE,
                                        color_by="genotype")
        drawn = {str(point[0]) for trace in figure.data
                 for point in (trace.customdata or [])}
        assert drawn == set(parse_newick(result["substitution_newick"]).tip_labels())


class TestUnitsAreNotConfused:
    def test_substitution_branch_lengths_are_small_fractions(self, pipeline_newick):
        tree = parse_newick(pipeline_newick)
        assert max(tree.depth(tip) for tip in tree.tips) < 1.0

    def test_temporal_branch_lengths_are_years(self, timetree_nexus):
        tree = parse_newick(timetree_nexus)
        assert 100 < max(tree.depth(tip) for tip in tree.tips) < 200

    def test_root_is_the_treetime_estimate(self, timetree_nexus):
        assert parse_newick(timetree_nexus).root_date == EXPECTED_ROOT_DATE

    def test_every_tip_is_dated_within_the_sampling_window(self, timetree_nexus):
        tree = parse_newick(timetree_nexus)
        assert all(2024 <= tip.date <= 2027 for tip in tree.tips)

    def test_the_two_axes_are_labelled_differently(self, result):
        substitution = build_phylogeny_figure(result, scale=SUBSTITUTION_SCALE)
        dated = build_phylogeny_figure(result, scale=TIME_SCALE)
        assert substitution.layout.xaxis.title.text == "Branch length"
        assert dated.layout.xaxis.title.text == "Year"

    def test_a_dated_tree_is_never_drawn_as_substitutions(self, result):
        dated = build_phylogeny_figure(result, scale=TIME_SCALE)
        substitution = build_phylogeny_figure(result, scale=SUBSTITUTION_SCALE)
        assert dated.data[0].x != substitution.data[0].x


class TestSupportBelongsToTheInferredTree:
    def test_iqtree_support_survives_parsing(self, pipeline_newick):
        assert parse_newick(pipeline_newick).has_support()

    def test_compound_shalrt_ufboot_labels_are_split(self, pipeline_newick):
        tree = parse_newick(pipeline_newick)
        sh_values = [node.support_sh_alrt for node in tree.internal_nodes
                     if node.support_sh_alrt is not None]
        uf_values = [node.support_ufboot for node in tree.internal_nodes
                     if node.support_ufboot is not None]
        assert sh_values and all(0 <= value <= 100 for value in sh_values)
        assert uf_values and all(0 <= value <= 100 for value in uf_values)

    def test_treetime_node_ids_are_not_misread_as_support(self):
        tree = parse_newick("((A:0.1,B:0.2)NODE_0000001:0.3,C:0.4);")
        assert not tree.has_support()


class TestNoFabrication:
    def test_absent_dated_tree_never_borrows_the_substitution_tree(self, result):
        result["time_tree_nexus"] = None
        assert build_phylogeny_figure(result, scale=TIME_SCALE).data == ()

    def test_missing_metadata_is_not_invented(self, result):
        result["tip_records"] = result["tip_records"][:1]
        figure = build_phylogeny_figure(result, color_by="genotype")
        assert any("Unknown" in (trace.name or "") for trace in figure.data)


def _clade_sets(tree):
    """Every internal node as the frozenset of tips beneath it."""
    tips_below = {}
    for node in tree.postorder():
        if node.is_tip:
            tips_below[node.id] = {node.name}
        else:
            tips_below[node.id] = set().union(
                *(tips_below[child.id] for child in node.children))
    return {frozenset(tips_below[node.id]) for node in tree.internal_nodes}


def _biopython_clade_sets(text, fmt="newick"):
    tree = next(Phylo.parse(io.StringIO(text), fmt))
    return {frozenset(leaf.name for leaf in clade.get_terminals())
            for clade in tree.get_nonterminals()}
