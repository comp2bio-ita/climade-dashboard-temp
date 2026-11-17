from utils.functions.geo_functions import (
    division_from_ncbi,
    filter_by_search_input,
    locality_from_ncbi,
    region_values_for_basic_echo,
)

ALL_COUNTRIES = ["Brazil", "Kenya", "Thailand"]
ALL_CONTINENTS = ["Africa", "Asia", "South America"]


class TestLocalityFromNcbi:
    def test_three_part_location_returns_municipality(self):
        assert locality_from_ncbi("Brazil: Sao Paulo: Campinas") == "Campinas"

    def test_two_part_location_returns_state(self):
        assert locality_from_ncbi("Brazil: Sao Paulo") == "Sao Paulo"

    def test_one_part_location_returns_country(self):
        assert locality_from_ncbi("Brazil") == "Brazil"

    def test_empty_string_returns_none(self):
        assert locality_from_ncbi("") is None

    def test_none_returns_none(self):
        assert locality_from_ncbi(None) is None

    def test_whitespace_around_parts_is_stripped(self):
        assert locality_from_ncbi(" Brazil : Sao Paulo : Campinas ") == "Campinas"

    def test_empty_segments_are_ignored(self):
        assert locality_from_ncbi("Brazil::Campinas") == "Campinas"

    def test_comma_in_division_segment_returns_city(self):
        assert locality_from_ncbi("Brazil: Sao Paulo, Piracicaba") == "Piracicaba"

    def test_comma_in_two_part_location_returns_city(self):
        assert locality_from_ncbi("Brazil: Acre, Rio Branco") == "Rio Branco"

    def test_comma_in_locality_segment_returns_last_part(self):
        assert locality_from_ncbi("Brazil: Sao Paulo: Campinas, SP") == "SP"


class TestDivisionFromNcbi:
    def test_three_part_location_returns_state(self):
        assert division_from_ncbi("Brazil: Sao Paulo: Campinas") == "Sao Paulo"

    def test_two_part_location_returns_state(self):
        assert division_from_ncbi("Brazil: Sao Paulo") == "Sao Paulo"

    def test_two_part_us_location_returns_state_code(self):
        assert division_from_ncbi("USA: FL") == "FL"

    def test_one_part_location_returns_none(self):
        assert division_from_ncbi("Brazil") is None

    def test_empty_string_returns_none(self):
        assert division_from_ncbi("") is None

    def test_none_returns_none(self):
        assert division_from_ncbi(None) is None

    def test_whitespace_around_parts_is_stripped(self):
        assert division_from_ncbi(" Brazil : Sao Paulo : Campinas ") == "Sao Paulo"

    def test_comma_in_division_segment_returns_state(self):
        assert division_from_ncbi("Brazil: Sao Paulo, Piracicaba") == "Sao Paulo"

    def test_comma_in_two_part_location_returns_state(self):
        assert division_from_ncbi("Brazil: Acre, Rio Branco") == "Acre"

    def test_whitespace_around_comma_parts_is_stripped(self):
        assert division_from_ncbi("Brazil:  Sao Paulo , Piracicaba") == "Sao Paulo"


class TestRegionValuesForBasicEcho:

    def test_unrestricted_geo_returns_empty_echo(self):
        assert region_values_for_basic_echo(
            ALL_COUNTRIES, ALL_CONTINENTS, ALL_COUNTRIES, ALL_CONTINENTS) == []

    def test_country_subset_echoes_country_values(self):
        assert region_values_for_basic_echo(
            ["Brazil"], ALL_CONTINENTS, ALL_COUNTRIES, ALL_CONTINENTS) == ["Brazil"]

    def test_continent_subset_echoes_continent_values(self):
        assert region_values_for_basic_echo(
            ALL_COUNTRIES, ["Africa"], ALL_COUNTRIES, ALL_CONTINENTS) == ["Africa"]

    def test_both_axes_narrowed_echoes_countries_then_continents(self):
        assert region_values_for_basic_echo(
            ["Brazil"], ["South America"], ALL_COUNTRIES, ALL_CONTINENTS) == [
                "Brazil", "South America"]

    def test_country_echo_round_trips_through_search_input(self):
        countries = ["Brazil"]
        continents = ALL_CONTINENTS
        echo = region_values_for_basic_echo(
            countries, continents, ALL_COUNTRIES, ALL_CONTINENTS)
        round_countries, round_continents = filter_by_search_input(
            echo, ALL_COUNTRIES, ALL_CONTINENTS)
        assert set(round_countries) == set(countries)
        assert set(round_continents) == set(continents)

    def test_continent_echo_round_trips_through_search_input(self):
        countries = ALL_COUNTRIES
        continents = ["Africa"]
        echo = region_values_for_basic_echo(
            countries, continents, ALL_COUNTRIES, ALL_CONTINENTS)
        round_countries, round_continents = filter_by_search_input(
            echo, ALL_COUNTRIES, ALL_CONTINENTS)
        assert set(round_countries) == set(countries)
        assert set(round_continents) == set(continents)
