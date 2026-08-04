"""Task 387 (extended task 406). Proves tools/cluster_day_check.py's weekly
scan actually counts real-calendar Mondays since founding, names a real
lapsed Monday, ignores a non-conforming chronicle filename, and treats
episode-001 (the founding-day release, week zero) as satisfying no Monday
at all -- the exact distinction orita-vault/hand/skipped.md's 2026-07-27
hand-count needed and this module has to get right or it under-counts the
gap it exists to name.

Task 406 adds coverage for the `cluster-day-covers` marker: a catch-up
episode that genuinely narrates more than one lapsed Monday (like the real
`chronicle/002-eighteen-days.md`) can now say so explicitly instead of
being permanently under-credited by the one-Monday-in-sequence fallback.
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


cdc = _load("cluster_day_check", os.path.join(ROOT, "tools", "cluster_day_check.py"))


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class FixtureCadenceCase(unittest.TestCase):
    def setUp(self):
        self.chronicle = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.chronicle, ignore_errors=True)

    def test_only_founding_episode_on_record_misses_every_real_monday(self):
        # The real live shape this repo is in as of task 387: episode-000
        # (casting prequel) and episode-001 (founding, a Saturday) exist;
        # three real Mondays have passed since with no episode-002.
        _write(os.path.join(self.chronicle, "000-the-casting.md"), "x")
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))
        self.assertEqual(result["total_episodes_on_record"], 2)
        self.assertEqual(result["cluster_day_episodes_shipped"], 0)
        self.assertEqual(result["mondays_due"], ["2026-07-13", "2026-07-20", "2026-07-27"])
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])

    def test_founding_day_itself_owes_nothing(self):
        # The day of the founding release (a Saturday) and the days before
        # the first real Monday are not yet in violation of anything.
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 11))
        self.assertEqual(result["mondays_due"], [])
        self.assertEqual(result["missed_mondays"], [])

    def test_one_cluster_day_episode_per_monday_is_clean(self):
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        _write(os.path.join(self.chronicle, "002-something.md"), "x")
        _write(os.path.join(self.chronicle, "003-something-else.md"), "x")
        # Only two real Mondays have passed (07-13, 07-20) by 07-22.
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 22))
        self.assertEqual(result["mondays_due"], ["2026-07-13", "2026-07-20"])
        self.assertEqual(result["cluster_day_episodes_shipped"], 2)
        self.assertEqual(result["missed_mondays"], [])

    def test_partial_catch_up_names_only_the_still_missing_monday(self):
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        _write(os.path.join(self.chronicle, "002-something.md"), "x")
        # Three Mondays owed (07-13, 07-20, 07-27), only one Cluster Day
        # episode shipped -- the tail (07-20, 07-27) is still missed.
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))
        self.assertEqual(result["missed_mondays"], ["2026-07-20", "2026-07-27"])

    def test_non_conforming_filename_is_ignored_not_counted(self):
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        _write(os.path.join(self.chronicle, "README.md"), "y")
        _write(os.path.join(self.chronicle, "notes.txt"), "z")
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 13))
        self.assertEqual(result["total_episodes_on_record"], 1)

    def test_no_chronicle_dir_is_empty_not_an_error(self):
        result = cdc.compute_cadence(os.path.join(self.chronicle, "does-not-exist"), today=date(2026, 7, 29))
        self.assertEqual(result["total_episodes_on_record"], 0)
        self.assertEqual(result["cluster_day_episodes_shipped"], 0)
        self.assertIsNone(result["latest_episode"])

    def test_format_names_lapsed_mondays(self):
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))
        formatted = cdc.format_cadence(result)
        self.assertIn("3 Cluster Days lapsed", formatted)
        self.assertIn("2026-07-13", formatted)
        self.assertIn("2026-07-20", formatted)
        self.assertIn("2026-07-27", formatted)

    def test_format_clean_when_nothing_missed(self):
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 11))
        formatted = cdc.format_cadence(result)
        self.assertIn("cluster day: current", formatted)
        self.assertNotIn("lapsed", formatted)


class CoversMarkerCase(unittest.TestCase):
    """Task 406: a chronicle episode can explicitly declare which real
    Mondays it covers, rather than being pinned to the one-Monday-in-
    sequence fallback."""

    def setUp(self):
        self.chronicle = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.chronicle, ignore_errors=True)

    def test_marked_episode_covers_every_date_it_declares(self):
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        _write(
            os.path.join(self.chronicle, "002-catch-up.md"),
            "# Ep 2\n\n<!-- cluster-day-covers: 2026-07-13, 2026-07-20, 2026-07-27 -->\n\ntext",
        )
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))
        self.assertEqual(result["cluster_day_episodes_shipped"], 1)
        self.assertEqual(result["missed_mondays"], [])

    def test_marked_episode_only_covers_what_it_declares_not_more(self):
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        _write(
            os.path.join(self.chronicle, "002-partial.md"),
            "<!-- cluster-day-covers: 2026-07-13 -->\ntext",
        )
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))
        self.assertEqual(result["missed_mondays"], ["2026-07-20", "2026-07-27"])

    def test_markerless_episode_still_uses_old_sequential_fallback(self):
        # Full backward compatibility: no marker anywhere behaves exactly
        # like the pre-406 module.
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        _write(os.path.join(self.chronicle, "002-something.md"), "x")
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))
        self.assertEqual(result["missed_mondays"], ["2026-07-20", "2026-07-27"])

    def test_mix_of_marked_and_markerless_episodes(self):
        _write(os.path.join(self.chronicle, "001-the-founding.md"), "x")
        _write(
            os.path.join(self.chronicle, "002-catch-up.md"),
            "<!-- cluster-day-covers: 2026-07-13, 2026-07-20 -->\ntext",
        )
        _write(os.path.join(self.chronicle, "003-next-week.md"), "x")  # no marker
        result = cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))
        # 002 explicitly covers 07-13/07-20; 003 (markerless) falls back to
        # claiming the earliest still-uncovered Monday, 07-27.
        self.assertEqual(result["missed_mondays"], [])

    def test_marker_naming_a_non_monday_is_malformed(self):
        _write(
            os.path.join(self.chronicle, "002-bad.md"),
            "<!-- cluster-day-covers: 2026-07-14 -->\ntext",  # a Tuesday
        )
        with self.assertRaises(cdc.MalformedCoversMarkerError):
            cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))

    def test_marker_naming_a_pre_founding_date_is_malformed(self):
        _write(
            os.path.join(self.chronicle, "002-bad.md"),
            "<!-- cluster-day-covers: 2026-07-06 -->\ntext",
        )
        with self.assertRaises(cdc.MalformedCoversMarkerError):
            cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))

    def test_marker_with_non_ascending_dates_is_malformed(self):
        _write(
            os.path.join(self.chronicle, "002-bad.md"),
            "<!-- cluster-day-covers: 2026-07-20, 2026-07-13 -->\ntext",
        )
        with self.assertRaises(cdc.MalformedCoversMarkerError):
            cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))

    def test_marker_with_duplicate_dates_is_malformed(self):
        _write(
            os.path.join(self.chronicle, "002-bad.md"),
            "<!-- cluster-day-covers: 2026-07-13, 2026-07-13 -->\ntext",
        )
        with self.assertRaises(cdc.MalformedCoversMarkerError):
            cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))

    def test_malformed_marker_names_the_file_in_its_message(self):
        path = os.path.join(self.chronicle, "002-bad.md")
        _write(path, "<!-- cluster-day-covers: not-a-date -->\ntext")
        with self.assertRaises(cdc.MalformedCoversMarkerError) as ctx:
            cdc.compute_cadence(self.chronicle, today=date(2026, 7, 29))
        self.assertIn("002-bad.md", str(ctx.exception))

    def test_marker_is_invisible_to_a_markdown_renderer(self):
        # It's an HTML comment -- the whole point is that it never shows
        # up in the rendered episode a mortal reads.
        _write(
            os.path.join(self.chronicle, "002-catch-up.md"),
            "<!-- cluster-day-covers: 2026-07-13 -->\ntext",
        )
        declared = cdc._covers_marker(os.path.join(self.chronicle, "002-catch-up.md"))
        self.assertEqual(declared, [date(2026, 7, 13)])


class RealChronicleCase(unittest.TestCase):
    """Confirms the module's default directory reads the real, live
    chronicle/ dir and reproduces orita-vault/hand/skipped.md's own
    2026-07-27 hand count -- not a duplicated hand-picked number, an
    independent recomputation of the same real files."""

    def test_real_chronicle_dir_matches_the_hand_counted_gap(self):
        # episode-002 ("Eighteen Days") shipped task 391 and, since task
        # 406, carries an explicit cluster-day-covers marker naming all
        # three Mondays (07-13, 07-20, 07-27) it genuinely narrates in its
        # own text -- so the real chronicle dir now reads clean, not
        # under-credited by the one-Monday-in-sequence fallback.
        #
        # Task 500 (kwaku-ananse): this test reads the live chronicle/
        # directory, not a frozen copy of it -- passing a frozen `today`
        # pins the Monday-cadence math, but `total_episodes_on_record` and
        # `cluster_day_episodes_shipped` still count whatever files
        # actually exist on disk right now, regardless of `today`. The
        # exact bug Nisaba's journal 0180 named ("the test I bolted to
        # it... stopped being true the moment the world changed") recurred
        # here the moment episode-003 ("Right On Time") shipped: the count
        # was 3 when this test was last touched, it is 4 now that a fourth
        # chronicle file exists on disk. Regression pin bumped 3->4 and
        # 1->2 to match, the same way that journal's own fix bumped 2->3 --
        # a hand-typed number, not a live-vs-live tautology, so a future
        # regression in `_episode_files` itself still has something real
        # to disagree with.
        result = cdc.compute_cadence(today=date(2026, 7, 29))
        self.assertEqual(result["total_episodes_on_record"], 4)
        self.assertEqual(result["cluster_day_episodes_shipped"], 2)
        self.assertEqual(result["missed_mondays"], [])

    def test_real_chronicle_dir_matches_todays_hand_counted_gap(self):
        # The same real chronicle/ directory, read against today's real
        # date instead of the frozen 2026-07-29 snapshot above -- confirms
        # episode-003's own cluster-day-covers marker (2026-08-03) actually
        # clears today's real Monday, not just an earlier one.
        result = cdc.compute_cadence(today=date(2026, 8, 3))
        self.assertEqual(result["total_episodes_on_record"], 4)
        self.assertEqual(result["cluster_day_episodes_shipped"], 2)
        self.assertEqual(result["missed_mondays"], [])


class MondayOfCase(unittest.TestCase):
    """Task 528. `_monday_of` moved here from three siblings
    (thegap_check, what_moved_check, nyx_traffic_check) that each held a
    byte-for-byte independent copy of the same one-line calendar-math
    helper -- one copy (nyx_traffic_check's) even had a different AST
    shape (an inline `from datetime import timedelta`), which is exactly
    why the naive AST-hash sweep tasks 508/509/510/513/515/516/523 ran
    caught the other two but not this third one on the first pass."""

    def test_a_monday_maps_to_itself(self):
        self.assertEqual(cdc._monday_of(date(2026, 8, 3)), date(2026, 8, 3))

    def test_a_midweek_day_maps_to_that_weeks_monday(self):
        self.assertEqual(cdc._monday_of(date(2026, 8, 6)), date(2026, 8, 3))

    def test_a_sunday_maps_to_the_preceding_monday(self):
        self.assertEqual(cdc._monday_of(date(2026, 8, 9)), date(2026, 8, 3))


SIBLINGS = ["thegap_check", "what_moved_check", "nyx_traffic_check"]


class MondayOfIdentityAcrossSiblingsCase(unittest.TestCase):
    """Every sibling must call `cluster_day_check._monday_of` itself
    (the same function object), not hold a private re-implementation --
    the only guarantee that makes the three-independent-copies drift
    this task closed structurally unable to recur one copy at a time."""

    def test_every_sibling_has_no_private_monday_of_of_its_own(self):
        for name in SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(name, os.path.join(ROOT, "tools", f"{name}.py"))
                self.assertFalse(
                    hasattr(mod, "_monday_of"),
                    f"{name} still holds its own _monday_of -- the "
                    "consolidation into cluster_day_check regressed",
                )
                # And it must actually be USING the shared one, not a
                # second silently-reintroduced private copy under a
                # different name.
                self.assertIs(mod.cluster_day_check._monday_of, cdc._monday_of)


if __name__ == "__main__":
    unittest.main()
