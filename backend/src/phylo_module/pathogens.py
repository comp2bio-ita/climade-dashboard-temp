"""Which metadata table a phylo job reads, keyed by the job's pathogen.

phylo_tb.pathogen carries the value the dashboard wrote. The pipeline resolves the metadata
entity through this registry rather than naming one, so supporting another arbovirus is a
line here and nothing in the watcher or the inference stages.

Naming: the canonical value is the WHO virus abbreviation — DENV, CHIKV, ZIKV — which is what
the column has held since 2026-08-08. Each also accepts its full lowercase name, because the
rows written before that date used that form and their trees are still reusable. Full names
are for display and stay on the dashboard side; they never appear in this column.

The frontend keeps its own registry (arboviruses-dashboard/src/pathogens.py). The two repos
share no code, only the MySQL database, so these names are the contract between them.
"""

from models.database_models import (
    ChikungunyaMetaEntity,
    DengueMetaEntity,
    YellowFeverMetaEntity,
    ZikaMetaEntity,
)

PATHOGEN_META_ENTITIES = {
    "DENV": DengueMetaEntity,
    "CHIKV": ChikungunyaMetaEntity,
    "ZIKV": ZikaMetaEntity,
    "YFV": YellowFeverMetaEntity,
}

# One full name per abbreviation, for rows written before the column settled on the WHO form
PATHOGEN_FULL_NAMES = {
    "dengue": "DENV",
    "chikungunya": "CHIKV",
    "zika": "ZIKV",
    "yellow fever": "YFV",
    "yellow-fever": "YFV",
}


def canonical_pathogen(pathogen):
    if not pathogen:
        raise ValueError(
            "phylo job carries no pathogen; the dashboard must write one of "
            f"{sorted(PATHOGEN_META_ENTITIES)}"
        )
    name = str(pathogen).strip()
    return PATHOGEN_FULL_NAMES.get(name.lower(), name.upper())


def meta_entity_for(pathogen):
    """The metadata table for this pathogen, or a clear failure for an unregistered one."""
    name = canonical_pathogen(pathogen)
    entity = PATHOGEN_META_ENTITIES.get(name)
    if entity is None:
        raise ValueError(
            f"phylo job names an unregistered pathogen {pathogen!r}; "
            f"register it in phylo_module/pathogens.py (known: {sorted(PATHOGEN_META_ENTITIES)})"
        )
    return entity
