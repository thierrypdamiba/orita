"""Task 773. Proves tools/report_regression_check.py catches a sealed
Report's "N milestone commit(s) since <fixed date>" running total reading
LOWER than the previous sealed tablet's own claim -- the exact continuity
break an Explore sweep of kwaku-ananse's narrative remit found live at TWO
points in fencepost/REPORTS/: 2026-07-12.md (13) -> 2026-07-13.md (11),
and 2026-07-13.md (11) -> 2026-07-18.md (4). Both sealed for over a month
with nothing in AUDIT.md or BUILDLOG.md explaining them.
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


src = _load("report_regression_check", os.path.join(ROOT, "tools", "report_regression_check.py"))


class ComputeReportRegressionCase(unittest.TestCase):
    def test_non_decreasing_sequence_reads_clean(self):
        counts = [("2026-07-20", 32), ("2026-07-21", 32), ("2026-07-22", 32), ("2026-07-23", 33)]
        result = src.compute_report_regression(counts, seeded_exceptions=frozenset())
        self.assertTrue(result["clean"])
        self.assertNotIn("regressions", result)

    def test_empty_sequence_reads_clean(self):
        result = src.compute_report_regression([], seeded_exceptions=frozenset())
        self.assertTrue(result["clean"])

    def test_single_entry_reads_clean(self):
        result = src.compute_report_regression([("2026-07-12", 13)], seeded_exceptions=frozenset())
        self.assertTrue(result["clean"])

    def test_unseeded_drop_flags_dirty(self):
        counts = [("2026-07-12", 13), ("2026-07-13", 11)]
        result = src.compute_report_regression(counts, seeded_exceptions=frozenset())
        self.assertFalse(result["clean"])
        self.assertEqual(len(result["regressions"]), 1)
        reg = result["regressions"][0]
        self.assertEqual(reg["from_date"], "2026-07-12")
        self.assertEqual(reg["from_count"], 13)
        self.assertEqual(reg["to_date"], "2026-07-13")
        self.assertEqual(reg["to_count"], 11)

    def test_seeded_drop_reads_clean(self):
        counts = [("2026-07-12", 13), ("2026-07-13", 11)]
        result = src.compute_report_regression(
            counts, seeded_exceptions=frozenset({("2026-07-12", "2026-07-13")})
        )
        self.assertTrue(result["clean"])
        self.assertIn("1 seeded historical exception", result["reason"])

    def test_seeding_only_covers_the_named_date_pair(self):
        """A seeded exception for one date pair must not blanket-exempt a
        different, unrelated drop -- each pair is checked on its own."""
        counts = [("2026-07-12", 13), ("2026-07-13", 11), ("2026-07-14", 5)]
        result = src.compute_report_regression(
            counts, seeded_exceptions=frozenset({("2026-07-12", "2026-07-13")})
        )
        self.assertFalse(result["clean"])
        self.assertEqual(len(result["regressions"]), 1)
        self.assertEqual(result["regressions"][0]["from_date"], "2026-07-13")

    def test_multiple_unseeded_drops_all_reported(self):
        counts = [("d1", 10), ("d2", 8), ("d3", 12), ("d4", 9)]
        result = src.compute_report_regression(counts, seeded_exceptions=frozenset())
        self.assertFalse(result["clean"])
        self.assertEqual(len(result["regressions"]), 2)

    def test_gap_days_without_a_milestone_entry_are_simply_absent(self):
        """Days like 2026-07-15/16/17 (a different gap that day, no
        milestone sentence at all) never enter `counts` in the first
        place -- read_report_counts skips them -- so comparison always
        happens between the two nearest entries that DO carry a count,
        never treated as an implicit drop to zero."""
        counts = [("2026-07-13", 11), ("2026-07-18", 4)]
        result = src.compute_report_regression(counts, seeded_exceptions=frozenset())
        self.assertFalse(result["clean"])
        self.assertEqual(result["regressions"][0]["from_date"], "2026-07-13")
        self.assertEqual(result["regressions"][0]["to_date"], "2026-07-18")

    def test_default_seeded_exceptions_cover_the_real_known_dips(self):
        result = src.compute_report_regression(
            [("2026-07-12", 13), ("2026-07-13", 11), ("2026-07-18", 4)]
        )
        self.assertTrue(result["clean"])


class ReadReportCountsCase(unittest.TestCase):
    def test_reads_real_sealed_reports_in_chronological_order(self):
        counts = src.read_report_counts()
        self.assertGreater(len(counts), 20)
        dates = [d for d, _ in counts]
        self.assertEqual(dates, sorted(dates))

    def test_known_first_two_counts_match_the_sealed_tablets(self):
        counts = dict(src.read_report_counts())
        self.assertEqual(counts["2026-07-12"], 13)
        self.assertEqual(counts["2026-07-13"], 11)

    def test_gap_days_absent_not_zero(self):
        counts = dict(src.read_report_counts())
        self.assertNotIn("2026-07-15", counts)

    def test_real_sealed_history_only_regresses_at_the_seeded_pairs(self):
        """The actual point: proves the live checkout's full sealed
        history has exactly the two known, documented dips (both from the
        town's first week) and nothing else -- the regression guard this
        task exists to stand up. A future hour that reseals a Report with
        an unexplained lower count fails this exact assertion."""
        result = src.compute_report_regression(src.read_report_counts())
        self.assertTrue(result["clean"], result.get("reason"))


if __name__ == "__main__":
    unittest.main()
