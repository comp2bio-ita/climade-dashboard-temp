#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Figure assembly."""

import math

import pytest

from utils.phylo.viewer import (
    figure_to_html,
    layout_coordinates,
    render_timetree,
    render_tree,
)
from utils.phylo.viewer.annotate import BaseAnnotator, MetadataAnnotator, TipStyle
from utils.phylo.viewer.parse import parse_newick
from utils.phylo.viewer.theme import CATEGORICAL, LIGHT

ALL_LAYOUTS = ["rect", "circ", "radial"]


def trace_names(fig):
    return [t.name for t in fig.data]


class TestBasicFigure:
    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_every_layout_produces_a_figure(self, example_newick, layout):
        fig = render_tree(example_newick, layout=layout)
        assert len(fig.data) >= 2
        assert fig.layout.height

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_figures_serialise(self, example_newick, layout):
        """A figure that cannot round-trip cannot reach the browser."""
        assert render_tree(example_newick, layout=layout).to_dict()["data"]

    def test_branches_are_the_first_trace(self, example_newick):
        assert render_tree(example_newick).data[0].name == "branches"

    def test_branches_do_not_capture_hover(self, example_newick):
        assert render_tree(example_newick).data[0].hoverinfo == "skip"

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_no_nan_coordinates_reach_the_figure(self, example_newick, layout):
        fig = render_tree(example_newick, layout=layout)
        for trace in fig.data:
            for axis in (trace.x, trace.y):
                for value in axis or ():
                    if value is not None:
                        assert math.isfinite(value)

    def test_accepts_a_path(self, example_tree_path):
        assert render_tree(example_tree_path).data

    def test_accepts_a_parsed_tree(self, example_newick):
        assert render_tree(parse_newick(example_newick)).data

    def test_title_is_rendered(self, example_newick):
        fig = render_tree(example_newick, title="My tree")
        assert any("My tree" in (a.text or "") for a in fig.layout.annotations)


class TestTraceBatching:
    def test_tips_are_batched_into_one_trace_per_group(self, example_newick,
                                                       example_metadata_path):
        """The whole point of the batching: trace count tracks groups, not tips."""
        fig = render_tree(example_newick, metadata=example_metadata_path,
                          color_by="region", show_support=False)
        tree = parse_newick(example_newick)
        annot = MetadataAnnotator(example_metadata_path, color_by="region")
        n_groups = len({annot.style_for(t.name).group for t in tree.tips})
        assert len(fig.data) == 1 + n_groups
        assert len(fig.data) < 12  # 202 tips, but only a handful of traces

    def test_trace_count_is_independent_of_tip_count(self, example_newick):
        big = render_tree(example_newick, show_support=False)
        small = render_tree("((A:0.1,B:0.2):0.3,C:0.4);", show_support=False)
        assert len(big.data) == len(small.data) == 2

    def test_every_tip_is_plotted_exactly_once(self, example_newick,
                                               example_metadata_path):
        fig = render_tree(example_newick, metadata=example_metadata_path,
                          color_by="subtype")
        plotted = [point[0] for trace in fig.data
                   if trace.customdata is not None
                   for point in trace.customdata]
        assert sorted(plotted) == sorted(parse_newick(example_newick).tip_labels())

    def test_group_names_become_legend_entries(self, example_newick,
                                               example_metadata_path):
        fig = render_tree(example_newick, metadata=example_metadata_path,
                          color_by="region", show_support=False)
        assert "Europe" in trace_names(fig)
        assert all(t.showlegend for t in fig.data[1:])


class TestLabels:
    def test_auto_shows_labels_on_a_small_tree(self):
        fig = render_tree("((A:0.1,B:0.2):0.3,C:0.4);", show_labels="auto")
        assert fig.data[1].mode == "markers+text"

    def test_auto_hides_labels_on_a_large_tree(self, example_newick):
        fig = render_tree(example_newick, show_labels="auto")
        assert fig.data[1].mode == "markers"

    def test_threshold_is_configurable(self, example_newick):
        fig = render_tree(example_newick, show_labels="auto", label_threshold=500)
        assert fig.data[1].mode == "markers+text"

    def test_labels_can_be_forced_on(self, example_newick):
        assert render_tree(example_newick, show_labels=True).data[1].mode == "markers+text"

    def test_labels_can_be_forced_off(self):
        fig = render_tree("((A:0.1,B:0.2):0.3,C:0.4);", show_labels=False)
        assert fig.data[1].mode == "markers"

    def test_hidden_labels_are_explained_in_the_figure(self, example_newick):
        fig = render_tree(example_newick, show_labels="auto")
        assert any("labels hidden" in (a.text or "") for a in fig.layout.annotations)

    def test_label_text_carries_the_tip_name(self):
        fig = render_tree("((A:0.1,B:0.2):0.3,C:0.4);", show_labels=True)
        assert "A" in "".join(fig.data[1].text)


