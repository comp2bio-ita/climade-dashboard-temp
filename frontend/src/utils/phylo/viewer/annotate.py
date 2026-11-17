#!/usr/bin/env python
"""Tip styling from metadata — colour, legend group, hover, click URL."""


import re
from pathlib import Path

from utils.color_schemes import UNKNOWN_CATEGORY_COLOR

from .theme import CATEGORICAL, LIGHT

__all__ = [
    "TipStyle",
    "BaseAnnotator",
    "NullAnnotator",
    "MetadataAnnotator",
    "load_metadata",
    "candidate_keys",
    "ncbi_url",
    "is_accession",
    "DEFAULT_GROUP",
    "MISSING_GROUP",
]

DEFAULT_GROUP = "Tips"
MISSING_GROUP = "Unknown"

# NCBI nucleotide accessions: 1-2 letters + 5 digits (M12345), 2 letters +
# 6 digits (PX945878), 4-6 letters + 8-10 digits (WGS), or RefSeq's
# underscore form (NC_001802). An optional ".N" version suffix is allowed.
_ACCESSION_RE = re.compile(r"^[A-Z]{1,6}_?\d{5,10}(\.\d+)?$", re.IGNORECASE)

# Trailing "_2", "_3" ... added by preprocessing that has to disambiguate
# duplicate FASTA ids. Stripped when looking up metadata.
_DUP_SUFFIX_RE = re.compile(r"_\d+$")

_NCBI_NUCCORE = "https://www.ncbi.nlm.nih.gov/nuccore/{}"


# ── The style a tip is drawn with ──────────────────────────────────────────


class TipStyle:
    """Everything the renderer needs to draw and describe one tip.

    `color=None` means "use the palette default", which lets an annotator opt
    out of colouring without having to know what that default is.
    """

    def __init__(self, group=DEFAULT_GROUP, color=None, hover_rows=(),
                 symbol="circle", size=None, url=None):
        self.group = group
        self.color = color
        self.hover_rows = tuple(hover_rows)
        self.symbol = symbol
        self.size = size
        self.url = url

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"<TipStyle group={self.group!r} color={self.color!r}>"


class BaseAnnotator:
    """What :func:`utils.phylo.viewer.render.render_tree` requires of an annotator.

    Subclass and implement both methods: `style_for(label)` returning a
    :class:`TipStyle`, and `groups()` returning the legend groups in the order
    they should appear.
    """

    def style_for(self, label):  # pragma: no cover - abstract
        raise NotImplementedError

    def groups(self):
        return []


# ── Label normalisation ────────────────────────────────────────────────────


def candidate_keys(label):
    """Lookup keys for `label`, most specific first (see README tip matching)."""
    seen = []

    def _add(value):
        value = value.strip()
        if value and value not in seen:
            seen.append(value)

    _add(label)

    # Progressively narrow: split on delimiters, then strip suffixes off
    # whatever remains. Applying these cumulatively (rather than only to the
    # original) is what makes "PX945878.1|BR|2025" resolve to "PX945878".
    narrowed = [label]
    for delimiter in ("|", " ", "\t"):
        narrowed.append(narrowed[-1].split(delimiter)[0])

    for value in narrowed:
        _add(value)
        stripped = _DUP_SUFFIX_RE.sub("", value)
        if stripped != value:
            _add(stripped)
        # Only strip a version suffix off a value that is already a bare
        # identifier. Doing it while delimiters remain would treat the dot in
        # "ACC|Aedes aegypti 1.2" as a version and mangle the key — and it
        # would also emit the loose key ahead of the exact one.
        if "." in stripped and not any(d in stripped for d in ("|", " ", "\t")):
            _add(stripped.rsplit(".", 1)[0])

    return seen


def is_accession(label):
    """True when `label` (or its first field) looks like an NCBI accession."""
    return any(_ACCESSION_RE.match(key) for key in candidate_keys(label))


def ncbi_url(label):
    """NCBI nuccore URL for `label`, or None if it is not accession-shaped.

    The version suffix is kept when present — NCBI resolves both, and keeping
    it lands the user on the exact record the tree was built from.
    """
    for key in candidate_keys(label):
        if _ACCESSION_RE.match(key):
            return _NCBI_NUCCORE.format(key)
    return None


# ── Metadata loading ───────────────────────────────────────────────────────


def load_metadata(path):
    """Read a metadata table into a ``pandas.DataFrame``.

    Supports CSV, TSV/TXT (delimiter sniffed by pandas) and XLSX. The dashboard
    joins metadata from the database instead; this path exists for fixtures and
    for callers holding a table on disk.
    """
    import pandas as pd

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=str)
    if suffix in {".tsv", ".tab"}:
        return pd.read_csv(path, sep="\t", dtype=str)
    if suffix in {".csv"}:
        return pd.read_csv(path, dtype=str)
    # Unknown extension: let pandas sniff the separator.
    return pd.read_csv(path, sep=None, engine="python", dtype=str)


def _to_records(table):
    """Normalise a DataFrame / list-of-dicts / path into records + column order."""
    if isinstance(table, (str, Path)):
        table = load_metadata(table)

    if hasattr(table, "to_dict") and hasattr(table, "columns"):  # DataFrame
        columns = [str(c) for c in table.columns]
        records = table.astype(object).where(table.notna(), None).to_dict("records")
        return [{str(k): v for k, v in row.items()} for row in records], columns

    records = [dict(row) for row in table]
    columns = []
    for row in records:
        for key in row:
            if key not in columns:
                columns.append(str(key))
    return records, columns


# ── Annotator implementations ──────────────────────────────────────────────


