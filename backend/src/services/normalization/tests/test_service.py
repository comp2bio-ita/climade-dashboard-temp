import json
import unittest
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

from services.normalization import brazil
from services.normalization.ibge_catalog import build_indexes, load_ibge_catalog
from services.normalization.service import (
    STRATEGIES,
    curate_location_normalized,
    get_curation_row,
    normalize_location,
    normalize_pending_locations,
    strategy_available,
)
from services.normalization.text import normalize_text, parse_location

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ibge_municipios_sample.json"


def sample_catalog():
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        municipalities = json.load(handle)
    return build_indexes(municipalities)


class TestTextHelpers(unittest.TestCase):
    def test_normalize_text_strips_accents_and_case(self):
        self.assertEqual(normalize_text("São Paulo"), "sao paulo")
        self.assertEqual(normalize_text("  Minas   Gerais "), "minas gerais")

    def test_parse_location_splits_country_and_parts(self):
        country, parts = parse_location("Brazil: Belo Horizonte, Minas Gerais")
        self.assertEqual(country, "Brazil")
        self.assertEqual(parts, ["Belo Horizonte", "Minas Gerais"])


class TestBrazilStrategy(unittest.TestCase):
    def setUp(self):
        self.catalog = sample_catalog()
        brazil.set_catalog(self.catalog)

    def tearDown(self):
        brazil.set_catalog(None)

    def test_canonical_ordering(self):
        result = brazil.normalize_brazil_location("Brazil: Minas Gerais, Belo Horizonte")
        self.assertEqual(result, "Brazil: Minas Gerais, Belo Horizonte")

    def test_reversed_ordering(self):
        result = brazil.normalize_brazil_location("Brazil: Belo Horizonte, Minas Gerais")
        self.assertEqual(result, "Brazil: Minas Gerais, Belo Horizonte")

    def test_uf_by_sigla(self):
        result = brazil.normalize_brazil_location("Brazil: MG, Belo Horizonte")
        self.assertEqual(result, "Brazil: Minas Gerais, Belo Horizonte")

    def test_capitalization_differences(self):
        result = brazil.normalize_brazil_location("Brazil: minas gerais, belo horizonte")
        self.assertEqual(result, "Brazil: Minas Gerais, Belo Horizonte")

    def test_accent_differences(self):
        result = brazil.normalize_brazil_location("Brazil: Minas Geraís, Belo Horizonte")
        self.assertEqual(result, "Brazil: Minas Gerais, Belo Horizonte")

    def test_municipality_validated_within_uf(self):
        result = brazil.normalize_brazil_location("Brazil: Rio Branco, Acre")
        self.assertEqual(result, "Brazil: Acre, Rio Branco")

    def test_unknown_municipality_returns_none(self):
        self.assertIsNone(brazil.normalize_brazil_location("Brazil: Minas Gerais, Cidade Inexistente"))

    def test_both_components_are_ufs_returns_none(self):
        self.assertIsNone(brazil.normalize_brazil_location("Brazil: Minas Gerais, Sao Paulo"))

    def test_neither_component_is_uf_returns_none(self):
        self.assertIsNone(brazil.normalize_brazil_location("Brazil: Belo Horizonte, Campinas"))

    def test_malformed_location_without_colon_returns_none(self):
        self.assertIsNone(brazil.normalize_brazil_location("Brazil Minas Gerais"))

    def test_unsupported_structure_with_three_parts_returns_none(self):
        self.assertIsNone(brazil.normalize_brazil_location("Brazil: Minas Gerais: Belo Horizonte"))

    def test_single_component_returns_none(self):
        self.assertIsNone(brazil.normalize_brazil_location("Brazil: Minas Gerais"))

    def test_same_name_in_canonical_order_resolves(self):
        self.assertEqual(
            brazil.normalize_brazil_location("Brazil: Sao Paulo, Sao Paulo"),
            "Brazil: São Paulo, São Paulo",
        )
        self.assertEqual(
            brazil.normalize_brazil_location("Brazil: Rio de Janeiro, Rio de Janeiro"),
            "Brazil: Rio de Janeiro, Rio de Janeiro",
        )

    def test_sigla_disambiguates_same_name_uf_and_municipality(self):
        self.assertEqual(
            brazil.normalize_brazil_location("Brazil: SP, Sao Paulo"),
            "Brazil: São Paulo, São Paulo",
        )
        self.assertEqual(
            brazil.normalize_brazil_location("Brazil: RJ, Rio de Janeiro"),
            "Brazil: Rio de Janeiro, Rio de Janeiro",
        )
        self.assertEqual(
            brazil.normalize_brazil_location("Brazil: Sao Paulo, SP"),
            "Brazil: São Paulo, São Paulo",
        )

    def test_homonymous_municipality_resolves_with_uf_context(self):
        self.assertEqual(
            brazil.normalize_brazil_location("Brazil: Piauí, Bom Jesus"),
            "Brazil: Piauí, Bom Jesus",
        )
        self.assertEqual(
            brazil.normalize_brazil_location("Brazil: Bom Jesus, Piauí"),
            "Brazil: Piauí, Bom Jesus",
        )
        self.assertEqual(
            brazil.normalize_brazil_location("Brazil: Rio Grande do Norte, Bom Jesus"),
            "Brazil: Rio Grande do Norte, Bom Jesus",
        )

    def test_equivalent_inputs_produce_same_canonical_output(self):
        sao_paulo_canonical = "Brazil: São Paulo, São Paulo"
        sao_paulo_variants = [
            "Brazil: SP, Sao Paulo",
            "Brazil: Sao Paulo, Sao Paulo",
            "Brazil: sao paulo, sao paulo",
            "Brazil: SP, São Paulo",
        ]
        for location in sao_paulo_variants:
            with self.subTest(location=location):
                self.assertEqual(
                    brazil.normalize_brazil_location(location),
                    sao_paulo_canonical,
                )

        belo_horizonte_canonical = "Brazil: Minas Gerais, Belo Horizonte"
        belo_horizonte_variants = [
            "Brazil: belo horizonte, minas gerais",
            "Brazil: Minas Gerais, Belo Horizonte",
            "Brazil: MG, Belo Horizonte",
            "Brazil: Belo Horizonte, Minas Gerais",
        ]
        for location in belo_horizonte_variants:
            with self.subTest(location=location):
                self.assertEqual(
                    brazil.normalize_brazil_location(location),
                    belo_horizonte_canonical,
                )

    def test_output_uses_ibge_official_names_with_diacritics(self):
        result = brazil.normalize_brazil_location("Brazil: SP, Sao Paulo")
        self.assertEqual(result, "Brazil: São Paulo, São Paulo")
        self.assertIn("São", result)
        self.assertNotIn("sao paulo", result.lower())

        result = brazil.normalize_brazil_location("Brazil: belo horizonte, minas gerais")
        self.assertEqual(result, "Brazil: Minas Gerais, Belo Horizonte")
        self.assertIn("Minas Gerais", result)
        self.assertNotEqual(result, "Brazil: minas gerais, belo horizonte")


