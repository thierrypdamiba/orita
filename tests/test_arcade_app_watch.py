"""Task 122. The gateway's own connected-app state, made testable: proves
"has what's connected to the-hand changed since last hour" resolves the
same way every time, instead of being noticed once and forgotten.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "arcade_app_watch", os.path.join(ROOT, "tools", "arcade_app_watch.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


aw = _load()

APPS_GITHUB_X_ONLY = [
    {"app_id": "arcade-github", "name": "GitHub", "connected": True, "permissions": ["repo"]},
    {"app_id": "arcade-x", "name": "X", "connected": True, "permissions": ["tweet.read", "tweet.write"]},
    {"app_id": "arcade-notion", "name": "Notion", "connected": False},
]

APPS_PLUS_GOOGLE = APPS_GITHUB_X_ONLY + [
    {
        "app_id": "arcade-google",
        "name": "Google",
        "connected": True,
        "permissions": ["gmail.readonly", "calendar.readonly"],
    },
]


class _TempLogCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.path)  # record_app_check/_append must create it fresh

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)


class TestComputeAppState(unittest.TestCase):
    def test_keeps_only_connected_apps(self):
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        self.assertEqual(state["connected_app_ids"], ["arcade-github", "arcade-x"])

    def test_sorts_connected_app_ids(self):
        shuffled = [APPS_PLUS_GOOGLE[3], APPS_PLUS_GOOGLE[0], APPS_PLUS_GOOGLE[1]]
        state = aw.compute_app_state(shuffled)
        self.assertEqual(state["connected_app_ids"], ["arcade-github", "arcade-google", "arcade-x"])

    def test_missing_permissions_key_is_an_empty_list_not_an_error(self):
        state = aw.compute_app_state(
            [{"app_id": "ap_town", "name": "town-app", "connected": True}]
        )
        self.assertEqual(state["scopes_by_app"]["ap_town"], [])

    def test_scopes_are_sorted(self):
        state = aw.compute_app_state(
            [{"app_id": "x", "connected": True, "permissions": ["z", "a", "m"]}]
        )
        self.assertEqual(state["scopes_by_app"]["x"], ["a", "m", "z"])


class TestRecordAppCheck(_TempLogCase):
    def test_records_a_line(self):
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state, "2026-07-18T03:00:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_never_edits_a_prior_line(self):
        state1 = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state1, "2026-07-18T02:00:00Z", path=self.path)
        with open(self.path) as f:
            before = f.readlines()
        state2 = aw.compute_app_state(APPS_PLUS_GOOGLE)
        aw.record_app_check(state2, "2026-07-18T03:00:00Z", path=self.path)
        with open(self.path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)


class TestRecordAppCheckDedup(_TempLogCase):
    def test_identical_state_skips_the_write(self):
        # Task 498: the log had 14 of 19 real lines byte-identical aside
        # from checked_at before this fix -- the same self-inflicted
        # duplication shape task 497 closed for square_check.py.
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        wrote_first = aw.record_app_check(state, "2026-07-18T02:00:00Z", path=self.path)
        wrote_second = aw.record_app_check(state, "2026-07-18T03:00:00Z", path=self.path)
        self.assertTrue(wrote_first)
        self.assertFalse(wrote_second)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_skip_despite_different_checked_at(self):
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state, "2026-07-18T02:00:00Z", path=self.path)
        aw.record_app_check(state, "2026-08-01T09:00:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_real_change_after_a_duplicate_still_writes(self):
        state1 = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state1, "2026-07-18T02:00:00Z", path=self.path)
        aw.record_app_check(state1, "2026-07-18T03:00:00Z", path=self.path)
        state2 = aw.compute_app_state(APPS_PLUS_GOOGLE)
        wrote = aw.record_app_check(state2, "2026-07-18T04:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 2)

    def test_no_prior_check_always_writes(self):
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        wrote = aw.record_app_check(state, "2026-07-18T02:00:00Z", path=self.path)
        self.assertTrue(wrote)

    def test_malformed_tip_does_not_block_a_write(self):
        with open(self.path, "w") as f:
            f.write("{not valid json\n")
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        wrote = aw.record_app_check(state, "2026-07-18T02:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 2)


class TestLastAppState(_TempLogCase):
    def test_none_when_never_checked(self):
        self.assertIsNone(aw.last_app_state(path=self.path))

    def test_returns_the_most_recent_not_the_first(self):
        state1 = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state1, "2026-07-18T02:00:00Z", path=self.path)
        state2 = aw.compute_app_state(APPS_PLUS_GOOGLE)
        aw.record_app_check(state2, "2026-07-18T03:00:00Z", path=self.path)
        last = aw.last_app_state(path=self.path)
        self.assertEqual(last["connected_app_ids"], ["arcade-github", "arcade-google", "arcade-x"])

    def test_entries_marks_a_malformed_line_instead_of_raising(self):
        # A hand-edit, stray merge-conflict marker, or truncated write can
        # leave a line that isn't valid JSON at all -- _entries() must name
        # it, not crash with an uncaught json.JSONDecodeError (the exact
        # crash tools/ledger.py's _entries() had before task 238's fix).
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state, "2026-07-18T02:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("not valid json garbage\n")
        entries = aw._entries(path=self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_raises_tampered_error_on_a_malformed_tip_instead_of_crashing(self):
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state, "2026-07-18T02:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("not valid json garbage\n")
        # Pre-fix this raised an uncaught json.JSONDecodeError; it must now
        # raise the named, catchable ArcadeAppWatchTamperedError instead.
        with self.assertRaises(aw.ArcadeAppWatchTamperedError):
            aw.last_app_state(path=self.path)

    def test_entries_marks_a_non_dict_json_line_as_malformed_too(self):
        # A line that parses cleanly (valid JSON) but not to an object -- a
        # bare number, null, list, or stray string -- is not "well-formed"
        # just because json.loads() didn't raise. Task 311, mirroring task
        # 309's change_gate.py / task 310's child_work_check.py fix.
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state, "2026-07-18T02:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("5\n")
        entries = aw._entries(path=self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_raises_tampered_error_on_a_non_dict_json_tip_instead_of_crashing(self):
        # Pre-fix this raised an uncaught AttributeError
        # ('int' object has no attribute 'get'); it must now raise the
        # named, catchable ArcadeAppWatchTamperedError instead.
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state, "2026-07-18T02:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("5\n")
        with self.assertRaises(aw.ArcadeAppWatchTamperedError):
            aw.last_app_state(path=self.path)

    def test_a_valid_tip_after_a_malformed_earlier_line_is_unaffected(self):
        # Only the TIP matters for last_app_state's guess-refusal -- an
        # older malformed line sitting earlier in the log (already surfaced
        # by _entries(), just not at the tip) must not block a real read.
        state1 = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state1, "2026-07-18T02:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("not valid json garbage\n")
        state2 = aw.compute_app_state(APPS_PLUS_GOOGLE)
        aw.record_app_check(state2, "2026-07-18T03:00:00Z", path=self.path)
        last = aw.last_app_state(path=self.path)
        self.assertEqual(last["connected_app_ids"], ["arcade-github", "arcade-google", "arcade-x"])


class TestAppDelta(_TempLogCase):
    def test_due_when_never_checked_before_and_names_current_apps(self):
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        changed, reason = aw.app_delta(state, path=self.path)
        self.assertTrue(changed)
        self.assertIn("no prior app check", reason)
        self.assertIn("arcade-github", reason)
        self.assertIn("arcade-x", reason)

    def test_not_due_when_fully_unchanged(self):
        state = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state, "2026-07-18T02:00:00Z", path=self.path)
        changed, reason = aw.app_delta(state, path=self.path)
        self.assertFalse(changed)
        self.assertIn("unchanged", reason)
        self.assertIn("arcade-github", reason)

    def test_due_and_names_a_newly_connected_app(self):
        state1 = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        aw.record_app_check(state1, "2026-07-18T02:00:00Z", path=self.path)
        state2 = aw.compute_app_state(APPS_PLUS_GOOGLE)
        changed, reason = aw.app_delta(state2, path=self.path)
        self.assertTrue(changed)
        self.assertIn("newly connected: arcade-google", reason)
        self.assertNotIn("newly disconnected", reason)

    def test_due_and_names_a_newly_disconnected_app(self):
        state1 = aw.compute_app_state(APPS_PLUS_GOOGLE)
        aw.record_app_check(state1, "2026-07-18T02:00:00Z", path=self.path)
        state2 = aw.compute_app_state(APPS_GITHUB_X_ONLY)
        changed, reason = aw.app_delta(state2, path=self.path)
        self.assertTrue(changed)
        self.assertIn("newly disconnected: arcade-google", reason)
        self.assertNotIn("newly connected", reason)

    def test_due_and_names_a_scope_change_distinct_from_connect_disconnect(self):
        state1 = aw.compute_app_state(APPS_PLUS_GOOGLE)
        aw.record_app_check(state1, "2026-07-18T02:00:00Z", path=self.path)
        widened = [dict(a) for a in APPS_PLUS_GOOGLE]
        widened[3] = dict(widened[3])
        widened[3]["permissions"] = widened[3]["permissions"] + ["gmail.send"]
        state2 = aw.compute_app_state(widened)
        changed, reason = aw.app_delta(state2, path=self.path)
        self.assertTrue(changed)
        self.assertIn("scope change on already-connected app", reason)
        self.assertIn("arcade-google", reason)
        self.assertIn("+gmail.send", reason)
        self.assertNotIn("newly connected", reason)
        self.assertNotIn("newly disconnected", reason)

    def test_scope_removal_is_named_with_a_minus(self):
        state1 = aw.compute_app_state(APPS_PLUS_GOOGLE)
        aw.record_app_check(state1, "2026-07-18T02:00:00Z", path=self.path)
        narrowed = [dict(a) for a in APPS_PLUS_GOOGLE]
        narrowed[3] = dict(narrowed[3])
        narrowed[3]["permissions"] = ["gmail.readonly"]
        state2 = aw.compute_app_state(narrowed)
        changed, reason = aw.app_delta(state2, path=self.path)
        self.assertTrue(changed)
        self.assertIn("-calendar.readonly", reason)


class TestMainCLI(_TempLogCase):
    def _write_apps_json(self, apps):
        import json
        fd, apps_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({"apps": apps}, f)
        return apps_path

    def test_record_then_check_round_trips(self):
        apps_path = self._write_apps_json(APPS_GITHUB_X_ONLY)
        real_log = aw.LOG
        aw.LOG = self.path  # never touch the real durable log from a test
        try:
            rc = aw.main(["arcade_app_watch.py", "record", apps_path, "2026-07-18T02:00:00Z"])
            self.assertEqual(rc, 0)
            self.assertIsNotNone(aw.last_app_state(path=aw.LOG))
        finally:
            aw.LOG = real_log
            os.remove(apps_path)

    def test_main_raises_named_error_on_non_dict_apps_json(self):
        # <apps.json> used to hand a bare `json.load(f)` result straight to
        # `raw.get("apps", [])`, crashing with a bare AttributeError on
        # anything but a real dict -- the same valid-JSON-wrong-shape crash
        # class task 364 fixed for ritual_check.py's own CLI. Must now
        # raise the named ArcadeAppWatchArgError instead.
        import json
        fd, apps_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump([1, 2, 3], f)
        try:
            with self.assertRaises(aw.ArcadeAppWatchArgError):
                aw.main(["arcade_app_watch.py", "check", apps_path])
        finally:
            os.remove(apps_path)


if __name__ == "__main__":
    unittest.main()
