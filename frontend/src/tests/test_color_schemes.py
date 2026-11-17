import pandas as pd

from graphs.area_plot import area_chart_lineage_subplot, marker_sizes_for_isolated_points
from graphs.bar import build_bar_plot
from utils.color_schemes import (
    UNKNOWN_CATEGORY_COLOR,
    color_for_classification,
    color_discrete_map_for_labels,
    dengue_color_scheme,
)


class TestColorForClassification:
    def test_known_label_uses_scheme_color(self):
        assert color_for_classification("DENV1", dengue_color_scheme) == "#6f54a5"

    def test_unknown_label_uses_default_gray(self):
        incomplete = {"DENV1": "#6f54a5"}
        assert color_for_classification("Unassigned", incomplete) == UNKNOWN_CATEGORY_COLOR
        assert UNKNOWN_CATEGORY_COLOR == "#808080"

    def test_discrete_map_covers_present_labels(self):
        resolved = color_discrete_map_for_labels(["DENV1", "Unassigned"], {"DENV1": "#6f54a5"})
        assert resolved == {"DENV1": "#6f54a5", "Unassigned": "#808080"}


class TestMarkerSizesForIsolatedPoints:
    def test_single_nonzero_bucket_gets_marker(self):
        assert marker_sizes_for_isolated_points([1]) == [6]

    def test_spike_between_zeros_gets_marker(self):
        assert marker_sizes_for_isolated_points([0, 1, 0]) == [0, 6, 0]

    def test_continuous_run_has_no_markers(self):
        assert marker_sizes_for_isolated_points([1, 2, 3]) == [0, 0, 0]

    def test_two_spikes_each_get_marker(self):
        assert marker_sizes_for_isolated_points([1, 0, 2]) == [6, 0, 6]


class TestBarAreaColorParity:
    def test_unmapped_label_matches_default_on_both_charts(self):
        incomplete_scheme = {"1I": "#6f54a5"}
        bar_df = pd.DataFrame({
            "datetime": pd.to_datetime(["2016-03-01"]),
            "date_from": pd.to_datetime(["2016-01-01"]),
            "period_start": ["2016-01"],
            "period_end": ["2016-03"],
            "genotype": ["Unassigned"],
            "proportion": [100.0],
        })
        bar_figure = build_bar_plot(
            bar_df,
            color_scheme=incomplete_scheme,
            pathogen_title="genotype",
        )
        area_trace = area_chart_lineage_subplot(
            pd.DataFrame({"Unassigned": [1]}, index=pd.to_datetime(["2016-03-01"])),
            "Unassigned",
            incomplete_scheme,
        )

        bar_color = bar_figure.data[0].marker.color
        assert area_trace.line.color == UNKNOWN_CATEGORY_COLOR
        assert area_trace.marker.color == UNKNOWN_CATEGORY_COLOR
        assert bar_color == UNKNOWN_CATEGORY_COLOR


class TestAreaSparseMarkers:
    def test_single_bucket_shows_isolated_marker_only(self):
        pivot = pd.DataFrame(
            {"ACL": [1]},
            index=pd.to_datetime(["2016-03-01"]),
        )
        color = "#ff9000"
        trace = area_chart_lineage_subplot(pivot, "ACL", {"ACL": color})

        assert trace.mode == "lines+markers"
        assert list(trace.marker.size) == [6]
        assert trace.marker.color == color

    def test_continuous_run_has_no_markers(self):
        pivot = pd.DataFrame(
            {"ACL": [1, 2, 3]},
            index=pd.to_datetime(["2016-01-01", "2016-02-01", "2016-03-01"]),
        )
        trace = area_chart_lineage_subplot(pivot, "ACL", {"ACL": "#ff9000"})

        assert trace.mode == "lines+markers"
        assert list(trace.marker.size) == [0, 0, 0]
