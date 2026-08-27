"""Task 57. Durable outage-check counting: proves the streak count never
drifts by one, the exact class of bug skipped.md's hand-narrated
"N consecutive hours" already committed (claimed SEVENTH when six real
checks had happened; claimed eighth while skipping that hour's check).

Task 246 adds the json.loads-guard campaign's eighth sibling fix: a
malformed line in either log must not crash the caller with an uncaught
json.JSONDecodeError.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "x_outage_tracker", os.path.join(ROOT, "tools", "x_outage_tracker.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


xot = _load()


class _TempLogCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.path)  # record_check/_append must create it fresh

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)


class TestRecordCheck(_TempLogCase):
    def test_records_a_line(self):
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_rejects_an_unknown_status(self):
        with self.assertRaises(ValueError):
            xot.record_check("X_PostTweet", "maybe", "2026-07-14T01:09:00Z", path=self.path)
        self.assertFalse(os.path.exists(self.path))

    def test_rejects_a_mis_cased_tool_name(self):
        """Task 1062 (nisaba): the log carried real mis-cased lines
        (`x_get_user_tweets`/`x_whoami` instead of `X_GetUserTweets`/
        `X_WhoAmI`) from at least three separate past hours before this
        guard existed -- each one a silent phantom "tool" `_tool_entries`
        would never match against the real streak, invisible until a
        future query happens to repeat the same typo. `record_check` must
        refuse any tool string outside `TRACKED_TOOLS` up front, the same
        way it already refuses an unknown `status`."""
        with self.assertRaises(ValueError):
            xot.record_check("x_get_user_tweets", "forbidden", "2026-07-14T01:09:00Z", path=self.path)
        self.assertFalse(os.path.exists(self.path))

    def test_accepts_every_real_tracked_tool_name(self):
        for tool in xot.TRACKED_TOOLS:
            xot.record_check(tool, "ok", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), len(xot.TRACKED_TOOLS))

    def test_never_edits_a_prior_line(self):
        xot.record_check("X_PostTweet", "ok", "2026-07-14T00:15:00Z", path=self.path)
        with open(self.path) as f:
            before = f.readlines()
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)


class TestRecordCheckDedup(_TempLogCase):
    """Task 503: the one `record_*` sibling task 501 named live and left
    unfixed ("no demonstrated bug there") turned out to share the exact
    unconditional-append shape `ci_watch.record_check` had before task 501 --
    two `ritual_check.py` invocations feeding this function the exact same
    already-recorded observation a second time grow `HAND/x-outage-log.jsonl`
    with byte-identical lines. Mirrors `ci_watch.record_check`'s narrower
    guard (task 501), not the single-baseline dedup tasks 487/497/498 gave
    `square_check`/`scribe_growth_check`/`word_watch`: `current_streak`
    REQUIRES that two genuinely separate real checks landing on the same
    status at two different real moments both count."""

    def test_no_prior_check_always_writes(self):
        wrote = xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 1)

    def test_exact_duplicate_is_skipped(self):
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T21:00:00Z", path=self.path)
        wrote = xot.record_check("X_PostTweet", "forbidden", "2026-07-14T21:00:00Z", path=self.path)
        self.assertFalse(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 1)

    def test_same_status_but_a_new_checked_at_still_writes(self):
        # The exact case current_streak depends on: a real check an hour
        # later that happens to repeat the same status is still a genuinely
        # new observation, not a duplicate.
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T21:00:00Z", path=self.path)
        wrote = xot.record_check("X_PostTweet", "forbidden", "2026-07-14T22:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 2)

    def test_a_real_change_after_a_duplicate_still_writes(self):
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.path)
        skipped = xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.path)
        wrote = xot.record_check("X_PostTweet", "ok", "2026-07-14T01:00:00Z", path=self.path)
        self.assertFalse(skipped)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 2)

    def test_dedup_is_scoped_per_tool(self):
        # An exact duplicate for X_WhoAmI must not be suppressed just
        # because X_PostTweet happens to hold an identical-looking last entry.
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.path)
        wrote = xot.record_check("X_WhoAmI", "forbidden", "2026-07-14T00:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 2)

    def test_a_malformed_line_elsewhere_does_not_block_a_real_write(self):
        # Reading (current_streak/last_check) refuses to guess past a
        # corrupted log -- writing must not inherit that refusal, or a
        # single bad hand-edit anywhere in the log would permanently wedge
        # every future real check for every tool.
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write('{"type": "check", broken <<<< not json\n')
        wrote = xot.record_check("X_PostTweet", "ok", "2026-07-14T01:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 3)

    def test_return_value_is_a_bool_not_none(self):
        wrote = xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.path)
        self.assertIs(wrote, True)
        wrote_again = xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.path)
        self.assertIs(wrote_again, False)


class TestLastCheck(_TempLogCase):
    def test_none_when_no_checks(self):
        self.assertIsNone(xot.last_check([], "X_PostTweet"))

    def test_returns_the_most_recent_entry(self):
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.path)
        xot.record_check("X_PostTweet", "ok", "2026-07-14T01:00:00Z", path=self.path)
        entries = xot._entries(self.path)
        last = xot.last_check(entries, "X_PostTweet")
        self.assertEqual(last["status"], "ok")
        self.assertEqual(last["checked_at"], "2026-07-14T01:00:00Z")


class TestCurrentStreak(unittest.TestCase):
    def test_empty_log_is_zero(self):
        self.assertEqual(xot.current_streak([], "X_PostTweet"), 0)

    def test_single_matching_check_is_one_not_zero_not_two(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "1"}]
        self.assertEqual(xot.current_streak(entries, "X_PostTweet"), 1)

    def test_a_trailing_run_of_three_is_exactly_three(self):
        entries = [
            {"type": "check", "tool": "X_PostTweet", "status": "ok", "checked_at": "1"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "3"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "4"},
        ]
        self.assertEqual(xot.current_streak(entries, "X_PostTweet"), 3)

    def test_most_recent_ok_resets_to_zero(self):
        entries = [
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "1"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2"},
            {"type": "check", "tool": "X_PostTweet", "status": "ok", "checked_at": "3"},
        ]
        self.assertEqual(xot.current_streak(entries, "X_PostTweet"), 0)

    def test_a_skipped_hour_does_not_inflate_the_streak(self):
        # Six real checks -- the exact backlog behind skipped.md's 06:2x note,
        # which narrated this as the "SEVENTH consecutive hour" by mistake.
        entries = [
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": f"h{i}"}
            for i in range(1, 7)
        ]
        self.assertEqual(xot.current_streak(entries, "X_PostTweet"), 6)

    def test_interleaved_tools_are_counted_independently(self):
        entries = [
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "1"},
            {"type": "check", "tool": "X_GetUserTweets", "status": "forbidden", "checked_at": "1"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2"},
            {"type": "check", "tool": "X_GetUserTweets", "status": "ok", "checked_at": "2"},
        ]
        self.assertEqual(xot.current_streak(entries, "X_PostTweet"), 2)
        self.assertEqual(xot.current_streak(entries, "X_GetUserTweets"), 0)


class TestStreakStartedAt(unittest.TestCase):
    def test_none_when_no_streak(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "ok", "checked_at": "1"}]
        self.assertIsNone(xot.streak_started_at(entries, "X_PostTweet"))

    def test_points_at_the_first_entry_of_the_trailing_run_not_the_whole_log(self):
        entries = [
            {"type": "check", "tool": "X_PostTweet", "status": "ok", "checked_at": "0"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T02:09:00Z"},
        ]
        self.assertEqual(xot.streak_started_at(entries, "X_PostTweet"), "2026-07-14T01:09:00Z")


class TestFormatStatusLine(unittest.TestCase):
    def test_no_checks_recorded(self):
        self.assertEqual(xot.format_status_line([], "X_PostTweet"), "X_PostTweet: no checks recorded")

    def test_ok_reports_ok_not_a_streak(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "ok", "checked_at": "2026-07-14T00:15:00Z"}]
        line = xot.format_status_line(entries, "X_PostTweet")
        self.assertIn("OK", line)
        self.assertNotIn("consecutive", line)

    def test_forbidden_streak_names_the_exact_count_and_since(self):
        entries = [
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T02:09:00Z"},
        ]
        line = xot.format_status_line(entries, "X_PostTweet")
        self.assertIn("2 consecutive forbidden checks", line)
        self.assertIn("2026-07-14T01:09:00Z", line)
        self.assertIn("2026-07-14T02:09:00Z", line)


class TestHoursSinceLastCheck(unittest.TestCase):
    def test_none_when_never_checked(self):
        self.assertIsNone(xot.hours_since_last_check([], "X_PostTweet", "2026-07-14T10:03:00Z"))

    def test_exact_hours_elapsed(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T06:20:00Z"}]
        elapsed = xot.hours_since_last_check(entries, "X_PostTweet", "2026-07-14T10:03:00Z")
        self.assertAlmostEqual(elapsed, 3 + 43 / 60, places=6)


class TestShouldRecheck(unittest.TestCase):
    def test_due_when_never_checked(self):
        self.assertTrue(xot.should_recheck([], "X_PostTweet", "2026-07-14T10:03:00Z"))

    def test_not_due_inside_the_cooldown(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T09:00:00Z"}]
        self.assertFalse(xot.should_recheck(entries, "X_PostTweet", "2026-07-14T10:03:00Z", cooldown_hours=2.0))

    def test_due_once_the_cooldown_has_elapsed(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T06:20:00Z"}]
        self.assertTrue(xot.should_recheck(entries, "X_PostTweet", "2026-07-14T10:03:00Z", cooldown_hours=2.0))

    def test_boundary_is_exact_not_off_by_one_hour(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T08:00:00Z"}]
        self.assertFalse(xot.should_recheck(entries, "X_PostTweet", "2026-07-14T09:59:59Z", cooldown_hours=2.0))
        self.assertTrue(xot.should_recheck(entries, "X_PostTweet", "2026-07-14T10:00:00Z", cooldown_hours=2.0))

    def test_tools_are_independent(self):
        entries = [
            {"type": "check", "tool": "X_GetUserTweets", "status": "forbidden", "checked_at": "2026-07-14T10:00:00Z"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T06:20:00Z"},
        ]
        self.assertFalse(xot.should_recheck(entries, "X_GetUserTweets", "2026-07-14T10:03:00Z", cooldown_hours=2.0))
        self.assertTrue(xot.should_recheck(entries, "X_PostTweet", "2026-07-14T10:03:00Z", cooldown_hours=2.0))


class TestTrackedToolsIncludesWhoAmI(unittest.TestCase):
    """Task 72. The tracker watched the write and one read; the profile
    read (X_WhoAmI) recovered a full day before the other two did, and
    nothing durable could say so until this tool knew to watch it too."""

    def test_who_am_i_is_tracked(self):
        self.assertIn("X_WhoAmI", xot.TRACKED_TOOLS)

    def test_status_output_includes_a_who_am_i_line(self):
        entries = [
            {"type": "check", "tool": "X_WhoAmI", "status": "ok", "checked_at": "2026-07-14T23:07:00Z"},
            {"type": "check", "tool": "X_GetUserTweets", "status": "forbidden", "checked_at": "2026-07-14T22:07:00Z"},
        ]
        lines = [xot.format_status_line(entries, tool) for tool in xot.TRACKED_TOOLS]
        who_am_i_lines = [ln for ln in lines if ln.startswith("X_WhoAmI:")]
        self.assertEqual(len(who_am_i_lines), 1)
        self.assertIn("OK as of 2026-07-14T23:07:00Z", who_am_i_lines[0])


class TestShouldEscalate(unittest.TestCase):
    """Task 81. An ongoing outage should tell the Hand exactly once when it
    crosses the threshold -- not every hour it stays broken, and not before
    it's actually old enough to matter."""

    def test_not_due_with_no_active_outage(self):
        due, reason = xot.should_escalate([], "X_PostTweet", "2026-07-14T10:00:00Z", escalation_entries=[])
        self.assertFalse(due)
        self.assertIn("no active outage", reason)

    def test_not_due_below_threshold(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        due, reason = xot.should_escalate(
            entries, "X_PostTweet", "2026-07-15T01:00:00Z", threshold_hours=48.0, escalation_entries=[]
        )
        self.assertFalse(due)
        self.assertIn("below 48.0h threshold", reason)

    def test_due_once_the_streak_crosses_the_threshold(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        due, reason = xot.should_escalate(
            entries, "X_PostTweet", "2026-07-16T02:00:00Z", threshold_hours=48.0, escalation_entries=[]
        )
        self.assertTrue(due)
        self.assertIn("crosses 48.0h threshold", reason)

    def test_boundary_is_exact_not_off_by_one_hour(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        due_before, _ = xot.should_escalate(
            entries, "X_PostTweet", "2026-07-16T01:08:59Z", threshold_hours=48.0, escalation_entries=[]
        )
        due_at, _ = xot.should_escalate(
            entries, "X_PostTweet", "2026-07-16T01:09:00Z", threshold_hours=48.0, escalation_entries=[]
        )
        self.assertFalse(due_before)
        self.assertTrue(due_at)

    def test_not_due_a_second_time_for_the_same_streak(self):
        entries = [
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-16T02:00:00Z"},
        ]
        prior_escalations = [
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-16T02:00:00Z",
                "hours": 48.85,
            }
        ]
        due, reason = xot.should_escalate(
            entries,
            "X_PostTweet",
            "2026-07-16T10:00:00Z",
            threshold_hours=48.0,
            escalation_entries=prior_escalations,
        )
        self.assertFalse(due)
        self.assertIn("already escalated", reason)

    def test_a_fresh_streak_after_recovery_gets_its_own_chance(self):
        entries = [
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"},
            {"type": "check", "tool": "X_PostTweet", "status": "ok", "checked_at": "2026-07-16T02:00:00Z"},
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-17T00:00:00Z"},
        ]
        prior_escalations = [
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-16T02:00:00Z",
                "hours": 48.85,
            }
        ]
        due, reason = xot.should_escalate(
            entries,
            "X_PostTweet",
            "2026-07-19T01:00:00Z",
            threshold_hours=48.0,
            escalation_entries=prior_escalations,
        )
        self.assertTrue(due)
        self.assertIn("crosses 48.0h threshold", reason)


class TestRecordEscalation(_TempLogCase):
    def test_records_a_line_and_never_edits_a_prior_one(self):
        xot.record_escalation("X_PostTweet", "2026-07-14T01:09:00Z", "2026-07-16T02:00:00Z", 48.85, path=self.path)
        with open(self.path) as f:
            before = f.readlines()
        xot.record_escalation("X_GetUserTweets", "2026-07-14T02:09:00Z", "2026-07-16T03:00:00Z", 48.85, path=self.path)
        with open(self.path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), 2)

    def test_already_escalated_for_streak_reads_the_written_entry_back(self):
        xot.record_escalation("X_PostTweet", "2026-07-14T01:09:00Z", "2026-07-16T02:00:00Z", 48.85, path=self.path)
        entries = xot._escalation_entries(path=self.path)
        self.assertTrue(xot.already_escalated_for_streak(entries, "X_PostTweet", "2026-07-14T01:09:00Z"))
        self.assertFalse(xot.already_escalated_for_streak(entries, "X_PostTweet", "2026-07-15T00:00:00Z"))
        self.assertFalse(xot.already_escalated_for_streak(entries, "X_GetUserTweets", "2026-07-14T01:09:00Z"))

    def test_omitted_threshold_defaults_to_the_48h_tier(self):
        xot.record_escalation("X_PostTweet", "2026-07-14T01:09:00Z", "2026-07-16T02:00:00Z", 48.85, path=self.path)
        entry = xot._escalation_entries(path=self.path)[0]
        self.assertEqual(entry["threshold_hours"], 48.0)


