"""The phylogeny viewer as a Dash panel: layout and the callbacks that drive it.

Adapted from the standalone phylotree app's `dash_components`, with its upload
inputs replaced by the result dictionary `result_provider` produces. Layout and
callbacks live together on purpose — one visual feature should be readable in
one file.

Every component id is derived from `panel_ids(prefix)`, so a second pathogen can
mount its own viewer on the same page without collisions, and nothing here holds
state between requests.
"""

import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, no_update
import dash_bootstrap_components as dbc

from utils.color_schemes import color_map_for_pathogen_field
from utils.phylo.viewer.annotate import MetadataAnnotator, ncbi_url
from utils.phylo.viewer.parse import NewickParseError, parse_newick
from utils.phylo.viewer.render import render_tree
from utils.phylo.viewer.theme import LIGHT

TIME_SCALE = "time"
SUBSTITUTION_SCALE = "substitutions"

TOGGLE_LABELS = "labels"
TOGGLE_SUPPORT = "support"
TOGGLE_LENGTHS = "lengths"
TOGGLE_ALIGN = "align"

DEFAULT_TOGGLES = [TOGGLE_LABELS, TOGGLE_SUPPORT, TOGGLE_LENGTHS]

SUPPORT_METRIC_SH_ALRT = "sh_alrt"
SUPPORT_METRIC_UFBOOT = "ufboot"
DEFAULT_SUPPORT_METRIC = SUPPORT_METRIC_SH_ALRT

_SUPPORT_METRIC_OPTIONS = [
    {"label": "SH-aLRT", "value": SUPPORT_METRIC_SH_ALRT},
    {"label": "Ultrafast Bootstrap", "value": SUPPORT_METRIC_UFBOOT},
]

NOTE_CSS = "text-muted"

# Clamp pasted label-size values (browser ignores input min/max)
LABEL_SIZE_MIN = 6
LABEL_SIZE_MAX = 24

def graph_config(prefix):
    # The PNG the modebar saves is named after the page that produced it
    return {
        "displayModeBar": True,
        "displaylogo": False,
        "scrollZoom": True,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "toImageButtonOptions": {"format": "png", "scale": 2,
                                 "filename": f"{prefix}_phylogenetic_tree"},
    }

_LAYOUT_OPTIONS = [
    {"label": "Rectangular", "value": "rect"},
    {"label": "Circular", "value": "circ"},
    {"label": "Radial", "value": "radial"},
]

_TOGGLE_OPTIONS = [
    {"label": " Tip labels", "value": TOGGLE_LABELS},
    {"label": " Branch support", "value": TOGGLE_SUPPORT},
    {"label": " Branch lengths", "value": TOGGLE_LENGTHS},
    {"label": " Align tips", "value": TOGGLE_ALIGN},
]

_ROTATING_LAYOUTS = {"circ", "radial"}

_FIELD_LABELS = {
    "serotype": "Serotype",
    "genotype": "Genotype",
    "major_lineage": "Major lineage",
    "minor_lineage": "Minor lineage",
    "country": "Country",
    "division": "Division (State)",
    "locality": "Locality",
    "host": "Host",
}


def panel_ids(prefix):
    """Every component id this panel owns, derived from one prefix."""
    return {
        "scale": f"{prefix}-scale",
        "layout": f"{prefix}-layout",
        "rotation": f"{prefix}-rotation",
        "rotation_wrap": f"{prefix}-rotation-wrap",
        "toggles": f"{prefix}-toggles",
        "color_by": f"{prefix}-color-by",
        "search": f"{prefix}-search",
        "support_min": f"{prefix}-support-min",
        "support_metric": f"{prefix}-support-metric",
        "label_size": f"{prefix}-label-size",
        "graph": f"{prefix}-graph",
        "detail": f"{prefix}-detail",
        "notes": f"{prefix}-notes",
    }


# ── Layout ─────────────────────────────────────────────────────────────────


