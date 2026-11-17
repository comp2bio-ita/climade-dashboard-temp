# import kaleido
# from base64 import b64encode
import json

from dash import html
from dash_extensions.javascript import assign
import dash_leaflet as dl
import dash_leaflet.express as dlx
import pandas as pd
import plotly.express as px

from utils.base_maps import CartoPositron, CartoVoyager, CartoDarkMatter
from utils.functions.geo_functions import df_to_geojson, geojson_geometry_property, geojson_id_property
from utils.color_schemes import heatmap_color

# Colorpleth map and custom icons documentation using Dash Leaflet
# https://www.dash-leaflet.com/docs/geojson_tutorial


def get_color_configs() -> dict[list[int], list[str]]:
    return dict(
        classes=heatmap_color['classes'],
        colorscale=heatmap_color['colorscale'],
    )


def build_colorbar(classes: list[int], colorscale: list[str]):
    ctg = [
        "{}+".format(cls, classes[i + 1])
        for i, cls in enumerate(classes[:-1])] + ["{}+".format(classes[-1])
    ]
    colorbar = dlx.categorical_colorbar(categories=ctg, colorscale=colorscale, width=300, height=30, position="bottomleft")
    return colorbar


def build_geojson(geojson: dict, enable_icons: bool = False, classes: list[int] = None, colorscale: list[str] = None, colorprop: str = None, icon_size: int = 30):

    style = dict(weight=2, opacity=1, color='white',
                 dashArray='3', fillOpacity=0.7)

    # Javascrip function to perform the color control on the GeoJSON map
    style_handle = assign("""
        function(feature, context){
            const {classes, colorscale, style, colorProp} = context.hideout;  // get props from hideout
            const value = feature.properties[colorProp]  // get value the determines the color
            for (let i = 0; i < classes.length; ++i) {
                if (value > classes[i]) {
                    style.fillColor = colorscale[i];  // set the fill color according to the class
                }
            }
            return style;
        }
    """)

    draw_icons = assign("""
        function(feature, latlng, context){
            const extendexDivIcon = L.DivIcon.extend({
                createIcon: function(oldIcon) {
                    let icon = L.DivIcon.prototype.createIcon.call(this, oldIcon);
                    icon.style.backgroundColor = this.options.color;
                    icon.style.border = this.options.border;
                    return icon;
                }     
            })
                        
            const { icon_size } = context.hideout

            const icon_item = new extendexDivIcon({
                html: feature.properties.icon,
                iconSize: [icon_size, icon_size],
                color: "transparent",
                border: "none"
            });

            return L.marker(latlng, {icon: icon_item, riseOnHover: true, riseOffset: 250});
        }"""
    )

    colorpleth = None

    if enable_icons:
        colorpleth = dl.GeoJSON(
            data=geojson,  # geojson dataset with dengue data
            pointToLayer=draw_icons,
            zoomToBounds=True,
            hideout=dict(icon_size=icon_size),
            id="geojson_map_icon"
        )
    else:
        colorpleth = dl.GeoJSON(
            data=geojson,  # geojson dataset with dengue data
            # pointToLayer=draw_icons,
            style=style_handle,  # how to style each polygon
            zoomToBounds=True,
            zoomToBoundsOnClick=True,
            hideout=dict(
                colorscale=colorscale, 
                classes=classes,
                style=style, 
                colorProp=colorprop
            ),  
            id="geojson_map_heatmap"
        )

    return colorpleth


def build_info_section_with_legend(pathogens: list[str], color_scheme: dict):

    legend = generate_legend_html(
        pathogens=pathogens, color_scheme=color_scheme
    )

    info = html.Div(
        children=[
            html.Strong("Detected genomes per country"),
            html.Br(),
            html.Br(),
            *legend
        ],
        id="info",
        className="info",
        style={"position": "absolute", "top": "10px","right": "2%", "zIndex": "1000"}
    )

    return info


def build_info_section():
    info = html.Div(
        # children=get_hover_info(),
        children=[
            html.Strong("Detected genomes per country"),
            
        ],
        id="info",
        className="info",
        style={"position": "absolute", "top": "10px",
               "right": "2%", "zIndex": "1000"}
    )

    return info

# Legacy function with plotly
# def build_icon(row:tuple, labels: list, color_scheme: dict, size: float = 30):
#     slices = [round(row[label]*100/row['total'], 2) for label in labels]
#     colors = labels
#     fig = px.pie(
#         values=slices,
#         color=colors,
#         color_discrete_map=color_scheme,
#         hole=.4,
#         width=size,
#         height=size
#     )  # names=dengue_labels
#     fig.update_traces(
#         textinfo='none',
#         marker=dict(line=dict(color='white', width=0.7))
#     )
#     fig.update_layout(
#         plot_bgcolor='rgba(0,0,0,0)',
#         paper_bgcolor='rgba(0,0,0,0)',
#         margin=dict(t=1, b=1, l=1, r=1)
#     )
#     svg = fig.to_image(format="svg", engine="kaleido")
#     icon = str(svg.decode("utf-8"))  # attempt one

#     return icon


