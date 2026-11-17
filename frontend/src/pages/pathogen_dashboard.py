"""The dashboard shared by /dengue, /chikungunya and /zika.

One implementation behind the three existing routes. Everything that differs between
pathogens arrives through the spec (src/pathogens.py) or through `view`, the display state
the page has already computed; nothing here branches on which pathogen it is building.

Component ids are derived from the spec's id_suffix by page_ids(), the way panel_ids(prefix)
derives the phylogeny panel's ids, so two pages never collide.

`filter_extras` and `extra_rows` are the two insertion points a page can use to add its own
blocks — dengue mounts its phylogeny toggle and card through them. The core does not know
what they contain.
"""

import dash_bootstrap_components as dbc
import dash_leaflet as dl
import pandas as pd
from dash import Input, Output, State, callback, ctx, dcc, html, no_update

from components import header
from graphs import bar, map
from graphs.area_plot import plot_area_chat
from utils.functions.date_functions import (
    date_to_slider_value,
    slider_value_to_date,
    slider_year_month_marks,
    today_in_dashboard_timezone,
)
from utils.functions.filter_functions import filter_by_continents
from utils.functions.selection_functions import (
    apply_selection_fields,
    classify_filter_source,
    resolve_filter_selection,
    selection_to_dict,
)


def page_ids(spec):
    """Every component id this layout declares, all carrying the pathogen's suffix."""
    suffix = spec["id_suffix"]
    return {
        "body": f"{suffix}-body-container",
        "download_store": f"{suffix}-download-store",
        # The resolved selection, kept so the phylogeny workflow can read what was applied
        "applied_selection": f"{suffix}-applied-selection",

        "n_sequences": f"n-sequences-selected-{suffix}",
        "n_countries": f"n-countries-selected-{suffix}",
        "n_hosts": f"n-hosts-selected-{suffix}",

        "basic_classification": f"classification-select-basic-{suffix}",
        "basic_regions": f"names-input-basic-{suffix}",
        "basic_start_date": f"start-date-basic-{suffix}",
        "basic_end_date": f"end-date-basic-{suffix}",
        "basic_apply": f"filter-button-{suffix}",
        "basic_reset": f"reset-filters-button-{suffix}",
        "open_advanced": f"advanced-filters-btn-{suffix}",
        "open_advanced_mobile": f"advanced-filters-btn-{suffix}-mobile",
        "reset_mobile": f"reset-filters-button-{suffix}-mobile",

        "region_mode": f"countries-radio-{suffix}",
        "region_mode_marker": f"countries-or-continents-{suffix}",
        "countries_select": f"countries-select-{suffix}",
        "countries_block": f"div-countries-select-{suffix}",
        "continents_select": f"continents-select-{suffix}",
        "continents_block": f"div-continents-select-{suffix}",
        "classification_select": f"classification-select-{suffix}",
        "subclassification_select": f"subclassification-select-{suffix}",
        "host_select": f"host-select-{suffix}",
        "advanced_start_date": f"start-date-advanced-{suffix}",
        "advanced_end_date": f"end-date-advanced-{suffix}",
        "date_slider": f"date-range-slider-{suffix}",
        "date_display": f"date-range-display-{suffix}",
        "advanced_apply": f"apply-filters-modal-btn-{suffix}",
        "advanced_close": f"close-modal-btn-{suffix}",
        "advanced_modal": f"advanced-modal-{suffix}",

        "map_block": f"colorpath-map-{suffix}",
        "map": f"leaflet_map_{suffix}",
        "bar_title": f"bar-chart-title-{suffix}",
        "bar_block": f"div-bar-plot-{suffix}",
        "bar_graph": f"bar-plot-{suffix}",
        "area_title": f"area-chart-title-{suffix}",
        "area_graph": f"area-chart-graph-{suffix}",
    }


