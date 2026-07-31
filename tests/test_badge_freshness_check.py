"""Proves tools/badge_freshness_check.py actually catches a stale
fencepost/BADGE.json (one that disagrees with a fresh live recompute),
stays clean when the two agree, degrades to clean-but-"unavailable" (never
a crash, never a false STALE) when the live recompute can't run in this
environment, and confirms the real, live, currently-committed BADGE.json
matches whatever `check_badge_freshness()` finds true right now.
"""
import importlib.util
import json
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


bfc = _load("badge_freshness_check", os.path.join(ROOT, "tools", "badge_freshness_check.py"))


def _write_badge(tmpdir, color="brightgreen", message="6/6 tools read-only · 0 writes fired across 22 sealed runs"):
    path = os.path.join(tmpdir, "BADGE.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"schemaVersion": 1, "label": "read-only", "message": message, "color": color, "isError": False},
            f,
        )
    return path


class TestCheckBadgeFreshness(unittest.TestCase):
    def test_agrees_when_committed_matches_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_badge(tmp)
            live = {"color": "brightgreen", "message": "6/6 tools read-only · 0 writes fired across 22 sealed runs"}
            result = bfc.check_badge_freshness(badge_path=path, live=live)
        self.assertTrue(result["clean"])
        self.assertEqual(result["status"], "current")

    def test_catches_a_stale_message(self):
        """The exact drift this module exists to catch: the committed file
        still names a run count the live Ledger has since moved past."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_badge(tmp, message="6/6 tools read-only · 0 writes fired across 21 sealed runs")
            live = {"color": "brightgreen", "message": "6/6 tools read-only · 0 writes fired across 22 sealed runs"}
            result = bfc.check_badge_freshness(badge_path=path, live=live)
        self.assertFalse(result["clean"])
        self.assertEqual(result["status"], "STALE")

    def test_catches_a_stale_color(self):
        """A red-vs-green disagreement is exactly the case the badge exists
        to surface -- must never read as clean just because the message
        text happens to still match."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_badge(tmp, color="red", message="1 violation found — see BADGE.json")
            live = {"color": "brightgreen", "message": "6/6 tools read-only · 0 writes fired across 22 sealed runs"}
            result = bfc.check_badge_freshness(badge_path=path, live=live)
        self.assertFalse(result["clean"])

    def test_live_none_is_clean_but_unavailable_not_a_false_pass(self):
        """`live=None` means "couldn't compute it," never "computed it and
        it happened to match." The `status` field keeps those two
        distinguishable even though both read `clean=True`."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_badge(tmp)
            result = bfc.check_badge_freshness(badge_path=path, live=None)
        self.assertTrue(result["clean"])
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["live"])

    def test_live_badge_state_degrades_to_none_on_any_exception(self):
        """A missing `arcade-mcp-server` install (dawn-run.yml's root test
        job installs only PyYAML, on purpose -- task 404's own note) must
        never crash the caller. Forces the failure deterministically via
        monkeypatch rather than depending on whether this particular
        environment happens to have the package installed."""
        real_seam_badge = bfc._seam_badge
        try:
            def _boom():
                raise ModuleNotFoundError("no module named 'arcade_mcp_server'")

            bfc._seam_badge = _boom
            self.assertIsNone(bfc.live_badge_state())
        finally:
            bfc._seam_badge = real_seam_badge

    def test_format_names_stale_explicitly(self):
        result = {
            "clean": False,
            "status": "STALE",
            "committed": {"color": "brightgreen", "message": "old"},
            "live": {"color": "red", "message": "new"},
        }
        self.assertIn("STALE", bfc.format_badge_freshness(result))

    def test_format_names_unavailable_explicitly(self):
        result = {"clean": True, "status": "unavailable", "committed": {"color": "brightgreen", "message": "x"}, "live": None}
        self.assertIn("unavailable", bfc.format_badge_freshness(result))

    def test_the_real_committed_badge_is_not_currently_stale(self):
        """Runs the real check against the real, live `fencepost/BADGE.json`
        with no injected `live` -- either the live recompute genuinely
        agrees with what's committed, or it's unavailable in this
        environment. Either way `clean` must be True; a real STALE result
        here would mean this task shipped while its own subject was
        already broken."""
        result = bfc.check_badge_freshness()
        self.assertTrue(result["clean"], result)


if __name__ == "__main__":
    unittest.main()
