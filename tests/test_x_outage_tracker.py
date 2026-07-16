"""Task 57. Durable outage-check counting: proves the streak count never
drifts by one, the exact class of bug skipped.md's hand-narrated
"N consecutive hours" already committed (claimed SEVENTH when six real
checks had happened; claimed eighth while skipping that hour's check).
"""
import importlib.util
import os
import sys
import tempfile
import unittest

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

    def test_never_edits_a_prior_line(self):
        xot.record_check("X_PostTweet", "ok", "2026-07-14T00:15:00Z", path=self.path)
        with open(self.path) as f:
            before = f.readlines()
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)


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


if __name__ == "__main__":
    unittest.main()
