"""Import the pathogen pages without a database.

Each page module opens a MySQL connection, queries a metadata table and writes a TSV to
`data/<pathogen>/` at import time (e.g. dengue_page.py:62-121), so until now no test could
import one. This installs a stand-in client and redirects those writes, which is enough to
exercise the pages in-process.

The stand-in follows the shape of FakeClient in src/tests/phylo/test_result_provider.py.
"""

import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from utils.models.database_models import (
    ChikungunyaMetaEntity,
    DengueMetaEntity,
    UpdateLogs,
    ZikaMetaEntity,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# The pages read data/geojson/ and write data/<pathogen>/ relative to the working directory
GEOJSON_RELATIVE_PATH = "data/geojson/world_geojson.json"


def blank_row(entity_class):
    # list_records returns every table column (DashDatabaseClient.__row2dict), so the
    # stand-in has to as well or the pages drop/rename columns that are not there
    return {column.name: None for column in entity_class.__table__.columns}


def sequence_row(entity_class, accession, country, host, collection_date, **classification):
    row = blank_row(entity_class)
    row["id"] = abs(hash(accession)) % 100000
    row["genbank_sequence_data_id"] = accession
    row["country"] = country
    row["host"] = host
    row["collection_date"] = collection_date
    row["length"] = 10500
    row.update(classification)
    return row


# A classification value carried ONLY by sequences from a country with no geojson match makes
# build_df_to_map raise KeyError on chikungunya and zika: the classification list is taken from
# the frame before the iso_a3 merge, while the pivot columns come from after it
# (chikungunya_script.py:66-79, zika_script.py:66-79). dengue_script.py:83-85 zero-fills the
# missing column and is unaffected. These rows deliberately keep the unmapped country and the
# unresolved classification on separate sequences so the harness does not depend on that defect.

def dengue_rows():
    # Serotypes and genotypes must be keys of dengue_color_scheme /
    # dengue_color_scheme_genotypes or dengue_page.py:101-107 rewrites them to "Unassigned"
    return [
        sequence_row(DengueMetaEntity, "AB000001.1", "Brazil", "Homo sapiens",
                     "2015-06-01T00:00:00Z", serotype="DENV1", genotype="1I",
                     major_lineage="1I_A", minor_lineage="1I_A.1"),
        sequence_row(DengueMetaEntity, "AB000002.1", "Brazil", "Aedes aegypti",
                     "2016-07-15T00:00:00Z", serotype="DENV2", genotype="2II",
                     major_lineage="2II_B", minor_lineage="2II_B.1"),
        # Dated but hostless, so host fillna("Unknown") stays covered now that the undated
        # sequences are dropped on every page
        sequence_row(DengueMetaEntity, "AB000003.1", "Thailand", None,
                     "2018-01-20T00:00:00Z", serotype="DENV3", genotype="3III"),
        # No collection date: dropped by clean_df on dengue and chikungunya, kept on zika
        sequence_row(DengueMetaEntity, "AB000004.1", "Colombia", None, None,
                     serotype="DENV4", genotype="4I"),
        # No ISO/geojson match; its serotype also occurs on a mapped country
        sequence_row(DengueMetaEntity, "AB000005.1", "Atlantis", "Homo sapiens",
                     "2019-03-10T00:00:00Z", serotype="DENV1", genotype="1I"),
        # Unresolved classification, on a mapped country
        sequence_row(DengueMetaEntity, "AB000006.1", "Brazil", "Homo sapiens",
                     "2020-05-05T00:00:00Z", serotype=None, genotype=None),
    ]


def chikungunya_rows():
    return [
        sequence_row(ChikungunyaMetaEntity, "CB000001.1", "Brazil", "Homo sapiens",
                     "2015-06-01T00:00:00Z", genotype="ECSA"),
        sequence_row(ChikungunyaMetaEntity, "CB000002.1", "Brazil", "Aedes aegypti",
                     "2016-07-15T00:00:00Z", genotype="ACL"),
        sequence_row(ChikungunyaMetaEntity, "CB000003.1", "Kenya", None,
                     "2018-01-20T00:00:00Z", genotype="WA"),
        sequence_row(ChikungunyaMetaEntity, "CB000004.1", "Colombia", None, None,
                     genotype="ECSA"),
        sequence_row(ChikungunyaMetaEntity, "CB000005.1", "Atlantis", "Homo sapiens",
                     "2019-03-10T00:00:00Z", genotype="ECSA"),
        sequence_row(ChikungunyaMetaEntity, "CB000006.1", "Brazil", "Homo sapiens",
                     "2020-05-05T00:00:00Z", genotype=None),
    ]


def zika_rows():
    return [
        sequence_row(ZikaMetaEntity, "ZB000001.1", "Brazil", "Homo sapiens",
                     "2015-06-01T00:00:00Z", genotype="Asian"),
        sequence_row(ZikaMetaEntity, "ZB000002.1", "Brazil", "Aedes aegypti",
                     "2016-07-15T00:00:00Z", genotype="Asian"),
        sequence_row(ZikaMetaEntity, "ZB000003.1", "Kenya", None,
                     "2018-01-20T00:00:00Z", genotype="African"),
        sequence_row(ZikaMetaEntity, "ZB000004.1", "Colombia", None, None,
                     genotype="African"),
        sequence_row(ZikaMetaEntity, "ZB000005.1", "Atlantis", "Homo sapiens",
                     "2019-03-10T00:00:00Z", genotype="Asian"),
        sequence_row(ZikaMetaEntity, "ZB000006.1", "Brazil", "Homo sapiens",
                     "2020-05-05T00:00:00Z", genotype=None),
    ]


RECORDS_BY_ENTITY = {
    DengueMetaEntity: dengue_rows,
    ChikungunyaMetaEntity: chikungunya_rows,
    ZikaMetaEntity: zika_rows,
}


class StandInDatabaseClient:
    """Just enough DashDatabaseClient to let a page module import."""

    def __init__(self):
        self.submitted_phylo_jobs = []

    def list_records(self, entity_class):
        build_rows = RECORDS_BY_ENTITY.get(entity_class)
        if build_rows is None:
            raise AssertionError(f"no stand-in records for {entity_class}")
        return build_rows()

    def get_last_update(self, entity_class=UpdateLogs):
        return {"timestamp": datetime(2026, 8, 10, 12, 0, 0)}

    def add_phylo_job(self, filter_params_json, accession_ids, pathogen, inference_method=None):
        self.submitted_phylo_jobs.append(
            {"filter_params": filter_params_json, "accession_ids": accession_ids,
             "pathogen": pathogen, "inference_method": inference_method}
        )
        return len(self.submitted_phylo_jobs)

    def get_phylo_job_status(self, job_id):
        return None

    def get_phylo_job_result(self, job_id):
        return None

    def get_tip_metadata(self, accession_ids):
        return []

    def get_locations_for_accessions(self, accession_ids):
        locations = {}
        for build_rows in RECORDS_BY_ENTITY.values():
            for row in build_rows():
                accession = row["genbank_sequence_data_id"]
                if accession in accession_ids:
                    country = row.get("country") or "Unknown"
                    locations[accession] = f"{country}: mock"
        return locations


@contextmanager
def triggered_by(component_id):
    """Run a page callback as if `component_id` fired it.

    The main callbacks branch on ctx.triggered_id (dengue_page.py:1031,
    chikungunya_page.py:770, zika_page.py:758) rather than on their positional arguments, so
    the trigger is the only thing that selects a filter path. Pass None for the initial /
    unrecognised trigger.
    """
    from dash._callback_context import context_value
    from dash._utils import AttributeDict

    triggered = [] if component_id is None else [{"prop_id": f"{component_id}.n_clicks"}]
    token = context_value.set(AttributeDict(triggered_inputs=triggered))
    try:
        yield
    finally:
        context_value.reset(token)


def download_header(tsv_text):
    """Column names from a download store payload (a TSV string)."""
    return tsv_text.splitlines()[0].split("\t")


def download_row_count(tsv_text):
    lines = [line for line in tsv_text.splitlines() if line.strip()]
    return len(lines) - 1


@pytest.fixture(scope="session")
def pathogen_pages(tmp_path_factory):
    """The three page modules, imported against the stand-in client."""
    written_datasets = tmp_path_factory.mktemp("page_datasets")

    import utils.database.DashDatabaseClient as client_module
    real_client = client_module.DashDatabaseClient
    real_to_csv = pd.DataFrame.to_csv
    previous_cwd = os.getcwd()

    def to_csv_into_tmp(self, path_or_buf=None, *args, **kwargs):
        # The download callbacks call to_csv with no path to get a string back; only the
        # import-time dataset dumps name a file, and those must not touch data/
        if isinstance(path_or_buf, (str, Path)):
            path_or_buf = str(written_datasets / Path(path_or_buf).name)
        return real_to_csv(self, path_or_buf, *args, **kwargs)

    client_module.DashDatabaseClient = StandInDatabaseClient
    pd.DataFrame.to_csv = to_csv_into_tmp
    os.chdir(REPO_ROOT)

    try:
        assert Path(GEOJSON_RELATIVE_PATH).exists(), (
            f"pages read {GEOJSON_RELATIVE_PATH} relative to the working directory"
        )
        # register_page refuses to run before an app exists. pages_folder="" keeps Dash from
        # walking src/pages itself, so the imports below stay explicit and ordered.
        import dash

        dash.Dash(__name__, use_pages=True, pages_folder="")

        import pages.chikungunya_page as chikungunya_page
        import pages.dengue_page as dengue_page
        import pages.zika_page as zika_page
    finally:
        pd.DataFrame.to_csv = real_to_csv
        client_module.DashDatabaseClient = real_client
        os.chdir(previous_cwd)

    yield {
        "dengue": dengue_page,
        "chikungunya": chikungunya_page,
        "zika": zika_page,
    }

    for module_name in ("pages.dengue_page", "pages.chikungunya_page", "pages.zika_page"):
        sys.modules.pop(module_name, None)
