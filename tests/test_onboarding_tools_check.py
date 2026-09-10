"""Proves tools/onboarding_tools_check.py actually catches
`fencepost/ONBOARDING.md`'s minute-3 tool roll call drifting from
`server.py`'s real `@app.tool(metadata=READ_ONLY)` catalog (the live find
that motivated building it: the doc said "four tools", the server had
grown to six), stays clean when the roll call matches exactly (names,
order, and count word), and confirms the real, currently committed
`ONBOARDING.md` is clean right now.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


otc = _load("onboarding_tools_check", os.path.join(ROOT, "tools", "onboarding_tools_check.py"))

_SERVER_FIXTURE = '''
from something import app, READ_ONLY

@app.tool(metadata=READ_ONLY)  # type: ignore[untyped-decorator, arg-type]
def list_repo_commits(owner):
    ...


@app.tool(metadata=READ_ONLY)  # type: ignore[untyped-decorator, arg-type]
def seam_scan(owner):
    ...
'''


def _write(tmp, name, text):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class TestLiveServerTools(unittest.TestCase):
    def test_extracts_decorated_tool_names_in_source_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "server.py", _SERVER_FIXTURE)
            self.assertEqual(otc.live_server_tools(path), ["list_repo_commits", "seam_scan"])

    def test_missing_file_is_an_empty_list_not_a_crash(self):
        self.assertEqual(otc.live_server_tools("/no/such/server.py"), [])


class TestOnboardingClaimedTools(unittest.TestCase):
    def test_parses_the_roll_call_paragraph(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = _write(
                tmp,
                "ONBOARDING.md",
                "two tools come up:\n`list_repo_commits`, `seam_scan` — all `READ_ONLY`.\n",
            )
            result = otc.onboarding_claimed_tools(doc)
        self.assertTrue(result["found"])
        self.assertEqual(result["count_word"], "two")
        self.assertEqual(result["names"], ["list_repo_commits", "seam_scan"])

    def test_missing_paragraph_is_found_false_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = _write(tmp, "ONBOARDING.md", "nothing relevant here.\n")
            result = otc.onboarding_claimed_tools(doc)
        self.assertFalse(result["found"])
        self.assertEqual(result["names"], [])


class TestCheckOnboardingTools(unittest.TestCase):
    def test_clean_when_names_order_and_count_all_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = _write(tmp, "server.py", _SERVER_FIXTURE)
            doc = _write(
                tmp,
                "ONBOARDING.md",
                "two tools come up:\n`list_repo_commits`, `seam_scan` — all `READ_ONLY`.\n",
            )
            result = otc.check_onboarding_tools(server_path=server, onboarding_path=doc)
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["problems"], [])

    def test_catches_the_real_drift_a_grown_server_with_a_stale_count(self):
        """The exact bug this module was built from: server.py grows a new
        tool, ONBOARDING.md's hand-typed roll call and count word don't."""
        with tempfile.TemporaryDirectory() as tmp:
            server = _write(tmp, "server.py", _SERVER_FIXTURE)
            doc = _write(
                tmp,
                "ONBOARDING.md",
                "one tools come up:\n`list_repo_commits` — all `READ_ONLY`.\n",
            )
            result = otc.check_onboarding_tools(server_path=server, onboarding_path=doc)
        self.assertFalse(result["clean"])
        self.assertTrue(any("missing" in p for p in result["problems"]))

    def test_catches_a_stale_tool_name_no_longer_on_the_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = _write(tmp, "server.py", _SERVER_FIXTURE)
            doc = _write(
                tmp,
                "ONBOARDING.md",
                "three tools come up:\n`list_repo_commits`, `seam_scan`, `retired_tool` — all `READ_ONLY`.\n",
            )
            result = otc.check_onboarding_tools(server_path=server, onboarding_path=doc)
        self.assertFalse(result["clean"])
        self.assertTrue(any("stale" in p for p in result["problems"]))

    def test_catches_a_count_word_mismatch_with_otherwise_correct_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = _write(tmp, "server.py", _SERVER_FIXTURE)
            doc = _write(
                tmp,
                "ONBOARDING.md",
                "three tools come up:\n`list_repo_commits`, `seam_scan` — all `READ_ONLY`.\n",
            )
            result = otc.check_onboarding_tools(server_path=server, onboarding_path=doc)
        self.assertFalse(result["clean"])
        self.assertTrue(any("count word" in p for p in result["problems"]))

    def test_missing_onboarding_paragraph_is_reported_not_silently_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = _write(tmp, "server.py", _SERVER_FIXTURE)
            doc = _write(tmp, "ONBOARDING.md", "nothing relevant here.\n")
            result = otc.check_onboarding_tools(server_path=server, onboarding_path=doc)
        self.assertFalse(result["clean"])
        self.assertTrue(any("not found" in p for p in result["problems"]))


class TestFormatOnboardingTools(unittest.TestCase):
    def test_clean_message_names_the_tool_count(self):
        msg = otc.format_onboarding_tools(
            {"clean": True, "live_tools": ["a", "b"], "claimed": {}, "problems": []}
        )
        self.assertIn("clean", msg)
        self.assertIn("2 live server tool", msg)

    def test_stale_message_names_the_problems(self):
        msg = otc.format_onboarding_tools(
            {"clean": False, "live_tools": ["a"], "claimed": {}, "problems": ["tool list mismatch -- missing ['b']"]}
        )
        self.assertIn("STALE", msg)
        self.assertIn("missing", msg)


class TestLiveRepoIsClean(unittest.TestCase):
    """The real find this module was built from: fencepost/ONBOARDING.md's
    minute-3 roll call must match server.py's real tool catalog now."""

    def test_real_onboarding_matches_real_server(self):
        result = otc.check_onboarding_tools()
        self.assertTrue(result["clean"], result["problems"])

    def test_real_server_has_six_tools_today(self):
        self.assertEqual(
            otc.live_server_tools(),
            [
                "list_repo_commits",
                "get_latest_release",
                "get_recent_x_posts",
                "seam_scan",
                "gmail_calendar_scan",
                "combined_scan_preview",
            ],
        )


if __name__ == "__main__":
    unittest.main()
