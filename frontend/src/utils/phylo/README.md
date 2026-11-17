# `utils.phylo` — the phylogeny feature

Everything between a completed pipeline job and a tree on screen.

## Public interface

```python
from utils.phylo import (
    evaluate_phylo_eligibility,   # can this filter produce a tree at all?
    load_phylogeny_status,        # progress of a running job
    load_phylogeny_result,        # the finished job, as the viewer needs it
    phylogeny_panel,              # the layout to drop into a page
    register_phylogeny_callbacks, # wire that layout to a result store
)
```

A page uses it in two lines:

```python
PHYLO_PREFIX = "dengue-phylo"
PHYLO_RESULT_STORE = "dengue-phylo-result"

# ... inside layout():
phylogeny_panel(PHYLO_PREFIX)

# ... at module scope:
register_phylogeny_callbacks(callback, PHYLO_PREFIX, PHYLO_RESULT_STORE)
```

`register_phylogeny_callbacks` takes a Dash app **or** Dash's module-level `callback`. A Dash
Pages module is imported before any app exists, so a page passes `callback`.

Every component id comes from `panel_ids(prefix)`. Two pathogens can each mount a viewer on the
same page without colliding, and no per-session state is stored anywhere in this package.

## Data flow

```
phylo_tb row (written by the dash_infra watcher)
   │  while running: get_phylo_job_status  — status, event log, no tree text
   │  once, on done: get_phylo_job_result  — both trees, provenance
   ▼
result_provider.load_phylogeny_result(database_client, job_id)
   ├─ parses tip accessions off the substitution Newick
   ├─ joins the pathogen's meta table through get_tip_metadata (resolved from src/pathogens.py)
   ├─ reports matched / unmatched / duplicated metadata keys
   └─ compares the substitution and dated tip sets
   ▼
dcc.Store  — a plain JSON dictionary, the viewer's only input
   ▼
panel.build_phylogeny_figure  →  viewer.render_tree  →  dcc.Graph
```

The page owns job submission and polling. The panel owns the figure. Neither reaches across:
there is no SQL in a viewer callback, and the viewer never sees a database client.

## Files

| File | Responsibility |
|---|---|
| `precheck.py` | Whether the current filter yields enough usable sequences. Pure. |
| `result_provider.py` | The only database-aware file. Job row → result dictionary. |
| `panel.py` | Layout **and** its callbacks, together. Figure assembly, provenance notes, tip detail. |
| `viewer/` | Tree text → Plotly figure. Knows nothing about Dash, the database, or dengue. |

### `viewer/`

| File | Responsibility |
|---|---|
| `parse.py` | Newick and TreeTime NEXUS → `PhyloTree`, via Biopython |
| `model.py` | `PhyloTree` / `TreeNode`, iterative traversals |
| `layouts/` | Coordinates only: rectangular (incl. time trees), circular, radial |
| `render.py` | Plotly traces, labels, legends, hover, axes |
| `annotate.py` | Metadata join, tip colour and hover, join reporting |
| `theme.py` | Palette |

## The two trees

A completed job carries **two different trees** and they are never interchanged:

- `newick` — the IQ-TREE or FastTree result. Branch lengths are **substitutions per site**.
  This is the only tree carrying branch support.
- `time_tree_nexus` — the TreeTime result, stored verbatim as NEXUS. Branch lengths are
  **years**, and the x-axis is a calendar. This is the only tree carrying dates.

`time_tree_nexus` is NULL whenever the temporal stage was skipped (too few dated sequences) or
failed. That is a normal outcome, not a job failure. When it is absent the Time option is
disabled with a reason and the panel says so — the substitution tree is never relabelled as
time-scaled.

Neither artifact is ever rewritten. A NEXUS round trip through Newick mangles the tip labels into
escaped comment text, and those labels are the GenBank accessions the metadata join depends on,
so the stored text goes to the parser exactly as the backend wrote it.

## Provenance

`viewer/` is vendored from the standalone `phylotree` reference application (MIT — see
`viewer/LICENSE`), which remains the working reference for this renderer. Only the reusable
visualization slice was taken: its Dash app, routing, upload interface, and page shell were not.
Two dashboard-specific changes were made to `annotate.py` — a value-keyed `color_map` so serotype
and genotype match the colours used by the bar chart and the map, and `join_report()` so metadata
mismatches are counted rather than silently absorbed into a "No metadata" legend group.

## Tests

```bash
venv/bin/python -m pytest              # from the repo root
```