def chart_titles(classification_column):
    """Card headings follow whichever axis is currently colouring the charts."""
    axis = f"{classification_column.capitalize()}s"
    return f"Circulating {axis}", f"Temporal Spread of {axis}"


def _stat_card(value, label, element_id, icon_class, icon_width, text_width):
    return dbc.Col([
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.I(className=icon_class)
                    ], lg=12, xl=icon_width,
                        class_name="d-flex flex-column justify-content-center h-100"),
                    dbc.Col([
                        html.Div([
                            html.H4(value, id=element_id, className="mb-0 fw-bold dashboard-h4"),
                            html.P(label, className="mb-0 small text-muted")
                        ], className="d-flex flex-column justify-content-center h-100")
                    ], lg=12, xl=text_width, className="d-flex align-items-center")
                ], class_name="justify-content-center")
            ])
        ], className="h-100 shadow-sm")
    ], sm=12, lg=4)


def _header_row(spec, view, ids):
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    header.load(select_pathogen_value=spec["title"]),
                    html.Span(f"Last updated: {view['last_updated_date']}",
                              className="text-muted small"),
                    dbc.ButtonGroup([
                        dbc.Button(
                            children=[
                                html.I(className="fas fa-filter me-2"),
                                html.Span("Filters")
                            ],
                            id=ids["open_advanced_mobile"],
                            color="primary",
                            outline=False,
                            size="sm",
                            className="mb-3 mt-3 ms-3 dashboard-btn-apply"
                        ),
                        dbc.Button(
                            "Reset Filters",
                            id=ids["reset_mobile"],
                            color="danger",
                            size="sm",
                            className="mb-3 mt-3 me-3 dashboard-btn-reset"
                        ),
                    ], vertical=False, className="d-block d-md-none mx-auto"),
                ], class_name="justify-content-center")
            ], className="h-100 shadow-sm")
        ], md=12, lg=6, xl=7, class_name="my-1"),

        dbc.Col([
            dbc.Row([
                _stat_card(view["n_sequences"], "Genomes selected", ids["n_sequences"],
                           "fas fa-dna fa-2x text-purple my-3", 5, 7),
                _stat_card(view["n_countries"], "Countries selected", ids["n_countries"],
                           "fas fa-globe fa-2x text-success my-2", 4, 8),
                _stat_card(view["n_hosts"], "Hosts selected", ids["n_hosts"],
                           "fas fa-mosquito fa-2x text-warning my-3", 5, 7),
            ])
        ], md=12, lg=6, xl=5,
            className="d-none d-lg-flex align-items-stretch justify-content-end my-1"),
    ], className="mb-4 align-items-stretch")


