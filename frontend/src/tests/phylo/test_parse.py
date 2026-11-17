#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Newick parsing and the tree model."""

import pytest

from utils.phylo.viewer.model import PhyloTree
from utils.phylo.viewer.parse import NewickParseError, parse_newick, read_newick


class TestBasicParsing:
    def test_tip_count_and_labels(self, simple_newick):
        tree = parse_newick(simple_newick)
        assert tree.n_tips == 4
        assert tree.tip_labels() == ["A", "B", "C", "D"]

    def test_branch_lengths(self, simple_newick):
        tree = parse_newick(simple_newick)
        by_name = {t.name: t.branch_length for t in tree.tips}
        assert by_name == pytest.approx({"A": 0.1, "B": 0.2, "C": 0.15, "D": 0.25})

    def test_depths_accumulate_along_the_path(self, simple_newick):
        tree = parse_newick(simple_newick)
        depths = {t.name: tree.depth(t) for t in tree.tips}
        assert depths["A"] == pytest.approx(0.4)   # 0.3 + 0.1
        assert depths["D"] == pytest.approx(0.30)  # 0.05 + 0.25

    def test_support_is_read_from_internal_labels(self, simple_newick):
        tree = parse_newick(simple_newick)
        assert tree.has_support()
        assert sorted(n.support for n in tree.internal_nodes if n.support) == [80.0, 95.0]

    def test_tips_never_carry_support(self, simple_newick):
        tree = parse_newick(simple_newick)
        assert all(t.support is None for t in tree.tips)

    def test_parent_links_and_root(self, simple_newick):
        tree = parse_newick(simple_newick)
        assert tree.root.is_root and tree.root.parent is None
        assert all(t.parent is not None for t in tree.tips)

    def test_node_ids_are_unique(self, example_newick):
        tree = parse_newick(example_newick)
        assert len({n.id for n in tree.preorder()}) == tree.n_nodes


class TestAwkwardInput:
    def test_cladogram_has_no_branch_lengths(self, cladogram_newick):
        tree = parse_newick(cladogram_newick)
        assert tree.n_tips == 4
        assert not tree.has_branch_lengths()
        assert tree.max_depth == 0.0

    def test_polytomy_is_preserved(self, polytomy_newick):
        tree = parse_newick(polytomy_newick)
        assert len(tree.root.children) == 4

    def test_unnamed_tips_get_synthetic_names(self, messy_newick):
        tree = parse_newick(messy_newick)
        assert all(t.name for t in tree.tips)
        assert sum(name.startswith("tip_") for name in tree.tip_labels()) == 2

    def test_duplicate_labels_stay_distinct_nodes(self, messy_newick):
        tree = parse_newick(messy_newick)
        assert tree.tip_labels().count("B") == 2
        assert len(tree.find_tips(["B"])) == 2

    def test_single_tip_tree(self):
        tree = parse_newick("(A:0.1);")
        assert tree.n_tips == 1
        assert tree.tip_labels() == ["A"]

    def test_iqtree_alrt_slash_bootstrap_labels(self):
        """`-alrt X -bb Y` writes "95/98"; both metrics are kept."""
        tree = parse_newick("((A:0.1,B:0.2)95/98:0.3,C:0.4);")
        internal = [n for n in tree.internal_nodes if n.support_sh_alrt is not None]
        assert len(internal) == 1
        assert internal[0].support_sh_alrt == 95.0
        assert internal[0].support_ufboot == 98.0
        assert internal[0].support == 95.0

    def test_non_numeric_internal_labels_are_not_support(self):
        tree = parse_newick("((A:0.1,B:0.2)clade_x:0.3,C:0.4);")
        assert not tree.has_support()


class TestSources:
    def test_accepts_a_path(self, example_tree_path):
        assert parse_newick(example_tree_path).n_tips == 202

    def test_accepts_a_path_string(self, example_tree_path):
        assert parse_newick(str(example_tree_path)).n_tips == 202

    def test_read_newick_alias(self, example_tree_path):
        assert read_newick(example_tree_path).n_tips == 202

    def test_accepts_a_file_handle(self, example_tree_path):
        with example_tree_path.open() as handle:
            assert parse_newick(handle).n_tips == 202

    def test_passes_a_parsed_tree_through(self, simple_newick):
        tree = parse_newick(simple_newick)
        assert parse_newick(tree) is tree


