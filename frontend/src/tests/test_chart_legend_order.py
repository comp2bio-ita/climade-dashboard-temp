"""Legend and trace order on the bar chart.

graphs/bar.py used to carry two hardcoded dengue serotype orders and decide between them
with `if pathogen_title.lower() == "serotype"`. The order a pathogen wants is declared in
src/pathogens.py and reaches the chart as `legend_order`, so those branches were a second
source for the same fact. These tests pin the resulting trace order so removing them is
verifiable rather than assumed.
"""

import unittest

import pandas as pd

from graphs.bar import build_bar_plot
from pathogens import get_pathogen


def percentage_frame(values, column):
    rows = []
    for period_start, period_end in (
        (pd.Timestamp("2015-01-01"), pd.Timestamp("2015-01-01")),
        (pd.Timestamp("2016-01-01"), pd.Timestamp("2016-01-01")),
    ):
        for value in values:
            rows.append({
                "datetime": period_end,
                "date_from": period_start,
                "period_start": period_start.strftime("%Y-%m"),
                "period_end": period_end.strftime("%Y-%m"),
                column: value,
                "proportion": 100.0 / len(values),
                "count": 1,
                "total_count": len(values),
            })
    return pd.DataFrame(rows)


def ordered_frame(values, column, category_order):
    frame = percentage_frame(values, column)
    present = frame[column].unique()
    ordered = ([v for v in category_order if v in present]
               + [v for v in present if v not in category_order])
    frame[column] = frame[column].astype("category").cat.reorder_categories(
        ordered, ordered=True)
    return frame


def trace_names(figure):
    return [trace.name for trace in figure.data]


class BarLegendOrderTest(unittest.TestCase):

    def figure_for(self, key, values):
        spec = get_pathogen(key)
        column = spec["classification_column"]
        order = [v for v in spec["classification_order"] if v in values]
        return build_bar_plot(
            df=ordered_frame(values, column, spec["classification_order"]),
            color_scheme=spec["color_scheme"],
            pathogen_title=column,
            legend_order=order,
        )

    def test_dengue_traces_follow_the_declared_serotype_order(self):
        # Deliberately fed in a scrambled order; the declared one must win
        figure = self.figure_for("denv", ["DENV3", "Unassigned", "DENV1", "DENV4", "DENV2"])
        self.assertEqual(trace_names(figure),
                         ["DENV1", "DENV2", "DENV3", "DENV4", "Unassigned"])

    def test_dengue_with_a_serotype_missing_from_the_selection(self):
        figure = self.figure_for("denv", ["DENV4", "DENV1"])
        self.assertEqual(trace_names(figure), ["DENV1", "DENV4"])

    def test_chikungunya_traces_follow_its_own_declared_order(self):
        figure = self.figure_for("chikv", ["WA", "Unassigned", "ECSA", "ACL"])
        self.assertEqual(trace_names(figure), ["ACL", "ECSA", "WA", "Unassigned"])

    def test_zika_traces_follow_its_own_declared_order(self):
        figure = self.figure_for("zikv", ["Unassigned", "Asian", "African"])
        self.assertEqual(trace_names(figure), ["African", "Asian", "Unassigned"])

    def test_dengue_genotype_axis_carries_no_serotype_order(self):
        # The detail-mode path: the second axis, and no legend_order supplied
        spec = get_pathogen("denv")
        figure = build_bar_plot(
            df=percentage_frame(["2II", "1I", "3III"], "genotype").assign(
                genotype=lambda f: f["genotype"].astype("category")),
            color_scheme=spec["subclassification_color_scheme"],
            pathogen_title="genotype",
        )
        self.assertEqual(sorted(trace_names(figure)), ["1I", "2II", "3III"])

    def test_a_value_outside_the_declared_order_is_kept_at_the_end(self):
        spec = get_pathogen("chikv")
        values = ["ECSA", "Novel", "ACL"]
        figure = build_bar_plot(
            df=ordered_frame(values, "genotype", spec["classification_order"]),
            color_scheme=spec["color_scheme"],
            pathogen_title="genotype",
            legend_order=[v for v in spec["classification_order"] if v in values],
        )
        self.assertEqual(trace_names(figure)[:2], ["ACL", "ECSA"])
        self.assertIn("Novel", trace_names(figure))


