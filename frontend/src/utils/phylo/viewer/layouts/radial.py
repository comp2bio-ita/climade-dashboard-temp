#!/usr/bin/env python
"""Unrooted equal-angle (Meacham) layout."""


import math

from .base import BREATHING_ROOM, AxisSpec, LayoutResult, NodePosition, polyline

name = "radial"
label = "Radial (unrooted)"
supports_rotation = True

# Zero-length branches would stack a node on its parent.
_MIN_BRANCH = 0.01


def compute(
    tree,
    cladogram=False,
    rotation_deg=0.0,
    show_labels=True,
    **_ignored,
):
    """Lay a tree out with the equal-angle algorithm."""
    positions = {}
    if tree.n_tips == 0:
        return LayoutResult(positions=positions)

    use_lengths = not cladogram and tree.has_branch_lengths()

    # Wedge width is proportional to tip count, so dense clades get the room
    # they need. Post-order guarantees children are counted first.
    tip_count = {}
    for node in tree.postorder():
        tip_count[node.id] = 1 if node.is_tip else sum(tip_count[c.id] for c in node.children)

    scale = tree.max_depth or 1.0
    min_branch = _MIN_BRANCH * scale if use_lengths else _MIN_BRANCH

    rot = math.radians(rotation_deg)
    root = tree.root
    positions[root.id] = NodePosition(x=0.0, y=0.0, angle=rot, radius=0.0)

    # Iterative pre-order carrying each node's angular wedge. The recursive
    # form of this is the classic textbook version, but it is also the one
    # that fails with RecursionError on a few-thousand-tip ladder tree.
    stack = [(root, rot, rot + 2 * math.pi)]
    while stack:
        node, a_start, a_end = stack.pop()
        if node.is_tip:
            continue
        parent = positions[node.id]
        total = tip_count[node.id]
        cursor = a_start
        for child in node.children:
            wedge = (a_end - a_start) * tip_count[child.id] / total
            mid = cursor + wedge / 2.0
            length = max(child.branch_length, min_branch) if use_lengths else 1.0
            positions[child.id] = NodePosition(
                x=parent.x + length * math.cos(mid),
                y=parent.y + length * math.sin(mid),
                angle=mid,
                radius=None,
            )
            stack.append((child, cursor, cursor + wedge))
            cursor += wedge

    branch_x = []
    branch_y = []
    for node in tree.preorder():
        p = positions[node.id]
        for child in node.children:
            c = positions[child.id]
            polyline(branch_x, branch_y, [(p.x, p.y), (c.x, c.y)])

    # Anchor each tip's label on the side its branch points, so labels lead
    # away from the tree rather than back across it.
    tip_anchor = {}
    tip_label_xy = {}
    for tip in tree.tips:
        pos = positions[tip.id]
        tip_label_xy[tip.id] = (pos.x, pos.y)
        deg = math.degrees(pos.angle or 0.0) % 360
        tip_anchor[tip.id] = "middle left" if 90 < deg < 270 else "middle right"

    xs = [p.x for p in positions.values()]
    ys = [p.y for p in positions.values()]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    extent = max(x_max - x_min, y_max - y_min) or 1.0
    # Symmetric, unlike the rectangular layout: an unrooted tree grows in every
    # direction, so there is no one side to reserve. Room for the labels is
    # added later by the renderer, which knows the font size and figure height.
    pad = extent * BREATHING_ROOM

    return LayoutResult(
        positions=positions,
        branch_x=branch_x,
        branch_y=branch_y,
        tip_anchor=tip_anchor,
        tip_label_xy=tip_label_xy,
        axes=AxisSpec(
            x_range=(x_min - pad, x_max + pad),
            y_range=(y_min - pad, y_max + pad),
            equal_aspect=True,
            show_x_axis=False,
            show_y_axis=False,
            height_hint=700,
        ),
    )