def _basic_filter_row(spec, view, ids, window_end, filter_extras):
    classification_label = spec["classification_column"].capitalize()
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Row([
                                dbc.Col([
                                    html.Label(f"Select {classification_label.lower()}:",
                                               className="form-label mb-1 small dashboard-form-label"),
                                    dcc.Dropdown(
                                        view["classifications"],
                                        view["classifications"],
                                        multi=True,
                                        id=ids["basic_classification"],
                                        placeholder=f"Select {classification_label.lower()}s...",
                                        style={"fontSize": "14px"}
                                    )
                                ], sm=6, lg=4, className="my-1"),

                                dbc.Col([
                                    html.Label("Search by region:",
                                               className="form-label mb-1 small dashboard-form-label"),
                                    dcc.Dropdown(
                                        id=ids["basic_regions"],
                                        options=view["regions"],
                                        value=[],
                                        multi=True,
                                        placeholder="Type to search countries or regions...",
                                        searchable=True,
                                        style={"fontSize": "14px"},
                                        className="custom-dropdown"
                                    )
                                ], sm=6, lg=4, className="my-1"),

                                dbc.Col([
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.InputGroup([
                                                dbc.InputGroupText("From:", className="small dashboard-form-label", style={"fontSize": "12px", "width": "30%"}),
                                                dcc.DatePickerSingle(
                                                    id=ids["basic_start_date"],
                                                    date=view["min_date"].date(),
                                                    display_format="YYYY-MM-DD",
                                                    style={"fontSize": "12px", "width": "50%"}
                                                )
                                            ], size="sm")
                                        ], width="auto"),
                                        dbc.Col([
                                            dbc.InputGroup([
                                                dbc.InputGroupText("To:", className="small dashboard-form-label", style={"fontSize": "12px", "width": "32.5%"}),
                                                dcc.DatePickerSingle(
                                                    id=ids["basic_end_date"],
                                                    date=window_end.date(),
                                                    display_format="YYYY-MM-DD",
                                                    style={"fontSize": "12px", "width": "50%"}
                                                )
                                            ], size="sm")
                                        ], width="auto")
                                    ], className="gap-1 align-items-center justify-content-start")
                                ], sm=12, lg=4,
                                    className="d-flex align-items-center justify-content-center my-1"),
                            ] + list(filter_extras or []))
                        ], md=12, lg=9),

                        dbc.Col([
                            dbc.ButtonGroup([
                                dbc.Button(
                                    "Apply Filters",
                                    id=ids["basic_apply"],
                                    color="outline-primary",
                                    size="s",
                                    className="mb-3 mt-3 ms-3 dashboard-btn-apply"
                                ),
                                dbc.Button(
                                    "Reset Filters",
                                    id=ids["basic_reset"],
                                    color="outline-danger",
                                    size="sm",
                                    className="mb-3 mt-3 me-3 dashboard-btn-reset"
                                ),
                            ], vertical=False, className="w-100"),
                            dbc.Button(
                                children=[
                                    html.I(className="fas fa-filter me-2"),
                                    html.Span("Advanced Filters", className="btn-text")
                                ],
                                id=ids["open_advanced"],
                                color="light",
                                outline=False,
                                size="sm",
                                className="text-btn d-flex justify-content-center align-items-center w-100"
                            )
                        ], md=12, lg=3,
                            className="d-flex flex-column justify-content-center align-items-center")
                    ])
                ])
            ], className="shadow-sm")
        ])
    ], className="mb-4 d-none d-md-flex")


def _region_mode_options():
    return [
        {"label": html.Div(["Show all countries"],
                           style={"display": "inline", "marginLeft": "1em"}), "value": "all"},
        {"label": html.Div(["Select regions"],
                           style={"display": "inline", "marginLeft": "1em"}),
         "value": "filtered-by-regions"},
        {"label": html.Div(["Select countries"],
                           style={"display": "inline", "marginLeft": "1em"}),
         "value": "filtered-by-country"},
    ]


def _classification_dropdowns(spec, view, ids):
    classification_label = spec["classification_column"].capitalize()
    blocks = [
        dbc.Col([
            html.Label(f"Select {classification_label.lower()}:",
                       className="form-label mb-1 small"),
            dcc.Dropdown(
                view["classifications"],
                view["classifications"],
                multi=True,
                id=ids["classification_select"],
                placeholder="Select...",
                className="custom-dropdown",
                style={"fontSize": "14px"}
            ),
        ], width=6, className="mb-3"),
    ]
    # Only dengue declares a second axis; the others simply do not render this dropdown
    if spec["subclassification_column"] is not None:
        sub_label = spec["subclassification_column"].capitalize()
        blocks.append(
            dbc.Col([
                html.Label(f"Select {sub_label.lower()}:", className="form-label mb-1 small"),
                dcc.Dropdown(
                    view["subclassifications"],
                    view["subclassifications"],
                    multi=True,
                    id=ids["subclassification_select"],
                    placeholder="Select...",
                    className="custom-dropdown",
                    style={"fontSize": "14px"}
                ),
            ], width=6, className="mb-3")
        )
    return blocks


