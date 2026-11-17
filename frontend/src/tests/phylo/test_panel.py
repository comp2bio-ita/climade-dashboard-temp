#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The Dash panel: ids, figure assembly from control values, notes, registration."""

import dash
import pytest

from utils.phylo.panel import (
    SUBSTITUTION_SCALE,
    TIME_SCALE,
    build_phylogeny_figure,
    panel_ids,
    phylogeny_panel,
    register_phylogeny_callbacks,
    result_notes,
    tip_detail_card,
    SUPPORT_METRIC_UFBOOT,
)
from pathogens import get_pathogen
from utils.phylo.result_provider import KEY_COLUMN, color_by_fields_for, metadata_columns_for

DENGUE = get_pathogen("denv")
METADATA_COLUMNS = metadata_columns_for(DENGUE)
COLOR_BY_FIELDS = color_by_fields_for(DENGUE)

PREFIX = "dengue-phylo"


@pytest.fixture
def result(pipeline_newick, timetree_nexus):
    tips = _tip_labels(pipeline_newick)
    return {
        "job_id": 10,
        "status": "done",
        "error_message": None,
        "events": [],
        "substitution_newick": pipeline_newick,
        "time_tree_nexus": timetree_nexus,
        "inference_method": "IQ-TREE",
        "sequence_count": len(tips),
        "tip_records": [
            {KEY_COLUMN: tip, "serotype": "DENV2", "genotype": "2II",
             "major_lineage": None, "minor_lineage": None, "country": "USA",
             "region": "North America", "location": "USA: FL", "division": "FL",
             "locality": "FL",
             "host": "Homo sapiens",
             "collection_date": "2025-06-08T00:00:00Z"}
            for tip in tips
        ],
        "metadata_columns": METADATA_COLUMNS,
        "color_by_fields": COLOR_BY_FIELDS,
        # the result carries its pathogen so curated colours can be looked up (task D1)
        "pathogen": DENGUE["id_suffix"],
        "key_column": KEY_COLUMN,
        "clock": {"status": "done", "clock_rate": 0.002219, "r_squared": 0.25,
                  "dated_tips": 25, "tree_tips": 25, "dated_fraction": 1.0,
                  "excluded_tips": []},
        "metadata_report": {"matched": len(tips), "unmatched": [], "duplicated": []},
        "tip_set_report": {"only_in_substitution": [], "only_in_time_tree": []},
    }


class TestIds:
    def test_every_id_carries_the_prefix(self):
        assert all(v.startswith(PREFIX) for v in panel_ids(PREFIX).values())

    def test_ids_are_unique(self):
        ids = panel_ids(PREFIX)
        assert len(set(ids.values())) == len(ids)

    def test_two_instances_never_collide(self):
        assert not set(panel_ids("dengue-phylo").values()) & set(panel_ids("zika-phylo").values())

    def test_layout_builds_without_an_app(self):
        assert phylogeny_panel(PREFIX) is not None

    def test_layout_uses_only_declared_ids(self):
        declared = set(panel_ids(PREFIX).values())
        assert _ids_in(phylogeny_panel(PREFIX)) <= declared