def phylogeny_panel(prefix):
    """The control strip, the tree, the provenance notes, and the tip detail card."""
    cid = panel_ids(prefix)
    return html.Div([
        dbc.Card(body=True, color="light", className="mb-3",
                 children=_controls(cid)),
        html.Div(id=cid["notes"], className="small mb-2"),
        # Height from tip count (no fixed height)
        dbc.Card(body=True, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id=cid["graph"], config=graph_config(prefix)),
            ]),
        ]),
        html.Div(id=cid["detail"]),
    ])


def _controls(cid):
    return html.Div(
        [
            _labelled("Tree scale", dbc.RadioItems(
                id=cid["scale"],
                options=_scale_options(dated_tree_available=False),
                value=SUBSTITUTION_SCALE,
                inline=True,
                inputClassName="me-1",
                labelClassName="me-3 small",
            )),
            _labelled("Layout", dbc.RadioItems(
                id=cid["layout"],
                options=_LAYOUT_OPTIONS,
                value="rect",
                inline=True,
                inputClassName="me-1",
                labelClassName="me-3 small",
            )),
            html.Div(
                id=cid["rotation_wrap"],
                children=_labelled("Rotation", dcc.Slider(
                    id=cid["rotation"],
                    min=0, max=345, step=15, value=0,
                    marks={0: "0°", 90: "90°", 180: "180°", 270: "270°"},
                    tooltip={"placement": "bottom", "always_visible": False},
                )),
                style=_rotation_style(enabled=False),
            ),
            _labelled("Show", dbc.Checklist(
                id=cid["toggles"],
                options=_TOGGLE_OPTIONS,
                value=list(DEFAULT_TOGGLES),
                inline=True,
                switch=True,
                labelClassName="me-3 small",
            )),
            _labelled("Hide support below", dcc.Slider(
                id=cid["support_min"],
                min=0, max=100, step=5, value=0,
                marks={0: "all", 50: "50", 80: "80", 100: "100"},
                tooltip={"placement": "bottom", "always_visible": False},
            ), style=_sized("180px")),
            _labelled("Branch support metric", dcc.Dropdown(
                id=cid["support_metric"],
                options=_SUPPORT_METRIC_OPTIONS,
                value=DEFAULT_SUPPORT_METRIC,
                clearable=False,
            ), style=_sized("300px")),
            html.Div(
                [
                    _labelled("Colour by", dcc.Dropdown(
                        id=cid["color_by"],
                        options=[],
                        value=None,
                        placeholder="no metadata yet…",
                        clearable=True,
                    ), style=_sized("300px")),
                    _labelled("Find tip", dbc.Input(
                        id=cid["search"],
                        type="text",
                        placeholder="accession or partial…",
                        debounce=True,
                        size="sm",
                    ), style=_sized("240px")),
                    _labelled("Tip label size", dbc.Input(
                        id=cid["label_size"],
                        type="number",
                        min=LABEL_SIZE_MIN, max=LABEL_SIZE_MAX, step=1,
                        value=None,
                        placeholder="auto",
                        size="sm",
                    ), style=_sized("120px")),
                ],
                style={"display": "flex", "flexWrap": "wrap", "gap": "1.25rem",
                       "alignItems": "flex-start", "flex": "1 1 100%"},
            ),
        ],
        style={"display": "flex", "flexWrap": "wrap", "gap": "1.25rem",
               "alignItems": "flex-start"},
    )


def _scale_options(dated_tree_available, reason=None):
    return [
        {
            "label": "Time (TreeTime)",
            "value": TIME_SCALE,
            "disabled": not dated_tree_available,
            "title": reason or "",
        },
        {"label": "Substitutions", "value": SUBSTITUTION_SCALE},
    ]


def _labelled(text, control, style=None):
    base = {"flex": "0 1 auto", "minWidth": 0}
    base.update(style or {})
    return html.Div(
        [
            html.Div(text, className="text-uppercase text-muted",
                     style={"fontSize": "10px", "letterSpacing": "0.06em",
                            "marginBottom": "0.25rem"}),
            control,
        ],
        style=base,
    )


