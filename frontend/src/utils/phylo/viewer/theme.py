#!/usr/bin/env python
"""Colour palette for rendered trees."""

__all__ = ["LIGHT", "CATEGORICAL", "color_for_index"]


# Hue + luminance spaced for colour-vision deficiency and greyscale print.
CATEGORICAL = [
    "#0969da",  # blue
    "#bc4c00",  # orange
    "#1a7f37",  # green
    "#cf222e",  # red
    "#8250df",  # purple
    "#1b7c83",  # teal
    "#a475f9",  # lilac
    "#9a6700",  # amber
    "#a40e26",  # crimson
    "#2da44e",  # mint
    "#218bff",  # pale blue
    "#bf3989",  # magenta
]


LIGHT = {
    "paper": "#ffffff",
    # White, matching every other dashboard chart (utils.color_schemes.get_chart_theme).
    "plot": "#ffffff",
    # Neutral grey — not a CATEGORICAL hue, so branches never read as a group.
    "line": "#3C4043",
    "text": "#1f2328",       # tip labels and axis text
    "muted": "#636c76",      # hints, secondary annotations
    "grid": "#eaeef2",
    "support": "#0D6EFD",    # branch support numerals
    "default_tip": "#1a7f37",  # tips with no metadata / no colour assignment
    "highlight": "#24292f",  # search-match ring
    "legend_border": "#d0d7de",
    "categorical": CATEGORICAL,
}


def color_for_index(index, palette=None):
    """Cycle a categorical palette. Stable for a given index."""
    palette = palette or CATEGORICAL
    return palette[index % len(palette)]
