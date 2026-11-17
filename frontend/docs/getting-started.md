# Getting started

**Purpose**: run this dashboard locally so you can inspect pages, filters, and phylogeny against a live MySQL database.

**Scientific context**: the app is a visualisation client. Metadata and completed trees are produced by the companion backend (`dash_infra`) and read here from MySQL.

**Decision rationale**: database credentials and the listen port live in `.env`. Tunable scientific thresholds live in `src/config.py`. Library versions are pinned in `requirements.txt`.

To run this dashboard, use Python (section 2). Use this repository's Dockerfiles (section 3) only if you need a container.

---

## 1. Database

This app will not start without a populated MySQL database: each pathogen page loads its metadata table at import.

Get credentials from one of:

- An account you already have.
- The project lead, if you do not have access yet.
- A local copy from `dash_infra`. That repository’s Docker Compose stack starts MySQL; its pipeline scripts create the schema and load metadata. Follow that repo. This frontend does not start or populate the database.

Copy `.env.example` to `.env` at this repository root and fill only the MySQL fields:

```
DASH_HOST=
DASH_PORT=
DASH_USER=
DASH_PASSWORD=
DASH_DATABASE=
```

Point those at whichever instance you chose. Do not copy host, port, or database names from this file; they belong to whoever runs MySQL.

Maps and charts work from the metadata tables alone. A tree request writes a `pending` row to `phylo_tb` and stays there until the backend job process marks it `done`. See `dash_infra` for that process.

---

## 2. Python environment

From the repository root, with a virtualenv:

```bash
pip install -r requirements.txt
```

`APP_PORT` in `.env` must be `5500` for development. Completeness thresholds, tip limits, and poll interval stay in `src/config.py`.

```bash
cd src
python app.py
```

Open http://localhost:5500. Do not use port `5000`; that is the production service.

---

## 3. Docker (this app only)

These images run the Dash process. They do not start MySQL. The container still needs the `DASH_*` values from `.env`.

`Dockerfile.dev` is the image to run locally. It listens on `5500`, the same `APP_PORT` as `.env.example`. `Dockerfile.prod` is production and listens on `5000`.

```bash
docker build -f Dockerfile.dev -t climade-dashboard-dev .
docker run -p 5500:5500 --env-file .env --name climade-dashboard-dev -d climade-dashboard-dev
```

Production (not for local work):

```bash
docker build -f Dockerfile.prod -t climade-dashboard .
docker run -p 5000:5000 --env-file .env --name climade-dashboard -d climade-dashboard
```

`--env-file .env` supplies `DASH_*` and `APP_PORT` at run time. These images do not start MySQL.

---

## Inputs and outputs

**In:** a populated MySQL database and `.env` credentials. **Out:** a Dash app on the registered pathogen routes plus `/about`.

## Interpretation notes

A successful page load means metadata tables are reachable. It does not mean a phylogeny job will complete.

## Limitations

This app visualises rows already in MySQL. Ingestion and tree inference are in `dash_infra`.
