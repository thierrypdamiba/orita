"""Task 780. Proves tools/story_so_far_check.py's weekly scan actually
counts real-calendar Mondays since founding against docs/story-so-far.md's
own `story-so-far-rewrite` markers -- mirroring tests/test_what_moved_check.py's
own shape for the sibling cadence it's built alongside, and proving the
live, real gap this module surfaces: before task 780, the doc carried zero
markers despite genuinely going stale (still claiming "nineteen recipes"
while the live repo had reached 80) with no sensor positioned to catch it,
the fifth and last of TOWN-OPERATIONS.md's five weekly Cluster Day
obligations to get one (`cluster_day_check.py`/`what_moved_check.py`/
`thegap_check.py`/`nyx_traffic_check.py` already covered the other four).
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ssc = _load("story_so_far_check", os.path.join(ROOT, "tools", "story_so_far_check.py"))


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class FixtureCadenceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.doc = os.path.join(self.tmp, "story-so-far.md")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_markers_at_all_misses_every_real_monday(self):
        _write(self.doc, "# The Story So Far\n\nSome prose.\n")
        result = ssc.compute_cadence(self.doc, today=date(2026, 7, 29))
        self.assertEqual(result["total_entries_on_record"], 0)
        self.assertIsNone(result["latest_entry"])
        self.assertEqual(result["mondays_due"], ["2026-07-13", "2026-07-20", "2026-07-27"])
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])

    def test_founding_day_itself_owes_nothing(self):
        _write(self.doc, "x")
        result = ssc.compute_cadence(self.doc, today=date(2026, 7, 11))
        self.assertEqual(result["mondays_due"], [])
        self.assertEqual(result["missed_mondays"], [])

    def test_one_marker_inside_each_mondays_week_is_clean(self):
        _write(
            self.doc,
            "*story-so-far-rewrite: 2026-07-14*\n"
            "*story-so-far-rewrite: 2026-07-21*\n",
        )
        result = ssc.compute_cadence(self.doc, today=date(2026, 7, 22))
        self.assertEqual(result["mondays_due"], ["2026-07-13", "2026-07-20"])
        self.assertEqual(result["total_entries_on_record"], 2)
        self.assertEqual(result["missed_mondays"], [])

    def test_partial_catch_up_names_only_the_still_missing_monday(self):
        _write(self.doc, "*story-so-far-rewrite: 2026-07-14*\n")
        result = ssc.compute_cadence(self.doc, today=date(2026, 7, 29))
        self.assertEqual(result["missed_mondays"], ["2026-07-20", "2026-07-27"])

    def test_latest_entry_is_the_most_recent_marker(self):
        _write(
            self.doc,
            "*story-so-far-rewrite: 2026-07-14*\n"
            "*story-so-far-rewrite: 2026-07-28*\n"
            "*story-so-far-rewrite: 2026-07-21*\n",
        )
        result = ssc.compute_cadence(self.doc, today=date(2026, 7, 29))
        self.assertEqual(result["latest_entry"], "2026-07-28")

    def test_no_doc_at_all_is_empty_not_an_error(self):
        result = ssc.compute_cadence(os.path.join(self.tmp, "does-not-exist.md"), today=date(2026, 7, 29))
        self.assertEqual(result["total_entries_on_record"], 0)
        self.assertIsNone(result["latest_entry"])
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])

    def test_malformed_marker_date_raises_loudly(self):
        _write(self.doc, "*story-so-far-rewrite: not-a-date*\n")
        with self.assertRaises(ssc.MalformedRewriteMarkerError):
            ssc.compute_cadence(self.doc, today=date(2026, 7, 29))

    def test_marker_line_is_not_counted_as_body_prose(self):
        # The whole reason this module's marker is a `*...*` line, not an
        # HTML comment like what_moved_check's: tests/test_story_so_far_
        # doctrine.py's own _body_word_count skips every line starting
        # with `*` (the same convention the footer itself already uses),
        # so a rewrite marker must never budget against the 287-word cap.
        sys.path.insert(0, os.path.join(ROOT, "tests"))
        import test_story_so_far_doctrine as doctrine

        body_without_marker = "Some real prose here, four words.\n"
        body_with_marker = body_without_marker + "*story-so-far-rewrite: 2026-08-15*\n"
        self.assertEqual(
            doctrine._body_word_count(body_without_marker),
            doctrine._body_word_count(body_with_marker),
        )

    def test_format_cadence_clean(self):
        result = {
            "total_entries_on_record": 2,
            "latest_entry": "2026-07-28",
            "mondays_due": ["2026-07-13", "2026-07-20"],
            "missed_mondays": [],
            "today": "2026-07-29",
        }
        line = ssc.format_cadence(result)
        self.assertIn("current", line)
        self.assertIn("2 rewrite(s)", line)

    def test_format_cadence_lapsed(self):
        result = {
            "total_entries_on_record": 0,
            "latest_entry": None,
            "mondays_due": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "missed_mondays": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "today": "2026-07-29",
        }
        line = ssc.format_cadence(result)
        self.assertIn("3 Cluster Days lapsed", line)
        self.assertIn("2026-07-13, 2026-07-20, 2026-07-27", line)

    def test_format_cadence_lapsed_with_entries_on_record(self):
        result = {
            "total_entries_on_record": 1,
            "latest_entry": "2026-08-01",
            "mondays_due": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "missed_mondays": ["2026-07-13", "2026-07-20"],
            "today": "2026-08-02",
        }
        line = ssc.format_cadence(result)
        self.assertNotIn("never carried a rewrite marker", line)
        self.assertIn("last marked rewritten 2026-08-01", line)
        self.assertIn("2 Cluster Days lapsed", line)

    def test_real_live_doc_today_carries_its_own_first_marker(self):
        # Task 780 both rewrote docs/story-so-far.md's content AND landed
        # its own first `story-so-far-rewrite: 2026-08-15` marker in the
        # same commit -- proving the live doc, not just a fixture.
        # 2026-08-15 (a Saturday) falls inside the calendar week of Monday
        # 2026-08-10, which is the most recent Monday due as of today --
        # so that week is covered. Every earlier Monday back to founding
        # is genuinely NOT backfilled (no rewrite actually happened those
        # weeks), named honestly rather than silently absorbed, same
        # discipline test_what_moved_check's own 07-13/07-20 gap holds.
        real_doc = os.path.join(ROOT, "docs", "story-so-far.md")
        result = ssc.compute_cadence(real_doc, today=date(2026, 8, 15))
        self.assertIn("2026-08-10", result["mondays_due"])
        self.assertNotIn("2026-08-10", result["missed_mondays"])


if __name__ == "__main__":
    unittest.main()
