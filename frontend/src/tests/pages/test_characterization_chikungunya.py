"""What src/pages/chikungunya_page.py does today.

Characterization only: these assertions describe current behavior, including behavior that is
known to be wrong. Each such case names the task that changes it. Tasks B1/B4 are expected to
change some of these values, deliberately.

Callback under test: chikungunya_page.update_map (chikungunya_page.py:724), a plain function
invoked directly. It branches on ctx.triggered_id (chikungunya_page.py:770).
"""

import pytest

from conftest import download_header, download_row_count, triggered_by

# Return positions, in the order of the shared Output list (pathogen_dashboard._main_outputs).
# Only these constants moved when the page adopted the shared core; every assertion below is
# unchanged. The shared contract adds the two chart titles and the applied-selection store.
MAP, BAR, GENOTYPES, COUNTRIES, CONTINENTS = 0, 1, 2, 3, 4
N_SEQUENCES, N_COUNTRIES, HOSTS, N_HOSTS, AREA = 5, 6, 7, 8, 9
BAR_TITLE, AREA_TITLE = 10, 11
BASIC_GENOTYPES, BASIC_NAMES, BASIC_START, BASIC_END = 12, 13, 14, 15
DOWNLOAD, APPLIED_SELECTION = 16, 17


def run_chikungunya(page, trigger, *, genotypes=None, countries=None, continents=None,
                    hosts=None, date_from="2015-01-01", date_to="2021-01-01",
                    basic_genotypes=None, names_input=None, slider=None):
    # Positional order follows the handler signature; its parameter names disagree with the
    # decorator's Input order, which is harmless because the body reads ctx.triggered_id
    # rather than these four values.
    from utils.functions.date_functions import date_to_slider_value, today_in_dashboard_timezone

    full_window = [date_to_slider_value(page.MIN_DF_DATE),
                   date_to_slider_value(today_in_dashboard_timezone())]
    with triggered_by(trigger):
        return page.update_map(
            1, 1, 1, 1,
            slider if slider is not None else full_window,
            genotypes if genotypes is not None else ["ECSA"],
            countries if countries is not None else ["Brazil"],
            continents if continents is not None else ["South America"],
            hosts if hosts is not None else ["Homo sapiens"],
            date_from, date_to,
            basic_genotypes if basic_genotypes is not None else ["ECSA"],
            names_input if names_input is not None else [],
        )


@pytest.fixture
def chikungunya_page(pathogen_pages):
    return pathogen_pages["chikungunya"]


class TestResetPath:
    def test_reset_restores_every_classification(self, chikungunya_page):
        result = run_chikungunya(chikungunya_page, "reset-filters-button-chikv")
        assert result[GENOTYPES] == ["ACL", "ECSA", "WA", "Unassigned"]

    def test_reset_opens_the_upper_date_bound_to_today(self, chikungunya_page):
        # Task B4: chikungunya_filter_vocabulary sets date_to from
        # today_in_dashboard_timezone(), matching dengue. It used to reset to MAX_DF_DATE.
        from utils.functions.date_functions import today_in_dashboard_timezone

        result = run_chikungunya(chikungunya_page, "reset-filters-button-chikv")
        assert result[BASIC_START] == chikungunya_page.MIN_DF_DATE.date()
        assert result[BASIC_END] == today_in_dashboard_timezone().date()

    def test_reset_clears_the_region_search_box(self, chikungunya_page):
        # chikungunya_page.py:943 tests this page's own button ids, so the branch runs and
        # blanks the search box. The identical block on zika tests chikungunya's ids
        # (zika_page.py:918) and therefore never fires — see the zika characterization.
        result = run_chikungunya(chikungunya_page, "reset-filters-button-chikv",
                                 names_input=["Brazil"])
        assert result[BASIC_NAMES] == []


class TestBasicFilterPath:
    def test_basic_filter_narrows_to_the_selected_classification(self, chikungunya_page):
        result = run_chikungunya(chikungunya_page, "filter-button-chikv",
                                 basic_genotypes=["ECSA"])
        assert result[GENOTYPES] == ["ECSA"]

    def test_basic_filter_echoes_the_typed_dates_back(self, chikungunya_page):
        import datetime

        result = run_chikungunya(chikungunya_page, "filter-button-chikv",
                                 date_from="2015-01-01", date_to="2021-01-01")
        assert result[BASIC_START] == datetime.date(2015, 1, 1)
        assert result[BASIC_END] == datetime.date(2021, 1, 1)

    def test_basic_filter_leaves_hosts_wide_open(self, chikungunya_page):
        result = run_chikungunya(chikungunya_page, "filter-button-chikv",
                                 basic_genotypes=["ECSA"])
        assert result[HOSTS] == chikungunya_page.ALL_HOSTS