class TestAngledLabels:
    """Polar layouts rotate each tip label to follow its own branch.

    `go.Scatter` has no `textangle`, so these labels are annotations rather
    than trace text — which is why the tip traces go markers-only.
    """

    def tip_annotations(self, fig):
        # Header annotations (title, "labels hidden") are paper-referenced;
        # tip labels are the ones placed in data coordinates.
        return [a for a in fig.layout.annotations if a.textangle is not None]

    @pytest.mark.parametrize("layout", ["circ", "radial"])
    def test_one_annotation_per_tip(self, example_newick, layout):
        fig = render_tree(example_newick, layout=layout, show_labels=True)
        assert len(self.tip_annotations(fig)) == parse_newick(example_newick).n_tips

    @pytest.mark.parametrize("layout", ["circ", "radial"])
    def test_no_label_is_ever_upside_down(self, example_newick, layout):
        """The readability invariant: every label reads left-to-right."""
        fig = render_tree(example_newick, layout=layout, show_labels=True)
        for annotation in self.tip_annotations(fig):
            assert -90.001 <= annotation.textangle <= 90.001

    def test_known_angles_produce_the_expected_rotation(self):
        """Four tips on a full circle land at 0/90/180/270 degrees."""
        fig = render_tree("(A:1,B:1,C:1,D:1);", layout="circ", show_labels=True)
        by_label = {a.text: a for a in self.tip_annotations(fig)}
        assert by_label["A"].textangle == 0     # pointing right
        assert by_label["B"].textangle == -90   # pointing up
        assert by_label["C"].textangle == 0     # pointing left, turned to read
        assert by_label["D"].textangle == 90    # pointing down

    def test_far_side_labels_are_turned_to_read_left_to_right(self, example_newick):
        """Without the 180-degree turn, half the circle would be mirror-written."""
        fig = render_tree(example_newick, layout="circ", show_labels=True)
        geometry = layout_coordinates(example_newick, "circ")
        tree = parse_newick(example_newick)
        flipped = {t.name for t in tree.tips
                   if geometry.tip_anchor[t.id] == "middle left"}
        assert flipped  # the fixture must actually exercise both halves
        by_label = {a.text: a for a in self.tip_annotations(fig)}
        for tip in tree.tips:
            degrees = math.degrees(geometry.positions[tip.id].angle) % 360
            expected = (180 - degrees) if tip.name in flipped else -degrees
            # Plotly wraps textangle into [-180, 180]; compare like for like.
            expected = ((expected + 180) % 360) - 180
            assert by_label[tip.name].textangle == pytest.approx(expected)

    def test_labels_sit_outside_their_tip_not_on_top_of_it(self):
        """Plotly centres a rotated label on its anchor, ignoring `xanchor`.

        Left unhandled, every label lands on its own tip — and because the
        anchor *is* honoured at 0/180 degrees, the label mass ends up wider
        than tall, so the tree reads as an oval instead of a circle. The
        outward pixel shift is what prevents both.
        """
        fig = render_tree("(A:1,B:1,C:1,D:1);", layout="circ", show_labels=True)
        geometry = layout_coordinates("(A:1,B:1,C:1,D:1);", "circ")
        tree = parse_newick("(A:1,B:1,C:1,D:1);")
        by_label = {a.text: a for a in self.tip_annotations(fig)}
        for tip in tree.tips:
            angle = geometry.positions[tip.id].angle
            annotation = by_label[tip.name]
            shift = math.hypot(annotation.xshift, annotation.yshift)
            assert shift > 0
            # The shift must point away from the centre, along the branch.
            assert annotation.xshift == pytest.approx(shift * math.cos(angle), abs=1e-6)
            assert annotation.yshift == pytest.approx(shift * math.sin(angle), abs=1e-6)

    def test_longer_labels_are_pushed_further_out(self):
        """Half-length offsets are what align every label's inner edge."""
        fig = render_tree("(A:1,BBBBBBBBBBBBBBBBBBBB:1);", layout="circ",
                          show_labels=True)
        by_label = {a.text: a for a in self.tip_annotations(fig)}
        short = math.hypot(by_label["A"].xshift, by_label["A"].yshift)
        long = math.hypot(by_label["BBBBBBBBBBBBBBBBBBBB"].xshift,
                          by_label["BBBBBBBBBBBBBBBBBBBB"].yshift)
        assert long > short

    def test_aligned_tips_keep_labels_clear_of_the_ring(self):
        """The reported bug: with align_tips on, labels landed on the markers."""
        newick = "((A:0.1,BBBBBBBBBBBB:0.9):0.2,(CCCCCCCCCCCC:0.5,D:0.3):0.4);"
        fig = render_tree(newick, layout="circ", align_tips=True, show_labels=True)
        geometry = layout_coordinates(newick, "circ", align_tips=True)
        tree = parse_newick(newick)
        by_label = {a.text: a for a in self.tip_annotations(fig)}
        for tip in tree.tips:
            x, y = geometry.label_xy(tip.id)
            annotation = by_label[tip.name]
            # Anchored on the aligned ring, then shifted off it in pixels.
            assert (annotation.x, annotation.y) == pytest.approx((x, y))
            assert math.hypot(annotation.xshift, annotation.yshift) > 0

    @pytest.mark.parametrize("layout", ["circ", "radial"])
    def test_tip_traces_are_markers_only(self, example_newick, layout):
        """Labels come from annotations, so trace text would double-draw them."""
        fig = render_tree(example_newick, layout=layout, show_labels=True)
        assert fig.data[1].mode == "markers"
        assert fig.data[1].text is None

    def test_rectangular_still_uses_trace_text(self, example_newick):
        fig = render_tree(example_newick, layout="rect", show_labels=True)
        assert not self.tip_annotations(fig)
        assert fig.data[1].mode == "markers+text"

    @pytest.mark.parametrize("layout", ["circ", "radial"])
    def test_no_annotations_when_labels_are_off(self, example_newick, layout):
        fig = render_tree(example_newick, layout=layout, show_labels=False)
        assert not self.tip_annotations(fig)

    @pytest.mark.parametrize("layout", ["circ", "radial"])
    def test_hover_survives(self, example_newick, layout):
        """Markers keep their identity even though the text moved out."""
        fig = render_tree(example_newick, layout=layout, show_labels=True)
        assert fig.data[1].customdata is not None
        assert "customdata[0]" in fig.data[1].hovertemplate

    def test_header_annotations_coexist_with_tip_labels(self, example_newick):
        fig = render_tree(example_newick, layout="circ", show_labels=True,
                          title="My tree")
        assert any("My tree" in (a.text or "") for a in fig.layout.annotations)
        assert len(self.tip_annotations(fig)) == parse_newick(example_newick).n_tips

    def test_rotating_the_tree_rotates_the_labels(self, example_newick):
        plain = render_tree(example_newick, layout="circ", show_labels=True)
        turned = render_tree(example_newick, layout="circ", show_labels=True,
                             rotation_deg=90)
        assert ([a.textangle for a in self.tip_annotations(plain)]
                != [a.textangle for a in self.tip_annotations(turned)])

    def test_long_labels_reserve_more_room(self):
        short = render_tree("(AB:1,CD:1,EF:1);", layout="circ", show_labels=True)
        long = render_tree(f"({'X' * 40}:1,{'Y' * 40}:1,{'Z' * 40}:1);",
                           layout="circ", show_labels=True)
        assert long.layout.xaxis.range[1] > short.layout.xaxis.range[1]

    def test_the_figure_margin_makes_room_for_overflow(self, example_newick):
        """Annotations are sized in pixels and spill past the axis range."""
        labelled = render_tree(example_newick, layout="circ", show_labels=True)
        bare = render_tree(example_newick, layout="circ", show_labels=False)
        assert labelled.layout.margin.r > bare.layout.margin.r