class MetadataAnnotator(BaseAnnotator):
    """Colour and describe tips from a metadata table keyed on the tip label.

    The phylo pipeline's case: tree tips are accessions, and the epidemiological
    fields (serotype, genotype, lineage, country, host) come from a metadata
    table joined on that accession.

    Parameters
    ----------
    table
        The metadata: a DataFrame, a list of dicts, or a path loaded via
        :func:`load_metadata`.
    key_col
        Column holding the tip identifier. Defaults to the first column, which
        is the convention for accession-keyed tables.
    color_by
        Column driving tip colour and legend grouping. When omitted, every tip
        shares one group and the default colour.
    hover_cols
        Columns shown on hover. Defaults to every column except the key.
    palette
        Overrides the categorical palette. Colours are assigned by the order a
        value first appears in the table.
    color_map
        Fixed value-to-colour mapping, overriding `palette`. Use it when a
        category already has a meaning elsewhere — the dashboard's serotype and
        genotype colours have to match the bar chart and the map, so DENV-1 is
        the same colour wherever it is drawn.
    link_ncbi
        Attach an NCBI nuccore URL to accession-shaped labels. Default True.
    """

    def __init__(self, table, key_col=None, color_by=None, hover_cols=None,
                 palette=None, color_map=None, link_ncbi=True):
        self.records, self.columns = _to_records(table)
        if not self.columns:
            raise ValueError("Metadata table has no columns.")

        self.key_col = str(key_col) if key_col else self.columns[0]
        if self.key_col not in self.columns:
            raise ValueError(
                f"key_col {self.key_col!r} not in metadata columns: {self.columns}"
            )

        self.color_by = str(color_by) if color_by else None
        if self.color_by and self.color_by not in self.columns:
            raise ValueError(
                f"color_by {self.color_by!r} not in metadata columns: {self.columns}"
            )

        self.hover_cols = (
            [str(c) for c in hover_cols]
            if hover_cols is not None
            else [c for c in self.columns if c != self.key_col]
        )
        self.link_ncbi = link_ncbi
        self.palette = list(palette) if palette else list(CATEGORICAL)
        self.color_map = dict(color_map) if color_map else None

        self._index = self._build_index()
        self._group_order = self._build_group_order()
        self._cache = {}

    # -- construction helpers --

    def _build_index(self):
        """Map every key spelling in the table to its row.

        The table side is normalised too, not just the tree side: metadata
        exported from a spreadsheet often carries the same version suffixes.
        First row wins on collision, so an exact key is never shadowed by a
        looser spelling of a different row.
        """
        index = {}
        for row in self.records:
            raw = row.get(self.key_col)
            if raw is None:
                continue
            for key in candidate_keys(str(raw)):
                index.setdefault(key, row)
                index.setdefault(key.upper(), row)
        return index

    def _build_group_order(self):
        if not self.color_by:
            return [DEFAULT_GROUP]
        order = []
        for row in self.records:
            value = _fmt(row.get(self.color_by))
            if value and value not in order:
                order.append(value)
        return order

    # -- protocol --

    def groups(self):
        return list(self._group_order)

    def _color_for(self, value):
        if self.color_map is not None:
            return self.color_map.get(value, UNKNOWN_CATEGORY_COLOR)
        return self.palette[self._group_order.index(value) % len(self.palette)]

    def join_report(self, tip_labels):
        """How the metadata table lined up with the tips actually on the tree.

        Returned so the caller can say so out loud. A tip with no metadata is
        drawn — it is a real sequence — but silently colouring it "unknown"
        would hide a broken join behind a plausible-looking figure.

        ``duplicated`` holds key spellings the table repeats; the first row wins
        for those, which is the same rule :meth:`lookup` follows.
        """
        matched = []
        unmatched = []
        for label in tip_labels:
            (matched if self.lookup(label) is not None else unmatched).append(label)

        seen = set()
        duplicated = []
        for row in self.records:
            raw = row.get(self.key_col)
            if raw is None:
                continue
            key = str(raw)
            if key in seen and key not in duplicated:
                duplicated.append(key)
            seen.add(key)

        return {
            "matched": len(matched),
            "unmatched": unmatched,
            "duplicated": duplicated,
        }

    def lookup(self, label):
        """The metadata row for `label`, or None. Public: the Dash app shows it."""
        for key in candidate_keys(label):
            row = self._index.get(key) or self._index.get(key.upper())
            if row is not None:
                return row
        return None

    def style_for(self, label):
        cached = self._cache.get(label)
        if cached is not None:
            return cached

        row = self.lookup(label)

        if self.color_by:
            value = _fmt(row.get(self.color_by)) if row else ""
            if value and value in self._group_order:
                group = value
                color = self._color_for(value)
            else:
                group = MISSING_GROUP
                color = UNKNOWN_CATEGORY_COLOR
        else:
            group = DEFAULT_GROUP
            color = LIGHT["default_tip"]

        hover_rows = tuple(
            (col, _fmt(row.get(col)))
            for col in self.hover_cols
            if row and _fmt(row.get(col))
        )

        style = TipStyle(
            group=group,
            color=color,
            hover_rows=hover_rows,
            url=ncbi_url(label) if self.link_ncbi else None,
        )
        self._cache[label] = style
        return style


class NullAnnotator(BaseAnnotator):
    """Default when the caller supplies nothing: one group, default colour."""

    def __init__(self, link_ncbi=True):
        self.link_ncbi = link_ncbi

    def groups(self):
        return [DEFAULT_GROUP]

    def style_for(self, label):
        return TipStyle(
            group=DEFAULT_GROUP,
            color=None,
            url=ncbi_url(label) if self.link_ncbi else None,
        )


def _fmt(value):
    """Render a cell as a display string; blanks and NaN become ''."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "<na>"} else text
