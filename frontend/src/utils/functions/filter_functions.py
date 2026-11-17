import pandas as pd

from utils.functions.geo_functions import attach_continent


def apply_filters_to_df(
    df: pd.DataFrame,
    date_from: pd.Timestamp | str = None,
    date_to: pd.Timestamp | str = None,
    serotypes: list[str] = None,
    genotypes: list[str] = None,
    lineages: list[str] = None,
    variants: list[str] = None,
    countries: list[str] = None,
    continents: list[str] = None,
    hosts: list[str] = None
) -> pd.DataFrame:

    filtered_df = df.copy()
    #TODO refact those conditional clauses
    if (date_from) and (date_to):
        begin = pd.to_datetime(date_from).tz_localize(None)
        end = pd.to_datetime(date_to).tz_localize(None)

        filtered_df = filtered_df.loc[(filtered_df['datetime'] >= begin) & (filtered_df['datetime'] <= end)]

    if serotypes:
        filtered_df = filtered_df.loc[filtered_df['serotype'].isin(serotypes)]

    if genotypes:
        filtered_df = filtered_df.loc[filtered_df['genotype'].isin(genotypes)]

    if lineages:
        filtered_df = filtered_df.loc[filtered_df['lineage'].isin(lineages)]

    if variants:
        filtered_df = filtered_df.loc[filtered_df['variant'].isin(variants)]

    if countries:
        filtered_df = filtered_df.loc[filtered_df['country'].isin(countries)]

    if continents:
        filtered_df = filtered_df.loc[filtered_df['continent'].isin(
            continents)]
        
    if hosts is not None:
        filtered_df = filtered_df.loc[filtered_df['host'].isin(hosts)]

    return filtered_df


def filter_by_continents(df, continents, geojson_df):
    # Single source of truth for the continent restriction. Enrich-if-needed (sequence frames have
    # no continent column; map frames already do), then reuse the one filtering primitive. Keeping
    # this composed lets per-sequence prechecks and the aggregated map share the exact same logic.
    enriched = attach_continent(df, geojson_df)
    return apply_filters_to_df(df=enriched, continents=continents)


def clean_df(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    cleaned_df = df.dropna(subset=columns)
    return cleaned_df


def get_unique_values_from_column(df: pd.DataFrame, column: str) -> list[str]:
    uniques = df[column].unique().tolist()
    uniques.sort()
    return uniques
