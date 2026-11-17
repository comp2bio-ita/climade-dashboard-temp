"""The phylogeny feature: from a completed pipeline job to a rendered tree.

Three pieces, one direction of dependency:

    precheck         can the current filter produce a tree at all
    result_provider  job queue and database -> a plain result dictionary
    panel            that dictionary -> Dash layout and callbacks
    viewer/          tree text -> Plotly figure (knows nothing else)

A page uses it in two lines: drop `phylogeny_panel(prefix)` into the layout and
call `register_phylogeny_callbacks(...)` once at import. See README.md.
"""

from utils.phylo.panel import phylogeny_panel, register_phylogeny_callbacks
from utils.phylo.precheck import evaluate_phylo_eligibility
from utils.phylo.result_provider import load_phylogeny_result, load_phylogeny_status

__all__ = [
    "evaluate_phylo_eligibility",
    "load_phylogeny_result",
    "load_phylogeny_status",
    "phylogeny_panel",
    "register_phylogeny_callbacks",
]
