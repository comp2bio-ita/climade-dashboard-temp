"""The shared layout builder, before any page consumes it.

Nothing imports pages.pathogen_dashboard in production yet (tasks C5-C7 do that), so these
tests are what keep it honest until then.
"""

import pandas as pd
import plotly.graph_objects as go
import pytest
from dash.development.base_component import Component

from pages.pathogen_dashboard import build_layout, chart_titles, page_ids
from pathogens import PATHOGENS, get_pathogen


def view_for(spec):
    """The display state a page hands the builder, with placeholder values."""
    return {
        "last_updated_date": "2026-08-10",
        "n_sequences": 10,
        "n_countries": 3,
        "n_hosts": 2,
        "classifications": list(spec["classification_order"]),
        "subclassifications": ["1I", "2II"] if spec["subclassification_column"] else [],
        "countries": ["Brazil", "Kenya"],
        "continents": ["Africa", "South America"],
        "hosts": ["Homo sapiens", "Aedes aegypti"],
        "regions": [{"label": "Brazil (Country)", "value": "Brazil"}],
        "min_date": pd.Timestamp("2015-06-01"),
        "max_date": pd.Timestamp("2020-05-05"),
        "map_components": [],
        "bar_figure": go.Figure(),
        "area_figure": go.Figure(),
    }


def ids_in(layout):
    found = set()
    for node in [layout] + list(layout._traverse()):
        if isinstance(node, Component) and isinstance(getattr(node, "id", None), str):
            found.add(node.id)
    return found


@pytest.fixture(params=sorted(PATHOGENS))
def spec(request):
    return get_pathogen(request.param)


class TestBuildsForEveryPathogen:
    def test_layout_builds_without_an_app(self, spec):
        assert build_layout(spec, view_for(spec)) is not None

    def test_every_id_carries_the_pathogen_suffix(self, spec):
        layout = build_layout(spec, view_for(spec))
        suffix = spec["id_suffix"]
        # Position varies: the download store must stay "<suffix>-download-store" to match
        # download_btn.DOWNLOAD_CONFIG, and the mobile buttons end in "-mobile"
        owned = set(page_ids(spec).values())
        for component_id in ids_in(layout) & owned:
            assert suffix in component_id, component_id

    def test_ids_are_unique_within_a_page(self, spec):
        layout = build_layout(spec, view_for(spec))
        seen = [node.id for node in [layout] + list(layout._traverse())
                if isinstance(node, Component) and isinstance(getattr(node, "id", None), str)]
        duplicates = {i for i in seen if seen.count(i) > 1}
        assert not duplicates, sorted(duplicates)

    def test_layout_uses_only_declared_ids(self, spec):
        layout = build_layout(spec, view_for(spec))
        declared = set(page_ids(spec).values())
        # header.load and download_btn bring ids this module does not declare
        from components import download_btn

        external = {"n-url-2", "title-header", "source-dropdown"}
        for config in download_btn.DOWNLOAD_CONFIG.values():
            external.update({config["btn_id"], config["download_id"]})
        assert ids_in(layout) - declared - external == set()


class TestTwoPagesNeverCollide:
    def test_no_shared_ids_between_any_two_pathogens(self):
        owned = {key: set(page_ids(spec).values()) for key, spec in PATHOGENS.items()}
        keys = sorted(owned)
        for first in range(len(keys)):
            for second in range(first + 1, len(keys)):
                overlap = owned[keys[first]] & owned[keys[second]]
                assert not overlap, f"{keys[first]}/{keys[second]}: {sorted(overlap)}"


class TestPathogenSpecificVariation:
    def test_only_dengue_renders_a_second_classification_dropdown(self):
        for key, spec in PATHOGENS.items():
            layout = build_layout(spec, view_for(spec))
            has_dropdown = page_ids(spec)["subclassification_select"] in ids_in(layout)
            assert has_dropdown == (key == "denv"), key

    def test_card_headings_follow_the_classification_axis(self):
        assert chart_titles("serotype") == (
            "Circulating Serotypes", "Temporal Spread of Serotypes")
        assert chart_titles("genotype") == (
            "Circulating Genotypes", "Temporal Spread of Genotypes")


class TestInsertionPoints:
    def test_a_page_can_add_its_own_filter_column(self):
        spec = get_pathogen("denv")
        from dash import html

        extra = [html.Div(id="an-extra-filter-block")]
        layout = build_layout(spec, view_for(spec), filter_extras=extra)
        assert "an-extra-filter-block" in ids_in(layout)

    def test_a_page_can_add_its_own_row(self):
        spec = get_pathogen("denv")
        from dash import html

        layout = build_layout(spec, view_for(spec),
                              extra_rows=[html.Div(id="an-extra-row")])
        assert "an-extra-row" in ids_in(layout)

    def test_the_core_renders_nothing_extra_by_default(self):
        spec = get_pathogen("chikv")
        layout = build_layout(spec, view_for(spec))
        assert "an-extra-row" not in ids_in(layout)


