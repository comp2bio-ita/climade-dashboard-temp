#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pure decimal-year tick generation for TreeTime phylo axes."""

from unittest.mock import patch

import pytest

from utils.functions.date_functions import phylo_decimal_year_axis_ticks


class TestPhyloDecimalYearAxisTicks:
    def test_narrow_window_uses_monthly_ticks(self):
        granularity, tickvals, ticktext, step_years = phylo_decimal_year_axis_ticks(
            2024.0, 2024.75
        )
        assert granularity == "monthly"
        assert len(tickvals) >= 2
        assert step_years is None
        assert any("Jan" in label for label in ticktext)
        assert any("2024" in label for label in ticktext)

    def test_ten_year_window_uses_yearly_ticks(self):
        granularity, tickvals, ticktext, step_years = phylo_decimal_year_axis_ticks(
            2014.0, 2024.0
        )
        assert granularity == "yearly"
        assert step_years == 1
        assert tickvals[0] == 2014.0
        assert "2024" in ticktext

    def test_pipeline_scale_span_does_not_raise(self):
        granularity, tickvals, ticktext, step_years = phylo_decimal_year_axis_ticks(
            1910.3, 2026.2
        )
        assert granularity == "yearly"
        assert step_years >= 1
        assert tickvals[0] <= 1910.0
        assert tickvals[-1] >= 2020.0

    def test_pre_1677_root_does_not_raise(self):
        granularity, tickvals, ticktext, step_years = phylo_decimal_year_axis_ticks(
            1200.0, 2025.0
        )
        assert granularity == "yearly"
        assert tickvals[0] == 1200.0
        assert max(tickvals) >= 1900.0
        assert step_years >= 1

    def test_roman_era_origin_does_not_raise(self):
        granularity, tickvals, ticktext, step_years = phylo_decimal_year_axis_ticks(
            10.0, 11.0
        )
        assert granularity in ("monthly", "quarterly", "yearly")
        assert tickvals
        assert ticktext

    def test_year_zero_edge_does_not_raise(self):
        granularity, tickvals, ticktext, step_years = phylo_decimal_year_axis_ticks(
            0.5, 1.5
        )
        assert granularity == "monthly"
        assert tickvals

    def test_negative_bound_does_not_raise(self):
        granularity, tickvals, ticktext, step_years = phylo_decimal_year_axis_ticks(
            -100.0, 2020.0
        )
        assert granularity == "yearly"
        assert tickvals[0] == -100.0

    def test_non_finite_bound_falls_back_without_error(self):
        granularity, tickvals, ticktext, step_years = phylo_decimal_year_axis_ticks(
            float("nan"), 2020.0
        )
        assert granularity == "yearly"
        assert tickvals

    def test_swapped_bounds_match_ordered_pair(self):
        ordered = phylo_decimal_year_axis_ticks(1900.0, 2025.0)
        swapped = phylo_decimal_year_axis_ticks(2025.0, 1900.0)
        assert ordered == swapped

    def test_never_calls_pandas_timestamp_helpers(self):
        with patch("utils.functions.date_functions.pd.date_range") as mock_date_range:
            with patch(
                "utils.functions.date_functions.decimal_year_to_timestamp"
            ) as mock_to_ts:
                phylo_decimal_year_axis_ticks(1200.0, 2025.0)
                phylo_decimal_year_axis_ticks(2024.0, 2024.75)
                phylo_decimal_year_axis_ticks(0.5, 1.5)
                mock_date_range.assert_not_called()
                mock_to_ts.assert_not_called()