class TestServiceDispatch(unittest.TestCase):
    def setUp(self):
        self.catalog = sample_catalog()
        brazil.set_catalog(self.catalog)

    def tearDown(self):
        brazil.set_catalog(None)

    def test_strategy_available_for_brazil_aliases(self):
        self.assertTrue(strategy_available("Brazil"))
        self.assertTrue(strategy_available("Brasil"))

    def test_strategy_unavailable_for_other_countries(self):
        self.assertFalse(strategy_available("Peru"))

    def test_dispatch_to_registered_strategy(self):
        result = normalize_location("Brazil", "Brazil: Belo Horizonte, Minas Gerais")
        self.assertEqual(result, "Brazil: Minas Gerais, Belo Horizonte")

    def test_unsupported_country_returns_none(self):
        with self.assertLogs("services.normalization.service", level="INFO") as logs:
            result = normalize_location("Peru", "Peru: Lima")
        self.assertIsNone(result)
        self.assertTrue(
            any("not available for country: Peru" in message for message in logs.output)
        )

    def test_brazil_registered_in_strategies(self):
        self.assertIn("brazil", STRATEGIES)
        self.assertIn("brasil", STRATEGIES)


class TestNormalizePendingLocations(unittest.TestCase):
    def setUp(self):
        self.catalog = sample_catalog()
        brazil.set_catalog(self.catalog)

    def tearDown(self):
        brazil.set_catalog(None)

    def test_distinct_locations_normalized_once_and_applied_to_all_rows(self):
        database_service = MagicMock()
        database_service.get_record_by_filters.return_value = [
            {"accession_id": "A1", "location": "Brazil: Belo Horizonte, Minas Gerais"},
            {"accession_id": "A2", "location": "Brazil: Belo Horizonte, Minas Gerais"},
            {"accession_id": "A3", "location": "Brazil: Rio Branco, Acre"},
        ]

        with patch(
            "services.normalization.service.normalize_location",
            wraps=normalize_location,
        ) as normalize_mock:
            summary = normalize_pending_locations(database_service)

        self.assertEqual(normalize_mock.call_count, 2)
        self.assertEqual(summary["distinct"], 2)
        self.assertEqual(summary["resolved"], 3)

        updates = database_service.update_bulk.call_args[0][1]
        self.assertEqual(len(updates), 3)
        by_accession = {row["accession_id"]: row["location_normalized"] for row in updates}
        self.assertEqual(
            by_accession["A1"],
            "Brazil: Minas Gerais, Belo Horizonte",
        )
        self.assertEqual(
            by_accession["A2"],
            "Brazil: Minas Gerais, Belo Horizonte",
        )
        self.assertEqual(by_accession["A3"], "Brazil: Acre, Rio Branco")

    def test_unresolved_results_remain_null(self):
        database_service = MagicMock()
        database_service.get_record_by_filters.return_value = [
            {"accession_id": "A1", "location": "Brazil: Minas Gerais, Cidade Inexistente"},
        ]

        summary = normalize_pending_locations(database_service)

        self.assertEqual(summary["unresolved"], 1)
        updates = database_service.update_bulk.call_args[0][1]
        self.assertIsNone(updates[0]["location_normalized"])

    def test_raw_location_is_not_modified(self):
        database_service = MagicMock()
        database_service.get_record_by_filters.return_value = [
            {"accession_id": "A1", "location": "Brazil: Belo Horizonte, Minas Gerais"},
        ]

        normalize_pending_locations(database_service)

        updates = database_service.update_bulk.call_args[0][1]
        self.assertNotIn("location", updates[0])

    def test_country_filter_skips_non_matching_rows(self):
        database_service = MagicMock()
        database_service.get_record_by_filters.return_value = [
            {"accession_id": "BR1", "location": "Brazil: Belo Horizonte, Minas Gerais"},
            {"accession_id": "US1", "location": "USA: Florida"},
        ]

        summary = normalize_pending_locations(database_service, country="Brazil")

        self.assertEqual(summary["distinct"], 1)
        self.assertEqual(summary["updated"], 1)
        updates = database_service.update_bulk.call_args[0][1]
        self.assertEqual([row["accession_id"] for row in updates], ["BR1"])

    def test_brasil_alias_matches_brazil_prefix_rows(self):
        database_service = MagicMock()
        database_service.get_record_by_filters.return_value = [
            {"accession_id": "BR1", "location": "Brazil: Belo Horizonte, Minas Gerais"},
        ]

        summary = normalize_pending_locations(database_service, country="Brasil")

        self.assertEqual(summary["distinct"], 1)
        self.assertEqual(summary["resolved"], 1)


