"""Task 464. Whether the-hand gateway exposes any Gmail/Calendar-capable
tool yet, made testable and durably recorded -- mirrors
tests/test_arcade_app_watch.py exactly, one layer down (which TOOLS a
connected app exposes, not which apps are connected).
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "gateway_toolset_check", os.path.join(ROOT, "tools", "gateway_toolset_check.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


gt = _load()

TOOLS_GITHUB_X_ONLY = [
    "Github_ListIssues", "Github_GetRepository", "X_PostTweet", "X_WhoAmI",
    "OutlookMail_CreateDraftEmail", "Arcade_ListApps",
]

TOOLS_PLUS_GMAIL = TOOLS_GITHUB_X_ONLY + ["Gmail_ListEmails", "Gmail_GetEmail"]
TOOLS_PLUS_CALENDAR = TOOLS_GITHUB_X_ONLY + ["GoogleCalendar_ListEvents"]


class _TempLogCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.path)  # record_toolset_check/_append must create it fresh

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        # Task 669: record_toolset_check's own auto-derived freshness
        # companion (self.path + ".freshness") when a test doesn't pass
        # freshness_path explicitly -- clean it up too.
        derived = f"{self.path}.freshness"
        if os.path.exists(derived):
            os.remove(derived)


class TestComputeToolsetState(unittest.TestCase):
    def test_no_match_reads_absent(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        self.assertFalse(state["has_gmail_calendar_tools"])
        self.assertEqual(state["matched_tools"], [])

    def test_gmail_tool_is_matched(self):
        state = gt.compute_toolset_state(TOOLS_PLUS_GMAIL)
        self.assertTrue(state["has_gmail_calendar_tools"])
        self.assertEqual(state["matched_tools"], ["Gmail_GetEmail", "Gmail_ListEmails"])

    def test_calendar_tool_is_matched(self):
        state = gt.compute_toolset_state(TOOLS_PLUS_CALENDAR)
        self.assertTrue(state["has_gmail_calendar_tools"])
        self.assertEqual(state["matched_tools"], ["GoogleCalendar_ListEvents"])

    def test_match_is_case_insensitive(self):
        state = gt.compute_toolset_state(["gmail_listemails"])
        self.assertTrue(state["has_gmail_calendar_tools"])

    def test_matched_tools_are_sorted(self):
        state = gt.compute_toolset_state(["Gmail_Z", "Gmail_A", "Gmail_M"])
        self.assertEqual(state["matched_tools"], ["Gmail_A", "Gmail_M", "Gmail_Z"])

    def test_empty_tool_list_reads_absent_not_an_error(self):
        state = gt.compute_toolset_state([])
        self.assertFalse(state["has_gmail_calendar_tools"])
        self.assertEqual(state["matched_tools"], [])


class TestRecordToolsetCheck(_TempLogCase):
    def test_records_a_line(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-01T19:00:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_never_edits_a_prior_line(self):
        state1 = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state1, "2026-08-01T18:00:00Z", path=self.path)
        with open(self.path) as f:
            before = f.readlines()
        state2 = gt.compute_toolset_state(TOOLS_PLUS_GMAIL)
        gt.record_toolset_check(state2, "2026-08-01T19:00:00Z", path=self.path)
        with open(self.path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)


class TestRecordToolsetCheckDedup(_TempLogCase):
    def test_identical_state_skips_the_write(self):
        # Task 498: the log had 4 of 5 real lines byte-identical aside
        # from checked_at before this fix -- the same self-inflicted
        # duplication shape task 497 closed for square_check.py and this
        # same task closed for arcade_app_watch.py's sibling log.
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        wrote_first = gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        wrote_second = gt.record_toolset_check(state, "2026-08-01T19:00:00Z", path=self.path)
        self.assertTrue(wrote_first)
        self.assertFalse(wrote_second)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_skip_despite_different_checked_at(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        gt.record_toolset_check(state, "2026-08-02T09:00:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_real_change_after_a_duplicate_still_writes(self):
        state1 = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state1, "2026-08-01T18:00:00Z", path=self.path)
        gt.record_toolset_check(state1, "2026-08-01T19:00:00Z", path=self.path)
        state2 = gt.compute_toolset_state(TOOLS_PLUS_GMAIL)
        wrote = gt.record_toolset_check(state2, "2026-08-01T20:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 2)

    def test_no_prior_check_always_writes(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        wrote = gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        self.assertTrue(wrote)

    def test_malformed_tip_does_not_block_a_write(self):
        with open(self.path, "w") as f:
            f.write("{not valid json\n")
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        wrote = gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 2)


class TestLastToolsetState(_TempLogCase):
    def test_none_when_never_checked(self):
        self.assertIsNone(gt.last_toolset_state(path=self.path))

    def test_returns_the_most_recent_not_the_first(self):
        state1 = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state1, "2026-08-01T18:00:00Z", path=self.path)
        state2 = gt.compute_toolset_state(TOOLS_PLUS_GMAIL)
        gt.record_toolset_check(state2, "2026-08-01T19:00:00Z", path=self.path)
        last = gt.last_toolset_state(path=self.path)
        self.assertTrue(last["has_gmail_calendar_tools"])

    def test_entries_marks_a_malformed_line_instead_of_raising(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("not valid json garbage\n")
        entries = gt._entries(path=self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_raises_tampered_error_on_a_malformed_tip_instead_of_crashing(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("not valid json garbage\n")
        with self.assertRaises(gt.GatewayToolsetCheckTamperedError):
            gt.last_toolset_state(path=self.path)

    def test_entries_marks_a_non_dict_json_line_as_malformed_too(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("5\n")
        entries = gt._entries(path=self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])

    def test_raises_tampered_error_on_a_non_dict_json_tip_instead_of_crashing(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("5\n")
        with self.assertRaises(gt.GatewayToolsetCheckTamperedError):
            gt.last_toolset_state(path=self.path)

    def test_a_valid_tip_after_a_malformed_earlier_line_is_unaffected(self):
        state1 = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state1, "2026-08-01T18:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("not valid json garbage\n")
        state2 = gt.compute_toolset_state(TOOLS_PLUS_GMAIL)
        gt.record_toolset_check(state2, "2026-08-01T19:00:00Z", path=self.path)
        last = gt.last_toolset_state(path=self.path)
        self.assertTrue(last["has_gmail_calendar_tools"])


class TestToolsetDelta(_TempLogCase):
    def test_due_when_never_checked_before_and_zero_state(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        changed, reason = gt.toolset_delta(state, path=self.path)
        self.assertTrue(changed)
        self.assertIn("no prior toolset check", reason)
        self.assertIn("(none)", reason)

    def test_not_due_when_fully_unchanged_at_zero(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        changed, reason = gt.toolset_delta(state, path=self.path)
        self.assertFalse(changed)
        self.assertIn("unchanged", reason)
        self.assertIn("zero gmail/calendar", reason)

    def test_not_due_when_fully_unchanged_and_present(self):
        state = gt.compute_toolset_state(TOOLS_PLUS_GMAIL)
        gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        changed, reason = gt.toolset_delta(state, path=self.path)
        self.assertFalse(changed)
        self.assertIn("unchanged, still exposed", reason)
        self.assertIn("Gmail_ListEmails", reason)

    def test_due_when_gmail_calendar_tools_newly_appear(self):
        state1 = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state1, "2026-08-01T18:00:00Z", path=self.path)
        state2 = gt.compute_toolset_state(TOOLS_PLUS_GMAIL)
        changed, reason = gt.toolset_delta(state2, path=self.path)
        self.assertTrue(changed)
        self.assertIn("False -> True", reason)
        self.assertIn("Gmail_ListEmails", reason)

    def test_due_when_gmail_calendar_tools_disappear(self):
        state1 = gt.compute_toolset_state(TOOLS_PLUS_GMAIL)
        gt.record_toolset_check(state1, "2026-08-01T18:00:00Z", path=self.path)
        state2 = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        changed, reason = gt.toolset_delta(state2, path=self.path)
        self.assertTrue(changed)
        self.assertIn("True -> False", reason)


class TestRecordToolsetCheckPingsFreshnessEvenWhenUnchanged(_TempLogCase):
    """Task 669's own load-bearing regression test. Discovered live, after
    the freshness feature's first commit: `record_toolset_check`'s state
    dedup (task 498) means a caller that dutifully re-checks every single
    hour and always finds the same "still zero gmail/calendar tools"
    answer would NEVER write a new line to `path` -- so if
    `compute_toolset_freshness` read `path`/`LOG` directly (as this
    feature's first draft did), it would read STALE forever, no matter
    how often someone genuinely re-verified, which defeats the entire
    point. This proves the fix: the separate freshness companion log
    (auto-derived from `path` here) gets a fresh entry on EVERY real call,
    identical-state or not."""

    def test_freshness_advances_on_repeated_identical_checks(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        freshness_path = f"{self.path}.freshness"
        self.addCleanup(lambda: os.path.exists(freshness_path) and os.remove(freshness_path))

        wrote1 = gt.record_toolset_check(state, "2026-08-04T00:00:00Z", path=self.path)
        wrote2 = gt.record_toolset_check(state, "2026-08-05T00:00:00Z", path=self.path)  # identical state
        wrote3 = gt.record_toolset_check(state, "2026-08-06T00:00:00Z", path=self.path)  # identical state

        # The STATE log's own dedup contract is completely unchanged:
        self.assertTrue(wrote1)
        self.assertFalse(wrote2)
        self.assertFalse(wrote3)
        with open(self.path) as f:
            self.assertEqual(len([ln for ln in f if ln.strip()]), 1)

        # But the freshness companion advanced on every real call:
        with open(freshness_path) as f:
            freshness_lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(freshness_lines), 3)

        # And compute_toolset_freshness reads the LATEST real check, not
        # the last STATE CHANGE -- proving the bug this test exists to
        # catch is actually fixed, not just that the log grew.
        now = datetime(2026, 8, 6, 1, 0, 0, tzinfo=timezone.utc)  # 1h after the 3rd check
        result = gt.compute_toolset_freshness(now, path=freshness_path)
        self.assertEqual(result["status"], "fresh")
        self.assertEqual(result["checked_at"], "2026-08-06T00:00:00Z")

    def test_freshness_path_defaults_to_the_real_constant_only_when_path_is_the_real_log(self):
        # Production callers pass path=LOG (or omit path); the derived
        # freshness_path must be the real FRESHNESS_LOG in that case, not
        # a suffixed variant of LOG's own path.
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        real_log, real_freshness_log = gt.LOG, gt.FRESHNESS_LOG
        gt.LOG = self.path
        gt.FRESHNESS_LOG = f"{self.path}.real-freshness"
        try:
            gt.record_toolset_check(state, "2026-08-04T00:00:00Z", path=gt.LOG)
            self.assertTrue(os.path.exists(gt.FRESHNESS_LOG))
            self.assertFalse(os.path.exists(f"{self.path}.freshness"))  # not the suffixed fallback
        finally:
            if os.path.exists(gt.FRESHNESS_LOG):
                os.remove(gt.FRESHNESS_LOG)
            gt.LOG, gt.FRESHNESS_LOG = real_log, real_freshness_log

    def test_explicit_freshness_path_overrides_both_defaults(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        explicit_path = f"{self.path}.explicit"
        self.addCleanup(lambda: os.path.exists(explicit_path) and os.remove(explicit_path))
        gt.record_toolset_check(state, "2026-08-04T00:00:00Z", path=self.path, freshness_path=explicit_path)
        self.assertTrue(os.path.exists(explicit_path))
        self.assertFalse(os.path.exists(f"{self.path}.freshness"))


class TestRecordToolsetFreshnessCheck(_TempLogCase):
    def test_first_check_always_writes(self):
        wrote = gt.record_toolset_freshness_check("2026-08-11T07:00:00Z", path=self.path)
        self.assertTrue(wrote)

    def test_exact_same_moment_resubmitted_is_skipped(self):
        gt.record_toolset_freshness_check("2026-08-11T07:00:00Z", path=self.path)
        wrote = gt.record_toolset_freshness_check("2026-08-11T07:00:00Z", path=self.path)
        self.assertFalse(wrote)
        with open(self.path) as f:
            self.assertEqual(len([ln for ln in f if ln.strip()]), 1)

    def test_a_different_moment_always_writes_even_with_no_state_change(self):
        gt.record_toolset_freshness_check("2026-08-11T07:00:00Z", path=self.path)
        wrote = gt.record_toolset_freshness_check("2026-08-11T08:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len([ln for ln in f if ln.strip()]), 2)

    def test_malformed_tip_does_not_block_a_write(self):
        with open(self.path, "w") as f:
            f.write("{not valid json\n")
        wrote = gt.record_toolset_freshness_check("2026-08-11T07:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len([ln for ln in f if ln.strip()]), 2)


class TestComputeToolsetFreshness(_TempLogCase):
    """Task 669: the freshness half `toolset_delta`/`check` don't cover --
    how long since this log's own last entry, elapsed-time-keyed since (
    unlike a daily report) there is no fixed 'expected reading for today'
    for this log to be measured against."""

    def test_never_checked_when_log_is_empty(self):
        result = gt.compute_toolset_freshness(datetime(2026, 8, 11, tzinfo=timezone.utc), path=self.path)
        self.assertEqual(result["status"], "never")
        self.assertIsNone(result["days_since"])
        self.assertIsNone(result["checked_at"])

    def test_fresh_well_under_the_bar(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-04T00:00:00Z", path=self.path)
        now = datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc)  # 6.0 days later
        result = gt.compute_toolset_freshness(now, path=self.path)
        self.assertEqual(result["status"], "fresh")
        self.assertLess(result["days_since"], gt.STALE_AFTER_DAYS)
        self.assertEqual(result["days_since"], 6.0)

    def test_exactly_on_the_bar_reads_fresh(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-04T00:00:00Z", path=self.path)
        now = datetime(2026, 8, 11, 0, 0, 0, tzinfo=timezone.utc)  # exactly 7.0 days later
        result = gt.compute_toolset_freshness(now, path=self.path)
        self.assertEqual(result["status"], "fresh")
        self.assertEqual(result["days_since"], gt.STALE_AFTER_DAYS)

    def test_stale_well_over_the_bar(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-04T00:00:00Z", path=self.path)
        now = datetime(2026, 8, 12, 0, 0, 0, tzinfo=timezone.utc)  # 8.0 days later
        result = gt.compute_toolset_freshness(now, path=self.path)
        self.assertEqual(result["status"], "stale")
        self.assertGreater(result["days_since"], gt.STALE_AFTER_DAYS)
        self.assertEqual(result["days_since"], 8.0)
        self.assertEqual(result["checked_at"], "2026-08-04T00:00:00Z")

    def test_stale_matches_this_hours_real_nine_day_gap(self):
        # Reproduces the real, live gap task 669 found in the durable log
        # (last real entry 2026-08-02T09:10:44Z) rather than only a
        # synthetic fixture -- pinned so a future fix to the real log
        # doesn't silently make this test meaningless.
        gt._append({"has_gmail_calendar_tools": False, "matched_tools": [],
                    "checked_at": "2026-08-02T09:10:44Z"}, self.path)
        now = datetime(2026, 8, 11, 7, 4, 41, tzinfo=timezone.utc)
        result = gt.compute_toolset_freshness(now, path=self.path)
        self.assertEqual(result["status"], "stale")
        self.assertAlmostEqual(result["days_since"], 8.9, delta=0.1)

    def test_malformed_tip_reads_stale_not_a_crash(self):
        with open(self.path, "w") as f:
            f.write("not valid json\n")
        result = gt.compute_toolset_freshness(datetime(2026, 8, 11, tzinfo=timezone.utc), path=self.path)
        self.assertEqual(result["status"], "stale")
        self.assertIsNone(result["checked_at"])
        self.assertIn("malformed", result["reason"])

    def test_naive_now_is_treated_as_utc(self):
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-10T00:00:00Z", path=self.path)
        naive_now = datetime(2026, 8, 11, 0, 0, 0)  # no tzinfo
        result = gt.compute_toolset_freshness(naive_now, path=self.path)
        self.assertEqual(result["status"], "fresh")
        self.assertAlmostEqual(result["days_since"], 1.0, delta=0.01)


class TestFormatToolsetFreshness(unittest.TestCase):
    def test_never_checked_message(self):
        msg = gt.format_toolset_freshness(
            {"status": "never", "days_since": None, "checked_at": None, "reason": "no gateway-toolset check has ever been recorded"}
        )
        self.assertIn("NEVER CHECKED", msg)

    def test_fresh_message_names_the_elapsed_days(self):
        msg = gt.format_toolset_freshness(
            {"status": "fresh", "days_since": 2.3, "checked_at": "2026-08-09T00:00:00Z", "reason": None}
        )
        self.assertIn("fresh", msg)
        self.assertIn("2.3", msg)
        self.assertIn("2026-08-09T00:00:00Z", msg)

    def test_stale_message_names_the_elapsed_days_and_the_bar(self):
        msg = gt.format_toolset_freshness(
            {"status": "stale", "days_since": 8.9, "checked_at": "2026-08-02T09:10:44Z", "reason": None}
        )
        self.assertIn("STALE", msg)
        self.assertIn("8.9", msg)
        self.assertIn("7-day", msg)

    def test_malformed_tip_message_uses_the_reason_not_a_day_count(self):
        msg = gt.format_toolset_freshness(
            {"status": "stale", "days_since": None, "checked_at": None, "reason": "the log's own tip is malformed -- last real freshness cannot be trusted"}
        )
        self.assertIn("STALE", msg)
        self.assertIn("malformed", msg)


class TestMainCLI(_TempLogCase):
    def _write_tools_json(self, tool_names):
        import json
        fd, tools_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({"tool_names": tool_names}, f)
        return tools_path

    def test_record_then_check_round_trips(self):
        tools_path = self._write_tools_json(TOOLS_GITHUB_X_ONLY)
        real_log, real_freshness_log = gt.LOG, gt.FRESHNESS_LOG
        gt.LOG = self.path  # never touch the real durable log from a test
        gt.FRESHNESS_LOG = f"{self.path}.freshness"  # nor its freshness companion (task 669)
        try:
            rc = gt.main(["gateway_toolset_check.py", "record", tools_path, "2026-08-01T18:00:00Z"])
            self.assertEqual(rc, 0)
            self.assertIsNotNone(gt.last_toolset_state(path=gt.LOG))
        finally:
            gt.LOG, gt.FRESHNESS_LOG = real_log, real_freshness_log
            os.remove(tools_path)
            if os.path.exists(f"{self.path}.freshness"):
                os.remove(f"{self.path}.freshness")

    def test_freshness_command_needs_no_tools_json(self):
        real_log = gt.LOG
        gt.LOG = self.path  # never touch the real durable log from a test
        try:
            rc = gt.main(["gateway_toolset_check.py", "freshness"])
            self.assertEqual(rc, 0)
        finally:
            gt.LOG = real_log

    def test_main_raises_named_error_on_non_dict_tools_json(self):
        import json
        fd, tools_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump([1, 2, 3], f)
        try:
            with self.assertRaises(gt.GatewayToolsetCheckArgError):
                gt.main(["gateway_toolset_check.py", "check", tools_path])
        finally:
            os.remove(tools_path)


if __name__ == "__main__":
    unittest.main()
