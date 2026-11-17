# Location normalization

Canonicalizes geographic `location` strings into `location_normalized` for supported countries. Brazil uses IBGE official names (UF + município).

## Prerequisites

- MySQL with `location_normalized` on `ncbi_sequence_data` (see `backend/database/alter_add_location_normalized.sql`)
- `backend/.env` configured
- IBGE cache at `backend/data/geo/ibge_municipios.json` (auto-fetched on first run)

## CLI

Run from `backend/`:

```bash
# Batch: rows with location set but location_normalized still null
python -m services.normalization pending --country Brazil

# Manual curation: set location_normalized on one row (with confirmation)
python -m services.normalization curate \
  --accession-id NC_001477 \
  --value "Brazil: Minas Gerais, Belo Horizonte"

# Skip confirmation prompt (scripting)
python -m services.normalization curate \
  --accession-id NC_001477 \
  --value "Brazil: Minas Gerais, Belo Horizonte" \
  --yes
```

`--country Brasil` is accepted as an alias for `pending`.

## Pipeline

`pipeline_controller.py` runs normalization between stage 1 and stage 2 for all supported countries (currently Brazil/Brasil only).

## Tests

```bash
cd backend
python -m unittest discover -s services/normalization/tests
```

## Output format

`Country: division, locality` — e.g. `Brazil: Minas Gerais, Belo Horizonte`. Division and locality come from IBGE catalog values, not folded input text.
