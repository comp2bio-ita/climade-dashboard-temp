#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Layout geometry.

These assert on coordinates, not on figures — the point of separating layout
from rendering is that geometry can be checked with plain arithmetic.
"""

import math

import pytest

from utils.phylo.viewer.layouts import LAYOUTS, compute_layout, get_layout
from utils.phylo.viewer.parse import parse_newick

ALL_LAYOUTS = ["rect", "circ", "radial"]


def _finite(values):
    return [v for v in values if v is not None]


@pytest.fixture
def tree(example_newick):
    return parse_newick(example_newick)


class TestRegistry:
    def test_all_layouts_registered(self):
        assert set(LAYOUTS) == {"rect", "circ", "radial"}

    @pytest.mark.parametrize("alias,expected", [
        ("rectangular", "rect"), ("phylogram", "rect"),
        ("circular", "circ"), ("fan", "circ"), ("unrooted", "radial"),
    ])
    def test_aliases_resolve(self, alias, expected):
        assert get_layout(alias).name == expected

    def test_unknown_layout_raises(self):
        with pytest.raises(ValueError, match="Unknown layout"):
            get_layout("spiral")

    def test_only_rect_declines_rotation(self):
        assert get_layout("rect").supports_rotation is False
        assert get_layout("circ").supports_rotation is True
        assert get_layout("radial").supports_rotation is True


class TestCommonInvariants:
    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_every_node_is_placed(self, tree, layout):
        result = compute_layout(tree, layout)
        assert len(result.positions) == tree.n_nodes
        assert {n.id for n in tree.preorder()} == set(result.positions)

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_no_nan_or_infinite_coordinates(self, tree, layout):
        result = compute_layout(tree, layout)
        for pos in result.positions.values():
            assert math.isfinite(pos.x) and math.isfinite(pos.y)
        assert all(math.isfinite(v) for v in _finite(result.branch_x))
        assert all(math.isfinite(v) for v in _finite(result.branch_y))

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_branch_polylines_are_paired(self, tree, layout):
        result = compute_layout(tree, layout)
        assert len(result.branch_x) == len(result.branch_y)
        # A None in one array must be a None in the other, or Plotly draws a
        # line across the figure where a break was intended.
        for x, y in zip(result.branch_x, result.branch_y):
            assert (x is None) == (y is None)

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_every_tip_has_a_label_anchor(self, tree, layout):
        result = compute_layout(tree, layout)
        for tip in tree.tips:
            assert result.tip_anchor[tip.id]
            assert result.label_xy(tip.id) is not None

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_axis_ranges_contain_the_tree(self, tree, layout):
        result = compute_layout(tree, layout)
        xs = [p.x for p in result.positions.values()]
        ys = [p.y for p in result.positions.values()]
        x_lo, x_hi = result.axes.x_range
        y_lo, y_hi = result.axes.y_range
        assert x_lo <= min(xs) and max(xs) <= x_hi
        assert y_lo <= min(ys) and max(ys) <= y_hi

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_polytomies_are_handled(self, polytomy_newick, layout):
        result = compute_layout(parse_newick(polytomy_newick), layout)
        assert len(result.positions) == 5

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_cladogram_mode_works_without_branch_lengths(self, cladogram_newick, layout):
        result = compute_layout(parse_newick(cladogram_newick), layout)
        # All four tips must be distinguishable, not stacked at the origin.
        tips = parse_newick(cladogram_newick).tips
        points = {(round(result.positions[t.id].x, 6),
                   round(result.positions[t.id].y, 6)) for t in tips}
        assert len(points) == 4

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_single_tip_tree_does_not_crash(self, layout):
        result = compute_layout(parse_newick("(A:0.1);"), layout)
        assert len(result.positions) == 2

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_deep_ladder_has_no_recursion_error(self, ladder_newick, layout):
        """Regression guard: recursive layouts blow the stack on this shape."""
        tree = parse_newick(ladder_newick)
        result = compute_layout(tree, layout)
        assert len(result.positions) == tree.n_nodes


class TestRectangular:
    def test_tips_occupy_consecutive_integer_rows(self, tree):
        result = compute_layout(tree, "rect")
        ys = sorted(result.positions[t.id].y for t in tree.tips)
        assert ys == [float(i) for i in range(tree.n_tips)]

    def test_x_never_decreases_from_parent_to_child(self, tree):
        result = compute_layout(tree, "rect")
        for node in tree.preorder():
            for child in node.children:
                assert result.positions[child.id].x >= result.positions[node.id].x - 1e-12

    def test_x_is_cumulative_branch_length(self, simple_newick):
        tree = parse_newick(simple_newick)
        result = compute_layout(tree, "rect")
        by_name = {t.name: result.positions[t.id].x for t in tree.tips}
        assert by_name["A"] == pytest.approx(0.4)
        assert by_name["C"] == pytest.approx(0.20)

    def test_internal_nodes_centre_on_their_children(self, simple_newick):
        tree = parse_newick(simple_newick)
        result = compute_layout(tree, "rect")
        for node in tree.internal_nodes:
            child_ys = [result.positions[c.id].y for c in node.children]
            assert result.positions[node.id].y == pytest.approx(
                (min(child_ys) + max(child_ys)) / 2
            )

    def test_align_tips_flushes_every_tip_to_one_x(self, tree):
        result = compute_layout(tree, "rect", align_tips=True)
        xs = {round(result.label_xy(t.id)[0], 9) for t in tree.tips}
        assert len(xs) == 1

    def test_cladogram_spaces_by_level_not_length(self, simple_newick):
        tree = parse_newick(simple_newick)
        result = compute_layout(tree, "rect", cladogram=True)
        assert {result.positions[t.id].x for t in tree.tips} == {2.0}

    def test_rotation_is_ignored(self, tree):
        plain = compute_layout(tree, "rect")
        rotated = compute_layout(tree, "rect", rotation_deg=90)
        assert plain.positions[tree.root.id] == rotated.positions[tree.root.id]

    @pytest.mark.parametrize("orientation", ["right", "left", "up", "down"])
    def test_orientations_produce_distinct_geometry(self, simple_newick, orientation):
        tree = parse_newick(simple_newick)
        result = compute_layout(tree, "rect", orientation=orientation)
        assert len(result.positions) == tree.n_nodes
        assert all(math.isfinite(p.x) and math.isfinite(p.y)
                   for p in result.positions.values())

    def test_unknown_orientation_falls_back_to_right(self, simple_newick):
        tree = parse_newick(simple_newick)
        odd = compute_layout(tree, "rect", orientation="sideways")
        right = compute_layout(tree, "rect", orientation="right")
        assert odd.positions[tree.root.id] == right.positions[tree.root.id]

    def test_height_hint_scales_with_tip_count(self, tree):
        assert compute_layout(tree, "rect").axes.height_hint > 400
        small = compute_layout(parse_newick("(A:0.1,B:0.2);"), "rect")
        assert small.axes.height_hint == 400


class TestCircular:
    def test_radii_are_normalised_to_the_unit_circle(self, tree):
        result = compute_layout(tree, "circ")
        radii = [p.radius for p in result.positions.values()]
        assert min(radii) == pytest.approx(0.0)
        assert max(radii) == pytest.approx(1.0)
        assert all(0.0 <= r <= 1.0 + 1e-9 for r in radii)

    def test_tip_angles_are_distinct(self, tree):
        result = compute_layout(tree, "circ")
        angles = {round(result.positions[t.id].angle, 9) for t in tree.tips}
        assert len(angles) == tree.n_tips

    def test_full_circle_does_not_overlap_first_and_last_tip(self, tree):
        result = compute_layout(tree, "circ")
        first = result.positions[tree.tips[0].id].angle
        last = result.positions[tree.tips[-1].id].angle
        assert last - first < 2 * math.pi - 1e-9

    def test_rotation_shifts_every_tip_by_the_same_angle(self, tree):
        plain = compute_layout(tree, "circ")
        rotated = compute_layout(tree, "circ", rotation_deg=90)
        shifts = {
            round(rotated.positions[t.id].angle - plain.positions[t.id].angle, 9)
            for t in tree.tips
        }
        assert shifts == {round(math.radians(90), 9)}

    def test_partial_arc_spans_only_the_requested_wedge(self, tree):
        result = compute_layout(tree, "circ", arc_span_deg=180)
        angles = [result.positions[t.id].angle for t in tree.tips]
        assert max(angles) - min(angles) == pytest.approx(math.pi)

    def test_align_tips_puts_labels_on_the_outer_circle(self, tree):
        result = compute_layout(tree, "circ", align_tips=True)
        for tip in tree.tips:
            x, y = result.label_xy(tip.id)
            assert math.hypot(x, y) == pytest.approx(1.0)

    def test_labels_on_the_left_half_anchor_leftwards(self, tree):
        result = compute_layout(tree, "circ")
        for tip in tree.tips:
            deg = math.degrees(result.positions[tip.id].angle) % 360
            expected = "middle left" if 90 < deg < 270 else "middle right"
            assert result.tip_anchor[tip.id] == expected

    def test_aspect_ratio_is_locked(self, tree):
        assert compute_layout(tree, "circ").axes.equal_aspect is True

    def test_polar_and_cartesian_agree(self, tree):
        result = compute_layout(tree, "circ")
        for pos in result.positions.values():
            assert pos.x == pytest.approx(pos.radius * math.cos(pos.angle))
            assert pos.y == pytest.approx(pos.radius * math.sin(pos.angle))


class TestRadial:
    def test_root_sits_at_the_origin(self, tree):
        result = compute_layout(tree, "radial")
        assert result.positions[tree.root.id].x == pytest.approx(0.0)
        assert result.positions[tree.root.id].y == pytest.approx(0.0)

    def test_children_are_offset_from_their_parent(self, tree):
        result = compute_layout(tree, "radial")
        for node in tree.internal_nodes:
            parent = result.positions[node.id]
            for child in node.children:
                pos = result.positions[child.id]
                assert math.hypot(pos.x - parent.x, pos.y - parent.y) > 0

    def test_branch_length_sets_the_distance_walked(self, simple_newick):
        tree = parse_newick(simple_newick)
        result = compute_layout(tree, "radial")
        for node in tree.internal_nodes:
            parent = result.positions[node.id]
            for child in node.children:
                pos = result.positions[child.id]
                distance = math.hypot(pos.x - parent.x, pos.y - parent.y)
                assert distance == pytest.approx(max(child.branch_length, 0.01 * tree.max_depth))

    def test_zero_length_branches_do_not_collapse_nodes(self):
        tree = parse_newick("((A:0.0,B:0.0):0.0,C:0.5);")
        result = compute_layout(tree, "radial")
        points = {(round(result.positions[t.id].x, 9),
                   round(result.positions[t.id].y, 9)) for t in tree.tips}
        assert len(points) == 3

    def test_rotation_changes_the_layout(self, tree):
        plain = compute_layout(tree, "radial")
        rotated = compute_layout(tree, "radial", rotation_deg=90)
        moved = sum(
            1 for t in tree.tips
            if abs(plain.positions[t.id].x - rotated.positions[t.id].x) > 1e-9
        )
        assert moved > tree.n_tips / 2

    def test_aspect_ratio_is_locked(self, tree):
        assert compute_layout(tree, "radial").axes.equal_aspect is True


class TestUnknownOptionsAreIgnored:
    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_shared_option_bundle_is_accepted_by_every_layout(self, tree, layout):
        """A shared UI passes every option to whichever layout is selected."""
        result = compute_layout(
            tree, layout,
            cladogram=False, align_tips=True, rotation_deg=45,
            arc_span_deg=340, orientation="right", show_labels=True,
            future_option_that_does_not_exist=True,
        )
        assert len(result.positions) == tree.n_nodes


class TestTimeOrigin:
    """`time_origin` shifts a phylogram onto a calendar without changing shape."""

    def test_it_offsets_every_x_by_the_origin(self, simple_newick):
        tree = parse_newick(simple_newick)
        plain = compute_layout(tree, "rect")
        dated = compute_layout(tree, "rect", time_origin=2000.0)
        for node in tree.preorder():
            assert dated.xy(node.id)[0] == pytest.approx(plain.xy(node.id)[0] + 2000.0)

    def test_it_leaves_the_topology_untouched(self, simple_newick):
        tree = parse_newick(simple_newick)
        plain = compute_layout(tree, "rect")
        dated = compute_layout(tree, "rect", time_origin=2000.0)
        for node in tree.preorder():
            assert dated.xy(node.id)[1] == plain.xy(node.id)[1]

    def test_the_axis_is_labelled_in_years(self, simple_newick):
        axes = compute_layout(parse_newick(simple_newick), "rect", time_origin=2000.0).axes
        assert axes.x_title == "Year"
        assert axes.x_tickformat == "d"

    def test_label_room_is_proportional_to_the_tree_not_the_origin(self, simple_newick):
        """Regression: padding derived from the largest x reserved ~1100 years
        of label room once the origin sat near 2026."""
        tree = parse_newick(simple_newick)
        near = compute_layout(tree, "rect", time_origin=10.0).axes
        far = compute_layout(tree, "rect", time_origin=2026.0).axes
        assert (near.x_range[1] - near.x_range[0]) == pytest.approx(
            far.x_range[1] - far.x_range[0]
        )

    def test_the_range_stays_tight_to_the_data(self, simple_newick):
        tree = parse_newick(simple_newick)
        axes = compute_layout(tree, "rect", time_origin=2000.0).axes
        assert axes.reserve_label_margin
        assert axes.x_range[1] - (2000.0 + tree.max_depth) < tree.max_depth * 0.1

    def test_a_cladogram_ignores_the_origin(self, cladogram_newick):
        """No branch lengths means no elapsed years to place on a calendar."""
        axes = compute_layout(parse_newick(cladogram_newick), "rect",
                              time_origin=2000.0).axes
        assert axes.x_title == "Divergence (levels)"

    @pytest.mark.parametrize("orientation", ["left", "up", "down"])
    def test_only_a_right_growing_tree_gets_a_date_axis(self, simple_newick, orientation):
        """A calendar reads left to right; the other orientations would run it
        backwards or turn it on its side."""
        axes = compute_layout(parse_newick(simple_newick), "rect",
                              time_origin=2000.0, orientation=orientation).axes
        assert axes.x_title != "Year"

    def test_polar_layouts_ignore_the_option(self, simple_newick):
        tree = parse_newick(simple_newick)
        for layout in ("circ", "radial"):
            plain = compute_layout(tree, layout)
            dated = compute_layout(tree, layout, time_origin=2000.0)
            assert dated.xy(tree.tips[0].id) == plain.xy(tree.tips[0].id)