class TestTieredEscalation(unittest.TestCase):
    """Task 92: a streak that already fired its 48h notice still earns a
    fresh, more severe notice once it crosses the 168h tier -- the gap
    task 81's single (tool, streak_started_at) suppression key left open
    on the town's own real, still-ongoing X outage."""

    def test_already_escalated_at_48h_does_not_suppress_the_168h_tier(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        prior_escalations = [
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-16T02:00:00Z",
                "hours": 48.85,
                "threshold_hours": 48.0,
            }
        ]
        due, reason = xot.should_escalate(
            entries, "X_PostTweet", "2026-07-21T02:00:00Z", threshold_hours=168.0, escalation_entries=prior_escalations
        )
        self.assertTrue(due)
        self.assertIn("crosses 168.0h threshold", reason)

    def test_a_pre_task_92_entry_with_no_threshold_field_reads_as_the_48h_tier(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        legacy_escalation = [
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-16T07:05:00Z",
                "hours": 53.9,
                # no "threshold_hours" field -- the real shape task 81 wrote.
            }
        ]
        still_suppressed, reason = xot.should_escalate(
            entries, "X_PostTweet", "2026-07-16T10:00:00Z", threshold_hours=48.0, escalation_entries=legacy_escalation
        )
        self.assertFalse(still_suppressed)
        self.assertIn("already escalated", reason)
        now_due, _ = xot.should_escalate(
            entries, "X_PostTweet", "2026-07-23T10:00:00Z", threshold_hours=168.0, escalation_entries=legacy_escalation
        )
        self.assertTrue(now_due)

    def test_next_escalation_tier_reports_the_worst_unfired_tier(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        # 200 hours in with nothing escalated yet: both tiers are crossed,
        # but the caller should only be told the worse one.
        tier = xot.next_escalation_tier(entries, "X_PostTweet", "2026-07-22T09:09:00Z", escalation_entries=[])
        self.assertEqual(tier[0], 168.0)

    def test_next_escalation_tier_falls_back_once_the_worst_tier_is_fired(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        fired_168 = [
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-22T09:09:00Z",
                "hours": 200.0,
                "threshold_hours": 168.0,
            }
        ]
        # 48h was never fired for this streak, 168h just was: the worst
        # REMAINING unfired tier is 48h, not "nothing left to say".
        tier = xot.next_escalation_tier(entries, "X_PostTweet", "2026-07-22T09:09:00Z", escalation_entries=fired_168)
        self.assertEqual(tier[0], 48.0)

    def test_next_escalation_tier_is_none_once_every_tier_has_fired(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        fired_both = [
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-16T02:00:00Z",
                "hours": 48.85,
                "threshold_hours": 48.0,
            },
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-22T09:09:00Z",
                "hours": 200.0,
                "threshold_hours": 168.0,
            },
        ]
        tier = xot.next_escalation_tier(entries, "X_PostTweet", "2026-07-22T09:09:00Z", escalation_entries=fired_both)
        self.assertIsNone(tier)

    def test_next_escalation_tier_none_with_no_active_outage(self):
        tier = xot.next_escalation_tier([], "X_PostTweet", "2026-07-22T09:09:00Z", escalation_entries=[])
        self.assertIsNone(tier)