class TestIbgeCatalog(unittest.TestCase):
    def test_load_from_fixture_without_network(self):
        catalog = load_ibge_catalog(cache_path=FIXTURE_PATH)
        self.assertIn("mg", catalog.uf_lookup)
        self.assertEqual(
            catalog.municipality_lookup[("MG", "belo horizonte")],
            "Belo Horizonte",
        )


class TestCurate(unittest.TestCase):
    def test_get_curation_row_returns_none_when_not_found(self):
        database_service = MagicMock()
        database_service.get_record_by_filters.return_value = []

        self.assertIsNone(get_curation_row(database_service, "MISSING"))

    def test_get_curation_row_returns_location_fields(self):
        database_service = MagicMock()
        database_service.get_record_by_filters.return_value = [
            {
                "accession_id": "NC_001477",
                "location": "Brazil: Belo Horizonte-MG",
                "location_normalized": None,
            }
        ]

        row = get_curation_row(database_service, "NC_001477")

        self.assertEqual(
            row,
            {
                "accession_id": "NC_001477",
                "location": "Brazil: Belo Horizonte-MG",
                "location_normalized": None,
            },
        )

    def test_curate_location_normalized_updates_row(self):
        database_service = MagicMock()
        database_service.get_record_by_filters.return_value = [
            {
                "accession_id": "NC_001477",
                "location": "Brazil: Belo Horizonte-MG",
                "location_normalized": None,
            }
        ]

        result = curate_location_normalized(
            database_service,
            "NC_001477",
            "Brazil: Minas Gerais, Belo Horizonte",
        )

        database_service.update_bulk.assert_called_once_with(
            ANY,
            [
                {
                    "accession_id": "NC_001477",
                    "location_normalized": "Brazil: Minas Gerais, Belo Horizonte",
                }
            ],
        )
        self.assertEqual(
            result["location_normalized"],
            "Brazil: Minas Gerais, Belo Horizonte",
        )

    def test_curate_location_normalized_returns_none_when_not_found(self):
        database_service = MagicMock()
        database_service.get_record_by_filters.return_value = []

        self.assertIsNone(
            curate_location_normalized(
                database_service,
                "MISSING",
                "Brazil: Minas Gerais, Belo Horizonte",
            )
        )
        database_service.update_bulk.assert_not_called()


