import plotly.express as px
import pandas as pd

def build_strip_chart_new(df: pd.DataFrame, color_scheme: dict, title: str = 'Prevalent Pathogen', pathogen_title: str = "genotype"):
    strip_chart = px.strip(
        df,
        x='datetime',
        y='country',
        color='prevalent_pathogen',
        color_discrete_map=color_scheme,
        stripmode='overlay',
        hover_name='country',
        labels={
            'country': 'Country',
            'datetime': 'Date',
            'prevalent_pathogen': title
        },
        custom_data=[
            'prevalent_pathogen',
            'total_genomes',
            'genomes_per_pathogen',
            'date_initial',
            'date_final'
        ],
    )
    set_strip_chart_layout(strip_chart, pathogen_title)

    return strip_chart


def build_strip_chart(df: pd.DataFrame, color_scheme: dict, title: str = 'Prevalent Pathogen', pathogen_title: str = "variant"):
    strip_chart = px.strip(
        df,
        x='date_2weeks',
        y='country',
        color='prevalent_pathogen',
        color_discrete_map=color_scheme,
        stripmode='overlay',
        hover_name='country',
        labels={
            'country': 'Country',
            'date_2weeks': 'Date',
            'prevalent_pathogen': title
        },
        custom_data=[
            'prevalent_pathogen',
            'total_genomes',
            'genomes_per_pathogen',
            'date_initial',
            'date_final'
        ],
    )
    set_strip_chart_layout(strip_chart, pathogen_title)

    return strip_chart


def set_strip_chart_layout(strip_chart: any, pathogen_title: str = "variant") -> None:
    strip_chart.update_layout(
        paper_bgcolor='#fff',
        plot_bgcolor='#fff',
        autosize=True,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(
            yanchor='top',
            y=1.1,
            orientation='h',
        ),
        font_color='#222'
    )

    strip_chart.update_traces(
        marker=dict(size=13, line=dict(
            width=0.5, color='#222')),
        hovertemplate=('<b>Country: %{y} <br>' +
                       'Date: %{customdata[3]} to %{customdata[4]} <br>' +
                       'Total of Genomes: %{customdata[1]} </b><br>' +
                       f'{"Prevalent Variant" if pathogen_title == "variant" else "Prevalent Lineage"}: ' + '%{customdata[0]} <br>' +
                       f'{"Genomes per Variant" if pathogen_title == "variant" else "Genomes per Lineage"}: ' + '%{customdata[2]} <br><extra></extra>'
                       )
    )

    strip_chart.update_yaxes(autorange="reversed", showgrid=True,
                             gridwidth=1, gridcolor='#222')
