import plotly.express as px

dengue_color_scheme = {
    'DENV1': '#6f54a5',
    'DENV2': '#307877',
    'DENV3': '#872646',
    'DENV4': '#ff9000',
    'Unassigned': '#808080',
    'Unclassified': '#334000'
}

# dengue_color_scheme_genotypes = {
#     "1I": "#6f54a5", "1II": "#9275c2", "1III": "#543b85", "1IV": "#b39ade", "1V": "#422c70",
#     "1VI": "#c8b3eb", "1VII": "#7d60b0", "1VIII": "#361f5d", "1IX": "#e0cdf7", "1X": "#9e89cc",

#     "2I": "#307877", "2II": "#4e9b9a", "2III": "#1e5756", "2IV": "#6cbebd", "2V": "#144240",
#     "2VI": "#8fd9d7", "2VII": "#3a8684", "2VIII": "#0a2e2d", "2IX": "#b3f2f0", "2X": "#529c9b",

#     "3I": "#872646", "3II": "#a53d5d", "3III": "#5f1a32", "3IV": "#c1657f", "3V": "#471223",
#     "3VI": "#da8b9f", "3VII": "#932d4f", "3VIII": "#2e0c17", "3IX": "#f4b7c3", "3X": "#b44a6a",

#     "4I": "#ff9000", "4II": "#ffac33", "4III": "#cc7300", "4IV": "#ffd480", "4V": "#a65f00",
#     "4VI": "#ffe5b3", "4VII": "#d97f00", "4VIII": "#804400", "4IX": "#fff2d9", "4X": "#e69500"
# }

dengue_color_scheme_genotypes = {
    # Dengue 1 (Genotypes I to VII)
    "1I": "#6f54a5",  # Main color for Dengue 1 (Purple)
    "1II": "#9370DB",  # Medium Purple
    "1III": "#17186D",  # Royal Blue
    "1IV": "#87CEEB",  # Sky Blue
    "1V": "#FF69B4",  # Hot Pink
    "1VI": "#C71585",  # Medium Violet Red
    "1VII": "#808080",  # Gray

    # Dengue 2 (Genotypes I to VI)
    "2I": "#307877",  # Main color for Dengue 2 (Teal)
    "2II": "#02B9F8",  # Light Sea Green
    "2III": "#2E8B57",  # Sea Green
    "2IV": "#66CDAA",  # Medium Aquamarine
    "2V": "#4682B4",  # Steel Blue
    "2VI": "#778899",  # Light Slate Gray

    # Dengue 3 (Genotypes I to V)
    "3I": "#872646",  # Main color for Dengue 3 (Dark Red)
    "3II": "#DC143C",  # Crimson
    "3III": "#F89144",  # Orange
    "3IV": "#FF1493",  # Deep Pink
    "3V": "#800080",  # Purple

    # Dengue 4 (Genotypes I to V)
    "4I": "#ff9000",  # Main color for Dengue 4 (Yellow)
    "4II": "#DAA520",  # Golden Rod
    "4III": "#54682E",  # Dark Golden Rod
    "4IV": "#8B4513",  # Saddle Brown
    "4V": "#CD853F",  # Peru
}

zika_color_scheme = {
    'African': '#ff9000',
    'Asian': '#307877',
    'Unassigned': '#808080',
    'Unclassified': '#334000'
}

chikungunya_color_scheme = {
    'ECSA': '#307877',
    'ACL': '#ff9000',
    'WA': '#872646',
    'Unassigned': '#808080',
    'Unclassified': '#334000'
}

yellow_fever_color_scheme = {
    'Angola': '#872646',
    'East Africa': '#ff9000',
    'East/Central Africa': '#DAA520',
    'West Africa I': '#6f54a5',
    'West Africa II': '#9370DB',
    'South America I': '#307877',
    'South America II': '#66CDAA',
    'Unassigned': '#808080',
    'Unclassified': '#334000'
}

# the number of colors in the colorscale list must be equal the number of classes in the classes list
heatmap_color = {
    'colorscale': ['#BFD3E7', '#99B9D9', '#729ECA', '#4C84BB', '#266AAD', '#00509E'],
    'classes': [1, 200, 600, 1200, 2400, 4800]
}

