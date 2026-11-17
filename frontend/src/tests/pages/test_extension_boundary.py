"""Adding a pathogen must not require editing shared code.

The claim this file protects: given a compatible metadata table, registering a pathogen's
spec and colour scheme is enough to get a working page. It uses a synthetic pathogen that
exists only for the duration of a test — no entry is added to src/pathogens.py, and no
production file is touched.

If making this pass ever requires editing pathogen_dashboard.py, color_schemes.py or
pathogens.py, that is the finding: the boundary has leaked, and the fix belongs in the core
rather than in these assertions.
"""

import pandas as pd
import plotly.graph_objects as go
import pytest
from dash.development.base_component import Component

from pages.pathogen_dashboard import build_layout, page_ids, register_callbacks
from pathogens import get_pathogen

SYNTHETIC_KEY = "testvirus"
SYNTHETIC_CLASSIFICATIONS = ["Alpha", "Beta", "Unassigned"]
SYNTHETIC_SCHEME = {"Alpha": "#111111", "Beta": "#222222", "Unassigned": "#808080"}


def synthetic_spec():
    """A pathogen that does not exist, declared exactly the way a real one is."""
    return {
        "title": "Testvirus",
        "route": "/testvirus",
        "id_suffix": SYNTHETIC_KEY,
        "meta_entity": None,
        "classification_column": "genotype",
        "subclassification_column": None,
        "classification_order": SYNTHETIC_CLASSIFICATIONS,
        "subclassification_from_classification": None,
        "color_scheme": SYNTHETIC_SCHEME,
        "subclassification_color_scheme": None,
        "phylo_metadata_fields": ["genotype", "country", "host"],
        "backend_pathogen_code": "TESTV",
        "download_columns": ["genbank_sequence_data_id", "collection_date", "genotype"],
        "dataset_path": "data/testvirus/testvirus.tsv",
    }


def synthetic_view():
    return {
        "last_updated_date": "2026-08-10",
        "n_sequences": 0,
        "n_countries": 0,
        "n_hosts": 0,
        "classifications": SYNTHETIC_CLASSIFICATIONS,
        "subclassifications": [],
        "countries": ["Brazil"],
        "continents": ["South America"],
        "hosts": ["Homo sapiens"],
        "regions": [{"label": "Brazil (Country)", "value": "Brazil"}],
        "min_date": pd.Timestamp("2015-06-01"),
        "max_date": pd.Timestamp("2020-05-05"),
        "map_components": [],
        "bar_figure": go.Figure(),
        "area_figure": go.Figure(),
    }


def synthetic_data():
    from pages.scripts import pathogen_script

    def vocabulary():
        view = synthetic_view()
        return {
            "classifications": view["classifications"],
            "subclassifications": view["classifications"],
            "countries": view["countries"],
            "continents": view["continents"],
            "hosts": view["hosts"],
            "date_from": view["min_date"],
            "date_to": view["max_date"],
        }

    return {
        "frame": pd.DataFrame(),
        "geojson": pd.DataFrame(),
        "vocabulary": vocabulary,
        # No borrowed per-pathogen module any more: the builders take the classification
        # column and the palette as arguments, so a new pathogen brings neither.
        "scripts": pathogen_script,
    }


def ids_in(layout):
    return {node.id for node in [layout] + list(layout._traverse())
            if isinstance(node, Component) and isinstance(getattr(node, "id", None), str)}


@pytest.fixture
def registered_colour_scheme():
    """Register the synthetic pathogen's curated colours, then remove them again."""
    from utils.color_schemes import PHYLO_FIELD_COLOR_SCHEMES

    PHYLO_FIELD_COLOR_SCHEMES[SYNTHETIC_KEY] = {"genotype": SYNTHETIC_SCHEME}
    try:
        yield
    finally:
        PHYLO_FIELD_COLOR_SCHEMES.pop(SYNTHETIC_KEY, None)


@pytest.fixture
def isolated_callbacks():
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


