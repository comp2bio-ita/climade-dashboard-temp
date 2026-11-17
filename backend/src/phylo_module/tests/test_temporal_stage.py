import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phylo_module import config
from phylo_module.pipeline_phylo import _run_temporal_stage

# Tip count clears TREETIME_MIN_DATED_SEQUENCES
TWELVE_TIPS = [f"OQ10000{index}" if index < 10 else f"OQ1000{index}" for index in range(12)]
SAMPLE_TREE = "(" + ",".join(f"{tip}:0.1" for tip in TWELVE_TIPS) + ");\n"
ALL_DATED = {tip: f"20{10 + index:02d}-06-15" for index, tip in enumerate(TWELVE_TIPS)}

TIMETREE_NEXUS = "#NEXUS\nBegin Trees;\n Tree tree1=(" + ",".join(
    f"{tip}:1.0" for tip in TWELVE_TIPS
) + ");\nEnd;\n"


def _treetime_result(clock_rate=5.2e-3, clock_filter_excluded=None, warnings=None):
    return {
        "output_path": "/somewhere/treetime/timetree.nexus",
        "timetree_nexus": TIMETREE_NEXUS,
        "alignment_records": len(ALL_DATED),
        "dated_tips": len(ALL_DATED),
        "clock_rate": clock_rate,
        "r_squared": 0.87,
        "clock_filter_excluded": clock_filter_excluded or [],
        "software": "TreeTime",
        "software_version": "0.12.1",
        "return_code": 0,
        "execution_time_seconds": 1.5,
        "treetime_command": ["treetime", "--aln", "aligned.fasta"],
        "treetime_settings": {"clock_filter": 4, "seed": 12345},
        "warnings": warnings or [],
    }


def _inputs(dated_tips=None, excluded_tips=None):
    return {
        "settings": {"seed": 12345},
        "dated_tips": ALL_DATED if dated_tips is None else dated_tips,
        "excluded_tips": excluded_tips or [],
    }


