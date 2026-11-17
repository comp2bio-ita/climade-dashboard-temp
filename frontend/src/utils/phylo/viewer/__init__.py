"""Phylogenetic tree rendering: tree text in, Plotly figure out.

Vendored from the standalone `phylotree` reference application (MIT, see LICENSE).
Nothing here knows about the database, the job queue, or Dash — the only inputs
are tree text (Newick or TreeTime NEXUS) and a metadata table.
"""

from .annotate import MetadataAnnotator, NullAnnotator, TipStyle, ncbi_url
from .model import PhyloTree, TreeNode
from .parse import NewickParseError, parse_newick, read_newick
from .render import figure_to_html, layout_coordinates, render_timetree, render_tree
from .theme import CATEGORICAL, LIGHT

__all__ = [
    "MetadataAnnotator",
    "NullAnnotator",
    "TipStyle",
    "ncbi_url",
    "PhyloTree",
    "TreeNode",
    "NewickParseError",
    "parse_newick",
    "read_newick",
    "render_tree",
    "render_timetree",
    "layout_coordinates",
    "figure_to_html",
    "LIGHT",
    "CATEGORICAL",
]
