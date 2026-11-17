# Development data

## `dengue_phylo_dev_accessions.tsv`

Seven **DENV2 complete-genome** accessions from Brazil (`Homo sapiens`), selected from `dengue_dataset_2026_05_07.tsv` for biologically coherent local phylo validation.

**Selection criteria (TSV metadata + Entrez title/length check):**

| Filter | Value |
|--------|--------|
| `serotype` | DENV2 only |
| `genotype` | `2III` (assigned) |
| `country` | Brazil |
| `host` | Homo sapiens |
| Locus (Entrez) | `complete genome` in record title; length ~10.5–10.7 kb |

**Why not the previous 5-accession set?** It mixed DENV1–4, complete genomes, and short partial CDSs (mostly E gene / polyprotein), producing MAFFT alignments that are technically valid but biologically weak.

**Limitations:** single serotype, single country, one genotype (`2III`); suitable for pipeline dev, not publication epidemiology.

**Validation (from `backend/`):**

```bash
python -m phylo_module.validation.stage_01_validate_fasta_fetch
python -m phylo_module.validation.stage_02_validate_alignment
python -m phylo_module.validation.stage_03_validate_fasttree
python -m phylo_module.validation.stage_04_smoke_test_pipeline
```

Stages 01–03: file-only. Stage 04: full pipeline + MySQL (`phylo_dengue_tb`).

Documented in [phylo_module/README.md](../../phylo_module/README.md) and [phylo_module/docs/08_dev_dataset_seed.md](../../phylo_module/docs/08_dev_dataset_seed.md).
