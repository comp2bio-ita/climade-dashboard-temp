from dash import html
import dash_bootstrap_components as dbc

# Reusable across pathogen pages: phylo inference is a general service, so this control
# carries no pathogen-specific config. component_id lets a page override the default when
# two phylo panels ever coexist. Values match the backend's _resolve_inference_method.
PHYLO_METHOD_ID = "phylo-method"


def load(component_id=PHYLO_METHOD_ID, sm=12, md="auto"):
    return dbc.Col(
        [
            html.Label(
                "Inference method:",
                className="form-label mb-1 small dashboard-form-label",
            ),
            dbc.RadioItems(
                id=component_id,
                options=[
                    {"label": "FastTree (fast)", "value": "fasttree"},
                    {"label": "IQ-TREE (branch support)", "value": "iqtree"},
                ],
                value="fasttree",
            ),
        ],
        sm=sm,
        md=md,
        className="my-1",
    )
