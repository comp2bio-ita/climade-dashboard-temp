import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta, datetime
from utils.color_schemes import color_for_classification, get_chart_theme
from utils.functions.date_functions import (
    axis_tick_granularity,
    chart_axis_range,
    datetime_year_dtick,
    yearly_tick_step_years,
    yearly_tick0,
    transform_to_semester,
    transform_to_trimester,
    transform_to_year,
)

def xaxis_settings_from_config(xaxis_config):
    keys = ('range', 'tickangle', 'type', 'tickmode', 'dtick', 'tick0', 'tickformat', 'tickvals', 'ticktext')
    return {key: xaxis_config[key] for key in keys if key in xaxis_config}

def _date_axis_base():
    return {
        'type': 'date',
        'tickmode': 'linear',
    }

def calculate_shared_xaxis_config(df: pd.DataFrame, datetime_col: str, date_from: str = None, date_to: str = None):
    """
    Calculate shared x-axis configuration for consistent date ranges and tick intervals.
    This ensures both bar chart and area chart use identical x-axis settings.
    """
    # Use the same date range calculation as bar chart
    delta_time = 0
    if isinstance(date_from, str) and isinstance(date_to, str):
        delta_time = datetime.strptime(date_to[0:10], '%Y-%m-%d') - datetime.strptime(date_from[0:10], '%Y-%m-%d')
    else:
        # Fallback to min/max if date_from/date_to not provided
        date_end = df[datetime_col].max()
        date_start = df[datetime_col].min()
        # Ensure we have datetime objects, not strings
        if isinstance(date_end, str):
            date_end = pd.to_datetime(date_end)
        if isinstance(date_start, str):
            date_start = pd.to_datetime(date_start)
        delta_time = date_end - date_start
    
    delta_in_years = int(delta_time.days / 365.25)
    
    # Get the actual date range from the processed data
    df_copy = df.copy(deep=True)
    
    # Ensure datetime column is in datetime format before applying transformations
    if df_copy[datetime_col].dtype == 'object' or df_copy[datetime_col].dtype == 'string':
        df_copy[datetime_col] = pd.to_datetime(df_copy[datetime_col], errors='coerce')

    raw_min_date = df_copy[datetime_col].min()
    raw_max_date = df_copy[datetime_col].max()
    if isinstance(raw_min_date, str):
        raw_min_date = pd.to_datetime(raw_min_date)
    if isinstance(raw_max_date, str):
        raw_max_date = pd.to_datetime(raw_max_date)
    
    # Apply the same date transformations as bar chart
    if delta_in_years > 40:
        df_copy[datetime_col] = df_copy[datetime_col].apply(transform_to_year)
        graph_time_gap = "Y"
    elif delta_in_years > 15:
        df_copy[datetime_col] = df_copy[datetime_col].apply(transform_to_semester)
        graph_time_gap = "M"
    elif delta_in_years > 5:
        df_copy[datetime_col] = df_copy[datetime_col].apply(transform_to_trimester)
        graph_time_gap = "M"
    else:
        graph_time_gap = "M"
    
    df_copy[datetime_col] = df_copy[datetime_col].dt.to_period(graph_time_gap).dt.to_timestamp()
    
    # Get the actual min/max dates from processed data (this respects the filter)
    actual_min_date = df_copy[datetime_col].min()
    actual_max_date = df_copy[datetime_col].max()
    
    # Ensure we have datetime objects for year extraction
    if isinstance(actual_min_date, str):
        actual_min_date = pd.to_datetime(actual_min_date)
    if isinstance(actual_max_date, str):
        actual_max_date = pd.to_datetime(actual_max_date)

    # A selection matching no sequence leaves no dated rows, so min/max come back as NaT and the
    # year extraction below would yield NaN. Fall back to the window the user asked for: the axis
    # then spans the requested period with nothing plotted on it.
    if pd.isna(actual_min_date) or pd.isna(actual_max_date):
        actual_min_date = pd.to_datetime(date_from) if date_from else pd.Timestamp.today()
        actual_max_date = pd.to_datetime(date_to) if date_to else actual_min_date
        raw_min_date = actual_min_date
        raw_max_date = actual_max_date

    axis_range = chart_axis_range(raw_min_date, raw_max_date, date_from, date_to)

    granularity = axis_tick_granularity(actual_min_date, actual_max_date)
    if granularity in ("monthly", "quarterly"):
        return {
            **_date_axis_base(),
            'dtick': 'M1' if granularity == 'monthly' else 'M3',
            'tickformat': '%b %Y',
            'range': axis_range,
            'tickangle': 0,
        }

    step = yearly_tick_step_years(actual_min_date, actual_max_date)

    return {
        **_date_axis_base(),
        'dtick': datetime_year_dtick(step),
        'tick0': yearly_tick0(date_from, actual_min_date),
        'tickformat': '%Y',
        'range': axis_range,
        'tickangle': 0,
    }

