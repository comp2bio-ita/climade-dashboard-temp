#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tip annotation: label matching, metadata joins, NCBI links."""

import pytest

from utils.color_schemes import UNKNOWN_CATEGORY_COLOR
from utils.phylo.viewer.annotate import (
    DEFAULT_GROUP,
    MISSING_GROUP,
    MetadataAnnotator,
    TipStyle,
    candidate_keys,
    is_accession,
    load_metadata,
    ncbi_url,
)
from utils.phylo.viewer.theme import CATEGORICAL, LIGHT

RECORDS = [
    {"accession": "AB078005", "country": "US", "year": "1997", "subtype": "B"},
    {"accession": "A04321", "country": "FR", "year": "1983", "subtype": "C"},
    {"accession": "HM208366", "country": "US", "year": "2006", "subtype": "B"},
]


class TestCandidateKeys:
    def test_exact_label_comes_first(self):
        assert candidate_keys("AB078005")[0] == "AB078005"

    def test_pipe_delimited_headers_yield_the_accession(self):
        assert "A04321" in candidate_keys("A04321|FR|1983")

    def test_version_suffix_is_stripped_after_the_versioned_form(self):
        keys = candidate_keys("AB078005.1|US|1997")
        assert keys.index("AB078005.1") < keys.index("AB078005")

    def test_duplicate_suffix_is_stripped(self):
        assert "AB078005" in candidate_keys("AB078005_2")

    def test_fasta_description_is_dropped(self):
        assert "AB078005" in candidate_keys("AB078005 Dengue virus 1 isolate from Brazil")

    def test_a_dot_inside_a_description_is_not_a_version(self):
        assert candidate_keys("ACC|Homo sapiens 1.2") == ["ACC|Homo sapiens 1.2", "ACC"]

    def test_keys_are_deduplicated_and_never_empty(self):
        keys = candidate_keys("PLAIN")
        assert keys == ["PLAIN"]
        assert len(keys) == len(set(keys))


class TestNcbiLinks:
    @pytest.mark.parametrize("label", [
        "AB078005", "A04321|FR|1983", "NC_001802.1", "M12345", "AB078005_2",
    ])
    def test_accession_shaped_labels_get_a_link(self, label):
        url = ncbi_url(label)
        assert url and url.startswith("https://www.ncbi.nlm.nih.gov/nuccore/")
        assert is_accession(label)

    @pytest.mark.parametrize("label", ["sample_one", "patient 42", "tip_7", ""])
    def test_other_labels_get_no_link(self, label):
        assert ncbi_url(label) is None
        assert not is_accession(label)

    def test_version_is_preserved_in_the_url(self):
        assert ncbi_url("AB078005.1").endswith("/AB078005.1")


class TestMetadataAnnotator:
    def test_key_column_defaults_to_the_first(self):
        assert MetadataAnnotator(RECORDS).key_col == "accession"

    def test_explicit_key_column(self):
        assert MetadataAnnotator(RECORDS, key_col="country").key_col == "country"

    def test_unknown_key_column_raises(self):
        with pytest.raises(ValueError, match="key_col"):
            MetadataAnnotator(RECORDS, key_col="nope")

    def test_unknown_color_by_raises(self):
        with pytest.raises(ValueError, match="color_by"):
            MetadataAnnotator(RECORDS, color_by="nope")

    def test_lookup_matches_a_piped_tree_label(self):
        annot = MetadataAnnotator(RECORDS)
        row = annot.lookup("AB078005|US|1997")
        assert row and row["subtype"] == "B"

    def test_lookup_is_case_insensitive(self):
        assert MetadataAnnotator(RECORDS).lookup("ab078005") is not None

    def test_grouping_follows_the_colour_column(self):
        annot = MetadataAnnotator(RECORDS, color_by="subtype")
        assert annot.style_for("AB078005|US|1997").group == "B"
        assert annot.style_for("A04321|FR|1983").group == "C"

    def test_group_order_is_first_seen_order(self):
        assert MetadataAnnotator(RECORDS, color_by="subtype").groups() == ["B", "C"]

    def test_same_group_gets_the_same_colour(self):
        annot = MetadataAnnotator(RECORDS, color_by="subtype")
        assert (annot.style_for("AB078005").color
                == annot.style_for("HM208366").color)

    def test_different_groups_get_different_colours(self):
        annot = MetadataAnnotator(RECORDS, color_by="subtype")
        assert annot.style_for("AB078005").color != annot.style_for("A04321").color

    def test_colours_are_stable_across_repeated_calls(self):
        annot = MetadataAnnotator(RECORDS, color_by="subtype")
        assert annot.style_for("AB078005").color == annot.style_for("AB078005").color

    def test_unmatched_tips_fall_into_the_missing_group(self):
        annot = MetadataAnnotator(RECORDS, color_by="subtype")
        style = annot.style_for("UNKNOWN_TIP")
        assert style.group == MISSING_GROUP
        assert style.color == UNKNOWN_CATEGORY_COLOR

    def test_without_color_by_every_tip_shares_one_group(self):
        annot = MetadataAnnotator(RECORDS)
        assert annot.style_for("AB078005").group == DEFAULT_GROUP
        assert annot.groups() == [DEFAULT_GROUP]

    def test_hover_rows_default_to_every_non_key_column(self):
        style = MetadataAnnotator(RECORDS).style_for("AB078005")
        assert dict(style.hover_rows) == {"country": "US", "year": "1997", "subtype": "B"}

    def test_hover_columns_can_be_restricted(self):
        annot = MetadataAnnotator(RECORDS, hover_cols=["year"])
        assert dict(annot.style_for("AB078005").hover_rows) == {"year": "1997"}

    def test_group_colours_come_from_the_categorical_palette(self):
        annot = MetadataAnnotator(RECORDS, color_by="subtype")
        assert annot.style_for("AB078005").color in CATEGORICAL

    def test_custom_palette_overrides_the_default(self):
        annot = MetadataAnnotator(RECORDS, color_by="subtype", palette=["#111111", "#222222"])
        assert annot.style_for("AB078005").color == "#111111"

    def test_ncbi_links_can_be_disabled(self):
        assert MetadataAnnotator(RECORDS, link_ncbi=False).style_for("AB078005").url is None

    def test_blank_and_nan_cells_are_dropped_from_hover(self):
        annot = MetadataAnnotator([{"accession": "X1", "note": None, "ok": "yes"}])
        assert dict(annot.style_for("X1").hover_rows) == {"ok": "yes"}

    def test_empty_table_raises(self):
        with pytest.raises(ValueError, match="no columns"):
            MetadataAnnotator([])


class TestMetadataFromFile:
    def test_loads_the_example_csv(self, example_metadata_path):
        frame = load_metadata(example_metadata_path)
        assert list(frame.columns)[0] == "accession"
        assert len(frame) == 202

    def test_annotator_accepts_a_path_directly(self, example_metadata_path):
        annot = MetadataAnnotator(example_metadata_path, color_by="region")
        assert annot.style_for("A04321|FR|1983").group == "Europe"

    def test_tsv_is_read_with_tabs(self, tmp_path):
        path = tmp_path / "meta.tsv"
        path.write_text("accession\tgroup\nAB078005\tB\n", encoding="utf-8")
        assert list(load_metadata(path).columns) == ["accession", "group"]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_metadata(tmp_path / "nope.csv")
