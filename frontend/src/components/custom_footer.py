from dash import html
import dash_bootstrap_components as dbc
from components import logo

def load():
    return html.Footer(
        className="custom-footer",
        children=[
            dbc.Container(
                className="footer-container",
                children=[
                    dbc.Row(
                        children=[
                            dbc.Col(
                                children=[
                                    dbc.Col(
                                        children=[html.P("Developed using:")],
                                    ),
                                    dbc.Col(
                                        children=[
                                            html.A(
                                                href="https://pathotrack.health/",
                                                target="_blank",  # Opens in a new tab
                                                children=[
                                                    logo.load(
                                                        id="genomic-dash-logo",
                                                        src="images/pathotrack_logo.png",
                                                        height=60
                                                    )
                                                ]
                                            )
                                        ],
                                    ),
                                    dbc.Col(
                                        children=[
                                            html.P(
                                                "Data from ",
                                                style={"display": "inline"},
                                            ),
                                            html.A(
                                                href="https://www.ncbi.nlm.nih.gov/",
                                                children=["NCBI"],
                                                target="_blank",
                                                style={"font-size":"16px","text-decoration":"none","color":"#888"}
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            dbc.Col(
                                children=[
                                    dbc.Col(
                                        children=[html.P("Powered by:")],
                                    ),
                                    dbc.Col(
                                        children=[
                                            logo.load(id="cloud-logo", 
                                                src="images/google-cloud.png", height=35
                                            )
                                        ],
                                    ),
                                ],
                            ),
                            dbc.Col(
                                children=[
                                    dbc.Row(
                                        children=[
                                            dbc.Col(
                                                children=[
                                                    html.P(
                                                        "Participating institutions and labs:"
                                                    )
                                                ],
                                            ),
                                            html.Div(
                                                className="logos-oficiais",
                                                style={
                                                    "display": "flex",
                                                    "justify-content": "flex-start",
                                                    "align-items": "center",
                                                    "gap": "20px",
                                                    "width": "100%",
                                                    "margin-bottom":"50px"
                                                },
                                                children=[
                                                    html.Div(
                                                        children=[
                                                            logo.load(id="sun-logo", 
                                                                src="images/sun_logo.png", height=50
                                                            )
                                                        ],
                                                    ),
                                                    html.Div(
                                                        children=[
                                                            logo.load(id="ceri-logo", 
                                                                src="images/ceri_logo.png", height=50
                                                            )
                                                        ],
                                                    ),
                                                    html.Div(
                                                        children=[
                                                            logo.load(id="ufmg-logo", 
                                                                src="images/ufmg_logo.png", height=50
                                                            )
                                                        ],
                                                    ),
                                                    html.Div(
                                                        children=[
                                                            logo.load(id="ita-logo", 
                                                                src="images/ita_logo.png", height=50
                                                            )
                                                        ],
                                                    ),
                                                ],
                                            ),

                                        ]
                                    )
                                ],
                            ),
                        ],
                    ),
                    dbc.Row(
                        style={
                            "display": "flex",
                            "text-align": "center",
                            "align-itens":"center",
                        },
                        children=[
                            
                            dbc.Col(
                                children=[
                                    
                                    html.P(
                                        "Best viewed using ",
                                        style={"display": "inline","font-size":"12px"},
                                    ),
                                    html.A(
                                        href="https://www.google.com/chrome/",
                                        children=["Chrome"],
                                        target="_blank",
                                        style={"display": "inline","text-decoration":"none","color":"black","font-size":"12px"},
                                    ),
                                    html.P(
                                        " on 1280x960 resolution and above.",
                                        style={"display": "inline","font-size":"12px"},
                                    ),
                                ],
                            ),
                            dbc.Col(
                                children=[
                                    html.H6("This website is free and open to all users and there is no login requirement.",
                                            style={'text-aligm':'end','color': '#909090', "font-size":"12px"}, className="text-secondary m-0"
                                    ), 
                                ],
                                className="col-md-6"
                            )
                        ]
                    )
                ]
            ),            
        ],
    )