"""Fetch nucleotide FASTA from NCBI Entrez to disk."""

import logging
import ssl
import time
from pathlib import Path

from Bio import Entrez
from dotenv import load_dotenv

from models.env_models import EnvSettings
from phylo_module import config

from shared.utils.handlers import SeqHandler

logger = logging.getLogger(__name__)

PHYLO_SEQUENCES_DIR = Path(__file__).resolve().parents[1] / "data" / "sequences"


def _configure_entrez():
    """Configure Entrez from EnvSettings."""
    load_dotenv()
    settings = EnvSettings()
    Entrez.email = settings.NCBI_EMAIL
    if settings.NCBI_API_KEY:
        Entrez.api_key = settings.NCBI_API_KEY
    ssl._create_default_https_context = ssl._create_unverified_context


def _normalize_accession_ids(accession_ids):
    seen = set()
    normalized = []
    for raw in accession_ids:
        acc_id = raw.strip()
        if not acc_id or acc_id in seen:
            continue
        seen.add(acc_id)
        normalized.append(acc_id)
    return normalized


def _fetch_batch(batch_ids):
    handle = Entrez.efetch(
        db="nucleotide",
        id=",".join(batch_ids),
        rettype="fasta",
        retmode="text",
    )
    # records = list(SeqIO.parse(handle, "fasta"))
    records = list(SeqHandler.parse_fasta(handle))

    handle.close()

    return records


def _fetch_single(accession_id):
    try:
        handle = Entrez.efetch(
            db="nucleotide",
            id=accession_id,
            rettype="fasta",
            retmode="text",
        )
        # record = SeqIO.read(handle, "fasta")
        record = SeqHandler.parse_fasta(handle)

        handle.close()
        return record[0] if record else None
        # return record

    except Exception as exc:
        logger.warning("Could not fetch %s: %s", accession_id, exc)
        return None


def _record_accession_id(record):
    return record.id.split()[0]


def _write_records(out_handle, records, fetched_ids):
    for record in records:

        # SeqIO.write(record, out_handle, "fasta")
        SeqHandler.write_fasta_record(out_handle, record)

        fetched_ids.add(_record_accession_id(record))


def _fetch_missing_individually(missing_ids, out_handle, fetched_ids, sleep_time):
    for accession_id in missing_ids:
        record = _fetch_single(accession_id)
        if record is None:
            continue

        # SeqIO.write(record, out_handle, "fasta")
        SeqHandler.write_fasta_record(out_handle, record)    

        fetched_ids.add(_record_accession_id(record))
        time.sleep(sleep_time)


def fetch_fasta_sequences(
    accession_ids,
    output_path,
    *,
    batch_size=config.ENTREZ_BATCH_SIZE,
    sleep_time=config.ENTREZ_SLEEP_SECONDS,
):
    """
    Fetch GenBank nucleotide records and write a multi-FASTA file.

    Returns a dict with output_path, requested, fetched, and failed_accessions.
    """
    ids = _normalize_accession_ids(accession_ids)
    if not ids:
        raise ValueError("accession_ids must contain at least one non-empty accession")

    _configure_entrez()

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    fetched_ids = set()

    logger.info(
        "Fetching %d accession(s) in batches of %d → %s",
        len(ids),
        batch_size,
        destination,
    )

    with destination.open("w") as out_handle:
        for start in range(0, len(ids), batch_size):
            batch_ids = ids[start : start + batch_size]
            batch_records = []

            try:
                batch_records = _fetch_batch(batch_ids)
                _write_records(out_handle, batch_records, fetched_ids)
            except Exception as exc:
                logger.error(
                    "Batch fetch failed for %s: %s — retrying individually",
                    batch_ids,
                    exc,
                )
                _fetch_missing_individually(batch_ids, out_handle, fetched_ids, sleep_time)
                time.sleep(sleep_time)
                continue

            returned = {_record_accession_id(record) for record in batch_records}
            missing_in_batch = [acc for acc in batch_ids if acc not in returned]
            if missing_in_batch:
                logger.warning(
                    "Batch returned %d/%d record(s); fetching missing: %s",
                    len(returned),
                    len(batch_ids),
                    missing_in_batch,
                )
                _fetch_missing_individually(
                    missing_in_batch, out_handle, fetched_ids, sleep_time
                )

            time.sleep(sleep_time)

    failed = [acc for acc in ids if acc not in fetched_ids]
    if failed:
        logger.warning("Failed to fetch %d accession(s): %s", len(failed), failed)
    else:
        logger.info("All %d accession(s) written to %s", len(fetched_ids), destination)

    return {
        "output_path": str(destination.resolve()),
        "requested": len(ids),
        "fetched": len(fetched_ids),
        "failed_accessions": failed,
    }
