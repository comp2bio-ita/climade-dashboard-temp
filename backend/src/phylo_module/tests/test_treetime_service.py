import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from Bio import Phylo

from phylo_module.services.treetime_service import (
    _build_treetime_command,
    _parse_clock_filter_excluded,
    _parse_molecular_clock,
    normalize_collection_dates,
    read_tree_tip_names,
    resolve_treetime_settings,
    run_treetime,
)

SAMPLE_ALIGNMENT = """>OQ100001
ACGTACGTAC
>OQ100002
ACGTATGTAC
>OQ100003
ACGTAAGTAC
>OQ100004
ACGTAAGAAC
>OQ100005
ACGTAAGAAG
"""

# FastTree numeric support on internals
FASTTREE_TREE = (
    "((OQ100001:0.1,OQ100002:0.2)0.899:0.05,"
    "(OQ100003:0.1,OQ100004:0.1)0.725:0.01,OQ100005:0.3);\n"
)

# IQ-TREE SH-aLRT/UFBoot compound labels
IQTREE_TREE = (
    "((OQ100001:0.1,OQ100002:0.2)98.3/95:0.05,"
    "(OQ100003:0.1,OQ100004:0.1)90/80:0.01,OQ100005:0.3);\n"
)

DATED_TIPS = {
    "OQ100001": "2015-06-15",
    "OQ100002": "2017-06-15",
    "OQ100003": "2019-06-15",
    "OQ100004": "2021-06-15",
}

SAMPLE_TIMETREE_NEXUS = """#NEXUS
Begin Taxa;
 Dimensions NTax=4;
 TaxLabels OQ100001 OQ100002 OQ100003 OQ100004;
End;
Begin Trees;
 Tree tree1=((OQ100001:1.5[&date=2015.45],OQ100002:2.5[&date=2017.45])NODE_0:0.1[&date=2014.1],\
(OQ100003:1.0[&date=2019.45],OQ100004:1.0[&date=2021.45])NODE_1:0.2[&date=2018.1]);
End;
"""

SAMPLE_MOLECULAR_CLOCK = "Root-Tip-Regression:\n --rate:\t5.274e-03\n --r^2:  \t0.98\n"

# TreeTime --outdir junk; must not survive the run
DISCARDED_ARTIFACTS = (
    "divergence_tree.nexus",
    "auspice_tree.json",
    "ancestral_sequences.fasta",
    "branch_mutations.txt",
    "dates.tsv",
    "sequence_evolution_model.txt",
    "trace_run.log",
    "timetree.pdf",
    "root_to_tip_regression.pdf",
)

OUTLIER_STDOUT = """
0.42\tTreeTime: the following tips have been marked as outliers. Their date constraints were not
      used. Please remove them from the tree. Their dates have been reset:

0.42\tOQ100003, input date: 2019.45, apparent date: 2011.02
"""

VERSION_BANNER = "treetime 0.12.1\n"


def _fake_run(timetree_text=SAMPLE_TIMETREE_NEXUS, clock_text=SAMPLE_MOLECULAR_CLOCK,
              stdout="", returncode=0, timeout=False, recorded_inputs=None):
    """Build a subprocess.run side_effect that emulates TreeTime filling --outdir."""

    def side_effect(command, *args, **kwargs):
        if "--version" in command:
            return MagicMock(returncode=0, stdout=VERSION_BANNER, stderr="")
        if timeout:
            raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs.get("timeout", 1))

        if recorded_inputs is not None:
            alignment = Path(command[command.index("--aln") + 1])
            tree = Path(command[command.index("--tree") + 1])
            dates = Path(command[command.index("--dates") + 1])
            recorded_inputs["alignment"] = {
                line[1:].strip()
                for line in alignment.read_text().splitlines()
                if line.startswith(">")
            }
            recorded_inputs["tree"] = {
                tip.name for tip in Phylo.read(str(tree), "newick").get_terminals()
            }
            date_lines = dates.read_text().splitlines()
            recorded_inputs["dates_header"] = date_lines[0]
            recorded_inputs["dates"] = {line.split("\t")[0] for line in date_lines[1:]}
            recorded_inputs["dates_path"] = dates

        outdir = Path(command[command.index("--outdir") + 1])
        outdir.mkdir(parents=True, exist_ok=True)
        if returncode == 0:
            if timetree_text is not None:
                (outdir / "timetree.nexus").write_text(timetree_text)
            if clock_text is not None:
                (outdir / "molecular_clock.txt").write_text(clock_text)
            for artifact in DISCARDED_ARTIFACTS:
                (outdir / artifact).write_text("noise")
        return MagicMock(
            returncode=returncode,
            stdout=stdout,
            stderr="TreeTime error" if returncode else "",
        )

    return side_effect


