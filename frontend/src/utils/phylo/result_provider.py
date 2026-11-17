"""The boundary between the phylo job queue and the tree viewer.

Everything the viewer needs comes from here as a plain dictionary. The viewer
never sees a database client, a table, or a column name, and this module never
builds a figure. It is also the only place that knows a completed job carries
two different trees.
"""

from utils.functions.geo_functions import division_from_ncbi, locality_from_ncbi
from utils.phylo.viewer.annotate import MetadataAnnotator
from utils.phylo.viewer.parse import NewickParseError, parse_newick

KEY_COLUMN = "accession_id"
DIVISION_FIELD = "division"
LOCALITY_FIELD = "locality"

# Present for every pathogen; region and location come from the GenBank row, not the
# pathogen's metadata table, and are hover-only (never offered for colouring)
UNIVERSAL_METADATA_COLUMNS = ["country", "region", "location", "host", "collection_date"]


def color_by_fields_for(spec):
    """Colour-by options are exactly what the pathogen declared it has."""
    fields = list(spec["phylo_metadata_fields"])
    if "country" in fields:
        insert_at = fields.index("country") + 1
        fields.insert(insert_at, DIVISION_FIELD)
        fields.insert(insert_at + 1, LOCALITY_FIELD)
    else:
        fields.append(DIVISION_FIELD)
        fields.append(LOCALITY_FIELD)
    return fields


def metadata_columns_for(spec):
    """Hover order (most identifying first): accession, classifications, then the rest."""
    classifications = [field for field in spec["phylo_metadata_fields"]
                       if field not in UNIVERSAL_METADATA_COLUMNS]
    return [KEY_COLUMN] + classifications + UNIVERSAL_METADATA_COLUMNS


def load_phylogeny_status(database_client, job_id):
    """Progress of a running job: status, event log, error. No trees.

    Returns None when the job row does not exist.
    """
    if not job_id:
        return None
    job = database_client.get_phylo_job_status(job_id)
    if not job:
        return None
    return {
        "job_id": job["id"],
        "status": job["status"],
        "events": job.get("warnings") or [],
        "error_message": job.get("error_message"),
        "sequence_count": job.get("sequence_count"),
        "inference_method": job.get("inference_method"),
    }


def load_phylogeny_result(database_client, job_id, spec):
    """Everything the viewer draws, for one finished job.

    The substitution tree and the TreeTime dated tree are both returned as the
    backend stored them, unparsed and unaltered: a NEXUS round trip through
    Newick rewrites the tip labels, and those labels are the GenBank accessions
    the metadata join depends on.

    `time_tree_nexus` is None whenever the temporal stage was skipped or failed.
    That is a normal outcome, not a job failure, and callers must present it as
    "no dated tree" rather than falling back to the substitution tree silently.
    """
    job = database_client.get_phylo_job_result(job_id)
    if not job:
        return _empty_result(job_id, "missing", "No such phylogenetic job.", spec=spec)

    if job["status"] == "failed":
        return _empty_result(job_id, "failed",
                             job.get("error_message") or "Tree generation failed.",
                             events=job.get("warnings") or [], spec=spec)

    newick = job.get("newick")
    if not newick:
        return _empty_result(job_id, "failed",
                             "The job finished without a tree.",
                             events=job.get("warnings") or [], spec=spec)

    try:
        tip_accessions = parse_newick(newick).tip_labels()
    except NewickParseError as error:
        return _empty_result(job_id, "failed",
                             f"The stored tree could not be read: {error}",
                             events=job.get("warnings") or [], spec=spec)

    tip_records = _tip_records(database_client, tip_accessions, spec)
    time_tree_nexus = job.get("time_tree_nexus")

    return {
        "job_id": job["id"],
        "status": "done",
        "error_message": None,
        "events": job.get("warnings") or [],
        "substitution_newick": newick,
        "time_tree_nexus": time_tree_nexus,
        "inference_method": job.get("inference_method"),
        "sequence_count": job.get("sequence_count"),
        "tip_records": tip_records,
        "metadata_columns": metadata_columns_for(spec),
        "color_by_fields": color_by_fields_for(spec),
        "key_column": KEY_COLUMN,
        "pathogen": spec["id_suffix"],
        "clock": _clock_summary(job.get("run_metadata")),
        "metadata_report": _metadata_report(tip_records, tip_accessions),
        "tip_set_report": _tip_set_report(tip_accessions, time_tree_nexus),
    }


def _empty_result(job_id, status, error_message, events=None, spec=None):
    return {
        "job_id": job_id,
        "status": status,
        "error_message": error_message,
        "events": events or [],
        "substitution_newick": None,
        "time_tree_nexus": None,
        "inference_method": None,
        "sequence_count": None,
        "tip_records": [],
        "metadata_columns": metadata_columns_for(spec) if spec else [KEY_COLUMN],
        "color_by_fields": color_by_fields_for(spec) if spec else [],
        "key_column": KEY_COLUMN,
        "pathogen": spec["id_suffix"] if spec else None,
        "clock": None,
        "metadata_report": None,
        "tip_set_report": None,
    }


def _tip_records(database_client, tip_accessions, spec):
    """The epidemiological table for these tips, as rows keyed on the accession.

    Tips are labelled with accessions only; the classification, country and host fields
    live in the pathogen's metadata table and are joined back on that accession after
    inference. A tip with no row simply has no record here.
    """
    metadata_by_accession = database_client.get_tip_metadata(tip_accessions, spec["id_suffix"])
    columns = metadata_columns_for(spec)
    records = []
    for accession in tip_accessions:
        fields = metadata_by_accession.get(accession)
        if fields is None:
            continue
        record = {KEY_COLUMN: accession}
        for column in columns[1:]:
            record[column] = fields.get(column)
        record[LOCALITY_FIELD] = locality_from_ncbi(fields.get("location"))
        record[DIVISION_FIELD] = division_from_ncbi(fields.get("location"))
        records.append(record)
    return records


def _metadata_report(tip_records, tip_accessions):
    if not tip_records:
        return {"matched": 0, "unmatched": list(tip_accessions), "duplicated": []}
    return MetadataAnnotator(tip_records, key_col=KEY_COLUMN).join_report(tip_accessions)


def _tip_set_report(tip_accessions, time_tree_nexus):
    """Which tips each tree carries.

    TreeTime drops sequences it cannot date and may exclude clock-filter
    outliers, so the dated tree is a subset of the substitution tree often
    enough that the difference has to be shown rather than assumed away.
    """
    if not time_tree_nexus:
        return None
    try:
        dated_tips = set(parse_newick(time_tree_nexus).tip_labels())
    except NewickParseError:
        return None
    substitution_tips = set(tip_accessions)
    return {
        "only_in_substitution": sorted(substitution_tips - dated_tips),
        "only_in_time_tree": sorted(dated_tips - substitution_tips),
    }


def _clock_summary(run_metadata):
    """The molecular-clock numbers, reported as measured.

    A low R² means the sequences carry little temporal signal, which is a fact
    about the data. The backend applies no threshold and neither does this: the
    dated tree is shown with its clock quality next to it.
    """
    treetime = (run_metadata or {}).get("treetime")
    if not treetime:
        return None
    return {
        "status": treetime.get("status"),
        "clock_rate": treetime.get("clock_rate"),
        "r_squared": treetime.get("r_squared"),
        "dated_tips": treetime.get("dated_tips"),
        "tree_tips": treetime.get("tree_tips"),
        "dated_fraction": treetime.get("dated_fraction"),
        "excluded_tips": treetime.get("excluded_tips") or [],
    }
