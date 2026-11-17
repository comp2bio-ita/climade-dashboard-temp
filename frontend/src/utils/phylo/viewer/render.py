#!/usr/bin/env python
"""Geometry + styling -> Plotly figure."""

import math
from pathlib import Path

import plotly.graph_objects as go

from .annotate import NullAnnotator, TipStyle
from .layouts import compute_layout, get_layout
from .model import copy_support_from
from .parse import parse_newick
from .theme import LIGHT

__all__ = [
    "render_tree",
    "render_timetree",
    "figure_to_html",
    "layout_coordinates",
]

# Above this many tips, labels overlap into an unreadable smear and are hidden
# by default; the information is still reachable on hover.
DEFAULT_LABEL_THRESHOLD = 60

# Figure margin used when tip labels are annotations. Annotations are placed in
# data coordinates but sized in pixels, so one near the edge of the range
# overflows the plot area; this gives that overflow somewhere to land.
_POLAR_MARGIN = 40


def render_tree(
    source,
    layout="rect",
    annotator=None,
    metadata=None,
    key_col=None,
    color_by=None,
    hover_cols=None,
    show_labels="auto",
    label_threshold=DEFAULT_LABEL_THRESHOLD,
    show_support=True,
    support_threshold=0.0,
    support_source=None,
    support_metric="sh_alrt",
    cladogram=False,
    align_tips=None,
    time_axis="auto",
    rotation_deg=0.0,
    arc_span_deg=360.0,
    orientation="right",
    highlight=None,
    marker_size=None,
    label_size=None,
    height=None,
    width=None,
    title=None,
    link_ncbi=True,
):
    """Render a phylogenetic tree as an interactive Plotly figure.

    Parameters
    ----------
    source
        Newick text, NEXUS text, a path to a tree file (IQ-TREE ``.treefile``,
        FastTree, TreeTime ``timetree.nexus``), or an already-parsed tree.
    layout
        'rect' rectangular phylogram, 'circ' circular fan, or 'radial'
        unrooted equal-angle.
    annotator
        Full control over tip styling. Mutually exclusive with `metadata`.
    metadata
        Shortcut that builds a :class:`~utils.phylo.viewer.annotate.MetadataAnnotator`
        from a table keyed on the tip label. Use with `color_by`/`hover_cols`.
    show_labels
        'auto' shows labels only when the tree has at most `label_threshold`
        tips.
    show_support
        Draw branch support (bootstrap / SH-aLRT) on internal nodes.
    support_threshold
        Print only the support values at or above this, to cut numeral clutter
        on a poorly resolved tree. Purely a display filter: the topology, the
        branch lengths and the tips are untouched, so a node whose numeral is
        hidden is still drawn exactly where it was. This does *not* collapse
        weakly supported clades into polytomies.
    cladogram
        Ignore branch lengths and space nodes by topology alone.
    align_tips
        Flush tip labels to a common edge. Defaults to on for 'circ' (where a
        fan is otherwise unreadable) and off for 'rect'.
    time_axis
        'auto' puts a dated tree on a calendar x-axis and leaves an undated one
        alone. True demands it (and is ignored if the tree carries no dates);
        False renders a dated tree as an ordinary phylogram.
    rotation_deg
        Rotate 'circ' / 'radial'. Ignored by 'rect', which is not rotatable —
        use `orientation` there instead.
    highlight
        Tip labels to ring, e.g. search matches.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    tree = parse_newick(source)
    if show_support and support_source is not None and not tree.has_support():
        copy_support_from(parse_newick(support_source), tree)
    layout_module = get_layout(layout)

    if align_tips is None:
        align_tips = layout_module.name == "circ"

    show_labels_resolved = _resolve_show_labels(show_labels, tree.n_tips, label_threshold)
    annot = _resolve_annotator(
        annotator, metadata,
        key_col=key_col, color_by=color_by, hover_cols=hover_cols,
        link_ncbi=link_ncbi,
    )

    time_origin = _resolve_time_origin(tree, time_axis, cladogram, align_tips)

    geometry = layout_module.compute(
        tree,
        cladogram=cladogram,
        align_tips=align_tips,
        rotation_deg=rotation_deg if layout_module.supports_rotation else 0.0,
        arc_span_deg=arc_span_deg,
        orientation=orientation,
        show_labels=show_labels_resolved,
        time_origin=time_origin,
    )

    if marker_size is None:
        marker_size = 5.0 if tree.n_tips > label_threshold else 7.0
    if label_size is None:
        label_size = 8 if tree.n_tips > 40 else 9

    # Polar layouts want each label rotated to follow its own branch, which
    # only annotations can do. Their tip traces therefore carry markers alone,
    # or the label would be drawn twice.
    angled_labels = show_labels_resolved and _supplies_angles(tree, geometry)
    if angled_labels:
        # These layouts are square (equal aspect), so height bounds the plot.
        figure_height = height or geometry.axes.height_hint or 700
        _expand_axes_for_labels(
            tree, geometry,
            label_size=label_size,
            plot_px=max(figure_height - _POLAR_MARGIN * 2, 100),
        )

    traces = [_branch_trace(geometry)]
    traces.extend(
        _tip_traces(
            tree, geometry, annot,
            show_labels=show_labels_resolved and not angled_labels,
            marker_size=marker_size,
            label_size=label_size,
            clip_labels=not geometry.axes.reserve_label_margin,
        )
    )
    if highlight:
        ring = _highlight_trace(tree, geometry, highlight, marker_size)
        if ring is not None:
            traces.append(ring)

    tip_labels = (
        _tip_label_annotations(
            tree, geometry,
            label_size=label_size, marker_size=marker_size,
        )
        if angled_labels
        else []
    )
    support_labels = (
        _support_annotations(tree, geometry, support_threshold, support_metric)
        if show_support and tree.has_support(support_metric)
        else []
    )

    fig = go.Figure(data=traces)
    _apply_layout(
        fig, geometry, tree,
        height=height, width=width, title=title,
        show_labels=show_labels_resolved,
        label_threshold=label_threshold,
        tip_labels=tip_labels,
        support_labels=support_labels,
        right_margin=_label_margin_px(tree, geometry, label_size, marker_size),
    )
    return fig


def render_timetree(source, **options):
    """Render a dated tree — TreeTime's ``timetree.nexus`` — on a calendar axis.

    The same renderer as :func:`render_tree`, but it insists the tree is dated
    instead of quietly falling back to a divergence axis. A host that asked for
    a time tree and was handed a substitution tree (the ``newick`` column
    rather than the ``time_tree_nexus`` one, say) finds out here rather than
    from a figure whose x-axis silently means something else.
    """
    tree = parse_newick(source)
    if not tree.has_dates():
        raise ValueError(
            "This tree carries no node dates, so it cannot be placed on a time "
            "axis. render_timetree expects TreeTime NEXUS output; use "
            "render_tree for a substitution tree."
        )
    options.setdefault("time_axis", True)
    return render_tree(tree, **options)


def layout_coordinates(source, layout="rect", **options):
    """Node coordinates without building a figure.

    For callers that want to drive their own rendering (a static image, a
    different plotting library, an export to another format).
    """
    return compute_layout(parse_newick(source), layout, **options)


def figure_to_html(fig, path=None, include_plotlyjs=True):
    """Write (or return) a self-contained interactive HTML page.

    `include_plotlyjs=True` inlines the Plotly bundle, so the file opens with
    full interactivity offline — the point of an export you can email.
    """
    html = fig.to_html(
        include_plotlyjs="inline" if include_plotlyjs else "cdn",
        full_html=True,
        config={"scrollZoom": True, "displaylogo": False},
    )
    if path is not None:
        Path(path).write_text(html, encoding="utf-8")
    return html


# ── Trace builders ─────────────────────────────────────────────────────────


def _branch_trace(geometry):
    """All branches as a single polyline trace.

    Hover is disabled: branches have no identity worth reporting, and leaving
    it on makes them steal hover events from the tips.
    """
    return go.Scatter(
        x=geometry.branch_x,
        y=geometry.branch_y,
        mode="lines",
        line=dict(color=LIGHT["line"], width=1.1),
        hoverinfo="skip",
        showlegend=False,
        name="branches",
    )


def _tip_traces(tree, geometry, annot, show_labels, marker_size, label_size,
                clip_labels=True):
    """One trace per legend group (not one per tip — keeps the figure JSON small)."""
    buckets = {}
    order_hint = list(annot.groups())

    for tip in tree.tips:
        style = annot.style_for(tip.name)
        bucket = buckets.setdefault(
            style.group,
            {"x": [], "y": [], "text": [], "textpos": [], "custom": [],
             "colors": [], "sizes": [], "symbol": style.symbol},
        )
        x, y = geometry.label_xy(tip.id)
        anchor = geometry.tip_anchor.get(tip.id, "middle right")
        bucket["x"].append(x)
        bucket["y"].append(y)
        bucket["colors"].append(style.color or LIGHT["default_tip"])
        bucket["sizes"].append(style.size or marker_size)
        bucket["textpos"].append(anchor)
        # Pad on the crowded side so the label clears its own marker; Plotly
        # offsets text by a fixed few pixels which is not enough at size 8.
        pad = "  "
        bucket["text"].append(
            f"{pad}{tip.name}" if anchor == "middle right" else f"{tip.name}{pad}"
        )
        bucket["custom"].append([tip.name, _hover_extra(style, tip), style.url or ""])

    # Groups the annotator declared come first and in its order; anything it
    # did not anticipate is appended, so no tip is ever dropped from the legend.
    ordered = [g for g in order_hint if g in buckets]
    ordered += [g for g in buckets if g not in ordered]

    traces = []
    for group in ordered:
        b = buckets[group]
        kwargs = dict(
            x=b["x"],
            y=b["y"],
            mode="markers+text" if show_labels else "markers",
            marker=dict(color=b["colors"], size=b["sizes"], symbol=b["symbol"],
                        line=dict(width=0)),
            customdata=b["custom"],
            hovertemplate="<b>%{customdata[0]}</b>%{customdata[1]}<extra></extra>",
            name=group,
            legendgroup=group,
            showlegend=True,
        )
        if show_labels:
            kwargs["text"] = b["text"]
            kwargs["textposition"] = b["textpos"]
            kwargs["textfont"] = dict(size=label_size, color=LIGHT["text"])
            # Plotly clips trace text to the plotting area, so a label beside a
            # tip at the very edge of the range is cut off mid-accession. The
            # time axis ends exactly at the newest tip, so every one of its
            # labels would be — letting them spill into the reserved margin is
            # what makes them readable.
            if not clip_labels:
                kwargs["cliponaxis"] = False
        traces.append(go.Scatter(**kwargs))
    return traces


# Width of a monospace glyph as a fraction of the font size. Plotly's default
# monospace stack sits close to 0.6; used only to size the space labels need.
_GLYPH_WIDTH_RATIO = 0.6

# Never let labels squeeze the tree below this fraction of the canvas. Past it
# the labels are unreadably cramped anyway and the tree has become a dot.
_MAX_LABEL_SHARE = 0.6

# Upper bound on the marker-to-label gap, for range fitting. The gap itself is
# derived from marker size per figure; this is just a constant allowance.
_LABEL_GAP_ALLOWANCE = 10.0


def _label_width(text, label_size):
    """Estimated rendered width of `text` in pixels.

    An estimate is all that is available — the true width depends on the font
    the browser resolves — but the labels are monospace, so character count
    times a fixed ratio is accurate enough to place and fit them.
    """
    return len(text) * label_size * _GLYPH_WIDTH_RATIO


def _expand_axes_for_labels(tree, geometry, label_size, plot_px):
    """Widen the axis range so rotated tip labels fit inside the plot.

    Angled labels radiate outward in every direction, so the space they need
    has to come from the axis range — a figure margin cannot help, because it
    would break the 1:1 aspect ratio these layouts depend on.

    The awkward part is a unit mismatch: the range is in data units but text is
    sized in pixels, so the conversion depends on how big the figure is. Given
    a plot `plot_px` wide showing `span` data units, a label of `label_px`
    needs padding `pad` on each side satisfying

        pad / (span + 2*pad) * plot_px = label_px

    which is what is solved below. This is why the calculation lives here and
    not in the layout: a layout knows neither the font nor the figure size.
    """
    longest = max((tip.name for tip in tree.tips), key=len, default="")
    if not longest:
        return

    # Include the marker gap: a label occupies from `gap` to `gap + width`
    # beyond its tip, and it is the outer edge that has to stay in frame.
    label_px = _label_width(longest, label_size) + _LABEL_GAP_ALLOWANCE
    # Beyond this the equation above has no useful solution (the denominator
    # goes to zero or negative), so cap the share labels may claim.
    label_px = min(label_px, plot_px * _MAX_LABEL_SHARE / 2)

    axes = geometry.axes
    for attribute in ("x_range", "y_range"):
        current = getattr(axes, attribute)
        if current is None:
            continue
        low, high = current
        span = high - low
        pad = label_px * span / max(plot_px - 2 * label_px, 1e-9)
        setattr(axes, attribute, (low - pad, high + pad))


def _label_margin_px(tree, geometry, label_size, marker_size):
    """Right margin, in pixels, for tip labels the axis range does not cover.

    Used by the time axis, which keeps its range tight to the data so that no
    tick shows a year the tree does not reach. The tree area shrinks by this
    much and the labels sit in the margin beside it — possible only because a
    rectangular layout has no aspect-ratio constraint to violate.
    """
    if not geometry.axes.reserve_label_margin:
        return None
    longest = max((tip.name for tip in tree.tips), key=len, default="")
    if not longest:
        return None
    gap = marker_size / 2.0 + 4.0
    return _label_width(longest, label_size) + gap


def _supplies_angles(tree, geometry):
    """Whether this layout gives its tips a meaningful direction.

    Tested as a capability rather than by layout name, so a future polar
    layout gets angled labels for free and `rect` — which leaves `angle` as
    None — keeps its faster trace-text path automatically.
    """
    return any(
        geometry.positions[tip.id].angle is not None
        for tip in tree.tips
        if tip.id in geometry.positions
    )


def _tip_label_annotations(tree, geometry, label_size, marker_size):
    """Rotated tip labels as annotations (Scatter has no textangle).

    textangle is clockwise while our angles are counterclockwise. Anchor at
    centre and push outward with xshift/yshift so labels clear the tip marker.
    """
    # Pixel gap — data-space gaps drift under zoom.
    gap = marker_size / 2.0 + 4.0

    annotations = []
    for tip in tree.tips:
        position = geometry.positions.get(tip.id)
        if position is None or position.angle is None:
            continue

        x, y = geometry.label_xy(tip.id)
        degrees = math.degrees(position.angle) % 360
        # `tip_anchor` already holds the layout's half-plane decision, so reuse
        # it rather than re-deriving which labels would read upside down.
        flipped = geometry.tip_anchor.get(tip.id) == "middle left"
        offset = gap + _label_width(tip.name, label_size) / 2.0

        annotations.append(dict(
            x=x,
            y=y,
            text=tip.name,
            showarrow=False,
            textangle=(180 - degrees) if flipped else -degrees,
            xanchor="center",
            yanchor="middle",
            xshift=offset * math.cos(position.angle),
            yshift=offset * math.sin(position.angle),
            font=dict(size=label_size, color=LIGHT["text"]),
        ))
    return annotations


def _support_value(node, support_metric):
    if support_metric == "ufboot":
        return node.support_ufboot
    return node.support_sh_alrt


def _support_annotations(tree, geometry, threshold, support_metric="sh_alrt"):
    """Branch support numerals on internal nodes at or above `threshold`."""
    annotations = []
    for node in tree.internal_nodes:
        value = _support_value(node, support_metric)
        if value is None or value < threshold:
            continue
        pos = geometry.positions.get(node.id)
        if pos is None:
            continue
        # IQ-TREE sometimes emits decimals; integers are the conventional display.
        numeral = f"{value:g}" if value % 1 else f"{int(value)}"
        annotations.append(dict(
            x=pos.x, y=pos.y,
            text=numeral,
            showarrow=False,
            xanchor="right", yanchor="bottom",
            xshift=24, yshift=-6,
            font=dict(size=8, color=LIGHT["support"]),
            name="support",
        ))
    return annotations


def _highlight_trace(tree, geometry, highlight, marker_size):
    """Open rings over matched tips. Drawn last so it sits above the markers."""
    wanted = {str(h) for h in highlight}
    xs, ys, labels = [], [], []
    for tip in tree.tips:
        if tip.name in wanted:
            x, y = geometry.label_xy(tip.id)
            xs.append(x)
            ys.append(y)
            labels.append(tip.name)
    if not xs:
        return None
    return go.Scatter(
        x=xs, y=ys, mode="markers",
        marker=dict(
            color="rgba(0,0,0,0)",
            size=marker_size * 2.6,
            symbol="circle",
            line=dict(color=LIGHT["highlight"], width=1.6),
        ),
        customdata=[[label] for label in labels],
        hovertemplate="<b>%{customdata[0]}</b><extra>match</extra>",
        name=f"Match ({len(xs)})",
        showlegend=True,
    )


# ── Figure layout ──────────────────────────────────────────────────────────


def _apply_layout(fig, geometry, tree, height, width, title,
                  show_labels, label_threshold, tip_labels=None,
                  support_labels=None, right_margin=None):
    axes = geometry.axes
    tip_labels = tip_labels or []
    support_labels = support_labels or []

    x_axis = dict(
        showgrid=axes.show_x_axis,
        gridcolor=LIGHT["grid"],
        zeroline=False,
        showticklabels=axes.show_x_axis,
        tickfont=dict(size=9),
        range=list(axes.x_range) if axes.x_range else None,
    )
    if axes.show_x_axis and axes.x_title:
        x_axis["title"] = dict(text=axes.x_title, font=dict(size=10))
    if axes.x_tickformat:
        x_axis["tickformat"] = axes.x_tickformat
    if axes.x_tickmode == "array":
        x_axis["tickmode"] = "array"
        x_axis["tickvals"] = axes.x_tickvals
        x_axis["ticktext"] = axes.x_ticktext
    elif axes.x_dtick is not None:
        x_axis["tickmode"] = "linear"
        x_axis["dtick"] = axes.x_dtick

    y_axis = dict(
        showgrid=False,
        zeroline=False,
        showticklabels=axes.show_y_axis,
        tickfont=dict(size=9),
        range=list(axes.y_range) if axes.y_range else None,
    )
    # A fan or unrooted tree is only meaningful at 1:1; without this the
    # circle becomes an ellipse the moment the container is resized.
    if axes.equal_aspect:
        x_axis["scaleanchor"] = "y"
        x_axis["scaleratio"] = 1

    # Header annotations are tracked separately from the tip labels: only they
    # need vertical room reserved at the top of the figure.
    header = []
    if title:
        header.append(dict(
            text=f"<b>{title}</b>", xref="paper", yref="paper",
            x=0.5, y=1.02, xanchor="center", showarrow=False,
            font=dict(size=13, color=LIGHT["text"]),
        ))
    if not show_labels and tree.n_tips > label_threshold:
        header.append(dict(
            text=(f"{tree.n_tips} tips — labels hidden for legibility. "
                  "Hover a tip to read it."),
            xref="paper", yref="paper", x=0.5, y=1.055 if title else 1.02,
            xanchor="center", showarrow=False,
            font=dict(size=10, color=LIGHT["muted"]),
        ))

    side = _POLAR_MARGIN if tip_labels else 20

    fig.update_layout(
        paper_bgcolor=LIGHT["paper"],
        plot_bgcolor=LIGHT["plot"],
        # Monospace, unlike the rest of the dashboard: _label_width estimates tip-label
        # width from a fixed glyph ratio to reserve axis or margin space, which only
        # holds for a fixed-pitch font. Accessions also align legibly this way.
        font=dict(color=LIGHT["text"], family="monospace", size=11),
        margin=dict(l=side, r=max(side, right_margin or 0),
                    t=50 if header else max(24, side),
                    b=max(40, side)),
        xaxis=x_axis,
        yaxis=y_axis,
        hovermode="closest",
        dragmode="pan",
        height=height or axes.height_hint or 700,
        width=width,
        # Tip labels first so the header stays last and wins any overlap.
        annotations=tip_labels + support_labels + header,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=LIGHT["legend_border"],
            borderwidth=1,
            font=dict(size=10),
            orientation="h",
            yanchor="bottom", y=1.005,
            xanchor="right", x=1,
        ),
    )


# ── Helpers ────────────────────────────────────────────────────────────────


def _resolve_show_labels(show_labels, n_tips, threshold):
    if isinstance(show_labels, str):
        return n_tips <= threshold if show_labels.lower() == "auto" else True
    return bool(show_labels)


def _resolve_time_origin(tree, time_axis, cladogram, align_tips):
    """The root's calendar date, when a time axis is both wanted and meaningful.

    Two settings silently contradict a calendar axis and so switch it off:

    * `cladogram` spaces nodes by level, not by elapsed years, so the numbers
      on the axis would be topological depth wearing a date label;
    * `align_tips` pushes every tip out to a common edge, which is exactly the
      information a time tree exists to show — a 2019 sample would be drawn
      alongside a 2025 one.
    """
    if time_axis is False:
        return None
    if not tree.has_dates():
        return None
    if cladogram or align_tips:
        return None
    return tree.root_date


def _resolve_annotator(annotator, metadata, key_col, color_by, hover_cols, link_ncbi):
    if annotator is not None and metadata is not None:
        raise ValueError(
            "Pass either `annotator` or `metadata`, not both — they are two "
            "ways of specifying the same thing."
        )

    if annotator is None and metadata is not None:
        from .annotate import MetadataAnnotator

        annotator = MetadataAnnotator(
            metadata,
            key_col=key_col,
            color_by=color_by,
            hover_cols=hover_cols,
            link_ncbi=link_ncbi,
        )
    if annotator is None:
        annotator = NullAnnotator(link_ncbi=link_ncbi)
    return annotator


def _hover_extra(style, tip):
    """Metadata rows appended under the tip name in the hover box."""
    parts = []
    if style.group:
        parts.append(f"<br><i>{style.group}</i>")
    # On a timetree these are the two facts the tree itself carries that the
    # metadata table does not: when TreeTime placed the tip, and how much
    # change it inferred on the branch leading to it.
    if tip.date is not None:
        parts.append(f"<br>date: {tip.date:.2f}")
    if tip.n_mutations is not None:
        parts.append(f"<br>mutations: {tip.n_mutations}")
    for key, value in style.hover_rows:
        parts.append(f"<br>{key}: {value}")
    if style.url:
        parts.append("<br><span style='font-size:10px'>click to open on NCBI</span>")
    return "".join(parts)
