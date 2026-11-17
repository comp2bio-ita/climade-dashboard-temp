#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The two dashboard-specific additions to MetadataAnnotator."""

import pytest

from utils.color_schemes import UNKNOWN_CATEGORY_COLOR, color_map_for_pathogen_field


def color_map_for_field(field, values):
    # These cases are all dengue's curated schemes; task D1 made the lookup pathogen-scoped
    return color_map_for_pathogen_field("denv", field, values)
from utils.phylo.viewer.annotate import MISSING_GROUP, MetadataAnnotator

RECORDS = [
    {"accession_id": "PH031933.1", "serotype": "DENV1", "country": "Brazil"},
    {"accession_id": "PX945878.1", "serotype": "DENV2", "country": "Brazil"},
    {"accession_id": "PX945876.1", "serotype": "DENV1", "country": "Peru"},
]


def annotator(color_map=None, records=None):
    return MetadataAnnotator(
        records if records is not None else RECORDS,
        key_col="accession_id",
        color_by="serotype",
        color_map=color_map,
    )


class TestCuratedColours:
    def test_serotype_colours_match_the_rest_of_the_dashboard(self):
        curated = color_map_for_field("serotype", ["DENV1", "DENV2"])
        styled = annotator(color_map=curated)
        assert styled.style_for("PH031933.1").color == curated["DENV1"]
        assert styled.style_for("PX945878.1").color == curated["DENV2"]

    def test_two_tips_of_one_serotype_share_a_colour(self):
        styled = annotator(color_map=color_map_for_field("serotype", ["DENV1"]))
        assert styled.style_for("PH031933.1").color == styled.style_for("PX945876.1").color

    def test_value_outside_the_curated_scheme_is_not_invented(self):
        records = RECORDS + [{"accession_id": "XX000000.1", "serotype": "DENV9",
                              "country": "Nowhere"}]
        styled = annotator(color_map=color_map_for_field("serotype", []), records=records)
        assert styled.style_for("XX000000.1").color == UNKNOWN_CATEGORY_COLOR

    def test_generated_map_covers_free_text_fields(self):
        generated = color_map_for_field("country", ["Brazil", "Peru"])
        styled = MetadataAnnotator(RECORDS, key_col="accession_id",
                                   color_by="country", color_map=generated)
        assert styled.style_for("PH031933.1").color == generated["Brazil"]
        assert styled.style_for("PX945876.1").color == generated["Peru"]

    def test_without_a_color_map_the_palette_still_drives_colour(self):
        styled = annotator()
        assert styled.style_for("PH031933.1").color in styled.palette

    def test_unknown_category_colour_is_available_to_callers(self):
        assert UNKNOWN_CATEGORY_COLOR == "#808080"


class TestJoinReport:
    def test_every_tip_matched(self):
        report = annotator().join_report(["PH031933.1", "PX945878.1"])
        assert report == {"matched": 2, "unmatched": [], "duplicated": []}

    def test_tip_missing_from_the_metadata_is_named(self):
        report = annotator().join_report(["PH031933.1", "ZZ999999.1"])
        assert report["matched"] == 1
        assert report["unmatched"] == ["ZZ999999.1"]

    def test_unmatched_tip_is_still_drawn_but_grouped_apart(self):
        assert annotator().style_for("ZZ999999.1").group == MISSING_GROUP

    def test_duplicate_metadata_rows_are_reported_once(self):
        records = RECORDS + [{"accession_id": "PH031933.1", "serotype": "DENV4",
                              "country": "Duplicate"}]
        report = annotator(records=records).join_report(["PH031933.1"])
        assert report["duplicated"] == ["PH031933.1"]
        assert report["matched"] == 1

    def test_first_row_wins_for_a_duplicated_accession(self):
        records = RECORDS + [{"accession_id": "PH031933.1", "serotype": "DENV4",
                              "country": "Duplicate"}]
        assert annotator(records=records).lookup("PH031933.1")["serotype"] == "DENV1"

    def test_report_on_the_real_pipeline_tree(self, pipeline_newick):
        from utils.phylo.viewer.parse import parse_newick

        labels = parse_newick(pipeline_newick).tip_labels()
        report = annotator().join_report(labels)
        assert report["matched"] == 3
        assert len(report["unmatched"]) == len(labels) - 3


class TestPerPathogenColourRegistry:
    """Curated schemes are keyed by pathogen as well as field (task C2)."""

    def test_each_pathogen_gets_its_own_genotype_scheme(self):
        from utils.color_schemes import color_map_for_pathogen_field

        assert "ECSA" in color_map_for_pathogen_field("chikv", "genotype", ["ECSA"])
        assert "African" in color_map_for_pathogen_field("zikv", "genotype", ["African"])
        assert "1I" in color_map_for_pathogen_field("denv", "genotype", ["1I"])

    def test_a_genotype_is_not_coloured_from_another_pathogens_scheme(self):
        # Before C2 there was one global "genotype" entry holding dengue's map, so a
        # chikungunya lineage fell through to UNKNOWN_CATEGORY_COLOR
        from utils.color_schemes import color_map_for_pathogen_field

        chik = color_map_for_pathogen_field("chikv", "genotype", ["ECSA"])
        assert "1I" not in chik

    def test_an_unregistered_pathogen_falls_back_to_generated_colours(self):
        from utils.color_schemes import color_map_for_pathogen_field

        generated = color_map_for_pathogen_field("yellow-fever", "genotype", ["I", "II"])
        assert set(generated) == {"I", "II"}

    def test_a_field_with_no_curated_scheme_is_generated(self):
        from utils.color_schemes import color_map_for_pathogen_field

        generated = color_map_for_pathogen_field("denv", "country", ["Brazil", "Peru"])
        assert set(generated) == {"Brazil", "Peru"}

    def test_locality_colours_are_generated_not_curated(self):
        from utils.color_schemes import color_map_for_pathogen_field

        generated = color_map_for_pathogen_field("denv", "locality", ["Campinas", "FL"])
        assert set(generated) == {"Campinas", "FL"}

    def test_division_colours_are_generated_not_curated(self):
        from utils.color_schemes import color_map_for_pathogen_field

        generated = color_map_for_pathogen_field("denv", "division", ["Sao Paulo", "FL"])
        assert set(generated) == {"Sao Paulo", "FL"}
