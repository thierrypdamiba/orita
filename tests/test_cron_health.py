import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.cron_health import (
    most_recent_scheduled_fire,
    parse_daily_cron,
    schedule_status,
)
from datetime import datetime, timezone


class TestParseDailyCron(unittest.TestCase):
    def test_parses_hour_minute(self):
        self.assertEqual(parse_daily_cron("0 12 * * *"), (12, 0))
        self.assertEqual(parse_daily_cron("30 5 * * *"), (5, 30))

    def test_rejects_non_daily_cron(self):
        with self.assertRaises(ValueError):
            parse_daily_cron("0 12 * * 1")

    def test_rejects_malformed_cron(self):
        with self.assertRaises(ValueError):
            parse_daily_cron("0 12 * *")

    def test_rejects_out_of_range_hour(self):
        with self.assertRaises(ValueError):
            parse_daily_cron("0 25 * * *")


class TestMostRecentScheduledFire(unittest.TestCase):
    def test_now_after_todays_fire_time_returns_today(self):
        now = datetime(2026, 7, 14, 13, 1, tzinfo=timezone.utc)
        due = most_recent_scheduled_fire("0 12 * * *", now)
        self.assertEqual(due, datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc))

    def test_now_before_todays_fire_time_returns_yesterday(self):
        now = datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc)
        due = most_recent_scheduled_fire("0 12 * * *", now)
        self.assertEqual(due, datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc))

    def test_exactly_at_fire_time_counts_as_today(self):
        now = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)
        due = most_recent_scheduled_fire("0 12 * * *", now)
        self.assertEqual(due, datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc))


class TestScheduleStatus(unittest.TestCase):
    CRON = "0 12 * * *"

    def test_on_time_when_run_landed_after_due(self):
        result = schedule_status(self.CRON, "2026-07-14T12:05:00Z", "2026-07-14T13:00:00Z")
        self.assertEqual(result["status"], "on_time")
        self.assertIsNone(result["hours_late"])

    def test_prior_day_run_does_not_count_as_on_time(self):
        # This is the exact mistake this hour's own hand-check risked: one
        # total run, dated yesterday, must not read as "ran today".
        result = schedule_status(self.CRON, "2026-07-13T14:30:16Z", "2026-07-14T13:01:45Z")
        self.assertNotEqual(result["status"], "on_time")

    def test_pending_shortly_after_window_opens_with_no_run_yet(self):
        result = schedule_status(
            self.CRON, "2026-07-13T14:30:16Z", "2026-07-14T13:01:45Z", grace_hours=2.0
        )
        self.assertEqual(result["status"], "pending")
        self.assertAlmostEqual(result["hours_late"], 1.03, places=1)

    def test_overdue_well_past_grace_with_no_run(self):
        result = schedule_status(
            self.CRON, "2026-07-13T14:30:16Z", "2026-07-14T15:30:00Z", grace_hours=2.0
        )
        self.assertEqual(result["status"], "overdue")

    def test_grace_boundary_inclusive_is_pending(self):
        result = schedule_status(
            self.CRON, None, "2026-07-14T14:00:00Z", grace_hours=2.0
        )
        self.assertEqual(result["hours_late"], 2.0)
        self.assertEqual(result["status"], "pending")

    def test_grace_boundary_one_second_past_is_overdue(self):
        result = schedule_status(
            self.CRON, None, "2026-07-14T14:00:01Z", grace_hours=2.0
        )
        self.assertEqual(result["status"], "overdue")

    def test_never_run_before_window_is_pending(self):
        result = schedule_status(self.CRON, None, "2026-07-14T12:30:00Z", grace_hours=2.0)
        self.assertEqual(result["status"], "pending")

    def test_never_run_long_past_window_is_overdue(self):
        # due_at always resolves to the most recent fire (<=24h ago); use a
        # `now` just before the NEXT window opens so elapsed is ~23h59m
        # against today's fire time -- genuinely overdue, not a fresh window.
        result = schedule_status(self.CRON, None, "2026-07-15T11:59:00Z", grace_hours=2.0)
        self.assertEqual(result["status"], "overdue")


if __name__ == "__main__":
    unittest.main()
