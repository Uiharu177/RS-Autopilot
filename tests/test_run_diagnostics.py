import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from resonance.debug import run_diagnostics


class RunDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.runs_dir = Path(self.tempdir.name) / "runs"
        self.patchers = [
            patch.object(run_diagnostics, "RUNS_DIR", self.runs_dir),
            patch.object(run_diagnostics, "_active", None),
            patch.object(run_diagnostics, "_last", None),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.tempdir.cleanup()

    def test_completed_run_can_be_read_and_exported(self):
        run_diagnostics.start_trade_run(["A", "B"], 1)
        run_diagnostics.set_step("buy_goods", round_index=1, city="A")
        run_diagnostics.finish("completed")

        report = run_diagnostics.latest_run()
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["current_step"], "buy_goods")
        self.assertGreaterEqual(len(report["events"]), 3)
        self.assertNotIn("_started_perf", report)
        summary = Path(report["directory"]) / "summary.json"
        self.assertNotIn("_started_perf", summary.read_text(encoding="utf-8"))

        archive = run_diagnostics.export_latest_run()
        self.assertIsNotNone(archive)
        self.assertTrue(archive.is_file())

    def test_failure_captures_snapshot_without_masking_original_error(self):
        run_diagnostics.start_trade_run(["A", "B"], 1)
        failure = RuntimeError("expected test failure")
        with patch(
            "resonance.debug.snapshot.capture_debug_snapshot",
            return_value={"success": True, "screenshot": None, "ocr_file": None},
        ):
            run_diagnostics.finish("failed", error=failure, capture_snapshot=True)

        report = run_diagnostics.latest_run()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["failure"]["type"], "RuntimeError")
        self.assertTrue(report["snapshot"]["success"])


if __name__ == "__main__":
    unittest.main()
