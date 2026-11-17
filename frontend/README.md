# CLIMADE Dashboard

## Project Overview

This dashboard visualises publicly available genomic surveillance data for arboviruses. For a selected date window, geography, host, and classification, it shows where genomes have been reported, which lineages are circulating, and how that mix has changed over time. On the same filter, a user can request a phylogenetic tree of the selected GenBank accessions.

## Scientific Context

The app continues the PathoTrack line of genomic dashboards: near-real-time views of arboviral sequence metadata sourced from GenBank. It supports outbreak-oriented questions (which classification is circulating where, over which dates) without treating sequence counts as incidence. Phylogeny is an on-demand view of the filtered accession set.

This repository is the Plotly Dash frontend. Classification and tree building live in a companion backend (`dash_infra`). The two codebases share a MySQL database and have no HTTP API between them.

## Environment Setup

Library versions are pinned in `requirements.txt`.

**Database.** Copy `.env.example` to `.env` and fill the `DASH_*` fields. Use credentials you already have, or ask the project lead for access. To run a local MySQL and load metadata, use the Docker setup in the companion backend (`dash_infra`). This repository does not start the database.

To run this dashboard, use Python. Use this repository's Dockerfiles only if you need a container.

**Python.** `pip install -r requirements.txt`, then:

```bash
python src/app.py
```

Open http://localhost:5500.

**Docker.** Optional. `Dockerfile.dev` on port `5500` is the local image; `Dockerfile.prod` on port `5000` is production. Commands are in [docs/getting-started.md](docs/getting-started.md). Neither image includes MySQL.

## Contribution Rules

Work against `dev`; production deploys from `main`. Tag a release with Semantic Versioning (`vMAJOR.MINOR.PATCH`). The commands are in [docs/git-version-tags.md](docs/git-version-tags.md).

The virus pages share one layout. What makes each virus different (which table it reads, which colours it uses, which filters it shows) is listed in `src/pathogens.py`. [docs/architecture.md](docs/architecture.md) is the place to start before changing that.

A preprint of the dashboard is at [doi.org/10.21203/rs.3.rs-9889257/v1](https://doi.org/10.21203/rs.3.rs-9889257/v1).

## Prerequisites Reference

Review the knowledge prerequisites before contributing: [docs/prerequisites.md](docs/prerequisites.md)

## Documentation Index

Read in this order:

1. [docs/prerequisites.md](docs/prerequisites.md): scientific concepts this codebase assumes (accessions, classifications, trees).
2. [docs/getting-started.md](docs/getting-started.md): database access, Python and Docker runs.
3. [docs/architecture.md](docs/architecture.md): Dash shell, shared MySQL, and where to put new code.
4. [docs/data-model.md](docs/data-model.md): MySQL tables, the accession join, and the `phylo_tb` job contract.
5. [docs/dashboard.md](docs/dashboard.md): shared pathogen page, filters, map, and temporal charts.
6. [docs/phylogeny.md](docs/phylogeny.md): requesting a tree, the two artifacts (substitution vs dated), and the viewer.
7. [docs/git-version-tags.md](docs/git-version-tags.md): how to tag a release.
