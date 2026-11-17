# Dashboard Infra Repository

This repo was created to keep the cloud infra config files and steps

## Setting up .env files

Before running the container, make sure to create `.env` files in the root folder of this directory `./` and in `src/`. You can use the .env.example files as a guide.

Required environment variables:

- `MYSQL_ROOT_PASSWORD` 
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `DASH_HOST=mysql` (change this velue to point to databases hosted in different environments)
- `DASH_PORT=3306` (change this for a mysql database being exposed in any non-default port)
- `DASH_USER`
- `DASH_PASSWORD`
- `DASH_DATABASE`
- `NCBI_EMAIL`
- `NCBI_API_KEY`
- `BACKEND_MEMORY_LIMIT=4G` (change this to obtain improved performance with Nexclade runs)
- `CA_CERT_PATH=` (necessary if running the container within internal servers)


## Dependencies

### Main environment dependencies

- Docker (for production or containerized execution)
- Miniconda (for local non-containerized execution)

### 

The dependencies for the processing pipeline are listed in the `environment.yml` file, including:

- fasttree
- pandas=2.2.3
- biopython=1.85
- requests=2.32.3
- duckdb=1.1.1
- sqlalchemy=2.0.35
- pymysql
- cryptography
- iqtree
- nextclade
- mysql-connector-python==9.0.0
- pydantic==2.9.2
- pydantic-settings==2.5.2
- python-dotenv==1.0.1

## Setting up a conda environment for local runs

Creating the environment:
```bash
conda create -f environment.yml
```

Activating the environment:
```bash
conda env activate climade-dashboard
```

## Setting up the containers for isolated or production runs

```bash
docker compose --env-file .env up --build -d
```