def _main_command(mock_run):
    for call in mock_run.call_args_list:
        command = call.args[0]
        if "--version" not in command:
            return command
    raise AssertionError("no main TreeTime run was recorded")


def _write_inputs(tmp, tree_text=FASTTREE_TREE):
    alignment = Path(tmp) / "aligned.fasta"
    alignment.write_text(SAMPLE_ALIGNMENT)
    tree = Path(tmp) / "tree.nwk"
    tree.write_text(tree_text)
    return alignment, tree


def _fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class TestNormalizeCollectionDates(unittest.TestCase):
    """Only the format the ingestion pipeline stores is usable; nothing is invented."""

    def test_stored_format_becomes_iso_day(self):
        normalized = normalize_collection_dates({"OQ100001": "2023-04-17T00:00:00Z"})
        self.assertEqual(normalized["dated_tips"], {"OQ100001": "2023-04-17"})
        self.assertEqual(normalized["excluded_tips"], [])

    def test_missing_date_is_excluded(self):
        normalized = normalize_collection_dates({"OQ100001": None, "OQ100002": "   "})
        self.assertEqual(normalized["dated_tips"], {})
        self.assertEqual(len(normalized["excluded_tips"]), 2)
        for excluded in normalized["excluded_tips"]:
            self.assertEqual(excluded["reason"], "no collection date")

    def test_bare_year_is_excluded_not_expanded_to_january_first(self):
        normalized = normalize_collection_dates({"OQ100001": "2021", "OQ100002": "2021-06"})
        self.assertEqual(normalized["dated_tips"], {})
        self.assertEqual(len(normalized["excluded_tips"]), 2)

    def test_other_date_formats_are_excluded(self):
        normalized = normalize_collection_dates(
            {"OQ100001": "2023-04-17", "OQ100002": "17-Apr-2023"}
        )
        self.assertEqual(normalized["dated_tips"], {})
        self.assertEqual(len(normalized["excluded_tips"]), 2)

    def test_exclusion_records_the_offending_value(self):
        normalized = normalize_collection_dates({"OQ100001": "17-Apr-2023"})
        self.assertIn("17-Apr-2023", normalized["excluded_tips"][0]["reason"])

    def test_mixed_input_splits_usable_from_unusable(self):
        normalized = normalize_collection_dates(
            {
                "OQ100001": "2015-06-15T00:00:00Z",
                "OQ100002": None,
                "OQ100003": "2019-06-15T00:00:00Z",
            }
        )
        self.assertEqual(sorted(normalized["dated_tips"]), ["OQ100001", "OQ100003"])
        self.assertEqual([tip["accession_id"] for tip in normalized["excluded_tips"]], ["OQ100002"])


