from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
from datetime import datetime
import pandas as pd

# Per-virus wiring for the download button. Ids must match each page's layout and its
# download Store; full_dataset_path points to the TSV each page rewrites from the database
# at startup (the fallback used when no filter has been applied yet).
DOWNLOAD_CONFIG = {
    "denv": {
        "btn_id": "denv_btn",
        "download_id": "denv_download-text",
        "store_id": "denv-download-store",
        "full_dataset_path": "data/dengue/Final_global_dengue.tsv",
        "filename_prefix": "dengue_dataset",
    },
    "chikv": {
        "btn_id": "chikv_btn",
        "download_id": "chikv_download-text",
        "store_id": "chikv-download-store",
        "full_dataset_path": "data/chikungunya/Final_global_chikv.tsv",
        "filename_prefix": "chik_dataset",
    },
    "zikv": {
        "btn_id": "zikv_btn",
        "download_id": "zikv_download-text",
        "store_id": "zikv-download-store",
        "full_dataset_path": "data/zika/Final_global_zika.tsv",
        "filename_prefix": "zika_dataset",
    },
    "yfv": {
        "btn_id": "yfv_btn",
        "download_id": "yfv_download-text",
        "store_id": "yfv-download-store",
        "full_dataset_path": "data/yellow_fever/Final_global_yfv.tsv",
        "filename_prefix": "yfv_dataset",
    },
}


def load(virus, size=25):
    config = DOWNLOAD_CONFIG[virus]
    return html.Span(
        children=[
            dbc.Button(
                id=config["btn_id"],
                color="outline-primary",
                className="w-100 d-flex align-items-center justify-content-center custom-btn ",
                size="m",
                style={"height": "60px"},
                children=[
                    html.I(className="fas fa-download fa-lg"),
                    html.Span("Download data", className="d-block d-lg-none ml-3")
                ]
            ),
            dcc.Download(id=config["download_id"]),
        ]
    )


def register_download_callback(virus):
    config = DOWNLOAD_CONFIG[virus]

    @callback(
        Output(config["download_id"], "data"),
        Input(config["btn_id"], "n_clicks"),
        State(config["store_id"], "data"),
        prevent_initial_call=True
    )
    def download_click(btn_click, filtered_content):
        date = datetime.now().strftime("%Y_%m_%d")
        filename = f"{config['filename_prefix']}_{date}.tsv"
        # A filter is active -> download exactly what the map and charts show
        if filtered_content:
            return dict(content=filtered_content, filename=filename)
        # No filter applied yet -> download the entire dataset
        full_dataset = pd.read_csv(config["full_dataset_path"], sep="\t")
        return dcc.send_data_frame(
            full_dataset.to_csv,
            filename=filename,
            sep="\t",
            index=False
        )


# Register one callback per virus, once, at import time
for virus_name in DOWNLOAD_CONFIG:
    register_download_callback(virus_name)
