from dash import callback, register_page

from graphs import bar, map
from graphs.area_plot import plot_area_chat
from pages.pathogen_dashboard import build_layout, legend_order_for, page_ids, register_callbacks
from pages.scripts import pathogen_script as page_scripts
from pathogens import get_pathogen
from utils.database.DashDatabaseClient import DashDatabaseClient
from utils.functions.date_functions import today_in_dashboard_timezone
from utils.phylo.job_workflow import (
    phylo_rows,
    phylo_toggle_column,
    register_phylo_job_callbacks,
)

SPEC = get_pathogen("chikv")

world_geojson = page_scripts.load_world_geojson()

dashDatabase = DashDatabaseClient()

last_updated_date = page_scripts.last_update_text(dashDatabase)

df_world_chikungunya = page_scripts.load_pathogen_frame(SPEC, dashDatabase)

page_scripts.write_dataset(SPEC, df_world_chikungunya)

VOCABULARY = page_scripts.derive_vocabulary(SPEC, df_world_chikungunya)

MIN_DF_DATE, MAX_DF_DATE = VOCABULARY["min_date"], VOCABULARY["max_date"]
ALL_GENOTYPES = VOCABULARY["classifications"]
ALL_COUNTRIES = VOCABULARY["countries"]
ALL_CONTINENTS_NAMES = VOCABULARY["continents"]
ALL_HOSTS = VOCABULARY["hosts"]
ALL_REGIONS = VOCABULARY["regions"]

BASIC_APPLY_ID = page_ids(SPEC)["basic_apply"]
RESET_IDS = (page_ids(SPEC)["basic_reset"], page_ids(SPEC)["reset_mobile"])


def chikungunya_filter_vocabulary():
    # Chikungunya has a single classification axis, so subclassifications stay wide open;
    # apply_selection_fields ignores them for a genotype-classified pathogen.
    return {
        "classifications": ALL_GENOTYPES,
        "subclassifications": ALL_GENOTYPES,
        "countries": ALL_COUNTRIES,
        "continents": ALL_CONTINENTS_NAMES,
        "hosts": ALL_HOSTS,
        "date_from": MIN_DF_DATE,
        "date_to": today_in_dashboard_timezone(),
    }


def page_data():
    return {
        "frame": df_world_chikungunya,
        "geojson": world_geojson,
        "vocabulary": chikungunya_filter_vocabulary,
        "scripts": page_scripts,
    }


# Initial, unfiltered picture shown before the first Apply
map_df = page_scripts.build_df_to_map(
    df_world_chikungunya, world_geojson,
    data_col=SPEC["classification_column"], color_scheme=SPEC["color_scheme"])

map_legend = map.build_info_section_with_legend(
    pathogens=ALL_GENOTYPES, color_scheme=SPEC["color_scheme"])

map_components = map.update_map(
    geo_df=map_df, color_scheme=SPEC["color_scheme"], enable_icons=True, info=map_legend)

bar_plot_df = page_scripts.build_df_to_bar_plot(
    df=df_world_chikungunya, date_from=MIN_DF_DATE, date_to=MAX_DF_DATE,
    data_col=SPEC["classification_column"],
    category_order=legend_order_for(SPEC, ALL_GENOTYPES))

bar_plot = bar.build_bar_plot(
    df=bar_plot_df,
    color_scheme=SPEC["color_scheme"],
    pathogen_title=SPEC["classification_column"],
    legend_order=legend_order_for(SPEC, ALL_GENOTYPES),
    axis_df=df_world_chikungunya,
)

area_chart = plot_area_chat(
    df=df_world_chikungunya,
    data_col=SPEC["classification_column"],
    target_pathogens=ALL_GENOTYPES,
    datetime_str_col="datetime",
    color_scheme=SPEC["color_scheme"],
    fig_title=None,
    legend_order=legend_order_for(SPEC, ALL_GENOTYPES),
)


def page_view():
    return {
        "last_updated_date": last_updated_date,
        "n_sequences": len(df_world_chikungunya),
        "n_countries": len(list(map_df['country'].unique())),
        "n_hosts": len(ALL_HOSTS),
        "classifications": ALL_GENOTYPES,
        "subclassifications": [],
        "countries": ALL_COUNTRIES,
        "continents": ALL_CONTINENTS_NAMES,
        "hosts": ALL_HOSTS,
        "regions": ALL_REGIONS,
        "min_date": MIN_DF_DATE,
        "max_date": MAX_DF_DATE,
        "map_components": map_components,
        "bar_figure": bar_plot,
        "area_figure": area_chart,
    }


# --- Phylogeny -------------------------------------------------------------------------
# Mounted through the core's two insertion points. The workflow itself is pathogen-agnostic
# (utils/phylo/job_workflow.py); this page only says where it goes and hands it the data.

def phylo_data():
    page = page_data()
    page["database"] = dashDatabase
    page["applied_selection_id"] = page_ids(SPEC)["applied_selection"]
    return page


register_page(__name__, path=SPEC["route"])


def layout(**kwargs):
    return build_layout(
        SPEC,
        page_view(),
        filter_extras=[phylo_toggle_column(SPEC)],
        extra_rows=phylo_rows(SPEC),
    )


_handlers = register_callbacks(SPEC, page_data())

# The page's main callback, under the name it has always had here
update_map = _handlers["main"]

_phylo = register_phylo_job_callbacks(SPEC, phylo_data(), callback)