class TestSupport:
    def test_support_is_present_when_the_tree_has_support(self, simple_newick):
        assert _support_annotations(render_tree(simple_newick))

    def test_support_can_be_switched_off(self, simple_newick):
        assert not _support_annotations(render_tree(simple_newick, show_support=False))

    def test_no_support_when_the_tree_has_none(self, cladogram_newick):
        assert not _support_annotations(render_tree(cladogram_newick))

    def test_threshold_filters_weak_nodes(self, simple_newick):
        """The fixture has support 95 and 80."""
        assert len(_support_annotations(render_tree(simple_newick))) == 2
        assert len(_support_annotations(
            render_tree(simple_newick, support_threshold=90))) == 1
        assert not _support_annotations(
            render_tree(simple_newick, support_threshold=99))

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_every_layout_draws_support(self, simple_newick, layout):
        """Radial used to omit support values; all three must agree."""
        assert _support_annotations(render_tree(simple_newick, layout=layout))

    def test_integral_support_renders_without_decimals(self, simple_newick):
        assert set(_support_numerals(render_tree(simple_newick))) == {"95", "80"}

    def test_every_numeral_is_offset_clear_of_its_branch(self, simple_newick):
        """The node sits on the branch; pixel shifts keep the numeral readable."""
        for annotation in _support_annotations(render_tree(simple_newick)):
            assert annotation.xshift == 24
            assert annotation.yshift == -6

    def test_numerals_use_the_support_colour(self, simple_newick):
        annotations = _support_annotations(render_tree(simple_newick))
        assert annotations
        assert all(a.font.color == LIGHT["support"] for a in annotations)
        assert LIGHT["support"] == "#0D6EFD"

    def test_dual_metric_tree_can_show_either_field(self):
        tree_text = "((A:0.1,B:0.2)95/98:0.3,C:0.4);"
        assert _support_numerals(render_tree(
            tree_text, support_metric="sh_alrt")) == ["95"]
        assert _support_numerals(render_tree(
            tree_text, support_metric="ufboot")) == ["98"]

    def test_threshold_applies_to_the_selected_metric(self):
        tree_text = "((A:0.1,B:0.2)95/98:0.3,C:0.4);"
        assert _support_numerals(render_tree(
            tree_text, support_metric="sh_alrt", support_threshold=96)) == []
        assert _support_numerals(render_tree(
            tree_text, support_metric="ufboot", support_threshold=96)) == ["98"]

    def test_dated_tree_borrows_support_from_substitution_tree(self):
        source = "((A:0.1,B:0.2)95/98:0.3,C:0.4);"
        target = "((A:0.1,B:0.2):0.3,C:0.4);"
        assert not parse_newick(target).has_support()
        assert _support_annotations(render_tree(
            target,
            support_source=source,
        ))