class TestCli(unittest.TestCase):
    def setUp(self):
        self.catalog = sample_catalog()
        brazil.set_catalog(self.catalog)

    def tearDown(self):
        brazil.set_catalog(None)

    def test_location_command_prints_normalized_value(self):
        from services.normalization.__main__ import main

        with patch("sys.stdout") as stdout:
            exit_code = main(
                ["location", "--country", "Brazil", "--value", "Brazil: Belo Horizonte, Minas Gerais"]
            )

        self.assertEqual(exit_code, 0)
        stdout.write.assert_any_call("Brazil: Minas Gerais, Belo Horizonte")

    def test_location_command_reports_unresolved(self):
        from services.normalization.__main__ import main

        with patch("sys.stdout") as stdout:
            exit_code = main(
                [
                    "location",
                    "--country",
                    "Brazil",
                    "--value",
                    "Brazil: Minas Gerais, Cidade Inexistente",
                ]
            )

        self.assertEqual(exit_code, 2)
        stdout.write.assert_any_call("Unresolved")

    def test_unsupported_country_message(self):
        from services.normalization.__main__ import main

        with patch("sys.stderr") as stderr:
            exit_code = main(
                ["location", "--country", "Peru", "--value", "Peru: Lima"]
            )

        self.assertEqual(exit_code, 1)
        written = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("Location normalization service not available for country: Peru", written)

    @patch("services.normalization.__main__._build_database_service")
    def test_curate_command_updates_with_yes_flag(self, build_database_service):
        from services.normalization.__main__ import main

        database_service = MagicMock()
        build_database_service.return_value = database_service
        database_service.get_record_by_filters.return_value = [
            {
                "accession_id": "NC_001477",
                "location": "Brazil: Belo Horizonte-MG",
                "location_normalized": None,
            }
        ]

        with patch("sys.stdout") as stdout:
            exit_code = main(
                [
                    "curate",
                    "--accession-id",
                    "NC_001477",
                    "--value",
                    "Brazil: Minas Gerais, Belo Horizonte",
                    "--yes",
                ]
            )

        self.assertEqual(exit_code, 0)
        database_service.update_bulk.assert_called_once()
        written = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("Updated.", written)

    @patch("services.normalization.__main__._build_database_service")
    def test_curate_command_cancels_without_confirmation(self, build_database_service):
        from services.normalization.__main__ import main

        database_service = MagicMock()
        build_database_service.return_value = database_service
        database_service.get_record_by_filters.return_value = [
            {
                "accession_id": "NC_001477",
                "location": "Brazil: Belo Horizonte-MG",
                "location_normalized": None,
            }
        ]

        with patch("builtins.input", return_value="n"):
            with patch("sys.stdout") as stdout:
                exit_code = main(
                    [
                        "curate",
                        "--accession-id",
                        "NC_001477",
                        "--value",
                        "Brazil: Minas Gerais, Belo Horizonte",
                    ]
                )

        self.assertEqual(exit_code, 0)
        database_service.update_bulk.assert_not_called()
        written = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("Cancelled.", written)

    @patch("services.normalization.__main__._build_database_service")
    def test_curate_command_rejects_missing_row(self, build_database_service):
        from services.normalization.__main__ import main

        database_service = MagicMock()
        build_database_service.return_value = database_service
        database_service.get_record_by_filters.return_value = []

        with patch("sys.stderr") as stderr:
            exit_code = main(
                [
                    "curate",
                    "--accession-id",
                    "MISSING",
                    "--value",
                    "Brazil: Minas Gerais, Belo Horizonte",
                    "--yes",
                ]
            )

        self.assertEqual(exit_code, 1)
        written = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("Row not found: MISSING", written)

    def test_curate_command_rejects_value_over_max_length(self):
        from services.normalization.__main__ import main

        with patch("sys.stderr") as stderr:
            exit_code = main(
                [
                    "curate",
                    "--accession-id",
                    "NC_001477",
                    "--value",
                    "x" * 101,
                    "--yes",
                ]
            )

        self.assertEqual(exit_code, 1)
        written = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("exceeds 100 characters", written)


if __name__ == "__main__":
    unittest.main()
