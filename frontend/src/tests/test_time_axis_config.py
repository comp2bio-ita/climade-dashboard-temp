import pandas as pd
import pytest

from graphs.area_plot import calculate_shared_xaxis_config
from graphs.bar import build_bar_plot
from utils.functions.date_functions import (
    axis_tick_granularity,
    chart_axis_range,
    decimal_year_to_timestamp,
    timestamp_to_decimal_year,
    yearly_tick_step_years,
    yearly_tick0,
)


def _dated_frame(start, end, n=6):
    dates = pd.date_range(start, end, periods=n)
    return pd.DataFrame({"datetime": dates, "genotype": ["A"] * n})


class TestAxisTickGranularity:
    def test_one_year_or_less_is_monthly(self):
        assert axis_tick_granularity("2024-01-01", "2024-12-31") == "monthly"

    def test_between_one_and_three_years_is_quarterly(self):
        assert axis_tick_granularity("2023-01-01", "2024-06-01") == "quarterly"

    def test_beyond_three_years_is_yearly(self):
        assert axis_tick_granularity("2020-01-01", "2024-06-01") == "yearly"


class TestYearlyTickStep:
    def test_ten_year_span_uses_one_year_steps(self):
        assert yearly_tick_step_years("2014-01-01", "2024-01-01") == 1

    def test_thirty_year_span_scales_proportionally(self):
        assert yearly_tick_step_years("1994-01-01", "2024-01-01") == 2


class TestChartAxisRange:
    def test_range_ends_at_month_containing_max_date(self):
        start, end = chart_axis_range("2014-03-15", "2024-11-20")
        assert start == "2014-03-01"
        assert end == "2024-11-30"

    def test_range_uses_filter_window_when_provided(self):
        start, end = chart_axis_range(
            "2014-03-15",
            "2024-11-20",
            date_from="2010-01-01",
            date_to="2020-12-31",
        )
        assert start == "2010-01-01"
        assert end == "2020-12-31"


class TestYearlyTick0:
    def test_anchors_to_january_first_of_start_year(self):
        assert yearly_tick0("2014-06-01", "2015-01-01") == "2014-01-01"

    def test_falls_back_to_data_start_when_no_filter(self):
        assert yearly_tick0(None, "2018-09-15") == "2018-01-01"


class TestDecimalYearConversion:
    def test_leap_year_uses_366_day_denominator(self):
        # 1 Mar 2024 is day 61 of 366
        assert timestamp_to_decimal_year("2024-03-01") == pytest.approx(2024 + 60 / 366)

    def test_common_year_uses_365_day_denominator(self):
        # 1 Mar 2023 is day 60 of 365
        assert timestamp_to_decimal_year("2023-03-01") == pytest.approx(2023 + 59 / 365)

    def test_round_trip_through_calendar_year(self):
        original = 2024.5
        restored = timestamp_to_decimal_year(decimal_year_to_timestamp(original))
        assert restored == pytest.approx(original, abs=0.01)


class TestSharedXaxisConfig:
    def _assert_date_axis(self, config):
        assert config["type"] == "date"
        assert config["tickmode"] == "linear"

    def test_sub_year_span_uses_monthly_ticks(self):
        frame = _dated_frame("2024-01-01", "2024-09-01")
        config = calculate_shared_xaxis_config(
            frame, "datetime", "2024-01-01", "2024-09-01"
        )
        self._assert_date_axis(config)
        assert config["dtick"] == "M1"
        assert config["tickformat"] == "%b %Y"
        assert "tickvals" not in config

    def test_eighteen_month_span_uses_quarterly_ticks(self):
        frame = _dated_frame("2023-06-01", "2024-12-01")
        config = calculate_shared_xaxis_config(
            frame, "datetime", "2023-06-01", "2024-12-01"
        )
        self._assert_date_axis(config)
        assert config["dtick"] == "M3"
        assert config["tickformat"] == "%b %Y"
        assert "tickvals" not in config

    def test_two_year_span_uses_quarterly_ticks(self):
        frame = _dated_frame("2022-01-01", "2024-01-01")
        config = calculate_shared_xaxis_config(
            frame, "datetime", "2022-01-01", "2024-01-01"
        )
        self._assert_date_axis(config)
        assert config["dtick"] == "M3"
        assert config["tickformat"] == "%b %Y"

    def test_ten_year_span_uses_one_year_dtick(self):
        frame = _dated_frame("2014-01-01", "2024-01-01")
        config = calculate_shared_xaxis_config(
            frame, "datetime", "2014-01-01", "2024-01-01"
        )
        self._assert_date_axis(config)
        assert config["dtick"] == "M12"
        assert config["tick0"] == "2014-01-01"
        assert config["tickformat"] == "%Y"
        assert "tickvals" not in config
        assert config["range"] == ["2014-01-01", "2024-01-01"]

    def test_sparse_ten_year_span_still_gets_tick_anchor(self):
        frame = pd.DataFrame({
            "datetime": pd.to_datetime(["2016-03-01", "2022-08-15"]),
            "genotype": ["A", "A"],
        })
        config = calculate_shared_xaxis_config(
            frame, "datetime", "2014-01-01", "2024-01-01"
        )
        self._assert_date_axis(config)
        assert config["dtick"] == "M12"
        assert config["tick0"] == "2014-01-01"
        assert config["range"] == ["2014-01-01", "2024-01-01"]

    def test_ten_year_filter_uses_yearly_ticks_not_decade_steps(self):
        # Dengue used to set chart_tick_interval: 10, forcing M120 on ~10y filtered windows.
        frame = pd.DataFrame({
            "datetime": pd.to_datetime(["2016-03-01", "2022-08-15"]),
            "genotype": ["A", "A"],
        })
        config = calculate_shared_xaxis_config(
            frame, "datetime", "2014-01-01", "2024-01-01"
        )
        assert config["dtick"] == "M12"
        assert config["dtick"] != "M120"

    def test_thirty_year_span_uses_scaled_dtick(self):
        frame = _dated_frame("1994-01-01", "2024-01-01")
        config = calculate_shared_xaxis_config(
            frame, "datetime", "1994-01-01", "2024-01-01"
        )
        self._assert_date_axis(config)
        assert config["dtick"] == "M24"
        assert config["tick0"] == "1994-01-01"
        assert config["tickformat"] == "%Y"
        assert "tickvals" not in config


class TestBarPlotDateAxis:
    def test_sparse_ten_year_data_uses_date_axis_with_yearly_ticks(self):
        axis_df = pd.DataFrame({
            "datetime": pd.to_datetime(["2016-03-01", "2022-08-15"]),
            "genotype": ["A", "B"],
        })
        bar_df = pd.DataFrame({
            "datetime": pd.to_datetime(["2016-03-01", "2022-08-15"]),
            "date_from": pd.to_datetime(["2016-01-01", "2022-07-01"]),
            "period_start": ["2016-01", "2022-07"],
            "period_end": ["2016-03", "2022-08"],
            "genotype": ["A", "B"],
            "proportion": [50.0, 50.0],
        })
        figure = build_bar_plot(
            df=bar_df,
            color_scheme={"A": "#111111", "B": "#222222"},
            pathogen_title="genotype",
            date_from="2014-01-01",
            date_to="2024-01-01",
            axis_df=axis_df,
        )
        assert figure.layout.xaxis.type == "date"
        assert figure.layout.xaxis.dtick == "M12"
        assert figure.layout.xaxis.tick0 is not None