class TestRecurringEscalationTiers(unittest.TestCase):
    """Task 422: ESCALATION_TIERS is a finite tuple (48h, 168h) that
    next_escalation_tier only ever walked -- so an outage that outlives
    168h without recovering reads "already escalated" forever after, no
    matter whether it is a week old or a year old (named directly to the
    Hand in hand/skipped.md 2026-07-27, still open at task 421). Once an
    outage runs past the highest named tier, one new tier every
    RECURRING_ESCALATION_INTERVAL_HOURS (168h, matching the second named
    tier's own cadence) must become due."""

    def test_extended_tiers_adds_nothing_before_the_first_recurring_boundary(self):
        # 336h is 168h (the highest named tier) + one more 168h interval.
        # Anything short of that has nothing to add.
        self.assertEqual(xot._extended_tiers(300.0, (48.0, 168.0)), (48.0, 168.0))

    def test_extended_tiers_adds_one_recurring_tier_past_the_boundary(self):
        self.assertEqual(xot._extended_tiers(400.0, (48.0, 168.0)), (48.0, 168.0, 336.0))

    def test_extended_tiers_adds_every_boundary_crossed(self):
        # 550h has crossed 336h (168+168) and 504h (168+168+168), not 672h.
        self.assertEqual(xot._extended_tiers(550.0, (48.0, 168.0)), (48.0, 168.0, 336.0, 504.0))

    def test_extended_tiers_empty_tiers_stays_empty(self):
        self.assertEqual(xot._extended_tiers(1000.0, ()), ())

    def test_next_escalation_tier_fires_a_recurring_tier_once_both_named_tiers_are_spent(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        fired_both_named_tiers = [
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-16T02:00:00Z",
                "hours": 48.85,
                "threshold_hours": 48.0,
            },
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-21T01:11:00Z",
                "hours": 168.03,
                "threshold_hours": 168.0,
            },
        ]
        # 2026-07-14T01:09:00Z + 336h = 2026-07-28T01:09:00Z, the first
        # recurring boundary -- matches this task's real live outage shape.
        tier = xot.next_escalation_tier(
            entries, "X_PostTweet", "2026-07-28T02:00:00Z", escalation_entries=fired_both_named_tiers
        )
        self.assertEqual(tier[0], 336.0)
        self.assertIn("crosses 336.0h threshold", tier[1])

    def test_next_escalation_tier_recurring_boundary_not_due_before_it_is_crossed(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        fired_both_named_tiers = [
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-16T02:00:00Z",
                "hours": 48.85,
                "threshold_hours": 48.0,
            },
            {
                "type": "escalation",
                "tool": "X_PostTweet",
                "streak_started_at": "2026-07-14T01:09:00Z",
                "escalated_at": "2026-07-21T01:11:00Z",
                "hours": 168.03,
                "threshold_hours": 168.0,
            },
        ]
        # Only 262h in -- short of the 336h recurring boundary.
        tier = xot.next_escalation_tier(
            entries, "X_PostTweet", "2026-07-25T03:00:00Z", escalation_entries=fired_both_named_tiers
        )
        self.assertIsNone(tier)

    def test_next_escalation_tier_recurring_tier_fires_once_then_suppresses(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        fired_through_336 = [
            {"type": "escalation", "tool": "X_PostTweet", "streak_started_at": "2026-07-14T01:09:00Z", "escalated_at": "2026-07-16T02:00:00Z", "hours": 48.85, "threshold_hours": 48.0},
            {"type": "escalation", "tool": "X_PostTweet", "streak_started_at": "2026-07-14T01:09:00Z", "escalated_at": "2026-07-21T01:11:00Z", "hours": 168.03, "threshold_hours": 168.0},
            {"type": "escalation", "tool": "X_PostTweet", "streak_started_at": "2026-07-14T01:09:00Z", "escalated_at": "2026-07-28T02:00:00Z", "hours": 336.85, "threshold_hours": 336.0},
        ]
        # Same 336h-crossed moment: already fired at that tier, and the
        # next boundary (504h) is not crossed yet -- nothing due.
        still_quiet = xot.next_escalation_tier(
            entries, "X_PostTweet", "2026-07-28T02:00:00Z", escalation_entries=fired_through_336
        )
        self.assertIsNone(still_quiet)
        # 504h later (2026-08-04T01:09:00Z is exactly 504h from start):
        # the next real recurring boundary is due.
        now_due = xot.next_escalation_tier(
            entries, "X_PostTweet", "2026-08-04T02:00:00Z", escalation_entries=fired_through_336
        )
        self.assertEqual(now_due[0], 504.0)

    def test_next_escalation_tier_recurring_boundary_respects_a_custom_interval(self):
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        # A 24h recurring interval crosses its first new boundary (192h)
        # well before the default 168h interval would (336h).
        tier = xot.next_escalation_tier(
            entries,
            "X_PostTweet",
            "2026-07-22T01:09:00Z",  # 192h in
            escalation_entries=[],
            recurring_interval=24.0,
        )
        self.assertEqual(tier[0], 192.0)

    def test_next_escalation_tier_regression_at_200h_still_reports_168_not_a_phantom_recurring_tier(self):
        # Guards task 92's own existing fixture: 200h in is short of the
        # 336h recurring boundary, so the worst unfired tier must stay 168.
        entries = [{"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}]
        tier = xot.next_escalation_tier(entries, "X_PostTweet", "2026-07-22T09:09:00Z", escalation_entries=[])
        self.assertEqual(tier[0], 168.0)


class TestTamperedCheckLog(_TempLogCase):
    """Task 246: a malformed line (bad hand-edit, stray merge-conflict
    marker, truncated write) in the check log must not crash
    current_streak()/streak_started_at()/should_recheck() with an
    uncaught json.JSONDecodeError -- the exact crash tools/ledger.py's
    _entries() had before task 238's fix, mirrored here since task 245's
    hour named this file as a remaining sibling."""

    def test_entries_marks_a_malformed_line_instead_of_raising(self):
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write('{"tool": "broken", broken <<<< not json\n')
        entries = xot._entries(self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_entries_marks_a_valid_but_non_dict_line_as_malformed(self):
        # A line that parses cleanly to a bare int (not a JSON object) must
        # not be handed back as-is -- _tool_entries()'s e.get("_malformed")
        # would crash on it with an uncaught AttributeError.
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("5\n")
        entries = xot._entries(self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_current_streak_raises_tampered_error_on_a_non_dict_tip_instead_of_crashing(self):
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("5\n")
        entries = xot._entries(self.path)
        with self.assertRaises(xot.XOutageTrackerTamperedError):
            xot.current_streak(entries, "X_PostTweet")

    def test_current_streak_raises_tampered_error_when_a_malformed_line_exists_anywhere(self):
        # The malformed line sits BEFORE the tip, not at it -- current_streak
        # can walk arbitrarily far back through a long trailing streak, so it
        # must refuse rather than silently skip a line that could belong to
        # the tool it's counting.
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write('{"tool": "broken", broken <<<< not json\n')
            f.write(
                json.dumps(
                    {
                        "type": "check",
                        "tool": "X_PostTweet",
                        "status": "forbidden",
                        "checked_at": "2026-07-14T02:09:00Z",
                    }
                )
                + "\n"
            )
        entries = xot._entries(self.path)
        with self.assertRaises(xot.XOutageTrackerTamperedError):
            xot.current_streak(entries, "X_PostTweet")

    def test_streak_started_at_raises_tampered_error_on_a_malformed_existing_line(self):
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write('{"tool": "broken", broken <<<< not json\n')
        entries = xot._entries(self.path)
        with self.assertRaises(xot.XOutageTrackerTamperedError):
            xot.streak_started_at(entries, "X_PostTweet")

    def test_should_recheck_raises_tampered_error_on_a_malformed_existing_line(self):
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write('{"tool": "broken", broken <<<< not json\n')
        entries = xot._entries(self.path)
        with self.assertRaises(xot.XOutageTrackerTamperedError):
            xot.should_recheck(entries, "X_PostTweet", "2026-07-14T10:00:00Z")


class TestTamperedEscalationLog(_TempLogCase):
    """Task 246: the same malformed-line guard, for the escalation log.
    already_escalated_for_streak must scan the whole escalation history to
    know whether a given (tool, streak, tier) already fired -- a malformed
    line anywhere could be hiding exactly that prior escalation, so it must
    refuse rather than silently treat it as a non-match."""

    def test_escalation_entries_marks_a_malformed_line_instead_of_raising(self):
        xot.record_escalation("X_PostTweet", "2026-07-14T01:09:00Z", "2026-07-16T02:00:00Z", 48.85, path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write('{"tool": "broken", broken <<<< not json\n')
        entries = xot._escalation_entries(path=self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_escalation_entries_marks_a_valid_but_non_dict_line_as_malformed(self):
        xot.record_escalation("X_PostTweet", "2026-07-14T01:09:00Z", "2026-07-16T02:00:00Z", 48.85, path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("5\n")
        entries = xot._escalation_entries(path=self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_already_escalated_for_streak_raises_tampered_error_on_a_non_dict_line_instead_of_crashing(self):
        xot.record_escalation("X_PostTweet", "2026-07-14T01:09:00Z", "2026-07-16T02:00:00Z", 48.85, path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("5\n")
        entries = xot._escalation_entries(path=self.path)
        with self.assertRaises(xot.XOutageTrackerTamperedError):
            xot.already_escalated_for_streak(entries, "X_PostTweet", "2026-07-14T01:09:00Z")

    def test_already_escalated_for_streak_raises_tampered_error_when_a_malformed_line_exists_anywhere(self):
        xot.record_escalation("X_PostTweet", "2026-07-14T01:09:00Z", "2026-07-16T02:00:00Z", 48.85, path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write('{"tool": "broken", broken <<<< not json\n')
        entries = xot._escalation_entries(path=self.path)
        with self.assertRaises(xot.XOutageTrackerTamperedError):
            xot.already_escalated_for_streak(entries, "X_PostTweet", "2026-07-14T01:09:00Z")

    def test_should_escalate_raises_tampered_error_on_a_malformed_escalation_line(self):
        check_entries = [
            {"type": "check", "tool": "X_PostTweet", "status": "forbidden", "checked_at": "2026-07-14T01:09:00Z"}
        ]
        xot.record_escalation("X_PostTweet", "2026-07-14T01:09:00Z", "2026-07-16T02:00:00Z", 48.85, path=self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write('{"tool": "broken", broken <<<< not json\n')
        escalation_entries = xot._escalation_entries(path=self.path)
        with self.assertRaises(xot.XOutageTrackerTamperedError):
            xot.should_escalate(
                check_entries,
                "X_PostTweet",
                "2026-07-16T02:00:00Z",
                threshold_hours=48.0,
                escalation_entries=escalation_entries,
            )


class TestEscalationEntriesDelegates(unittest.TestCase):
    """Task 691. _escalation_entries() must genuinely call through to the
    shared jsonl_read.read_jsonl_entries -- the same reader its sibling
    _entries() (task 540) already delegates to -- not carry a reinlined
    copy of the read-and-mark-malformed logic. Patch-and-observe, the
    same identity guarantee tests/test_jsonl_read.py's
    DelegatesToSharedReaderCase uses for the fourteen simple siblings."""

    def test_escalation_entries_delegates_to_shared_reader(self):
        sentinel = [{"marker": "escalation"}]
        with mock.patch.object(
            xot.jsonl_read, "read_jsonl_entries", return_value=sentinel
        ) as patched:
            result = xot._escalation_entries(path="/does/not/matter.jsonl")
        patched.assert_called_once_with("/does/not/matter.jsonl")
        self.assertEqual(result, sentinel)

    def test_escalation_entries_default_path_is_the_module_constant(self):
        with mock.patch.object(
            xot.jsonl_read, "read_jsonl_entries", return_value=[]
        ) as patched:
            xot._escalation_entries()
        patched.assert_called_once_with(xot.ESCALATION_LOG)


class CliArgvBoundsCase(unittest.TestCase):
    """Task 683. `record`/`should-recheck`/`should-escalate`/`next-tier` each
    unpacked `sys.argv[2:]` positionally with zero bounds checking -- the
    same unguarded-argv shape tasks 663/672/675/682 already swept from
    other tools/ CLIs but never reached `x_outage_tracker.py`. Runs the
    real script as a subprocess so it exercises the actual `__main__`
    block."""

    SCRIPT = os.path.join(ROOT, "tools", "x_outage_tracker.py")

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True,
            text=True,
        )

    def test_record_with_too_few_args_names_the_problem_not_indexerror(self):
        result = self._run("record", "X_PostTweet", "forbidden")
        self.assertEqual(result.returncode, 2, result)
        self.assertIn("usage: x_outage_tracker.py record", result.stdout, result)
        self.assertNotIn("IndexError", result.stderr, result)
        self.assertNotIn("Traceback", result.stderr, result)

    def test_should_recheck_with_too_few_args_names_the_problem_not_indexerror(self):
        result = self._run("should-recheck", "X_PostTweet")
        self.assertEqual(result.returncode, 2, result)
        self.assertIn("usage: x_outage_tracker.py should-recheck", result.stdout, result)
        self.assertNotIn("IndexError", result.stderr, result)
        self.assertNotIn("Traceback", result.stderr, result)

    def test_should_escalate_with_too_few_args_names_the_problem_not_indexerror(self):
        result = self._run("should-escalate", "X_PostTweet")
        self.assertEqual(result.returncode, 2, result)
        self.assertIn("usage: x_outage_tracker.py should-escalate", result.stdout, result)
        self.assertNotIn("IndexError", result.stderr, result)
        self.assertNotIn("Traceback", result.stderr, result)

    def test_next_tier_with_too_few_args_names_the_problem_not_indexerror(self):
        result = self._run("next-tier", "X_PostTweet")
        self.assertEqual(result.returncode, 2, result)
        self.assertIn("usage: x_outage_tracker.py next-tier", result.stdout, result)
        self.assertNotIn("IndexError", result.stderr, result)
        self.assertNotIn("Traceback", result.stderr, result)

    def test_next_tier_with_no_args_names_the_problem_not_indexerror(self):
        result = self._run("next-tier")
        self.assertEqual(result.returncode, 2, result)
        self.assertIn("usage: x_outage_tracker.py next-tier", result.stdout, result)
        self.assertNotIn("IndexError", result.stderr, result)
        self.assertNotIn("Traceback", result.stderr, result)


if __name__ == "__main__":
    unittest.main()