class AreaSubplotOrderTest(unittest.TestCase):
    """The area chart stacks one subplot per classification. That stack has to read in the
    same order as the legend beside it, or a reader matching one against the other lands on
    the wrong panel. graphs/area_plot.py used to order the stack by a hardcoded serotype
    list, falling back to sorted() — so chikungunya's panels ran ACL, ECSA, Unassigned, WA
    against a legend reading ACL, ECSA, WA, Unassigned.
    """

    def area_figure(self, key, values):
        from graphs.area_plot import plot_area_chat
        from pages.pathogen_dashboard import legend_order_for

        spec = get_pathogen(key)
        column = spec["classification_column"]
        rows = [{"datetime": pd.Timestamp(f"{2015 + index}-06-01"), column: value}
                for index, value in enumerate(values)]
        rows += [{"datetime": pd.Timestamp("2021-06-01"), column: value} for value in values]
        return plot_area_chat(
            df=pd.DataFrame(rows), data_col=column, target_pathogens=list(values),
            datetime_str_col="datetime", color_scheme=spec["color_scheme"],
            date_from="2015-01-01", date_to="2021-12-31",
            legend_order=legend_order_for(spec, values))

    def stack_order(self, figure):
        """Series in subplot order: add_trace(row=n) binds a trace to yaxis y<n>."""
        placed = [(1 if (trace.yaxis or "y") == "y" else int(trace.yaxis[1:]), trace.name)
                  for trace in figure.data]
        return [name for _, name in sorted(placed)]

    def test_chikungunya_stacks_in_its_declared_order(self):
        figure = self.area_figure("chikv", ["ACL", "ECSA", "WA", "Unassigned"])
        self.assertEqual(self.stack_order(figure), ["ACL", "ECSA", "WA", "Unassigned"])

    def test_dengue_and_zika_stack_in_their_declared_order(self):
        for key in ("denv", "zikv"):
            spec = get_pathogen(key)
            values = spec["classification_order"]
            figure = self.area_figure(key, values)
            self.assertEqual(self.stack_order(figure), list(values), key)

    def test_the_stack_and_the_legend_agree(self):
        for key in ("denv", "chikv", "zikv"):
            values = get_pathogen(key)["classification_order"]
            figure = self.area_figure(key, values)
            self.assertEqual(self.stack_order(figure), trace_names(figure), key)

    def test_a_value_the_pathogen_never_declared_stacks_last(self):
        figure = self.area_figure("chikv", ["ECSA", "Novel", "ACL"])
        self.assertEqual(self.stack_order(figure), ["ACL", "ECSA", "Novel"])


class LegendTitleTest(unittest.TestCase):
    """The legend used to be titled "Serotype" on every chart of every page, because
    get_chart_theme() hardcoded it. It now follows the axis the chart is coloured by."""

    def title_of(self, figure):
        return figure.layout.legend.title.text

    def test_dengue_serotype_charts_still_say_serotype(self):
        spec = get_pathogen("denv")
        values = ["DENV1", "DENV2"]
        figure = build_bar_plot(
            df=ordered_frame(values, "serotype", spec["classification_order"]),
            color_scheme=spec["color_scheme"], pathogen_title="serotype",
            legend_order=values)
        self.assertEqual(self.title_of(figure), "Serotype")

    def test_a_genotype_axis_says_genotype(self):
        for key, values in (("chikv", ["ACL", "ECSA"]), ("zikv", ["African", "Asian"])):
            spec = get_pathogen(key)
            figure = build_bar_plot(
                df=ordered_frame(values, "genotype", spec["classification_order"]),
                color_scheme=spec["color_scheme"], pathogen_title="genotype",
                legend_order=values)
            self.assertEqual(self.title_of(figure), "Genotype", key)

    def test_dengues_detail_view_says_genotype_too(self):
        spec = get_pathogen("denv")
        figure = build_bar_plot(
            df=percentage_frame(["1I", "2II"], "genotype"),
            color_scheme=spec["subclassification_color_scheme"],
            pathogen_title="genotype")
        self.assertEqual(self.title_of(figure), "Genotype")

    def test_the_area_chart_titles_its_legend_the_same_way(self):
        from graphs.area_plot import plot_area_chat

        spec = get_pathogen("chikv")
        frame = pd.DataFrame([
            {"datetime": pd.Timestamp("2015-06-01"), "genotype": "ACL"},
            {"datetime": pd.Timestamp("2016-06-01"), "genotype": "ECSA"},
        ])
        figure = plot_area_chat(
            df=frame, data_col="genotype", target_pathogens=["ACL", "ECSA"],
            datetime_str_col="datetime", color_scheme=spec["color_scheme"],
            date_from="2015-01-01", date_to="2017-01-01")
        self.assertEqual(self.title_of(figure), "Genotype")


if __name__ == "__main__":
    unittest.main()
