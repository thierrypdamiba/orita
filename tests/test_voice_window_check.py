import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import voice_window_check as vwc  # noqa: E402


class VoiceWindowCheckCase(unittest.TestCase):
    """Task 103: Iron Rule #7's window clause ("Nyx- and Zashiki-voiced
    commits carry author timestamps in that window") gets its first
    running check. The set of Nyx/Zashiki-Warashi commits is a
    caller-supplied live GitHub read (this checkout is shallow, per task
    101), mirroring check_ci's/check_cron's/check_child_work's shape; the
    in-window verdict itself is pure local arithmetic on the author date."""

    def setUp(self):
        self.log = os.path.join(tempfile.mkdtemp(), "voice-window-log.jsonl")
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(self.log), ignore_errors=True))

    # -- in_window --

    def test_in_window_hours(self):
        self.assertTrue(vwc.in_window("2026-07-16T00:00:00Z"))
        self.assertTrue(vwc.in_window("2026-07-16T03:00:00Z"))
        self.assertTrue(vwc.in_window("2026-07-16T05:59:59Z"))

    def test_out_of_window_hours(self):
        self.assertFalse(vwc.in_window("2026-07-16T06:00:00Z"))
        self.assertFalse(vwc.in_window("2026-07-16T14:55:56Z"))
        self.assertFalse(vwc.in_window("2026-07-16T23:59:59Z"))

    # -- record_commits --

    def test_record_commits_is_idempotent_by_sha(self):
        commits = [{"sha": "a1", "author": "Nyx", "author_date": "2026-07-16T03:00:00Z"}]
        first = vwc.record_commits(commits, "2026-07-17T07:00:00Z", path=self.log)
        second = vwc.record_commits(commits, "2026-07-17T07:05:00Z", path=self.log)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 0)
        self.assertEqual(len(vwc._entries(self.log)), 1)

    def test_record_commits_stamps_in_window(self):
        commits = [
            {"sha": "a1", "author": "Nyx", "author_date": "2026-07-16T03:00:00Z"},
            {"sha": "a2", "author": "Nyx", "author_date": "2026-07-16T14:55:56Z"},
        ]
        vwc.record_commits(commits, "2026-07-17T07:00:00Z", path=self.log)
        entries = {e["sha"]: e for e in vwc._entries(self.log)}
        self.assertTrue(entries["a1"]["in_window"])
        self.assertFalse(entries["a2"]["in_window"])

    # -- check / grandfathering --

    def test_all_pre_cutoff_violations_are_grandfathered_clean(self):
        commits = [
            {"sha": "a1", "author": "Nyx", "author_date": "2026-07-16T14:55:56Z"},
            {"sha": "a2", "author": "Zashiki-Warashi", "author_date": "2026-07-14T18:14:43Z"},
        ]
        result = vwc.check(commits=commits, now_iso="2026-07-17T07:00:00Z", path=self.log, fix_landed_at="2026-07-17T07:30:00Z")
        self.assertTrue(result["clean"])
        self.assertEqual(result["violation_count"], 2)
        self.assertEqual(result["new_violations"], [])
        formatted = vwc.format_check(result)
        self.assertIn("clean", formatted)
        self.assertIn("2 historical", formatted)

    def test_violation_at_or_after_cutoff_is_not_grandfathered(self):
        commits = [{"sha": "b1", "author": "Nyx", "author_date": "2026-07-17T13:00:00Z"}]
        result = vwc.check(commits=commits, now_iso="2026-07-17T13:00:05Z", path=self.log, fix_landed_at="2026-07-17T07:30:00Z")
        self.assertFalse(result["clean"])
        self.assertEqual(result["new_violations"], ["b1"])
        formatted = vwc.format_check(result)
        self.assertIn("NEW VIOLATION", formatted)
        self.assertIn("Iron Rule #7", formatted)

    def test_no_fresh_commits_still_rechecks_already_logged_ones(self):
        commits = [{"sha": "c1", "author": "Nyx", "author_date": "2026-07-17T13:00:00Z"}]
        vwc.check(commits=commits, now_iso="2026-07-17T13:00:05Z", path=self.log, fix_landed_at="2026-07-17T07:30:00Z")
        result = vwc.check(commits=None, now_iso=None, path=self.log, fix_landed_at="2026-07-17T07:30:00Z")
        self.assertFalse(result["clean"])
        self.assertEqual(result["new_violations"], ["c1"])
        self.assertEqual(result["newly_logged"], [])

    def test_in_window_commit_after_cutoff_is_clean(self):
        commits = [{"sha": "d1", "author": "Zashiki-Warashi", "author_date": "2026-07-18T03:00:00Z"}]
        result = vwc.check(commits=commits, now_iso="2026-07-18T03:00:05Z", path=self.log, fix_landed_at="2026-07-17T07:30:00Z")
        self.assertTrue(result["clean"])
        self.assertEqual(result["violation_count"], 0)

    def test_commits_without_now_iso_raises(self):
        with self.assertRaises(ValueError):
            vwc.check(commits=[{"sha": "e1", "author": "Nyx", "author_date": "2026-07-16T03:00:00Z"}], now_iso=None, path=self.log)

    # -- live proof: the real 20 historical violations this task found --

    def test_live_real_commits_are_all_grandfathered_and_clean(self):
        real_commits = [
            {"sha": "ce2ff562", "author": "Nyx", "author_date": "2026-07-16T14:55:56Z"},
            {"sha": "29d5012e", "author": "Nyx", "author_date": "2026-07-16T14:55:46Z"},
            {"sha": "a7f3374a", "author": "Nyx", "author_date": "2026-07-16T14:55:44Z"},
            {"sha": "74b7d71a", "author": "Nyx", "author_date": "2026-07-16T14:55:42Z"},
            {"sha": "5615b1c9", "author": "Nyx", "author_date": "2026-07-16T14:55:40Z"},
            {"sha": "f9f9ec68", "author": "Nyx", "author_date": "2026-07-16T14:55:38Z"},
            {"sha": "d72a8b6e", "author": "Nyx", "author_date": "2026-07-16T13:10:54Z"},
            {"sha": "b8c571df", "author": "Nyx", "author_date": "2026-07-15T14:44:24Z"},
            {"sha": "d6a39a73", "author": "Nyx", "author_date": "2026-07-14T14:45:04Z"},
            {"sha": "4cc5896a", "author": "Nyx", "author_date": "2026-07-12T21:07:19Z"},
            {"sha": "af234106", "author": "Nyx", "author_date": "2026-07-12T08:40:21Z"},
            {"sha": "0905d9aa", "author": "Nyx", "author_date": "2026-07-12T08:39:56Z"},
            {"sha": "af262de7", "author": "Zashiki-Warashi", "author_date": "2026-07-16T14:55:58Z"},
            {"sha": "0d89d5ed", "author": "Zashiki-Warashi", "author_date": "2026-07-16T14:55:53Z"},
            {"sha": "f86a3542", "author": "Zashiki-Warashi", "author_date": "2026-07-16T14:55:49Z"},
            {"sha": "7cce3c91", "author": "Zashiki-Warashi", "author_date": "2026-07-14T18:14:54Z"},
            {"sha": "ec53b570", "author": "Zashiki-Warashi", "author_date": "2026-07-14T18:14:43Z"},
            {"sha": "0602658f", "author": "Zashiki-warashi", "author_date": "2026-07-13T06:04:22Z"},
            {"sha": "eb6efec0", "author": "Zashiki-warashi", "author_date": "2026-07-13T06:03:50Z"},
            {"sha": "f56f4bd3", "author": "Zashiki-warashi", "author_date": "2026-07-12T20:25:20Z"},
        ]
        result = vwc.check(commits=real_commits, now_iso="2026-07-17T07:20:00Z", path=self.log)
        self.assertEqual(result["violation_count"], 20)
        self.assertEqual(result["new_violations"], [])
        self.assertTrue(result["clean"])