class TestAdvancedFilterPath:
    def test_advanced_filter_applies_the_host_selection(self, chikungunya_page):
        result = run_chikungunya(chikungunya_page, "apply-filters-modal-btn-chikv",
                                 hosts=["Homo sapiens"])
        assert result[HOSTS] == ["Homo sapiens"]
        assert result[N_HOSTS] == 1

    def test_advanced_slider_is_absolute_days_since_the_unix_epoch(self, chikungunya_page):
        # Task B4: was an offset in days from MIN_DF_DATE with step=30; now matches dengue's
        # day-resolution slider so a typed date round-trips through it exactly.
        import datetime

        from utils.functions.date_functions import date_to_slider_value

        target = datetime.date(2018, 1, 1)
        result = run_chikungunya(
            chikungunya_page, "apply-filters-modal-btn-chikv",
            slider=[date_to_slider_value(chikungunya_page.MIN_DF_DATE),
                    date_to_slider_value(target)])
        assert result[BASIC_END] == target


class TestUnknownTrigger:
    def test_an_unrecognised_trigger_behaves_like_reset(self, chikungunya_page):
        unknown = run_chikungunya(chikungunya_page, None)
        reset = run_chikungunya(chikungunya_page, "reset-filters-button-chikv")
        assert unknown[GENOTYPES] == reset[GENOTYPES]
        assert unknown[N_SEQUENCES] == reset[N_SEQUENCES]


class TestCounts:
    # Normalized by task B1 to dengue's semantics: both cards are computed from
    # filtered_sequences, the continent-filtered row frame that also feeds the download.

    def test_sequence_count_counts_the_filtered_rows(self, chikungunya_page):
        result = run_chikungunya(chikungunya_page, "reset-filters-button-chikv")
        assert result[N_SEQUENCES] == 4
        assert isinstance(result[N_SEQUENCES], int)

    def test_host_count_counts_hosts_present_in_the_filtered_data(self, chikungunya_page):
        # Was len(selected_hosts) == 2 before B1, i.e. the whole host vocabulary regardless
        # of the filter. Only one sequence matches, carrying one host.
        result = run_chikungunya(chikungunya_page, "filter-button-chikv",
                                 basic_genotypes=["ECSA"])
        assert result[N_HOSTS] == 1


class TestDatasetShape:
    def test_undated_sequences_are_dropped_at_import(self, chikungunya_page):
        # chikungunya_page.py:50 passes ['country', 'collection_date'], like dengue:79.
        # Zika does not — see the zika characterization.
        assert not chikungunya_page.df_world_chikungunya["collection_date"].isna().any()


class TestDownloadPayload:
    def test_download_exports_seven_columns(self, chikungunya_page):
        result = run_chikungunya(chikungunya_page, "reset-filters-button-chikv")
        assert download_header(result[DOWNLOAD]) == [
            "genbank_sequence_data_id", "collection_date", "genotype",
            "host", "country", "country_acr", "location",
        ]

    def test_download_carries_the_filtered_rows(self, chikungunya_page):
        result = run_chikungunya(chikungunya_page, "reset-filters-button-chikv")
        assert download_row_count(result[DOWNLOAD]) == 4


class TestFigures:
    def test_one_trace_per_selected_classification(self, chikungunya_page):
        reset = run_chikungunya(chikungunya_page, "reset-filters-button-chikv")
        assert len(reset[BAR].data) == 4
        narrow = run_chikungunya(chikungunya_page, "filter-button-chikv",
                                 basic_genotypes=["ECSA"])
        assert len(narrow[BAR].data) == 1

    def test_chart_titles_are_driven_by_the_callback(self, chikungunya_page):
        # The shared core writes the titles on every page. The text is what this page always
        # showed; before the migration these were static children under an id duplicated
        # across all three pages.
        result = run_chikungunya(chikungunya_page, "reset-filters-button-chikv")
        assert result[BAR_TITLE] == "Circulating Genotypes"
        assert result[AREA_TITLE] == "Temporal Spread of Genotypes"


class TestEmptySelectionIsHandled:
    def test_a_selection_matching_no_sequence_renders_instead_of_raising(self, chikungunya_page):
        # Task B4 ported dengue's two guards (dengue_script.py:83-85 and :97-101) into
        # chikungunya_script and started passing the date window to the charts explicitly,
        # so an empty frame no longer has to supply its own min/max.
        result = run_chikungunya(chikungunya_page, "filter-button-chikv",
                                 basic_genotypes=["ECSA"],
                                 date_from="2016-01-01", date_to="2019-01-01")
        assert result[N_SEQUENCES] == 0
        assert len(result[BAR].data) == 0
