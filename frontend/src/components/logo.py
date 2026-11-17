from dash import html, get_asset_url

def load(id: str, src: str, width: int = None , height: int = None):
    return html.Img(
        id=id,
        src=get_asset_url(src),
        width=width,
        height=height,
    )