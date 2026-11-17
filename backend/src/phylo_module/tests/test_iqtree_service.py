import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from phylo_module.services.iqtree_service import (
    _build_iqtree_command,
    _normalize_iqtree_settings,
    _parse_threads_used,
    run_iqtree,
)

SAMPLE_ALIGNMENT = """>tip_a
ACGTACGT
>tip_b
ACGTATGT
>tip_c
ACGTAAGT
>tip_d
ACGTAAGA
"""

# IQ-TREE SH-aLRT/UFBoot compound label on internal node
SAMPLE_TREEFILE = "((tip_a:0.1,tip_b:0.2)98.3/95:0.05,(tip_c:0.1,tip_d:0.1)90/80:0.0);\n"

SAMPLE_IQTREE_REPORT = """IQ-TREE 2.4.0

Best-fit model according to BIC: GTR+F+G4

Model of substitution: GTR+F+G4

BEST NUMBER OF THREADS: 3
"""

SAMPLE_IQTREE_REPORT_NO_THREADS = """IQ-TREE 2.4.0

Best-fit model according to BIC: GTR+F+G4

Model of substitution: GTR+F+G4
"""

VERSION_BANNER = "IQ-TREE multicore version 2.4.0 for Linux 64-bit\n"


def _fake_run(treefile_text=SAMPLE_TREEFILE, report_text=SAMPLE_IQTREE_REPORT, returncode=0,
              timeout=False):
    """Build a subprocess.run side_effect that emulates IQ-TREE writing files to <prefix>."""

    def side_effect(command, *args, **kwargs):
        if "--version" in command:
            return MagicMock(returncode=0, stdout=VERSION_BANNER, stderr="")
        if timeout:
            raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs.get("timeout", 1))
        prefix = command[command.index("--prefix") + 1]
        if returncode == 0:
            if treefile_text is not None:
                Path(prefix + ".treefile").write_text(treefile_text)
            if report_text is not None:
                Path(prefix + ".iqtree").write_text(report_text)
        return MagicMock(
            returncode=returncode,
            stdout="",
            stderr="IQ-TREE error" if returncode else "",
        )

    return side_effect


def _main_command(mock_run):
    for call in mock_run.call_args_list:
        command = call.args[0]
        if "--version" not in command:
            return command
    raise AssertionError("no main IQ-TREE run was recorded")


class TestBuildIqtreeCommand(unittest.TestCase):
    """Pure command-construction assertions (no subprocess, no filesystem)."""

    BASE = {
        "subst_type": "DNA",
        "model": "MFP",
        "thread_mode": "AUTO",
        "ntmax": 8,
        "seed": 12345,
        "ufboot_enabled": True,
        "ufboot_replicates": 1000,
        "shalrt_enabled": True,
        "shalrt_replicates": 1000,
        "bnni_enabled": False,
        "memory_limit": "8G",
    }

    def _build(self, **overrides):
        settings = dict(self.BASE, **overrides)
        return _build_iqtree_command("/usr/bin/iqtree2", "/data/aligned.fasta",
                                     "/runs/hash/iqtree/tree", settings)

    def test_default_profile(self):
        command = self._build()
        self.assertEqual(command[0], "/usr/bin/iqtree2")
        for pair in (["-s", "/data/aligned.fasta"], ["-st", "DNA"], ["-m", "MFP"],
                     ["-T", "AUTO"], ["-ntmax", "8"], ["-seed", "12345"],
                     ["--prefix", "/runs/hash/iqtree/tree"], ["-B", "1000"],
                     ["-alrt", "1000"], ["-mem", "8G"]):
            self.assertIn(pair[1], command)
        self.assertNotIn("-bnni", command)
        self.assertNotIn("-redo", command)

    def test_bnni_only_when_ufboot_on(self):
        self.assertIn("-bnni", self._build(bnni_enabled=True))
        self.assertNotIn("-bnni", self._build(bnni_enabled=True, ufboot_enabled=False))

    def test_ufboot_off_omits_bootstrap(self):
        command = self._build(ufboot_enabled=False, bnni_enabled=True)
        self.assertNotIn("-B", command)
        self.assertNotIn("-bnni", command)

    def test_shalrt_off_omits_alrt(self):
        self.assertNotIn("-alrt", self._build(shalrt_enabled=False))

    def test_no_memory_flag_when_unset(self):
        self.assertNotIn("-mem", self._build(memory_limit=None))