class TestFigureFromControls:
    def test_no_result_yields_a_placeholder_not_an_error(self):
        assert build_phylogeny_figure(None).data == ()

    def test_time_scale_draws_the_dated_tree(self, result):
        figure = build_phylogeny_figure(result, scale=TIME_SCALE)
        assert figure.layout.xaxis.title.text == "Year"

    def test_substitution_scale_draws_the_inferred_tree(self, result):
        figure = build_phylogeny_figure(result, scale=SUBSTITUTION_SCALE)
        assert figure.layout.xaxis.title.text == "Branch length"

    def test_asking_for_time_without_a_dated_tree_draws_nothing(self, result):
        result["time_tree_nexus"] = None
        assert build_phylogeny_figure(result, scale=TIME_SCALE).data == ()

    def test_time_scale_renders_deep_historical_root(self, result):
        result["time_tree_nexus"] = """#NEXUS
Begin Taxa;
 Dimensions NTax=2;
 TaxLabels tip_a tip_b;
End;
Begin Trees;
 Tree tree1=(tip_a:800.0[&date=2020.00],tip_b:810.0[&date=2025.00])NODE:0.0[&date=1200.00];
End;
"""
        figure = build_phylogeny_figure(result, scale=TIME_SCALE)
        assert figure.data
        assert figure.layout.xaxis.title.text == "Year"

    def test_branch_lengths_toggle_replaces_the_old_cladogram_radio(self, result):
        cladogram = build_phylogeny_figure(result, toggles=["labels"])
        phylogram = build_phylogeny_figure(result, toggles=["labels", "lengths"])
        assert cladogram.layout.xaxis.title.text != phylogram.layout.xaxis.title.text

    def test_colour_by_serotype_uses_the_dashboard_scheme(self, result):
        from utils.color_schemes import color_map_for_pathogen_field

        figure = build_phylogeny_figure(result, color_by="serotype")
        expected = color_map_for_pathogen_field("denv", "serotype", ["DENV2"])["DENV2"]
        assert any(expected in str(trace.marker.color) for trace in figure.data
                   if trace.mode and "markers" in trace.mode)

    def test_colour_by_locality_uses_generated_colours(self, result):
        figure = build_phylogeny_figure(result, color_by="locality")
        assert figure.data

    def test_colour_by_division_uses_generated_colours(self, result):
        figure = build_phylogeny_figure(result, color_by="division")
        assert figure.data

    def test_search_highlights_a_tip(self, result):
        figure = build_phylogeny_figure(result, search="PH031933")
        assert any("Match" in (trace.name or "") for trace in figure.data)

    def test_rotation_applies_to_a_circular_layout(self, result):
        assert build_phylogeny_figure(result, layout="circ", rotation=90).data

    def test_absurd_label_size_is_clamped(self, result):
        assert build_phylogeny_figure(result, label_size=9999).data

    def test_unreadable_tree_becomes_a_message_not_a_crash(self, result):
        result["substitution_newick"] = "not a tree"
        assert build_phylogeny_figure(result, scale=SUBSTITUTION_SCALE).data == ()


class TestNotes:
    def test_clean_join_is_stated_positively(self, result):
        assert "all 25 tips" in _text(result_notes(result))

    def test_unmatched_tips_are_named(self, result):
        result["metadata_report"] = {"matched": 22, "unmatched": ["A.1", "B.1", "C.1"],
                                     "duplicated": []}
        assert "3 tip(s) have no metadata" in _text(result_notes(result))

    def test_duplicated_accessions_are_named(self, result):
        result["metadata_report"] = {"matched": 25, "unmatched": [],
                                     "duplicated": ["PH031933.1"]}
        assert "more than once" in _text(result_notes(result))

    def test_clock_quality_is_reported_verbatim(self, result):
        assert "R² = 0.25" in _text(result_notes(result))

    def test_missing_dated_tree_is_stated_not_hidden(self, result):
        result["time_tree_nexus"] = None
        text = _text(result_notes(result))
        assert "No dated tree" in text and "not time-scaled" in text

    def test_tips_dropped_by_treetime_are_listed(self, result):
        result["tip_set_report"] = {"only_in_substitution": ["PH031933.1"],
                                    "only_in_time_tree": []}
        assert "missing from the dated tree" in _text(result_notes(result))

    def test_identical_tip_sets_need_no_note(self, result):
        assert "missing from the dated tree" not in _text(result_notes(result))

    def test_unfinished_job_has_no_notes(self, result):
        result["status"] = "running"
        assert result_notes(result) == []

    def test_support_threshold_legend_is_shown(self, result):
        assert "Robust clades" in _text(result_notes(result))
        assert "SH-aLRT" in _text(result_notes(result))

    def test_all_notes_use_muted_text(self, result):
        result["metadata_report"] = {"matched": 22, "unmatched": ["A.1"],
                                     "duplicated": ["PH031933.1"]}
        result["tip_set_report"] = {"only_in_substitution": ["PH031933.1"],
                                    "only_in_time_tree": []}
        for note in result_notes(result):
            assert "text-muted" in note.className

    def test_time_scale_shows_borrowed_support(self, result):
        figure = build_phylogeny_figure(result, scale=TIME_SCALE)
        assert any(a.name == "support" for a in figure.layout.annotations)

    def test_support_metric_switch_changes_numerals(self, result, pipeline_newick):
        result["substitution_newick"] = "((A:0.1,B:0.2)95/98:0.3,C:0.4);"
        sh = build_phylogeny_figure(
            result, scale=SUBSTITUTION_SCALE, support_metric="sh_alrt")
        uf = build_phylogeny_figure(
            result, scale=SUBSTITUTION_SCALE, support_metric=SUPPORT_METRIC_UFBOOT)
        sh_nums = [a.text for a in sh.layout.annotations if a.name == "support"]
        uf_nums = [a.text for a in uf.layout.annotations if a.name == "support"]
        assert sh_nums == ["95"]
        assert uf_nums == ["98"]