class TestBuildTreetimeCommand(unittest.TestCase):
    """Pure command-construction assertions (no subprocess, no filesystem)."""

    def _build(self, **overrides):
        settings = dict(resolve_treetime_settings({}), **overrides)
        return _build_treetime_command(
            "/usr/bin/treetime", "/tmp/aligned.fasta", "/tmp/tree.nwk",
            "/tmp/collection_dates.tsv", "/tmp/outdir", settings,
        )

    def test_documented_parameter_set(self):
        command = self._build()
        for flag, value in (
            ("--aln", "/tmp/aligned.fasta"),
            ("--tree", "/tmp/tree.nwk"),
            ("--dates", "/tmp/collection_dates.tsv"),
            ("--name-column", "accession_id"),
            ("--date-column", "collection_date"),
            ("--reroot", "least-squares"),
            ("--clock-filter", "4"),
            ("--clock-filter-method", "residual"),
            ("--branch-length-mode", "auto"),
            ("--rng-seed", "12345"),
            ("--outdir", "/tmp/outdir"),
        ):
            self.assertEqual(command[command.index(flag) + 1], value, flag)
        self.assertIn("--keep-polytomies", command)

    def test_no_clock_rate_confidence_coalescent_or_covariation(self):
        command = self._build()
        for never_emitted in ("--clock-rate", "--confidence", "--coalescent", "--covariation",
                              "--stochastic-resolve", "--greedy-resolve", "--relax",
                              "--keep-root", "--plot-rtt", "--plot-tree"):
            self.assertNotIn(never_emitted, command)

    def test_polytomies_are_kept_unless_explicitly_disabled(self):
        self.assertNotIn("--keep-polytomies", self._build(keep_polytomies=False))

    def test_seed_is_fixed_for_reproducibility(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first[first.index("--rng-seed") + 1], "12345")


class TestParseMolecularClock(unittest.TestCase):
    def test_reads_rate_and_r_squared(self):
        clock = _parse_molecular_clock(SAMPLE_MOLECULAR_CLOCK)
        self.assertAlmostEqual(clock["clock_rate"], 5.274e-03)
        self.assertAlmostEqual(clock["r_squared"], 0.98)

    def test_reads_negative_rate(self):
        clock = _parse_molecular_clock(
            "Root-Tip-Regression:\n --rate:\t-1.200e-04\n --r^2:  \t0.01\n"
        )
        self.assertLess(clock["clock_rate"], 0)

    def test_reads_the_covariation_variant(self):
        clock = _parse_molecular_clock(
            "Root-Tip-Regression:\n --rate:\t4.089e-04 +/- 1.20e-05 (one std-dev)\n"
            " --chi^2:\t3.10\n --r^2:  \t0.94\n"
        )
        self.assertAlmostEqual(clock["clock_rate"], 4.089e-04)
        self.assertAlmostEqual(clock["r_squared"], 0.94)

    def test_missing_report_yields_none(self):
        clock = _parse_molecular_clock("")
        self.assertIsNone(clock["clock_rate"])
        self.assertIsNone(clock["r_squared"])


class TestParseClockFilterExcluded(unittest.TestCase):
    def test_reads_reported_outliers(self):
        excluded = _parse_clock_filter_excluded(OUTLIER_STDOUT)
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0]["accession_id"], "OQ100003")
        self.assertEqual(excluded[0]["input_date"], "2019.45")
        self.assertAlmostEqual(excluded[0]["apparent_date"], 2011.02)

    def test_no_outliers_reported(self):
        self.assertEqual(_parse_clock_filter_excluded("nothing to report"), [])


class TestReadTreeTipNames(unittest.TestCase):
    def test_reads_tip_labels_of_both_engines(self):
        # Internal support labels (FastTree numeric, IQ-TREE compound) are not tips.
        with tempfile.TemporaryDirectory() as tmp:
            for tree_text in (FASTTREE_TREE, IQTREE_TREE):
                tree = Path(tmp) / "tree.nwk"
                tree.write_text(tree_text)
                self.assertEqual(
                    read_tree_tip_names(tree),
                    {"OQ100001", "OQ100002", "OQ100003", "OQ100004", "OQ100005"},
                )


