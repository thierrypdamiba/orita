"""Task 1301. Proves the new GitHub-MCP-session outage tracker counts a
streak correctly, dedupes an exact resubmission, refuses to guess past a
corrupted log line, and answers should-recheck off a real cooldown --
the same shapes tests/test_x_outage_tracker.py already proves for the
sibling X tracker.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "github_mcp_outage_check", os.path.join(ROOT, "tools", "github_mcp_outage_check.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


gmo = _load()


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
        gmo.record_check("invalid_session", "2026-09-07T01:22:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["status"], "invalid_session")

    def test_rejects_an_unknown_status(self):
        with self.assertRaises(ValueError):
            gmo.record_check("maybe", "2026-09-07T01:22:00Z", path=self.path)
        self.assertFalse(os.path.exists(self.path))

    def test_rejects_an_unparseable_timestamp(self):
        with self.assertRaises(ValueError):
            gmo.record_check("ok", "--checked-at", path=self.path)

    def test_dedupes_the_exact_same_entry(self):
        first = gmo.record_check("invalid_session", "2026-09-07T01:22:00Z", path=self.path)
        second = gmo.record_check("invalid_session", "2026-09-07T01:22:00Z", path=self.path)
        self.assertTrue(first)
        self.assertFalse(second)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_does_not_dedupe_a_later_check_with_the_same_status(self):
        gmo.record_check("invalid_session", "2026-09-07T01:22:00Z", path=self.path)
        gmo.record_check("invalid_session", "2026-09-07T02:22:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 2)


class TestStreak(_TempLogCase):
    def test_zero_when_no_checks(self):
        self.assertEqual(gmo.current_streak(gmo._entries(self.path)), 0)

    def test_zero_when_most_recent_is_ok(self):
        gmo.record_check("invalid_session", "2026-09-07T01:00:00Z", path=self.path)
        gmo.record_check("ok", "2026-09-07T02:00:00Z", path=self.path)
        self.assertEqual(gmo.current_streak(gmo._entries(self.path)), 0)

    def test_counts_consecutive_trailing_matches_only(self):
        gmo.record_check("ok", "2026-09-07T00:00:00Z", path=self.path)
        gmo.record_check("invalid_session", "2026-09-07T01:00:00Z", path=self.path)
        gmo.record_check("invalid_session", "2026-09-07T02:00:00Z", path=self.path)
        gmo.record_check("invalid_session", "2026-09-07T03:00:00Z", path=self.path)
        self.assertEqual(gmo.current_streak(gmo._entries(self.path)), 3)

    def test_streak_started_at_names_the_oldest_of_the_run(self):
        gmo.record_check("ok", "2026-09-07T00:00:00Z", path=self.path)
        gmo.record_check("invalid_session", "2026-09-07T01:00:00Z", path=self.path)
        gmo.record_check("invalid_session", "2026-09-07T02:00:00Z", path=self.path)
        self.assertEqual(
            gmo.streak_started_at(gmo._entries(self.path)), "2026-09-07T01:00:00Z"
        )

    def test_streak_started_at_none_when_streak_is_zero(self):
        self.assertIsNone(gmo.streak_started_at(gmo._entries(self.path)))


class TestShouldRecheck(_TempLogCase):
    def test_due_when_never_checked(self):
        self.assertTrue(gmo.should_recheck(gmo._entries(self.path), "2026-09-07T01:00:00Z"))

    def test_not_due_inside_cooldown(self):
        gmo.record_check("ok", "2026-09-07T01:00:00Z", path=self.path)
        self.assertFalse(
            gmo.should_recheck(gmo._entries(self.path), "2026-09-07T02:00:00Z", cooldown_hours=2.0)
        )

    def test_due_past_cooldown(self):
        gmo.record_check("ok", "2026-09-07T01:00:00Z", path=self.path)
        self.assertTrue(
            gmo.should_recheck(gmo._entries(self.path), "2026-09-07T04:00:00Z", cooldown_hours=2.0)
        )


class TestTamperedLog(_TempLogCase):
    def _write_raw(self, line: str) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a") as f:
            f.write(line + "\n")

    def test_current_streak_refuses_to_guess_past_a_bad_line(self):
        gmo.record_check("invalid_session", "2026-09-07T01:00:00Z", path=self.path)
        self._write_raw("{not valid json")
        with self.assertRaises(gmo.GithubMcpOutageTrackerTamperedError):
            gmo.current_streak(gmo._entries(self.path))

    def test_record_check_still_writes_past_a_corrupted_log(self):
        self._write_raw("{not valid json")
        wrote = gmo.record_check("ok", "2026-09-07T01:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 2)


class TestCli(_TempLogCase):
    def _run(self, *args):
        env = dict(os.environ)
        return subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "github_mcp_outage_check.py"), *args],
            capture_output=True, text=True, env=env,
        )

    def test_status_with_no_checks(self):
        result = self._run("status")
        self.assertIn("no checks recorded", result.stdout)

    def test_unknown_command_errors(self):
        result = self._run("bogus")
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
