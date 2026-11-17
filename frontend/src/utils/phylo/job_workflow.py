"""The phylogeny job workflow: request a tree, watch it build, show the result.

Extracted from dengue_page so any registered pathogen can mount it. Ids come from the
spec's id_suffix, the way panel_ids(prefix) does for the viewer, so two pages can carry the
workflow at once without colliding.

The page supplies `data`: its sequence frame, its geojson, its filter vocabulary and the
database client. Nothing here names a pathogen.
"""

import json

import dash_bootstrap_components as dbc
from dash import Input, Output, State, clientside_callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

import config
from components import phylo_method_selector
from utils.functions.selection_functions import (
    RESET_FILTER,
    apply_selection_to_sequences,
    canonical_accession_ids,
    selection_from_dict,
)
from utils.phylo.panel import phylogeny_panel, register_phylogeny_callbacks
from utils.phylo.precheck import evaluate_phylo_eligibility
from utils.phylo.result_provider import load_phylogeny_result, load_phylogeny_status

TOGGLE_BLOCK_HIDDEN = "d-none"
TOGGLE_BLOCK_VISIBLE = "my-1"
BLOCK_HIDDEN = {"display": "none"}
BLOCK_VISIBLE = {"display": "block"}


def phylo_ids(spec):
    """Every id the workflow declares, all carrying the pathogen's suffix."""
    suffix = spec["id_suffix"]
    return {
        "prefix": f"{suffix}-phylo",
        "result_store": f"{suffix}-phylo-result",
        "toggle": f"phylo-toggle-{suffix}",
        "toggle_target": f"phylo-toggle-target-{suffix}",
        "toggle_tooltip": f"phylo-toggle-tooltip-{suffix}",
        "toggle_block": f"phylo-toggle-block-{suffix}",
        "precheck": f"phylo-precheck-{suffix}",
        "scroll_dummy": f"phylo-scroll-dummy-{suffix}",
        "card_row": f"phylo-card-row-{suffix}",
        "options": f"phylo-options-{suffix}",
        "completeness": f"phylo-completeness-{suffix}",
        "reuse": f"phylo-reuse-{suffix}",
        "start": f"phylo-start-{suffix}",
        "start_status": f"phylo-start-status-{suffix}",
        "poll": f"phylo-poll-{suffix}",
        "active_job": f"phylo-active-job-{suffix}",
        "stage": f"phylo-stage-{suffix}",
        "runtime": f"phylo-runtime-{suffix}",
        "status_line": f"phylo-status-line-{suffix}",
        "event_log": f"phylo-event-log-{suffix}",
        "retry": f"phylo-retry-{suffix}",
        "retry_block": f"phylo-retry-block-{suffix}",
        "result_block": f"phylo-result-block-{suffix}",
        "method": f"phylo-method-{suffix}",
    }


PHYLO_EVENT_ICONS = {
    "info": "fas fa-circle-check",
    "warning": "fas fa-triangle-exclamation",
    "error": "fas fa-circle-xmark",
}


def phylo_toggle_column(spec):
    """The switch that reveals the card, for the basic filter row."""
    ids = phylo_ids(spec)
    return (
        dbc.Col([
            html.Span(
                "Phylogenetic tree",
                className="form-label mb-1 small dashboard-form-label me-2"
            ),
            html.Span(
                dbc.Switch(
                    id=ids["toggle"],
                    value=False,
                    disabled=True,
                    className="d-inline-block",
                ),
                id=ids["toggle_target"],
            ),
            dbc.Tooltip(
                "",
                id=ids["toggle_tooltip"],
                target=ids["toggle_target"],
            ),
        ],
            id=ids["toggle_block"],
            sm=12, lg=12,
            className=TOGGLE_BLOCK_HIDDEN,
        )
    )


