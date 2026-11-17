"""The phylogeny job workflow, once it stopped belonging to dengue.

Tasks D3/D4: the workflow moved out of dengue_page into a module any registered pathogen can
mount. These assertions cover what that move has to preserve — namespaced ids, no shared
component between two pages, and a pre-check that reads the right pathogen's data.
"""

import pytest

from pathogens import PATHOGENS, get_pathogen
from utils.phylo.job_workflow import phylo_ids

PAGE_BY_KEY = {"denv": "dengue", "chikv": "chikungunya", "zikv": "zika"}


class TestIdsAreNamespaced:
    @pytest.mark.parametrize("key", sorted(PATHOGENS))
    def test_every_id_carries_the_pathogen_suffix(self, key):
        spec = get_pathogen(key)
        for name, value in phylo_ids(spec).items():
            assert spec["id_suffix"] in value, f"{name}: {value}"

    def test_no_two_pathogens_share_a_workflow_id(self):
        owned = {key: set(phylo_ids(get_pathogen(key)).values()) for key in PATHOGENS}
        keys = sorted(owned)
        for first in range(len(keys)):
            for second in range(first + 1, len(keys)):
                overlap = owned[keys[first]] & owned[keys[second]]
                assert not overlap, f"{keys[first]}/{keys[second]}: {sorted(overlap)}"

    def test_the_inference_method_selector_is_namespaced_too(self):
        # It used to render under the shared id "phylo-method" on whichever page mounted it;
        # with three pages mounting the workflow that became ambiguous
        assert phylo_ids(get_pathogen("denv"))["method"] != \
            phylo_ids(get_pathogen("chikv"))["method"]


class TestEveryPageMountsTheWorkflow:
    @pytest.mark.parametrize("key", sorted(PATHOGENS))
    def test_the_layout_renders_every_workflow_component(self, key, pathogen_pages):
        from dash.development.base_component import Component

        spec = get_pathogen(key)
        layout = pathogen_pages[PAGE_BY_KEY[key]].layout()
        rendered = {node.id for node in [layout] + list(layout._traverse())
                    if isinstance(node, Component) and isinstance(getattr(node, "id", None), str)}
        missing = [value for name, value in phylo_ids(spec).items()
                   if name != "prefix" and value not in rendered]
        assert not missing, missing

    @pytest.mark.parametrize("key", sorted(PATHOGENS))
    def test_the_viewer_panel_is_mounted_under_the_pathogen_prefix(self, key, pathogen_pages):
        from dash.development.base_component import Component

        spec = get_pathogen(key)
        layout = pathogen_pages[PAGE_BY_KEY[key]].layout()
        rendered = {node.id for node in [layout] + list(layout._traverse())
                    if isinstance(node, Component) and isinstance(getattr(node, "id", None), str)}
        assert any(i.startswith(phylo_ids(spec)["prefix"]) for i in rendered)


class TestPrecheckReadsTheRightPathogen:
    @pytest.mark.parametrize("key", sorted(PATHOGENS))
    def test_a_selection_is_measured_against_that_pathogens_own_frame(self, key, pathogen_pages):
        """Regression guard for D4.

        apply_selection_to_sequences defaults to classification_column="serotype"; a
        genotype-classified pathogen has no such column and raised KeyError until the
        workflow started passing the spec's column.
        """
        from utils.functions.selection_functions import selection_to_dict

        page = pathogen_pages[PAGE_BY_KEY[key]]
        spec = get_pathogen(key)
        vocabulary = page.page_data()["vocabulary"]()
        selection = selection_to_dict({
            "source": "basic",
            "date_from": vocabulary["date_from"],
            "date_to": vocabulary["date_to"],
            "classifications": vocabulary["classifications"],
            "subclassifications": vocabulary["subclassifications"],
            "countries": vocabulary["countries"],
            "continents": vocabulary["continents"],
            "hosts": vocabulary["hosts"],
            "search_regions": [],
        })

        precheck, toggle_class = page._phylo["precheck"](selection)
        assert precheck["n_selected"] >= 0
        assert toggle_class

    def test_a_reset_selection_hides_the_toggle_again(self, pathogen_pages):
        from utils.functions.selection_functions import selection_to_dict

        page = pathogen_pages["chikungunya"]
        vocabulary = page.page_data()["vocabulary"]()
        reset = selection_to_dict({
            "source": "reset",
            "date_from": vocabulary["date_from"],
            "date_to": vocabulary["date_to"],
            "classifications": vocabulary["classifications"],
            "subclassifications": vocabulary["subclassifications"],
            "countries": vocabulary["countries"],
            "continents": vocabulary["continents"],
            "hosts": vocabulary["hosts"],
            "search_regions": [],
        })

        precheck, toggle_class = page._phylo["precheck"](reset)
        assert precheck is None
        assert toggle_class == "d-none"


