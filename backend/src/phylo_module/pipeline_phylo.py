"""Dynamic phylo pipeline: accession list in, persisted Newick out. Run as __main__ for the job watcher."""

import hashlib
import json
import logging
import os
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models.database_models import PhyloEntity
from phylo_module.pathogens import canonical_pathogen, meta_entity_for
from models.env_models import EnvSettings
from phylo_module import config
from phylo_module.services.alignment_service import align_fasta_sequences
from phylo_module.services.fasta_service import fetch_fasta_sequences
from phylo_module.services.iqtree_service import run_iqtree
from phylo_module.services.persistence_service import persist_phylo_run
from phylo_module.services.tree_service import build_fasttree
from phylo_module.services.treetime_service import (
    normalize_collection_dates,
    read_tree_tip_names,
    resolve_treetime_settings,
    run_treetime,
)
from services.DatabaseService import DatabaseService

# Accepted inference_method values; reject unknowns
INFERENCE_METHOD_FASTTREE = "FastTree"
INFERENCE_METHOD_IQTREE = "IQ-TREE"

logger = logging.getLogger(__name__)

PHYLO_RUNS_DIR = Path(__file__).resolve().parent / "data" / "runs"

PHYLO_STATUS_PENDING = "pending"
PHYLO_STATUS_PROCESSING = "processing"
PHYLO_STATUS_DONE = "done"
PHYLO_STATUS_FAILED = "failed"


class PhyloRequestTooLargeError(Exception):
    pass


def _normalize_accession_ids(accession_ids):
    seen = set()
    normalized = []
    for raw in accession_ids:
        acc_id = raw.strip() if raw else ""
        if not acc_id or acc_id in seen:
            continue
        seen.add(acc_id)
        normalized.append(acc_id)
    return normalized


def _inference_settings(inference_method):
    # Engine params from config (offline hash; no binary probe)
    if inference_method == INFERENCE_METHOD_IQTREE:
        return {
            "model": config.IQTREE_MODEL,
            "subst_type": config.IQTREE_SUBST_TYPE,
            "ufboot_enabled": config.IQTREE_UFBOOT_ENABLED,
            "ufboot_replicates": config.IQTREE_UFBOOT_REPLICATES,
            "shalrt_enabled": config.IQTREE_SHALRT_ENABLED,
            "shalrt_replicates": config.IQTREE_SHALRT_REPLICATES,
            "bnni_enabled": config.IQTREE_BNNI_ENABLED,
            "seed": config.IQTREE_SEED,
        }
    return {"nt_flag": config.FASTTREE_NT_FLAG}


def _phylo_job_hash(accession_ids, inference_method, treetime_inputs):
    """SHA-256 of sorted job inputs (accessions, engine, alignment, optional TreeTime)."""
    payload = {
        "cache_version": config.PIPELINE_CACHE_VERSION,
        "accession_ids": sorted(_normalize_accession_ids(accession_ids)),
        "inference_method": inference_method,
        "inference_settings": _inference_settings(inference_method),
        "alignment": {"mafft_algorithm_flag": config.MAFFT_ALGORITHM_FLAG},
    }
    if treetime_inputs is not None:
        payload["treetime"] = {
            "settings": treetime_inputs["settings"],
            "dates": sorted(treetime_inputs["dated_tips"].items()),
        }
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def _resolve_inference_method(raw_method):
    # Null → config default; unknown → hard error
    if not raw_method:
        raw_method = config.INFERENCE_METHOD
    normalized = str(raw_method).strip().lower().replace("_", "").replace("-", "")
    if normalized == "iqtree":
        return INFERENCE_METHOD_IQTREE
    if normalized == "fasttree":
        return INFERENCE_METHOD_FASTTREE
    raise ValueError(
        f"Unsupported inference_method: {raw_method!r} "
        f"(expected {INFERENCE_METHOD_FASTTREE!r} or {INFERENCE_METHOD_IQTREE!r})."
    )