def phylo_rows(spec):
    """The stores and the tree card, for the page's extra rows."""
    ids = phylo_ids(spec)
    return [
        # Cached phylo pre-check (from Apply)
        dcc.Store(id=ids["precheck"]),
        # Unused sink for clientside scroll callback
        dcc.Store(id=ids["scroll_dummy"]),
        dbc.Row(
            id=ids["card_row"],
            className="mb-4",
            style={"display": "none"},
            children=[
                dbc.Col(
                    className="col-md-12",
                    children=[
                        dbc.Card([
                            dbc.CardHeader(
                                html.H5("Phylogenetic Tree", className="mb-0 dashboard-h5")
                            ),
                            dbc.CardBody([
                                dbc.Card(
                                    id=ids["options"],
                                    body=True,
                                    children=[
                                        dbc.Row([
                                            dbc.Col([
                                                dbc.Row([
                                                    dbc.Col([
                                                        html.Label(
                                                            "Sequence quality:",
                                                            className="form-label mb-1 small dashboard-form-label"
                                                        ),
                                                        dbc.RadioItems(
                                                            id=ids["completeness"],
                                                            options=[
                                                                {"label": "Complete genomes only", "value": "complete_genome"},
                                                                {"label": "Any length",            "value": "any"},
                                                            ],
                                                            value="complete_genome",
                                                        ),
                                                    ], sm=12, md=4, className="my-1"),
                                                    phylo_method_selector.load(component_id=ids["method"], sm=12, md=4),
                                                    dbc.Col([
                                                        html.Label(
                                                            "Existing tree:",
                                                            className="form-label mb-1 small dashboard-form-label"
                                                        ),
                                                        dbc.RadioItems(
                                                            id=ids["reuse"],
                                                            options=[
                                                                {"label": "Reuse if available", "value": "reuse"},
                                                                {"label": "Build a new tree",   "value": "rebuild"},
                                                            ],
                                                            value="reuse",
                                                        ),
                                                    ], sm=12, md=4, className="my-1"),
                                                ], className="g-3"),
                                            ], md=12, lg=9),

                                            dbc.Col(
                                                dbc.Button(
                                                    "Build phylogenetic tree",
                                                    id=ids["start"],
                                                    color="outline-primary",
                                                    className="mb-3 mt-3 dashboard-btn-apply w-100",
                                                ),
                                                md=12, lg=3,
                                                className="d-flex flex-column justify-content-center align-items-center",
                                            ),
                                        ]),
                                        html.Div(
                                            id=ids["start_status"],
                                            className="small mt-2 text-center text-muted",
                                        ),
                                    ],
                                ),
                                # Job poll interval + stores
                                dcc.Interval(
                                    id=ids["poll"],
                                    interval=config.PHYLO_POLL_MS,
                                    n_intervals=0,
                                    disabled=True,
                                ),
                                dcc.Store(id=ids["active_job"]),
                                dcc.Store(id=ids["result_store"]),
                                dcc.Store(id=ids["stage"]),

                                dbc.Card(
                                    id=ids["runtime"],
                                    body=True,
                                    color="light",
                                    style=BLOCK_HIDDEN,
                                    children=[
                                        html.Div(
                                            "Backend runtime information",
                                            className="dashboard-h5 mb-2 text-center",
                                        ),
                                        html.Div(id=ids["status_line"], className="small fw-bold mb-2"),
                                        html.Ul(id=ids["event_log"], className="list-unstyled small mb-0"),
                                        dbc.Row(
                                            dbc.Col(
                                                dbc.Button(
                                                    [html.I(className="fas fa-rotate-left me-2"), "Return to options"],
                                                    id=ids["retry"],
                                                    color="secondary",
                                                    size="sm",
                                                    outline=True,
                                                ),
                                                width="auto",
                                            ),
                                            id=ids["retry_block"],
                                            style=BLOCK_HIDDEN,
                                            justify="center",
                                            className="mt-3",
                                        ),
                                    ],
                                ),

                                dbc.Card(
                                    id=ids["result_block"],
                                    body=True,
                                    style=BLOCK_HIDDEN,
                                    children=[
                                        html.Div(
                                            "Phylogenetic result",
                                            className="dashboard-h5 mb-2 text-center",
                                        ),
                                        phylogeny_panel(ids["prefix"]),
                                    ],
                                ),
                            ]),
                        ], className="shadow-sm"),
                    ],
                ),
            ],
        ),
    ]