class TestErrors:
    @pytest.mark.parametrize("bad", ["", "   ", "\n"])
    def test_empty_input_is_rejected(self, bad):
        with pytest.raises(NewickParseError, match="Empty input"):
            parse_newick(bad)

    def test_missing_file_is_rejected(self, tmp_path):
        with pytest.raises(NewickParseError, match="not found"):
            parse_newick(tmp_path / "nope.nwk")

    def test_multiple_trees_are_rejected(self):
        with pytest.raises(NewickParseError, match="2 trees"):
            parse_newick("(A,B);(C,D);")

    def test_malformed_newick_is_rejected(self):
        with pytest.raises(NewickParseError):
            parse_newick("((((A,B);")

    def test_error_message_quotes_the_input(self):
        with pytest.raises(NewickParseError, match="MARKER"):
            parse_newick("((MARKER,B);")


class TestTraversal:
    def test_postorder_places_children_before_parents(self, example_newick):
        tree = parse_newick(example_newick)
        seen= set()
        for node in tree.postorder():
            assert all(child.id in seen for child in node.children)
            seen.add(node.id)

    def test_preorder_places_parents_before_children(self, example_newick):
        tree = parse_newick(example_newick)
        seen= set()
        for node in tree.preorder():
            if node.parent is not None:
                assert node.parent.id in seen
            seen.add(node.id)

    def test_both_orders_cover_every_node(self, example_newick):
        tree = parse_newick(example_newick)
        assert len(tree.preorder()) == len(tree.postorder()) == tree.n_nodes

    def test_deep_ladder_parses_without_recursion_error(self, ladder_newick):
        tree = parse_newick(ladder_newick)
        assert tree.n_tips == 2000
        assert isinstance(tree, PhyloTree)

    def test_levels_count_edges_from_the_root(self, cladogram_newick):
        tree = parse_newick(cladogram_newick)
        levels = tree.levels()
        assert levels[tree.root.id] == 0
        assert {levels[t.id] for t in tree.tips} == {2}


class TestNexusTimetree:
    """TreeTime writes NEXUS, not Newick, and dates every node."""

    def test_nexus_text_parses(self, timetree_nexus):
        tree = parse_newick(timetree_nexus)
        assert tree.n_tips == 25

    def test_nexus_path_parses(self, timetree_path):
        assert parse_newick(timetree_path).n_tips == 25

    def test_nexus_header_semicolons_are_not_counted_as_trees(self, timetree_nexus):
        """Regression: the Newick multi-tree guard read the NEXUS header blocks
        as extra trees and rejected every timetree with "Input holds 7 trees"."""
        assert parse_newick(timetree_nexus).n_tips == 25

    def test_every_node_carries_a_date(self, timetree_nexus):
        tree = parse_newick(timetree_nexus)
        assert tree.has_dates()
        assert all(n.date is not None for n in tree.preorder())

    def test_root_date_precedes_every_tip(self, timetree_nexus):
        tree = parse_newick(timetree_nexus)
        assert tree.root_date == pytest.approx(1910.3)
        assert all(t.date > tree.root_date for t in tree.tips)

    def test_depth_plus_root_date_reproduces_each_node_date(self, timetree_nexus):
        """Branch lengths are years, so root_date + depth is the node's date.

        This is the property the calendar axis rests on. TreeTime prints dates
        rounded to two decimals while branch lengths keep full precision, so
        agreement is only expected to within a few days.
        """
        tree = parse_newick(timetree_nexus)
        worst = max(abs(tree.root_date + tree.depth(n) - n.date) for n in tree.preorder())
        assert worst < 0.01  # years, i.e. under four days

    def test_mutation_counts_are_kept_but_not_the_list(self, timetree_nexus):
        tree = parse_newick(timetree_nexus)
        assert all(isinstance(t.n_mutations, int) for t in tree.tips)
        assert max(t.n_mutations for t in tree.tips) > 0

    def test_treetime_node_ids_are_not_read_as_support(self):
        """TreeTime NODE_* ids must not be parsed as bootstrap values."""
        tree = parse_newick("((A:0.1,B:0.2)NODE_0000001:0.3,C:0.4);")
        assert not tree.has_support()

    def test_a_plain_newick_tree_is_undated(self, simple_newick):
        tree = parse_newick(simple_newick)
        assert not tree.has_dates()
        assert tree.root_date is None
        assert all(t.date is None for t in tree.tips)


class TestRealPipelineOutput:
    def test_example_tree_shape(self, example_newick):
        tree = parse_newick(example_newick)
        assert tree.n_tips == 202
        assert tree.has_support()
        assert tree.has_branch_lengths()

    def test_pipe_delimited_labels_survive_intact(self, example_newick):
        tree = parse_newick(example_newick)
        assert "A04321|FR|1983" in tree.tip_labels()
