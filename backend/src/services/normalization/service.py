import logging
from collections import defaultdict
from typing import Callable

from models.database_models import GenbankSequenceDataEntity
from services.DatabaseService import DatabaseService
from services.normalization.brazil import normalize_brazil_location
from services.normalization.text import normalize_text
from shared.utils.handlers.RegexHandler import RegexHandler

logger = logging.getLogger(__name__)

Strategy = Callable[[str], str | None]

STRATEGIES: dict[str, Strategy] = {
    "brazil": normalize_brazil_location,
    "brasil": normalize_brazil_location,
}

COUNTRY_FILTER_ALIASES: dict[str, str] = {
    "brazil": "brazil",
    "brasil": "brazil",
}


def _normalize_country_filter(country: str) -> str:
    return COUNTRY_FILTER_ALIASES.get(normalize_text(country), normalize_text(country))


def strategy_available(country: str) -> bool:
    return normalize_text(country) in STRATEGIES


def normalize_location(country: str, location: str) -> str | None:
    """Dispatch a location to the registered country strategy."""
    if not location:
        return None

    strategy = STRATEGIES.get(normalize_text(country))
    if strategy is None:
        logger.info(
            "Location normalization service not available for country: %s",
            country,
        )
        return None

    return strategy(location)


def normalize_pending_locations(
    database_service: DatabaseService,
    country: str | None = None,
) -> dict[str, int]:
    """Normalize pending rows using a distinct-location de-para."""
    regex_handler = RegexHandler()

    and_filters = [
        GenbankSequenceDataEntity.location.isnot(None),
        GenbankSequenceDataEntity.location_normalized.is_(None),
    ]

    rows = database_service.get_record_by_filters(
        entity_class=GenbankSequenceDataEntity,
        and_filters=and_filters,
        order_column="accession_id",
        order_desc=False,
    )

    accessions_by_location: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        location = row["location"]
        row_country = regex_handler.match_country(location)
        if country is not None and _normalize_country_filter(row_country) != _normalize_country_filter(country):
            continue
        accessions_by_location[location].append(row["accession_id"])

    if not accessions_by_location:
        logger.info("No pending locations to normalize")
        return {"distinct": 0, "updated": 0, "resolved": 0, "unresolved": 0}

    cache: dict[str, str | None] = {}
    unresolved_brazil: list[str] = []

    for location in accessions_by_location:
        row_country = regex_handler.match_country(location)
        normalized = normalize_location(row_country, location)
        cache[location] = normalized

        if normalized is None and row_country and normalize_text(row_country) in STRATEGIES:
            unresolved_brazil.append(location)

    updates = []
    resolved = 0
    unresolved = 0

    for location, accessions in accessions_by_location.items():
        normalized = cache[location]
        if normalized is not None:
            resolved += len(accessions)
        else:
            unresolved += len(accessions)

        for accession_id in accessions:
            updates.append(
                {
                    "accession_id": accession_id,
                    "location_normalized": normalized,
                }
            )

    database_service.update_bulk(GenbankSequenceDataEntity, updates)

    for location in sorted(set(unresolved_brazil)):
        logger.warning("Unresolved Brazil location: %s", location)

    summary = {
        "distinct": len(accessions_by_location),
        "updated": len(updates),
        "resolved": resolved,
        "unresolved": unresolved,
    }
    logger.info(
        "Location normalization finished: %s distinct, %s resolved, %s unresolved",
        summary["distinct"],
        summary["resolved"],
        summary["unresolved"],
    )
    return summary


LOCATION_NORMALIZED_MAX_LENGTH = 100


def get_curation_row(
    database_service: DatabaseService,
    accession_id: str,
) -> dict | None:
    """Return accession location fields for manual curation, or None if not found."""
    rows = database_service.get_record_by_filters(
        entity_class=GenbankSequenceDataEntity,
        and_filters=[GenbankSequenceDataEntity.accession_id == accession_id],
        order_column="accession_id",
        order_desc=False,
        all_records=False,
    )
    if not rows:
        return None

    row = rows[0]
    return {
        "accession_id": row["accession_id"],
        "location": row["location"],
        "location_normalized": row["location_normalized"],
    }


def curate_location_normalized(
    database_service: DatabaseService,
    accession_id: str,
    location_normalized: str,
) -> dict | None:
    """Set location_normalized on a single row. Returns updated row snapshot or None."""
    row = get_curation_row(database_service, accession_id)
    if row is None:
        return None

    database_service.update_bulk(
        GenbankSequenceDataEntity,
        [
            {
                "accession_id": accession_id,
                "location_normalized": location_normalized,
            }
        ],
    )
    return {
        **row,
        "location_normalized": location_normalized,
    }
