import unittest

import pandas as pd

from utils.functions.date_functions import date_to_slider_value
from utils.functions.selection_functions import (
    ADVANCED_FILTER,
    BASIC_FILTER,
    RESET_FILTER,
    classify_filter_source,
    order_unassigned_last,
    resolve_date_window,
    resolve_filter_selection,
    resolve_slider_window,
    selected_or_all,
    selection_from_dict,
    selection_to_dict,
)


# A miniature dengue vocabulary. Kept local so the tests do not need a database.
ALL_SEROTYPES = ["DENV1", "DENV2", "DENV3", "DENV4", "Unassigned"]
ALL_GENOTYPES = ["1I", "1II", "2I", "Unassigned"]
ALL_COUNTRIES = ["Brazil", "Kenya", "Thailand"]
ALL_CONTINENTS = ["Africa", "Asia", "South America"]
ALL_HOSTS = ["Homo sapiens", "Aedes aegypti"]
MIN_DATE = pd.Timestamp("1944-01-01")
MAX_DATE = pd.Timestamp("2026-03-20")

VOCABULARY = {
    "classifications": ALL_SEROTYPES,
    "subclassifications": ALL_GENOTYPES,
    "countries": ALL_COUNTRIES,
    "continents": ALL_CONTINENTS,
    "hosts": ALL_HOSTS,
    "date_from": MIN_DATE,
    "date_to": MAX_DATE,
}

BASIC_APPLY = "filter-button-dengue"
ADVANCED_APPLY = "apply-filters-modal-btn-dengue"
RESET_BUTTONS = ("reset-filters-button-dengue", "reset-filters-button-dengue-mobile")


def resolve(source, basic=None, advanced=None):
    return resolve_filter_selection(source, basic or {}, advanced or {}, VOCABULARY)


class SelectedOrAllTest(unittest.TestCase):

    def test_cleared_dropdown_means_no_restriction(self):
        # Dash sends None when the user clears a multi-dropdown entirely and [] when the last
        # chip is removed. Both mean "every serotype", not "no serotype".
        self.assertEqual(selected_or_all(None, ALL_SEROTYPES), ALL_SEROTYPES)
        self.assertEqual(selected_or_all([], ALL_SEROTYPES), ALL_SEROTYPES)

    def test_returns_a_copy_of_the_vocabulary(self):
        # The caller holds the page's module-level option list; mutating it would reorder the
        # dropdown for every later request.
        resolved = selected_or_all(None, ALL_SEROTYPES)
        resolved.append("DENV5")
        self.assertEqual(ALL_SEROTYPES, ["DENV1", "DENV2", "DENV3", "DENV4", "Unassigned"])

    def test_explicit_selection_is_kept(self):
        self.assertEqual(selected_or_all(["DENV2"], ALL_SEROTYPES), ["DENV2"])


class OrderUnassignedLastTest(unittest.TestCase):

    def test_unassigned_moves_to_the_end(self):
        self.assertEqual(
            order_unassigned_last(["Unassigned", "DENV1", "DENV2"]),
            ["DENV1", "DENV2", "Unassigned"],
        )

    def test_input_list_is_not_mutated(self):
        serotypes = ["Unassigned", "DENV1"]
        order_unassigned_last(serotypes)
        self.assertEqual(serotypes, ["Unassigned", "DENV1"])

    def test_absent_unassigned_is_not_added(self):
        self.assertEqual(order_unassigned_last(["DENV1", "DENV2"]), ["DENV1", "DENV2"])


