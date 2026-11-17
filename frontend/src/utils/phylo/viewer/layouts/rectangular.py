#!/usr/bin/env python
"""Rectangular phylogram / cladogram / time tree."""


from .base import AxisSpec, LayoutResult, NodePosition, polyline
from utils.functions.date_functions import phylo_decimal_year_axis_ticks

name = "rect"
label = "Rectangular"
supports_rotation = False

ORIENTATIONS = {"right", "left", "up", "down"}

_LABEL_SHARE = 0.55
_NO_LABEL_SHARE = 0.02


def compute(
    tree,
    cladogram=False,
    align_tips=False,
    orientation="right",
    show_labels=True,
    time_origin=None,
    **_ignored,
):
    """Lay a tree out as a rectangular phylogram.

    Parameters
    ----------
    cladogram
        Ignore branch lengths and space nodes by level instead. Also forced on
        when the tree carries no branch lengths at all, since every node would
        otherwise collapse onto x=0.
    align_tips
        Push every tip out to the same x, so labels form a flush column.
        A leader line marks the distance that was skipped.
    orientation
        Direction the tree grows: 'right', 'left', 'up' or 'down'. 'right' is
        the conventional reading order.
    time_origin
        Calendar date of the root. When given, x becomes a calendar date rather
        than a distance and the axis is labelled in years. Ignored for a
        cladogram (levels are not years) and for orientations other than
        'right', where a date axis would run backwards or vertically.
    """
    if orientation not in ORIENTATIONS:
        orientation = "right"

    use_lengths = not cladogram and tree.has_branch_lengths()
    depths = tree.depths if use_lengths else {k: float(v) for k, v in tree.levels().items()}
    # The tree's own width in data units, before any calendar shift. Every
    # proportional measure below is taken from this rather than from the
    # largest x, which under a calendar origin is ~2026 and would reserve a
    # thousand years of label room.
    span = max(depths.values(), default=0.0) or 1.0

    dated = time_origin is not None and use_lengths and orientation == "right"
    origin = float(time_origin) if dated else 0.0

    positions = {}

    # Tips get consecutive integer rows in traversal order, which keeps sister
    # taxa adjacent. Internal nodes centre on their children — computed in
    # post-order so every child is placed before its parent is read.
    for row, tip in enumerate(tree.tips):
        positions[tip.id] = NodePosition(x=origin + depths[tip.id], y=float(row))
    for node in tree.postorder():
        if node.is_tip:
            continue
        ys = [positions[c.id].y for c in node.children]
        positions[node.id] = NodePosition(
            x=origin + depths[node.id],
            y=(min(ys) + max(ys)) / 2.0,
        )

    tip_x = origin + span if align_tips else None

    branch_x = []
    branch_y = []
    for node in tree.preorder():
        if node.is_tip:
            continue
        px, py = positions[node.id].x, positions[node.id].y
        child_ys = [positions[c.id].y for c in node.children]
        # One vertical spine spanning the children, rather than a separate
        # connector per child: half the segments, identical appearance.
        polyline(branch_x, branch_y, [(px, min(child_ys)), (px, max(child_ys))])
        for child in node.children:
            cx, cy = positions[child.id].x, positions[child.id].y
            polyline(branch_x, branch_y, [(px, cy), (cx, cy)])

    # Leader lines from each tip out to the aligned edge.
    if align_tips:
        for tip in tree.tips:
            pos = positions[tip.id]
            if tip_x - pos.x > 1e-12:
                polyline(branch_x, branch_y, [(pos.x, pos.y), (tip_x, pos.y)])

    tip_label_xy = {}
    tip_anchor = {}
    for tip in tree.tips:
        pos = positions[tip.id]
        x = tip_x if align_tips else pos.x
        tip_label_xy[tip.id] = (x, pos.y)
        tip_anchor[tip.id] = "middle right"

    n_tips = max(tree.n_tips, 1)
    x_max = max((p.x for p in positions.values()), default=origin)
    x_max = max(x_max, origin + span)
    # Reserve horizontal room for labels; without it long accessions are
    # clipped at the plot edge. On a calendar axis that room cannot come out
    # of the range — stretching it to 2090 to fit labels would print tick
    # labels for years no sequence was collected in — so the renderer is asked
    # for a pixel margin instead and the range stays tight to the data.
    label_pad = span * (_LABEL_SHARE if show_labels else _NO_LABEL_SHARE)
    if dated:
        label_pad = span * _NO_LABEL_SHARE

    if dated:
        x_title = "Year"
        tick_granularity, tickvals, ticktext, step_years = phylo_decimal_year_axis_ticks(origin, x_max)
        if tick_granularity == "yearly":
            x_tickformat = "d"
            x_tickmode = None
            x_tickvals = None
            x_ticktext = None
            x_dtick = step_years
        else:
            x_tickformat = None
            x_tickmode = "array"
            x_tickvals = tickvals
            x_ticktext = ticktext
            x_dtick = None
    elif use_lengths:
        x_title = "Branch length"
        x_tickformat = None
        x_tickmode = None
        x_tickvals = None
        x_ticktext = None
        x_dtick = None
    else:
        x_title = "Divergence (levels)"
        x_tickformat = None
        x_tickmode = None
        x_tickvals = None
        x_ticktext = None
        x_dtick = None

    result = LayoutResult(
        positions=positions,
        branch_x=branch_x,
        branch_y=branch_y,
        tip_anchor=tip_anchor,
        tip_label_xy=tip_label_xy,
        axes=AxisSpec(
            x_range=(origin - span * 0.02, x_max + label_pad),
            y_range=(-0.8, n_tips - 0.2),
            equal_aspect=False,
            x_title=x_title,
            x_tickformat=x_tickformat,
            x_tickmode=x_tickmode,
            x_tickvals=x_tickvals,
            x_ticktext=x_ticktext,
            x_dtick=x_dtick,
            show_x_axis=True,
            show_y_axis=False,
            # 14px per tip matches a readable ~9pt label; clamped so a
            # 5-tip tree is not a sliver and a 5000-tip tree stays scrollable.
            height_hint=max(400, min(3000, n_tips * 14)),
            label_pad=label_pad,
            reserve_label_margin=dated and show_labels,
        ),
    )
    return _reorient(result, orientation, n_tips, span + label_pad)