def _support_annotations(fig):
    return [a for a in fig.layout.annotations if a.name == "support"]


def _support_numerals(fig):
    return [a.text for a in _support_annotations(fig)]


class TestHover:
    def test_customdata_carries_label_hover_and_url(self, example_newick):
        fig = render_tree(example_newick)
        label, hover, url = fig.data[1].customdata[0]
        assert label
        assert isinstance(hover, str)
        assert url.startswith("https://www.ncbi.nlm.nih.gov/")

    def test_hovertemplate_reads_from_customdata(self, example_newick):
        assert "customdata[0]" in render_tree(example_newick).data[1].hovertemplate

    def test_metadata_columns_appear_in_the_hover_text(self, example_newick,
                                                      example_metadata_path):
        fig = render_tree(example_newick, metadata=example_metadata_path,
                          color_by="region", hover_cols=["country", "year"])
        hover = fig.data[1].customdata[0][1]
        assert "country:" in hover and "year:" in hover

    def test_ncbi_links_can_be_disabled(self, example_newick):
        fig = render_tree(example_newick, link_ncbi=False)
        assert fig.data[1].customdata[0][2] == ""


class TestHighlight:
    def test_matching_tips_get_a_highlight_trace(self, example_newick):
        fig = render_tree(example_newick, highlight=["A04321|FR|1983"])
        assert any((t.name or "").startswith("Match") for t in fig.data)

    def test_highlight_counts_the_matches(self, example_newick):
        fig = render_tree(example_newick, highlight=["A04321|FR|1983", "AB078005|US|1997"])
        assert "Match (2)" in trace_names(fig)

    def test_no_trace_when_nothing_matches(self, example_newick):
        fig = render_tree(example_newick, highlight=["not-a-tip"])
        assert not any((t.name or "").startswith("Match") for t in fig.data)

    def test_highlight_is_drawn_last(self, example_newick):
        fig = render_tree(example_newick, highlight=["A04321|FR|1983"])
        assert (fig.data[-1].name or "").startswith("Match")