# Phylogenetic tip coloring. Serotype and genotype reuse the curated dashboard schemes; any
# other categorical field (country, host, lineage) gets colors generated from a qualitative
# palette. Dark24 + Light24 give 48 distinct hues before the palette wraps around.
UNKNOWN_CATEGORY_COLOR = "#808080"
_CATEGORICAL_PALETTE = px.colors.qualitative.Dark24 + px.colors.qualitative.Light24


def color_for_classification(label, color_scheme):
    return color_scheme.get(label, UNKNOWN_CATEGORY_COLOR)


def color_discrete_map_for_labels(labels, color_scheme):
    return {str(label): color_for_classification(label, color_scheme) for label in labels}

# Curated schemes per pathogen and field. "genotype" means different values for each
# pathogen, so it cannot be a single global entry: a chikungunya tree coloured by genotype
# would otherwise be handed dengue's 1I/2II/... map and render every tip as unknown.
# Registering another arbovirus means adding its key here, nothing else.
PHYLO_FIELD_COLOR_SCHEMES = {
    "denv": {
        "serotype": dengue_color_scheme,
        "genotype": dengue_color_scheme_genotypes,
    },
    "chikv": {
        "genotype": chikungunya_color_scheme,
    },
    "zikv": {
        "genotype": zika_color_scheme,
    },
    "yfv": {
        "genotype": yellow_fever_color_scheme,
    },
}


def categorical_color_map(values):
    """Stable value-to-color mapping from the qualitative palette (sorted for determinism)."""
    distinct_values = sorted({str(value) for value in values if value is not None})
    color_map = {}
    for index, value in enumerate(distinct_values):
        color_map[value] = _CATEGORICAL_PALETTE[index % len(_CATEGORICAL_PALETTE)]
    return color_map


def color_map_for_pathogen_field(pathogen, field, values):
    """
    Color map for a tip-metadata field: the curated scheme when this pathogen defines one for
    the field, otherwise a generated categorical map. Returned keys are strings; callers fall
    back to UNKNOWN_CATEGORY_COLOR for values missing from a fixed scheme.
    """
    curated = PHYLO_FIELD_COLOR_SCHEMES.get(pathogen, {})
    if field in curated:
        return dict(curated[field])
    return categorical_color_map(values)



# Note: UI color schemes have been moved to assets/dashboard-colors.css
# This file now only contains graph-related color schemes and utility functions

# Standardized chart theme configuration

def get_chart_theme(legend_title: str) -> dict:
    """
    Returns standardized theme configuration for all charts to ensure consistency.

    `legend_title` names the axis the chart is currently coloured by. It is required rather
    than defaulted: it used to be the constant "Serotype", which titled the chikungunya and
    zika legends — and dengue's own genotype view — with the wrong word.

    Returns:
        dict: Theme configuration dictionary
    """
    return {
        'paper_bgcolor': '#fff',
        'plot_bgcolor': '#fff',
        'font_color': '#222',
        'font_family': 'Arial, sans-serif',
        'font_size': 12,
        'title_font_size': 16,
        'margin': dict(l=60, r=40, t=60, b=100),  # Reduced top margin, increased bottom for legend
        'legend': dict(
            orientation='h',
            yanchor='top',
            y=-0.15,  # Position below the plot
            xanchor='left',
            x=0,  # Position at left edge
            font=dict(size=11),
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor='#ddd',
            borderwidth=1,
            title=dict(
                text=legend_title,
                font=dict(size=12, color='#2c3e50')
            )
        ),
        'xaxis': dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='#ddd',
            tickfont=dict(size=10),
            title_font=dict(size=12),
            ticklen=5,  # Length of tick marks
            tickcolor='#333',
            ticks='outside',  # Position ticks outside the plot area
            tickwidth=1,
            showline=True,  # Show the axis line
            linewidth=1,
            linecolor='#ddd',
            mirror=True,  # Mirror the axis line
            ticklabelstandoff=5  # Add 5px spacing between tick labels and axis
        ),
        'yaxis': dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='#ddd',
            tickfont=dict(size=10),
            title_font=dict(size=12),
            ticklen=5,  # Length of tick marks
            tickcolor='#333',
            ticks='outside',  # Position ticks outside the plot area
            tickwidth=1,
            showline=True,  # Show the axis line
            linewidth=1,
            linecolor='#ddd',
            mirror=True,  # Mirror the axis line
            ticklabelstandoff=5  # Add 5px spacing between tick labels and axis
        )
    }
