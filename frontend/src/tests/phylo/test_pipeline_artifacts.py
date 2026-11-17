#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The two artifacts the backend actually produces, rendered side by side.

`pipeline_tree.nwk` and `example_timetree.nexus` come from the same phylo run
(IQ-TREE then TreeTime, 25 dengue accessions). Together they guard the one
distinction the dashboard must never blur: substitutions per site is not
calendar time.
"""

from utils.phylo.viewer.parse import parse_newick
from utils.phylo.viewer.render import render_tree


class TestArtifactPair:
    def test_same_tips_in_both_artifacts(self, pipeline_newick, timetree_nexus):
        substitution = parse_newick(pipeline_newick)
        dated = parse_newick(timetree_nexus)
        assert set(substitution.tip_labels()) == set(dated.tip_labels())
        assert substitution.n_tips == 25

    def test_accessions_survive_parsing_unchanged(self, timetree_nexus):
        labels = parse_newick(timetree_nexus).tip_labels()
        assert "PH031933.1" in labels
        # A NEXUS round trip through Newick mangles these into escaped comment
        # text; every label must still be a bare versioned GenBank accession.
        assert all(label.count(".") == 1 and "[" not in label for label in labels)

    def test_only_the_treetime_artifact_carries_dates(self, pipeline_newick, timetree_nexus):
        assert parse_newick(pipeline_newick).has_dates() is False
        assert parse_newick(timetree_nexus).has_dates() is True

    def test_substitution_artifact_carries_support(self, pipeline_newick):
        assert parse_newick(pipeline_newick).has_support() is True

    def test_timetree_may_embed_iqtree_support_strings(self, timetree_nexus):
        # TreeTime NEXUS often retains IQ-TREE internal labels such as "91/96".
        assert parse_newick(timetree_nexus).has_support() is True

    def test_root_date_is_the_treetime_estimate(self, timetree_nexus):
        assert parse_newick(timetree_nexus).root_date == 1910.3


class TestArtifactAxes:
    def test_dated_tree_gets_a_calendar_axis(self, timetree_nexus):
        figure = render_tree(timetree_nexus)
        assert figure.layout.xaxis.title.text == "Year"
        assert figure.layout.xaxis.tickformat == "d"

    def test_substitution_tree_gets_a_divergence_axis(self, pipeline_newick):
        figure = render_tree(pipeline_newick)
        assert figure.layout.xaxis.title.text == "Branch length"
        assert figure.layout.xaxis.tickformat in (None, "")

    def test_tip_coordinates_are_sample_years(self, timetree_nexus):
        tree = parse_newick(timetree_nexus)
        tip_years = [tree.root_date + tree.depth(tip) for tip in tree.tips]
        assert all(2020 < year < 2030 for year in tip_years)

    def test_cladogram_refuses_to_wear_a_calendar_axis(self, timetree_nexus):
        figure = render_tree(timetree_nexus, cladogram=True)
        assert figure.layout.xaxis.title.text != "Year"
