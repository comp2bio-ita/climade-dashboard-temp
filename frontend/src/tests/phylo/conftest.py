#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Shared fixtures.

`example.nwk` is real IQ-TREE output (202 tips, SH-aLRT support, pipe-delimited
Los Alamos labels), so the suite exercises the shapes that actually arrive from
a pipeline rather than only hand-written toy trees.
"""

from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "fixtures"

# Four tips, two clades, SH-aLRT support on both internal nodes.
SIMPLE_NEWICK = "((A:0.1,B:0.2)95:0.3,(C:0.15,D:0.25)80:0.05);"

# No branch lengths anywhere — a pure cladogram.
CLADOGRAM_NEWICK = "((A,B),(C,D));"

# Trifurcation: layouts must not assume strictly binary trees.
POLYTOMY_NEWICK = "(A:0.1,B:0.2,C:0.3,D:0.4);"

# Unnamed tips, and one duplicated label.
MESSY_NEWICK = "((:0.1,B:0.2):0.3,(B:0.15,:0.25):0.05);"


@pytest.fixture
def simple_newick():
    return SIMPLE_NEWICK


@pytest.fixture
def cladogram_newick():
    return CLADOGRAM_NEWICK


@pytest.fixture
def polytomy_newick():
    return POLYTOMY_NEWICK


@pytest.fixture
def messy_newick():
    return MESSY_NEWICK


@pytest.fixture(scope="session")
def example_tree_path():
    path = EXAMPLES / "example.nwk"
    if not path.exists():  # pragma: no cover
        pytest.skip("examples/example.nwk is missing")
    return path


@pytest.fixture(scope="session")
def example_newick(example_tree_path):
    return example_tree_path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def example_metadata_path():
    path = EXAMPLES / "example_metadata.csv"
    if not path.exists():  # pragma: no cover
        pytest.skip("examples/example_metadata.csv is missing")
    return path


@pytest.fixture(scope="session")
def timetree_path():
    path = EXAMPLES / "example_timetree.nexus"
    if not path.exists():  # pragma: no cover
        pytest.skip("examples/example_timetree.nexus is missing")
    return path


@pytest.fixture(scope="session")
def timetree_nexus(timetree_path):
    """Real TreeTime output: 25 dengue accessions, root 1910.3, tips 2025-2026.

    Branch lengths are years and every node carries [&mutations=...,date=...],
    so this is the fixture that exercises the calendar axis end to end.
    """
    return timetree_path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def pipeline_newick():
    """The IQ-TREE substitution tree from the same run as `timetree_nexus`.

    Same 25 accessions, branch lengths in substitutions per site rather than
    years — the pair the dashboard has to keep distinct.
    """
    path = EXAMPLES / "pipeline_tree.nwk"
    if not path.exists():  # pragma: no cover
        pytest.skip("fixtures/pipeline_tree.nwk is missing")
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def ladder_newick():
    """A 2000-tip ladder tree — maximally deep, minimally wide.

    This is the shape that makes a recursive layout raise RecursionError, so
    it is the regression guard for the iterative traversals.
    """
    newick = "T0:0.01"
    for i in range(1, 2000):
        newick = f"({newick},T{i}:0.02):0.01"
    return newick + ";"