class TemporalStageCase(unittest.TestCase):
    """TreeTime orchestration with service patched; no DB (job_id None)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tree_path = Path(self._tmp.name) / "tree.nwk"
        self.tree_path.write_text(SAMPLE_TREE)
        self.alignment_path = Path(self._tmp.name) / "aligned.fasta"
        self.alignment_path.write_text(">x\nACGT\n")
        self.treetime_dir = Path(self._tmp.name) / "treetime"
        self.events = []

    def tearDown(self):
        self._tmp.cleanup()

    def run_stage(self, treetime_inputs):
        return _run_temporal_stage(
            None, None, self.events, self.alignment_path, self.tree_path,
            self.treetime_dir, treetime_inputs,
        )

    def warning_messages(self):
        return [event["message"] for event in self.events if event["level"] == "warning"]


class TestTemporalGate(TemporalStageCase):
    @patch("phylo_module.pipeline_phylo.run_treetime")
    def test_too_few_dated_tips_skips_without_running_treetime(self, mock_run_treetime):
        few_dated = dict(list(ALL_DATED.items())[: config.TREETIME_MIN_DATED_SEQUENCES - 1])

        result = self.run_stage(_inputs(dated_tips=few_dated))

        mock_run_treetime.assert_not_called()
        self.assertIsNone(result["time_tree_nexus"])
        self.assertEqual(result["metadata"]["status"], "skipped")

    @patch("phylo_module.pipeline_phylo.run_treetime")
    def test_dated_fraction_is_measured_before_pruning(self, mock_run_treetime):
        # Fraction over whole tree tip count, not dated-only subset
        mock_run_treetime.return_value = _treetime_result()
        eleven_dated = dict(list(ALL_DATED.items())[:11])
        forty_tips = TWELVE_TIPS + [f"OQ2000{index:02d}" for index in range(28)]
        wide_tree = Path(self._tmp.name) / "wide.nwk"
        wide_tree.write_text("(" + ",".join(f"{tip}:0.1" for tip in forty_tips) + ");\n")

        cleared = _run_temporal_stage(
            None, None, [], self.alignment_path, self.tree_path, self.treetime_dir,
            _inputs(dated_tips=eleven_dated),
        )
        gated = _run_temporal_stage(
            None, None, self.events, self.alignment_path, wide_tree, self.treetime_dir,
            _inputs(dated_tips=eleven_dated),
        )

        self.assertNotEqual(cleared["metadata"]["status"], "skipped")
        self.assertEqual(gated["metadata"]["status"], "skipped")
        self.assertEqual(gated["metadata"]["tree_tips"], 40)
        self.assertEqual(gated["metadata"]["dated_tips"], 11)
        mock_run_treetime.assert_called_once()

    @patch("phylo_module.pipeline_phylo.run_treetime")
    def test_skip_reports_counts_fraction_and_thresholds(self, _mock_run_treetime):
        few_dated = dict(list(ALL_DATED.items())[:4])

        result = self.run_stage(_inputs(dated_tips=few_dated))

        metadata = result["metadata"]
        self.assertEqual(metadata["dated_tips"], 4)
        self.assertEqual(metadata["tree_tips"], 12)
        self.assertAlmostEqual(metadata["dated_fraction"], 4 / 12, places=3)
        self.assertEqual(metadata["min_dated_sequences"], config.TREETIME_MIN_DATED_SEQUENCES)
        self.assertEqual(metadata["min_dated_fraction"], config.TREETIME_MIN_DATED_FRACTION)
        self.assertIn(metadata["reason"], self.warning_messages())

    @patch("phylo_module.pipeline_phylo.run_treetime")
    def test_dates_for_accessions_absent_from_the_tree_are_ignored(self, mock_run_treetime):
        # Ghost accessions (fetch failed) must not inflate dated fraction
        mock_run_treetime.return_value = _treetime_result()
        with_ghosts = dict(ALL_DATED, GHOST0001="2020-01-01", GHOST0002="2020-02-01")

        result = self.run_stage(_inputs(dated_tips=with_ghosts))

        self.assertEqual(result["metadata"]["dated_tips"], 12)
        self.assertEqual(result["metadata"]["dated_fraction"], 1.0)
        self.assertEqual(set(mock_run_treetime.call_args.args[2]), set(ALL_DATED))

    @patch("phylo_module.pipeline_phylo.run_treetime")
    def test_undated_tips_are_reported_with_their_accessions(self, mock_run_treetime):
        mock_run_treetime.return_value = _treetime_result()
        excluded = [{"accession_id": "OQ100099", "reason": "no collection date"}]

        self.run_stage(_inputs(excluded_tips=excluded))

        self.assertTrue(any("OQ100099" in message for message in self.warning_messages()))


class TestTemporalSuccess(TemporalStageCase):
    @patch("phylo_module.pipeline_phylo.run_treetime")
    def test_stores_nexus_and_clock_metrics(self, mock_run_treetime):
        mock_run_treetime.return_value = _treetime_result()

        result = self.run_stage(_inputs())

        self.assertEqual(result["time_tree_nexus"], TIMETREE_NEXUS)
        metadata = result["metadata"]
        self.assertEqual(metadata["status"], "done")
        self.assertAlmostEqual(metadata["clock_rate"], 5.2e-3)
        self.assertAlmostEqual(metadata["r_squared"], 0.87)
        self.assertEqual(metadata["software_version"], "0.12.1")

    @patch("phylo_module.pipeline_phylo.run_treetime")
    def test_persisted_timetree_path_is_relative_to_the_run_bundle(self, mock_run_treetime):
        mock_run_treetime.return_value = _treetime_result()

        result = self.run_stage(_inputs())

        self.assertEqual(result["metadata"]["timetree_path"], "treetime/timetree.nexus")

    @patch("phylo_module.pipeline_phylo.run_treetime")
    def test_low_r_squared_is_recorded_but_never_gates(self, mock_run_treetime):
        weak_clock = _treetime_result()
        weak_clock["r_squared"] = 0.02
        mock_run_treetime.return_value = weak_clock

        result = self.run_stage(_inputs())

        self.assertEqual(result["metadata"]["status"], "done")
        self.assertIsNotNone(result["time_tree_nexus"])

    @patch("phylo_module.pipeline_phylo.run_treetime")
    def test_non_positive_clock_rate_warns_and_keeps_the_dated_tree(self, mock_run_treetime):
        mock_run_treetime.return_value = _treetime_result(clock_rate=-1.2e-4)

        result = self.run_stage(_inputs())

        self.assertEqual(result["metadata"]["status"], "done")
        self.assertTrue(any("non-positive clock rate" in message
                            for message in self.warning_messages()))

    @patch("phylo_module.pipeline_phylo.run_treetime")
    def test_temporal_outliers_are_reported_on_the_event_log(self, mock_run_treetime):
        mock_run_treetime.return_value = _treetime_result(
            clock_filter_excluded=[
                {"accession_id": "OQ100003", "input_date": "2013-06-15", "apparent_date": 2001.2}
            ]
        )

        result = self.run_stage(_inputs())

        self.assertEqual(len(result["metadata"]["clock_filter_excluded"]), 1)
        self.assertTrue(any("OQ100003" in message for message in self.warning_messages()))


class TestTemporalFailureIsNonFatal(TemporalStageCase):
    @patch("phylo_module.pipeline_phylo.run_treetime", side_effect=RuntimeError("TreeTime failed"))
    def test_failure_is_recorded_without_raising(self, _mock_run_treetime):
        result = self.run_stage(_inputs())

        self.assertIsNone(result["time_tree_nexus"])
        self.assertEqual(result["metadata"]["status"], "failed")
        self.assertIn("TreeTime failed", result["metadata"]["error"])

    @patch("phylo_module.pipeline_phylo.run_treetime",
           side_effect=FileNotFoundError("TreeTime executable not found"))
    def test_missing_executable_does_not_end_the_run(self, _mock_run_treetime):
        result = self.run_stage(_inputs())

        self.assertEqual(result["metadata"]["status"], "failed")
        # Non-fatal TreeTime failure → warning, not error
        self.assertEqual([event["level"] for event in self.events if event["level"] == "error"], [])
        self.assertTrue(any("phylogenetic tree is unaffected" in message
                            for message in self.warning_messages()))


if __name__ == "__main__":
    unittest.main()
