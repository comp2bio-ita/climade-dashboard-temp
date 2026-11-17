#pip install pycountry

import pycountry

aditional_countries_iso = {  # these are  not covered in pycountry? (double check)
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