class FlagAnnotator(BaseAnnotator):
    """A caller-supplied annotator, to prove the extension point still works."""

    def __init__(self, flagged=(), group_order=None):
        self.flagged = set(flagged)
        self._groups = list(group_order) if group_order is not None else ["Flagged", "Plain"]

    def groups(self):
        return list(self._groups)

    def style_for(self, label):
        if label in self.flagged:
            return TipStyle(group="Flagged", color="#cf222e")
        return TipStyle(group="Plain", color="#1a7f37")


class TestAnnotators:
    def test_a_custom_annotator_drives_colours_and_groups(self, example_newick):
        annot = FlagAnnotator(flagged=["A04321|FR|1983"])
        fig = render_tree(example_newick, annotator=annot, show_support=False)
        assert trace_names(fig) == ["branches", "Flagged", "Plain"]
        assert len(fig.data[1].x) == 1

    def test_annotator_and_metadata_are_mutually_exclusive(self, example_newick,
                                                           example_metadata_path):
        with pytest.raises(ValueError, match="not both"):
            render_tree(example_newick, annotator=FlagAnnotator(),
                        metadata=example_metadata_path)

    def test_metadata_colours_come_from_the_categorical_palette(self, example_newick):
        annot = MetadataAnnotator([{"accession": "A04321", "g": "x"}], color_by="g")
        render_tree(example_newick, annotator=annot)
        assert annot.style_for("A04321").color in CATEGORICAL

    def test_unanticipated_groups_still_reach_the_legend(self, example_newick):
        """A group the annotator did not declare must not silently drop tips."""
        annot = FlagAnnotator(group_order=[])
        fig = render_tree(example_newick, annotator=annot, show_support=False)
        assert "Plain" in trace_names(fig)


class TestPalette:
    def test_the_light_palette_is_applied(self, example_newick):
        fig = render_tree(example_newick)
        assert fig.layout.paper_bgcolor == LIGHT["paper"]
        assert fig.layout.plot_bgcolor == LIGHT["plot"]
        assert fig.data[0].line.color == LIGHT["line"]

    def test_branches_are_the_project_grey(self, example_newick):
        """Pinned to the literal: the value is the requirement, not whatever
        happens to sit in the palette."""
        assert LIGHT["line"] == "#3C4043"
        assert render_tree(example_newick).data[0].line.color == "#3C4043"

    def test_branches_do_not_share_a_colour_with_a_metadata_group(self):
        """The tree skeleton is structure, not data — it must not read as one
        of the categorical groups."""
        assert LIGHT["line"] not in CATEGORICAL


class TestFigureLayout:
    def test_circular_and_radial_lock_the_aspect_ratio(self, example_newick):
        for layout in ("circ", "radial"):
            fig = render_tree(example_newick, layout=layout)
            assert fig.layout.xaxis.scaleanchor == "y"

    def test_rectangular_does_not_lock_the_aspect_ratio(self, example_newick):
        assert render_tree(example_newick).layout.xaxis.scaleanchor is None

    def test_rectangular_shows_a_distance_axis(self, example_newick):
        fig = render_tree(example_newick)
        assert fig.layout.xaxis.showticklabels
        assert "Branch length" in fig.layout.xaxis.title.text

    def test_cladogram_relabels_the_axis(self, example_newick):
        fig = render_tree(example_newick, cladogram=True)
        assert "levels" in fig.layout.xaxis.title.text

    def test_circular_hides_the_axes(self, example_newick):
        fig = render_tree(example_newick, layout="circ")
        assert not fig.layout.xaxis.showticklabels
        assert not fig.layout.yaxis.showticklabels

    def test_explicit_height_and_width_win(self, example_newick):
        fig = render_tree(example_newick, height=1234, width=567)
        assert fig.layout.height == 1234 and fig.layout.width == 567

    def test_pan_is_the_default_drag_mode(self, example_newick):
        assert render_tree(example_newick).layout.dragmode == "pan"


