#!/usr/bin/env python
"""Layout registry. Add a module with name/label/supports_rotation/compute, then register it here."""


from . import circular, radial, rectangular
from .base import AxisSpec, LayoutResult, NodePosition, polyline

__all__ = [
    "LAYOUTS",
    "LAYOUT_CHOICES",
    "get_layout",
    "compute_layout",
    "AxisSpec",
    "LayoutResult",
    "NodePosition",
    "polyline",
]

LAYOUTS = {
    rectangular.name: rectangular,
    circular.name: circular,
    radial.name: radial,
}

LAYOUT_CHOICES = [
    {"label": module.label, "value": key} for key, module in LAYOUTS.items()
]

# Names people reach for that are not the registry key.
_ALIASES = {
    "rectangular": "rect",
    "phylogram": "rect",
    "circular": "circ",
    "fan": "circ",
    "unrooted": "radial",
}


def get_layout(layout):
    """Resolve a layout name (or a layout module) to a layout.

    Raises
    ------
    ValueError
        On an unknown name — silently falling back would hide a typo behind a
        tree that looks plausible but is not the one that was asked for.
    """
    if hasattr(layout, "compute"):
        return layout
    key = str(layout).lower()
    key = _ALIASES.get(key, key)
    if key not in LAYOUTS:
        raise ValueError(
            f"Unknown layout {layout!r}. Available: {', '.join(LAYOUTS)}"
        )
    return LAYOUTS[key]


def compute_layout(tree, layout="rect", **options):
    """Compute geometry for `tree` under `layout`. Coordinates only, no figure."""
    return get_layout(layout).compute(tree, **options)