class DateWindowTest(unittest.TestCase):

    def test_inverted_dates_are_swapped(self):
        start, end = resolve_date_window("2020-01-01", "2010-01-01", MIN_DATE, MAX_DATE)
        self.assertEqual(start, pd.Timestamp("2010-01-01"))
        self.assertEqual(end, pd.Timestamp("2020-01-01"))

    def test_unparsable_dates_fall_back_to_the_dataset_bounds(self):
        start, end = resolve_date_window("not-a-date", "2010-01-01", MIN_DATE, MAX_DATE)
        self.assertEqual((start, end), (MIN_DATE, MAX_DATE))

    def test_missing_dates_fall_back_to_the_dataset_bounds(self):
        self.assertEqual(resolve_date_window(None, None, MIN_DATE, MAX_DATE), (MIN_DATE, MAX_DATE))

    def test_slider_range_round_trips_through_days_since_epoch(self):
        low = date_to_slider_value(pd.Timestamp("2015-01-01"))
        high = date_to_slider_value(pd.Timestamp("2016-12-31"))
        start, end = resolve_slider_window([low, high], MIN_DATE, MAX_DATE)
        self.assertEqual(start, pd.Timestamp("2015-01-01"))
        self.assertEqual(end, pd.Timestamp("2016-12-31"))

    def test_malformed_slider_falls_back_to_the_dataset_bounds(self):
        self.assertEqual(resolve_slider_window([5], MIN_DATE, MAX_DATE), (MIN_DATE, MAX_DATE))
        self.assertEqual(resolve_slider_window(None, MIN_DATE, MAX_DATE), (MIN_DATE, MAX_DATE))


class ClassifyFilterSourceTest(unittest.TestCase):

    def classify(self, triggered_by):
        return classify_filter_source(triggered_by, BASIC_APPLY, ADVANCED_APPLY, RESET_BUTTONS)

    def test_each_button_maps_to_its_filter(self):
        self.assertEqual(self.classify(BASIC_APPLY), BASIC_FILTER)
        self.assertEqual(self.classify(ADVANCED_APPLY), ADVANCED_FILTER)
        self.assertEqual(self.classify("reset-filters-button-dengue"), RESET_FILTER)
        self.assertEqual(self.classify("reset-filters-button-dengue-mobile"), RESET_FILTER)

    def test_unknown_trigger_falls_back_to_the_whole_dataset(self):
        self.assertEqual(self.classify(None), RESET_FILTER)
        self.assertEqual(self.classify("some-button-added-later"), RESET_FILTER)


