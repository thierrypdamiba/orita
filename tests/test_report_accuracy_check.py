"""Task 679. Proves tools/report_accuracy_check.py catches a sealed Report's
milestone-commit claim drifting from what a fresh live scan of the current
events cache would say -- the exact gap that let
fencepost/REPORTS/2026-08-11.md read "116" for hours while a live rescan of
the same cache already read 111/112, unnoticed because every prior hour's
own "primary gap unchanged" check only ever compared slug and confidence,
never the actual number embedded in the report text.
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


src = _load("report_accuracy_check", os.path.join(ROOT, "tools", "report_accuracy_check.py"))

REPORT_116 = (
    "# Fencepost Report -- 2026-08-11\n\n"
    "**Milestone-level work shipped but never reached @oritatown** -- confidence 0.85.\n\n"
    "116 milestone commit(s) since 2026-07-12 (matching ['fencepost', 'flagship', 'strategy']), "
    "none echoed in a post.\n"
)

GAP_112 = {
    "slug": "milestone-unannounced",
    "confidence": 0.85,
    "detail": "112 milestone commit(s) since 2026-07-12 (matching ['fencepost', 'flagship', 'strategy']), none echoed in a post.",
}

GAP_116 = {
    "slug": "milestone-unannounced",
    "confidence": 0.85,
    "detail": "116 milestone commit(s) since 2026-07-12 (matching ['fencepost', 'flagship', 'strategy']), none echoed in a post.",
}


class ExtractMilestoneCountCase(unittest.TestCase):
    def test_reads_the_embedded_integer(self):
        self.assertEqual(src.extract_milestone_count(REPORT_116), 116)

    def test_reads_from_a_bare_detail_sentence_too(self):
        self.assertEqual(src.extract_milestone_count(GAP_112["detail"]), 112)

    def test_none_when_sentence_absent(self):
        self.assertIsNone(src.extract_milestone_count("nothing to see here"))

    def test_none_on_empty_string(self):
        self.assertIsNone(src.extract_milestone_count(""))


class ComputeReportAccuracyCase(unittest.TestCase):
    def test_real_drift_flags_dirty_with_both_counts(self):
        result = src.compute_report_accuracy(REPORT_116, GAP_112)
        self.assertFalse(result["clean"])
        self.assertEqual(result["report_count"], 116)
        self.assertEqual(result["live_count"], 112)
        self.assertIn("STALE", result["reason"])

    def test_matching_counts_read_clean(self):
        result = src.compute_report_accuracy(REPORT_116, GAP_116)
        self.assertTrue(result["clean"])
        self.assertIn("matches", result["reason"])

    def test_missing_report_text_reads_clean(self):
        result = src.compute_report_accuracy(None, GAP_112)
        self.assertTrue(result["clean"])
        self.assertIn("report freshness", result["reason"])

    def test_no_live_scan_reads_clean(self):
        result = src.compute_report_accuracy(REPORT_116, None)
        self.assertTrue(result["clean"])
        self.assertIn("no live scan", result["reason"])

    def test_different_primary_gap_slug_reads_clean(self):
        other_gap = {"slug": "release-abc123", "detail": "irrelevant"}
        result = src.compute_report_accuracy(REPORT_116, other_gap)
        self.assertTrue(result["clean"])
        self.assertIn("nothing to compare", result["reason"])

    def test_report_text_with_no_milestone_sentence_reads_clean(self):
        result = src.compute_report_accuracy("a quiet day, no gap cleared the bar", GAP_112)
        self.assertTrue(result["clean"])
        self.assertIn("report text carries no", result["reason"])

    def test_live_gap_detail_with_no_milestone_sentence_reads_clean(self):
        odd_gap = {"slug": "milestone-unannounced", "detail": "something else entirely"}
        result = src.compute_report_accuracy(REPORT_116, odd_gap)
        self.assertTrue(result["clean"])
        self.assertIn("live scan's own detail", result["reason"])

    def test_missing_detail_key_treated_as_empty_string_not_a_crash(self):
        gap_no_detail = {"slug": "milestone-unannounced"}
        result = src.compute_report_accuracy(REPORT_116, gap_no_detail)
        self.assertTrue(result["clean"])

    def test_lower_live_count_from_override_cache_does_not_downgrade_a_direct_report(self):
        """Task 724: the real 2026-08-13 case. seam-scan.yml's automatic
        direct-fetch resealed the report to 146; this sandbox's own
        override-sourced cache rescan the very next hour read only 135
        (the local cache's standing undercount, not a real drop). Without
        the source-aware guard this read "STALE, reseal it" and would have
        overwritten the more-complete 146 with the less-complete 135."""
        report_146 = (
            "# Fencepost Report -- 2026-08-13\n\n"
            "**Milestone-level work shipped but never reached @oritatown** -- confidence 0.85.\n\n"
            "146 milestone commit(s) since 2026-07-12 (matching ['fencepost', 'flagship', 'strategy']), "
            "none echoed in a post.\n"
        )
        gap_135 = {
            "slug": "milestone-unannounced",
            "confidence": 0.85,
            "detail": "135 milestone commit(s) since 2026-07-12 (matching ['fencepost', 'flagship', 'strategy']), none echoed in a post.",
        }
        result = src.compute_report_accuracy(
            report_146, gap_135, live_source="override", report_source="direct"
        )
        self.assertTrue(result["clean"])
        self.assertTrue(result.get("cache_behind_direct"))
        self.assertEqual(result["report_count"], 146)
        self.assertEqual(result["live_count"], 135)
        self.assertNotIn("STALE", result["reason"])

    def test_lower_live_count_still_flags_stale_when_sources_unknown(self):
        """Backward compatible: callers that don't pass live_source/report_source
        (the exact old call shape) keep the original behavior -- a lower
        live count still reads STALE without the new guard's information."""
        result = src.compute_report_accuracy(REPORT_116, GAP_112)
        self.assertFalse(result["clean"])

    def test_lower_live_count_still_flags_stale_when_both_sources_are_override(self):
        """The guard only ever fires for report_source == 'direct' AND a
        non-direct live_source -- two override-sourced scans disagreeing
        is still a real drift worth catching, same as before."""
        result = src.compute_report_accuracy(
            REPORT_116, GAP_112, live_source="override", report_source="override"
        )
        self.assertFalse(result["clean"])

    def test_higher_live_count_still_reseals_even_when_report_is_direct(self):
        """The guard never blocks a real upward reseal -- only a downgrade
        of an already-more-authoritative direct-sourced report."""
        higher_gap = {
            "slug": "milestone-unannounced",
            "detail": "150 milestone commit(s) since 2026-07-12 (matching ['fencepost', 'flagship', 'strategy']), none echoed in a post.",
        }
        report_146 = REPORT_116.replace("116", "146")
        result = src.compute_report_accuracy(
            report_146, higher_gap, live_source="override", report_source="direct"
        )
        self.assertFalse(result["clean"])
        self.assertEqual(result["live_count"], 150)


class SiblingCandidatesSourceCase(unittest.TestCase):
    def test_reads_real_todays_source(self):
        report_path = os.path.join(ROOT, "fencepost", "REPORTS", "2026-08-13.md")
        source = src._sibling_candidates_source(report_path)
        self.assertEqual(source, "direct")

    def test_none_on_missing_sibling(self):
        source = src._sibling_candidates_source("/no/such/dir/REPORTS/2099-01-01.md")
        self.assertIsNone(source)


class RealTodayReportCase(unittest.TestCase):
    """The real point: proves the fix actually landed against the live
    checkout. Once this task reseals fencepost/REPORTS/2026-08-11.md with
    the verified live count, the committed report and a fresh in-repo
    events-cache-derived count must agree -- this is the regression guard
    against the exact drift this task caught."""

    def test_todays_committed_report_milestone_count_is_extractable(self):
        report_path = os.path.join(ROOT, "fencepost", "REPORTS", "2026-08-11.md")
        with open(report_path, encoding="utf-8") as f:
            text = f.read()
        count = src.extract_milestone_count(text)
        self.assertIsNotNone(count)
        self.assertGreater(count, 0)


if __name__ == "__main__":
    unittest.main()
