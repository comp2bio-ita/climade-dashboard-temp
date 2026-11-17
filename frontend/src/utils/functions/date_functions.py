
import calendar
import math

import pandas as pd


# The advanced-filter RangeSlider stores absolute days since the Unix epoch (not an offset from the
# dataset start), so the client-side tooltip can format a date from the raw value with no base date.
SLIDER_EPOCH = pd.Timestamp("1970-01-01")

DASHBOARD_TIMEZONE = "Africa/Johannesburg"


def today_in_dashboard_timezone():
    # The surveillance team reads the dashboard in South African time, so "today" is their day,
    # not the server's. Returned naive to compare directly with the naive collection dates.
    return pd.Timestamp.now(tz=DASHBOARD_TIMEZONE).normalize().tz_localize(None)


def date_to_slider_value(date):
    return int((pd.to_datetime(date).normalize() - SLIDER_EPOCH).days)


def slider_value_to_date(value):
    return SLIDER_EPOCH + pd.Timedelta(days=int(value))


def slider_year_month_marks(min_date, max_date, fractions=(0, 0.25, 0.5, 0.75, 1.0)):
    low = date_to_slider_value(min_date)
    span = date_to_slider_value(max_date) - low
    return {
        low + int(span * fraction): slider_value_to_date(low + int(span * fraction)).strftime('%Y-%m')
        for fraction in fractions
    }


def transform_to_semester(date: pd.Timestamp) -> pd.Timestamp:
    if date.month <= 6:
        return pd.Timestamp(year=date.year, month=6, day=1)
    else:
        return pd.Timestamp(year=date.year, month=12, day=1)


def transform_to_trimester(date: pd.Timestamp) -> pd.Timestamp:
    if date.month <= 3:
        return pd.Timestamp(year=date.year, month=3, day=1)
    elif date.month <= 6:
        return pd.Timestamp(year=date.year, month=6, day=1)
    elif date.month <= 9:
        return pd.Timestamp(year=date.year, month=9, day=1)
    else:
        return pd.Timestamp(year=date.year, month=12, day=1)


def transform_to_year(date: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(year=date.year, month=1, day=1)


def days_in_calendar_year(year):
    return 366 if calendar.isleap(year) else 365


def axis_tick_granularity(date_from, date_to):
    start = pd.to_datetime(date_from)
    end = pd.to_datetime(date_to)
    if end <= start + pd.DateOffset(years=1):
        return "monthly"
    if end <= start + pd.DateOffset(years=3):
        return "quarterly"
    return "yearly"


def yearly_tick_step_years(start, end):
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    if end <= start + pd.DateOffset(years=15):
        return 1
    span_years = end.year - start.year + 1
    return max(1, span_years // 12)


def datetime_year_dtick(step_years):
    return f"M{12 * step_years}"


def yearly_tick0(date_from, fallback_start):
    anchor = pd.to_datetime(date_from) if date_from else pd.to_datetime(fallback_start)
    return pd.Timestamp(year=anchor.year, month=1, day=1).strftime("%Y-%m-%d")


def chart_axis_range(raw_min, raw_max, date_from=None, date_to=None):
    if date_from and date_to:
        range_start = pd.to_datetime(date_from).normalize()
        range_end = pd.to_datetime(date_to).normalize()
        return [range_start.strftime("%Y-%m-%d"), range_end.strftime("%Y-%m-%d")]

    raw_min = pd.Timestamp(raw_min).normalize()
    raw_max = pd.Timestamp(raw_max).normalize()
    range_start = raw_min.replace(day=1)
    range_end = raw_max + pd.offsets.MonthEnd(0)
    return [range_start.strftime("%Y-%m-%d"), range_end.strftime("%Y-%m-%d")]


def timestamp_to_decimal_year(ts):
    ts = pd.Timestamp(ts).normalize()
    year = ts.year
    day_of_year = ts.timetuple().tm_yday
    return year + (day_of_year - 1) / days_in_calendar_year(year)


def decimal_year_to_timestamp(decimal_year):
    year = int(decimal_year)
    days_in_year = days_in_calendar_year(year)
    day_of_year = int(round((decimal_year - year) * days_in_year)) + 1
    day_of_year = min(max(day_of_year, 1), days_in_year)
    return pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=day_of_year - 1)


def decimal_year_tick_granularity(x_min, x_max):
    lo, hi = min(x_min, x_max), max(x_min, x_max)
    span = hi - lo
    if span <= 1.0:
        return "monthly"
    if span <= 3.0:
        return "quarterly"
    return "yearly"


def yearly_tick_step_from_decimal_span(x_min, x_max):
    lo, hi = min(x_min, x_max), max(x_min, x_max)
    span_years = int(hi) - int(lo) + 1
    if span_years <= 15:
        return 1
    return max(1, span_years // 12)


def floor_decimal_year_to_month(decimal_year):
    return math.floor(decimal_year * 12) / 12.0


def floor_decimal_year_to_quarter(decimal_year):
    return math.floor(decimal_year * 4) / 4.0


def decimal_year_to_month_label(decimal_year):
    year = int(decimal_year)
    month = int((decimal_year - year) * 12) + 1
    month = min(12, max(1, month))
    return f"{calendar.month_abbr[month]} {year}"


def _yearly_decimal_year_ticks(x_min, x_max):
    step_years = yearly_tick_step_from_decimal_span(x_min, x_max)
    min_year = int(min(x_min, x_max))
    max_year = int(max(x_min, x_max)) + 1
    tickvals = [float(y) for y in range(min_year, max_year + 1, step_years)]
    ticktext = [str(int(y)) for y in tickvals]
    return tickvals, ticktext, step_years


def _normalize_phylo_axis_bounds(x_min, x_max):
    if not math.isfinite(x_min):
        x_min = x_max if math.isfinite(x_max) else 2000.0
    if not math.isfinite(x_max):
        x_max = x_min
    lo, hi = min(x_min, x_max), max(x_min, x_max)
    if lo == hi:
        hi = lo + 1.0
    return lo, hi


def phylo_decimal_year_axis_ticks(x_min, x_max):
    """Tick plan for TreeTime calendar axes. Pure float/int; never uses pandas."""
    had_non_finite = not (math.isfinite(x_min) and math.isfinite(x_max))
    lo, hi = _normalize_phylo_axis_bounds(x_min, x_max)
    if had_non_finite:
        tickvals, ticktext, step_years = _yearly_decimal_year_ticks(lo, hi)
        return "yearly", tickvals, ticktext, step_years

    granularity = decimal_year_tick_granularity(lo, hi)

    if granularity == "yearly":
        tickvals, ticktext, step_years = _yearly_decimal_year_ticks(lo, hi)
        return granularity, tickvals, ticktext, step_years

    step = 1 / 12 if granularity == "monthly" else 0.25
    floor_fn = (floor_decimal_year_to_month if granularity == "monthly"
                else floor_decimal_year_to_quarter)
    tick = floor_fn(lo)
    tickvals = []
    ticktext = []
    while tick <= hi + step * 0.5:
        tickvals.append(tick)
        ticktext.append(decimal_year_to_month_label(tick))
        tick += step
    return granularity, tickvals, ticktext, None


def decimal_year_axis_ticks(x_min, x_max):
    return phylo_decimal_year_axis_ticks(x_min, x_max)
