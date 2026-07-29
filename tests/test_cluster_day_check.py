"""Task 387. Proves tools/cluster_day_check.py's weekly scan actually
counts real-calendar Mondays since founding, names a real lapsed Monday,
ignores a non-conforming chronicle filename, and treats episode-001 (the
founding-day release, week zero) as satisfying no Monday at all -- the
exact distinction orita-vault/hand/skipped.md's 2026-07-27 hand-count
needed and this module has to get right or it under-counts the gap it
exists to name.
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


class RealChronicleCase(unittest.TestCase):
    """Confirms the module's default directory reads the real, live
    chronicle/ dir and reproduces orita-vault/hand/skipped.md's own
    2026-07-27 hand count -- not a duplicated hand-picked number, an
    independent recomputation of the same real files."""

    def test_real_chronicle_dir_matches_the_hand_counted_gap(self):
        # episode-002 ("Eighteen Days") shipped task 391, satisfying the
        # first owed Monday (07-13). 07-20 and 07-27 remain owed.
        result = cdc.compute_cadence(today=date(2026, 7, 29))
        self.assertEqual(result["total_episodes_on_record"], 3)
        self.assertEqual(result["cluster_day_episodes_shipped"], 1)
        self.assertEqual(result["missed_mondays"], ["2026-07-20", "2026-07-27"])


if __name__ == "__main__":
    unittest.main()