def _advanced_modal(spec, view, ids, window_end, latest_selectable_date):
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Advanced Filters")),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Select regions to show:", className="form-label mb-1 small"),
                    dcc.RadioItems(
                        _region_mode_options(),
                        id=ids["region_mode"],
                        value="all",
                        inputClassName="form-check-input",
                        labelClassName="form-check-label"
                    ),
                    html.Div(
                        id=ids["region_mode_marker"],
                        style={"display": "none"},
                        children=["countries"],
                    ),
                ], width=12, className="mb-3"),

                dbc.Col([
                    html.Label("Select countries:", className="form-label mb-1 small"),
                    dcc.Dropdown(
                        view["countries"],
                        view["countries"],
                        multi=True,
                        id=ids["countries_select"],
                        placeholder="Select...",
                        className="custom-dropdown",
                        style={"fontSize": "14px"}
                    ),
                ], width=6, className="mb-3", id=ids["countries_block"],
                    style={"display": "none"}),

                dbc.Col([
                    html.Label("Select continents:", className="form-label mb-1 small"),
                    dcc.Dropdown(
                        view["continents"],
                        view["continents"],
                        multi=True,
                        id=ids["continents_select"],
                        placeholder="Select...",
                        className="custom-dropdown",
                        style={"fontSize": "14px"}
                    ),
                ], width=6, className="mb-3", id=ids["continents_block"],
                    style={"display": "none"}),
            ] + _classification_dropdowns(spec, view, ids) + [

                dbc.Col([
                    html.Label("Select hosts:", className="form-label mb-1 small"),
                    dcc.Dropdown(
                        options=view["hosts"],
                        value=view["hosts"],
                        multi=True,
                        id=ids["host_select"],
                        placeholder="Select...",
                        className="custom-dropdown",
                        style={"fontSize": "14px"}
                    ),
                ], width=6, className="mb-3"),

                dbc.Col([
                    html.Label("Date range:", className="form-label mb-1 small"),
                    dbc.Row([
                        dbc.Col([
                            dbc.InputGroup([
                                dbc.InputGroupText("From:", className="small dashboard-form-label", style={"fontSize": "12px"}),
                                dcc.DatePickerSingle(
                                    id=ids["advanced_start_date"],
                                    date=view["min_date"].date(),
                                    min_date_allowed=view["min_date"].date(),
                                    max_date_allowed=latest_selectable_date.date(),
                                    display_format="YYYY-MM-DD",
                                    style={"fontSize": "12px"}
                                )
                            ], size="sm")
                        ], width="auto"),
                        dbc.Col([
                            dbc.InputGroup([
                                dbc.InputGroupText("To:", className="small dashboard-form-label", style={"fontSize": "12px"}),
                                dcc.DatePickerSingle(
                                    id=ids["advanced_end_date"],
                                    date=window_end.date(),
                                    min_date_allowed=view["min_date"].date(),
                                    max_date_allowed=latest_selectable_date.date(),
                                    display_format="YYYY-MM-DD",
                                    style={"fontSize": "12px"}
                                )
                            ], size="sm")
                        ], width="auto"),
                    ], className="gap-1 align-items-center justify-content-center mb-2"),
                    dcc.RangeSlider(
                        id=ids["date_slider"],
                        min=date_to_slider_value(view["min_date"]),
                        max=date_to_slider_value(latest_selectable_date),
                        step=1,  # day resolution so a typed date round-trips through the slider exactly
                        value=[date_to_slider_value(view["min_date"]),
                               date_to_slider_value(window_end)],
                        marks=slider_year_month_marks(view["min_date"], latest_selectable_date),
                        tooltip={"placement": "bottom", "always_visible": True,
                                 "transform": "sliderDaysToDate"}
                    ),
                    html.Div(id=ids["date_display"],
                             className="mt-2 text-center small text-muted")
                ], width=12, className="mb-3"),
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button("Apply Filters", id=ids["advanced_apply"], color="primary", size="sm"),
            dbc.Button("Close", id=ids["advanced_close"], color="secondary", size="sm")
        ])
    ], id=ids["advanced_modal"], is_open=False, size="lg")