class TestNormalizeIqtreeSettings(unittest.TestCase):
    def test_defaults_apply(self):
        warnings = []
        settings = _normalize_iqtree_settings({}, warnings)
        self.assertEqual(settings["model"], "MFP")
        self.assertTrue(settings["ufboot_enabled"])
        self.assertEqual(settings["ufboot_replicates"], 1000)
        self.assertFalse(settings["bnni_enabled"])
        self.assertEqual(warnings, [])

    def test_bnni_without_ufboot_warns_and_drops(self):
        warnings = []
        settings = _normalize_iqtree_settings(
            {"ufboot_enabled": False, "bnni_enabled": True}, warnings
        )
        self.assertFalse(settings["bnni_enabled"])
        self.assertTrue(any("BNNI" in w for w in warnings))

    def test_replicates_below_minimum_rejected(self):
        with self.assertRaises(ValueError):
            _normalize_iqtree_settings({"ufboot_replicates": 500}, [])

    def test_replicates_above_server_limit_rejected(self):
        with self.assertRaises(ValueError):
            _normalize_iqtree_settings({"ufboot_replicates": 999999}, [])

    def test_ntmax_above_server_limit_rejected(self):
        with self.assertRaises(ValueError):
            _normalize_iqtree_settings({"ntmax": 9999}, [])

    def test_invalid_seed_rejected(self):
        with self.assertRaises(ValueError):
            _normalize_iqtree_settings({"seed": "not-an-int"}, [])

    def test_invalid_model_rejected(self):
        with self.assertRaises(ValueError):
            _normalize_iqtree_settings({"model": "GTR; rm -rf"}, [])

    def test_invalid_subst_type_rejected(self):
        with self.assertRaises(ValueError):
            _normalize_iqtree_settings({"subst_type": "PROTEINS"}, [])


