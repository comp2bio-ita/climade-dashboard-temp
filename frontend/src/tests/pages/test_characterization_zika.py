"""What src/pages/zika_page.py does today.

Characterization only: these assertions describe current behavior, including behavior that is
known to be wrong. Each such case names the task that changes it. Tasks B1/B2/B5 are expected
to change some of these values, deliberately.

Callback under test: zika_page.update_map (zika_page.py:713), a plain function invoked
directly. It branches on ctx.triggered_id (zika_page.py:758), so the trigger selects the path.
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


def run_zika(zika_page, trigger, *, genotypes=None, countries=None, continents=None,
             hosts=None, date_from="2015-01-01", date_to="2021-01-01",
             basic_genotypes=None, names_input=None, slider=None):
    # Positional order follows the handler signature. Its parameter names disagree with the
    # decorator's Input order, which is harmless because the body reads ctx.triggered_id
    # rather than these four values.
    from utils.functions.date_functions import date_to_slider_value, today_in_dashboard_timezone

    full_window = [date_to_slider_value(zika_page.MIN_DF_DATE),
                   date_to_slider_value(today_in_dashboard_timezone())]
    with triggered_by(trigger):
        return zika_page.update_map(
            1, 1, 1, 1,
            slider if slider is not None else full_window,
            genotypes if genotypes is not None else ["Asian"],
            countries if countries is not None else ["Brazil"],
            continents if continents is not None else ["South America"],
            hosts if hosts is not None else ["Homo sapiens"],
            date_from, date_to,
            basic_genotypes if basic_genotypes is not None else ["Asian"],
            names_input if names_input is not None else [],
        )


@pytest.fixture
def zika_page(pathogen_pages):
    return pathogen_pages["zika"]


class TestResetPath:
    def test_reset_restores_every_classification(self, zika_page):
        result = run_zika(zika_page, "reset-filters-button-zikv")
        assert result[GENOTYPES] == ["African", "Asian", "Unassigned"]

    def test_reset_opens_the_upper_date_bound_to_today(self, zika_page):
        # Task B5: zika_filter_vocabulary sets date_to from today_in_dashboard_timezone(),
        # matching dengue. It used to reset to MAX_DF_DATE.
        from utils.functions.date_functions import today_in_dashboard_timezone

        result = run_zika(zika_page, "reset-filters-button-zikv")
        assert result[BASIC_START] == zika_page.MIN_DF_DATE.date()
        assert result[BASIC_END] == today_in_dashboard_timezone().date()

    def test_reset_restores_every_host_and_continent(self, zika_page):
        result = run_zika(zika_page, "reset-filters-button-zikv")
        assert result[HOSTS] == zika_page.ALL_HOSTS
        assert result[CONTINENTS] == zika_page.ALL_CONTINENTS_NAMES

    def test_reset_clears_the_region_search_box(self, zika_page):
        # Task B3: the branch used to test chikungunya's button ids, so it never ran on zika
        # and the search box kept its text. Now matches chikungunya and dengue.
        result = run_zika(zika_page, "reset-filters-button-zikv", names_input=["Brazil"])
        assert result[BASIC_NAMES] == []


class TestBasicFilterPath:
    def test_basic_filter_narrows_to_the_selected_classification(self, zika_page):
        result = run_zika(zika_page, "filter-button-zikv", basic_genotypes=["Asian"])
        assert result[GENOTYPES] == ["Asian"]

    def test_basic_filter_echoes_the_typed_dates_back(self, zika_page):
        import datetime

        result = run_zika(zika_page, "filter-button-zikv",
                          date_from="2016-01-01", date_to="2019-01-01")
        assert result[BASIC_START] == datetime.date(2016, 1, 1)
        assert result[BASIC_END] == datetime.date(2019, 1, 1)

    def test_basic_filter_leaves_hosts_wide_open(self, zika_page):
        # The basic bar has no host control (zika_page.py:823), so every host stays selected
        result = run_zika(zika_page, "filter-button-zikv", basic_genotypes=["Asian"])
        assert result[HOSTS] == zika_page.ALL_HOSTS


class TestAdvancedFilterPath:
    def test_advanced_filter_applies_the_host_selection(self, zika_page):
        result = run_zika(zika_page, "apply-filters-modal-btn-zikv", hosts=["Homo sapiens"])
        assert result[HOSTS] == ["Homo sapiens"]
        assert result[N_HOSTS] == 1

    def test_advanced_filter_applies_the_continent_selection(self, zika_page):
        vocabulary = zika_page.page_data()["vocabulary"]()
        result = run_zika(
            zika_page, "apply-filters-modal-btn-zikv",
            countries=vocabulary["countries"],
            continents=["South America"],
        )
        assert result[CONTINENTS] == ["South America"]
        assert result[BASIC_NAMES] == ["South America"]

    def test_advanced_slider_is_absolute_days_since_the_unix_epoch(self, zika_page):
        # Task B5: was an offset in days from MIN_DF_DATE with step=30; now matches dengue's
        # day-resolution slider so a typed date round-trips through it exactly.
        import datetime

        from utils.functions.date_functions import date_to_slider_value

        target = datetime.date(2018, 1, 1)
        result = run_zika(
            zika_page, "apply-filters-modal-btn-zikv",
            slider=[date_to_slider_value(zika_page.MIN_DF_DATE),
                    date_to_slider_value(target)])
        assert result[BASIC_END] == target


class TestUnknownTrigger:
    def test_an_unrecognised_trigger_behaves_like_reset(self, zika_page):
        unknown = run_zika(zika_page, None)
        reset = run_zika(zika_page, "reset-filters-button-zikv")
        assert unknown[GENOTYPES] == reset[GENOTYPES]
        assert unknown[N_SEQUENCES] == reset[N_SEQUENCES]


class TestCounts:
    # Normalized by task B1 to dengue's semantics: both cards are computed from
    # filtered_sequences, the continent-filtered row frame that also feeds the download.

    def test_sequence_count_counts_the_filtered_rows(self, zika_page):
        result = run_zika(zika_page, "reset-filters-button-zikv")
        assert result[N_SEQUENCES] == 4
        assert isinstance(result[N_SEQUENCES], int)

    def test_host_count_counts_hosts_present_in_the_filtered_data(self, zika_page):
        # Was len(selected_hosts) == 3 before B1, i.e. the whole host vocabulary regardless of
        # the filter. Two mappable sequences match, carrying two distinct hosts; the third
        # "Asian" sequence sits in a country with no geojson match and is dropped with it.
        result = run_zika(zika_page, "filter-button-zikv", basic_genotypes=["Asian"])
        assert result[N_HOSTS] == 2


class TestDatasetShape:
    def test_undated_sequences_are_dropped_at_import(self, zika_page):
        # Task B2 added 'collection_date' to clean_df (zika_page.py:48), matching dengue:79
        # and chikungunya:50. Measured against arbodash_dev this drops no production rows —
        # collection_date is never null there — but it keeps the three pages consistent.
        assert not zika_page.df_world_zika["collection_date"].isna().any()


class TestDownloadPayload:
    def test_download_exports_seven_columns(self, zika_page):
        result = run_zika(zika_page, "reset-filters-button-zikv")
        assert download_header(result[DOWNLOAD]) == [
            "genbank_sequence_data_id", "collection_date", "genotype",
            "host", "country", "country_acr", "location",
        ]

    def test_download_carries_the_filtered_rows(self, zika_page):
        narrow = run_zika(zika_page, "filter-button-zikv", basic_genotypes=["Asian"],
                          date_from="2016-01-01", date_to="2019-01-01")
        assert download_row_count(narrow[DOWNLOAD]) == 1


class TestFigures:
    def test_one_trace_per_selected_classification(self, zika_page):
        reset = run_zika(zika_page, "reset-filters-button-zikv")
        assert len(reset[BAR].data) == 3
        narrow = run_zika(zika_page, "filter-button-zikv", basic_genotypes=["Asian"])
        assert len(narrow[BAR].data) == 1

    def test_the_map_is_rebuilt_as_components(self, zika_page):
        result = run_zika(zika_page, "reset-filters-button-zikv")
        assert isinstance(result[MAP], list) and result[MAP]


class TestEmptySelectionIsHandled:
    def test_a_selection_matching_no_sequence_renders_instead_of_raising(self, zika_page):
        # Task B5 ported dengue's two guards (dengue_script.py:83-85 and :97-101) into
        # zika_script and started passing the date window to the charts explicitly, so an
        # empty frame no longer has to supply its own min/max.
        result = run_zika(zika_page, "filter-button-zikv", basic_genotypes=["African"],
                          date_from="2016-01-01", date_to="2017-01-01")
        assert result[N_SEQUENCES] == 0
        assert len(result[BAR].data) == 0
