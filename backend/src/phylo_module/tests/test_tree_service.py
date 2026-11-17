import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phylo_module.services.tree_service import build_fasttree

SAMPLE_ALIGNMENT = """>tip_a
ACGTACGT
>tip_b
ACGTATGT
"""

SAMPLE_NEWICK = "((tip_a:0.1,tip_b:0.2):0.0);\n"


class TestBuildFasttree(unittest.TestCase):
    def test_raises_when_alignment_missing(self):
        with self.assertRaises(FileNotFoundError):
            build_fasttree("/nonexistent/aligned.fasta", "/tmp/tree.nwk")

    @patch("phylo_module.services.tree_service.shutil.which", return_value=None)
    def test_raises_when_fasttree_not_found(self, _which):
        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            with self.assertRaises(FileNotFoundError) as ctx:
                build_fasttree(str(alignment), str(Path(tmp) / "tree.nwk"))
            self.assertIn("FastTree", str(ctx.exception))

    @patch("phylo_module.services.tree_service.shutil.which", return_value="/usr/bin/FastTree")
    @patch("phylo_module.services.tree_service.subprocess.run")
    def test_writes_newick_tree(self, mock_run, _which):
        mock_run.return_value = unittest.mock.MagicMock(
            returncode=0,
            stdout=SAMPLE_NEWICK,
            stderr="",
        )

        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            tree_path = Path(tmp) / "tree.nwk"
            alignment.write_text(SAMPLE_ALIGNMENT)

            result = build_fasttree(str(alignment), str(tree_path))

            self.assertEqual(result["alignment_records"], 2)
            self.assertTrue(tree_path.is_file())
            self.assertTrue(tree_path.read_text().startswith("("))
            self.assertEqual(result["tree_characters"], len(SAMPLE_NEWICK.strip()))
            mock_run.assert_called_once()
            self.assertEqual(mock_run.call_args[0][0][0], "/usr/bin/FastTree")
            self.assertEqual(mock_run.call_args[0][0][1], "-nt")

    @patch("phylo_module.services.tree_service.shutil.which", return_value="/usr/bin/FastTree")
    @patch("phylo_module.services.tree_service.subprocess.run")
    def test_raises_when_fasttree_fails(self, mock_run, _which):
        mock_run.return_value = unittest.mock.MagicMock(
            returncode=1,
            stdout="",
            stderr="FastTree error",
        )

        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            with self.assertRaises(RuntimeError) as ctx:
                build_fasttree(str(alignment), str(Path(tmp) / "tree.nwk"))
            self.assertIn("FastTree failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
