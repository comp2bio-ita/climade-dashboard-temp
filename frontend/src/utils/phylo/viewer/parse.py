#!/usr/bin/env python
"""Newick / NEXUS -> PhyloTree, via Biopython."""


import io
import os
import re
import warnings
from pathlib import Path

with warnings.catch_warnings():
    # Biopython warns "you may be importing from inside the source tree"
    # whenever it finds a pyproject.toml above its install location — which is
    # true of any project whose virtualenv lives in the checkout. It says
    # nothing about this package, and it fires on every single startup.
    # Scoped to this import so no other Biopython warning is affected.
    warnings.filterwarnings(
        "ignore",
        message="You may be importing Biopython from inside the source tree",
    )
    from Bio import Phylo

from .model import PhyloTree, TreeNode

__all__ = ["parse_newick", "read_newick", "NewickParseError"]


class NewickParseError(ValueError):
    """Raised when the input is not a single readable tree."""


# TreeTime's per-node comment, e.g. [&mutations="T226C,C837T",date=2025.00].
_DATE_RE = re.compile(r"\bdate=([0-9]+(?:\.[0-9]+)?)")
_MUTATIONS_RE = re.compile(r'\bmutations="([^"]*)"')


def parse_newick(source):
    """Parse `source` into a :class:`~utils.phylo.viewer.model.PhyloTree`.

    Parameters
    ----------
    source
        Newick text, NEXUS text, a path to a tree file, an open text handle,
        or an already-parsed tree (returned unchanged, so callers can accept
        either).

    Raises
    ------
    NewickParseError
        On empty input, malformed input, a file that does not exist, or a
        Newick file holding more than one tree.
    """
    if isinstance(source, PhyloTree):
        return source

    text = _read_text(source)
    if not text.strip():
        raise NewickParseError("Empty input: no tree found.")

    # NEXUS carries several ';'-terminated statements in its header blocks, so
    # the multi-tree check below — a Newick rule — has to be skipped for it.
    nexus = _looks_like_nexus(text)
    if not nexus:
        _reject_multiple_trees(text)

    try:
        trees = list(Phylo.parse(io.StringIO(text), "nexus" if nexus else "newick"))
    except Exception as exc:  # Biopython raises a grab-bag of exception types
        raise NewickParseError(f"Could not parse tree: {exc}\n{_excerpt(text)}") from exc

    if not trees:
        raise NewickParseError(f"No tree found in input.\n{_excerpt(text)}")

    tree = _from_biopython(trees[0])
    if tree.n_tips == 0:
        raise NewickParseError(f"Parsed tree has no tips.\n{_excerpt(text)}")
    return tree


def read_newick(path):
    """Read a tree file from disk. Thin alias kept for call-site readability."""
    return parse_newick(Path(path))


# ── Internals ──────────────────────────────────────────────────────────────


def _looks_like_nexus(text):
    return text.lstrip().upper().startswith("#NEXUS")


def _reject_multiple_trees(text):
    """Refuse a Newick file holding several trees, before Biopython sees it.

    Bootstrap replicate files and IQ-TREE's ``.ufboot`` hold one tree per line.
    Left to Biopython these fail with "Text after semicolon", which does not
    tell the user what is actually wrong or what to do about it.
    """
    head, separator, tail = text.partition(";")
    if separator and tail.strip():
        count = text.count(";")
        raise NewickParseError(
            f"Input holds {count} trees; the viewer renders one at a time. "
            "Split the file, or pass a single tree."
        )


def _read_text(source):
    if hasattr(source, "read"):
        return source.read()

    if isinstance(source, (str, bytes, os.PathLike)):
        if isinstance(source, bytes):
            source = source.decode("utf-8", errors="replace")
        # Blank input is neither a tree nor a path; caught here so that ""
        # does not fall through and get resolved as the current directory.
        if isinstance(source, str) and not source.strip():
            return ""
        # Tree text always contains a paren or a semicolon; a path never does.
        # Checking content first avoids OSError on absurdly long strings.
        looks_like_tree = isinstance(source, str) and ("(" in source or ";" in source)
        if not looks_like_tree:
            path = Path(source)
            if not path.exists():
                raise NewickParseError(f"Tree file not found: {path}")
            return path.read_text(encoding="utf-8", errors="replace")
        return source

    raise NewickParseError(f"Unsupported source type: {type(source).__name__}")


