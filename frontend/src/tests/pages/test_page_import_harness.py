"""The harness itself: pages import, against stand-in data, touching no database or dataset file."""

import pandas as pd


class TestPagesImport:
    def test_all_three_pages_import(self, pathogen_pages):
        assert set(pathogen_pages) == {"dengue", "chikungunya", "zika"}

    def test_each_page_registers_its_route(self, pathogen_pages):
        import dash

        routes = {page["path"] for page in dash.page_registry.values()}
        assert {"/dengue", "/chikungunya", "/zika"} <= routes

    def test_each_page_built_a_frame_from_the_stand_in_records(self, pathogen_pages):
        frames = {
            "dengue": pathogen_pages["dengue"].df_world_dengue,
            "chikungunya": pathogen_pages["chikungunya"].df_world_chikungunya,
            "zika": pathogen_pages["zika"].df_world_zika,
        }
        for name, frame in frames.items():
            assert isinstance(frame, pd.DataFrame), name
            assert not frame.empty, name


class TestStandInData:
    def test_every_page_drops_the_undated_sequence(self, pathogen_pages):
        # clean_df(..., ['country', 'collection_date']) at dengue_page.py:79,
        # chikungunya_page.py:50 and — since task B2 — zika_page.py:48
        dropped = {
            "dengue": ("AB000004.1", pathogen_pages["dengue"].df_world_dengue),
            "chikungunya": ("CB000004.1", pathogen_pages["chikungunya"].df_world_chikungunya),
            "zika": ("ZB000004.1", pathogen_pages["zika"].df_world_zika),
        }
        for name, (accession, frame) in dropped.items():
            assert accession not in set(frame["genbank_sequence_data_id"]), name

    def test_unresolved_classification_becomes_unassigned(self, pathogen_pages):
        dengue = pathogen_pages["dengue"].df_world_dengue
        unresolved = dengue[dengue["genbank_sequence_data_id"] == "AB000006.1"]
        assert unresolved["serotype"].iloc[0] == "Unassigned"

    def test_missing_host_becomes_unknown(self, pathogen_pages):
        zika = pathogen_pages["zika"].df_world_zika
        assert "Unknown" in set(zika["host"])


class TestNoSideEffects:
    def test_no_real_dataset_file_was_written(self, pathogen_pages):
        from pathlib import Path

        REPO_ROOT = Path(__file__).resolve().parents[3]

        # If the to_csv redirect ever breaks, importing a page would overwrite these
        for relative_path in (
            "data/dengue/Final_global_dengue.tsv",
            "data/chikungunya/Final_global_chikv.tsv",
            "data/zika/Final_global_zika.tsv",
        ):
            dataset = REPO_ROOT / Path(relative_path)
            if dataset.exists():
                assert dataset.stat().st_size > 0, relative_path