def plot_area_chat(df: pd.DataFrame, data_col: str, target_pathogens: list[str], datetime_str_col: str, color_scheme: dict, fig_title: str = None, date_from: str = None, date_to: str = None, legend_order: list = None) -> go.Figure:

    # The subplots are stacked in this order, so it has to be the order the legend reads in:
    # whatever the pathogen declared, which arrives as legend_order. Anything the pathogen
    # does not name keeps its place at the end.
    if legend_order:
        target_pathogens = ([p for p in legend_order if p in target_pathogens]
                            + [p for p in target_pathogens if p not in legend_order])
    else:
        # sorted() rather than .sort(): the caller passes its module-level list of every known
        # genotype, and reordering it in place would leak into the dropdown options.
        target_pathogens = sorted(target_pathogens)

    subplots = [ 
        area_chart_lineage_subplot(
            data_process_pivot_lineage(df, data_col, pathogen, datetime_str_col, date_from, date_to), pathogen, color_scheme
        )
        for pathogen in target_pathogens
    ]

    valid_subplots = [ subplot for subplot in subplots if subplot ]
    
    n_rows = len(valid_subplots)  # numero de linhas eh igual ao numero de subplots   # o len() e uma funcao que retorna o tamanho de uma lista (o numero de elementos) # len = length

    # A selection can match no sequence at all, leaving nothing to stack. make_subplots rejects
    # rows=0, so keep one empty panel: the chart draws its axes and the genome counters on the
    # cards already tell the viewer the selection is empty.
    # going to create a subplot
    fig = make_subplots(rows=max(n_rows, 1), cols=1, x_title="Date", y_title="Number of Genomes")

    # Add traces to the subplots
    for index, subplot in enumerate(valid_subplots, start=1):
        fig.add_trace(subplot, row=index, col=1)
        fig.update_yaxes(gridcolor="#000", row=index, col=1)
        # fig.update_layout(**{f'xaxis{index if index > 1 else ""}': dict(tickangle=0)})

    # Get shared x-axis configuration for consistency with bar chart
    xaxis_config = calculate_shared_xaxis_config(df, datetime_str_col, date_from, date_to)
    xaxis_settings = xaxis_settings_from_config(xaxis_config)

    # Get standardized theme
    theme = get_chart_theme(data_col.capitalize())

    # Apply standardized theme (figure-level; axis styling applied below)
    fig.update_layout(
        title=fig_title,
        height=960,  # Increased from 800 to 960 (20% increase)
        width=None,  # Allow responsive width
        **theme
    )

    for idx in range(1, max(n_rows, 1) + 1):
        fig.update_xaxes(**theme['xaxis'], **xaxis_settings, row=idx, col=1)
        fig.update_yaxes(**theme['yaxis'], row=idx, col=1)

    # Apply custom legend order if provided
    if legend_order:
        # target_pathogens is already in legend order — it had to be, because it also fixed
        # the order the subplots were stacked in above.
        fig.update_layout(
            legend=dict(
                **theme['legend'],
                traceorder='normal',
                itemsizing='constant'
            )
        )

        # Reorder traces to match the desired legend order
        # Process in reverse order to get correct forward display order
        for serotype in reversed(target_pathogens):
            for trace in fig.data:
                if trace.name == serotype:
                    # Move this trace to the front of the legend
                    fig.data = [trace] + [t for t in fig.data if t.name != serotype]
                    break
    else:
        # For non-serotype data, use normal ordering
        fig.update_layout(
            legend=dict(
                **theme['legend'],
                traceorder='normal'
            )
        )

    return fig

