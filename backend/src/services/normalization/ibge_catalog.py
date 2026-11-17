import gzip
import json
import logging
from pathlib import Path
from typing import Any

import requests

from services.normalization.text import normalize_text

logger = logging.getLogger(__name__)

IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
DEFAULT_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "geo" / "ibge_municipios.json"


class IbgeCatalog:
    def __init__(
        self,
        uf_lookup: dict[str, dict[str, str]],
        municipality_lookup: dict[tuple[str, str], str],
    ) -> None:
        self.uf_lookup = uf_lookup
        self.municipality_lookup = municipality_lookup


def _extract_uf(municipality: dict[str, Any]) -> dict[str, str] | None:
    microrregiao = municipality.get("microrregiao")
    if not microrregiao:
        return None

    mesorregiao = microrregiao.get("mesorregiao")
    if not mesorregiao:
        return None

    uf = mesorregiao.get("UF")
    if not uf:
        return None

    return {"name": uf["nome"], "sigla": uf["sigla"]}


def build_indexes(municipalities: list[dict[str, Any]]) -> IbgeCatalog:
    uf_lookup: dict[str, dict[str, str]] = {}
    municipality_lookup: dict[tuple[str, str], str] = {}

    for municipality in municipalities:
        uf = _extract_uf(municipality)
        if uf is None:
            continue

        uf_record = {"name": uf["name"], "sigla": uf["sigla"]}
        uf_lookup[normalize_text(uf["name"])] = uf_record
        uf_lookup[normalize_text(uf["sigla"])] = uf_record

        municipality_name = municipality["nome"]
        municipality_lookup[(uf["sigla"], normalize_text(municipality_name))] = municipality_name

    return IbgeCatalog(uf_lookup=uf_lookup, municipality_lookup=municipality_lookup)


def _fetch_municipalities_from_api() -> list[dict[str, Any]]:
    response = requests.get(
        IBGE_MUNICIPIOS_URL,
        headers={"Accept-Encoding": "gzip"},
        timeout=120,
    )
    response.raise_for_status()

    content = response.content
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)

    return json.loads(content.decode("utf-8"))


def load_ibge_catalog(cache_path: Path | None = None) -> IbgeCatalog:
    cache_file = cache_path or DEFAULT_CACHE_PATH

    if cache_file.is_file():
        logger.info("Loading IBGE catalog from cache: %s", cache_file)
        with cache_file.open(encoding="utf-8") as handle:
            municipalities = json.load(handle)
        return build_indexes(municipalities)

    logger.info("Fetching IBGE municipalities catalog")
    municipalities = _fetch_municipalities_from_api()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("w", encoding="utf-8") as handle:
        json.dump(municipalities, handle, ensure_ascii=False)
    logger.info("Cached IBGE catalog at %s", cache_file)
    return build_indexes(municipalities)
