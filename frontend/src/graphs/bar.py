import plotly.express as px
import pandas as pd
from utils.color_schemes import (
    color_discrete_map_for_labels,
    get_chart_theme,
)
from graphs.area_plot import calculate_shared_xaxis_config, xaxis_settings_from_config


def build_bar_plot(df: pd.DataFrame, color_scheme: dict, pathogen_title: str = "genotype", date_from: str = None, date_to: str = None, legend_order: list = None, axis_df=None):
    # The order a pathogen wants arrives as legend_order, from its classification_order in
    # src/pathogens.py; set_bar_plot_layout applies it to the traces below.
    resolved_colors = color_discrete_map_for_labels(df[pathogen_title].unique(), color_scheme)
    bar_plot = px.bar(
        df,
        x='datetime',
        y='proportion',
        color=pathogen_title,
        color_discrete_map=resolved_colors,
        labels={
            'proportion': 'Proportion of Genomes',
            'datetime': 'Date',
            pathogen_title: pathogen_title.capitalize()
        },
        custom_data=[
            pathogen_title,
            'proportion',
            'period_start',
            'period_end'
        ],
    )
    set_bar_plot_layout(bar_plot, pathogen_title, df, date_from, date_to, legend_order, axis_df)

    return bar_plot


def set_bar_plot_layout(bar_plot: any, pathogen_title: str = "genotype", df: pd.DataFrame = None, date_from: str = None, date_to: str = None, legend_order: list = None, axis_df=None) -> None:
    # Get standardized theme
    theme = get_chart_theme(pathogen_title.capitalize())

    # Apply standardized theme
    bar_plot.update_layout(
        width=None,  # Allow responsive width
        height=480,  # Increased from 400 to 480 (20% increase)
        **theme
    )

    pathogen = pathogen_title.capitalize()

    bar_plot.update_traces(
        # width=15770000000, #Due to data type being a date parameter width is set in miliseconds
        hovertemplate='<b>' + pathogen + ': %{customdata[0]} </b><br><br>' + \
        '%{customdata[1]}% of genomes <br>' + \
        'from %{customdata[2]} to %{customdata[3]}<br><extra></extra>'
    )

    # Apply custom legend order if provided
    if legend_order:
        # Update legend configuration
        bar_plot.update_layout(
            legend=dict(
                **theme['legend'],
                traceorder='normal',
                itemsizing='constant'
            )
        )
        
        # Reorder traces to match the desired legend order
        # Process in reverse order to get correct forward display order
        for serotype in reversed(legend_order):
            for trace in bar_plot.data:
                if trace.name == serotype:
                    # Move this trace to the front of the legend
                    bar_plot.data = [trace] + [t for t in bar_plot.data if t.name != serotype]
                    break

    # Get shared x-axis configuration for consistency with area chart
    config_df = axis_df if axis_df is not None else df
    if config_df is not None:
        xaxis_config = calculate_shared_xaxis_config(config_df, 'datetime', date_from, date_to)
        bar_plot.update_xaxes(
            **theme['xaxis'],
            **xaxis_settings_from_config(xaxis_config),
        )
    else:
        bar_plot.update_xaxes(**theme['xaxis'])
    
    bar_plot.update_yaxes(**theme['yaxis'])