class ResolveFilterSelectionTest(unittest.TestCase):

    def test_the_two_filters_agree_on_the_same_intent(self):
        # DENV2 over the whole period, expressed through each filter. The dashboard promises the
        # two are interchangeable, so every axis of the resolved selection must match.
        basic = resolve(BASIC_FILTER, basic={
            "classifications": ["DENV2"], "search_regions": [],
            "date_from": str(MIN_DATE.date()), "date_to": str(MAX_DATE.date()),
        })
        advanced = resolve(ADVANCED_FILTER, advanced={
            "classifications": ["DENV2"],
            "date_slider": [date_to_slider_value(MIN_DATE), date_to_slider_value(MAX_DATE)],
        })
        for axis in ("classifications", "subclassifications", "countries", "continents",
                     "hosts", "date_from", "date_to"):
            self.assertEqual(basic[axis], advanced[axis], axis)

    def test_cleared_basic_classification_does_not_raise(self):
        # The regression: a fully cleared basic serotype dropdown used to reach len(None).
        selection = resolve(BASIC_FILTER, basic={"classifications": None})
        self.assertEqual(selection["classifications"], ALL_SEROTYPES)

    def test_cleared_advanced_dropdowns_do_not_raise(self):
        selection = resolve(ADVANCED_FILTER, advanced={
            "classifications": None, "subclassifications": None, "countries": None,
            "continents": None, "hosts": None, "date_slider": None,
        })
        self.assertEqual(selection["classifications"], ALL_SEROTYPES)
        self.assertEqual(selection["hosts"], ALL_HOSTS)
        self.assertEqual(selection["date_from"], MIN_DATE)

    def test_basic_filter_leaves_genotype_and_host_open(self):
        # The basic card has no genotype or host control, so neither may narrow the selection.
        selection = resolve(BASIC_FILTER, basic={"classifications": ["DENV1"]})
        self.assertEqual(selection["subclassifications"], ALL_GENOTYPES)
        self.assertEqual(selection["hosts"], ALL_HOSTS)

    def test_region_search_narrows_one_axis_and_leaves_the_other_open(self):
        # Picking a country must not also narrow the continents, or the two would cancel out.
        selection = resolve(BASIC_FILTER, basic={"search_regions": ["Brazil"]})
        self.assertEqual(selection["countries"], ["Brazil"])
        self.assertEqual(selection["continents"], ALL_CONTINENTS)

    def test_advanced_filter_echoes_country_subset_to_search_regions(self):
        selection = resolve(ADVANCED_FILTER, advanced={"countries": ["Brazil"]})
        self.assertEqual(selection["search_regions"], ["Brazil"])

    def test_advanced_filter_echoes_continent_subset_to_search_regions(self):
        selection = resolve(ADVANCED_FILTER, advanced={"continents": ["Africa"]})
        self.assertEqual(selection["search_regions"], ["Africa"])

    def test_advanced_filter_leaves_search_regions_empty_when_geo_unrestricted(self):
        selection = resolve(ADVANCED_FILTER, advanced={
            "classifications": None, "subclassifications": None, "countries": None,
            "continents": None, "hosts": None, "date_slider": None,
        })
        self.assertEqual(selection["search_regions"], [])

    def test_basic_and_advanced_geo_intent_matches_search_regions(self):
        basic = resolve(BASIC_FILTER, basic={"search_regions": ["Brazil"]})
        advanced = resolve(ADVANCED_FILTER, advanced={"countries": ["Brazil"]})
        for axis in ("countries", "continents", "search_regions"):
            self.assertEqual(basic[axis], advanced[axis], axis)

    def test_reset_returns_the_whole_dataset(self):
        selection = resolve(RESET_FILTER, basic={"classifications": ["DENV1"]})
        self.assertEqual(selection["classifications"], ALL_SEROTYPES)
        self.assertEqual(selection["countries"], ALL_COUNTRIES)
        self.assertEqual(selection["date_from"], MIN_DATE)
        self.assertEqual(selection["date_to"], MAX_DATE)
        self.assertEqual(selection["search_regions"], [])

    def test_unassigned_is_ordered_last_on_both_taxonomic_levels(self):
        selection = resolve(ADVANCED_FILTER, advanced={
            "classifications": ["Unassigned", "DENV1"],
            "subclassifications": ["Unassigned", "1I"],
        })
        self.assertEqual(selection["classifications"], ["DENV1", "Unassigned"])
        self.assertEqual(selection["subclassifications"], ["1I", "Unassigned"])

    def test_resolution_never_mutates_the_vocabulary(self):
        before_serotypes = list(ALL_SEROTYPES)
        before_genotypes = list(ALL_GENOTYPES)
        resolve(RESET_FILTER)
        resolve(BASIC_FILTER, basic={"classifications": None})
        resolve(ADVANCED_FILTER, advanced={"classifications": ["Unassigned", "DENV1"]})
        self.assertEqual(ALL_SEROTYPES, before_serotypes)
        self.assertEqual(ALL_GENOTYPES, before_genotypes)


class SelectionStoreRoundTripTest(unittest.TestCase):

    def test_dates_survive_the_json_store(self):
        # dcc.Store serialises to JSON, so the two Timestamps travel as ISO dates and must come
        # back as Timestamps for the filtering primitives.
        selection = resolve(BASIC_FILTER, basic={
            "classifications": ["DENV1"], "date_from": "2020-01-01", "date_to": "2021-12-31",
        })
        restored = selection_from_dict(selection_to_dict(selection))
        self.assertEqual(restored["date_from"], pd.Timestamp("2020-01-01"))
        self.assertEqual(restored["date_to"], pd.Timestamp("2021-12-31"))
        self.assertEqual(restored["classifications"], ["DENV1"])
        self.assertEqual(restored["source"], BASIC_FILTER)


if __name__ == "__main__":
    unittest.main()