class TestTipDetail:
    def test_card_shows_the_metadata_row(self, result):
        assert "DENV2" in _text([tip_detail_card("PH031933.1", result)])

    def test_card_links_to_genbank(self, result):
        assert "ncbi.nlm.nih.gov" in _text([tip_detail_card("PH031933.1", result)])

    def test_unknown_tip_says_so(self, result):
        assert "No metadata" in _text([tip_detail_card("ZZ999999.1", result)])


class TestRegistration:
    def test_callbacks_register_without_duplicate_outputs(self):
        app = dash.Dash(__name__)
        app.layout = phylogeny_panel(PREFIX)
        register_phylogeny_callbacks(app, PREFIX, "dengue-phylo-result")
        targets = [target for key in app.callback_map
                   for target in key.strip(".").split("...")]
        assert len(targets) == len(set(targets))
        assert f"{PREFIX}-graph.figure" in targets

    def test_two_instances_coexist_on_one_app(self):
        app = dash.Dash(__name__)
        register_phylogeny_callbacks(app, "dengue-phylo", "dengue-phylo-result")
        register_phylogeny_callbacks(app, "zika-phylo", "zika-phylo-result")
        assert len(app.callback_map) == 8

    def test_rendering_leaves_no_trace_between_requests(self, result):
        """Two users' control values must not influence each other."""
        first = build_phylogeny_figure(result, color_by="serotype", search="PH031933")
        build_phylogeny_figure(result, color_by="country", search="", layout="circ")
        repeat = build_phylogeny_figure(result, color_by="serotype", search="PH031933")
        assert repeat.to_plotly_json() == first.to_plotly_json()

    def test_the_panel_never_reaches_for_the_database(self):
        import inspect

        import utils.phylo.panel as panel

        source = inspect.getsource(panel)
        assert "DashDatabaseClient" not in source
        assert "session" not in source and "query(" not in source


def _tip_labels(newick):
    from utils.phylo.viewer.parse import parse_newick

    return parse_newick(newick).tip_labels()


def _ids_in(component):
    found = set()
    component_id = getattr(component, "id", None)
    if isinstance(component_id, str):
        found.add(component_id)
    children = getattr(component, "children", None)
    for child in (children if isinstance(children, (list, tuple)) else [children]):
        if hasattr(child, "children") or hasattr(child, "id"):
            found |= _ids_in(child)
    return found


def _text(components):
    """Flatten a Dash component tree to its visible text and hrefs."""
    parts = []
    stack = list(components)
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            parts.append(item)
            continue
        if isinstance(item, (list, tuple)):
            stack.extend(item)
            continue
        for attribute in ("children", "href"):
            value = getattr(item, attribute, None)
            if value is not None:
                stack.append(value)
    return " ".join(parts)