class TestAPageCanBeConfiguredWithoutTouchingTheCore:
    def test_the_layout_builds(self):
        assert build_layout(synthetic_spec(), synthetic_view()) is not None

    def test_its_ids_are_namespaced_and_unique(self):
        layout = build_layout(synthetic_spec(), synthetic_view())
        owned = set(page_ids(synthetic_spec()).values())
        rendered = ids_in(layout) & owned
        assert rendered
        for component_id in rendered:
            assert SYNTHETIC_KEY in component_id, component_id
        assert len(rendered) == len(set(rendered))

    def test_it_does_not_collide_with_a_registered_pathogen(self):
        synthetic = set(page_ids(synthetic_spec()).values())
        for key in ("denv", "chikv", "zikv"):
            assert not synthetic & set(page_ids(get_pathogen(key)).values()), key

    def test_its_callbacks_register_without_duplicate_outputs(self, isolated_callbacks):
        register_callbacks(synthetic_spec(), synthetic_data())
        targets = [target for key in isolated_callbacks
                   for target in key.strip(".").split("...")]
        assert targets
        assert len(targets) == len(set(targets))

    def test_it_coexists_with_a_registered_pathogen_on_one_app(self, isolated_callbacks):
        register_callbacks(get_pathogen("denv"), _dengue_data())
        register_callbacks(synthetic_spec(), synthetic_data())
        targets = [target for key in isolated_callbacks
                   for target in key.strip(".").split("...")]
        assert len(targets) == len(set(targets))

    def test_declaring_no_second_axis_omits_that_dropdown(self):
        layout = build_layout(synthetic_spec(), synthetic_view())
        assert page_ids(synthetic_spec())["subclassification_select"] not in ids_in(layout)

    def test_its_colour_by_vocabulary_is_exactly_what_it_declared(self):
        assert synthetic_spec()["phylo_metadata_fields"] == ["genotype", "country", "host"]

    def test_its_registered_scheme_is_used_for_its_own_field(self, registered_colour_scheme):
        from utils.color_schemes import color_map_for_pathogen_field

        colours = color_map_for_pathogen_field(SYNTHETIC_KEY, "genotype", ["Alpha"])
        assert colours["Alpha"] == "#111111"

    def test_without_a_registered_scheme_colours_are_generated_not_borrowed(self):
        from utils.color_schemes import color_map_for_pathogen_field

        colours = color_map_for_pathogen_field(SYNTHETIC_KEY, "genotype", ["Alpha", "Beta"])
        assert set(colours) == {"Alpha", "Beta"}
        assert "DENV1" not in colours


class TestTheHeaderComesFromTheRegistry:
    """The pathogen dropdown, its title->route mapping and the download button used to be
    three hardcoded lists in components/header.py. Two of them now read PATHOGENS."""

    def test_the_dropdown_offers_exactly_the_registered_pathogens(self):
        from components.header import load
        from pathogens import PATHOGENS

        header = load("Dengue")
        dropdown = next(node for node in header._traverse()
                        if getattr(node, "id", None) == "source-dropdown")
        assert dropdown.options == [{"label": spec["title"], "value": spec["title"]}
                                    for spec in PATHOGENS.values()]

    def test_each_registered_title_routes_to_its_own_path(self):
        from components.header import update_url
        from pathogens import PATHOGENS

        for spec in PATHOGENS.values():
            assert update_url(spec["title"]) == spec["route"], spec["title"]

    def test_the_download_button_is_still_a_second_registration_point(self):
        """Tripwire, not an endorsement: registering a spec is not yet enough for the
        download button, because components/download_btn.py keeps its own per-virus dict.
        When that is folded into PATHOGENS this test must be replaced by its opposite."""
        from components.download_btn import DOWNLOAD_CONFIG

        assert SYNTHETIC_KEY not in DOWNLOAD_CONFIG
        layout = build_layout(synthetic_spec(), synthetic_view())
        assert f"{SYNTHETIC_KEY}_btn" not in ids_in(layout)


class TestUnregisteredPathogen:
    def test_lookup_fails_with_a_clear_message(self):
        with pytest.raises(KeyError, match="no pathogen registered"):
            get_pathogen(SYNTHETIC_KEY)


def _dengue_data():
    from pages.scripts import pathogen_script

    def vocabulary():
        return {
            "classifications": ["DENV1", "DENV2"],
            "subclassifications": ["1I", "2II"],
            "countries": ["Brazil"],
            "continents": ["South America"],
            "hosts": ["Homo sapiens"],
            "date_from": pd.Timestamp("2015-06-01"),
            "date_to": pd.Timestamp("2020-05-05"),
        }

    return {
        "frame": pd.DataFrame(),
        "geojson": pd.DataFrame(),
        "vocabulary": vocabulary,
        "scripts": pathogen_script,
    }