def _map_row(view, ids):
    return dbc.Row(
        className="mb-4",
        children=[
            dbc.Col(
                className="col-md-12",
                children=[
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Geographic Distribution", className="mb-0 dashboard-h5")
                        ]),
                        dbc.CardBody([
                            dbc.Col(
                                className="col-md-12",
                                children=[
                                    html.Div(
                                        id=ids["map_block"],
                                        className="map-container",
                                        children=[
                                            dl.Map(
                                                id=ids["map"],
                                                center=[0, 0],
                                                zoom=2,
                                                minZoom=1,
                                                maxZoom=5,
                                                className="responsive-map",
                                                children=view["map_components"]
                                            )
                                        ],
                                    )
                                ],
                            ),
                        ])
                    ], className="shadow-sm")
                ]
            )
        ],
    )


def _chart_rows(view, ids, bar_title, area_title):
    return [
        dbc.Row(
            className="mb-4",
            children=[
                dbc.Col(children=[
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5(id=ids["bar_title"], children=bar_title,
                                    className="mb-0 dashboard-h5")
                        ]),
                        dbc.CardBody([
                            dbc.Col(
                                className="mt-2",
                                id=ids["bar_block"],
                                children=[
                                    dcc.Graph(id=ids["bar_graph"], figure=view["bar_figure"],
                                              style={'height': '500px'}),
                                ],
                            ),
                        ])
                    ], className="shadow-sm")
                ])
            ]
        ),
        dbc.Row(
            className="mb-4",
            children=[
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5(id=ids["area_title"], children=area_title,
                                    className="mb-0 dashboard-h5")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(id=ids["area_graph"], figure=view["area_figure"],
                                      style={'height': '1000px'})
                        ])
                    ], className="shadow-sm")
                ])
            ]
        ),
    ]


def build_layout(spec, view, filter_extras=None, extra_rows=None):
    """The dashboard for one pathogen.

    `view` carries the display state the page has already computed: option lists, the stat
    numbers, the initial figures and the dataset's date bounds. `filter_extras` are extra
    columns for the basic filter row; `extra_rows` are extra rows placed after the modal.
    """
    ids = page_ids(spec)
    # Fresh "today" on each page load (not server boot day)
    window_end = today_in_dashboard_timezone()
    # Allow future GenBank collection dates if present in the data
    latest_selectable_date = max(window_end, view["max_date"])
    bar_title, area_title = chart_titles(spec["classification_column"])

    return dbc.Container(
        fluid=True,
        id=ids["body"],
        className="main-body content-container",
        children=[
            _header_row(spec, view, ids),
            _basic_filter_row(spec, view, ids, window_end, filter_extras),

            # Filtered rows (TSV) for the download button
            dcc.Store(id=ids["download_store"]),
            dcc.Store(id=ids["applied_selection"]),

            _advanced_modal(spec, view, ids, window_end, latest_selectable_date),
        ]
        + list(extra_rows or [])
        + [_map_row(view, ids)]
        + _chart_rows(view, ids, bar_title, area_title),
    )


# --- Callbacks -------------------------------------------------------------------------
#
# register_callbacks(spec, data) wires the five callbacks every pathogen page needs, plus
# the classification cascade for a pathogen that declares a second axis. It follows the
# shape of register_phylogeny_callbacks(app, prefix, store_id) in utils/phylo/panel.py:
# ids come from the spec, so registering two pathogens on one app cannot collide.
#
# `data` is the page's own state: the sequence frame, the geojson, the vocabulary callable
# and the script module that builds the map and bar frames.


def legend_order_for(spec, selected):
    """Curated order for the values currently selected, dropping the rest."""
    return [value for value in spec["classification_order"] if value in selected]


def _as_date_text(value):
    return value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value)[0:10]


