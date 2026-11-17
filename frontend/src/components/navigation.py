import dash_bootstrap_components as dbc
from dash import html

def load(app):
    navbar = dbc.Navbar(
        color="#336eb0",
        dark=True,
        style={ "display":"block",
               "align-items":"center",
                "height":"75px",
        },
        children=[
            dbc.Container(
                className="navigation-container",
                style={
                    "height":"100%",
                    "display":"flex",
                    "justify-content":"space-between",
                    "align-items":"center",
                },
                children=[
                    html.A(
                        href="/dengue",
                        style={
                            "display":"flex",
                            "align-items":"center",
                            "text-decoration":"none",
                            "margin":"0",
                            "padding":"0"
                        },
                        children=[
                            html.Img(src=app.get_asset_url('images/climade_dash_logo.png'),
                            style={
                                "height":"40px",
                                "width":"auto",
                                "margin-right":"10px",
                                "margin":"0 10px 0 0"
                            }),
                            dbc.NavbarBrand(
                                "Dashboard",
                                style={"margin":"0", "padding":"0"}
                            )
                        ]
                    ),
                    dbc.Nav(
                        style={
                            "display":"flex",
                            "justify-content":"space-evenly",
                            "margin":"0",
                            "padding":"0"
                        },
                        children=[
                            dbc.NavItem(
                                className="navitem",
                                children=[
                                    dbc.NavLink("ABOUT", href="/about",
                                    className="navlink")
                                ]
                            )
                        ],
                        navbar=True
                    ),
                ],
                fluid=True
            ),
        ]
    )
    return navbar