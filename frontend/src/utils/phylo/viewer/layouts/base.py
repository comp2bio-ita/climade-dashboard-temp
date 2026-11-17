#!/usr/bin/env python
"""Contract every layout implements: node coordinates, no Plotly."""


from dataclasses import dataclass, field

__all__ = ["NodePosition", "AxisSpec", "LayoutResult", "polyline", "BREATHING_ROOM"]

# Fraction of extent to keep markers off the axis edge; label room is in render.
BREATHING_ROOM = 0.08


@dataclass(frozen=True)
class NodePosition:
    """Cartesian position of a node, plus polar coordinates when meaningful.

    `angle` and `radius` are populated by the circular and radial layouts and
    left as None by the rectangular one. The renderer uses `angle` to decide
    which side of a tip its label should sit on.
    """

    x: float
    y: float
    angle: float = None
    radius: float = None


@dataclass
class AxisSpec:
    """How the figure's axes should be configured for this layout.

    Layouts know their own aspect-ratio and range requirements — a fan tree is
    meaningless unless x and y share a scale — so they declare them here rather
    than leaving the renderer to guess per layout type.
    """

    x_range: tuple = None
    y_range: tuple = None
    equal_aspect: bool = False
    x_title: str = None
    # Plotly d3 tick format for the x axis. Set to "d" by the time axis so
    # calendar years read as 1980, not 1980.5.
    x_tickformat: str = None
    x_tickmode: str = None
    x_tickvals: list = None
    x_ticktext: list = None
    x_dtick: float = None
    show_x_axis: bool = False
    show_y_axis: bool = False
    height_hint: int = None
    label_pad: float = 0.0  # extra x-space reserved for tip labels
    # Ask the renderer for tip-label room as a right *margin* in pixels rather
    # than as extra axis range. The time axis needs this: padding its range
    # would print tick labels for calendar years the data does not reach.
    # Only safe on a layout that is not equal-aspect.
    reserve_label_margin: bool = False


@dataclass
class LayoutResult:
    """Geometry for one tree under one layout.

    Attributes
    ----------
    positions
        ``{TreeNode.id: NodePosition}``.
    branch_x, branch_y
        A single flat polyline of every branch, with ``None`` separating
        disconnected segments. This is Plotly's own format for a many-segment
        line, and keeping it flat means all branches render as one trace
        instead of thousands.
    tip_anchor
        Plotly `textposition` for each tip's label, keyed on node id.
    tip_label_xy
        Where the label sits, which is not always the tip's own position —
        circular layouts push labels out to a common radius.
    """

    positions: dict
    branch_x: list = field(default_factory=list)
    branch_y: list = field(default_factory=list)
    tip_anchor: dict = field(default_factory=dict)
    tip_label_xy: dict = field(default_factory=dict)
    axes: AxisSpec = field(default_factory=AxisSpec)

    def xy(self, node_id):
        pos = self.positions[node_id]
        return pos.x, pos.y

    def label_xy(self, node_id):
        return self.tip_label_xy.get(node_id) or self.xy(node_id)


def polyline(xs, ys, points):
    """Append `points` as one connected segment, then a break.

    Every layout builds its branches this way, so the ``None`` terminator is
    applied in exactly one place instead of being repeated at each call site
    (a missing terminator draws a spurious line across the figure).
    """
    for x, y in points:
        xs.append(x)
        ys.append(y)
    xs.append(None)
    ys.append(None)
