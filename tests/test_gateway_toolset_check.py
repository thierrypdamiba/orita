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
        state = gt.compute_toolset_state(TOOLS_GITHUB_X_ONLY)
        gt.record_toolset_check(state, "2026-08-01T18:00:00Z", path=self.path)
        with open(self.path) as f:
            before = f.readlines()
        gt.record_toolset_check(state, "2026-08-01T19:00:00Z", path=self.path)
        with open(self.path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)


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


class TestMainCLI(_TempLogCase):
    def _write_tools_json(self, tool_names):
        import json
        fd, tools_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({"tool_names": tool_names}, f)
        return tools_path

    def test_record_then_check_round_trips(self):
        tools_path = self._write_tools_json(TOOLS_GITHUB_X_ONLY)
        real_log = gt.LOG
        gt.LOG = self.path  # never touch the real durable log from a test
        try:
            rc = gt.main(["gateway_toolset_check.py", "record", tools_path, "2026-08-01T18:00:00Z"])
            self.assertEqual(rc, 0)
            self.assertIsNotNone(gt.last_toolset_state(path=gt.LOG))
        finally:
            gt.LOG = real_log
            os.remove(tools_path)

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
