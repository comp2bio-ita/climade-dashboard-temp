"""Frame builders behind the pathogen dashboard.

One module for all three pathogens. It used to be three — dengue_script.py, chikungunya_script.py
and zika_script.py — which were the same code with two things swapped: the classification column
and the colour palette. Both are declared in src/pathogens.py, so they arrive as arguments here
and nothing in this module knows which virus it is building for.

The caller supplies `data_col` and `color_scheme` explicitly rather than the module importing a
palette, which is what allowed the three copies to become one.
"""

from datetime import datetime

import pandas as pd

from graphs.map import build_icon
from utils.functions.date_functions import (
    transform_to_semester,
    transform_to_trimester,
    transform_to_year,
)
from utils.functions.filter_functions import clean_df
from utils.functions.geo_functions import (
    CONTINENTS_NAMES_LIST,
    country_to_ISO,
    geojson_geometry_property,
    geojson_id_property,
    geojson_props_of_interest,
    geojson_to_df,
    read_geojson,
)
from utils.models.database_models import UpdateLogs


# --- Import-time data preparation ------------------------------------------------------
#
# A page runs load_world_geojson() and load_pathogen_frame() once, at import, then applies
# any rule of its own to the rows before calling write_dataset() and derive_vocabulary().
# Splitting it there is what keeps dengue's collection-date floor in dengue_page.py: it is
# the one thing here that is true of a single virus, and it stays visible on that page
# rather than becoming a field every pathogen has to declare.


def load_world_geojson():
    return geojson_to_df(
        read_geojson("data/geojson/world_geojson.json"),
        geojson_props_of_interest,
        geojson_geometry_property,
        geojson_id_property
    )


def last_update_text(database):
    record = database.get_last_update(entity_class=UpdateLogs)
    if not record or not record.get("timestamp"):
        return "Unknown"
    return record["timestamp"].strftime("%Y-%m-%d")


def _clamp_to_scheme(frame, column, color_scheme):
    """A value the palette does not name cannot be drawn, so it is shown as Unassigned."""
    frame[column] = frame[column].apply(
        lambda value: value if value in list(color_scheme.keys()) else "Unassigned")


def load_pathogen_frame(spec, database):
    """The pathogen's metadata table, normalised. `datetime` comes back tz-naive.

    No date-domain rule is applied here — a page that has one applies it to the returned
    rows before deriving its vocabulary.
    """
    frame = pd.DataFrame(database.list_records(entity_class=spec["meta_entity"]))

    frame = clean_df(frame, ['country', 'collection_date'])

    frame = frame.replace(to_replace="unknown", value="Unknown")

    frame = frame.replace(to_replace="unassigned", value="Unassigned")

    
    if spec["db_classification_name_map"]:
        frame[spec["classification_column"]] = frame[spec["classification_column"]].str.strip()
        frame[spec["classification_column"]] = frame[spec["classification_column"]].replace(spec["db_classification_name_map"])

    frame[spec["classification_column"]] = frame[spec["classification_column"]].fillna("Unassigned")

    country_to_ISO(df=frame, column="country", new_iso_column_name="iso_a3")

    frame['datetime'] = pd.to_datetime(
        frame['collection_date'],
        format='%Y-%m-%dT%H:%M:%SZ', utc=True,
        errors='coerce'
    )

    frame["datetime"] = frame["datetime"].dt.tz_localize(None)

    frame['host'] = frame['host'].fillna(value="Unknown")

    _clamp_to_scheme(frame, spec["classification_column"], spec["color_scheme"])

    if spec["subclassification_column"] is not None:
        _clamp_to_scheme(frame, spec["subclassification_column"],
                         spec["subclassification_color_scheme"])

    frame = frame.drop(columns=["id"], axis=1)

    frame["country_acr"] = frame["iso_a3"]

    locations = database.get_locations_for_accessions(
        frame["genbank_sequence_data_id"].tolist()
    )
    frame["location"] = frame["genbank_sequence_data_id"].map(locations)

    return frame


def write_dataset(spec, frame):
    """The full-dataset TSV the download button falls back to before any filter."""
    frame.to_csv(
        spec["dataset_path"],
        sep="\t",
        index=False,
        columns=spec["download_columns"]
    )


def _sorted_with_unassigned_last(values):
    ordered = sorted(values)
    if "Unassigned" in ordered:
        ordered.remove("Unassigned")
        ordered.append("Unassigned")
    return ordered


def derive_vocabulary(spec, frame):
    """The option lists and date bounds the page's widgets and filters read."""
    countries = sorted(frame['country'].unique().tolist())
    continents = CONTINENTS_NAMES_LIST

    subclassifications = []
    if spec["subclassification_column"] is not None:
        subclassifications = _sorted_with_unassigned_last(
            frame[spec["subclassification_column"]].unique().tolist())

    return {
        "classifications": _sorted_with_unassigned_last(
            frame[spec["classification_column"]].unique().tolist()),
        "subclassifications": subclassifications,
        "countries": countries,
        "continents": continents,
        "hosts": frame["host"].unique().tolist(),
        # Country and continent share one search box, so the options carry which kind they are
        "regions": (
            [{"label": f"{country} (Country)", "value": country} for country in countries]
            + [{"label": f"{continent} (Continent)", "value": continent}
               for continent in continents]
        ),
        "min_date": frame["datetime"].min(skipna=True),
        "max_date": frame["datetime"].max(skipna=True),
    }


# --- Figure frames ---------------------------------------------------------------------


def build_tooltip(row: tuple, labels: list[str], color_map: dict) -> str:
    item = dict(row)
    return f"<b>{item['name_en']} ({int(item['total'])} genomes):</b><br><br>\n" + "<br>\n".join([
        f"""<a style="color:{color_map[label]};font-size:120%;margin-left:2%;">◼</a> {label}: {int(item[label])}""" for label in labels
    ]) + f"""<br><br>
          First sequence: {item['first_detected']}<br>\n
          Last sequence: {item['last_detected']}<br>
          """