def _sized(width):
    # minWidth 0 so a control can shrink instead of forcing a horizontal scrollbar.
    return {"flex": f"0 1 {width}", "minWidth": 0}


def _rotation_style(enabled=True):
    style = _sized("220px")
    style["opacity"] = 1 if enabled else 0.35
    return style


# ── Figure assembly ────────────────────────────────────────────────────────


def build_phylogeny_figure(result, scale=SUBSTITUTION_SCALE, layout="rect", rotation=0,
                           toggles=None, support_min=0, support_metric=DEFAULT_SUPPORT_METRIC,
                           color_by=None, search=None, label_size=None):
    """Turn raw control values into a figure.

    Kept out of the callback so it can be tested without a Dash app. Which tree
    is drawn is decided here and nowhere else: `scale` picks between the
    substitution tree and the TreeTime dated tree, and the two are never mixed.
    """
    tree_text = _tree_text_for(result, scale)
    if not tree_text:
        return placeholder_figure("Generate a tree to see it here.")

    # None = defaults; empty list = user cleared all toggles
    toggles = list(DEFAULT_TOGGLES) if toggles is None else list(toggles)
    annotator = _annotator_for(result, color_by)

    try:
        # Support lives on the inferred tree; the dated tree borrows it for display only.
        support_source = (
            result.get("substitution_newick") if scale == TIME_SCALE else None
        )
        return render_tree(
            tree_text,
            layout=layout,
            annotator=annotator,
            show_labels=TOGGLE_LABELS in toggles,
            show_support=TOGGLE_SUPPORT in toggles,
            support_threshold=float(support_min or 0),
            support_source=support_source,
            support_metric=support_metric or DEFAULT_SUPPORT_METRIC,
            cladogram=TOGGLE_LENGTHS not in toggles,
            align_tips=TOGGLE_ALIGN in toggles,
            rotation_deg=float(rotation or 0),
            highlight=_matching_tips(tree_text, search),
            label_size=_clamp_label_size(label_size),
        )
    except (NewickParseError, ValueError) as error:
        return placeholder_figure(f"This tree could not be drawn:<br>{error}")


def _tree_text_for(result, scale):
    if not result:
        return None
    if scale == TIME_SCALE:
        return result.get("time_tree_nexus")
    return result.get("substitution_newick")


def _annotator_for(result, color_by):
    records = (result or {}).get("tip_records")
    if not records:
        return None
    field = color_by or None
    color_map = None
    if field:
        # Curated schemes differ per pathogen: "genotype" means different values for each
        color_map = color_map_for_pathogen_field(
            (result or {}).get("pathogen"), field, [row.get(field) for row in records])
    return MetadataAnnotator(
        records,
        key_col=result["key_column"],
        color_by=field,
        hover_cols=[c for c in result["metadata_columns"] if c != result["key_column"]],
        color_map=color_map,
    )


def _matching_tips(tree_text, query):
    query = (query or "").strip().lower()
    if not query:
        return []
    try:
        tree = parse_newick(tree_text)
    except NewickParseError:
        return []
    return [tip.name for tip in tree.tips if query in tip.name.lower()]


def _clamp_label_size(value):
    if value is None or value == "":
        return None
    try:
        size = int(float(value))
    except (TypeError, ValueError):
        return None
    return max(LABEL_SIZE_MIN, min(LABEL_SIZE_MAX, size))


def placeholder_figure(message):
    """An empty figure carrying a message, so a bad tree never breaks the page."""
    figure = go.Figure()
    figure.update_layout(
        paper_bgcolor=LIGHT["paper"],
        plot_bgcolor=LIGHT["plot"],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=20, b=20),
        annotations=[dict(text=message, xref="paper", yref="paper", x=0.5, y=0.5,
                          showarrow=False, align="center",
                          font=dict(size=13, color=LIGHT["muted"]))],
    )
    return figure


