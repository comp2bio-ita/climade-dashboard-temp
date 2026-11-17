import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from phylo_module.services.fasta_service import (
    _normalize_accession_ids,
    fetch_fasta_sequences,
)


def _record(acc_id: str) -> MagicMock:
    record = MagicMock()
    record.id = acc_id
    return record


class TestNormalizeAccessionIds(unittest.TestCase):
    def test_deduplicates_and_strips(self):
        result = _normalize_accession_ids([" AB1.1 ", "AB1.1", "", "XY2.2"])
        self.assertEqual(result, ["AB1.1", "XY2.2"])


class TestFetchFastaSequences(unittest.TestCase):
    def test_raises_when_no_accessions(self):
        with self.assertRaises(ValueError):
            fetch_fasta_sequences([], "out.fasta")

    @patch("phylo_module.services.fasta_service._configure_entrez")
    @patch("phylo_module.services.fasta_service._fetch_single")
    @patch("phylo_module.services.fasta_service._fetch_batch")
    @patch("phylo_module.services.fasta_service.time.sleep")
    def test_writes_all_batches_and_reports_failures(
        self, _sleep, mock_batch, mock_single, _configure
    ):
        mock_batch.side_effect = [
            [_record("AB1.1"), _record("AB2.2")],
            [_record("AB3.3")],
        ]
        mock_single.return_value = None

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "subset.fasta"
            result = fetch_fasta_sequences(
                ["AB1.1", "AB2.2", "MISSING.9", "AB3.3"],
                str(output),
                batch_size=2,
                sleep_time=0,
            )

            content = output.read_text()
            self.assertIn(">AB1.1", content)
            self.assertIn(">AB2.2", content)
            self.assertIn(">AB3.3", content)
            self.assertEqual(result["requested"], 4)
            self.assertEqual(result["fetched"], 3)
            self.assertEqual(result["failed_accessions"], ["MISSING.9"])

    @patch("phylo_module.services.fasta_service._configure_entrez")
    @patch("phylo_module.services.fasta_service._fetch_single")
    @patch("phylo_module.services.fasta_service._fetch_batch")
    @patch("phylo_module.services.fasta_service.time.sleep")
    def test_batch_failure_falls_back_to_single_fetch(
        self, _sleep, mock_batch, mock_single, _configure
    ):
        mock_batch.side_effect = RuntimeError("Entrez unavailable")
        mock_single.return_value = _record("AB1.1")

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "fallback.fasta"
            result = fetch_fasta_sequences(["AB1.1"], str(output), sleep_time=0)

            self.assertEqual(result["fetched"], 1)
            self.assertEqual(result["failed_accessions"], [])
            self.assertIn(">AB1.1", output.read_text())
            mock_single.assert_called_once_with("AB1.1")


if __name__ == "__main__":
    unittest.main()