def build_percentage_df(df: pd.DataFrame, data_col: str) -> pd.DataFrame:

    # Group by time period and classification, count how many were detected
    value_counts = df.groupby(
        [df['datetime'], data_col]).size().reset_index(name='count')

    # Calculate the total acquired in each time period
    period_totals = df.groupby(
        df['datetime']).size().reset_index(name='total_count')

    # Merge the counts and totals DataFrames
    result = pd.merge(value_counts, period_totals, on='datetime')

    result['proportion'] = (
        round(result['count']*100/result['total_count'], 2))

    return result


def build_df_to_map(df: pd.DataFrame, geo_df: pd.DataFrame, enable_icons: bool = True,
                    *, data_col: str, color_scheme: dict) -> pd.DataFrame:

    copy_df = df.copy(deep=True)

    # calculating the fist detected date and the last detected date
    detected_dates_df = copy_df.groupby('country').agg(
        {'datetime': ['min', 'max']
         })['datetime'].reset_index()

    detected_dates_df.rename(
        columns={"min": "first_detected", "max": "last_detected"},
        inplace=True
    )

    detected_dates_df['first_detected'] = detected_dates_df['first_detected'].dt.strftime('%Y-%m-%d')
    detected_dates_df['last_detected'] = detected_dates_df['last_detected'].dt.strftime('%Y-%m-%d')

    # combining the original filtered dataset to the detected_dates
    merged_df = copy_df.merge(detected_dates_df, how="left", on=["country"])

    # grouping by the columns of interest and generating count of genomes
    grouped_count_df = merged_df.groupby(
        ['country', 'iso_a3', 'first_detected', 'last_detected', data_col]
    ).size().reset_index(name="detected_count")

    labels = list(copy_df[data_col].unique())

    labels.sort()

    # pivoting dataframw to reorganize the data for the map
    grouped_pivot_df = pd.pivot_table(
        grouped_count_df,
        values='detected_count', index=['country', 'iso_a3', 'first_detected', 'last_detected'],
        columns=[data_col], fill_value=0
    )
    grouped_pivot_df.reset_index(inplace=True)

    # A value present in the selection can still be absent from the pivot — every sequence
    # carrying it may lack a collection date or a mappable country, and those rows are dropped
    # above. Give it an explicit zero column so the tooltip still lists it and the sum below
    # cannot raise KeyError.
    for label in labels:
        if label not in grouped_pivot_df.columns:
            grouped_pivot_df[label] = 0

    # Calculating proportion and generationg new columns
    grouped_pivot_df['total'] = grouped_pivot_df[labels].sum(axis=1)

    final_df = grouped_pivot_df.merge(geo_df, on="iso_a3")

    # A selection can legitimately match no sequence (an absent genotype/host pair, a year with
    # no surveillance). DataFrame.apply over an empty frame returns a DataFrame rather than a
    # Series, which pandas refuses to assign to a single column, so the per-row columns are added
    # only when there are rows. The caller gets an empty frame of the right shape.
    if final_df.empty:
        final_df['tooltip'] = pd.Series(dtype="object")
        if enable_icons:
            final_df['icon'] = pd.Series(dtype="object")
        return final_df

    final_df['tooltip'] = final_df.apply(
        build_tooltip, labels=labels, color_map=color_scheme, axis=1)

    if enable_icons:
        final_df['icon'] = final_df.apply(
            build_icon, labels=labels, color_scheme=color_scheme, axis=1)

    return final_df


def build_df_to_bar_plot(df: pd.DataFrame, date_from: str, date_to: str, data_col: str,
                         category_order: list[str] = None) -> pd.DataFrame:
    df_copy = df.copy(deep=True)

    delta_time = 0

    if isinstance(date_from, str) and isinstance(date_to, str):
        delta_time = datetime.strptime(date_to[0:10], '%Y-%m-%d') - datetime.strptime(date_from[0:10], '%Y-%m-%d')
    else:
        delta_time = date_to - date_from

    delta_in_years = int(delta_time.days / 365.25)

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

    if offset_months == 3:
        df_copy['datetime'] = df_copy['datetime'].apply(
            transform_to_trimester)
    elif offset_months == 6:
        df_copy['datetime'] = df_copy['datetime'].apply(
            transform_to_semester)
    elif offset_years == 1:
        df_copy['datetime'] = df_copy['datetime'].apply(
            transform_to_year)

    df_copy['datetime'] = df_copy['datetime'].dt.to_period(
        graph_time_gap).dt.to_timestamp()

    data_col_percentage = build_percentage_df(df_copy, data_col)

    data_col_percentage['date_from'] = data_col_percentage['datetime'] - \
        pd.DateOffset(months=offset_months, years=offset_years)

    data_col_percentage.sort_values(by=['datetime', data_col], inplace=True)
    data_col_percentage['period_start'] = data_col_percentage['date_from'].dt.strftime('%Y-%m')
    data_col_percentage['period_end'] = data_col_percentage['datetime'].dt.strftime('%Y-%m')

    # The curated order the pathogen declares, restricted to what this selection actually
    # contains; anything unrecognised keeps its place at the end.
    if category_order:
        available = data_col_percentage[data_col].unique()
        ordered = ([value for value in category_order if value in available]
                   + [value for value in available if value not in category_order])
        data_col_percentage[data_col] = data_col_percentage[data_col].astype(
            'category').cat.reorder_categories(ordered, ordered=True)
    else:
        data_col_percentage[data_col] = data_col_percentage[data_col].astype('category')

    return data_col_percentage