def _resolve(spec, data, basic_widgets, advanced_widgets):
    return resolve_filter_selection(
        classify_filter_source(
            ctx.triggered_id,
            page_ids(spec)["basic_apply"],
            page_ids(spec)["advanced_apply"],
            (page_ids(spec)["basic_reset"], page_ids(spec)["reset_mobile"]),
        ),
        basic_widgets=basic_widgets,
        advanced_widgets=advanced_widgets,
        available=data["vocabulary"](),
    )


def _build_view(spec, data, selection):
    """Everything the main callback returns, from one resolved selection."""
    scripts = data["scripts"]
    classification_column = spec["classification_column"]
    subclassification_column = spec["subclassification_column"]

    selected_classifications = selection["classifications"]
    selected_continents = selection["continents"]

    filtered_df = apply_selection_fields(
        data["frame"], selection, classification_column=classification_column)

    # A single selected classification is not worth colouring by, so a pathogen with a
    # second axis switches the charts to it. Pathogens without one simply never switch.
    detail_mode = bool(subclassification_column) and len(selected_classifications) <= 1
    enable_icons = len(selected_classifications) > 1

    # The map keeps the primary axis and its palette even when the charts switch to the
    # second one, so it is not handed chart_column/chart_scheme below.
    map_df = scripts.build_df_to_map(
        filtered_df.copy(), data["geojson"], enable_icons,
        data_col=classification_column, color_scheme=spec["color_scheme"])
    filtered_map_df = filter_by_continents(map_df, selected_continents, data["geojson"])

    # Row-level version of the current picture, continent filter included. The stat cards
    # and the download both read it, so the numbers match the exported file.
    filtered_sequences = filter_by_continents(
        filtered_df, selected_continents, data["geojson"])
    download_content = filtered_sequences.to_csv(
        sep="\t", index=False, columns=spec["download_columns"])

    chart_column = subclassification_column if detail_mode else classification_column
    chart_values = (selection["subclassifications"] if detail_mode
                    else selected_classifications)
    chart_scheme = (spec["subclassification_color_scheme"] if detail_mode
                    else spec["color_scheme"])
    chart_order = None if detail_mode else legend_order_for(spec, selected_classifications)

    date_from_text = _as_date_text(selection["date_from"])
    date_to_text = _as_date_text(selection["date_to"])

    bar_plot_df = scripts.build_df_to_bar_plot(
        df=filtered_df, date_from=date_from_text, date_to=date_to_text,
        data_col=chart_column, category_order=chart_order)

    bar_figure = bar.build_bar_plot(
        df=bar_plot_df,
        color_scheme=chart_scheme,
        pathogen_title=chart_column,
        date_from=date_from_text,
        date_to=date_to_text,
        legend_order=chart_order,
        axis_df=filtered_df,
    )

    # The date window is passed explicitly so the axis span comes from the selection rather
    # than from the frame: a selection matching no sequence has no min/max to subtract.
    area_figure = plot_area_chat(
        df=filtered_df,
        data_col=chart_column,
        target_pathogens=chart_values,
        datetime_str_col="datetime",
        color_scheme=chart_scheme,
        date_from=date_from_text,
        date_to=date_to_text,
        legend_order=chart_order,
    )

    # The map always keeps the primary axis, even when the charts switch
    map_legend = map.build_info_section_with_legend(
        pathogens=selected_classifications, color_scheme=spec["color_scheme"])
    map_components = map.update_map(
        geo_df=filtered_map_df, color_scheme=spec["color_scheme"],
        enable_icons=enable_icons, info=map_legend)

    bar_title, area_title = chart_titles(chart_column)

    return (
        map_components,
        bar_figure,
        selected_classifications,
        selection["countries"],
        selected_continents,
        len(filtered_sequences),
        len(list(filtered_map_df['country'].unique())),
        selection["hosts"],
        len(list(filtered_sequences['host'].unique())),
        area_figure,
        bar_title,
        area_title,
        selected_classifications,
        selection["search_regions"],
        selection["date_from"].date(),
        selection["date_to"].date(),
        download_content,
        selection_to_dict(selection),
    )


