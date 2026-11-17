import dash
from dash import dcc, html, Input, Output, callback, State
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.express as px
from datetime import datetime, date

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP,"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"])

# Sample data for the map (you can replace this with your actual data)
countries_data = [
    {"country": "Brazil", "lat": -14.2350, "lon": -51.9253, "sequences": 8500},
    {"country": "Colombia", "lat": 4.5709, "lon": -74.2973, "sequences": 5200},
    {"country": "Mexico", "lat": 23.6345, "lon": -102.5528, "sequences": 4800},
    {"country": "Peru", "lat": -9.1900, "lon": -75.0152, "sequences": 3200},
    {"country": "Venezuela", "lat": 6.4238, "lon": -66.5897, "sequences": 2800},
    {"country": "Argentina", "lat": -38.4161, "lon": -63.6167, "sequences": 2400},
    {"country": "Ecuador", "lat": -1.8312, "lon": -78.1834, "sequences": 1900},
    {"country": "Thailand", "lat": 15.8700, "lon": 100.9925, "sequences": 1600},
    {"country": "India", "lat": 20.5937, "lon": 78.9629, "sequences": 1400},
    {"country": "Philippines", "lat": 12.8797, "lon": 121.7740, "sequences": 1200}
]

# Create map markers
map_markers = []
for country in countries_data:
    map_markers.append(
        dl.CircleMarker(
            center=[country["lat"], country["lon"]],
            radius=max(5, country["sequences"] / 500),  # Scale marker size by sequences
            children=[
                dl.Tooltip(f"{country['country']}: {country['sequences']} sequences")
            ],
            color="#dc3545",
            fill=True,
            fillOpacity=0.6
        )
    )

