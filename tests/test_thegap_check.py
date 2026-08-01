"""Task 463. Proves tools/thegap_check.py's weekly scan actually counts
real-calendar Mondays since founding against thegap/README.md's own
`gap-hidden` markers, plus the confession-predraft accountability half
neither sibling cadence (chronicle, what-moved) needs -- mirroring
tests/test_what_moved_check.py's own shape for the sibling it's built
alongside, and proving the live, real gap this module surfaces: as of
task 463, the real README carries exactly one marker (2026-07-30) and
misses the two Mondays before it (07-13, 07-20).
"""
import importlib.util
import os
import shutil
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


tgc = _load("thegap_check", os.path.join(ROOT, "tools", "thegap_check.py"))


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class FixtureCadenceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.readme = os.path.join(self.tmp, "thegap", "README.md")
        self.vault = os.path.join(self.tmp, "orita-vault")

    def _draft(self, due_iso, name="fixture-bug.md"):
        _write(os.path.join(self.vault, "hand", "gap-confessions", f"{due_iso}-{name}"), "x")

    def test_no_markers_at_all_misses_every_real_monday_and_has_no_predraft_debt(self):
        _write(self.readme, "# The Gap\n\nnothing hidden yet.\n")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 7, 29))
        self.assertEqual(result["total_hidden_on_record"], 0)
        self.assertIsNone(result["latest_hidden"])
        self.assertEqual(result["mondays_due"], ["2026-07-13", "2026-07-20", "2026-07-27"])
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])
        self.assertEqual(result["missing_predraft"], [])
        self.assertEqual(result["confession_due_now"], [])

    def test_founding_day_itself_owes_nothing(self):
        _write(self.readme, "x")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 7, 11))
        self.assertEqual(result["mondays_due"], [])
        self.assertEqual(result["missed_mondays"], [])

    def test_one_hide_inside_each_mondays_week_is_clean(self):
        _write(
            self.readme,
            "<!-- gap-hidden: 2026-07-14 -->\n<!-- gap-hidden: 2026-07-21 -->\n",
        )
        self._draft("2026-07-20")
        self._draft("2026-07-27")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 7, 22))
        self.assertEqual(result["mondays_due"], ["2026-07-13", "2026-07-20"])
        self.assertEqual(result["total_hidden_on_record"], 2)
        self.assertEqual(result["missed_mondays"], [])

    def test_partial_catch_up_names_only_the_still_missing_monday(self):
        _write(self.readme, "<!-- gap-hidden: 2026-07-14 -->\n")
        self._draft("2026-07-20")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 7, 29))
        self.assertEqual(result["missed_mondays"], ["2026-07-20", "2026-07-27"])

    def test_latest_hidden_is_the_most_recent_marker(self):
        _write(
            self.readme,
            "<!-- gap-hidden: 2026-07-14 -->\n"
            "<!-- gap-hidden: 2026-07-28 -->\n"
            "<!-- gap-hidden: 2026-07-21 -->\n",
        )
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 7, 29))
        self.assertEqual(result["latest_hidden"], "2026-07-28")

    def test_no_readme_at_all_is_empty_not_an_error(self):
        result = tgc.compute_cadence(
            os.path.join(self.tmp, "does-not-exist.md"), self.vault, today=date(2026, 7, 29)
        )
        self.assertEqual(result["total_hidden_on_record"], 0)
        self.assertIsNone(result["latest_hidden"])
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])

    def test_malformed_marker_date_raises_loudly(self):
        _write(self.readme, "<!-- gap-hidden: not-a-date -->\n")
        with self.assertRaises(tgc.MalformedGapHiddenMarkerError):
            tgc.compute_cadence(self.readme, self.vault, today=date(2026, 7, 29))

    def test_no_vault_dir_at_all_is_missing_predraft_not_an_error(self):
        # A checkout without orita-vault attached (or the vault dir simply
        # absent) must not crash -- it reads as "no draft on record,"
        # exactly like `journal_numbering_check.py`'s own absent-vault
        # handling for the identical class of gap.
        _write(self.readme, "<!-- gap-hidden: 2026-07-14 -->\n")
        result = tgc.compute_cadence(
            self.readme, os.path.join(self.tmp, "no-such-vault"), today=date(2026, 7, 15)
        )
        self.assertEqual(result["missing_predraft"], ["2026-07-14"])
        self.assertEqual(result["confession_due_now"], [])

    def test_missing_predraft_named_regardless_of_due_date(self):
        # Iron Rule: the draft must exist BEFORE the bug ships, not by
        # its due date -- a hide event one day old with no draft at all
        # is already a violation, not something that waits for its due
        # date to arrive first.
        _write(self.readme, "<!-- gap-hidden: 2026-07-30 -->\n")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 7, 31))
        self.assertEqual(result["missing_predraft"], ["2026-07-30"])
        self.assertEqual(result["confession_due_now"], [])

    def test_predrafted_but_not_yet_due_is_clean(self):
        _write(self.readme, "<!-- gap-hidden: 2026-07-30 -->\n")
        self._draft("2026-08-03", "fencepost-posts-needed.md")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 8, 1))
        self.assertEqual(result["missing_predraft"], [])
        self.assertEqual(result["confession_due_now"], [])

    def test_predrafted_and_due_today_is_named(self):
        _write(self.readme, "<!-- gap-hidden: 2026-07-30 -->\n")
        self._draft("2026-08-03", "fencepost-posts-needed.md")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 8, 3))
        self.assertEqual(
            result["confession_due_now"], [{"hidden": "2026-07-30", "due": "2026-08-03"}]
        )

    def test_predrafted_and_overdue_stays_named(self):
        _write(self.readme, "<!-- gap-hidden: 2026-07-30 -->\n")
        self._draft("2026-08-03", "fencepost-posts-needed.md")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 8, 10))
        self.assertEqual(
            result["confession_due_now"], [{"hidden": "2026-07-30", "due": "2026-08-03"}]
        )

    def test_format_cadence_clean(self):
        result = {
            "total_hidden_on_record": 2,
            "latest_hidden": "2026-07-28",
            "mondays_due": ["2026-07-13", "2026-07-20"],
            "missed_mondays": [],
            "missing_predraft": [],
            "confession_due_now": [],
            "today": "2026-07-29",
        }
        line = tgc.format_cadence(result)
        self.assertIn("current", line)
        self.assertIn("2 bug(s) hidden", line)

    def test_format_cadence_lapsed(self):
        result = {
            "total_hidden_on_record": 0,
            "latest_hidden": None,
            "mondays_due": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "missed_mondays": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "missing_predraft": [],
            "confession_due_now": [],
            "today": "2026-07-29",
        }
        line = tgc.format_cadence(result)
        self.assertIn("3 Cluster Days lapsed", line)
        self.assertIn("2026-07-13, 2026-07-20, 2026-07-27", line)

    def test_format_cadence_missing_predraft(self):
        result = {
            "total_hidden_on_record": 1,
            "latest_hidden": "2026-07-30",
            "mondays_due": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "missed_mondays": [],
            "missing_predraft": ["2026-07-30"],
            "confession_due_now": [],
            "today": "2026-07-31",
        }
        line = tgc.format_cadence(result)
        self.assertIn("missing pre-drafted confession for 2026-07-30", line)
        self.assertIn("Iron Rule violation", line)

    def test_format_cadence_confession_due_now(self):
        result = {
            "total_hidden_on_record": 1,
            "latest_hidden": "2026-07-30",
            "mondays_due": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "missed_mondays": [],
            "missing_predraft": [],
            "confession_due_now": [{"hidden": "2026-07-30", "due": "2026-08-03"}],
            "today": "2026-08-03",
        }
        line = tgc.format_cadence(result)
        self.assertIn("confession due now: 2026-07-30->2026-08-03", line)

    def test_real_live_readme_today_reproduces_the_named_gap(self):
        # Proves the live README + real vault, not just a fixture: one
        # real gap-hidden marker (2026-07-30), a real pre-drafted
        # confession on record (due 2026-08-03), not yet due as of
        # 2026-08-01, and the two Mondays before it (07-13, 07-20)
        # genuinely missed -- task 463's own research pass found this
        # live, unwatched until this module.
        real_readme = os.path.join(ROOT, "thegap", "README.md")
        real_vault = os.path.join(os.path.dirname(ROOT), "orita-vault")
        result = tgc.compute_cadence(real_readme, real_vault, today=date(2026, 8, 1))
        self.assertEqual(result["total_hidden_on_record"], 1)
        self.assertEqual(result["latest_hidden"], "2026-07-30")
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20"])
        self.assertEqual(result["missing_predraft"], [])
        self.assertEqual(result["confession_due_now"], [])


if __name__ == "__main__":
    unittest.main()
