from dash import dcc, html, Dash, page_container
import dash_bootstrap_components as dbc
from dotenv import load_dotenv
from flask import Flask, redirect
import os

from dash.dependencies import Input, Output

from components import custom_footer, navigation

load_dotenv()

APP_PORT = os.getenv('APP_PORT')

# FONT_AWESOME = "https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css"
# dbc.themes.CYBORG

FONT_AWESOME = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"

external_stylesheets = [dbc.themes.BOOTSTRAP, FONT_AWESOME]

server = Flask(__name__)

@server.route('/')
def index_redirect():
    return redirect('/dengue')

app = Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    title="Climade Dashboard",
    assets_folder="../assets",
    use_pages=True,
    server=server
)

app.config.suppress_callback_exceptions = True

server = app.server

app.layout = dcc.Loading(
    type="circle",
    fullscreen=True,
    children=[
        html.Div(
            style={"height": "100vh"},
            children=[
                # dcc.Location(id="url", refresh=False),
                html.Div(
                    [navigation.load(app)]
                ),
                dbc.Container(
                    fluid=True,
                    id="body-container",
                    className="main-body",
                    children=[
                        html.Div(
                            className="layout-container",
                            id='page-content',
                            children=[
                                page_container
                            ]
                        ),
                        custom_footer.load(),
                    ],
                ),
                dcc.Store(id='url-store')
            ]
        )
    ]
)

@app.callback(
    Output('header-container', 'style'),
    Input('url', 'href')
)
def hide_header_on_about(href):
    if href and '/about' in href:
        return {'display': 'none'}
    else:
        return {'display': 'block'}

if __name__ == "__main__":
    app.run_server(
        host="0.0.0.0",
        debug=False, 
        dev_tools_ui=False, 
        dev_tools_props_check=False, 
        port=int(APP_PORT) if APP_PORT else 8080
    )
