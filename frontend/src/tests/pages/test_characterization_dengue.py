"""What src/pages/dengue_page.py does today.

Dengue is the reference implementation for behavior shared across the three pathogen pages,
so most of these assertions describe the target state rather than a defect. They exist to
prove the structural extraction in Phase C does not change dengue.

Callback under test: dengue_page.update_view (dengue_page.py:1017), a plain function invoked
directly. It resolves its filter through utils.functions.selection_functions rather than an
inline branch (dengue_page.py:1031-1051).
"""

import pytest

from conftest import download_header, download_row_count, triggered_by

# Return positions, in the order of the decorator's Output list (dengue_page.py:969-991)
MAP, BAR, SEROTYPES, COUNTRIES, CONTINENTS = 0, 1, 2, 3, 4
N_SEQUENCES, N_COUNTRIES, HOSTS, N_HOSTS, AREA = 5, 6, 7, 8, 9
BAR_TITLE, AREA_TITLE = 10, 11
BASIC_SEROTYPES, BASIC_NAMES, BASIC_START, BASIC_END = 12, 13, 14, 15
DOWNLOAD, APPLIED_SELECTION = 16, 17


def run_dengue(page, trigger, *, serotypes=None, genotypes=None, countries=None,
               continents=None, hosts=None, date_from="2015-01-01", date_to="2021-01-01",
               basic_serotypes=None, names_input=None, slider=None):
    from utils.functions.date_functions import date_to_slider_value

    default_slider = [date_to_slider_value(page.MIN_DF_DATE),
                      date_to_slider_value(page.MAX_DF_DATE)]
    with triggered_by(trigger):
        return page.update_view(
            1, 1, 1, 1,
            slider if slider is not None else default_slider,
            serotypes if serotypes is not None else ["DENV1"],
            genotypes if genotypes is not None else ["1I"],
            countries if countries is not None else ["Brazil"],
            continents if continents is not None else ["South America"],
            hosts if hosts is not None else ["Homo sapiens"],
            date_from, date_to,
            basic_serotypes if basic_serotypes is not None else ["DENV1"],
            names_input if names_input is not None else [],
        )


@pytest.fixture
def dengue_page(pathogen_pages):
    return pathogen_pages["dengue"]


class TestResetPath:
    def test_reset_restores_every_classification(self, dengue_page):
        result = run_dengue(dengue_page, "reset-filters-button-denv")
        assert result[SEROTYPES] == ["DENV1", "DENV2", "DENV3", "Unassigned"]

    def test_reset_opens_the_upper_date_bound_to_today(self, dengue_page):
        # dengue_filter_vocabulary sets date_to from today_in_dashboard_timezone()
        # (dengue_page.py:167), not MAX_DF_DATE. Chikungunya and zika reset to MAX_DF_DATE;
        # tasks B4/B5 bring them onto this behavior.
        from utils.functions.date_functions import today_in_dashboard_timezone

        result = run_dengue(dengue_page, "reset-filters-button-denv")
        assert result[BASIC_START] == dengue_page.MIN_DF_DATE.date()
        assert result[BASIC_END] == today_in_dashboard_timezone().date()

    def test_reset_clears_the_region_search_box(self, dengue_page):
        # resolve_filter_selection returns search_regions=[] on reset
        # (selection_functions.py:110), so this needs no separate branch
        result = run_dengue(dengue_page, "reset-filters-button-denv", names_input=["Brazil"])
        assert result[BASIC_NAMES] == []


class TestBasicFilterPath:
    def test_basic_filter_narrows_to_the_selected_classification(self, dengue_page):
        result = run_dengue(dengue_page, "filter-button-denv", basic_serotypes=["DENV1"])
        assert result[SEROTYPES] == ["DENV1"]

    def test_basic_filter_echoes_the_typed_dates_back(self, dengue_page):
        import datetime

        result = run_dengue(dengue_page, "filter-button-denv",
                            date_from="2015-01-01", date_to="2021-01-01")
        assert result[BASIC_START] == datetime.date(2015, 1, 1)
        assert result[BASIC_END] == datetime.date(2021, 1, 1)


class TestAdvancedFilterPath:
    def test_advanced_slider_is_absolute_days_since_the_unix_epoch(self, dengue_page):
        # dengue_page.py:654-660 with date_to_slider_value/slider_value_to_date. Chikungunya
        # and zika use an offset from MIN_DF_DATE instead; tasks B4/B5 change that.
        import datetime

        from utils.functions.date_functions import date_to_slider_value

        target = datetime.date(2018, 1, 1)
        result = run_dengue(dengue_page, "apply-filters-modal-btn-denv",
                            slider=[date_to_slider_value(dengue_page.MIN_DF_DATE),
                                    date_to_slider_value(target)])
        assert result[BASIC_END] == target

    def test_advanced_filter_applies_the_host_selection(self, dengue_page):
        result = run_dengue(dengue_page, "apply-filters-modal-btn-denv",
                            hosts=["Homo sapiens"])
        assert result[HOSTS] == ["Homo sapiens"]

    def test_advanced_filter_echoes_geo_to_basic_region_search(self, dengue_page):
        result = run_dengue(dengue_page, "apply-filters-modal-btn-denv", countries=["Brazil"])
        assert result[BASIC_NAMES] == ["Brazil"]


