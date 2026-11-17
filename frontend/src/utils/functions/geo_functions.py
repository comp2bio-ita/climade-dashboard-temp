# Utils functions
import pycountry
import pandas as pd
import json

aditional_countries_iso = {
    'USA': 'USA',
    'Russia': 'RUS',
    'Taiwan': 'TWN',
    'Venezuela': 'VEN',
    'South Korea': 'KOR',
    'Micronesia': 'FSM',
    'Virgin Islands': 'VIR',
    'Laos': 'LAO',
    'Republic of the Congo': 'COG',
    'Bolivia': 'BOL',
    'Saint Martin': 'MAF',
    'Democratic Republic of the Congo': 'COD',
    'St. Lucia': 'LCA',
    'Reunion': 'REU',
    'Iran': 'IRN',
    'British Virgin Islands': 'VGB',
    'Tanzania': 'TZA',
    'St. Vincent and the Grenadines': 'VCT',
    'Brunei': 'BRN',
    'Saint Barthelemy': 'BLM',
    'Cote d\'Ivoire': 'CIV'
}

CONTINENTS_NAMES_LIST = [
    "Africa",
    "Asia",
    "Central America",
    "Europe",
    "North America",
    "Oceania",
    "South America",
]

geojson_props_of_interest = [
    "name_en",
    "iso_a3",
    "continent",
    "region_un",
    "subregion",
    "label_x",
    "label_y"
]

geojson_id_property = "id"

geojson_geometry_property = "geometry"


def convert_country_util(x):
    country_name = str(x).strip()

    query_country = None

    try:
        if aditional_countries_iso[country_name]:
            query_country = aditional_countries_iso[country_name]
    except:
        query_country = None

    if query_country:
        return query_country
    else:
        try:
            query_country = [pycountry.countries.get(name=country_name)]
        except:
            try:
                query_country = list(
                    pycountry.countries.search_fuzzy(country_name))
            except:
                query_country = None
        if query_country != None and query_country[0] != None:
            return query_country[0].alpha_3
        return None


def country_to_ISO(df, column, new_iso_column_name):
    df[new_iso_column_name] = df[column].apply(convert_country_util)
    return


def _first_comma_segment(text):
    if "," in text:
        return text.split(",")[0].strip()
    return text


def _last_comma_segment(text):
    if "," in text:
        return text.split(",")[-1].strip()
    return text


def locality_from_ncbi(location):
    """Finest geographic label from an NCBI colon-separated location string."""
    if not location:
        return None
    parts = [part.strip() for part in str(location).split(":") if part.strip()]
    if not parts:
        return None
    if len(parts) >= 3:
        return _last_comma_segment(parts[2])
    if len(parts) >= 2:
        return _last_comma_segment(parts[1])
    return _first_comma_segment(parts[0])


def division_from_ncbi(location):
    """State or province from an NCBI colon-separated location string."""
    if not location:
        return None
    parts = [part.strip() for part in str(location).split(":") if part.strip()]
    if len(parts) >= 2:
        return _first_comma_segment(parts[1])
    return None


def filter_by_search_input(selected_regions, all_countries, all_continents):
    # Resolve the basic-filter region search (a single dropdown mixing countries and continents)
    # into a (countries, continents) pair. Virus-agnostic: it only reasons over the supplied
    # country/continent vocabularies. Selecting only countries leaves continents wide open (and
    # vice versa) so the two axes never narrow each other.
    if not selected_regions:
        return all_countries, all_continents

    filtered_countries = []
    filtered_continents = []
    for region in selected_regions:
        if region in all_countries:
            filtered_countries.append(region)
        if region in all_continents:
            filtered_continents.append(region)

    if not filtered_countries and not filtered_continents:
        return all_countries, all_continents
    if filtered_countries and not filtered_continents:
        filtered_continents = all_continents
    if filtered_continents and not filtered_countries:
        filtered_countries = all_countries
    return filtered_countries, filtered_continents


def region_values_for_basic_echo(countries, continents, all_countries, all_continents):
    # Inverse of filter_by_search_input for the basic region dropdown: map resolved geo subsets
    # back to valid option values. Full vocabulary on both axes means no active region filter.
    if set(countries) == set(all_countries) and set(continents) == set(all_continents):
        return []
    echo = []
    if set(countries) != set(all_countries):
        echo.extend(country for country in countries if country in all_countries)
    if set(continents) != set(all_continents):
        echo.extend(continent for continent in continents if continent in all_continents)
    return echo


def attach_continent(df, geojson_df, iso_column="iso_a3"):
    # Continent lives on the geojson, not the sequence frame; join it on iso_a3 (the same key
    # build_df_to_map uses). Deduplicate so a sequence row never fans out into several.
    if "continent" in df.columns:
        return df
    continent_by_iso = geojson_df[[iso_column, "continent"]].drop_duplicates(iso_column)
    return df.merge(continent_by_iso, on=iso_column, how="left")


def read_geojson(path: str) -> any:
    return json.load(open(path, "r", encoding="utf8"))


def geojson_to_df(
    geojson_dict: dict,
    props_of_interest: list[str],
    geometry_prop: str = "geometry",
    id_prop: str = None
) -> pd.DataFrame:

    filtered_geojson = []

    for feature in geojson_dict['features']:

        properties = feature['properties']

        entry_dict = {prop: properties[prop] for prop in props_of_interest}
        entry_dict[geometry_prop] = json.dumps(feature[geometry_prop])
        entry_dict[id_prop] = feature[id_prop]

        filtered_geojson.append(dict(entry_dict))
    return pd.DataFrame(filtered_geojson)


def df_to_geojson(df: pd.DataFrame, column_to_props: list[str], geometry_column: str, id_column: str) -> dict:

    df_dict = df.to_dict(orient='records')

    converted_dict = dict(
        type="FeatureCollection",
        features=list([])
    )

    for record in df_dict:

        converted_dict['features'].append(
            dict(
                type="Feature",
                id=record[id_column],
                geometry=json.loads(record[geometry_column]),
                properties=dict({prop: record[prop]
                                for prop in column_to_props})
            )
        )
    return converted_dict
