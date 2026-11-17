import dash
from dash import dcc, html, callback
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from pathogens import PATHOGENS, pathogen_by_title

from . import download_btn
# Color schemes are now handled by CSS classes in dashboard-colors.css

def load(select_pathogen_value):
    # Color schemes are now handled by CSS classes in dashboard-colors.css

    spec = pathogen_by_title(select_pathogen_value)
    virus_key = spec["id_suffix"] if spec else None
    download_button = download_btn.load(virus_key) if virus_key else html.Div()

    # Layout for the header
    header = html.Div(
        children=[
            dcc.Location(id='n-url-2', refresh=True),  # To update the URL
            
            dbc.Row([
                # Title
                dbc.Col([
                    html.H2(
                        select_pathogen_value,
                        className="mb-0 fw-bold text-primary dashboard-h2",
                        id="title-header",
                        style={"marginRight": "2rem"}
                    )
                ], md=6, lg=4 ,class_name="my-2"),
                
                # Dropdown
                dbc.Col([
                    html.Label("Select the pathogen:", className="form-label mb-1 small dashboard-pathogen-label"),
                    dcc.Dropdown(
                        id="source-dropdown",
                        options=[{"label": registered["title"], "value": registered["title"]}
                                 for registered in PATHOGENS.values()],
                        value=select_pathogen_value,
                        className="mb-0 dashboard-select-serotype w-90 mt-lx-4",
                        style={"fontSize": "14px"}
                    )
                ], md=6, lg=6, class_name="my-2 justify-content-between"),
                
                # Download btn
                dbc.Col([
                    download_button,
                    dbc.Tooltip("Download CSV file", target=f"{virus_key}_btn")
                ], md=12, xl=2, class_name="my-2"),
            ], className="align-items-center justify-content-between"),
        ]
    )
    return header



# Callback to update the URL based on the dropdown selection
@callback(
    Output('n-url-2', 'href'),
    Input('source-dropdown', 'value'),
    prevent_initial_call=True
)
def update_url(selected_source):
    spec = pathogen_by_title(selected_source)
    return spec["route"] if spec else dash.no_update
