"""Task 116. Proves tools/report_cadence_check.py's scan actually counts a
real trailing streak, names a real gap day, ignores a non-conforming
filename -- and, the real point, confirms the live, current
fencepost/REPORTS/ directory's honest numbers: a 3-day trailing streak, 5
tablets shipped total, and the one already-documented gap day
(2026-07-14, BUILDLOG.md's own 2026-07-14 13:14/14:10 notes) actually
named instead of only narrated in prose.
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


class RealReportsCase(unittest.TestCase):
    """The real point: the live checkout's actual fencepost/REPORTS/
    directory, counted for real -- not a fixture standing in for it."""

    def test_real_reports_dir_holds_the_true_streak_and_the_real_gap(self):
        result = rcc.compute_cadence(os.path.join(ROOT, "fencepost", "REPORTS"))
        self.assertEqual(result["total_shipped"], 5)
        self.assertEqual(result["most_recent_date"], "2026-07-17")
        self.assertEqual(result["current_streak"], 3)
        self.assertEqual(result["missing_dates"], ["2026-07-14"])


if __name__ == "__main__":
    unittest.main()