class TestJobSubmissionCarriesThePathogen:
    @pytest.mark.parametrize("key", sorted(PATHOGENS))
    def test_the_queued_row_names_the_pathogen_the_page_declared(self, key, pathogen_pages):
        from utils.functions.selection_functions import selection_to_dict

        page = pathogen_pages[PAGE_BY_KEY[key]]
        spec = get_pathogen(key)
        vocabulary = page.page_data()["vocabulary"]()
        selection = selection_to_dict({
            "source": "basic",
            "date_from": vocabulary["date_from"],
            "date_to": vocabulary["date_to"],
            "classifications": vocabulary["classifications"],
            "subclassifications": vocabulary["subclassifications"],
            "countries": vocabulary["countries"],
            "continents": vocabulary["continents"],
            "hosts": vocabulary["hosts"],
            "search_regions": [],
        })

        page._phylo["submit"](1, selection, "any", "fasttree", "reuse")

        submitted = page.dashDatabase.submitted_phylo_jobs
        assert submitted, "no job was queued"
        assert submitted[-1]["pathogen"] == spec["backend_pathogen_code"]
        assert submitted[-1]["accession_ids"], "the accession set is what the backend builds from"


class TestTheViewerIsActuallyDriven:
    """The card can render completely and still show no tree.

    Every component existed and every id resolved, but register_phylogeny_callbacks was
    never called, so nothing wrote a figure into the graph. Component-level checks all
    passed; only asking whether the callback exists catches it.
    """

    @pytest.mark.parametrize("key", sorted(PATHOGENS))
    def test_a_callback_writes_the_figure(self, key, pathogen_pages):
        from dash._callback import GLOBAL_CALLBACK_MAP
        from utils.phylo.panel import panel_ids

        pathogen_pages[PAGE_BY_KEY[key]]          # ensure the page registered its callbacks
        graph_id = panel_ids(phylo_ids(get_pathogen(key))["prefix"])["graph"]
        assert any(graph_id in registered for registered in GLOBAL_CALLBACK_MAP), (
            f"nothing drives {graph_id}; the card would render empty"
        )

    @pytest.mark.parametrize("key", sorted(PATHOGENS))
    def test_the_figure_callback_reads_that_pathogens_result_store(self, key, pathogen_pages):
        from dash._callback import GLOBAL_CALLBACK_MAP
        from utils.phylo.panel import panel_ids

        pathogen_pages[PAGE_BY_KEY[key]]
        ids = phylo_ids(get_pathogen(key))
        graph_id = panel_ids(ids["prefix"])["graph"]
        registered = next(k for k in GLOBAL_CALLBACK_MAP if graph_id in k)
        sources = [spec["id"] for spec in GLOBAL_CALLBACK_MAP[registered]["inputs"]]
        assert ids["result_store"] in sources

    @pytest.mark.parametrize("key", sorted(PATHOGENS))
    def test_the_poll_callback_fills_that_same_store(self, key, pathogen_pages):
        from dash._callback import GLOBAL_CALLBACK_MAP

        pathogen_pages[PAGE_BY_KEY[key]]
        ids = phylo_ids(get_pathogen(key))
        writers = [k for k in GLOBAL_CALLBACK_MAP if ids["result_store"] in k]
        assert writers, f"nothing writes {ids['result_store']}"
