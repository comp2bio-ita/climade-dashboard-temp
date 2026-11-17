"""The registry must agree with the pages it was transcribed from.

Nothing consumes src/pathogens.py yet, so this is the only thing keeping it honest until
the shared page core is wired up. Each assertion compares a registry value against the live
page module, so a page edited without the registry fails here.
"""

import pytest

from components import download_btn
from pathogens import PATHOGENS, get_pathogen, pathogen_keys

PAGE_BY_KEY = {"denv": "dengue", "chikv": "chikungunya", "zikv": "zika"}


@pytest.fixture
def page_for(pathogen_pages):
    return lambda key: pathogen_pages[PAGE_BY_KEY[key]]


class TestRegistryShape:
    def test_every_pathogen_declares_the_same_fields(self):
        fields = [set(spec) for spec in PATHOGENS.values()]
        assert all(f == fields[0] for f in fields)

    def test_keys_match_the_download_registry(self):
        # header.load maps a title to these keys before calling download_btn.load
        assert set(pathogen_keys()) == set(download_btn.DOWNLOAD_CONFIG)

    def test_an_unregistered_pathogen_raises_a_clear_error(self):
        with pytest.raises(KeyError, match="no pathogen registered"):
            get_pathogen("yellow-fever")


class TestAgreesWithThePages:
    @pytest.mark.parametrize("key", ["denv", "chikv", "zikv"])
    def test_dataset_path_matches_the_download_registry(self, key):
        assert (get_pathogen(key)["dataset_path"]
                == download_btn.DOWNLOAD_CONFIG[key]["full_dataset_path"])

    @pytest.mark.parametrize("key", ["denv", "chikv", "zikv"])
    def test_route_matches_the_registered_page(self, key, page_for):
        import dash

        routes = {page["path"] for page in dash.page_registry.values()}
        assert get_pathogen(key)["route"] in routes

    @pytest.mark.parametrize("key", ["denv", "chikv", "zikv"])
    def test_id_suffix_matches_the_pages_own_button_ids(self, key, page_for):
        suffix = get_pathogen(key)["id_suffix"]
        assert page_for(key).BASIC_APPLY_ID == f"filter-button-{suffix}"
        assert page_for(key).RESET_IDS[0] == f"reset-filters-button-{suffix}"

    @pytest.mark.parametrize("key", ["denv", "chikv", "zikv"])
    def test_classification_column_is_the_one_the_page_filters_on(self, key, page_for):
        spec = get_pathogen(key)
        frame = getattr(page_for(key), f"df_world_{PAGE_BY_KEY[key]}")
        assert spec["classification_column"] in frame.columns
        if spec["subclassification_column"] is not None:
            assert spec["subclassification_column"] in frame.columns

    @pytest.mark.parametrize("key", ["denv", "chikv", "zikv"])
    def test_download_columns_match_what_the_page_exports(self, key, page_for):
        # The page writes its dataset TSV with the same column list at import time
        frame = getattr(page_for(key), f"df_world_{PAGE_BY_KEY[key]}")
        for column in get_pathogen(key)["download_columns"]:
            assert column in frame.columns, column

    @pytest.mark.parametrize("key", ["denv", "chikv", "zikv"])
    def test_colour_scheme_covers_the_declared_classification_order(self, key):
        spec = get_pathogen(key)
        for value in spec["classification_order"]:
            assert value in spec["color_scheme"], value

    @pytest.mark.parametrize("key", ["denv", "chikv", "zikv"])
    def test_phylo_fields_exist_on_the_metadata_entity(self, key):
        spec = get_pathogen(key)
        columns = {c.name for c in spec["meta_entity"].__table__.columns}
        for field in spec["phylo_metadata_fields"]:
            assert field in columns, f"{key}: {field}"


class TestPathogenSpecificVariation:
    def test_only_dengue_has_a_second_classification_axis(self):
        with_sub = [k for k, s in PATHOGENS.items()
                    if s["subclassification_column"] is not None]
        assert with_sub == ["denv"]

    def test_only_dengue_exposes_lineages_for_colouring(self):
        with_lineage = [k for k, s in PATHOGENS.items()
                        if any("lineage" in f for f in s["phylo_metadata_fields"])]
        assert with_lineage == ["denv"]
