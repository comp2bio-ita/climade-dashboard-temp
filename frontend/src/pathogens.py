"""What differs between the three pathogen dashboards.

One entry per pathogen, so that adding another arbovirus over an existing metadata table
means registering it here rather than editing shared page code. Every value below is
transcribed from the page module named in its comment; this module changes no behavior on
its own.

Keys match components.download_btn.DOWNLOAD_CONFIG and the virus_key map in
components.header, so the three registries address pathogens the same way.
"""

from utils.color_schemes import (
    chikungunya_color_scheme,
    dengue_color_scheme,
    dengue_color_scheme_genotypes,
    yellow_fever_color_scheme,
    zika_color_scheme,
)
from utils.models.database_models import (
    ChikungunyaMetaEntity,
    DengueMetaEntity,
    YellowFeverMetaEntity,
    ZikaMetaEntity,
)

def dengue_genotypes_for_serotypes(selected_serotypes, all_genotypes):
    """DENV genotype labels start with their serotype's number, e.g. DENV2 -> 2I, 2II."""
    serotype_numbers = [serotype[-1] for serotype in selected_serotypes]
    return [genotype for genotype in all_genotypes
            for number in serotype_numbers if number in genotype]


PATHOGENS = {
    "denv": {
        "title": "Dengue",
        "route": "/dengue",
        "id_suffix": "denv",
        "meta_entity": DengueMetaEntity,

        # Dengue is the only pathogen with a second classification axis: genotypes are
        # derived from the selected serotypes (dengue_page.py:951).
        "classification_column": "serotype",
        "subclassification_column": "genotype",
        "classification_order": ["DENV1", "DENV2", "DENV3", "DENV4", "Unassigned"],
        "db_classification_name_map": {
            "DENV1": "DENV1", 
            "DENV2": "DENV2", 
            "DENV3": "DENV3", 
            "DENV4": "DENV4",
        },
        # The one behavioural hook in the registry: dengue narrows its genotype dropdown to
        # whatever the selected serotypes imply. Absent for a single-axis pathogen.
        "subclassification_from_classification": dengue_genotypes_for_serotypes,
        "color_scheme": dengue_color_scheme,
        "subclassification_color_scheme": dengue_color_scheme_genotypes,

        # Colour-by options offered by the phylogeny panel. Only dengue carries lineages.
        "phylo_metadata_fields": [
            "serotype", "genotype", "major_lineage", "minor_lineage", "country", "host",
        ],
        # Written to phylo_tb.pathogen: the WHO virus abbreviation, which is what the
        # column has held since 2026-08-08. Distinct from "title", which is what users see.
        "backend_pathogen_code": "DENV",

        "download_columns": [
            "genbank_sequence_data_id", "collection_date", "serotype", "genotype",
            "major_lineage", "minor_lineage", "country", "country_acr", "location", "host",
        ],
        "dataset_path": "data/dengue/Final_global_dengue.tsv",
    },

    "chikv": {
        "title": "Chikungunya",
        "route": "/chikungunya",
        "id_suffix": "chikv",
        "meta_entity": ChikungunyaMetaEntity,

        "classification_column": "genotype",
        "subclassification_column": None,
        "classification_order": ["ACL", "ECSA", "WA", "Unassigned"],
        "db_classification_name_map": {
            "ECSA": "ECSA", 
            "Asian": "ACL", 
            "WestAfrica": "WA"
        },
        "subclassification_from_classification": None,
        "color_scheme": chikungunya_color_scheme,
        "subclassification_color_scheme": None,

        "phylo_metadata_fields": ["genotype", "country", "host"],
        "backend_pathogen_code": "CHIKV",

        "download_columns": [
            "genbank_sequence_data_id", "collection_date", "genotype",
            "host", "country", "country_acr", "location",
        ],
        "dataset_path": "data/chikungunya/Final_global_chikv.tsv",
    },

    "zikv": {
        "title": "Zika",
        "route": "/zika",
        "id_suffix": "zikv",
        "meta_entity": ZikaMetaEntity,

        "classification_column": "genotype",
        "subclassification_column": None,
        "classification_order": ["African", "Asian", "Unassigned"],
        "db_classification_name_map": {
            "African": "African", 
            "Asian": "Asian"
        },
        "subclassification_from_classification": None,
        "color_scheme": zika_color_scheme,
        "subclassification_color_scheme": None,

        "phylo_metadata_fields": ["genotype", "country", "host"],
        "backend_pathogen_code": "ZIKV",

        "download_columns": [
            "genbank_sequence_data_id", "collection_date", "genotype",
            "host", "country", "country_acr", "location",
        ],
        "dataset_path": "data/zika/Final_global_zika.tsv",
    },

    "yfv": {
        "title": "Yellow Fever",
        "route": "/yellow-fever",
        "id_suffix": "yfv",
        "meta_entity": YellowFeverMetaEntity,

        "classification_column": "genotype",
        "subclassification_column": None,
        "classification_order": [
            "Angola", "East Africa", "East/Central Africa", "West Africa I",
            "West Africa II", "South America I", "South America II", "Unassigned",
        ],
        "db_classification_name_map": {
            "Angola": "Angola",
            "East Africa": "East Africa",
            "East/Central Africa": "East/Central Africa",
            "West Africa I": "West Africa I",
            "West Africa II": "West Africa II",
            "South America I": "South America I",
            "South America II": "South America II",
            "Unassigned": "Unassigned"
        },
        "subclassification_from_classification": None,
        "color_scheme": yellow_fever_color_scheme,
        "subclassification_color_scheme": None,

        "phylo_metadata_fields": ["genotype", "country", "host"],
        "backend_pathogen_code": "YFV",

        "download_columns": [
            "genbank_sequence_data_id", "collection_date", "genotype",
            "host", "country", "country_acr", "location",
        ],
        "dataset_path": "data/yellow_fever/Final_global_yfv.tsv",
    },
}


def get_pathogen(key):
    spec = PATHOGENS.get(key)
    if spec is None:
        raise KeyError(
            f"no pathogen registered under {key!r}; known keys: {sorted(PATHOGENS)}"
        )
    return spec


def pathogen_keys():
    return list(PATHOGENS)


def pathogen_by_title(title):
    """The spec whose display name is `title`, or None. The pathogen dropdown addresses
    pathogens by the name the user reads, so the header resolves them this way."""
    for spec in PATHOGENS.values():
        if spec["title"] == title:
            return spec
    return None
