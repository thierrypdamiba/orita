"""Task 449. Proves tools/what_moved_check.py's weekly scan actually counts
real-calendar Mondays since founding against docs/what-moved.html's own
`what-moved-entry` markers -- mirroring tests/test_cluster_day_check.py's
own shape for the sibling cadence it's built alongside, and proving the
live, real gap this module surfaces: as of task 449, the real page carries
zero markers and misses every real Monday since founding.
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


wmc = _load("what_moved_check", os.path.join(ROOT, "tools", "what_moved_check.py"))


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class FixtureCadenceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.page = os.path.join(self.tmp, "what-moved.html")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_markers_at_all_misses_every_real_monday(self):
        # The real live shape docs/what-moved.html is in as of task 449:
        # founding-day placeholder content, zero what-moved-entry markers.
        _write(self.page, "<h1>what moved</h1><p>the town is one day old.</p>")
        result = wmc.compute_cadence(self.page, today=date(2026, 7, 29))
        self.assertEqual(result["total_entries_on_record"], 0)
        self.assertIsNone(result["latest_entry"])
        self.assertEqual(result["mondays_due"], ["2026-07-13", "2026-07-20", "2026-07-27"])
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])

    def test_founding_day_itself_owes_nothing(self):
        _write(self.page, "x")
        result = wmc.compute_cadence(self.page, today=date(2026, 7, 11))
        self.assertEqual(result["mondays_due"], [])
        self.assertEqual(result["missed_mondays"], [])

    def test_one_entry_inside_each_mondays_week_is_clean(self):
        _write(
            self.page,
            "<!-- what-moved-entry: 2026-07-14 -->\n"
            "<!-- what-moved-entry: 2026-07-21 -->\n",
        )
        # Two real Mondays owed by 07-22 (07-13, 07-20); an entry landing
        # anywhere inside each Monday's own calendar week (Mon-Sun) covers
        # it, not only the Monday's exact date.
        result = wmc.compute_cadence(self.page, today=date(2026, 7, 22))
        self.assertEqual(result["mondays_due"], ["2026-07-13", "2026-07-20"])
        self.assertEqual(result["total_entries_on_record"], 2)
        self.assertEqual(result["missed_mondays"], [])

    def test_partial_catch_up_names_only_the_still_missing_monday(self):
        _write(self.page, "<!-- what-moved-entry: 2026-07-14 -->\n")
        # Three Mondays owed (07-13, 07-20, 07-27), only the first week's
        # entry exists -- the tail (07-20, 07-27) is still missed.
        result = wmc.compute_cadence(self.page, today=date(2026, 7, 29))
        self.assertEqual(result["missed_mondays"], ["2026-07-20", "2026-07-27"])

    def test_latest_entry_is_the_most_recent_marker(self):
        _write(
            self.page,
            "<!-- what-moved-entry: 2026-07-14 -->\n"
            "<!-- what-moved-entry: 2026-07-28 -->\n"
            "<!-- what-moved-entry: 2026-07-21 -->\n",
        )
        result = wmc.compute_cadence(self.page, today=date(2026, 7, 29))
        self.assertEqual(result["latest_entry"], "2026-07-28")

    def test_no_page_at_all_is_empty_not_an_error(self):
        result = wmc.compute_cadence(os.path.join(self.tmp, "does-not-exist.html"), today=date(2026, 7, 29))
        self.assertEqual(result["total_entries_on_record"], 0)
        self.assertIsNone(result["latest_entry"])
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])

    def test_malformed_marker_date_raises_loudly(self):
        _write(self.page, "<!-- what-moved-entry: not-a-date -->\n")
        with self.assertRaises(wmc.MalformedEntryMarkerError):
            wmc.compute_cadence(self.page, today=date(2026, 7, 29))

    def test_format_cadence_clean(self):
        result = {
            "total_entries_on_record": 2,
            "latest_entry": "2026-07-28",
            "mondays_due": ["2026-07-13", "2026-07-20"],
            "missed_mondays": [],
            "today": "2026-07-29",
        }
        line = wmc.format_cadence(result)
        self.assertIn("current", line)
        self.assertIn("2 entry/entries", line)

    def test_format_cadence_lapsed(self):
        result = {
            "total_entries_on_record": 0,
            "latest_entry": None,
            "mondays_due": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "missed_mondays": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "today": "2026-07-29",
        }
        line = wmc.format_cadence(result)
        self.assertIn("3 Cluster Days lapsed", line)
        self.assertIn("2026-07-13, 2026-07-20, 2026-07-27", line)

    def test_real_live_page_today_reproduces_the_named_gap(self):
        # The actual real docs/what-moved.html this task found: zero
        # markers, three real Mondays lapsed as of 2026-07-29 (the day
        # before this test module's own fixed reference point elsewhere
        # in this suite). Proves the live page, not just a fixture.
        real_page = os.path.join(ROOT, "docs", "what-moved.html")
        result = wmc.compute_cadence(real_page, today=date(2026, 7, 29))
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])


if __name__ == "__main__":
    unittest.main()