def _main_outputs(ids):
    return [
        Output(ids["map"], "children"),
        Output(ids["bar_graph"], "figure"),
        Output(ids["classification_select"], "value"),
        Output(ids["countries_select"], "value"),
        Output(ids["continents_select"], "value"),
        Output(ids["n_sequences"], "children"),
        Output(ids["n_countries"], "children"),
        Output(ids["host_select"], "value"),
        Output(ids["n_hosts"], "children"),
        Output(ids["area_graph"], "figure"),
        Output(ids["bar_title"], "children"),
        Output(ids["area_title"], "children"),
        Output(ids["basic_classification"], "value"),
        Output(ids["basic_regions"], "value"),
        Output(ids["basic_start_date"], "date"),
        Output(ids["basic_end_date"], "date"),
        Output(ids["download_store"], "data"),
        Output(ids["applied_selection"], "data"),
    ]


def _main_inputs(ids):
    return [
        Input(ids["basic_apply"], "n_clicks"),
        Input(ids["advanced_apply"], "n_clicks"),
        Input(ids["basic_reset"], "n_clicks"),
        Input(ids["reset_mobile"], "n_clicks"),
    ]


def register_callbacks(spec, data):
    ids = page_ids(spec)

    @callback(
        [
            Output(ids["countries_block"], "style"),
            Output(ids["countries_select"], "value", allow_duplicate=True),
            Output(ids["continents_block"], "style"),
            Output(ids["continents_select"], "value", allow_duplicate=True),
            Output(ids["region_mode_marker"], "children"),
        ],
        [Input(ids["region_mode"], "value")],
        prevent_initial_call=True,
    )
    def show_countries_options(value):
        vocabulary = data["vocabulary"]()
        if value == "filtered-by-country":
            return ({"display": "block"}, [], {"display": "none"},
                    vocabulary["continents"], ["countries"])
        if value == "filtered-by-regions":
            return ({"display": "none"}, vocabulary["countries"], {"display": "block"},
                    [vocabulary["continents"][0]], ["continents"])
        return ({"display": "none"}, vocabulary["countries"], {"display": "none"},
                vocabulary["continents"], ["countries"])

    advanced_states = [
        State(ids["date_slider"], "value"),
        State(ids["classification_select"], "value"),
    ]
    if spec["subclassification_column"] is not None:
        advanced_states.append(State(ids["subclassification_select"], "value"))
    advanced_states += [
        State(ids["countries_select"], "value"),
        State(ids["continents_select"], "value"),
        State(ids["host_select"], "value"),
        State(ids["basic_start_date"], "date"),
        State(ids["basic_end_date"], "date"),
        State(ids["basic_classification"], "value"),
        State(ids["basic_regions"], "value"),
    ]

    running = [
        (Output(ids["basic_apply"], "disabled"), True, False),
        (Output(ids["basic_reset"], "disabled"), True, False),
        (Output(ids["reset_mobile"], "disabled"), True, False),
    ]

    def apply_filters(slider, classifications, subclassifications, countries, continents,
                      hosts, start_date, end_date, basic_classifications, regions):
        selection = _resolve(
            spec, data,
            basic_widgets={
                "classifications": basic_classifications,
                "search_regions": regions,
                "date_from": start_date,
                "date_to": end_date,
            },
            advanced_widgets={
                "classifications": classifications,
                "subclassifications": subclassifications,
                "countries": countries,
                "continents": continents,
                "hosts": hosts,
                "date_slider": slider,
            },
        )
        return _build_view(spec, data, selection)

    # Two thin wrappers rather than *args, so each signature says what it receives. Only a
    # pathogen with a second classification axis has that dropdown to read.
    if spec["subclassification_column"] is not None:
        @callback(_main_outputs(ids), _main_inputs(ids), advanced_states,
                  prevent_initial_call=True, running=running)
        def update_view(_basic, _advanced, _reset, _reset_mobile, slider, classifications,
                        subclassifications, countries, continents, hosts, start_date,
                        end_date, basic_classifications, regions):
            return apply_filters(slider, classifications, subclassifications, countries,
                                 continents, hosts, start_date, end_date,
                                 basic_classifications, regions)
    else:
        @callback(_main_outputs(ids), _main_inputs(ids), advanced_states,
                  prevent_initial_call=True, running=running)
        def update_view(_basic, _advanced, _reset, _reset_mobile, slider, classifications,
                        countries, continents, hosts, start_date, end_date,
                        basic_classifications, regions):
            return apply_filters(slider, classifications, None, countries, continents,
                                 hosts, start_date, end_date, basic_classifications,
                                 regions)

    handlers = {"main": update_view, "region_mode": show_countries_options}

    if spec["subclassification_column"] is not None:
        @callback(
            [Output(ids["subclassification_select"], "value")],
            [Input(ids["classification_select"], "value")],
        )
        def narrow_subclassifications(selected_classifications):
            return [spec["subclassification_from_classification"](
                selected_classifications, data["vocabulary"]()["subclassifications"])]

        handlers["cascade"] = narrow_subclassifications

    @callback(
        Output(ids["date_display"], "children"),
        [Input(ids["date_slider"], "value")],
    )
    def update_date_display(slider_value):
        if not slider_value:
            return ""
        start_value, end_value = sorted(slider_value)
        start_date = slider_value_to_date(start_value)
        end_date = slider_value_to_date(end_value)
        return (f"Selected range: {start_date.strftime('%Y-%m-%d')} "
                f"to {end_date.strftime('%Y-%m-%d')}")

    # Keep the typed advanced dates and the slider showing the same window
    @callback(
        [
            Output(ids["date_slider"], "value"),
            Output(ids["advanced_start_date"], "date"),
            Output(ids["advanced_end_date"], "date"),
        ],
        [
            Input(ids["date_slider"], "value"),
            Input(ids["advanced_start_date"], "date"),
            Input(ids["advanced_end_date"], "date"),
        ],
        prevent_initial_call=True,
    )
    def sync_advanced_date_controls(slider_value, start_date, end_date):
        if ctx.triggered_id == ids["date_slider"]:
            if not slider_value or len(slider_value) != 2:
                return no_update, no_update, no_update
            start_value, end_value = sorted(slider_value)
            return ([start_value, end_value],
                    slider_value_to_date(start_value).date(),
                    slider_value_to_date(end_value).date())

        if not start_date or not end_date:
            return no_update, no_update, no_update

        window_start = pd.to_datetime(start_date)
        window_end = pd.to_datetime(end_date)
        if window_start > window_end:
            window_start, window_end = window_end, window_start
        return ([date_to_slider_value(window_start), date_to_slider_value(window_end)],
                window_start.date(), window_end.date())

    @callback(
        Output(ids["advanced_modal"], "is_open"),
        [
            Input(ids["open_advanced"], "n_clicks"),
            Input(ids["open_advanced_mobile"], "n_clicks"),
            Input(ids["advanced_close"], "n_clicks"),
            Input(ids["advanced_apply"], "n_clicks"),
        ],
        [State(ids["advanced_modal"], "is_open")],
    )
    def toggle_modal(n_advanced, n_advanced_mobile, n_close, n_apply, is_open):
        if n_advanced or n_advanced_mobile or n_close or n_apply:
            return not is_open
        return is_open

    # Returned so a page keeps a handle on its own callbacks under the names it used before
    handlers.update({"date_display": update_date_display,
                     "date_sync": sync_advanced_date_controls,
                     "toggle_modal": toggle_modal})
    return handlers
