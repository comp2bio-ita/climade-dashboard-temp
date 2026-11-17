#!/usr/bin/env python
"""Circular fan phylogram — root at centre, tips on a circle."""


import math

from .base import BREATHING_ROOM, AxisSpec, LayoutResult, NodePosition, polyline

name = "circ"
label = "Circular"
supports_rotation = True

_ARC_SEGMENTS_PER_PI = 80
_MIN_ARC_SEGMENTS = 8


def compute(
    tree,
    cladogram=False,
    align_tips=True,
    rotation_deg=0.0,
    arc_span_deg=360.0,
    show_labels=True,
    **_ignored,
):
    """Lay a tree out as a circular fan.

    Parameters
    ----------
    align_tips
        Place tip labels on the outer circle (r=1) regardless of the tip's own
        radius. On by default: it is what makes a fan readable.
    rotation_deg
        Rotate the whole fan. Useful for moving a clade of interest away from
        the label-crowded left side.
    arc_span_deg
        Angular extent, default a full 360°. A value like 340 opens a wedge at
        the top, which stops the first and last tips colliding and gives the
        root a visible orientation.
    """
    n_tips = tree.n_tips
    positions = {}
    if n_tips == 0:
        return LayoutResult(positions=positions)

    use_lengths = not cladogram and tree.has_branch_lengths()
    depths = tree.depths if use_lengths else {k: float(v) for k, v in tree.levels().items()}
    max_depth = max(depths.values(), default=0.0) or 1.0
    radius_of = {nid: d / max_depth for nid, d in depths.items()}

    rot = math.radians(rotation_deg)
    span = math.radians(max(min(arc_span_deg, 360.0), 1.0))
    # A full circle wraps, so the last tip must not land on top of the first:
    # divide by n. A partial arc does not wrap, so its endpoints are both
    # usable: divide by n-1.
    is_full = span >= 2 * math.pi - 1e-9
    denom = n_tips if is_full else max(n_tips - 1, 1)

    angles = {}
    for i, tip in enumerate(tree.tips):
        angles[tip.id] = rot + span * i / denom

    # An internal node sits at the midpoint of the angular range its
    # descendants occupy. Tracking (min, max) in post-order gives that in one
    # pass without revisiting subtrees.
    ang_lo = {}
    ang_hi = {}
    for node in tree.postorder():
        if node.is_tip:
            ang_lo[node.id] = ang_hi[node.id] = angles[node.id]
        else:
            ang_lo[node.id] = min(ang_lo[c.id] for c in node.children)
            ang_hi[node.id] = max(ang_hi[c.id] for c in node.children)
            angles[node.id] = (ang_lo[node.id] + ang_hi[node.id]) / 2.0

    for node in tree.preorder():
        r = radius_of[node.id]
        a = angles[node.id]
        positions[node.id] = NodePosition(
            x=r * math.cos(a), y=r * math.sin(a), angle=a, radius=r
        )

    branch_x = []
    branch_y = []
    for node in tree.preorder():
        if node.is_tip:
            continue
        pr = radius_of[node.id]
        child_angles = sorted(angles[c.id] for c in node.children)
        if len(child_angles) > 1:
            polyline(branch_x, branch_y, _arc(pr, child_angles[0], child_angles[-1]))
        for child in node.children:
            a = angles[child.id]
            cr = radius_of[child.id]
            polyline(branch_x, branch_y,
                     [(pr * math.cos(a), pr * math.sin(a)),
                      (cr * math.cos(a), cr * math.sin(a))])

    label_r = 1.0
    if align_tips:
        for tip in tree.tips:
            a = angles[tip.id]
            r = radius_of[tip.id]
            if label_r - r > 1e-9:
                polyline(branch_x, branch_y,
                         [(r * math.cos(a), r * math.sin(a)),
                          (label_r * math.cos(a), label_r * math.sin(a))])

    # Labels on the left half of the circle would read right-to-left if drawn
    # outward, so they hang off the left of their marker instead. The renderer
    # reads this back to decide which labels to turn a further 180 degrees.
    tip_anchor = {}
    tip_label_xy = {}
    for tip in tree.tips:
        a = angles[tip.id]
        r = label_r if align_tips else radius_of[tip.id]
        tip_label_xy[tip.id] = (r * math.cos(a), r * math.sin(a))
        deg = math.degrees(a) % 360
        tip_anchor[tip.id] = "middle left" if 90 < deg < 270 else "middle right"

    # Tips sit on the unit circle; this leaves a little air around them. Room
    # for the labels themselves is added later by the renderer, which is the
    # only place that knows the font size and the figure dimensions.
    extent = 1.0 + BREATHING_ROOM

    return LayoutResult(
        positions=positions,
        branch_x=branch_x,
        branch_y=branch_y,
        tip_anchor=tip_anchor,
        tip_label_xy=tip_label_xy,
        axes=AxisSpec(
            x_range=(-extent, extent),
            y_range=(-extent, extent),
            equal_aspect=True,
            show_x_axis=False,
            show_y_axis=False,
            height_hint=700,
        ),
    )


def _arc(radius, a0, a1):
    """Points along the arc from `a0` to `a1` at `radius`."""
    sweep = abs(a1 - a0)
    steps = max(_MIN_ARC_SEGMENTS, int(sweep / math.pi * _ARC_SEGMENTS_PER_PI))
    return [
        (radius * math.cos(a0 + (a1 - a0) * i / steps),
         radius * math.sin(a0 + (a1 - a0) * i / steps))
        for i in range(steps + 1)
    ]