# Define the layout
app.layout = dbc.Container([
    # First horizontal container
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H2("Dengue", className="mb-0 fw-bold text-primary")
                        ]),
                        
                        dbc.Col([
                            html.Label("Select the pathogen:", className="form-label mb-1 small"),
                            dcc.Dropdown(
                                id="pathogen-dropdown",
                                options=[
                                    {"label": "Dengue", "value": "dengue"},
                                    {"label": "Chikungunya", "value": "chikungunya"},
                                    {"label": "Zika", "value": "zika"}
                                ],
                                value="dengue",
                                className="mb-0",
                                style={"fontSize": "14px"}
                            )
                        ]),
                        dbc.Col([
                            dbc.Button(
                                html.I(className="fas fa-download fa-lg"),
                                id="download-btn",
                                color="outline-primary",
                                className="flaot-start",
                                size="lg",
                                style={"height": "60px"}
                            ),
                            dbc.Tooltip("Download CSV file", target="download-btn")
                        ], width="auto"),
                    ], className="align-items-center justify-content-between")
                ])
            ], className="shadow-sm")
        ], width=5),
        
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.I(className="fas fa-dna fa-2x text-primary mb-2")
                                ], width=4),
                                dbc.Col([
                                    html.H4("33,713", className="mb-0 fw-bold"),
                                    html.P("Sequences selected", className="mb-0 small text-muted")
                                ], width=8)
                            ])
                        ])
                    ], className="h-100 shadow-sm")
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.I(className="fas fa-globe fa-2x text-success mb-2")
                                ], width=4),
                                dbc.Col([
                                    html.H4("91", className="mb-0 fw-bold"),
                                    html.P("Countries selected", className="mb-0 small text-muted")
                                ], width=8)
                            ])
                        ])
                    ], className="h-100 shadow-sm")
                ], width=6),
            ])
        ], width=7, className="d-flex align-items-center justify-content-end"),
        
    ], className="mb-4 align-items-center"),
    
    # Second container - Filters
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Select serotype:", className="form-label mb-1 small"),
                    dcc.Dropdown(
                        id="serotype-dropdown",
                        options=[
                            {"label": "DENV-1", "value": "denv1"},
                            {"label": "DENV-2", "value": "denv2"},
                            {"label": "DENV-3", "value": "denv3"},
                            {"label": "DENV-4", "value": "denv4"}
                        ],
                        multi=True,
                        placeholder="Select serotypes...",
                        style={"fontSize": "14px"}
                    )
                ], width=2),
                
                dbc.Col([
                    html.Label("Search by region:", className="form-label mb-1 small"),
                    dbc.Input(
                        id="names-input",
                        type="text",
                        placeholder="Enter names of countries or regions...",
                        size="sm"
                    )
                ], width=3),
                
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            dbc.InputGroup([
                                dbc.InputGroupText("Start date:", className="small m-0"),
                                dcc.DatePickerSingle(
                                    id="start-date",
                                    date=date(2020, 1, 1),
                                    display_format="YYYY-MM-DD",
                                    style={"fontSize": "14px"}
                                )
                            ], size="sm")
                        ], width="auto"),
                        dbc.Col([
                            dbc.InputGroup([
                                dbc.InputGroupText("End date:", className="small m-0"),
                                dcc.DatePickerSingle(
                                    id="end-date",
                                    date=date.today(),
                                    display_format="YYYY-MM-DD",
                                    style={"fontSize": "14px"}
                                )
                            ], size="sm")
                        ], width="auto")
                    ], className="g-1 align-items-center justify-content-center")
                ], width=3, className="d-flex align-items-center justify-content-start"),
                
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button(
                            "Apply filters",
                            id="apply-filter-btn",
                            color="outline-primary",
                            size="m",
                            className="mb-2 mt-2"
                        ),
                        dbc.Button(
                            "Advanced filters",
                            id="advanced-filters-btn",
                            color="outline-secondary",
                            size="m",
                            className="mb-2 mt-2"
                        ),
                        dbc.Button(
                            "Reset",
                            id="reset-btn",
                            color="outline-danger",
                            size="m",
                            className="mb-2 mt-2"
                        )
                    ],style={"width": "500px"})
                ], width=4, className="d-flex justify-content-end")
            ])
        ])
    ], className="mb-4 shadow-sm"),
    
    # Advanced filters modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Advanced Filters")),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Genome completeness:", className="form-label mb-1 small"),
                    dcc.RangeSlider(
                        id="completeness-slider",
                        min=0,
                        max=100,
                        step=5,
                        value=[80, 100],
                        marks={i: f"{i}%" for i in range(0, 101, 20)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], width=12, className="mb-3"),
                
                dbc.Col([
                    html.Label("Host:", className="form-label mb-1 small"),
                    dcc.Dropdown(
                        id="host-dropdown",
                        options=[
                            {"label": "Human", "value": "human"},
                            {"label": "Aedes aegypti", "value": "aedes_aegypti"},
                            {"label": "Aedes albopictus", "value": "aedes_albopictus"}
                        ],
                        multi=True,
                        placeholder="Select hosts...",
                        style={"fontSize": "14px"}
                    )
                ], width=6),
                
                dbc.Col([
                    html.Label("Collection method:", className="form-label mb-1 small"),
                    dcc.Dropdown(
                        id="collection-dropdown",
                        options=[
                            {"label": "Clinical sample", "value": "clinical"},
                            {"label": "Vector sample", "value": "vector"},
                            {"label": "Environmental", "value": "environmental"}
                        ],
                        multi=True,
                        placeholder="Select methods...",
                        style={"fontSize": "14px"}
                    )
                ], width=6)
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button("Apply Filters", id="apply-filters-btn", color="primary", size="sm"),
            dbc.Button("Close", id="close-modal-btn", color="secondary", size="sm")
        ])
    ], id="advanced-modal", is_open=False, size="lg"),
    
    # Map container
    dbc.Card([
        dbc.CardHeader([
            html.H5("Geographic Distribution", className="mb-0")
        ]),
        dbc.CardBody([
            dl.Map([
                dl.TileLayer(),
                *map_markers
            ], 
            style={'width': '100%', 'height': '500px'},
            center=[0, 0],
            zoom=2,
            id="world-map")
        ])
    ], className="shadow-sm")
    
], fluid=True, className="py-4")

# Callbacks
@app.callback(
    Output("advanced-modal", "is_open"),
    [Input("advanced-filters-btn", "n_clicks"), Input("close-modal-btn", "n_clicks")],
    [State("advanced-modal", "is_open")]
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@app.callback(
    [Output("pathogen-dropdown", "value"),
     Output("serotype-dropdown", "value"),
     Output("names-input", "value"),
     Output("start-date", "date"),
     Output("end-date", "date")],
    [Input("reset-btn", "n_clicks")]
)
def reset_filters(n_clicks):
    if n_clicks:
        return "dengue", [], "", date(2020, 1, 1), date.today()
    return dash.no_update

if __name__ == "__main__":
    print("[v0] Starting Dengue Dashboard...")
    print("[v0] Dashboard will be available at: http://localhost:8050")
    print("[v0] Make sure you have the required packages installed:")
    print("[v0] pip install dash dash-bootstrap-components dash-leaflet")
    app.run_server(debug=True, host='0.0.0.0', port=8050)
