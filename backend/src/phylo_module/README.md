# Phylogenetic module (`phylo_module`)

## Project Overview

`phylo_module` builds phylogenetic artifacts from **filtered GenBank accession lists** for the arbovirus epidemiological dashboard backend. It fetches nucleotide sequences, aligns whole genomes with MAFFT, infers nucleotide trees with FastTree, and persists Newick output for dashboard integration.

**Scientific outputs:**

- On disk: multi-FASTA, aligned multi-FASTA, Newick (`.nwk`), dated tree (`timetree.nexus`)
- In MySQL: `phylo_tb` rows (`pathogen`, `newick`, `time_tree_nexus`, run audit, `accession_set_hash`, `inference_method`)

**Implemented:** Entrez FASTA retrieval, MAFFT alignment, FastTree and IQ-TREE inference (with UFBoot/SH-aLRT support), TreeTime temporal analysis, staged validation (01–07), `run_dengue_phylo_pipeline` orchestration, job-queue watcher, `phylo_tb` persistence, frontend job insert + poll + Biopython/Plotly tree rendering.

**Not implemented:** per-locus partial-CDS trees, continent filter in accession resolver, dashboard rendering of the dated tree.

## Scientific Context

The dashboard stores **metadata and classifications** in MySQL. Phylogenetic inference requires **sequence files** and external CLI tools. Two paths coexist:

1. **Stages 01–03** — file-only dev smoke tests with fixed artifact names and the seven-accession dev TSV.
2. **`run_dengue_phylo_pipeline`** — dynamic accession lists from dashboard filters, per-run artifacts under `data/runs/`, Newick persisted for frontend load.

Validated decisions and planned extensions: [docs/dev-notes.md](docs/dev-notes.md).

## Environment Setup

**Python dependencies** (repo root):

```bash
pip install -r requirements.txt
```

**Bioinformatics tools** (not in `requirements.txt`):

```bash
conda install -c bioconda mafft fasttree
```

**Credentials:** `backend/.env` from `backend/.env.example` — at minimum `NCBI_EMAIL` for Entrez. Stage 04 and the production pipeline also need `DASH_*` pointing at local or server MySQL with `phylo_tb` created (`python database/create_db_schema.py`).

**Run from `backend/`:**

```bash
cd backend

# File-only dev path (no MySQL required)
python -m phylo_module.validation.stage_01_validate_fasta_fetch
python -m phylo_module.validation.stage_02_validate_alignment
python -m phylo_module.validation.stage_03_validate_fasttree

# Orchestrated path (MySQL + Entrez + MAFFT + FastTree)
python -m phylo_module.validation.stage_04_smoke_test_pipeline

# Job queue manual test (watcher must already be running)
python -m phylo_module.validation.stage_05_validate_job_queue
```

| Stage | Primary output |
|-------|----------------|
| 01 | `data/sequences/dev_validation.fasta` |
| 02 | `data/alignments/dev_validation_aligned.fasta` |
| 03 | `data/trees/dev_validation_tree.nwk` |
| 04 | `phylo_tb` row + `data/runs/<hash>/` artifacts |
| 05 | `phylo_tb` pending job → watcher fills same row (`done`) |

Dev accession seed: [../data/dev/dengue_phylo_dev_accessions.tsv](../data/dev/dengue_phylo_dev_accessions.tsv) — [docs/08_dev_dataset_seed.md](docs/08_dev_dataset_seed.md).

## Contribution Rules

- **Documentation:** validated rationale in [docs/dev-notes.md](docs/dev-notes.md) first, then formal `docs/` files.
- **Pipeline code:** reusable logic in `services/` and `pipeline_phylo.py`; ordered smoke tests in `validation/stage_XX_*.py`.
- **Artifacts:** generated `*.fasta` and `*.nwk` under `data/` are gitignored; commit TSV seeds and source only.
- **Execution:** invoke validation as `python -m phylo_module...` from `backend/`, not by file path from repo root.

<!-- DECISION RATIONALE: branch naming and versioning strategy to be documented by maintainer -->

## Prerequisites Reference

> Review the knowledge prerequisites before contributing: [docs/prerequisites.md](docs/prerequisites.md)

## Documentation Index

| Document | Purpose |
|----------|---------|
| [docs/prerequisites.md](docs/prerequisites.md) | Concepts required to understand the module (Entrez, FASTA, alignment, Newick, DENV context). |
| [docs/01_module_overview.md](docs/01_module_overview.md) | Scope, dual execution paths, and MVP limitations. |
| [docs/02_project_structure.md](docs/02_project_structure.md) | Directories, services, pipeline, stages, and artifact paths. |
| [docs/03_fasta_retrieval.md](docs/03_fasta_retrieval.md) | Entrez fetch, `fasta_service`, stage 01. |
| [docs/04_alignment.md](docs/04_alignment.md) | MAFFT alignment, `alignment_service`, stage 02. |
| [docs/05_fasttree_inference.md](docs/05_fasttree_inference.md) | FastTree Newick output, `tree_service`, stage 03. |
| [docs/06_tree_validation.md](docs/06_tree_validation.md) | Verify and interpret Newick — file path and stage 04 checks. |
| [docs/07_metadata_linkage.md](docs/07_metadata_linkage.md) | `phylo_tb` vs `dengue_meta_tb` tip join (implemented on frontend). |
| [docs/08_dev_dataset_seed.md](docs/08_dev_dataset_seed.md) | Dev accession TSV and full export filter source. |
| [docs/09_pipeline_orchestration.md](docs/09_pipeline_orchestration.md) | `run_dengue_phylo_pipeline`, persistence, caps, `data/runs/`, stage 04. |
| [docs/10_job_queue_validation.md](docs/10_job_queue_validation.md) | Manual job-queue test (stage 05): insert `pending`, watcher → `done`. |
| [docs/dev-notes.md](docs/dev-notes.md) | Append-only validated decisions and planned extensions. |

**Repo-level backend local setup (Docker MySQL, pipeline denylist):** [../../docs/LOCAL_DEVELOPMENT.md](../../docs/LOCAL_DEVELOPMENT.md)

**Unit tests:** `tests/test_*_service.py` (mocked Entrez and CLI).
