import unittest

import numpy as np
import pandas as pd

from utils.functions.selection_functions import (
    apply_selection_to_sequences,
    canonical_accession_ids,
)


# Miniature dengue frame + geojson (no DB)
DENGUE_SEQUENCES = pd.DataFrame([
    {"genbank_sequence_data_id": "OR123456.1", "country": "Brazil", "iso_a3": "BRA",
     "serotype": "DENV2", "genotype": "2III", "host": "Homo sapiens",
     "datetime": pd.Timestamp("2023-05-01"), "length": 10700},
    {"genbank_sequence_data_id": "OR123457.1", "country": "Brazil", "iso_a3": "BRA",
     "serotype": "DENV2", "genotype": "2III", "host": "Homo sapiens",
     "datetime": pd.Timestamp("2023-07-14"), "length": 10650},
    {"genbank_sequence_data_id": "OR123458.1", "country": "Thailand", "iso_a3": "THA",
     "serotype": "DENV2", "genotype": "2III", "host": "Homo sapiens",
     "datetime": pd.Timestamp("2023-08-02"), "length": 10500},
    {"genbank_sequence_data_id": "OR123459.1", "country": "Kenya", "iso_a3": "KEN",
     "serotype": "DENV2", "genotype": "2III", "host": "Aedes aegypti",
     "datetime": pd.Timestamp("2023-09-30"), "length": 4200},
])

WORLD_GEOJSON = pd.DataFrame([
    {"iso_a3": "BRA", "continent": "South America"},
    {"iso_a3": "THA", "continent": "Asia"},
    {"iso_a3": "KEN", "continent": "Africa"},
])

ALL_CONTINENTS = ["Africa", "Asia", "South America"]


def selection(continents):
    return {
        "date_from": pd.Timestamp("2023-01-01"),
        "date_to": pd.Timestamp("2023-12-31"),
        "classifications": ["DENV2"],
        "subclassifications": ["2III"],
        "countries": ["Brazil", "Thailand", "Kenya"],
        "continents": continents,
        "hosts": ["Homo sapiens", "Aedes aegypti"],
    }


def submitted_accession_ids(continents):
    # Submission path: curated sequences → canonical accession set
    selected_sequences = apply_selection_to_sequences(
        DENGUE_SEQUENCES, selection(continents), WORLD_GEOJSON
    )
    return canonical_accession_ids(selected_sequences["genbank_sequence_data_id"])


class CanonicalAccessionIdsTest(unittest.TestCase):

    def test_missing_and_blank_values_are_dropped(self):
        messy = pd.Series(["OR123456.1", None, np.nan, "   ", "", "OR123457.1"])
        self.assertEqual(canonical_accession_ids(messy), ["OR123456.1", "OR123457.1"])

    def test_duplicates_and_row_order_do_not_change_the_set(self):
        shuffled = pd.Series(["OR123457.1", "OR123456.1", "OR123457.1", " OR123456.1 "])
        self.assertEqual(canonical_accession_ids(shuffled), ["OR123456.1", "OR123457.1"])

    def test_accession_versions_are_preserved(self):
        # .1 and .2 are distinct depositions
        revised = pd.Series(["OR123456.2", "OR123456.1"])
        self.assertEqual(canonical_accession_ids(revised), ["OR123456.1", "OR123456.2"])


class SubmittedSelectionTest(unittest.TestCase):

    def test_submitted_ids_match_the_curated_selection_exactly(self):
        selected_sequences = apply_selection_to_sequences(
            DENGUE_SEQUENCES, selection(ALL_CONTINENTS), WORLD_GEOJSON
        )
        self.assertEqual(
            submitted_accession_ids(ALL_CONTINENTS),
            sorted(selected_sequences["genbank_sequence_data_id"]),
        )

    def test_continent_narrowing_reaches_the_submitted_set(self):
        # Continent comes from geojson, not dengue_meta_tb
        south_america_only = submitted_accession_ids(["South America"])

        self.assertEqual(south_america_only, ["OR123456.1", "OR123457.1"])
        self.assertLess(len(south_america_only), len(submitted_accession_ids(ALL_CONTINENTS)))

    def test_each_continent_selects_its_own_sequences(self):
        self.assertEqual(submitted_accession_ids(["Asia"]), ["OR123458.1"])
        self.assertEqual(submitted_accession_ids(["Africa"]), ["OR123459.1"])


if __name__ == "__main__":
    unittest.main()
