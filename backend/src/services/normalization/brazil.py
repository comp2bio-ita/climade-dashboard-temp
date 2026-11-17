"""Brazil location normalization using official IBGE names for output."""

import logging

from services.normalization.ibge_catalog import IbgeCatalog, load_ibge_catalog
from services.normalization.text import normalize_text, parse_location

logger = logging.getLogger(__name__)

LOCATION_MAX_LENGTH = 100

_catalog: IbgeCatalog | None = None


def _get_catalog() -> IbgeCatalog:
    global _catalog
    if _catalog is None:
        _catalog = load_ibge_catalog()
    return _catalog


def set_catalog(catalog: IbgeCatalog | None) -> None:
    """Replace the cached catalog (used by tests)."""
    global _catalog
    _catalog = catalog


def _lookup_uf(component: str, catalog: IbgeCatalog) -> dict[str, str] | None:
    return catalog.uf_lookup.get(normalize_text(component))


def _is_sigla_component(component: str, uf_record: dict[str, str]) -> bool:
    normalized = normalize_text(component)
    return len(normalized) == 2 and normalized == normalize_text(uf_record["sigla"])


def _municipality_in_uf(component: str, uf: dict[str, str], catalog: IbgeCatalog) -> bool:
    return (uf["sigla"], normalize_text(component)) in catalog.municipality_lookup


def _resolve_state_and_municipality(
    first: str,
    second: str,
    catalog: IbgeCatalog,
) -> tuple[dict[str, str], str] | None:
    first_uf = _lookup_uf(first, catalog)
    second_uf = _lookup_uf(second, catalog)

    if first_uf and not second_uf:
        return first_uf, second
    if second_uf and not first_uf:
        return second_uf, first
    if not first_uf or not second_uf:
        return None

    if first_uf["sigla"] != second_uf["sigla"]:
        return None

    if _is_sigla_component(first, first_uf) and not _is_sigla_component(second, second_uf):
        return first_uf, second
    if _is_sigla_component(second, second_uf) and not _is_sigla_component(first, first_uf):
        return second_uf, first

    if _municipality_in_uf(second, first_uf, catalog):
        return first_uf, second
    if _municipality_in_uf(first, second_uf, catalog):
        return second_uf, first

    return None


def _format_brazil_canonical(
    country: str | None,
    state: dict[str, str],
    municipality_name: str,
) -> str:
    """Build the canonical string from IBGE catalog values only."""
    country_token = country if country else "Brazil"
    return f"{country_token}: {state['name']}, {municipality_name}"


def normalize_brazil_location(location: str, catalog: IbgeCatalog | None = None) -> str | None:
    country, parts = parse_location(location)

    if len(parts) != 2:
        return None

    first, second = parts
    catalog = catalog or _get_catalog()

    resolved = _resolve_state_and_municipality(first, second, catalog)
    if resolved is None:
        return None

    state, municipality = resolved
    municipality_name = catalog.municipality_lookup.get(
        (state["sigla"], normalize_text(municipality))
    )
    if municipality_name is None:
        return None

    canonical = _format_brazil_canonical(country, state, municipality_name)

    if len(canonical) > LOCATION_MAX_LENGTH:
        logger.warning(
            "Canonical Brazil location exceeds %s characters and was left unresolved: %s",
            LOCATION_MAX_LENGTH,
            canonical,
        )
        return None

    return canonical