def _promote_canonical_tree(source_tree_path, destination_tree_path):
    # Atomic promote to canonical tree.nwk
    tree_text = Path(source_tree_path).read_text()
    destination = Path(destination_tree_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_name(destination.name + ".tmp")
    temp_path.write_text(tree_text)
    os.replace(temp_path, destination)


def _collect_host_metadata():
    host = {
        "cpu_model": None,
        "cpu_cores_physical": None,
        "cpu_cores_logical": None,
        "ram_gb": None,
        "os": None,
        "python_version": None,
    }
    try:
        host["os"] = platform.platform()
    except Exception:
        pass
    try:
        host["python_version"] = platform.python_version()
    except Exception:
        pass
    try:
        host["cpu_cores_logical"] = os.cpu_count()
    except Exception:
        pass
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text()
        for line in cpuinfo.splitlines():
            if line.startswith("model name"):
                host["cpu_model"] = line.split(":", 1)[1].strip()
                break
        physical_ids = set()
        physical_id = None
        core_id = None
        for line in cpuinfo.splitlines():
            if line.startswith("physical id"):
                physical_id = line.split(":", 1)[1].strip()
            elif line.startswith("core id"):
                core_id = line.split(":", 1)[1].strip()
            elif not line.strip():
                if physical_id is not None and core_id is not None:
                    physical_ids.add((physical_id, core_id))
                physical_id = None
                core_id = None
        if physical_id is not None and core_id is not None:
            physical_ids.add((physical_id, core_id))
        if physical_ids:
            host["cpu_cores_physical"] = len(physical_ids)
    except Exception:
        pass
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                kib = int(line.split()[1])
                host["ram_gb"] = round(kib / (1024 * 1024), 1)
                break
    except Exception:
        pass
    return host


def _build_run_metadata(inference_method, inference_result):
    return {
        "inference_method": inference_method,
        "software": inference_result.get("software", inference_method),
        "software_version": inference_result.get("software_version"),
        "selected_model": inference_result.get("selected_model"),
        "command": inference_result.get("iqtree_command")
        or inference_result.get("fasttree_command"),
        "execution_time_seconds": inference_result.get("execution_time_seconds"),
        "threads_used": inference_result.get("threads_used"),
        "engine_warnings": inference_result.get("warnings") or [],
    }


def _write_run_manifest(run_dir, accession_set_hash, sequence_count, run_metadata, events):
    # On-disk twin of DB run_metadata
    manifest = {
        "accession_set_hash": accession_set_hash,
        "sequence_count": sequence_count,
        "run_metadata": run_metadata,
        "events": events,
    }
    manifest_path = Path(run_dir) / "run.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))


def _filter_params_for_storage(filter_params):
    if isinstance(filter_params, dict):
        return json.dumps(filter_params)
    return filter_params


def _parse_filter_params(filter_params):
    if filter_params is None:
        return {}
    if isinstance(filter_params, str):
        return json.loads(filter_params)
    return dict(filter_params)


def _job_accession_ids(job):
    return sorted(_normalize_accession_ids(job.get("accession_ids") or []))


def accessions_passing_completeness(database_service, accession_ids, completeness, meta_entity):
    min_length = config.MIN_SEQUENCE_LENGTH if completeness == "any" else config.WHOLE_GENOME_MIN_LENGTH

    meta_rows = database_service.get_record_by_filters(
        entity_class=meta_entity,
        and_filters=[meta_entity.genbank_sequence_data_id.in_(accession_ids)],
        order_column="genbank_sequence_data_id",
        order_desc=False,
        all_records=True,
    )
    return [
        row["genbank_sequence_data_id"]
        for row in meta_rows
        if row.get("genbank_sequence_data_id")
        and row.get("length") is not None
        and row["length"] >= min_length
    ]


def resolve_collection_dates(database_service, accession_ids, meta_entity):
    """collection_date per accession from the pathogen's meta table (None if missing)."""
    meta_rows = database_service.get_record_by_filters(
        entity_class=meta_entity,
        and_filters=[meta_entity.genbank_sequence_data_id.in_(accession_ids)],
        order_column="genbank_sequence_data_id",
        order_desc=False,
        all_records=True,
    )
    stored_dates = {
        row["genbank_sequence_data_id"]: row.get("collection_date")
        for row in meta_rows
        if row.get("genbank_sequence_data_id")
    }
    return {accession_id: stored_dates.get(accession_id) for accession_id in accession_ids}


def _treetime_enabled(filter_params):
    # Missing key → config default (not off)
    return bool(filter_params.get("treetime", config.TREETIME_ENABLED))


def _treetime_job_inputs(database_service, accession_ids, filter_params, meta_entity):
    """TreeTime parameters and normalized tip dates, or None when the stage is disabled."""
    if not _treetime_enabled(filter_params):
        return None
    normalized = normalize_collection_dates(
        resolve_collection_dates(database_service, accession_ids, meta_entity)
    )
    return {
        "settings": resolve_treetime_settings({}),
        "dated_tips": normalized["dated_tips"],
        "excluded_tips": normalized["excluded_tips"],
    }


def _update_phylo_job(database_service, job_id, fields):
    payload = {"id": job_id}
    payload.update(fields)
    database_service.update_bulk(PhyloEntity, [payload])


def _event(message, level="info"):
    # level: info | warning | error
    return {"message": message, "level": level, "ts": datetime.now().isoformat(timespec="seconds")}


def _emit(events, database_service, job_id, message, level="info"):
    # Stage event log; watcher overwrites warnings each step
    events.append(_event(message, level))
    if job_id is not None:
        _update_phylo_job(database_service, job_id, {"warnings": events})


def _run_id_after_persist(database_service, accession_set_hash):
    # add_record() detaches; read id back by hash
    rows = database_service.get_record_by_filters(
        entity_class=PhyloEntity,
        and_filters=[PhyloEntity.accession_set_hash == accession_set_hash],
        order_column="created_at",
        all_records=False,
    )
    if not rows:
        raise RuntimeError(
            f"No phylo_tb row found for accession_set_hash={accession_set_hash}"
        )
    return rows[0]["id"]


def _find_reusable_tree(database_service, accession_set_hash, inference_method, treetime_inputs):
    # Explicit engine filter; require time_tree_nexus when temporal stage is on
    reuse_filters = [
        PhyloEntity.accession_set_hash == accession_set_hash,
        PhyloEntity.inference_method == inference_method,
        PhyloEntity.status == PHYLO_STATUS_DONE,
        PhyloEntity.newick.isnot(None),
    ]
    if treetime_inputs is not None:
        reuse_filters.append(PhyloEntity.time_tree_nexus.isnot(None))

    rows = database_service.get_record_by_filters(
        entity_class=PhyloEntity,
        and_filters=reuse_filters,
        order_column="completed_at",
        order_desc=True,
    )
    return rows[0] if rows else None


def _reused_run_metadata(existing_job):
    provenance = dict(existing_job.get("run_metadata") or {})
    provenance["reused_from_job_id"] = existing_job["id"]
    provenance["reused_at"] = datetime.now().isoformat(timespec="seconds")
    return provenance


def _complete_phylo_job(
    database_service,
    job_id,
    newick,
    time_tree_nexus,
    sequence_count,
    filter_params,
    accession_set_hash,
    inference_method,
    run_metadata,
    events,
):
    _update_phylo_job(
        database_service,
        job_id,
        {
            "newick": newick,
            "time_tree_nexus": time_tree_nexus,
            "sequence_count": sequence_count,
            "filter_params": filter_params,
            "accession_set_hash": accession_set_hash,
            "inference_method": inference_method,
            "run_metadata": run_metadata,
            "warnings": events,
            "status": PHYLO_STATUS_DONE,
            "completed_at": datetime.now(),
            "error_message": None,
        },
    )


def _run_temporal_stage(database_service, phylo_job_id, events, alignment_path, tree_path,
                        treetime_dir, treetime_inputs):
    """TreeTime post-process; never raises — failure keeps the substitution tree."""
    excluded_tips = treetime_inputs["excluded_tips"]

    # Signal vs tips actually on the tree (intersect dated set with tip labels)
    tree_tip_names = read_tree_tip_names(tree_path)
    tree_tips = len(tree_tip_names)
    dated_tips = {
        accession_id: collection_date
        for accession_id, collection_date in treetime_inputs["dated_tips"].items()
        if accession_id in tree_tip_names
    }
    dated_fraction = len(dated_tips) / tree_tips if tree_tips else 0.0

    temporal_metadata = {
        "dated_tips": len(dated_tips),
        "tree_tips": tree_tips,
        "dated_fraction": round(dated_fraction, 4),
        "min_dated_sequences": config.TREETIME_MIN_DATED_SEQUENCES,
        "min_dated_fraction": config.TREETIME_MIN_DATED_FRACTION,
        "excluded_tips": excluded_tips,
    }

    if excluded_tips:
        excluded_list = ", ".join(tip["accession_id"] for tip in excluded_tips)
        _emit(
            events,
            database_service,
            phylo_job_id,
            f"{len(excluded_tips)} sequence(s) have no usable collection date and were left out "
            f"of the temporal analysis: {excluded_list}.",
            level="warning",
        )

    if (len(dated_tips) < config.TREETIME_MIN_DATED_SEQUENCES
            or dated_fraction < config.TREETIME_MIN_DATED_FRACTION):
        skip_reason = (
            f"Temporal analysis skipped: {len(dated_tips)} of {tree_tips} tip(s) carry a usable "
            f"collection date ({dated_fraction:.0%}), below the required "
            f"{config.TREETIME_MIN_DATED_SEQUENCES} dated tip(s) and "
            f"{config.TREETIME_MIN_DATED_FRACTION:.0%} of the tree. The phylogenetic tree is "
            "unaffected."
        )
        _emit(events, database_service, phylo_job_id, skip_reason, level="warning")
        temporal_metadata.update({"status": "skipped", "reason": skip_reason})
        return {"time_tree_nexus": None, "metadata": temporal_metadata}

    _emit(events, database_service, phylo_job_id, "Running TreeTime temporal analysis")

    try:
        treetime_result = run_treetime(
            str(alignment_path), str(tree_path), dated_tips, str(treetime_dir), {}
        )
    except Exception as exc:
        # Keep substitution tree; warn only (do not fail the job)
        logger.exception("TreeTime failed; keeping the substitution tree")
        _emit(
            events,
            database_service,
            phylo_job_id,
            f"Temporal analysis failed and no dated tree was produced; the phylogenetic tree "
            f"is unaffected: {exc}",
            level="warning",
        )
        temporal_metadata.update({"status": "failed", "error": str(exc)})
        return {"time_tree_nexus": None, "metadata": temporal_metadata}

    for engine_warning in treetime_result["warnings"]:
        _emit(events, database_service, phylo_job_id, engine_warning, level="warning")

    clock_filter_excluded = treetime_result["clock_filter_excluded"]
    if clock_filter_excluded:
        outlier_list = ", ".join(tip["accession_id"] for tip in clock_filter_excluded)
        _emit(
            events,
            database_service,
            phylo_job_id,
            f"{len(clock_filter_excluded)} sequence(s) deviate from the molecular clock by more "
            f"than {treetime_result['treetime_settings']['clock_filter']} interquartile ranges "
            f"and were excluded from rate estimation: {outlier_list}.",
            level="warning",
        )

    clock_rate = treetime_result["clock_rate"]
    if clock_rate is not None and clock_rate <= 0:
        _emit(
            events,
            database_service,
            phylo_job_id,
            f"TreeTime estimated a non-positive clock rate ({clock_rate:.3e}); this dataset "
            "carries too little temporal signal for the dated tree to be interpreted as a "
            "time scale.",
            level="warning",
        )

    # Record r^2; do not gate on it
    temporal_metadata.update(
        {
            "status": "done",
            "software": treetime_result["software"],
            "software_version": treetime_result["software_version"],
            "command": treetime_result["treetime_command"],
            "settings": treetime_result["treetime_settings"],
            "execution_time_seconds": treetime_result["execution_time_seconds"],
            "clock_rate": clock_rate,
            "r_squared": treetime_result["r_squared"],
            "clock_filter_excluded": clock_filter_excluded,
            # Path relative to run bundle
            "timetree_path": f"{Path(treetime_dir).name}/{Path(treetime_result['output_path']).name}",
        }
    )
    _emit(events, database_service, phylo_job_id, "Dated tree generated successfully")

    return {"time_tree_nexus": treetime_result["timetree_nexus"], "metadata": temporal_metadata}


def run_phylo_pipeline(
    database_service,
    accession_ids,
    filter_params,
    max_sequences,
    phylo_job_id=None,
    events=None,
    inference_method=None,
    treetime_inputs=None,
    pathogen="DENV",
):
    """Fetch, align, infer, optional TreeTime, persist. phylo_job_id set → update row; else insert."""
    inference_method = _resolve_inference_method(inference_method)
    normalized_ids = _normalize_accession_ids(accession_ids)
    request_size = len(normalized_ids)
    if events is None:
        events = []

    if request_size > max_sequences:
        raise PhyloRequestTooLargeError(
            f"Request has {request_size} accessions; max_sequences is {max_sequences}. "
            "Refine filters or raise the cap after benchmarking on this server."
        )

    if request_size < config.MIN_TREE_SEQUENCES:
        logger.warning(
            "Only %d sequence(s) requested — trees with fewer than %d tips are not "
            "phylogenetically meaningful for interpretation.",
            request_size,
            config.MIN_TREE_SEQUENCES,
        )
        _emit(
            events,
            database_service,
            phylo_job_id,
            "This tree uses fewer than four sequences. Trees this small are difficult to "
            "interpret and may not show meaningful relationships.",
            level="warning",
        )

    if treetime_inputs is None:
        treetime_inputs = _treetime_job_inputs(
            database_service, normalized_ids, _parse_filter_params(filter_params),
            meta_entity_for(pathogen)
        )

    accession_set_hash = _phylo_job_hash(normalized_ids, inference_method, treetime_inputs)

    run_dir = PHYLO_RUNS_DIR / accession_set_hash[:16]
    fasta_path = run_dir / "sequences.fasta"
    alignment_path = run_dir / "aligned.fasta"
    tree_path = run_dir / "tree.nwk"

    stages = {}
    host_metadata = _collect_host_metadata()

    _emit(events, database_service, phylo_job_id, "Retrieving sequences from GenBank")

    stage_started = time.perf_counter()
    fetch_result = fetch_fasta_sequences(normalized_ids, str(fasta_path))
    stages["fasta_fetch_s"] = round(time.perf_counter() - stage_started, 3)

    if fetch_result["failed_accessions"]:
        failed_list = ", ".join(fetch_result["failed_accessions"])
        _emit(
            events,
            database_service,
            phylo_job_id,
            f"{len(fetch_result['failed_accessions'])} sequence(s) could not be retrieved "
            f"from GenBank and were left out of the tree: {failed_list}.",
            level="warning",
        )

    _emit(events, database_service, phylo_job_id, "Running MAFFT alignment")

    stage_started = time.perf_counter()
    align_fasta_sequences(fetch_result["output_path"], str(alignment_path))
    stages["alignment_s"] = round(time.perf_counter() - stage_started, 3)

    # Same alignment → engine subdir → promote to tree.nwk
    if inference_method == INFERENCE_METHOD_IQTREE:
        _emit(events, database_service, phylo_job_id, "Running IQ-TREE inference")
        iqtree_dir = run_dir / "iqtree"
        inference_result = run_iqtree(str(alignment_path), str(iqtree_dir), {})
        stages["iqtree_s"] = inference_result["execution_time_seconds"]
        for engine_warning in inference_result.get("warnings", []):
            _emit(events, database_service, phylo_job_id, engine_warning, level="warning")
    else:
        _emit(events, database_service, phylo_job_id, "Running FastTree inference")
        fasttree_dir = run_dir / "fasttree"
        stage_started = time.perf_counter()
        inference_result = build_fasttree(
            str(alignment_path), str(fasttree_dir / "tree.nwk")
        )
        stages["fasttree_s"] = round(time.perf_counter() - stage_started, 3)

    _promote_canonical_tree(inference_result["output_path"], tree_path)

    newick = tree_path.read_text().strip()
    sequence_count = fetch_result["requested"] - len(fetch_result["failed_accessions"])
    stored_filter_params = _filter_params_for_storage(filter_params)
    run_metadata = _build_run_metadata(inference_method, inference_result)

    events.append(_event("Tree generated successfully"))

    # Temporal stage after inference; does not replace tree.nwk
    time_tree_nexus = None
    if treetime_inputs is not None:
        temporal_result = _run_temporal_stage(
            database_service,
            phylo_job_id,
            events,
            alignment_path,
            tree_path,
            run_dir / "treetime",
            treetime_inputs,
        )
        time_tree_nexus = temporal_result["time_tree_nexus"]
        run_metadata["treetime"] = temporal_result["metadata"]
        if temporal_result["metadata"].get("status") == "done":
            stages["treetime_s"] = temporal_result["metadata"]["execution_time_seconds"]

    run_metadata["stages"] = stages
    run_metadata["host"] = host_metadata

    _write_run_manifest(run_dir, accession_set_hash, sequence_count, run_metadata, events)

    if phylo_job_id is not None:
        _complete_phylo_job(
            database_service,
            phylo_job_id,
            newick=newick,
            time_tree_nexus=time_tree_nexus,
            sequence_count=sequence_count,
            filter_params=stored_filter_params,
            accession_set_hash=accession_set_hash,
            inference_method=inference_method,
            run_metadata=run_metadata,
            events=events,
        )
        run_id = phylo_job_id
    else:
        persist_phylo_run(
            database_service,
            newick=newick,
            time_tree_nexus=time_tree_nexus,
            sequence_count=sequence_count,
            filter_params=stored_filter_params,
            accession_ids=normalized_ids,
            accession_set_hash=accession_set_hash,
            inference_method=inference_method,
            pathogen=canonical_pathogen(pathogen),
            run_metadata=run_metadata,
            warnings=events,
        )
        run_id = _run_id_after_persist(database_service, accession_set_hash)

    return {
        "run_id": run_id,
        "sequence_count": sequence_count,
        "failed_accessions": fetch_result["failed_accessions"],
        "newick": newick,
        "time_tree_nexus": time_tree_nexus,
        "warnings": events,
    }


def reset_orphaned_phylo_jobs(database_service):
    """Rows stuck in processing after an interrupted watcher run are retried."""
    orphaned = database_service.get_record_by_filters(
        entity_class=PhyloEntity,
        and_filters=[PhyloEntity.status == PHYLO_STATUS_PROCESSING],
        order_column="created_at",
        order_desc=False,
        all_records=True,
    )
    for row in orphaned:
        # Clear partial event log before retry
        _update_phylo_job(
            database_service,
            row["id"],
            {
                "status": PHYLO_STATUS_PENDING,
                "started_at": None,
                "warnings": None,
            },
        )
        logger.info("Reset orphaned phylo job %s to pending", row["id"])


def _mark_phylo_job_failed(database_service, job_id, error_message):
    # error_message + closing error event (events re-read; in-memory list out of scope)
    rows = database_service.get_record_by_filters(
        entity_class=PhyloEntity,
        and_filters=[PhyloEntity.id == job_id],
        all_records=False,
    )
    events = (rows[0].get("warnings") if rows else None) or []
    events.append(_event(str(error_message), level="error"))
    _update_phylo_job(
        database_service,
        job_id,
        {
            "status": PHYLO_STATUS_FAILED,
            "warnings": events,
            "error_message": str(error_message),
            "completed_at": datetime.now(),
        },
    )


def _process_pending_phylo_job(database_service, job, max_sequences):
    job_id = job["id"]
    filter_params = _parse_filter_params(job.get("filter_params"))

    events = []

    # Single-worker: plain status update (no row lock)
    _update_phylo_job(
        database_service,
        job_id,
        {
            "status": PHYLO_STATUS_PROCESSING,
            "started_at": datetime.now(),
            "warnings": events,
        },
    )
    _emit(events, database_service, job_id, "Reading the selected accessions")

    selected_accessions = _job_accession_ids(job)
    if not selected_accessions:
        raise ValueError(
            "phylo job carries no accession_ids; the dashboard must submit the selected sequence set"
        )

    # The accession set is authoritative; the pathogen only says which table describes it
    meta_entity = meta_entity_for(job.get("pathogen"))

    accession_ids = accessions_passing_completeness(
        database_service, selected_accessions, filter_params.get("completeness"), meta_entity
    )
    if not accession_ids:
        raise ValueError("no selected accession met the minimum sequence length")

    selected_count = len(selected_accessions)
    too_short = selected_count - len(accession_ids)
    _emit(events, database_service, job_id, f"{selected_count} sequence(s) selected")
    if too_short:
        _emit(
            events,
            database_service,
            job_id,
            f"{too_short} sequence(s) below the minimum length were removed",
        )
    _emit(events, database_service, job_id, f"{len(accession_ids)} sequence(s) kept")

    inference_method = _resolve_inference_method(job.get("inference_method"))
    # Resolve once so cache lookup hash matches stored hash
    treetime_inputs = _treetime_job_inputs(
        database_service, accession_ids, filter_params, meta_entity)
    accession_set_hash = _phylo_job_hash(accession_ids, inference_method, treetime_inputs)

    if not filter_params.get("force_rebuild"):
        existing_job = _find_reusable_tree(
            database_service, accession_set_hash, inference_method, treetime_inputs
        )
        if existing_job:
            _emit(
                events,
                database_service,
                job_id,
                f"Reusing the tree from job #{existing_job['id']} — identical sequence set, "
                f"same engine ({inference_method})",
            )
            _complete_phylo_job(
                database_service,
                job_id,
                newick=existing_job["newick"],
                time_tree_nexus=existing_job.get("time_tree_nexus"),
                sequence_count=existing_job["sequence_count"],
                filter_params=_filter_params_for_storage(filter_params),
                accession_set_hash=accession_set_hash,
                inference_method=inference_method,
                run_metadata=_reused_run_metadata(existing_job),
                events=events,
            )
            return

    run_phylo_pipeline(
        database_service,
        accession_ids,
        filter_params,
        max_sequences,
        phylo_job_id=job_id,
        events=events,
        inference_method=inference_method,
        treetime_inputs=treetime_inputs,
        pathogen=job.get("pathogen"),
    )


def run_phylo_job_watcher(database_service, max_sequences, poll_seconds=config.WATCHER_POLL_SECONDS):
    reset_orphaned_phylo_jobs(database_service)
    print("Dengue phylo job watcher started. Press Ctrl+C to stop.")

    while True:
        try:
            pending_jobs = database_service.get_record_by_filters(
                entity_class=PhyloEntity,
                and_filters=[PhyloEntity.status == PHYLO_STATUS_PENDING],
                order_column="created_at",
                order_desc=False,
                all_records=False,
            )

            if not pending_jobs:
                # print("Waiting for phylo job requests...")
                time.sleep(poll_seconds)
                continue

            job = pending_jobs[0]
            job_id = job["id"]
            # print(f"Processing phylo job {job_id}...")
            # logger.info("Processing phylo job %s", job_id)

            try:
                _process_pending_phylo_job(database_service, job, max_sequences)
                print(f"Phylo job {job_id} done.")
            except Exception as exc:
                logger.exception("Phylo job %s failed", job_id)
                _mark_phylo_job_failed(database_service, job_id, exc)
                print(f"Phylo job {job_id} failed: {exc}")

        except KeyboardInterrupt:
            print("Stopping phylo job watcher.")
            break


def _build_database_service():
    load_dotenv()
    settings = EnvSettings()
    return DatabaseService(
        host=settings.DASH_HOST,
        port=settings.DASH_PORT,
        database=settings.DASH_DATABASE,
        user=settings.DASH_USER,
        password=settings.DASH_PASSWORD,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    database_service = _build_database_service()
    run_phylo_job_watcher(database_service, max_sequences=config.MAX_SEQUENCES)