class TestErrors:
    def test_an_unknown_layout_raises(self, example_newick):
        with pytest.raises(ValueError, match="Unknown layout"):
            render_tree(example_newick, layout="spiral")


class TestExports:
    def test_layout_coordinates_returns_geometry_without_a_figure(self, example_newick):
        geometry = layout_coordinates(example_newick, "radial")
        assert len(geometry.positions) == parse_newick(example_newick).n_nodes

    def test_figure_to_html_writes_a_self_contained_page(self, example_newick, tmp_path):
        path = tmp_path / "tree.html"
        figure_to_html(render_tree(example_newick, layout="circ"), path)
        html = path.read_text(encoding="utf-8")
        assert html.startswith("<html")
        # Inlined Plotly means the file works offline, which is the point.
        # (The bundle itself mentions a CDN for topojson, so the check has to
        # be for a remote script source, not for the bare hostname.)
        assert 'src="https://cdn.plot.ly' not in html
        assert path.stat().st_size > 100_000

    def test_figure_to_html_can_use_the_cdn(self, example_newick):
        fig = render_tree(example_newick)
        cdn = figure_to_html(fig, include_plotlyjs=False)
        assert 'src="https://cdn.plot.ly' in cdn
        # The saving over the inlined form is the reason to choose the CDN.
        assert len(cdn) < len(figure_to_html(fig)) / 10


class TestScale:
    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_a_deep_ladder_renders(self, ladder_newick, layout):
        fig = render_tree(ladder_newick, layout=layout)
        assert len(fig.data) >= 2