# Updated function with matplotlib
def build_icon(row: dict, labels: list, color_scheme: dict, size: float = 30):
    import matplotlib.pyplot as plt
    import io

    slices = [round(row[label]*100/row['total'], 2) for label in labels]
    
    # Extract colors in the exact order of the labels
    colors = [color_scheme.get(label, '#000000') for label in labels]
    
    # Matplotlib uses inches, so convert pixels to inches (assuming standard 100 dpi)
    size_inches = size / 100.0
    
    # Create figure with transparent background
    fig, ax = plt.subplots(figsize=(size_inches, size_inches), dpi=100)
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    
    # Build donut chart
    # Matplotlib uses 'width' as the fraction of the radius, so 1.0 - 0.4 = 0.6
    ax.pie(
        slices, 
        colors=colors, 
        wedgeprops=dict(width=0.6, edgecolor='white', linewidth=0.7)
    )
    
    # Ensure perfect circle and remove all margins
    ax.axis('equal')
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1)
    
    # Export to SVG string in memory
    buffer = io.BytesIO()
    plt.savefig(
        buffer, 
        format="svg", 
        transparent=True, 
        bbox_inches='tight', 
        pad_inches=0
    )
    
    # Free memory instantly (crucial for web servers like Flask/Dash)
    plt.close(fig)  
    
    return buffer.getvalue().decode('utf-8')

# Update function with pygal
# def build_icon(row: dict, labels: list, color_scheme: dict, size: float = 30):
#     import pygal
#     from pygal.style import Style

#     slices = [round(row[label]*100/row['total'], 2) for label in labels]
    
#     # Extract colors in the exact order of the labels
#     colors = tuple(color_scheme.get(label, '#000000') for label in labels)
    
#     # Define custom style for colors and transparent background
#     custom_style = Style(
#         colors=colors,
#         background='transparent',
#         plot_background='transparent'
#     )
    
#     # Initialize the Donut chart
#     pie = pygal.Pie(
#         inner_radius=0.4, 
#         width=int(size),
#         height=int(size),
#         show_legend=False, 
#         print_values=False,
#         margin=1,
#         style=custom_style
#     )
    
#     # Add data slices (passing an empty string for the label since you had textinfo='none')
#     for value in slices:
#         pie.add('', value)
        
#     # Render directly to an SVG string and decode
#     svg_bytes = pie.render()
#     return svg_bytes.decode('utf-8')

def generate_legend_html(pathogens: list[str], color_scheme: dict) -> str:
    legend = [
        html.Div([
            html.Span(
                style={"marginRight": "3%"},
                children=[
                    html.A("◼", style={"color": f"{color_scheme[pathogen]}", "fontSize": "140%", "marginRight": "1%"}),
                    pathogen,
                ]
            ),
            html.Br()
        ]) for pathogen in pathogens
    ]
    return legend

def generate_legend_info(pathogens: list[str], color_scheme: dict) -> str:
    legend = [
        "<br>\n".join([
            f"""<a style="color:{color_scheme[pathogen]};font-size:120%;margin-left:2%;">◼</a> {pathogen}""" for pathogen in pathogens
        ])
    ]
    return legend


def update_map(geo_df: pd.DataFrame, color_scheme: dict, enable_icons: bool = True, icon_size: int = 30, info:html.Div = html.Div()):

    # dict_df = geo_df.to_dict("records")

    # generating geojson for the colorpleth

    columns_of_interest = list(set(geo_df.columns.to_list(
    )) - set([geojson_geometry_property, geojson_id_property]))

    heatmap_geojson = df_to_geojson(
        df=geo_df,
        column_to_props=columns_of_interest,
        geometry_column=geojson_geometry_property,
        id_column='id'
    )

    # building the map

    color_configs = get_color_configs()

    colorbar = build_colorbar(
        classes=color_configs["classes"], colorscale=color_configs["colorscale"])

    colorpleth = build_geojson(
        geojson=heatmap_geojson,
        classes=color_configs["classes"],
        colorscale=color_configs["colorscale"],
        colorprop="total"
    )

    # Layer management
    colorpleth_layer_children = [
        colorpleth,
        colorbar
    ]

    icon_layer_children = []

    if enable_icons:
        # generationg geojson for the pie icons
        pie_geo_df = geo_df.drop(columns="geometry")

        pie_geo_df["geometry"] = pie_geo_df.apply(
            lambda row: json.dumps(
                dict(
                    type='Point',
                    coordinates=[row['label_x'],row['label_y']],
                )
            ), 
            axis=1
        )

        pie_geojson = df_to_geojson(
            df=pie_geo_df,
            column_to_props=columns_of_interest,
            geometry_column=geojson_geometry_property,
            id_column='id'
        )

        pie_map = build_geojson(
            geojson=pie_geojson,
            enable_icons=enable_icons,
            icon_size=30
        )

        icon_layer_children = [
            pie_map
        ]

    # time.sleep(1)

    layers = [
        dl.BaseLayer(
        name="Base Map",
        checked=True,
        children=[
            dl.TileLayer(**CartoVoyager)
        ])
    ]

    if colorpleth_layer_children:
        layers.append(
            dl.Overlay(name="Number of Genomes", checked=True, children=[
                dl.LayerGroup(colorpleth_layer_children),
            ])
        )

    if enable_icons and icon_layer_children:
        layers.append(
            dl.Overlay(name="Proportional Serotype", checked=True, children=[
                dl.LayerGroup(icon_layer_children)
            ])
        )


    # Generating layers
    map_layers = dl.LayersControl(
        position="bottomright",
        children=layers, 
        id="lc"
    )

    # Generating Map
    return [
        map_layers,
        info,
    ]
    