def data_process_pivot_lineage(df: pd.DataFrame, data_col: str, target_pathogen: str, datetime_col: str, date_from: str = None, date_to: str = None):
    # Use the same date processing logic as the bar chart
    df_copy = df.copy(deep=True)
    
    # Use the same date range calculation as bar chart
    delta_time = 0
    if isinstance(date_from, str) and isinstance(date_to, str):
        delta_time = datetime.strptime(date_to[0:10], '%Y-%m-%d') - datetime.strptime(date_from[0:10], '%Y-%m-%d')
    else:
        # Fallback to min/max if date_from/date_to not provided
        date_end = df_copy[datetime_col].max()
        date_start = df_copy[datetime_col].min()
        # Ensure we have datetime objects, not strings
        if isinstance(date_end, str):
            date_end = pd.to_datetime(date_end)
        if isinstance(date_start, str):
            date_start = pd.to_datetime(date_start)
        delta_time = date_end - date_start
    
    delta_in_years = int(delta_time.days / 365.25)
    
    # Use the same time grouping logic as bar chart
    graph_time_gap = "M"
    offset_months = 1
    offset_years = 0
    
    if delta_in_years > 40:
        graph_time_gap = "Y"
        offset_months = 0
        offset_years = 1
    elif delta_in_years > 15:
        offset_months = 6
    elif delta_in_years > 5:
        offset_months = 3
    else:
        offset_months = 1
    
    # Apply the same date transformations as bar chart
    if offset_months == 3:
        df_copy[datetime_col] = df_copy[datetime_col].apply(transform_to_trimester)
    elif offset_months == 6:
        df_copy[datetime_col] = df_copy[datetime_col].apply(transform_to_semester)
    elif offset_years == 1:
        df_copy[datetime_col] = df_copy[datetime_col].apply(transform_to_year)
    
    df_copy[datetime_col] = df_copy[datetime_col].dt.to_period(graph_time_gap).dt.to_timestamp()
    
    # Filter for the specific pathogen
    df_filtered = df_copy[df_copy[data_col] == target_pathogen].copy()
    
    # Group by pathogen and date
    df_count = df_filtered.groupby([data_col, datetime_col]).size().reset_index(name="Count")
    
    not_null_values = [value for value in list(set(df_count["Count"])) if value]
    
    if not not_null_values:
        return pd.DataFrame()
    
    # Create pivot table with the same date format as bar chart
    pivot_df = df_count.pivot(index=datetime_col, columns=data_col, values="Count")
    pivot_df.fillna(0, inplace=True)
    pivot_df = pivot_df.sort_index()

    return pivot_df

ISOLATED_MARKER_SIZE = 6


def marker_sizes_for_isolated_points(y_series):
    counts = list(y_series)
    sizes = []
    for index, count in enumerate(counts):
        if count <= 0:
            sizes.append(0)
        elif (index == 0 or counts[index - 1] == 0) and (
            index == len(counts) - 1 or counts[index + 1] == 0
        ):
            sizes.append(ISOLATED_MARKER_SIZE)
        else:
            sizes.append(0)
    return sizes


def area_chart_lineage_subplot(df: pd.DataFrame, pathogen: str, color_scheme: dict):

    if df.empty:
        return None

    color = color_for_classification(pathogen, color_scheme)
    y_series = df[pathogen]
    trace = go.Scatter(
        name=pathogen,
        mode="lines+markers",
        line=dict(smoothing=0.5, shape="spline", color=color),
        marker=dict(size=marker_sizes_for_isolated_points(y_series), color=color),
        fill="tonexty",
        fillcolor=color,
        x=df.index,
        y=y_series,
        hovertemplate="%{x|%Y-%m}<br>Count: %{y}<extra></extra>",
    )
    return trace