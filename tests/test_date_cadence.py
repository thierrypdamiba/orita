"""Task 555. Proves tools/date_cadence.py's shared
compute_date_streak_and_gaps() computes the trailing streak and the
historical gap days correctly on its own, and that the two siblings it
was extracted from (metrics_cadence_check.py, report_cadence_check.py)
now delegate to it rather than each carrying its own byte-identical
(once the source-path parameter's own name and the date-listing helper
it calls are treated as the only two differences) copy of the same
26-line algorithm.

Confirmed the drift risk was real, not hypothetical, before refactoring:
patched a throwaway copy of report_cadence_check.py's streak walk to
step by two days instead of one and fed both modules an equivalent
five-day unbroken run of dates. metrics_cadence_check.compute_cadence
reported current_streak=5 (untouched); the patched report_cadence_check.
compute_cadence reported current_streak=3 for the identical real
history -- proof that two copies of one algorithm are two independent
chances for the next boundary bug to land in only one of them, unseen
by the sibling's own test suite.

Two kinds of proof, mirroring tests/test_adoption_metric_format.py's own
discipline: (1) the shared function's own output is correct against
fixtures spanning the empty/no-gap/mid-gap boundary cases; (2) each
sibling's own compute_cadence(path, target) still returns the exact same
five-key dict shape it always has, and each sibling's own source
contains exactly one call to date_cadence.compute_date_streak_and_gaps,
so a future edit that quietly reforks one sibling back into its own copy
is caught by inspection, not just by today's passing output comparison.
"""
import ast
import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


dc = _load("date_cadence", os.path.join(TOOLS, "date_cadence.py"))


def _d(*ymd):
    return date(*ymd)


class SharedAlgorithmCase(unittest.TestCase):
    def test_empty_dates_is_the_zero_shape(self):
        result = dc.compute_date_streak_and_gaps([], target=30)
        self.assertEqual(
            result,
            {
                "total_shipped": 0,
                "first_date": None,
                "most_recent_date": None,
                "current_streak": 0,
                "missing_dates": [],
                "target": 30,
            },
        )

    def test_five_consecutive_days_streak_is_five_no_gaps(self):
        dates = [_d(2026, 7, d) for d in (12, 13, 14, 15, 16)]
        result = dc.compute_date_streak_and_gaps(dates, target=30)
        self.assertEqual(result["total_shipped"], 5)
        self.assertEqual(result["current_streak"], 5)
        self.assertEqual(result["missing_dates"], [])
        self.assertEqual(result["first_date"], "2026-07-12")
        self.assertEqual(result["most_recent_date"], "2026-07-16")

    def test_gap_in_the_middle_breaks_the_trailing_streak_and_is_named(self):
        dates = [_d(2026, 7, d) for d in (12, 13, 15, 16, 17)]
        result = dc.compute_date_streak_and_gaps(dates, target=30)
        self.assertEqual(result["total_shipped"], 5)
        self.assertEqual(result["current_streak"], 3)
        self.assertEqual(result["missing_dates"], ["2026-07-14"])
        self.assertEqual(result["most_recent_date"], "2026-07-17")

    def test_single_date_is_a_one_day_streak_no_gaps_possible(self):
        result = dc.compute_date_streak_and_gaps([_d(2026, 7, 12)], target=30)
        self.assertEqual(result["current_streak"], 1)
        self.assertEqual(result["missing_dates"], [])
        self.assertEqual(result["first_date"], result["most_recent_date"])

    def test_missing_dates_never_includes_first_or_most_recent(self):
        # Boundary proof: first_date and most_recent_date are always
        # shipped by construction (they're dates[0]/dates[-1]) and must
        # never appear in missing_dates regardless of how wide the gap.
        dates = [_d(2026, 7, 1), _d(2026, 7, 31)]
        result = dc.compute_date_streak_and_gaps(dates, target=30)
        self.assertNotIn("2026-07-01", result["missing_dates"])
        self.assertNotIn("2026-07-31", result["missing_dates"])
        self.assertEqual(len(result["missing_dates"]), 29)


