"""Task 116 (fixed by task 129). Proves tools/report_cadence_check.py's
scan actually counts a real trailing streak, names a real gap day,
ignores a non-conforming filename -- and, the real point, confirms the
live, current fencepost/REPORTS/ directory's honest numbers against an
INDEPENDENT scan written directly in this file, never a pinned literal.

Task 129: the original `RealReportsCase` pinned `compute_cadence()`'s
output on the real, live `fencepost/REPORTS/` directory to the literal
numbers true the hour it was written (5 shipped, most recent 07-17, a
3-day streak). The hourly ritual ships a new dated tablet almost every
day, so that pin was guaranteed to go stale and break `dawn-run` for
real the very next time the directory it claims to check actually grew
-- which is exactly what happened. Fixed the same way
`tools/wip_reclaim_check.py`'s own `RealCheckoutCase` (task 123)
already does it: assert against a live, independent recomputation of
the real directory's real state, never a snapshotted magic number.
"""
import glob
import importlib.util
import os
import re
import sys
import tempfile
import unittest
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


rcc = _load("report_cadence_check", os.path.join(ROOT, "tools", "report_cadence_check.py"))


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class FixtureCadenceCase(unittest.TestCase):
    def setUp(self):
        self.reports = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.reports, ignore_errors=True)

    def test_five_consecutive_days_streak_is_five_no_gaps(self):
        for d in ("2026-07-12", "2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16"):
            _write(os.path.join(self.reports, f"{d}.md"), "x")
        result = rcc.compute_cadence(self.reports)
        self.assertEqual(result["total_shipped"], 5)
        self.assertEqual(result["current_streak"], 5)
        self.assertEqual(result["missing_dates"], [])
        self.assertEqual(result["first_date"], "2026-07-12")
        self.assertEqual(result["most_recent_date"], "2026-07-16")

    def test_gap_in_the_middle_breaks_the_trailing_streak_and_is_named(self):
        for d in ("2026-07-12", "2026-07-13", "2026-07-15", "2026-07-16", "2026-07-17"):
            _write(os.path.join(self.reports, f"{d}.md"), "x")
        result = rcc.compute_cadence(self.reports)
        self.assertEqual(result["total_shipped"], 5)
        # trailing streak only counts back from most_recent_date (07-17)
        # to the first missing day -- 07-17, 16, 15, then 07-14 is missing.
        self.assertEqual(result["current_streak"], 3)
        self.assertEqual(result["missing_dates"], ["2026-07-14"])
        self.assertEqual(result["most_recent_date"], "2026-07-17")

    def test_non_conforming_filename_is_ignored_not_counted(self):
        _write(os.path.join(self.reports, "2026-07-12.md"), "x")
        _write(os.path.join(self.reports, "README.md"), "y")
        _write(os.path.join(self.reports, "notes.txt"), "z")
        result = rcc.compute_cadence(self.reports)
        self.assertEqual(result["total_shipped"], 1)
        self.assertEqual(result["current_streak"], 1)

    def test_no_reports_dir_is_empty_not_an_error(self):
        result = rcc.compute_cadence(os.path.join(self.reports, "does-not-exist"))
        self.assertEqual(result["total_shipped"], 0)
        self.assertEqual(result["current_streak"], 0)
        self.assertIsNone(result["most_recent_date"])

    def test_format_no_reports_shipped(self):
        result = rcc.compute_cadence(os.path.join(self.reports, "does-not-exist"))
        formatted = rcc.format_cadence(result)
        self.assertIn("no Fencepost Report has ever shipped", formatted)

    def test_format_names_streak_and_gap(self):
        for d in ("2026-07-12", "2026-07-13", "2026-07-15"):
            _write(os.path.join(self.reports, f"{d}.md"), "x")
        result = rcc.compute_cadence(self.reports)
        formatted = rcc.format_cadence(result)
        self.assertIn("1-day streak", formatted)
        self.assertIn("2026-07-14", formatted)


def _independent_scan(reports_dir):
    """Reimplements the counting from scratch, deliberately not calling
    anything in report_cadence_check -- so this stays a real check of
    the module's correctness against real data, not a tautology, and
    never goes stale as the directory grows (task 129)."""
    name_re = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")
    dates = []
    for path in glob.glob(os.path.join(reports_dir, "*.md")):
        m = name_re.match(os.path.basename(path))
        if not m:
            continue
        try:
            dates.append(date(*(int(g) for g in m.groups())))
        except ValueError:
            continue
    dates = sorted(set(dates))
    streak = 0
    cursor = dates[-1]
    shipped = set(dates)
    while cursor in shipped:
        streak += 1
        cursor -= timedelta(days=1)
    missing = []
    cursor = dates[0] + timedelta(days=1)
    while cursor < dates[-1]:
        if cursor not in shipped:
            missing.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return {
        "total_shipped": len(dates),
        "most_recent_date": dates[-1].isoformat(),
        "current_streak": streak,
        "missing_dates": missing,
    }


class RealReportsCase(unittest.TestCase):
    """The real point: the live checkout's actual fencepost/REPORTS/
    directory, counted for real -- not a fixture standing in for it, and
    not pinned to a snapshot the ritual's own daily work will outdate
    (task 129: the directory grows, so the expectation must be computed
    live too, independently of the module under test)."""

    def test_real_reports_dir_holds_the_true_streak_and_the_real_gap(self):
        reports_dir = os.path.join(ROOT, "fencepost", "REPORTS")
        expected = _independent_scan(reports_dir)
        result = rcc.compute_cadence(reports_dir)
        self.assertEqual(result["total_shipped"], expected["total_shipped"])
        self.assertEqual(result["most_recent_date"], expected["most_recent_date"])
        self.assertEqual(result["current_streak"], expected["current_streak"])
        self.assertEqual(result["missing_dates"], expected["missing_dates"])
        # 2026-07-14 is a real, permanent, already-documented historical
        # gap (BUILDLOG.md's 2026-07-14 13:14/14:10 notes) -- it can
        # never be un-missed, so it must always appear here regardless
        # of how many more tablets ship after it.
        self.assertIn("2026-07-14", result["missing_dates"])


if __name__ == "__main__":
    unittest.main()