# ── Provenance notes ───────────────────────────────────────────────────────


def result_notes(result):
    """What the figure cannot say for itself: clock quality and join outcomes."""
    if not result or result.get("status") != "done":
        return []
    return [note for note in (
        _clock_note(result.get("clock"), bool(result.get("time_tree_nexus"))),
        _metadata_note(result.get("metadata_report")),
        _tip_set_note(result.get("tip_set_report")),
        _support_threshold_note(),
    ) if note is not None]


def _note(icon, text, css):
    return html.Div([html.I(className=f"{icon} me-2"), text], className=f"{css} mb-1")


def _clock_note(clock, dated_tree_available):
    if not dated_tree_available:
        reason = "the temporal stage did not run for this job"
        if clock and clock.get("status"):
            reason = f"the temporal stage reported '{clock['status']}'"
        return _note("fas fa-clock",
                     f"No dated tree — {reason}. The substitution tree is not time-scaled.",
                     NOTE_CSS)
    if not clock:
        return None
    rate = clock.get("clock_rate")
    r_squared = clock.get("r_squared")
    dated = clock.get("dated_tips")
    total = clock.get("tree_tips")
    text = (f"Molecular clock: {rate:.2e} substitutions/site/year, "
            f"R² = {r_squared:.2f}, {dated}/{total} tips dated."
            if rate is not None and r_squared is not None
            else f"Molecular clock: {dated}/{total} tips dated.")
    # Low R² = weak temporal signal (still show the tree)
    return _note("fas fa-clock", text, NOTE_CSS)


def _metadata_note(report):
    if not report:
        return None
    unmatched = report.get("unmatched") or []
    duplicated = report.get("duplicated") or []
    if not unmatched and not duplicated:
        return _note("fas fa-circle-check",
                     f"Metadata joined for all {report['matched']} tips.", NOTE_CSS)
    parts = []
    if unmatched:
        parts.append(f"{len(unmatched)} tip(s) have no metadata "
                     f"({_first_few(unmatched)})")
    if duplicated:
        parts.append(f"{len(duplicated)} accession(s) appear more than once in the "
                     f"metadata ({_first_few(duplicated)}); the first row was used")
    return _note("fas fa-triangle-exclamation",
                 f"Metadata joined for {report['matched']} tips; " + "; ".join(parts) + ".",
                 NOTE_CSS)


def _tip_set_note(report):
    if not report:
        return None
    dropped = report.get("only_in_substitution") or []
    added = report.get("only_in_time_tree") or []
    if not dropped and not added:
        return None
    parts = []
    if dropped:
        parts.append(f"{len(dropped)} tip(s) are missing from the dated tree "
                     f"({_first_few(dropped)}) — TreeTime excludes undated sequences "
                     "and clock outliers")
    if added:
        parts.append(f"{len(added)} tip(s) appear only in the dated tree "
                     f"({_first_few(added)})")
    return _note("fas fa-code-branch", "; ".join(parts) + ".", NOTE_CSS)


def _support_threshold_note():
    return _note(
        "fas fa-info-circle",
        "Robust clades: SH-aLRT ≥ 80% | UFBoot ≥ 95%",
        NOTE_CSS,
    )


def _first_few(labels, limit=3):
    shown = ", ".join(labels[:limit])
    return shown if len(labels) <= limit else f"{shown}, +{len(labels) - limit} more"


# ── Tip detail ─────────────────────────────────────────────────────────────