class TestTamperedLog(unittest.TestCase):
    """Task 245: a malformed line (bad hand-edit, stray merge-conflict
    marker, truncated write) must not crash record_commits()/check() with
    an uncaught json.JSONDecodeError -- the exact crash tools/ledger.py's
    _entries() had before task 238's fix, mirrored here since task 244's
    hour named this file as a remaining sibling."""

    def setUp(self):
        self.log = os.path.join(tempfile.mkdtemp(), "voice-window-log.jsonl")
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(self.log), ignore_errors=True))

    def test_entries_marks_a_malformed_line_instead_of_raising(self):
        vwc.record_commits(
            [{"sha": "a1", "author": "Nyx", "author_date": "2026-07-16T03:00:00Z"}],
            "2026-07-17T07:00:00Z",
            path=self.log,
        )
        with open(self.log, "a", encoding="utf-8") as f:
            f.write('{"sha": "broken", broken <<<< not json\n')
        entries = vwc._entries(self.log)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_check_raises_tampered_error_when_a_malformed_line_exists_anywhere(self):
        # The malformed line here sits BEFORE the tip, not at it -- check()'s
        # violation count folds over every known entry, so it must refuse
        # rather than silently skip a line that could hide a real violation.
        # Written directly to the file (not via record_commits, which now
        # guards on its own read too) to isolate check()'s own guard.
        vwc.record_commits(
            [{"sha": "a1", "author": "Nyx", "author_date": "2026-07-16T03:00:00Z"}],
            "2026-07-17T07:00:00Z",
            path=self.log,
        )
        with open(self.log, "a", encoding="utf-8") as f:
            f.write('{"sha": "broken", broken <<<< not json\n')
            f.write(
                json.dumps(
                    {
                        "sha": "a2",
                        "author": "Nyx",
                        "author_date": "2026-07-16T14:55:56Z",
                        "in_window": False,
                        "logged_at": "2026-07-17T07:05:00Z",
                    }
                )
                + "\n"
            )
        with self.assertRaises(vwc.VoiceWindowTamperedError):
            vwc.check(commits=None, now_iso=None, path=self.log)

    def test_record_commits_raises_tampered_error_on_a_malformed_existing_line(self):
        vwc.record_commits(
            [{"sha": "a1", "author": "Nyx", "author_date": "2026-07-16T03:00:00Z"}],
            "2026-07-17T07:00:00Z",
            path=self.log,
        )
        with open(self.log, "a", encoding="utf-8") as f:
            f.write('{"sha": "broken", broken <<<< not json\n')
        with self.assertRaises(vwc.VoiceWindowTamperedError):
            vwc.record_commits(
                [{"sha": "a2", "author": "Nyx", "author_date": "2026-07-16T14:55:56Z"}],
                "2026-07-17T07:05:00Z",
                path=self.log,
            )

    def test_entries_marks_a_non_dict_line_instead_of_crashing(self):
        # A line can parse cleanly as JSON but not be an object at all (a
        # bare number, null, list, or stray string) -- _entries() must name
        # it the same as a decode failure, not hand back the raw value for
        # a caller's unconditional .get("_malformed") to crash on.
        vwc.record_commits(
            [{"sha": "a1", "author": "Nyx", "author_date": "2026-07-16T03:00:00Z"}],
            "2026-07-17T07:00:00Z",
            path=self.log,
        )
        with open(self.log, "a", encoding="utf-8") as f:
            f.write("5\n")
        entries = vwc._entries(self.log)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_raises_tampered_error_on_a_non_dict_tip_instead_of_crashing(self):
        # Pre-fix this raised an uncaught AttributeError ('int' object has
        # no attribute 'get'); it must now raise the named, catchable
        # VoiceWindowTamperedError instead, same as a decode failure.
        vwc.record_commits(
            [{"sha": "a1", "author": "Nyx", "author_date": "2026-07-16T03:00:00Z"}],
            "2026-07-17T07:00:00Z",
            path=self.log,
        )
        with open(self.log, "a", encoding="utf-8") as f:
            f.write("5\n")
        with self.assertRaises(vwc.VoiceWindowTamperedError):
            vwc.check(commits=None, now_iso=None, path=self.log)


if __name__ == "__main__":
    unittest.main()
