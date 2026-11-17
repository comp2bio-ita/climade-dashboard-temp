import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phylo_module.services.alignment_service import (
    align_fasta_sequences,
)


SAMPLE_INPUT = """>seq_a description A
ACGTACGT
>seq_b description B
ACGTATGT
"""

MAFFT_OUTPUT = """>seq_a description A
ACGTACGT
>seq_b description B
ACGTATGT
"""


class TestAlignFastaSequences(unittest.TestCase):
    def test_raises_when_input_missing(self):
        with self.assertRaises(FileNotFoundError):
            align_fasta_sequences("/nonexistent/input.fasta", "/tmp/out.fasta")

    def test_raises_when_mafft_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "in.fasta"
            input_path.write_text(SAMPLE_INPUT)
            with patch(
                "phylo_module.services.alignment_service.shutil.which",
                return_value=None,
            ):
                with self.assertRaises(FileNotFoundError) as ctx:
                    align_fasta_sequences(str(input_path), str(Path(tmp) / "out.fasta"))
                self.assertIn("MAFFT", str(ctx.exception))

    @patch("phylo_module.services.alignment_service.shutil.which", return_value="/usr/bin/mafft")
    @patch("phylo_module.services.alignment_service.subprocess.run")
    def test_writes_aligned_fasta_and_returns_counts(self, mock_run, _which):
        mock_run.return_value = unittest.mock.MagicMock(
            returncode=0,
            stdout=MAFFT_OUTPUT,
            stderr="",
        )

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "in.fasta"
            output_path = Path(tmp) / "aligned.fasta"
            input_path.write_text(SAMPLE_INPUT)

            result = align_fasta_sequences(str(input_path), str(output_path))

            self.assertEqual(result["input_records"], 2)
            self.assertEqual(result["output_records"], 2)
            self.assertTrue(output_path.is_file())
            self.assertIn(">seq_a", output_path.read_text())
            mock_run.assert_called_once()
            self.assertEqual(mock_run.call_args[0][0][0], "/usr/bin/mafft")
            self.assertEqual(mock_run.call_args[0][0][1], "--auto")

    @patch("phylo_module.services.alignment_service.shutil.which", return_value="/usr/bin/mafft")
    @patch("phylo_module.services.alignment_service.subprocess.run")
    def test_raises_when_mafft_fails(self, mock_run, _which):
        mock_run.return_value = unittest.mock.MagicMock(
            returncode=1,
            stdout="",
            stderr="MAFFT error",
        )

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "in.fasta"
            input_path.write_text(SAMPLE_INPUT)
            with self.assertRaises(RuntimeError) as ctx:
                align_fasta_sequences(str(input_path), str(Path(tmp) / "out.fasta"))
            self.assertIn("MAFFT failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