class TestTimeAxis:
    """A TreeTime timetree is a phylogram whose x-axis is a calendar."""

    NARROW_TIMETREE = """#NEXUS
Begin Taxa;
 Dimensions NTax=2;
 TaxLabels tip_a tip_b;
End;
Begin Trees;
 Tree tree1=(tip_a:0.3[&date=2024.25],tip_b:0.5[&date=2024.75])NODE:0.0[&date=2024.00];
End;
"""

    BROAD_10Y_TIMETREE = """#NEXUS
Begin Taxa;
 Dimensions NTax=2;
 TaxLabels tip_a tip_b;
End;
Begin Trees;
 Tree tree1=(tip_a:5.0[&date=2019.00],tip_b:5.0[&date=2024.00])NODE:0.0[&date=2014.00];
End;
"""

    ANCIENT_ROOT_TIMETREE = """#NEXUS
Begin Taxa;
 Dimensions NTax=2;
 TaxLabels tip_a tip_b;
End;
Begin Trees;
 Tree tree1=(tip_a:800.0[&date=2020.00],tip_b:810.0[&date=2025.00])NODE:0.0[&date=1200.00];
End;
"""

    PRE_1677_ROOT_TIMETREE = """#NEXUS
Begin Taxa;
 Dimensions NTax=2;
 TaxLabels tip_a tip_b;
End;
Begin Trees;
 Tree tree1=(tip_a:400.0[&date=2020.00],tip_b:425.0[&date=2025.00])NODE:0.0[&date=1600.00];
End;
"""

    def test_a_dated_tree_gets_a_year_axis_without_being_asked(self, timetree_nexus):
        fig = render_tree(timetree_nexus)
        assert fig.layout.xaxis.title.text == "Year"
        assert fig.layout.xaxis.tickformat == "d"
        assert fig.layout.xaxis.tickmode == "linear"
        assert fig.layout.xaxis.dtick >= 1

    def test_a_narrow_dated_tree_shows_month_year_ticks(self):
        fig = render_tree(self.NARROW_TIMETREE)
        assert fig.layout.xaxis.tickmode == "array"
        labels = list(fig.layout.xaxis.ticktext)
        assert any("Jan" in label for label in labels)
        assert any("2024" in label for label in labels)

    def test_a_ten_year_dated_tree_uses_linear_one_year_ticks(self):
        fig = render_tree(self.BROAD_10Y_TIMETREE)
        assert fig.layout.xaxis.tickmode == "linear"
        assert fig.layout.xaxis.dtick == 1
        assert fig.layout.xaxis.tickformat == "d"

    def test_ancient_root_dated_tree_renders_without_error(self):
        fig = render_tree(self.ANCIENT_ROOT_TIMETREE)
        assert len(fig.data) >= 2
        assert fig.layout.xaxis.title.text == "Year"

    def test_pre_1677_root_dated_tree_renders_without_error(self):
        fig = render_tree(self.PRE_1677_ROOT_TIMETREE)
        assert len(fig.data) >= 2
        assert fig.layout.xaxis.title.text == "Year"

    def test_an_undated_tree_keeps_the_divergence_axis(self, example_newick):
        assert render_tree(example_newick).layout.xaxis.title.text == "Branch length"

    def test_the_axis_spans_calendar_years(self, timetree_nexus):
        low, high = render_tree(timetree_nexus).layout.xaxis.range
        assert 1900 < low < 1915           # root is 1910.3
        assert 2026 < high < 2035          # newest tip is 2026.22

    def test_the_axis_does_not_run_past_the_data_to_fit_labels(self, timetree_nexus):
        """Regression: label room used to be taken from the axis range, which
        on a calendar axis printed ticks for years no sequence was collected in."""
        tree = parse_newick(timetree_nexus)
        newest = max(t.date for t in tree.tips)
        fig = render_tree(timetree_nexus)
        _low, high = fig.layout.xaxis.range
        assert high - newest < 5           # years of slack, not the ~64 of a data pad
        assert fig.layout.margin.r > 20    # labels live in the margin instead

    def test_each_tip_sits_on_its_own_date(self, timetree_nexus):
        tree = parse_newick(timetree_nexus)
        geometry = layout_coordinates(tree, "rect", time_origin=tree.root_date)
        for tip in tree.tips:
            # TreeTime rounds the dates it prints to two decimals; the geometry
            # uses full-precision branch lengths, so a few days of slack.
            assert geometry.xy(tip.id)[0] == pytest.approx(tip.date, abs=0.01)

    def test_hover_carries_the_date_and_mutation_count(self, timetree_nexus):
        fig = render_tree(timetree_nexus)
        hover = fig.data[1].customdata[0][1]
        assert "date: 20" in hover
        assert "mutations: " in hover

    def test_time_axis_can_be_turned_off(self, timetree_nexus):
        fig = render_tree(timetree_nexus, time_axis=False)
        assert fig.layout.xaxis.title.text == "Branch length"
        assert fig.layout.xaxis.range[0] < 1

    def test_a_cladogram_is_never_put_on_a_time_axis(self, timetree_nexus):
        """Levels are not years, so the numbers would be depth in date's clothing."""
        fig = render_tree(timetree_nexus, cladogram=True)
        assert fig.layout.xaxis.title.text == "Divergence (levels)"

    def test_aligning_tips_disables_the_time_axis(self, timetree_nexus):
        """Flushing tips to one edge destroys exactly what a timetree shows."""
        fig = render_tree(timetree_nexus, align_tips=True)
        assert fig.layout.xaxis.title.text == "Branch length"

    @pytest.mark.parametrize("layout", ALL_LAYOUTS)
    def test_every_layout_renders_a_timetree(self, timetree_nexus, layout):
        fig = render_tree(timetree_nexus, layout=layout)
        assert len(fig.data) >= 2


class TestRenderTimetree:
    def test_it_renders_a_dated_tree(self, timetree_nexus):
        assert render_timetree(timetree_nexus).layout.xaxis.title.text == "Year"

    def test_it_refuses_a_substitution_tree(self, example_newick):
        """A host that read the wrong column finds out here, not from a
        plausible-looking figure whose axis means something else."""
        with pytest.raises(ValueError, match="no node dates"):
            render_timetree(example_newick)

    def test_options_pass_through(self, timetree_nexus):
        fig = render_timetree(timetree_nexus, layout="circ")
        assert len(fig.data) >= 2