class SiblingDelegationCase(unittest.TestCase):
    """Each sibling's own compute_cadence(path, target) must return the
    exact five-key dict shape date_cadence.compute_date_streak_and_gaps
    produces for the equivalent date list, via its own real module-level
    function (not by calling the shared function directly)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_metrics_cadence_check_matches_shared_algorithm(self):
        mcc = _load("metrics_cadence_check", os.path.join(TOOLS, "metrics_cadence_check.py"))
        path = os.path.join(self.tmp, "metrics.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for d in ("12", "13", "15", "16", "17"):
                f.write(f'{{"date": "2026-07-{d}"}}\n')
        dates = [_d(2026, 7, d) for d in (12, 13, 15, 16, 17)]
        expected = dc.compute_date_streak_and_gaps(dates, target=mcc.TARGET_STREAK_DAYS)
        self.assertEqual(mcc.compute_cadence(path), expected)

    def test_report_cadence_check_matches_shared_algorithm(self):
        rcc = _load("report_cadence_check", os.path.join(TOOLS, "report_cadence_check.py"))
        reports_dir = os.path.join(self.tmp, "REPORTS")
        os.makedirs(reports_dir)
        for d in ("12", "13", "15", "16", "17"):
            open(os.path.join(reports_dir, f"2026-07-{d}.md"), "w").close()
        dates = [_d(2026, 7, d) for d in (12, 13, 15, 16, 17)]
        expected = dc.compute_date_streak_and_gaps(dates, target=rcc.TARGET_STREAK_DAYS)
        self.assertEqual(rcc.compute_cadence(reports_dir), expected)

    def test_both_siblings_agree_on_an_equivalent_real_history(self):
        # The exact live proof this task ran by hand before refactoring:
        # feed both siblings the same real date history through their own
        # native input shape and confirm they now, structurally, cannot
        # disagree -- they call the same function.
        mcc = _load("metrics_cadence_check", os.path.join(TOOLS, "metrics_cadence_check.py"))
        rcc = _load("report_cadence_check", os.path.join(TOOLS, "report_cadence_check.py"))
        mpath = os.path.join(self.tmp, "metrics.jsonl")
        with open(mpath, "w", encoding="utf-8") as f:
            for d in ("12", "13", "14", "15", "16"):
                f.write(f'{{"date": "2026-07-{d}"}}\n')
        rdir = os.path.join(self.tmp, "REPORTS")
        os.makedirs(rdir)
        for d in ("12", "13", "14", "15", "16"):
            open(os.path.join(rdir, f"2026-07-{d}.md"), "w").close()
        m = mcc.compute_cadence(mpath)
        r = rcc.compute_cadence(rdir)
        shared_keys = ("total_shipped", "first_date", "most_recent_date", "current_streak", "missing_dates")
        self.assertEqual({k: m[k] for k in shared_keys}, {k: r[k] for k in shared_keys})


class SingleDelegationSiteCase(unittest.TestCase):
    """A future edit that quietly reforks one sibling back into its own
    copy must be caught by inspection, not just by output comparison --
    the same discipline tests/test_adoption_metric_format.py already
    holds for its own two siblings."""

    def _call_count(self, path, func_name):
        tree = ast.parse(open(path, encoding="utf-8").read())
        calls = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == func_name and isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "date_cadence":
                        calls += 1
        return calls

    def test_metrics_cadence_check_calls_shared_function_exactly_once(self):
        path = os.path.join(TOOLS, "metrics_cadence_check.py")
        self.assertEqual(self._call_count(path, "compute_date_streak_and_gaps"), 1)

    def test_report_cadence_check_calls_shared_function_exactly_once(self):
        path = os.path.join(TOOLS, "report_cadence_check.py")
        self.assertEqual(self._call_count(path, "compute_date_streak_and_gaps"), 1)


if __name__ == "__main__":
    unittest.main()