class TestUnknownTrigger:
    def test_an_unrecognised_trigger_behaves_like_reset(self, dengue_page):
        # classify_filter_source falls through to RESET (selection_functions.py:68)
        unknown = run_dengue(dengue_page, None)
        reset = run_dengue(dengue_page, "reset-filters-button-denv")
        assert unknown[SEROTYPES] == reset[SEROTYPES]
        assert unknown[N_SEQUENCES] == reset[N_SEQUENCES]


class TestCountsAreTheReference:
    def test_sequence_count_counts_the_filtered_rows(self, dengue_page):
        # dengue_page.py:1118. This is the semantics tasks B1 propagates to the other two.
        result = run_dengue(dengue_page, "reset-filters-button-denv")
        assert result[N_SEQUENCES] == 4
        assert isinstance(result[N_SEQUENCES], int)

    def test_host_count_counts_hosts_present_in_the_filtered_data(self, dengue_page):
        # dengue_page.py:1120. A basic filter matching one sequence reports one host, where
        # chikungunya and zika would report the whole host vocabulary.
        result = run_dengue(dengue_page, "filter-button-denv", basic_serotypes=["DENV1"])
        assert result[N_HOSTS] == 1


class TestClassificationAxes:
    def test_titles_track_serotypes_when_several_are_selected(self, dengue_page):
        result = run_dengue(dengue_page, "reset-filters-button-denv")
        assert result[BAR_TITLE] == "Circulating Serotypes"
        assert result[AREA_TITLE] == "Temporal Spread of Serotypes"

    def test_titles_switch_to_genotypes_when_one_serotype_is_selected(self, dengue_page):
        # dengue_page.py:1068-1071 switches the colour axis at <=1 selected serotype.
        # Genuine dengue behavior: chikungunya and zika have no second classification axis.
        result = run_dengue(dengue_page, "filter-button-denv", basic_serotypes=["DENV1"])
        assert result[BAR_TITLE] == "Circulating Genotypes"
        assert result[AREA_TITLE] == "Temporal Spread of Genotypes"

    def test_genotypes_are_derived_from_the_selected_serotypes(self, dengue_page):
        # update_genotype_filter (dengue_page.py:951) matches the trailing serotype digit
        assert dengue_page.update_genotype_filter(["DENV1"]) == [["1I"]]
        assert dengue_page.update_genotype_filter([]) == [[]]


class TestAppliedSelectionStore:
    def test_the_store_records_the_resolved_selection(self, dengue_page):
        # dengue_page.py:1167 writes selection_to_dict; the phylo pre-check and job submission
        # read it back (dengue_page.py:1316, :1441). No equivalent exists on the other pages.
        result = run_dengue(dengue_page, "filter-button-denv", basic_serotypes=["DENV1"])
        selection = result[APPLIED_SELECTION]
        assert selection["source"] == "basic"
        assert selection["classifications"] == ["DENV1"]
        assert selection["date_from"] == "2015-01-01"
        assert selection["date_to"] == "2021-01-01"

    def test_the_store_marks_reset_as_its_own_source(self, dengue_page):
        result = run_dengue(dengue_page, "reset-filters-button-denv")
        assert result[APPLIED_SELECTION]["source"] == "reset"


class TestDownloadPayload:
    def test_download_exports_ten_columns_including_lineages(self, dengue_page):
        # dengue_page.py:1081. major_lineage/minor_lineage are dengue-only data; the other
        # two pages export six columns.
        result = run_dengue(dengue_page, "reset-filters-button-denv")
        assert download_header(result[DOWNLOAD]) == [
            "genbank_sequence_data_id", "collection_date", "serotype", "genotype",
            "major_lineage", "minor_lineage", "country", "country_acr", "location", "host",
        ]

    def test_download_carries_the_filtered_rows(self, dengue_page):
        result = run_dengue(dengue_page, "reset-filters-button-denv")
        assert download_row_count(result[DOWNLOAD]) == 4


class TestEmptySelectionIsHandled:
    def test_a_selection_matching_no_sequence_renders_instead_of_raising(self, dengue_page):
        # dengue_script.py:83-85 and :97-101 guard this. The same selection shape raises on
        # chikungunya and zika until tasks B4/B5 port the guard.
        result = run_dengue(dengue_page, "filter-button-denv", basic_serotypes=["DENV1"],
                            date_from="2016-01-01", date_to="2017-01-01")
        assert result[N_SEQUENCES] == 0
        assert len(result[BAR].data) == 0