class TestRunTreetime(unittest.TestCase):
    def test_raises_when_alignment_missing(self):
        with self.assertRaises(FileNotFoundError):
            run_treetime("/nonexistent/aligned.fasta", "/nonexistent/tree.nwk", DATED_TIPS,
                         "/tmp/treetime", {})

    def test_raises_when_tree_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            alignment, _tree = _write_inputs(tmp)
            with self.assertRaises(FileNotFoundError):
                run_treetime(str(alignment), str(Path(tmp) / "absent.nwk"), DATED_TIPS,
                             str(Path(tmp) / "treetime"), {})

    def test_raises_without_dated_tips(self):
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)
            with self.assertRaises(ValueError):
                run_treetime(str(alignment), str(tree), {}, str(Path(tmp) / "treetime"), {})

    @patch("phylo_module.services.treetime_service.shutil.which", return_value=None)
    def test_raises_when_treetime_not_found(self, _which):
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)
            with self.assertRaises(FileNotFoundError) as ctx:
                run_treetime(str(alignment), str(tree), DATED_TIPS,
                             str(Path(tmp) / "treetime"), {})
            self.assertIn("TreeTime", str(ctx.exception))

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_successful_run_on_fasttree_tree(self, mock_run, _which):
        mock_run.side_effect = _fake_run()
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)
            method_dir = Path(tmp) / "treetime"

            result = run_treetime(str(alignment), str(tree), DATED_TIPS, str(method_dir), {})

            self.assertEqual(result["software"], "TreeTime")
            self.assertEqual(result["software_version"], "0.12.1")
            self.assertEqual(result["alignment_records"], 4)
            self.assertEqual(result["dated_tips"], 4)
            self.assertAlmostEqual(result["clock_rate"], 5.274e-03)
            self.assertAlmostEqual(result["r_squared"], 0.98)
            self.assertEqual(result["warnings"], [])
            self.assertTrue((method_dir / "timetree.nexus").is_file())
            self.assertTrue(result["timetree_nexus"].startswith("#NEXUS"))

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_successful_run_on_iqtree_tree_with_compound_support_labels(self, mock_run, _which):
        recorded = {}
        mock_run.side_effect = _fake_run(recorded_inputs=recorded)
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp, tree_text=IQTREE_TREE)

            result = run_treetime(str(alignment), str(tree), DATED_TIPS,
                                  str(Path(tmp) / "treetime"), {})

            self.assertEqual(result["alignment_records"], 4)
            self.assertEqual(recorded["tree"], set(DATED_TIPS))

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_identifiers_match_across_alignment_tree_and_dates(self, mock_run, _which):
        recorded = {}
        mock_run.side_effect = _fake_run(recorded_inputs=recorded)
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)

            run_treetime(str(alignment), str(tree), DATED_TIPS, str(Path(tmp) / "treetime"), {})

            self.assertEqual(recorded["alignment"], set(DATED_TIPS))
            self.assertEqual(recorded["tree"], set(DATED_TIPS))
            self.assertEqual(recorded["dates"], set(DATED_TIPS))
            self.assertEqual(recorded["dates_header"], "accession_id\tcollection_date")
            # Undated tip pruned from all inputs
            self.assertNotIn("OQ100005", recorded["alignment"] | recorded["tree"] | recorded["dates"])

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_dates_file_is_written_outside_outdir(self, mock_run, _which):
        # Avoid clash with TreeTime's own dates.tsv in --outdir
        recorded = {}
        mock_run.side_effect = _fake_run(recorded_inputs=recorded)
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)
            run_treetime(str(alignment), str(tree), DATED_TIPS, str(Path(tmp) / "treetime"), {})
            outdir = Path(_main_command(mock_run)[_main_command(mock_run).index("--outdir") + 1])
            self.assertNotEqual(recorded["dates_path"].parent, outdir)

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_original_alignment_and_tree_are_unchanged(self, mock_run, _which):
        mock_run.side_effect = _fake_run()
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)
            before = (_fingerprint(alignment), _fingerprint(tree))

            run_treetime(str(alignment), str(tree), DATED_TIPS, str(Path(tmp) / "treetime"), {})

            self.assertEqual((_fingerprint(alignment), _fingerprint(tree)), before)

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_only_the_canonical_timetree_is_retained(self, mock_run, _which):
        mock_run.side_effect = _fake_run()
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)
            method_dir = Path(tmp) / "treetime"

            run_treetime(str(alignment), str(tree), DATED_TIPS, str(method_dir), {})

            self.assertEqual(sorted(item.name for item in method_dir.iterdir()),
                             ["timetree.nexus"])

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_accession_labels_survive_verbatim_in_the_stored_nexus(self, mock_run, _which):
        mock_run.side_effect = _fake_run()
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)

            result = run_treetime(str(alignment), str(tree), DATED_TIPS,
                                  str(Path(tmp) / "treetime"), {})

            for accession_id in DATED_TIPS:
                self.assertIn(accession_id, result["timetree_nexus"])

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_persisted_values_carry_no_machine_specific_paths(self, mock_run, _which):
        mock_run.side_effect = _fake_run()
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)

            result = run_treetime(str(alignment), str(tree), DATED_TIPS,
                                  str(Path(tmp) / "treetime"), {})

            for argument in result["treetime_command"]:
                self.assertNotIn("/", argument)
            self.assertEqual(result["treetime_command"][0], "treetime")

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_temporal_outliers_are_reported(self, mock_run, _which):
        mock_run.side_effect = _fake_run(stdout=OUTLIER_STDOUT)
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)

            result = run_treetime(str(alignment), str(tree), DATED_TIPS,
                                  str(Path(tmp) / "treetime"), {})

            self.assertEqual([tip["accession_id"] for tip in result["clock_filter_excluded"]],
                             ["OQ100003"])

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_negative_clock_rate_is_reported_not_raised(self, mock_run, _which):
        mock_run.side_effect = _fake_run(
            clock_text="Root-Tip-Regression:\n --rate:\t-2.100e-04\n --r^2:  \t0.02\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)

            result = run_treetime(str(alignment), str(tree), DATED_TIPS,
                                  str(Path(tmp) / "treetime"), {})

            self.assertLess(result["clock_rate"], 0)

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_unreadable_clock_report_warns_without_failing(self, mock_run, _which):
        mock_run.side_effect = _fake_run(clock_text=None)
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)

            result = run_treetime(str(alignment), str(tree), DATED_TIPS,
                                  str(Path(tmp) / "treetime"), {})

            self.assertIsNone(result["clock_rate"])
            self.assertTrue(any("clock rate" in warning for warning in result["warnings"]))

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_nonzero_exit_fails(self, mock_run, _which):
        mock_run.side_effect = _fake_run(returncode=2)
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)
            with self.assertRaises(RuntimeError) as ctx:
                run_treetime(str(alignment), str(tree), DATED_TIPS,
                             str(Path(tmp) / "treetime"), {})
            self.assertIn("TreeTime failed", str(ctx.exception))

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_timeout_fails(self, mock_run, _which):
        mock_run.side_effect = _fake_run(timeout=True)
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)
            with self.assertRaises(RuntimeError) as ctx:
                run_treetime(str(alignment), str(tree), DATED_TIPS,
                             str(Path(tmp) / "treetime"), {"timeout": 1})
            self.assertIn("timed out", str(ctx.exception))

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_missing_timetree_fails(self, mock_run, _which):
        mock_run.side_effect = _fake_run(timetree_text=None)
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)
            with self.assertRaises(RuntimeError) as ctx:
                run_treetime(str(alignment), str(tree), DATED_TIPS,
                             str(Path(tmp) / "treetime"), {})
            self.assertIn("timetree.nexus", str(ctx.exception))

    @patch("phylo_module.services.treetime_service.shutil.which", return_value="/usr/bin/treetime")
    @patch("phylo_module.services.treetime_service.subprocess.run")
    def test_failure_leaves_the_substitution_tree_intact(self, mock_run, _which):
        mock_run.side_effect = _fake_run(returncode=2)
        with tempfile.TemporaryDirectory() as tmp:
            alignment, tree = _write_inputs(tmp)
            before = (_fingerprint(alignment), _fingerprint(tree))
            with self.assertRaises(RuntimeError):
                run_treetime(str(alignment), str(tree), DATED_TIPS,
                             str(Path(tmp) / "treetime"), {})
            self.assertEqual((_fingerprint(alignment), _fingerprint(tree)), before)


if __name__ == "__main__":
    unittest.main()