def data_for(spec, frame=None):
    """The page state the registrar needs, with a small in-test frame."""
    import numpy as np
    from pages.scripts import pathogen_script as scripts

    view = view_for(spec)

    def vocabulary():
        return {
            "classifications": view["classifications"],
            "subclassifications": view["subclassifications"] or view["classifications"],
            "countries": view["countries"],
            "continents": view["continents"],
            "hosts": view["hosts"],
            "date_from": view["min_date"],
            "date_to": view["max_date"],
        }

    return {
        "frame": frame if frame is not None else pd.DataFrame(),
        "geojson": pd.DataFrame(),
        "vocabulary": vocabulary,
        "scripts": scripts,
    }


@pytest.fixture
def isolated_callbacks():
    """Register into the real Dash registry, then put it back.

    The core uses the module-level @callback, so registrations land in
    GLOBAL_CALLBACK_MAP rather than on any app instance. Snapshotting it keeps each test
    independent and stops these registrations leaking into the page tests.
    """
    from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

    saved_map = dict(GLOBAL_CALLBACK_MAP)
    saved_list = list(GLOBAL_CALLBACK_LIST)
    GLOBAL_CALLBACK_MAP.clear()
    GLOBAL_CALLBACK_LIST.clear()
    try:
        yield GLOBAL_CALLBACK_MAP
    finally:
        GLOBAL_CALLBACK_MAP.clear()
        GLOBAL_CALLBACK_MAP.update(saved_map)
        GLOBAL_CALLBACK_LIST.clear()
        GLOBAL_CALLBACK_LIST.extend(saved_list)


def registered_targets(callback_map):
    return [target for key in callback_map
            for target in key.strip(".").split("...")]


class TestRegistration:
    def test_a_pathogen_registers_its_callbacks(self, isolated_callbacks):
        from pages.pathogen_dashboard import page_ids, register_callbacks

        spec = get_pathogen("chikv")
        register_callbacks(spec, data_for(spec))

        assert isolated_callbacks, "nothing registered"
        targets = registered_targets(isolated_callbacks)
        assert f'{page_ids(spec)["bar_graph"]}.figure' in targets

    def test_callbacks_register_without_duplicate_outputs(self, isolated_callbacks):
        from pages.pathogen_dashboard import register_callbacks

        spec = get_pathogen("chikv")
        register_callbacks(spec, data_for(spec))

        targets = registered_targets(isolated_callbacks)
        assert len(targets) == len(set(targets))

    def test_all_three_pathogens_coexist(self, isolated_callbacks):
        from pages.pathogen_dashboard import register_callbacks

        for key in sorted(PATHOGENS):
            spec = get_pathogen(key)
            register_callbacks(spec, data_for(spec))

        targets = registered_targets(isolated_callbacks)
        assert len(targets) == len(set(targets)), "two pathogens wrote the same output"

    def test_only_a_pathogen_with_a_second_axis_registers_the_cascade(
            self, isolated_callbacks):
        from pages.pathogen_dashboard import page_ids, register_callbacks

        for key in sorted(PATHOGENS):
            spec = get_pathogen(key)
            register_callbacks(spec, data_for(spec))

        targets = registered_targets(isolated_callbacks)
        cascade = {key: f'{page_ids(get_pathogen(key))["subclassification_select"]}.value'
                   in targets for key in sorted(PATHOGENS)}
        assert cascade == {"chikv": False, "denv": True, "yfv": False, "zikv": False}


class TestClassificationCascade:
    def test_dengue_genotypes_follow_the_selected_serotypes(self):
        from pathogens import dengue_genotypes_for_serotypes

        all_genotypes = ["1I", "1II", "2I", "2II", "3III", "4I"]
        assert dengue_genotypes_for_serotypes(["DENV2"], all_genotypes) == ["2I", "2II"]
        assert dengue_genotypes_for_serotypes([], all_genotypes) == []

    def test_a_single_axis_pathogen_declares_no_cascade(self):
        for key in ("chikv", "zikv"):
            assert get_pathogen(key)["subclassification_from_classification"] is None


class TestLegendOrder:
    def test_curated_order_is_applied_and_unselected_values_dropped(self):
        from pages.pathogen_dashboard import legend_order_for

        spec = get_pathogen("denv")
        assert legend_order_for(spec, ["DENV3", "DENV1"]) == ["DENV1", "DENV3"]

    def test_every_pathogen_has_a_curated_order(self):
        from pages.pathogen_dashboard import legend_order_for

        for key, spec in PATHOGENS.items():
            selected = list(spec["classification_order"])
            assert legend_order_for(spec, selected) == selected, key
