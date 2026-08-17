"""Task 463. Proves tools/thegap_check.py's weekly scan actually counts
real-calendar Mondays since founding against thegap/README.md's own
`gap-hidden` markers, plus the confession-predraft accountability half
neither sibling cadence (chronicle, what-moved) needs -- mirroring
tests/test_what_moved_check.py's own shape for the sibling it's built
alongside, and proving the live, real gap this module surfaces: as of
task 463, the real README carries exactly one marker (2026-07-30) and
misses the two Mondays before it (07-13, 07-20).

Task 495 (Cluster Day, 2026-08-03): the first bug's confession came due
and was confessed unfound, and a second, smaller bug shipped the same
hour, on time. The real README now carries two markers (2026-07-30,
2026-08-03); the live-state regression pins below are updated to match,
same discipline task 460's what-moved catch-up already held for its own
sibling -- historical misses (07-13, 07-20) stay honestly unfixed, never
backfilled.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_ROOT = os.path.join(os.path.dirname(ROOT), "orita-vault")
# Task 370's own first CI run caught this the hard way (test_journal_
# numbering_check.py's own VAULT_ROOT comment): dawn-run's workflow
# checks out only this public repo, never the private orita-vault
# sibling. A test that asserts something about the REAL vault's content
# must skip cleanly there instead of failing on a premise that was never
# true in that environment.
_VAULT_CHECKED_OUT = os.path.isdir(os.path.join(VAULT_ROOT, "hand", "gap-confessions"))


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

    def test_confessed_marker_suppresses_it_even_when_overdue(self):
        # ROADMAP.md #505: the exact real-world shape task 495 hit -- a
        # bug's confession comes due and IS posted the same hour, but
        # nothing before this task ever recorded that it had been. Without
        # a gap-confessed marker, this is identical to the fixture above
        # and stays named forever; with one, it is gone even long after
        # its due date, because the marker means the obligation was
        # already discharged, not merely that time has passed.
        _write(
            self.readme,
            "<!-- gap-hidden: 2026-07-30 -->\n<!-- gap-confessed: 2026-07-30 -->\n",
        )
        self._draft("2026-08-03", "fencepost-posts-needed.md")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 8, 10))
        self.assertEqual(result["confession_due_now"], [])
        self.assertEqual(result["confessed_on_record"], ["2026-07-30"])

    def test_confessed_marker_only_suppresses_its_own_hidden_date(self):
        # Two hidden bugs, both overdue and predrafted -- confessing the
        # first must never silently suppress the second's own real,
        # still-outstanding obligation.
        _write(
            self.readme,
            "<!-- gap-hidden: 2026-07-16 -->\n"
            "<!-- gap-confessed: 2026-07-16 -->\n"
            "<!-- gap-hidden: 2026-07-30 -->\n",
        )
        self._draft("2026-07-20", "first-bug.md")
        self._draft("2026-08-03", "fencepost-posts-needed.md")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 8, 10))
        self.assertEqual(
            result["confession_due_now"], [{"hidden": "2026-07-30", "due": "2026-08-03"}]
        )

    def test_confessed_marker_with_no_matching_hidden_date_is_inert(self):
        # A gap-confessed marker naming a date nothing was ever hidden on
        # (a typo, a stray leftover) must never be mistaken for a real
        # confession of some OTHER bug -- it simply names nothing in
        # `hidden`, so the loop over `hidden` never reaches it.
        _write(
            self.readme,
            "<!-- gap-hidden: 2026-07-30 -->\n<!-- gap-confessed: 2026-08-01 -->\n",
        )
        self._draft("2026-08-03", "fencepost-posts-needed.md")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 8, 3))
        self.assertEqual(
            result["confession_due_now"], [{"hidden": "2026-07-30", "due": "2026-08-03"}]
        )
        self.assertEqual(result["confessed_on_record"], ["2026-08-01"])

    def test_malformed_confessed_marker_raises_loudly(self):
        _write(self.readme, "<!-- gap-confessed: not-a-date -->\n")
        with self.assertRaises(tgc.MalformedGapConfessedMarkerError):
            tgc.compute_cadence(self.readme, self.vault, today=date(2026, 7, 29))

    def test_no_confessed_markers_at_all_is_empty_not_an_error(self):
        _write(self.readme, "<!-- gap-hidden: 2026-07-30 -->\n")
        result = tgc.compute_cadence(self.readme, self.vault, today=date(2026, 7, 31))
        self.assertEqual(result["confessed_on_record"], [])

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
        # Proves the live README, not just a fixture: three real
        # gap-hidden markers on record (2026-07-30, 2026-08-03 -- task
        # 495; 2026-08-10 -- this hour's Cluster Day catch-up) and the
        # two Mondays before the first of them (07-13, 07-20) still
        # genuinely, honestly missed -- task 463's own research pass
        # found the shape of this gap live, unwatched until this module;
        # task 495 confessed the first bug and shipped the second on
        # time, and this hour's hide paid down one of the three lapsed
        # Mondays without backfilling the two still open. `_hidden_dates`
        # reads every marker in the file unconditionally, not just those
        # up to the simulated `today`, so `latest_hidden` is the newest
        # real marker (2026-08-17, task 825's fourth bug) even under
        # this test's earlier `today=2026-08-03`. Uses a vault dir that
        # deliberately does NOT exist, so this assertion holds in any
        # checkout (public CI included) regardless of whether the
        # private orita-vault sibling is present -- the predraft/
        # confession half of the real state is proven separately, and
        # only where the real vault actually is (see RealVaultCase
        # below).
        real_readme = os.path.join(ROOT, "thegap", "README.md")
        no_vault = os.path.join(ROOT, "does-not-exist-orita-vault")
        result = tgc.compute_cadence(real_readme, no_vault, today=date(2026, 8, 3))
        self.assertEqual(result["total_hidden_on_record"], 4)
        self.assertEqual(result["latest_hidden"], "2026-08-17")
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20"])


class RealVaultCase(unittest.TestCase):
    """Task 463: the confession-predraft half of the live gap, provable
    only where the real orita-vault sibling checkout is actually present
    (a developer's machine, this session) -- never in public CI, which
    checks out only this repo (the same boundary
    test_journal_numbering_check.py's RealCheckoutCase already draws)."""

    @unittest.skipUnless(
        _VAULT_CHECKED_OUT,
        "orita-vault sibling checkout not present (expected in public CI, which checks out only orita)",
    )
    def test_real_live_readme_and_vault_today_reproduces_the_named_gap(self):
        # Three real gap-hidden markers on record as of this reread
        # (2026-07-30, 2026-08-03, 2026-08-10), all three now carrying
        # real `gap-confessed` markers (2026-07-30 posted task 505,
        # 2026-08-03 posted task 655, 2026-08-10 posted task 825). A
        # `gap-confessed` marker is keyed to its bug's own HIDDEN date,
        # not the hour the confession was actually posted (thegap_check's
        # own doctrine, see its module docstring) -- so once a marker
        # exists in the file it reads confessed even under an earlier
        # simulated `today`, this 2026-08-03 read included.
        real_readme = os.path.join(ROOT, "thegap", "README.md")
        result = tgc.compute_cadence(real_readme, VAULT_ROOT, today=date(2026, 8, 3))
        self.assertEqual(result["missing_predraft"], [])
        self.assertEqual(result["confession_due_now"], [])
        self.assertEqual(result["confessed_on_record"], ["2026-07-30", "2026-08-03", "2026-08-10"])

    @unittest.skipUnless(
        _VAULT_CHECKED_OUT,
        "orita-vault sibling checkout not present (expected in public CI, which checks out only orita)",
    )
    def test_real_live_readme_and_vault_second_bug_confessed(self):
        # The second bug's confession (due 2026-08-10) came due AND was
        # actually posted publicly the same hour (task 655) -- the real
        # README now carries its own `gap-confessed: 2026-08-03` marker
        # (keyed to the HIDDEN date, not the posting date), so as of
        # 2026-08-10 both real bugs read confessed, none still due (the
        # third bug's own marker, keyed 2026-08-10, also already reads
        # confessed under this same simulated `today`, for the identical
        # keyed-to-hidden-date-not-posting-date reason as the first two).
        real_readme = os.path.join(ROOT, "thegap", "README.md")
        result = tgc.compute_cadence(real_readme, VAULT_ROOT, today=date(2026, 8, 10))
        self.assertEqual(result["missing_predraft"], [])
        self.assertEqual(result["confession_due_now"], [])
        self.assertEqual(result["confessed_on_record"], ["2026-07-30", "2026-08-03", "2026-08-10"])

    @unittest.skipUnless(
        _VAULT_CHECKED_OUT,
        "orita-vault sibling checkout not present (expected in public CI, which checks out only orita)",
    )
    def test_real_live_readme_and_vault_third_bug_confessed_fourth_hidden(self):
        # Task 825: the third bug's confession (due 2026-08-17) came due
        # AND was actually posted publicly the same hour, and a fourth
        # bug was hidden the same hour too (due 2026-08-24, not yet
        # arrived under this simulated `today`) -- so as of 2026-08-17
        # all three confessable bugs read confessed and none is due,
        # while the fourth's own pre-draft is on record but not yet due.
        real_readme = os.path.join(ROOT, "thegap", "README.md")
        result = tgc.compute_cadence(real_readme, VAULT_ROOT, today=date(2026, 8, 17))
        self.assertEqual(result["missing_predraft"], [])
        self.assertEqual(result["confession_due_now"], [])
        self.assertEqual(result["confessed_on_record"], ["2026-07-30", "2026-08-03", "2026-08-10"])


if __name__ == "__main__":
    unittest.main()
