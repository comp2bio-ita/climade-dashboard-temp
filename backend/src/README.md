# Dashboard Backend

This folder contains the Dashboard Backend scripts, including:

-   The pipelines for data retrieving and processing
-   Functions to fetch metadata from Ncbi
-   Functions to fetch sequence data from Entrez Ncbi
-   Classes to connect to the dashboard database
-   Model Classes to parse data

## Schema changes for existing databases

`create_db_schema.py` only creates missing tables. To add columns to existing tables, run the matching SQL manually. See [database/alter_add_location_normalized.sql](database/alter_add_location_normalized.sql).

## Backend Pipeline
The backend pipeline was built to pull metadata from NCBI/GenBank, run nextclade to obtain accurate serotype and genotype classifications, and then load the output into the CLIMADE Dashboard's database. 

This pipeline can be executed by running:
``` python
pyhton pipeline_controller.py
```

or by manually running each stage script located in the `./pipeline` directory:
```python
python -m pipeline.stage_X_cccccc
```


## Phylo Process CLI

This pipeline serves as a background process that need to be activated to support phylogenetic analysis in the dashboard.

Executing the pipeline:
```
python pipeline_cli.py run
```

Usage instructions:
```
python pipeline_cli.py -h
```