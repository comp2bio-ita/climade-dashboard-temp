import pandas as pd

from utils.functions.date_functions import slider_value_to_date
from utils.functions.filter_functions import apply_filters_to_df, filter_by_continents
from utils.functions.geo_functions import filter_by_search_input, region_values_for_basic_echo


# Resolve basic/advanced/reset widgets into one selection (virus-agnostic)

BASIC_FILTER = "basic"
ADVANCED_FILTER = "advanced"
RESET_FILTER = "reset"

# Unresolved classification; kept, sorted last for legends/map colours
UNASSIGNED = "Unassigned"


def selected_or_all(selected, available):
    # Empty/None = no restriction; always return a new list
    if not selected:
        return list(available)
    return list(selected)


def order_unassigned_last(values):
    named = [value for value in values if value != UNASSIGNED]
    if len(named) == len(values):
        return named
    return named + [UNASSIGNED]


def resolve_date_window(date_from, date_to, default_from, default_to):
    # Basic filter date pickers; fix unparsable/inverted pairs
    try:
        window_start = pd.to_datetime(date_from) if date_from else default_from
        window_end = pd.to_datetime(date_to) if date_to else default_to
    except (ValueError, TypeError):
        return default_from, default_to

    if window_start > window_end:
        return window_end, window_start
    return window_start, window_end


def resolve_slider_window(slider_range, default_from, default_to):
    # Advanced RangeSlider (days since Unix epoch)
    try:
        if not slider_range or len(slider_range) != 2:
            return default_from, default_to
        window_start = slider_value_to_date(slider_range[0])
        window_end = slider_value_to_date(slider_range[1])
    except (ValueError, TypeError, IndexError):
        return default_from, default_to

    if window_start > window_end:
        return window_end, window_start
    return window_start, window_end


def classify_filter_source(triggered_by, basic_apply_id, advanced_apply_id, reset_ids):
    # Unknown trigger → reset (full dataset)
    if triggered_by in reset_ids:
        return RESET_FILTER
    if triggered_by == advanced_apply_id:
        return ADVANCED_FILTER
    if triggered_by == basic_apply_id:
        return BASIC_FILTER
    return RESET_FILTER


def resolve_filter_selection(source, basic_widgets, advanced_widgets, available):
    if source == ADVANCED_FILTER:
        window_start, window_end = resolve_slider_window(
            advanced_widgets.get("date_slider"), available["date_from"], available["date_to"]
        )
        classifications = selected_or_all(
            advanced_widgets.get("classifications"), available["classifications"])
        subclassifications = selected_or_all(
            advanced_widgets.get("subclassifications"), available["subclassifications"])
        countries = selected_or_all(advanced_widgets.get("countries"), available["countries"])
        continents = selected_or_all(advanced_widgets.get("continents"), available["continents"])
        hosts = selected_or_all(advanced_widgets.get("hosts"), available["hosts"])
        search_regions = region_values_for_basic_echo(
            countries, continents, available["countries"], available["continents"])

    elif source == BASIC_FILTER:
        window_start, window_end = resolve_date_window(
            basic_widgets.get("date_from"), basic_widgets.get("date_to"),
            available["date_from"], available["date_to"]
        )
        classifications = selected_or_all(
            basic_widgets.get("classifications"), available["classifications"])
        # Basic has no genotype/host controls — leave both open
        subclassifications = list(available["subclassifications"])
        hosts = list(available["hosts"])

        search_regions = basic_widgets.get("search_regions") or []
        countries, continents = filter_by_search_input(
            search_regions, available["countries"], available["continents"])
        countries = list(countries)
        continents = list(continents)

    else:
        window_start = available["date_from"]
        window_end = available["date_to"]
        classifications = list(available["classifications"])
        subclassifications = list(available["subclassifications"])
        countries = list(available["countries"])
        continents = list(available["continents"])
        hosts = list(available["hosts"])
        search_regions = []

    return {
        "source": source,
        "date_from": window_start,
        "date_to": window_end,
        "classifications": order_unassigned_last(classifications),
        "subclassifications": order_unassigned_last(subclassifications),
        "countries": countries,
        "continents": continents,
        "hosts": hosts,
        "search_regions": search_regions,
    }


def apply_selection_fields(sequences_df, selection, classification_column="serotype"):
    # Continent omitted here (on geojson) — see apply_selection_to_sequences
    if classification_column == "serotype":
        serotypes = selection["classifications"]
        genotypes = selection["subclassifications"]
    else:
        serotypes = None
        genotypes = selection["classifications"]

    return apply_filters_to_df(
        df=sequences_df,
        date_from=selection["date_from"],
        date_to=selection["date_to"],
        serotypes=serotypes,
        genotypes=genotypes,
        countries=selection["countries"],
        hosts=selection["hosts"],
    )


def apply_selection_to_sequences(sequences_df, selection, geojson_df,
                                 classification_column="serotype"):
    # Full restriction including continent (joined from geojson)
    filtered = apply_selection_fields(sequences_df, selection, classification_column)
    return filter_by_continents(filtered, selection["continents"], geojson_df)


def canonical_accession_ids(accession_values):
    unique_accessions = set()
    for value in accession_values:
        if pd.isna(value):
            continue
        accession_id = str(value).strip()
        if accession_id:
            unique_accessions.add(accession_id)
    return sorted(unique_accessions)


def selection_to_dict(selection):
    # dcc.Store needs ISO dates (JSON)
    stored = dict(selection)
    stored["date_from"] = pd.to_datetime(selection["date_from"]).strftime("%Y-%m-%d")
    stored["date_to"] = pd.to_datetime(selection["date_to"]).strftime("%Y-%m-%d")
    return stored


def selection_from_dict(stored):
    selection = dict(stored)
    selection["date_from"] = pd.to_datetime(stored["date_from"])
    selection["date_to"] = pd.to_datetime(stored["date_to"])
    return selection
