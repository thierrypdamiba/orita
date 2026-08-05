"""Task 117. Proves tools/metrics_cadence_check.py's scan actually counts a
real trailing streak over records/metrics.jsonl's own dated readings, names
a real gap day, ignores a malformed line -- and, the real point, confirms
the live, current records/metrics.jsonl's honest numbers before this task's
own catch-up entry lands: three historical gap days (07-13, 07-15, 07-17)
that TOWN-OPERATIONS.md's 18:00 UTC daily aggregate silently skipped and no
prior tool ever named.

Task 549 adds `compute_metrics_freshness`/`format_metrics_freshness`: the
freshness half `compute_cadence` above structurally cannot hold, since its
own `missing_dates` walk only ever covers days strictly between the first
and most recent shipped reading -- a gap more recent than the last reading
(the cadence stalled RIGHT NOW) can never appear there. Mirrors
`tools/ritual_check.py`'s own `check_report_freshness` current/pending/
stale shape for the sibling `fencepost/REPORTS/` cadence.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

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

    def test_a_valid_but_non_dict_line_is_ignored_not_a_crash(self):
        # A line that parses cleanly as JSON but isn't an object (a bare
        # number, null, list, or stray string) is not caught by the
        # existing `except json.JSONDecodeError` -- .get() on it used to
        # raise an uncaught AttributeError instead of being skipped like
        # any other malformed line.
        rows = ['{"date": "2026-07-12"}', "5", "null", "[1, 2]", '"just a string"']
        _write_jsonl(self.path, rows)
        result = mcc.compute_cadence(self.path)
        self.assertEqual(result["total_shipped"], 1)
        self.assertEqual(result["current_streak"], 1)

    def test_read_dates_raises_nothing_on_a_non_dict_only_file(self):
        _write_jsonl(self.path, ["5"])
        self.assertEqual(mcc._read_dates(self.path), [])

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


class FixtureFreshnessCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "metrics.jsonl")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_current_when_todays_reading_exists(self):
        _write_jsonl(self.path, ['{"date": "2026-07-14"}'])
        now = datetime(2026, 7, 14, 20, 0, tzinfo=timezone.utc)
        result = mcc.compute_metrics_freshness(now, metrics_path=self.path)
        self.assertEqual(result["status"], "current")
        self.assertEqual(result["date"], "2026-07-14")

    def test_pending_when_only_yesterdays_reading_exists(self):
        _write_jsonl(self.path, ['{"date": "2026-07-13"}'])
        now = datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc)
        result = mcc.compute_metrics_freshness(now, metrics_path=self.path)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["fallback_date"], "2026-07-13")

    def test_stale_when_neither_reading_exists(self):
        _write_jsonl(self.path, ['{"date": "2026-07-10"}'])
        now = datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc)
        result = mcc.compute_metrics_freshness(now, metrics_path=self.path)
        self.assertEqual(result["status"], "stale")
        self.assertIsNone(result["fallback_date"])

    def test_stale_when_file_missing_entirely(self):
        now = datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc)
        result = mcc.compute_metrics_freshness(now, metrics_path=os.path.join(self.tmp, "nope.jsonl"))
        self.assertEqual(result["status"], "stale")

    def test_format_each_status(self):
        _write_jsonl(self.path, ['{"date": "2026-07-14"}'])
        now = datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc)
        current = mcc.format_metrics_freshness(mcc.compute_metrics_freshness(now, metrics_path=self.path))
        self.assertIn("current", current)
        stale = mcc.format_metrics_freshness(
            mcc.compute_metrics_freshness(now, metrics_path=os.path.join(self.tmp, "nope.jsonl"))
        )
        self.assertIn("STALE", stale)


class RealMetricsFreshnessCase(unittest.TestCase):
    """The real point: task 556's own daily-aggregate reading landed a real
    2026-08-05 entry in records/metrics.jsonl this hour, closing the
    staleness this same class asserted that morning (2026-08-04's 18:00
    UTC aggregate having been silently skipped). Locks that this really is
    what compute_metrics_freshness reports against the live checkout now --
    current, not stale, evaluated later the same day the entry landed."""

    def test_real_metrics_file_is_current_as_of_2026_08_05(self):
        now = datetime(2026, 8, 5, 19, 30, tzinfo=timezone.utc)
        result = mcc.compute_metrics_freshness(now, metrics_path=os.path.join(ROOT, "records", "metrics.jsonl"))
        self.assertEqual(result["status"], "current")


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