def tip_detail_card(accession, result):
    """The metadata row behind one tip, plus a link to its GenBank record."""
    rows = []
    records = (result or {}).get("tip_records")
    if records:
        record = MetadataAnnotator(records, key_col=result["key_column"]).lookup(accession)
        if record:
            rows = [
                html.Tr([
                    html.Td(str(key), className="pe-3 text-muted",
                            style={"whiteSpace": "nowrap"}),
                    html.Td(str(value)),
                ])
                for key, value in record.items()
                if value not in (None, "") and str(value).lower() != "nan"
            ]

    body = [html.Div(accession, className="fw-bold text-break",
                     style={"fontSize": "13px"})]
    body.append(
        dbc.Table(html.Tbody(rows), borderless=True, size="sm",
                  className="mb-1 mt-2", style={"fontSize": "12px"})
        if rows else
        html.Div("No metadata for this tip.", className="text-muted small mt-2")
    )
    url = ncbi_url(accession)
    if url:
        body.append(html.A(
            [html.I(className="fas fa-arrow-up-right-from-square me-1"), "Open on NCBI"],
            href=url, target="_blank", rel="noopener noreferrer", className="small",
        ))
    return dbc.Card(dbc.CardBody(body, className="py-2 px-3"), className="mt-2")


# ── Callback registration ──────────────────────────────────────────────────


def register_phylogeny_callbacks(app, prefix, result_store_id):
    """Wire one viewer instance to the store holding its result dictionary.

    Call once at page-module import. The store is filled by whoever owns the job
    workflow; this panel only reads it.

    `app` is a Dash app, or Dash's module-level `callback` — a page module is
    imported before any app exists, so that is what a Dash Pages page has to pass.
    """
    cid = panel_ids(prefix)
    register = getattr(app, "callback", app)

    @register(
        Output(cid["graph"], "figure"),
        Input(result_store_id, "data"),
        Input(cid["scale"], "value"),
        Input(cid["layout"], "value"),
        Input(cid["rotation"], "value"),
        Input(cid["toggles"], "value"),
        Input(cid["support_min"], "value"),
        Input(cid["support_metric"], "value"),
        Input(cid["color_by"], "value"),
        Input(cid["search"], "value"),
        Input(cid["label_size"], "value"),
    )
    def _update_figure(result, scale, layout, rotation, toggles, support_min,
                       support_metric, color_by, search, label_size):
        return build_phylogeny_figure(
            result, scale=scale, layout=layout, rotation=rotation, toggles=toggles,
            support_min=support_min, support_metric=support_metric,
            color_by=color_by, search=search,
            label_size=label_size,
        )

    # Dim rotation on rectangular layout (no effect)
    @register(
        Output(cid["rotation"], "disabled"),
        Output(cid["rotation_wrap"], "style"),
        Input(cid["layout"], "value"),
    )
    def _toggle_rotation(layout):
        rotatable = layout in _ROTATING_LAYOUTS
        return (not rotatable), _rotation_style(rotatable)

    @register(
        Output(cid["scale"], "options"),
        Output(cid["scale"], "value"),
        Output(cid["color_by"], "options"),
        Output(cid["color_by"], "value"),
        Output(cid["notes"], "children"),
        Input(result_store_id, "data"),
        State(cid["color_by"], "value"),
    )
    def _configure_for_result(result, current_color_by):
        if not result or result.get("status") != "done":
            return (_scale_options(False), SUBSTITUTION_SCALE, [], None, [])

        dated = bool(result.get("time_tree_nexus"))
        reason = None if dated else "This job produced no dated tree."
        fields = result.get("color_by_fields") or []
        options = [{"label": _FIELD_LABELS.get(f, f), "value": f} for f in fields]
        color_by = current_color_by if current_color_by in fields else (
            fields[0] if fields else None)
        return (
            _scale_options(dated, reason),
            TIME_SCALE if dated else SUBSTITUTION_SCALE,
            options,
            color_by,
            result_notes(result),
        )

    @register(
        Output(cid["detail"], "children"),
        Input(cid["graph"], "clickData"),
        State(result_store_id, "data"),
    )
    def _show_detail(click_data, result):
        points = (click_data or {}).get("points")
        if not points:
            return no_update
        custom = points[0].get("customdata") or []
        if not custom:
            return no_update
        return tip_detail_card(str(custom[0]), result)
