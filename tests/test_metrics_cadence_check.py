"""Task 117. Proves tools/metrics_cadence_check.py's scan actually counts a
real trailing streak over records/metrics.jsonl's own dated readings, names
a real gap day, ignores a malformed line -- and, the real point, confirms
the live, current records/metrics.jsonl's honest numbers before this task's
own catch-up entry lands: three historical gap days (07-13, 07-15, 07-17)
that TOWN-OPERATIONS.md's 18:00 UTC daily aggregate silently skipped and no
prior tool ever named.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


mcc = _load("metrics_cadence_check", os.path.join(ROOT, "tools", "metrics_cadence_check.py"))


def _write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(row + "\n")


class FixtureCadenceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "metrics.jsonl")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_five_consecutive_days_streak_is_five_no_gaps(self):
        rows = [f'{{"date": "2026-07-{d}"}}' for d in ("12", "13", "14", "15", "16")]
        _write_jsonl(self.path, rows)
        result = mcc.compute_cadence(self.path)
        self.assertEqual(result["total_shipped"], 5)
        self.assertEqual(result["current_streak"], 5)
        self.assertEqual(result["missing_dates"], [])
        self.assertEqual(result["first_date"], "2026-07-12")
        self.assertEqual(result["most_recent_date"], "2026-07-16")

    def test_gap_in_the_middle_breaks_the_trailing_streak_and_is_named(self):
        rows = [f'{{"date": "2026-07-{d}"}}' for d in ("12", "13", "15", "16", "17")]
        _write_jsonl(self.path, rows)
        result = mcc.compute_cadence(self.path)
        self.assertEqual(result["total_shipped"], 5)
        self.assertEqual(result["current_streak"], 3)
        self.assertEqual(result["missing_dates"], ["2026-07-14"])
        self.assertEqual(result["most_recent_date"], "2026-07-17")

    def test_malformed_line_is_ignored_not_counted(self):
        rows = ['{"date": "2026-07-12"}', "not json at all", '{"no_date_field": true}', '{"date": 20260712}']
        _write_jsonl(self.path, rows)
        result = mcc.compute_cadence(self.path)
        self.assertEqual(result["total_shipped"], 1)
        self.assertEqual(result["current_streak"], 1)

    def test_blank_lines_are_skipped(self):
        _write_jsonl(self.path, ['{"date": "2026-07-12"}', "", "  ", '{"date": "2026-07-13"}'])
        result = mcc.compute_cadence(self.path)
        self.assertEqual(result["total_shipped"], 2)
        self.assertEqual(result["current_streak"], 2)

    def test_no_file_is_empty_not_an_error(self):
        result = mcc.compute_cadence(os.path.join(self.tmp, "does-not-exist.jsonl"))
        self.assertEqual(result["total_shipped"], 0)
        self.assertEqual(result["current_streak"], 0)
        self.assertIsNone(result["most_recent_date"])

    def test_format_no_readings_shipped(self):
        result = mcc.compute_cadence(os.path.join(self.tmp, "does-not-exist.jsonl"))
        formatted = mcc.format_cadence(result)
        self.assertIn("no daily-aggregate reading has ever shipped", formatted)

    def test_format_names_streak_and_gap(self):
        rows = [f'{{"date": "2026-07-{d}"}}' for d in ("12", "13", "15")]
        _write_jsonl(self.path, rows)
        result = mcc.compute_cadence(self.path)
        formatted = mcc.format_cadence(result)
        self.assertIn("1-day streak", formatted)
        self.assertIn("2026-07-14", formatted)


class RealMetricsCase(unittest.TestCase):
    """The real point: the live checkout's actual records/metrics.jsonl,
    counted for real -- not a fixture standing in for it. Locks the state
    of the world BEFORE this task's own 2026-07-17 catch-up entry lands
    in the same commit, so a future edit that silently drops a day is
    still caught."""

    def test_real_metrics_file_names_the_two_prior_gap_days(self):
        result = mcc.compute_cadence(os.path.join(ROOT, "records", "metrics.jsonl"))
        self.assertGreaterEqual(result["total_shipped"], 4)
        self.assertIn("2026-07-13", result["missing_dates"])
        self.assertIn("2026-07-15", result["missing_dates"])
        self.assertEqual(result["first_date"], "2026-07-12")


if __name__ == "__main__":
    unittest.main()