def _reorient(result, orientation, n_tips, x_extent):
    """Mirror/transpose a right-growing layout into the requested direction.

    Doing this as a post-pass keeps the placement logic above single-purpose;
    the alternative is four sign-juggling variants of the same code. Only
    reached with `time_origin` unset, so coordinates start at 0 here.
    """
    if orientation == "right":
        return result

    def _map(x, y):
        if orientation == "left":
            return -x, y
        if orientation == "up":
            return y, x
        return y, -x  # down

    result.positions = {
        nid: NodePosition(*_map(p.x, p.y), angle=p.angle, radius=p.radius)
        for nid, p in result.positions.items()
    }
    result.branch_x, result.branch_y = _remap_polyline(result.branch_x, result.branch_y, _map)
    result.tip_label_xy = {nid: _map(x, y) for nid, (x, y) in result.tip_label_xy.items()}

    anchor = {
        "left": "middle left",
        "up": "top center",
        "down": "bottom center",
    }[orientation]
    result.tip_anchor = {nid: anchor for nid in result.tip_anchor}

    axes = result.axes
    tip_span = (-0.8, n_tips - 0.2)
    if orientation == "left":
        axes.x_range = (-x_extent, x_extent * 0.02)
        axes.y_range = tip_span
    elif orientation == "up":
        axes.x_range = tip_span
        axes.y_range = (-x_extent * 0.02, x_extent)
        axes.show_x_axis, axes.show_y_axis = False, True
        axes.height_hint = 700
    else:  # down
        axes.x_range = tip_span
        axes.y_range = (-x_extent, x_extent * 0.02)
        axes.show_x_axis, axes.show_y_axis = False, True
        axes.height_hint = 700
    return result


def _remap_polyline(xs, ys, fn):
    out_x = []
    out_y = []
    for x, y in zip(xs, ys):
        if x is None or y is None:
            out_x.append(None)
            out_y.append(None)
            continue
        nx, ny = fn(x, y)
        out_x.append(nx)
        out_y.append(ny)
    return out_x, out_y