class TestRunIqtree(unittest.TestCase):
    def test_raises_when_alignment_missing(self):
        with self.assertRaises(FileNotFoundError):
            run_iqtree("/nonexistent/aligned.fasta", "/tmp/iqtree", {})

    @patch("phylo_module.services.iqtree_service.shutil.which", return_value=None)
    def test_raises_when_iqtree_not_found(self, _which):
        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            with self.assertRaises(FileNotFoundError) as ctx:
                run_iqtree(str(alignment), str(Path(tmp) / "iqtree"), {})
            self.assertIn("IQ-TREE", str(ctx.exception))

    @patch("phylo_module.services.iqtree_service.shutil.which", return_value="/usr/bin/iqtree2")
    @patch("phylo_module.services.iqtree_service.subprocess.run")
    def test_successful_run(self, mock_run, _which):
        mock_run.side_effect = _fake_run()
        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            method_dir = Path(tmp) / "iqtree"

            result = run_iqtree(str(alignment), str(method_dir), {})

            command = _main_command(mock_run)
            self.assertEqual(command[0], "/usr/bin/iqtree2")
            self.assertIn("-B", command)
            self.assertIn("1000", command)
            self.assertNotIn("-bnni", command)
            self.assertEqual(result["alignment_records"], 4)
            self.assertEqual(result["software"], "IQ-TREE")
            self.assertEqual(result["software_version"], "2.4.0")
            self.assertEqual(result["selected_model"], "GTR+F+G4")
            self.assertEqual(result["threads_used"], 3)
            # canonical tree.nwk written from the .treefile, compound labels preserved
            canonical = method_dir / "tree.nwk"
            self.assertTrue(canonical.is_file())
            self.assertEqual(canonical.read_text(), SAMPLE_TREEFILE)
            self.assertIn("98.3/95", canonical.read_text())
            self.assertTrue(result["output_path"].endswith("tree.nwk"))

    @patch("phylo_module.services.iqtree_service.shutil.which", return_value="/usr/bin/iqtree2")
    @patch("phylo_module.services.iqtree_service.subprocess.run")
    def test_threads_used_null_when_absent(self, mock_run, _which):
        mock_run.side_effect = _fake_run(report_text=SAMPLE_IQTREE_REPORT_NO_THREADS)
        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            result = run_iqtree(str(alignment), str(Path(tmp) / "iqtree"), {})
            self.assertIsNone(result["threads_used"])

    def test_parse_threads_used_from_log_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "tree.log"
            log_path.write_text("Measuring multi-threading\nBEST NUMBER OF THREADS: 11\n")
            self.assertEqual(_parse_threads_used(log_path), 11)
            self.assertIsNone(_parse_threads_used(Path(tmp) / "missing.log"))

    @patch("phylo_module.services.iqtree_service.shutil.which", return_value="/usr/bin/iqtree2")
    @patch("phylo_module.services.iqtree_service.subprocess.run")
    def test_enhanced_profile_emits_bnni(self, mock_run, _which):
        mock_run.side_effect = _fake_run()
        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            run_iqtree(str(alignment), str(Path(tmp) / "iqtree"), {"bnni_enabled": True})
            self.assertIn("-bnni", _main_command(mock_run))

    @patch("phylo_module.services.iqtree_service.shutil.which", return_value="/usr/bin/iqtree2")
    @patch("phylo_module.services.iqtree_service.subprocess.run")
    def test_invalid_config_rejected_before_success(self, mock_run, _which):
        mock_run.side_effect = _fake_run()
        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            with self.assertRaises(ValueError):
                run_iqtree(str(alignment), str(Path(tmp) / "iqtree"),
                           {"ufboot_replicates": 10})

    @patch("phylo_module.services.iqtree_service.shutil.which", return_value="/usr/bin/iqtree2")
    @patch("phylo_module.services.iqtree_service.subprocess.run")
    def test_timeout_reports_checkpoint(self, mock_run, _which):
        mock_run.side_effect = _fake_run(timeout=True)
        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            with self.assertRaises(RuntimeError) as ctx:
                run_iqtree(str(alignment), str(Path(tmp) / "iqtree"), {"timeout": 1})
            self.assertIn("timed out", str(ctx.exception))
            self.assertIn("ckp.gz", str(ctx.exception))

    @patch("phylo_module.services.iqtree_service.shutil.which", return_value="/usr/bin/iqtree2")
    @patch("phylo_module.services.iqtree_service.subprocess.run")
    def test_nonzero_exit_fails(self, mock_run, _which):
        mock_run.side_effect = _fake_run(returncode=2)
        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            with self.assertRaises(RuntimeError) as ctx:
                run_iqtree(str(alignment), str(Path(tmp) / "iqtree"), {})
            self.assertIn("IQ-TREE failed", str(ctx.exception))

    @patch("phylo_module.services.iqtree_service.shutil.which", return_value="/usr/bin/iqtree2")
    @patch("phylo_module.services.iqtree_service.subprocess.run")
    def test_missing_treefile_fails(self, mock_run, _which):
        # returncode 0 but the side_effect writes no treefile.
        mock_run.side_effect = _fake_run(treefile_text=None)
        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            with self.assertRaises(RuntimeError) as ctx:
                run_iqtree(str(alignment), str(Path(tmp) / "iqtree"), {})
            self.assertIn("no tree file", str(ctx.exception))

    @patch("phylo_module.services.iqtree_service.shutil.which", return_value="/usr/bin/iqtree2")
    @patch("phylo_module.services.iqtree_service.subprocess.run")
    def test_invalid_newick_fails(self, mock_run, _which):
        mock_run.side_effect = _fake_run(treefile_text="this is not newick\n")
        with tempfile.TemporaryDirectory() as tmp:
            alignment = Path(tmp) / "aligned.fasta"
            alignment.write_text(SAMPLE_ALIGNMENT)
            with self.assertRaises(ValueError):
                run_iqtree(str(alignment), str(Path(tmp) / "iqtree"), {})


if __name__ == "__main__":
    unittest.main()