def _from_biopython(bp_tree):
    """Convert a Bio.Phylo tree, iteratively, assigning stable node ids."""
    counter = 0

    def _new(clade, parent):
        nonlocal counter
        node = TreeNode(
            id=counter,
            branch_length=float(clade.branch_length or 0.0),
            parent=parent,
        )
        counter += 1
        return node

    root = _new(bp_tree.root, None)
    stack = [(bp_tree.root, root)]
    while stack:
        clade, node = stack.pop()
        is_tip = not clade.clades
        node.name = _node_name(clade, node.id, is_tip)
        if not is_tip:
            sh_alrt, ufboot = _support_metrics(clade)
            node.support_sh_alrt = sh_alrt
            node.support_ufboot = ufboot
            node.support = sh_alrt
        node.date, node.n_mutations = _temporal(clade)
        for child_clade in clade.clades:
            child = _new(child_clade, node)
            node.children.append(child)
            stack.append((child_clade, child))

    return PhyloTree(root)


def _node_name(clade, node_id, is_tip):
    """Tip label, guaranteed non-empty.

    Internal-node labels are support values (IQ-TREE, FastTree) or synthetic
    node ids (TreeTime's ``NODE_0000001``) in practice, never anything worth
    drawing, so they are read by `_support` instead and not used as names.
    """
    if not is_tip:
        return ""
    name = (clade.name or "").strip()
    return name or f"tip_{node_id}"


def _parse_support_fields(text):
    if not text:
        return None, None
    raw = str(text).strip()
    if raw.upper().startswith("NODE_"):
        return None, None
    parts = [part.strip() for part in raw.split("/") if part.strip()]
    if not parts:
        return None, None
    try:
        sh_alrt = float(parts[0])
    except ValueError:
        return None, None
    ufboot = None
    if len(parts) > 1:
        try:
            ufboot = float(parts[1])
        except ValueError:
            pass
    return sh_alrt, ufboot


def _support_metrics(clade):
    """SH-aLRT and UFBoot from an internal node label.

    Biopython puts a purely numeric internal label in ``confidence`` and
    anything else in ``name``, so both have to be checked. IQ-TREE run with
    ``-alrt X -B Y`` writes ``"95/98"``. TreeTime's ``NODE_0000001`` ids
    parse as neither and correctly come back as (None, None).
    """
    conf = getattr(clade, "confidence", None)
    if conf is not None:
        sh_alrt, ufboot = _parse_support_fields(conf)
        if sh_alrt is not None:
            return sh_alrt, ufboot

    label = (getattr(clade, "name", None) or "").strip()
    return _parse_support_fields(label)


def _temporal(clade):
    """(date, mutation count) from a TreeTime node comment; (None, None) otherwise.

    TreeTime hangs ``[&mutations="T226C,C837T,...",date=2025.00]`` on every
    node of ``timetree.nexus``. The date is a decimal calendar year and is what
    puts the tree on a time axis. Only the *count* of mutations is kept: the
    list itself runs to tens of kilobytes on deep branches and nothing in the
    renderer can show it usefully.
    """
    comment = getattr(clade, "comment", None)
    if not comment:
        return None, None

    date_match = _DATE_RE.search(comment)
    date = float(date_match.group(1)) if date_match else None

    mutations_match = _MUTATIONS_RE.search(comment)
    n_mutations = None
    if mutations_match:
        listed = mutations_match.group(1).strip()
        n_mutations = len(listed.split(",")) if listed else 0

    return date, n_mutations


def _excerpt(text, limit=120):
    snippet = text.strip().replace("\n", " ")
    if len(snippet) > limit:
        snippet = snippet[:limit] + "..."
    return f"  Input began: {snippet}"
