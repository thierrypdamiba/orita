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
        never crash the caller. Forces the in-process failure
        deterministically via monkeypatch rather than depending on whether
        this particular environment happens to have the package installed
        -- and, since task 574, also blocks the `uv` fallback (`shutil.
        which` -> None) so this proves the FULL degrade-to-None path, not
        just the in-process leg; `TestLiveBadgeStateViaUv`'s own tests
        below cover the fallback engaging on its own."""
        real_seam_badge = bfc._seam_badge
        real_which = bfc.shutil.which
        try:
            def _boom():
                raise ModuleNotFoundError("no module named 'arcade_mcp_server'")

            bfc._seam_badge = _boom
            bfc.shutil.which = lambda name: None
            self.assertIsNone(bfc.live_badge_state())
        finally:
            bfc.shutil.which = real_which
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


class TestLiveBadgeStateViaUv(unittest.TestCase):
    """Task 574: `live_badge_state()` now falls back to `fencepost/
    seam_engine`'s own `uv` venv (the one place `arcade-mcp-server` is
    actually installed) when the bare in-process import fails. Every path
    through `_live_badge_state_via_uv` is exercised here via monkeypatched
    `shutil.which`/`subprocess.run` -- no real `uv` venv required for the
    unit tests themselves, mirroring `recipe_command_check.py`'s own test
    discipline for the identical class of fallback."""

    def setUp(self):
        self._real_which = bfc.shutil.which
        self._real_run = bfc.subprocess.run
        self.addCleanup(setattr, bfc.shutil, "which", self._real_which)
        self.addCleanup(setattr, bfc.subprocess, "run", self._real_run)

    def test_no_uv_on_path_returns_none(self):
        bfc.shutil.which = lambda name: None
        self.assertIsNone(bfc._live_badge_state_via_uv())

    def test_successful_subprocess_parses_stdout(self):
        bfc.shutil.which = lambda name: "/usr/bin/uv"

        class _Proc:
            returncode = 0
            stdout = '{"color": "brightgreen", "message": "6/6 tools read-only"}\n'
            stderr = ""

        bfc.subprocess.run = lambda *a, **k: _Proc()
        result = bfc._live_badge_state_via_uv()
        self.assertEqual(result, {"color": "brightgreen", "message": "6/6 tools read-only"})

    def test_nonzero_exit_returns_none(self):
        bfc.shutil.which = lambda name: "/usr/bin/uv"

        class _Proc:
            returncode = 1
            stdout = ""
            stderr = "uv: command not found"

        bfc.subprocess.run = lambda *a, **k: _Proc()
        self.assertIsNone(bfc._live_badge_state_via_uv())

    def test_empty_stdout_returns_none(self):
        bfc.shutil.which = lambda name: "/usr/bin/uv"

        class _Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        bfc.subprocess.run = lambda *a, **k: _Proc()
        self.assertIsNone(bfc._live_badge_state_via_uv())

    def test_malformed_json_stdout_returns_none(self):
        bfc.shutil.which = lambda name: "/usr/bin/uv"

        class _Proc:
            returncode = 0
            stdout = "not json at all"
            stderr = ""

        bfc.subprocess.run = lambda *a, **k: _Proc()
        self.assertIsNone(bfc._live_badge_state_via_uv())

    def test_missing_expected_keys_returns_none(self):
        bfc.shutil.which = lambda name: "/usr/bin/uv"

        class _Proc:
            returncode = 0
            stdout = '{"color": "brightgreen"}\n'
            stderr = ""

        bfc.subprocess.run = lambda *a, **k: _Proc()
        self.assertIsNone(bfc._live_badge_state_via_uv())

    def test_timeout_returns_none(self):
        bfc.shutil.which = lambda name: "/usr/bin/uv"

        def _raise(*a, **k):
            raise bfc.subprocess.TimeoutExpired(cmd="uv", timeout=60.0)

        bfc.subprocess.run = _raise
        self.assertIsNone(bfc._live_badge_state_via_uv())

    def test_oserror_returns_none(self):
        bfc.shutil.which = lambda name: "/usr/bin/uv"

        def _raise(*a, **k):
            raise OSError("no such file or directory")

        bfc.subprocess.run = _raise
        self.assertIsNone(bfc._live_badge_state_via_uv())

    def test_live_badge_state_falls_back_to_uv_when_in_process_import_fails(self):
        """The end-to-end wiring: `live_badge_state()` itself must reach
        the uv fallback, not just `_live_badge_state_via_uv` in isolation."""
        real_seam_badge = bfc._seam_badge

        def _boom():
            raise ModuleNotFoundError("no module named 'arcade_mcp_server'")

        bfc._seam_badge = _boom
        self.addCleanup(setattr, bfc, "_seam_badge", real_seam_badge)

        bfc.shutil.which = lambda name: "/usr/bin/uv"

        class _Proc:
            returncode = 0
            stdout = '{"color": "red", "message": "via uv fallback"}\n'
            stderr = ""

        bfc.subprocess.run = lambda *a, **k: _Proc()
        result = bfc.live_badge_state()
        self.assertEqual(result, {"color": "red", "message": "via uv fallback"})

    def test_live_badge_state_stays_none_when_both_paths_fail(self):
        real_seam_badge = bfc._seam_badge

        def _boom():
            raise ModuleNotFoundError("no module named 'arcade_mcp_server'")

        bfc._seam_badge = _boom
        self.addCleanup(setattr, bfc, "_seam_badge", real_seam_badge)
        bfc.shutil.which = lambda name: None
        self.assertIsNone(bfc.live_badge_state())

    def test_the_real_uv_fallback_against_the_real_seam_engine_venv(self):
        """Unmocked: if this environment genuinely has `uv` on PATH and the
        `fencepost/seam_engine` venv carries `arcade-mcp-server` (true in a
        full dev checkout), the fallback must return the real, current
        badge state rather than `None` -- proving the fallback actually
        reaches a real venv, not just its own mocks. Skipped, not failed,
        wherever that dependency genuinely isn't present."""
        if bfc.shutil.which("uv") is None:
            self.skipTest("uv not on PATH in this environment")
        result = bfc._live_badge_state_via_uv()
        if result is None:
            self.skipTest("fencepost/seam_engine's uv venv lacks arcade-mcp-server here")
        self.assertIn("color", result)
        self.assertIn("message", result)
        with open(os.path.join(ROOT, "fencepost", "BADGE.json"), encoding="utf-8") as f:
            committed = json.load(f)
        self.assertEqual(result, {"color": committed["color"], "message": committed["message"]})


if __name__ == "__main__":
    unittest.main()