def register_phylo_job_callbacks(spec, data, callback):
    """Wire the workflow for one pathogen. `callback` is Dash's callback decorator."""
    ids = phylo_ids(spec)

    # The viewer's own controls (scale, layout, colour-by, search) drive the graph; without
    # this the card renders but nothing ever puts a figure in it
    register_phylogeny_callbacks(callback, ids["prefix"], ids["result_store"])

    def _render_event_log(events):
        if not events:
            return []
        items = []
        for event in events:
            level = event.get("level", "info")
            icon = PHYLO_EVENT_ICONS.get(level, "fas fa-circle")
            css = "text-danger" if level == "error" else ("text-warning" if level == "warning" else "text-muted")
            items.append(
                html.Li([html.I(className=f"{icon} me-2"), event.get("message", "")], className=f"{css} mb-1")
            )
        return items


    @callback(
        [
            Output(ids["status_line"], "children"),
            Output(ids["event_log"], "children"),
            Output(ids["poll"], "disabled", allow_duplicate=True),
            Output(ids["result_store"], "data", allow_duplicate=True),
            Output(ids["stage"], "data", allow_duplicate=True),
        ],
        Input(ids["poll"], "n_intervals"),
        State(ids["active_job"], "data"),
        prevent_initial_call=True,
    )
    def poll_phylo_job(_n_intervals, job_id):
        # Poll status/log; fetch tree text once on completion
        if not job_id:
            raise PreventUpdate
        progress = load_phylogeny_status(data["database"], job_id)
        if not progress:
            raise PreventUpdate

        status = progress["status"]
        event_items = _render_event_log(progress["events"])

        if status == "done":
            result = load_phylogeny_result(data["database"], job_id, spec)
            tips = progress["sequence_count"]
            engine = progress["inference_method"]
            summary = ", ".join(part for part in (
                f"{tips} tips" if tips is not None else None,
                engine,
                "dated tree available" if result.get("time_tree_nexus") else "no dated tree",
            ) if part)
            status_line = [html.I(className="fas fa-circle-check text-success me-2"),
                           f"Tree ready ({summary})."]
            return status_line, event_items, True, result, "done"

        if status == "failed":
            error_text = progress["error_message"] or "Tree generation failed."
            status_line = [html.I(className="fas fa-circle-xmark text-danger me-2"), f"Failed: {error_text}"]
            return status_line, event_items, True, no_update, "failed"

        # pending → Queued; processing → Running
        running_text = "Queued…" if status == "pending" else "Running…"
        status_line = [html.I(className="fas fa-spinner fa-spin me-2"), running_text]
        return status_line, event_items, False, no_update, "running"


    # Phylo tree generation — pre-check, toggle, job submission

    @callback(
        [
            Output(ids["precheck"], "data"),
            Output(ids["toggle_block"], "className"),
        ],
        Input(data["applied_selection_id"], "data"),
        prevent_initial_call=True,
    )
    def evaluate_phylo_precheck(applied_selection):
        # In-memory pre-check from applied selection (not widgets)
        if not applied_selection:
            raise PreventUpdate

        selection = selection_from_dict(applied_selection)

        # Reset: hide toggle until next Apply
        if selection["source"] == RESET_FILTER:
            return None, TOGGLE_BLOCK_HIDDEN

        filtered_df = apply_selection_to_sequences(
            data["frame"], selection, data["geojson"],
            classification_column=spec["classification_column"])

        precheck = evaluate_phylo_eligibility(
            filtered_df["length"],
            whole_genome_min=config.WHOLE_GENOME_MIN_LENGTH,
            min_length=config.MIN_SEQUENCE_LENGTH,
            min_tips=config.MIN_TREE_TIPS,
            max_sequences=config.MAX_SEQUENCES,
        )
        # Reveal toggle; card stays hidden until switch is on
        return precheck, TOGGLE_BLOCK_VISIBLE


    @callback(
        [
            Output(ids["toggle"], "disabled"),
            Output(ids["toggle_tooltip"], "children"),
            Output(ids["toggle"], "value"),
        ],
        Input(ids["precheck"], "data"),
        prevent_initial_call=True,
    )
    def gate_phylo_toggle(precheck):
        # Enable only when eligible; force off on every Apply/Reset
        if not precheck:
            return True, "Apply a filter first to check whether a tree can be built.", False

        can_generate = precheck.get("can_generate", False)
        reason = precheck.get("reason", "")
        return (not can_generate), reason, False


    @callback(
        [
            Output(ids["card_row"], "style"),
            Output(ids["stage"], "data"),
            Output(ids["poll"], "disabled", allow_duplicate=True),
            Output(ids["active_job"], "data", allow_duplicate=True),
            Output(ids["result_store"], "data", allow_duplicate=True),
            Output(ids["start_status"], "children", allow_duplicate=True),
        ],
        Input(ids["toggle"], "value"),
        prevent_initial_call=True,
    )
    def reveal_phylo_card(is_on):
        # Toggle change (incl. forced-off) clears any tracked job
        card_style = BLOCK_VISIBLE if is_on else BLOCK_HIDDEN
        return card_style, "options", True, None, None, ""


    @callback(
        [
            Output(ids["options"], "style"),
            Output(ids["runtime"], "style"),
            Output(ids["result_block"], "style"),
            Output(ids["retry_block"], "style"),
        ],
        Input(ids["stage"], "data"),
        prevent_initial_call=True,
    )
    def apply_phylo_stage(stage):
        if stage == "running":
            return BLOCK_HIDDEN, BLOCK_VISIBLE, BLOCK_HIDDEN, BLOCK_HIDDEN
        if stage == "done":
            return BLOCK_HIDDEN, BLOCK_HIDDEN, BLOCK_VISIBLE, BLOCK_HIDDEN
        if stage == "failed":
            # Keep runtime block visible for failure log
            return BLOCK_HIDDEN, BLOCK_VISIBLE, BLOCK_HIDDEN, BLOCK_VISIBLE
        return BLOCK_VISIBLE, BLOCK_HIDDEN, BLOCK_HIDDEN, BLOCK_HIDDEN


    @callback(
        [
            Output(ids["stage"], "data", allow_duplicate=True),
            Output(ids["active_job"], "data", allow_duplicate=True),
            Output(ids["start_status"], "children", allow_duplicate=True),
        ],
        Input(ids["retry"], "n_clicks"),
        prevent_initial_call=True,
    )
    def return_to_phylo_options(_n_clicks):
        return "options", None, ""


    # Smooth-scroll to phylo card (clientside)
    clientside_callback(
        """
        function(isOn) {
            if (isOn) {
                const card = document.getElementById('__CARD_ROW__');
                if (card) { card.scrollIntoView({behavior: 'smooth', block: 'start'}); }
            }
            return window.dash_clientside.no_update;
        }
        """.replace("__CARD_ROW__", ids["card_row"]),
        Output(ids["scroll_dummy"], "data"),
        Input(ids["toggle"], "value"),
        prevent_initial_call=True,
    )


    @callback(
        [
            Output(ids["start_status"], "children"),
            Output(ids["active_job"], "data"),
            Output(ids["poll"], "disabled"),
            Output(ids["stage"], "data", allow_duplicate=True),
            Output(ids["result_store"], "data", allow_duplicate=True),
        ],
        Input(ids["start"], "n_clicks"),
        [
            State(data["applied_selection_id"], "data"),
            State(ids["completeness"], "value"),
            State(ids["method"], "value"),
            State(ids["reuse"], "value"),
        ],
        prevent_initial_call=True,
    )
    def submit_phylo_job(
        n_clicks, applied_selection, phylo_completeness, inference_method, existing_tree_choice,
    ):
        # Uses dengue-applied-selection (same set as pre-check)
        if not applied_selection:
            return ("Apply a filter before requesting a tree.", no_update, True, "options", no_update)

        selection = selection_from_dict(applied_selection)
        selected_classifications = selection["classifications"]
        selected_subclassifications = selection["subclassifications"]
        selected_countries = selection["countries"]
        selected_continents = selection["continents"]
        selected_hosts = selection["hosts"]

        start_date_str = selection["date_from"].strftime("%Y-%m-%d")
        end_date_str = selection["date_to"].strftime("%Y-%m-%d")

        # Omit "all selected" fields — filter_params is String(1000)
        filter_params = {
            "start_date": start_date_str,
            "end_date": end_date_str,
            "completeness": phylo_completeness,
        }
        # The backend reads filter_params for provenance only; the accession set is what it
        # actually builds from. Keys follow the pathogen's own classification columns.
        available = data["vocabulary"]()
        narrowable_fields = [
            (spec["classification_column"], selected_classifications,
             available["classifications"]),
            ("country", selected_countries, available["countries"]),
            ("continent", selected_continents, available["continents"]),
            ("host", selected_hosts, available["hosts"]),
        ]
        if spec["subclassification_column"]:
            narrowable_fields.insert(1, (spec["subclassification_column"],
                                         selected_subclassifications,
                                         available["subclassifications"]))
        for key, selected_values, all_values in narrowable_fields:
            if selected_values and set(selected_values) != set(all_values):
                filter_params[key] = selected_values

        # Opt out of watcher tree reuse
        if existing_tree_choice == "rebuild":
            filter_params["force_rebuild"] = True

        selected_sequences = apply_selection_to_sequences(
            data["frame"], selection, data["geojson"],
            classification_column=spec["classification_column"])
        accession_ids = canonical_accession_ids(selected_sequences["genbank_sequence_data_id"])
        if not accession_ids:
            return ("The current filter selects no sequences.", no_update, True, "options", no_update)

        try:
            job_id = data["database"].add_phylo_job(
                json.dumps(filter_params),
                accession_ids,
                pathogen=spec["backend_pathogen_code"],
                inference_method=inference_method,
            )
            status = f"Queued (job #{job_id}). Tracking progress below…"
            # Start poller; clear previous tree
            return status, job_id, False, "running", None
        except Exception as exc:
            # Stay on options so the queue error remains visible
            return f"Could not queue the tree request: {exc}", no_update, True, "options", no_update

    # Returned so a page (or a test) can call the workflow's handlers directly
    return {
        "poll": poll_phylo_job,
        "precheck": evaluate_phylo_precheck,
        "gate_toggle": gate_phylo_toggle,
        "reveal_card": reveal_phylo_card,
        "apply_stage": apply_phylo_stage,
        "retry": return_to_phylo_options,
        "submit": submit_phylo_job,
    }
