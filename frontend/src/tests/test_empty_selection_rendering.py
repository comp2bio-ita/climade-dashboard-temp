import unittest

import pandas as pd

from graphs.area_plot import plot_area_chat
from pages.scripts import pathogen_script
from utils.color_schemes import dengue_color_scheme


def build_df_to_map(df, geo_df, enable_icons):
    # The builders are shared now, so the pathogen arrives as arguments; these tests are
    # about dengue's guards, so they pin dengue's column and palette.
    return pathogen_script.build_df_to_map(
        df, geo_df, enable_icons,
        data_col="serotype", color_scheme=dengue_color_scheme)


# A filter can legitimately select no sequence at all — an absent serotype/host pair, a year with
# no surveillance, a biologically impossible serotype/genotype combination. That used to take the
# whole filter callback down with it, which read as "the filter stopped working" because the map,
# both charts and every counter froze together. These tests pin the empty path.

SEQUENCE_COLUMNS = ["datetime", "country", "iso_a3", "serotype", "genotype", "host", "length"]

GEO_FRAME = pd.DataFrame([
    {"iso_a3": "BRA", "name_en": "Brazil", "continent": "South America"},
    {"iso_a3": "KEN", "name_en": "Kenya", "continent": "Africa"},
])


def sequences(rows):
    # The page always slices df_world_dengue, so the collection date stays datetime64 even when
    # the slice is empty. The fixture declares that dtype so an empty frame here behaves as an
    # empty selection does in the app.
    frame = pd.DataFrame(rows, columns=SEQUENCE_COLUMNS)
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    return frame


def dengue_rows():
    return sequences([
        {"datetime": pd.Timestamp("2020-03-01"), "country": "Brazil", "iso_a3": "BRA",
         "serotype": "DENV1", "genotype": "1I", "host": "Homo sapiens", "length": 10500},
        {"datetime": pd.Timestamp("2021-06-01"), "country": "Kenya", "iso_a3": "KEN",
         "serotype": "DENV2", "genotype": "2I", "host": "Aedes aegypti", "length": 10600},
    ])


class BuildMapFrameOnEmptySelectionTest(unittest.TestCase):

    def test_empty_selection_returns_an_empty_frame_instead_of_raising(self):
        # DataFrame.apply over an empty frame returns a DataFrame, which pandas refuses to assign
        # to the single 'tooltip' column.
        map_frame = build_df_to_map(sequences([]), GEO_FRAME, True)
        self.assertTrue(map_frame.empty)
        self.assertIn("tooltip", map_frame.columns)
        self.assertIn("total", map_frame.columns)

    def test_empty_selection_without_icons(self):
        map_frame = build_df_to_map(sequences([]), GEO_FRAME, False)
        self.assertTrue(map_frame.empty)
        self.assertNotIn("icon", map_frame.columns)

    def test_undated_sequence_is_still_counted_for_its_country(self):
        # The first/last detected dates are joined back on country, so an undated DENV3 genome
        # from a country that has dated genomes keeps its place in the serotype counts.
        undated = sequences([{"datetime": pd.NaT, "country": "Brazil", "iso_a3": "BRA",
                              "serotype": "DENV3", "genotype": "3I", "host": "Homo sapiens",
                              "length": 10400}])
        map_frame = build_df_to_map(
            pd.concat([dengue_rows(), undated], ignore_index=True), GEO_FRAME, False)
        self.assertEqual(len(map_frame), 2)
        self.assertEqual(map_frame["DENV3"].sum(), 1)

    def test_selection_where_every_sequence_is_undated_does_not_raise(self):
        # Nothing survives the date dropna, so the pivot carries no serotype column at all while
        # the serotype list still names DENV3 — the KeyError case.
        only_undated = sequences([{"datetime": pd.NaT, "country": "Brazil", "iso_a3": "BRA",
                                   "serotype": "DENV3", "genotype": "3I", "host": "Homo sapiens",
                                   "length": 10400}])
        map_frame = build_df_to_map(only_undated, GEO_FRAME, False)
        self.assertTrue(map_frame.empty)
        self.assertIn("DENV3", map_frame.columns)

    def test_populated_selection_still_aggregates_per_country(self):
        map_frame = build_df_to_map(dengue_rows(), GEO_FRAME, False)
        self.assertEqual(sorted(map_frame["country"]), ["Brazil", "Kenya"])
        self.assertEqual(map_frame["total"].sum(), 2)


class AreaChartOnEmptySelectionTest(unittest.TestCase):

    def chart(self, frame, target_pathogens):
        return plot_area_chat(
            df=frame,
            data_col="serotype",
            target_pathogens=target_pathogens,
            datetime_str_col="datetime",
            color_scheme=dengue_color_scheme,
            date_from="1944-01-01",
            date_to="2026-03-20",
        )

    def test_empty_selection_draws_an_empty_chart(self):
        # make_subplots rejects rows=0, and the NaT min/max would otherwise yield a NaN year.
        figure = self.chart(sequences([]), ["DENV1", "DENV2"])
        self.assertEqual(len(figure.data), 0)

    def test_populated_selection_still_draws_one_band_per_serotype(self):
        figure = self.chart(dengue_rows(), ["DENV1", "DENV2"])
        self.assertEqual(len(figure.data), 2)

    def test_the_caller_pathogen_list_is_not_reordered(self):
        # The page passes its module-level genotype list; sorting it in place would reorder the
        # dropdown options for every later request.
        genotypes = ["2I", "1I"]
        plot_area_chat(
            df=dengue_rows(), data_col="genotype", target_pathogens=genotypes,
            datetime_str_col="datetime", color_scheme={"1I": "#111111", "2I": "#222222"},
            date_from="1944-01-01", date_to="2026-03-20",
        )
        self.assertEqual(genotypes, ["2I", "1I"])


if __name__ == "__main__":
    unittest.main()
