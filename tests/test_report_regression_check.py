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
import tempfile
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


def _sentence(count):
    return f"{count} milestone commit(s) since 2026-07-12 (matching ['fencepost', 'flagship', 'strategy']), none echoed in a post."


class PrecheckSealCase(unittest.TestCase):
    """Task 964. 2026-08-23's real incident: the hourly hand-dogfood
    ritual sealed that day's first entry at 250 (override-sourced), a
    real regression from 2026-08-22's sealed 272, six minutes before
    `seam-scan.yml`'s automatic cron overwrote it with the authoritative
    273. `compute_report_regression` caught it in CI -- but only after it
    was already committed. `precheck_seal` is the check moved BEFORE the
    write, on a candidate that isn't on disk yet."""

    def _fixture_dir(self, dated_texts):
        d = tempfile.TemporaryDirectory()
        for date, count in dated_texts:
            with open(os.path.join(d.name, f"{date}.md"), "w", encoding="utf-8") as f:
                f.write(_sentence(count))
        return d

    def test_new_day_lower_than_prior_sealed_day_is_flagged(self):
        with self._fixture_dir([("2026-08-21", 260), ("2026-08-22", 272)]) as reports_dir:
            result = src.precheck_seal(_sentence(250), "2026-08-23", reports_dir=reports_dir)
        self.assertFalse(result["clean"])
        self.assertEqual(result["regressions"][0]["from_date"], "2026-08-22")
        self.assertEqual(result["regressions"][0]["to_date"], "2026-08-23")
        self.assertEqual(result["regressions"][0]["from_count"], 272)
        self.assertEqual(result["regressions"][0]["to_count"], 250)

    def test_new_day_at_or_above_prior_sealed_day_is_clean(self):
        with self._fixture_dir([("2026-08-21", 260), ("2026-08-22", 272)]) as reports_dir:
            result = src.precheck_seal(_sentence(273), "2026-08-23", reports_dir=reports_dir)
        self.assertTrue(result["clean"])

    def test_reseal_of_an_already_sealed_day_compares_against_the_day_before_it_not_itself(self):
        """An intra-day reseal (candidate_date already has a file on disk)
        must replace that day's own entry, not double-count it against
        itself -- the candidate is judged against the PRIOR day only."""
        with self._fixture_dir([("2026-08-22", 272), ("2026-08-23", 250)]) as reports_dir:
            result = src.precheck_seal(_sentence(273), "2026-08-23", reports_dir=reports_dir)
        self.assertTrue(result["clean"])

    def test_seeded_exception_pair_still_passes_through_precheck(self):
        with self._fixture_dir([("2026-07-12", 13)]) as reports_dir:
            result = src.precheck_seal(_sentence(11), "2026-07-13", reports_dir=reports_dir)
        self.assertTrue(result["clean"])

    def test_candidate_with_no_milestone_sentence_is_clean(self):
        with self._fixture_dir([("2026-08-22", 272)]) as reports_dir:
            result = src.precheck_seal(
                "A different gap today, nothing to compare.", "2026-08-23", reports_dir=reports_dir
            )
        self.assertTrue(result["clean"])
        self.assertNotIn("regressions", result)

    def test_first_ever_report_has_nothing_to_regress_against(self):
        with self._fixture_dir([]) as reports_dir:
            result = src.precheck_seal(_sentence(1), "2026-07-12", reports_dir=reports_dir)
        self.assertTrue(result["clean"])

    def test_real_live_reports_dir_would_have_flagged_the_2026_08_23_incident(self):
        """Not a fixture -- runs `precheck_seal` against this checkout's
        own real `fencepost/REPORTS/` history with the actual candidate
        text 2026-08-23's transient bad seal used, proving this would have
        refused the write live, not just in a synthetic fixture."""
        result = src.precheck_seal(_sentence(250), "2026-08-23")
        self.assertFalse(result["clean"])
        self.assertEqual(result["regressions"][0]["to_count"], 250)


if __name__ == "__main__":
    unittest.main()
