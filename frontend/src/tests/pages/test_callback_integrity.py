"""Resolve every callback reference against the components the pages actually render.

src/app.py:37 sets suppress_callback_exceptions = True, so Dash never complains when a
callback points at a component that does not exist or at a property that component does not
define. This walks the three page layouts and checks those references in-process.

Known violations are listed explicitly rather than marked xfail: KNOWN_UNDECLARED_PROPERTIES
and PAGE_SHARED_IDS are subtracted before asserting, and a second pair of tests asserts each
listed item is still real. A new violation fails the first test; a fixed one fails the
tripwire, which forces the list to be updated instead of quietly drifting.
"""

from pathlib import Path

import pytest
from dash._callback import GLOBAL_CALLBACK_MAP
from dash.development.base_component import Component

REPO_ROOT = Path(__file__).resolve().parents[3]

# (component id, property) pairs a callback writes that the component does not declare.
# Empty since task B1 pointed the chikungunya and zika hosts KPI at "children" instead of
# "value"; an html.H4 has no "value" prop, so those two callbacks never reached their card.
KNOWN_UNDECLARED_PROPERTIES = set()

# bar-chart-title, area-chart-title and div-bar-plot used to be declared identically by all
# three pages. page_ids() now derives every id from the pathogen's suffix, so nothing is
# shared; TestNoIdIsSharedBetweenPages holds the line.


def components_of(layout):
    """Every Component in a layout, root included (_traverse omits the root)."""
    if not isinstance(layout, Component):
        return []
    return [layout] + [node for node in layout._traverse() if isinstance(node, Component)]


def declared_properties(component):
    properties = getattr(component, "_prop_names", None)
    if properties is None:
        # Never treat unknown metadata as agreement; the caller reports these separately
        return None
    return set(properties)


def page_layout(module):
    # dengue builds its layout per request (dengue_page.py:247); the other two freeze it at
    # import (chikungunya_page.py:192, zika_page.py:182)
    layout = module.layout
    return layout() if callable(layout) else layout


@pytest.fixture(scope="module")
def rendered_pages(pathogen_pages):
    return {name: page_layout(module) for name, module in pathogen_pages.items()}


@pytest.fixture(scope="module")
def properties_by_id(rendered_pages):
    """Union of ids across the three pages -> the properties that component declares."""
    declared = {}
    for layout in rendered_pages.values():
        for component in components_of(layout):
            component_id = getattr(component, "id", None)
            if not isinstance(component_id, str):
                continue
            properties = declared_properties(component)
            if properties is None:
                continue
            declared.setdefault(component_id, set()).update(properties)
    return declared


@pytest.fixture(scope="module")
def components_without_metadata(rendered_pages):
    missing = set()
    for layout in rendered_pages.values():
        for component in components_of(layout):
            component_id = getattr(component, "id", None)
            if isinstance(component_id, str) and declared_properties(component) is None:
                missing.add(component_id)
    return missing


def callback_references():
    """Every (id, property) a registered callback reads or writes."""
    references = []
    for key, callback in GLOBAL_CALLBACK_MAP.items():
        for target in key.strip(".").split("..."):
            # allow_duplicate outputs carry an @<hash> suffix
            component_id, _, prop = target.split("@")[0].rpartition(".")
            if component_id:
                references.append((component_id, prop))
        for spec in list(callback.get("inputs") or []) + list(callback.get("state") or []):
            if isinstance(spec.get("id"), str):
                references.append((spec["id"], spec["property"]))
    return references


class TestLayoutIds:
    def test_each_page_declares_every_id_once(self, rendered_pages):
        for name, layout in rendered_pages.items():
            seen = []
            for component in components_of(layout):
                component_id = getattr(component, "id", None)
                if isinstance(component_id, str):
                    seen.append(component_id)
            duplicates = {i for i in seen if seen.count(i) > 1}
            assert not duplicates, f"{name} declares these ids more than once: {sorted(duplicates)}"

    def test_every_rendered_component_exposes_its_property_metadata(
        self, components_without_metadata
    ):
        assert not components_without_metadata, (
            "cannot validate these components; _prop_names is unavailable: "
            f"{sorted(components_without_metadata)}"
        )


class TestCallbackReferences:
    def test_every_referenced_id_is_rendered_by_some_page(self, properties_by_id):
        unresolved = {
            component_id
            for component_id, _ in callback_references()
            if component_id not in properties_by_id
        }
        assert not unresolved, (
            "callbacks reference ids no page renders; suppress_callback_exceptions hides this: "
            f"{sorted(unresolved)}"
        )

    def test_every_referenced_property_is_declared(self, properties_by_id):
        violations = {
            (component_id, prop)
            for component_id, prop in callback_references()
            if component_id in properties_by_id and prop not in properties_by_id[component_id]
        }
        assert not violations - KNOWN_UNDECLARED_PROPERTIES, (
            "callbacks write properties these components do not define: "
            f"{sorted(violations - KNOWN_UNDECLARED_PROPERTIES)}"
        )


class TestKnownViolationsStillExist:
    """Tripwires: when a listed violation is fixed, its entry must be removed from the list."""

    def test_the_hosts_kpi_now_writes_a_declared_property(self, properties_by_id):
        # Regression guard for task B1
        for page_suffix in ("chikv", "zikv", "denv"):
            assert "children" in properties_by_id[f"n-hosts-selected-{page_suffix}"]

    def test_no_page_component_id_is_declared_by_two_pages(self, rendered_pages):
        # header.load and download_btn are shared components mounted on every page, so their
        # ids legitimately repeat; everything a page owns must be namespaced.
        from components import download_btn

        # header.load; the leaflet layers graphs/map.py builds with fixed ids (:87, :102,
        # :121, :299) — all predate this refactoring and are harmless because Dash renders
        # one page at a time
        shared_components = {"n-url-2", "title-header", "source-dropdown",
                             "lc", "info", "geojson_map_icon", "geojson_map_heatmap"}
        for config in download_btn.DOWNLOAD_CONFIG.values():
            shared_components.update({config["btn_id"], config["download_id"]})

        pages_declaring = {}
        for name, layout in rendered_pages.items():
            for component in components_of(layout):
                component_id = getattr(component, "id", None)
                if isinstance(component_id, str):
                    pages_declaring.setdefault(component_id, set()).add(name)

        shared = {i: sorted(pages) for i, pages in pages_declaring.items()
                  if len(pages) > 1 and i not in shared_components}
        assert not shared, shared


class TestAppShell:
    def test_app_registers_a_callback_for_a_component_that_does_not_exist(self):
        """src/app.py:73-81 writes to 'header-container'; nothing declares that id.

        Source inspection rather than import, so this test does not build a second Dash app.
        Follows the approach of src/tests/phylo/test_panel.py:185.
        Deferred, not fixed by this plan — see the deferred-work table.
        """
        app_source = (REPO_ROOT / "src" / "app.py").read_text()
        assert "header-container" in app_source
        marker = "header-container"
        declares_it = [
            path
            for path in (REPO_ROOT / "src").rglob("*.py")
            if "tests" not in path.parts
            and (f'id="{marker}"' in path.read_text() or f"id='{marker}'" in path.read_text())
        ]
        assert not declares_it, (
            f"'header-container' is now rendered by {declares_it}; update this test"
        )
