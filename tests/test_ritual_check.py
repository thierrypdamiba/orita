"""Task 61. Proves tools/ritual_check.py's four local checks each report
correctly against fixture state -- both ledgers intact, a broken ledger,
a stale/missing/pending report, and an X recheck due/not-due -- the same
kind of fixture proof tasks 57-59 gave the tools they consolidate.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


rc = _load("ritual_check", os.path.join(ROOT, "tools", "ritual_check.py"))
xot = _load("_test_ritual_outage_tracker", os.path.join(ROOT, "tools", "x_outage_tracker.py"))

sys.path.insert(0, os.path.join(ROOT, "fencepost", "seam_engine", "src"))
import seam_engine.ledger as seam_ledger  # noqa: E402

# Task 88: check_words() now records a durable entry as a side effect on
# every call, unconditionally (task 87). Most test classes in this file
# call rc.run_ritual_check() incidentally, without caring about words at
# all -- before this module-level guard, every one of those calls would
# have appended a real entry to the REAL HAND/word-check-log.jsonl just
# from running the test suite, the exact "a test run silently wrote to
# the real log" bug class tasks 71/83/85/86 already caught and fixed
# elsewhere. Point the default rc._word_watch() at a throwaway temp LOG
# for the whole module (ROOT stays the real repo, so reads are still
# real); WordFoldCase's own setUp overrides this locally with its own
# fully-isolated module to test word_watch's behavior directly, and
# restores this module-level default afterward via addCleanup.
_safe_word_watch_dir = tempfile.mkdtemp()
_safe_word_watch = _load("_test_module_safe_word_watch", os.path.join(ROOT, "tools", "word_watch.py"))
_safe_word_watch.LOG = os.path.join(_safe_word_watch_dir, "word-check-log.jsonl")


def setUpModule():
    rc._word_watch = lambda: _safe_word_watch


def tearDownModule():
    shutil.rmtree(_safe_word_watch_dir, ignore_errors=True)


def _scan(*, generated_at: str) -> dict:
    return {
        "generated_at": generated_at,
        "repo": "x/orita",
        "window_hours": 24,
        "confidence_bar": 0.7,
        "separation_margin": 0.15,
        "primary_gap": {
            "slug": "milestone-unannounced",
            "headline": "Milestone-level work shipped but never reached the sky",
            "detail": "1 milestone commit(s), none echoed in a post.",
            "confidence": 0.85,
            "evidence": ["https://github.com/x/orita/commit/0000001"],
            "label": "primary",
        },
        "tail": [],
        "excluded": [],
    }


class TownLedgerCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.mod = _load(
            f"_ritual_town_ledger_{id(self)}", os.path.join(ROOT, "tools", "ledger.py")
        )
        self.mod.LEDGER = os.path.join(self.tmpdir, "ledger.jsonl")

    def _patched_check(self):
        mod = self.mod
        entries = mod._entries()
        prev = mod.GENESIS
        for i, e in enumerate(entries):
            e = dict(e)
            h = e.pop("hash")
            if e["prev"] != prev or mod._hash(e, prev) != h:
                return {"ok": False, "count": len(entries), "broken_at_seq": i}
            prev = h
        return {"ok": True, "count": len(entries), "broken_at_seq": None}

    def test_intact_chain(self):
        self.mod.append("nisaba", "test", "one", "2026-07-14T00:00:00+00:00")
        self.mod.append("nisaba", "test", "two", "2026-07-14T00:01:00+00:00")
        result = self._patched_check()
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 2)
        self.assertIsNone(result["broken_at_seq"])

    def test_empty_chain_is_intact(self):
        result = self._patched_check()
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 0)

    def test_tampered_entry_reports_broken_at_seq(self):
        self.mod.append("nisaba", "test", "one", "2026-07-14T00:00:00+00:00")
        self.mod.append("nisaba", "test", "two", "2026-07-14T00:01:00+00:00")
        with open(self.mod.LEDGER) as f:
            lines = f.readlines()
        tampered = json.loads(lines[0])
        tampered["detail"] = "tampered"
        lines[0] = json.dumps(tampered, ensure_ascii=False) + "\n"
        with open(self.mod.LEDGER, "w") as f:
            f.writelines(lines)
        result = self._patched_check()
        self.assertFalse(result["ok"])
        self.assertEqual(result["broken_at_seq"], 0)


class FencepostLedgerCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def test_intact_chain_reports_count(self):
        seam_ledger.append_scan(
            _scan(generated_at="2026-07-14T11:00:00+00:00"),
            now=datetime(2026, 7, 14, tzinfo=timezone.utc),
            base=self.tmpdir,
        )
        result = rc.check_fencepost_ledger(base=str(self.tmpdir))
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["problems"], [])

    def test_no_tablets_yet_is_intact_and_empty(self):
        result = rc.check_fencepost_ledger(base=str(self.tmpdir))
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 0)

    def test_tampered_tablet_is_broken(self):
        tablet = seam_ledger.append_scan(
            _scan(generated_at="2026-07-14T11:00:00+00:00"),
            now=datetime(2026, 7, 14, tzinfo=timezone.utc),
            base=self.tmpdir,
        )
        text = tablet.read_text()
        tablet.write_text(text.replace("milestone commit(s)", "TAMPERED"))
        result = rc.check_fencepost_ledger(base=str(self.tmpdir))
        self.assertFalse(result["ok"])
        self.assertTrue(result["problems"])


class ReportFreshnessCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def _write(self, date_str):
        with open(os.path.join(self.tmpdir, f"{date_str}.md"), "w") as f:
            f.write("report\n")

    def test_current_when_todays_report_exists(self):
        self._write("2026-07-14")
        now = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)
        result = rc.check_report_freshness(now, reports_dir=self.tmpdir)
        self.assertEqual(result["status"], "current")

    def test_pending_when_only_yesterdays_report_exists(self):
        self._write("2026-07-13")
        now = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)
        result = rc.check_report_freshness(now, reports_dir=self.tmpdir)
        self.assertEqual(result["status"], "pending")
        self.assertTrue(result["fallback_path"].endswith("2026-07-13.md"))

    def test_stale_when_neither_report_exists(self):
        now = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)
        result = rc.check_report_freshness(now, reports_dir=self.tmpdir)
        self.assertEqual(result["status"], "stale")
        self.assertIsNone(result["fallback_path"])


class XRecheckCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.log = os.path.join(self.tmpdir, "x-outage-log.jsonl")

    def test_never_checked_is_due(self):
        result = self._check(now_iso="2026-07-14T12:00:00Z")
        for tool in ("X_PostTweet", "X_GetUserTweets"):
            self.assertTrue(result[tool]["due"])

    def test_recent_check_is_not_due(self):
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T11:00:00Z", path=self.log)
        result = self._check(now_iso="2026-07-14T11:30:00Z")
        self.assertFalse(result["X_PostTweet"]["due"])

    def test_old_check_is_due(self):
        xot.record_check("X_PostTweet", "forbidden", "2026-07-14T08:00:00Z", path=self.log)
        result = self._check(now_iso="2026-07-14T12:00:00Z")
        self.assertTrue(result["X_PostTweet"]["due"])

    def _check(self, now_iso):
        entries = xot._entries(self.log)
        result = {}
        for tool in xot.TRACKED_TOOLS:
            result[tool] = {
                "due": xot.should_recheck(entries, tool, now_iso, 2.0),
                "status_line": xot.format_status_line(entries, tool),
            }
        return result


class XEscalationCase(unittest.TestCase):
    """Task 83: check_x_escalation folds x_outage_tracker.should_escalate
    (task 81) into the same structured result check_x_recheck already
    covers, mirroring its exact read-only shape -- no write of its own."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.xot = _load(f"_test_ritual_outage_tracker_{id(self)}", os.path.join(ROOT, "tools", "x_outage_tracker.py"))
        self.xot.LOG = os.path.join(self.tmpdir, "x-outage-log.jsonl")
        self.xot.ESCALATION_LOG = os.path.join(self.tmpdir, "escalations.jsonl")
        original_loader = rc._outage_tracker
        rc._outage_tracker = lambda: self.xot
        self.addCleanup(setattr, rc, "_outage_tracker", original_loader)

    def test_no_active_outage_is_not_due(self):
        self.xot.record_check("X_PostTweet", "ok", "2026-07-14T00:00:00Z", path=self.xot.LOG)
        result = rc.check_x_escalation("2026-07-14T12:00:00Z")
        self.assertFalse(result["X_PostTweet"]["due"])
        self.assertIn("no active outage", result["X_PostTweet"]["reason"])

    def test_below_threshold_is_not_due(self):
        self.xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.xot.LOG)
        result = rc.check_x_escalation("2026-07-14T10:00:00Z")
        self.assertFalse(result["X_PostTweet"]["due"])
        self.assertIn("below", result["X_PostTweet"]["reason"])

    def test_past_threshold_is_due(self):
        self.xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.xot.LOG)
        result = rc.check_x_escalation("2026-07-16T01:00:00Z")
        self.assertTrue(result["X_PostTweet"]["due"])
        self.assertIn("crosses", result["X_PostTweet"]["reason"])

    def test_already_escalated_for_streak_is_not_due(self):
        self.xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.xot.LOG)
        self.xot.record_escalation("X_PostTweet", "2026-07-14T00:00:00Z", "2026-07-16T01:00:00Z", 49.0, path=self.xot.ESCALATION_LOG)
        result = rc.check_x_escalation("2026-07-16T02:00:00Z")
        self.assertFalse(result["X_PostTweet"]["due"])
        self.assertIn("already escalated", result["X_PostTweet"]["reason"])

    def test_result_covers_all_tracked_tools(self):
        result = rc.check_x_escalation("2026-07-14T12:00:00Z")
        self.assertEqual(set(result.keys()), set(self.xot.TRACKED_TOOLS))

    def test_a_streak_already_escalated_at_48h_still_surfaces_the_168h_tier(self):
        """Task 92: check_x_escalation reads the worst crossed-and-unfired
        tier, not a single fixed threshold -- a real outage this old should
        surface as due again, not read "already escalated" forever."""
        self.xot.record_check("X_PostTweet", "forbidden", "2026-07-14T00:00:00Z", path=self.xot.LOG)
        self.xot.record_escalation(
            "X_PostTweet", "2026-07-14T00:00:00Z", "2026-07-16T01:00:00Z", 49.0,
            threshold_hours=48.0, path=self.xot.ESCALATION_LOG,
        )
        result = rc.check_x_escalation("2026-07-21T01:00:00Z")
        self.assertTrue(result["X_PostTweet"]["due"])
        self.assertEqual(result["X_PostTweet"]["threshold_hours"], 168.0)
        self.assertIn("crosses 168.0h threshold", result["X_PostTweet"]["reason"])


class SquareFoldCase(unittest.TestCase):
    """Task 71: run_ritual_check(square_state=...) folds square_check.py's
    durable comparison into the same structured result, without either tool
    making a network call of its own."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.sq = _load(f"_test_ritual_square_check_{id(self)}", os.path.join(ROOT, "tools", "square_check.py"))
        self.sq.LOG = os.path.join(self.tmpdir, "square-check-log.jsonl")
        # rc.check_square loads its own fresh copy of square_check.py via
        # _load(), so point rc at the same module instance/log for this test,
        # restoring the original loader after so other tests are unaffected.
        original_loader = rc._square_check
        rc._square_check = lambda: self.sq
        self.addCleanup(setattr, rc, "_square_check", original_loader)

    def test_no_square_state_is_none(self):
        self.assertIsNone(rc.check_square(None, "2026-07-14T21:00:00Z"))

    def test_first_check_is_changed(self):
        state = self.sq.compute_square_state(
            [{"number": 1, "updated_at": "2026-07-12T06:43:35Z"}], []
        )
        result = rc.check_square(state, "2026-07-14T21:00:00Z")
        self.assertTrue(result["changed"])
        self.assertIn("no prior square check recorded", result["reason"])

    def test_unchanged_after_recording(self):
        state = self.sq.compute_square_state(
            [{"number": 1, "updated_at": "2026-07-12T06:43:35Z"}], []
        )
        self.sq.record_square_check(state, "2026-07-14T21:00:00Z", path=self.sq.LOG)
        result = rc.check_square(state, "2026-07-14T22:00:00Z")
        self.assertFalse(result["changed"])
        self.assertIn("unchanged since", result["reason"])

    def test_new_issue_is_changed(self):
        old = self.sq.compute_square_state(
            [{"number": 1, "updated_at": "2026-07-12T06:43:35Z"}], []
        )
        self.sq.record_square_check(old, "2026-07-14T21:00:00Z", path=self.sq.LOG)
        new = self.sq.compute_square_state(
            [
                {"number": 1, "updated_at": "2026-07-12T06:43:35Z"},
                {"number": 6, "updated_at": "2026-07-14T22:00:00Z"},
            ],
            [],
        )
        result = rc.check_square(new, "2026-07-14T22:05:00Z")
        self.assertTrue(result["changed"])

    def test_check_square_records_so_next_call_reads_it_back(self):
        state = self.sq.compute_square_state(
            [{"number": 1, "updated_at": "2026-07-12T06:43:35Z"}], []
        )
        rc.check_square(state, "2026-07-14T21:00:00Z")
        with open(self.sq.LOG) as f:
            lines = [line for line in f.read().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertIn('"checked_at": "2026-07-14T21:00:00Z"', lines[0])

    def test_a_real_change_settles_into_new_baseline_next_call(self):
        """Task 88's regression case: before the fix, `check_square` never
        recorded, so a real change would compare against the SAME stale
        pre-change baseline every subsequent hour and report "changed"
        forever, never settling. It must settle on the very next call."""
        old = self.sq.compute_square_state(
            [{"number": 1, "updated_at": "2026-07-12T06:43:35Z"}], []
        )
        self.sq.record_square_check(old, "2026-07-14T21:00:00Z", path=self.sq.LOG)
        new = self.sq.compute_square_state(
            [
                {"number": 1, "updated_at": "2026-07-12T06:43:35Z"},
                {"number": 6, "updated_at": "2026-07-14T22:00:00Z"},
            ],
            [],
        )
        first = rc.check_square(new, "2026-07-14T22:05:00Z")
        self.assertTrue(first["changed"])
        second = rc.check_square(new, "2026-07-14T23:05:00Z")
        self.assertFalse(second["changed"])
        self.assertIn("unchanged since", second["reason"])

    def test_run_ritual_check_folds_square_key(self):
        state = self.sq.compute_square_state(
            [{"number": 1, "updated_at": "2026-07-12T06:43:35Z"}], []
        )
        result = rc.run_ritual_check(square_state=state)
        self.assertIsNotNone(result["square"])
        self.assertIn("changed", result["square"])

    def test_run_ritual_check_square_none_when_omitted(self):
        result = rc.run_ritual_check()
        self.assertIsNone(result["square"])

    def test_format_includes_square_line_only_when_present(self):
        with_square = rc.format_ritual_check(
            {**rc.run_ritual_check(), "square": {"changed": False, "reason": "unchanged since X"}}
        )
        self.assertIn("square: unchanged -- unchanged since X", with_square)
        without_square = rc.format_ritual_check(rc.run_ritual_check())
        self.assertNotIn("square:", without_square)


class ArcadeAppsFoldCase(unittest.TestCase):
    """Task 125: run_ritual_check(arcade_apps_state=...) folds task 122's
    arcade_app_watch.py into the same structured result -- SquareFoldCase's
    exact shape, since check_arcade_apps mirrors check_square line for line
    (caller-supplied state, no network call of its own, delta computed
    before the state is recorded so a real change is never compared
    against itself)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.aw = _load(
            f"_test_ritual_arcade_app_watch_{id(self)}", os.path.join(ROOT, "tools", "arcade_app_watch.py")
        )
        self.aw.LOG = os.path.join(self.tmpdir, "arcade-app-check-log.jsonl")
        original_loader = rc._arcade_app_watch
        rc._arcade_app_watch = lambda: self.aw
        self.addCleanup(setattr, rc, "_arcade_app_watch", original_loader)

    def _state(self, apps):
        return self.aw.compute_app_state(apps)

    def test_no_arcade_apps_state_is_none(self):
        self.assertIsNone(rc.check_arcade_apps(None, "2026-07-18T06:00:00Z"))

    def test_first_check_is_changed(self):
        state = self._state([{"app_id": "arcade-github", "connected": True, "permissions": ["repo"]}])
        result = rc.check_arcade_apps(state, "2026-07-18T06:00:00Z")
        self.assertTrue(result["changed"])
        self.assertIn("no prior app check recorded", result["reason"])

    def test_unchanged_after_recording(self):
        state = self._state([{"app_id": "arcade-github", "connected": True, "permissions": ["repo"]}])
        self.aw.record_app_check(state, "2026-07-18T06:00:00Z", path=self.aw.LOG)
        result = rc.check_arcade_apps(state, "2026-07-18T07:00:00Z")
        self.assertFalse(result["changed"])
        self.assertIn("unchanged, still connected", result["reason"])

    def test_newly_connected_app_is_changed(self):
        old = self._state([{"app_id": "arcade-github", "connected": True, "permissions": ["repo"]}])
        self.aw.record_app_check(old, "2026-07-18T06:00:00Z", path=self.aw.LOG)
        new = self._state(
            [
                {"app_id": "arcade-github", "connected": True, "permissions": ["repo"]},
                {"app_id": "arcade-google", "connected": True, "permissions": ["gmail.readonly"]},
            ]
        )
        result = rc.check_arcade_apps(new, "2026-07-18T07:00:00Z")
        self.assertTrue(result["changed"])
        self.assertIn("newly connected: arcade-google", result["reason"])

    def test_newly_disconnected_app_is_changed(self):
        old = self._state(
            [
                {"app_id": "arcade-github", "connected": True, "permissions": ["repo"]},
                {"app_id": "arcade-slack", "connected": True, "permissions": []},
            ]
        )
        self.aw.record_app_check(old, "2026-07-18T06:00:00Z", path=self.aw.LOG)
        new = self._state([{"app_id": "arcade-github", "connected": True, "permissions": ["repo"]}])
        result = rc.check_arcade_apps(new, "2026-07-18T07:00:00Z")
        self.assertTrue(result["changed"])
        self.assertIn("newly disconnected: arcade-slack", result["reason"])

    def test_scope_change_on_already_connected_app_is_changed(self):
        old = self._state([{"app_id": "arcade-google", "connected": True, "permissions": ["gmail.readonly"]}])
        self.aw.record_app_check(old, "2026-07-18T06:00:00Z", path=self.aw.LOG)
        new = self._state(
            [{"app_id": "arcade-google", "connected": True, "permissions": ["gmail.readonly", "calendar.readonly"]}]
        )
        result = rc.check_arcade_apps(new, "2026-07-18T07:00:00Z")
        self.assertTrue(result["changed"])
        self.assertIn("scope change on already-connected app(s)", result["reason"])

    def test_check_arcade_apps_records_so_next_call_reads_it_back(self):
        state = self._state([{"app_id": "arcade-github", "connected": True, "permissions": ["repo"]}])
        rc.check_arcade_apps(state, "2026-07-18T06:00:00Z")
        with open(self.aw.LOG) as f:
            lines = [line for line in f.read().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertIn('"checked_at": "2026-07-18T06:00:00Z"', lines[0])

    def test_a_real_change_settles_into_new_baseline_next_call(self):
        """Same regression class task 88 fixed for check_square: the delta
        must be computed against the PRIOR baseline, then recorded, so a
        real change settles on the very next call instead of comparing
        against the same stale pre-change state forever."""
        old = self._state([{"app_id": "arcade-github", "connected": True, "permissions": ["repo"]}])
        self.aw.record_app_check(old, "2026-07-18T06:00:00Z", path=self.aw.LOG)
        new = self._state(
            [
                {"app_id": "arcade-github", "connected": True, "permissions": ["repo"]},
                {"app_id": "arcade-google", "connected": True, "permissions": ["gmail.readonly"]},
            ]
        )
        first = rc.check_arcade_apps(new, "2026-07-18T07:00:00Z")
        self.assertTrue(first["changed"])
        second = rc.check_arcade_apps(new, "2026-07-18T08:00:00Z")
        self.assertFalse(second["changed"])
        self.assertIn("unchanged, still connected", second["reason"])

    def test_run_ritual_check_folds_arcade_apps_key(self):
        state = self._state([{"app_id": "arcade-github", "connected": True, "permissions": ["repo"]}])
        result = rc.run_ritual_check(arcade_apps_state=state)
        self.assertIsNotNone(result["arcade_apps"])
        self.assertIn("changed", result["arcade_apps"])

    def test_run_ritual_check_arcade_apps_none_when_omitted(self):
        result = rc.run_ritual_check()
        self.assertIsNone(result["arcade_apps"])
        self.assertFalse(result["broken"])

    def test_format_includes_arcade_apps_line_only_when_present(self):
        with_state = rc.format_ritual_check(
            {**rc.run_ritual_check(), "arcade_apps": {"changed": False, "reason": "unchanged, still connected: arcade-github"}}
        )
        self.assertIn("arcade apps: unchanged -- unchanged, still connected: arcade-github", with_state)
        without_state = rc.format_ritual_check(rc.run_ritual_check())
        self.assertNotIn("arcade apps:", without_state)

    def test_arcade_apps_change_never_flips_broken(self):
        old = self._state([{"app_id": "arcade-github", "connected": True, "permissions": ["repo"]}])
        self.aw.record_app_check(old, "2026-07-18T06:00:00Z", path=self.aw.LOG)
        new = self._state(
            [
                {"app_id": "arcade-github", "connected": True, "permissions": ["repo"]},
                {"app_id": "arcade-google", "connected": True, "permissions": ["gmail.readonly"]},
            ]
        )
        result = rc.run_ritual_check(arcade_apps_state=new)
        self.assertTrue(result["arcade_apps"]["changed"])
        self.assertFalse(result["broken"])


class ScribeGrowthFoldCase(unittest.TestCase):
    """Task 168: run_ritual_check() folds tools/scribe_growth_check.py's
    real ROADMAP.md/BUILDLOG.md byte sizes in -- unlike square/arcade_apps,
    this makes its OWN filesystem read (no caller-supplied live-API state
    needed) so it runs unconditionally on every call, including a bare
    rc.run_ritual_check() with no arguments.

    Task 374: reading (folding sizes into the result dict) and recording
    (durably writing this hour's sizes to the log) are two different
    things. Every test below scopes `self.sgc.LOG` to a tmpdir, so none of
    them ever risk the real `HAND/scribe-growth-log.jsonl` -- the
    write-by-default bug this class's own new tests below prove fixed was
    only ever reachable through the real, unmocked module (a bare hand-run
    `python3 tools/ritual_check.py`, or `rc.run_ritual_check()` called
    directly against the real repo with no loader patched in), which is
    exactly what `WriteDefaultFoldCase` below reproduces and proves fixed."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        with open(os.path.join(self.tmpdir, "ROADMAP.md"), "w") as f:
            f.write("x" * 100)
        with open(os.path.join(self.tmpdir, "BUILDLOG.md"), "w") as f:
            f.write("x" * 50)
        self.sgc = _load(
            f"_test_ritual_scribe_growth_check_{id(self)}", os.path.join(ROOT, "tools", "scribe_growth_check.py")
        )
        self.sgc.LOG = os.path.join(self.tmpdir, "scribe-growth-log.jsonl")
        original_loader = rc._scribe_growth_check
        rc._scribe_growth_check = lambda: self.sgc
        self.addCleanup(setattr, rc, "_scribe_growth_check", original_loader)

    def test_reads_real_sizes_off_the_given_root(self):
        result = rc.check_scribe_growth("2026-07-20T06:00:00Z", scribe_root=self.tmpdir)
        self.assertEqual(result["sizes"], {"ROADMAP.md": 100, "BUILDLOG.md": 50})
        self.assertTrue(result["clean"])

    def test_records_so_next_call_reads_it_back(self):
        rc.check_scribe_growth("2026-07-20T06:00:00Z", scribe_root=self.tmpdir)
        with open(self.sgc.LOG) as f:
            lines = [line for line in f.read().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertIn('"checked_at": "2026-07-20T06:00:00Z"', lines[0])

    def test_growth_settles_against_the_prior_baseline_next_call(self):
        rc.check_scribe_growth("2026-07-20T06:00:00Z", scribe_root=self.tmpdir)
        with open(os.path.join(self.tmpdir, "ROADMAP.md"), "w") as f:
            f.write("x" * 140)
        result = rc.check_scribe_growth("2026-07-20T07:00:00Z", scribe_root=self.tmpdir)
        self.assertEqual(result["growth_since_last_check"]["ROADMAP.md"], 40)

    def test_run_ritual_check_folds_scribe_growth_key_with_no_arguments(self):
        # No scribe_root override: proves a bare rc.run_ritual_check() call
        # (the same shape tests elsewhere in this file already make) reads
        # the real repo's ROADMAP.md/BUILDLOG.md without erroring.
        result = rc.run_ritual_check()
        self.assertIn("ROADMAP.md", result["scribe_growth"]["sizes"])
        self.assertIn("BUILDLOG.md", result["scribe_growth"]["sizes"])

    def test_scribe_growth_over_threshold_never_flips_broken(self):
        original_warn = self.sgc.WARN_BYTES
        self.sgc.WARN_BYTES = 10
        self.addCleanup(setattr, self.sgc, "WARN_BYTES", original_warn)
        result = rc.run_ritual_check(scribe_root=self.tmpdir)
        self.assertFalse(result["scribe_growth"]["clean"])
        self.assertFalse(result["broken"])

    def test_format_includes_scribe_growth_line(self):
        formatted = rc.format_ritual_check(rc.run_ritual_check(scribe_root=self.tmpdir))
        self.assertIn("scribe growth: clean", formatted)
        self.assertIn("ROADMAP.md", formatted)

    def test_run_ritual_check_default_does_not_record(self):
        """Task 374: a bare/library rc.run_ritual_check() call (the shape
        every dev-verification and every other test in this file already
        makes) must not write to the scribe-growth log by default."""
        rc.run_ritual_check(scribe_root=self.tmpdir)
        self.assertFalse(os.path.exists(self.sgc.LOG))

    def test_run_ritual_check_records_only_when_asked(self):
        rc.run_ritual_check(scribe_root=self.tmpdir, record_scribe_growth=True)
        with open(self.sgc.LOG) as f:
            lines = [line for line in f.read().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)

    def test_run_ritual_check_default_still_folds_sizes_even_unrecorded(self):
        """Not recording must not mean not reading -- the returned dict
        still carries this hour's real sizes either way."""
        result = rc.run_ritual_check(scribe_root=self.tmpdir)
        self.assertEqual(result["scribe_growth"]["sizes"], {"ROADMAP.md": 100, "BUILDLOG.md": 50})
        self.assertFalse(os.path.exists(self.sgc.LOG))


class ScribeGrowthWriteDefaultCase(unittest.TestCase):
    """Task 374: the real bug lived in the REAL, unmocked module -- every
    other test in this file (including ScribeGrowthFoldCase above) patches
    `rc._scribe_growth_check` to a tmpdir-scoped copy, which never touched
    the real repo's `HAND/scribe-growth-log.jsonl` even before this fix.
    The actual pollution came from the real CLI / a bare `rc.run_ritual_check()`
    call with NOTHING patched, run against the real repo -- exactly what a
    god does mid-task to sanity-check state. These tests exercise the real,
    unpatched module directly (still scoped to a tmpdir root via
    `scribe_root`, but NOT via a patched loader) to prove the write-by-default
    class of bug is closed at its actual source."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        with open(os.path.join(self.tmpdir, "ROADMAP.md"), "w") as f:
            f.write("x" * 10)
        with open(os.path.join(self.tmpdir, "BUILDLOG.md"), "w") as f:
            f.write("x" * 10)
        # Real module, real LOG constant -- redirected to a tmp file so this
        # test can prove "did it write" without ever touching the real
        # production log, not because the module itself is mocked.
        real_sgc = _load("_test_real_scribe_growth_check", os.path.join(ROOT, "tools", "scribe_growth_check.py"))
        real_sgc.LOG = os.path.join(self.tmpdir, "scribe-growth-log.jsonl")
        original_loader = rc._scribe_growth_check
        rc._scribe_growth_check = lambda: real_sgc
        self.addCleanup(setattr, rc, "_scribe_growth_check", original_loader)
        self.log_path = real_sgc.LOG

    def test_bare_call_against_the_real_module_does_not_write(self):
        rc.run_ritual_check(scribe_root=self.tmpdir)
        self.assertFalse(os.path.exists(self.log_path))

    def test_cli_main_records_for_real(self):
        """main() is the one real hourly entrypoint -- it must still
        record, exactly once per invocation, unchanged from before this
        fix. main() doesn't take a scribe_root flag (scribe growth always
        watches the real repo's own ROADMAP.md/BUILDLOG.md in production),
        so this wraps run_ritual_check to both capture its kwargs (proving
        main() explicitly asks for recording) and redirect scribe_root to
        this test's tmpdir (proving the write actually lands, without ever
        touching the real repo's own tracked files)."""
        captured = {}
        original = rc.run_ritual_check

        def capturing(*args, **kwargs):
            captured.update(kwargs)
            return original(*args, **{**kwargs, "scribe_root": self.tmpdir})

        rc.run_ritual_check = capturing
        try:
            rc.main([])
        finally:
            rc.run_ritual_check = original
        self.assertTrue(captured.get("record_scribe_growth") is True)
        with open(self.log_path) as f:
            lines = [line for line in f.read().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)


class CIFoldCase(unittest.TestCase):
    """Task 73: run_ritual_check(ci_checks=...) folds ci_watch.py's durable
    CI-conclusion log into the same structured result, the same shape task
    71 already gave the square. Unlike the square, ci_checks are recorded
    (not just compared) so the printed status line always reflects this
    hour's real observation -- the one durable write ritual_check.py makes,
    scoped to a local append-only log, no network call of its own."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.ciw = _load(f"_test_ritual_ci_watch_{id(self)}", os.path.join(ROOT, "tools", "ci_watch.py"))
        self.ciw.LOG = os.path.join(self.tmpdir, "ci-watch-log.jsonl")
        original_loader = rc._ci_watch
        rc._ci_watch = lambda: self.ciw
        self.addCleanup(setattr, rc, "_ci_watch", original_loader)

    def test_no_ci_checks_is_none(self):
        self.assertIsNone(rc.check_ci(None))

    def test_recording_a_success_reports_it(self):
        result = rc.check_ci(
            [{"workflow": "dawn-run", "conclusion": "success", "run_id": 1, "checked_at": "2026-07-14T23:08:01Z"}]
        )
        self.assertEqual(result["dawn-run"], "dawn-run: success as of 2026-07-14T23:08:01Z (run 1)")

    def test_only_supplied_workflows_move_the_others_stay_unrecorded(self):
        result = rc.check_ci(
            [{"workflow": "dawn-run", "conclusion": "success", "run_id": 1, "checked_at": "2026-07-14T23:08:01Z"}]
        )
        self.assertEqual(result["pages"], "pages: no checks recorded")

    def test_a_recorded_failure_streak_survives_across_calls(self):
        rc.check_ci([{"workflow": "dawn-run", "conclusion": "failure", "run_id": 1, "checked_at": "2026-07-14T11:00:00Z"}])
        result = rc.check_ci(
            [{"workflow": "dawn-run", "conclusion": "failure", "run_id": 2, "checked_at": "2026-07-14T12:00:00Z"}]
        )
        self.assertIn("2 consecutive failure checks", result["dawn-run"])

    def test_run_ritual_check_folds_ci_key(self):
        result = rc.run_ritual_check(
            ci_checks=[
                {"workflow": "dawn-run", "conclusion": "success", "run_id": 1, "checked_at": "2026-07-14T23:08:01Z"},
                {"workflow": "pages", "conclusion": "success", "run_id": 2, "checked_at": "2026-07-14T23:08:01Z"},
            ]
        )
        self.assertIsNotNone(result["ci"])
        self.assertIn("dawn-run", result["ci"])
        self.assertIn("pages", result["ci"])

    def test_run_ritual_check_ci_none_when_omitted(self):
        result = rc.run_ritual_check()
        self.assertIsNone(result["ci"])

    def test_format_includes_ci_lines_only_when_present(self):
        with_ci = rc.format_ritual_check(
            {**rc.run_ritual_check(), "ci": {"dawn-run": "dawn-run: success as of X (run 1)"}}
        )
        self.assertIn("ci/dawn-run: dawn-run: success as of X (run 1)", with_ci)
        without_ci = rc.format_ritual_check(rc.run_ritual_check())
        self.assertNotIn("ci/", without_ci)


class CronFoldCase(unittest.TestCase):
    """Task 82: run_ritual_check(cron_checks=...) folds cron_health.py's
    schedule_status() into the same structured result, the identical
    live-API-input-but-no-network-call shape task 73 already proved for
    ci_checks -- cron_health's own docstring once claimed it could never
    join this fold; this proves that claim was wrong."""

    def test_no_cron_checks_is_none(self):
        self.assertIsNone(rc.check_cron(None, "2026-07-16T08:00:00Z"))

    def test_on_time_workflow_reports_on_time(self):
        result = rc.check_cron(
            [{"workflow": "seam-scan", "cron_expr": "0 12 * * *", "last_run_at": "2026-07-15T12:05:00Z"}],
            "2026-07-16T08:00:00Z",
        )
        self.assertEqual(result["seam-scan"]["status"], "on_time")

    def test_overdue_workflow_reports_overdue(self):
        result = rc.check_cron(
            [{"workflow": "oracle-cadence", "cron_expr": "0 13 * * *", "last_run_at": "2026-07-14T13:00:00Z"}],
            "2026-07-16T08:00:00Z",
        )
        self.assertEqual(result["oracle-cadence"]["status"], "overdue")

    def test_unparseable_cron_reports_error_not_crash(self):
        result = rc.check_cron(
            [{"workflow": "weird", "cron_expr": "0 12 1 * *", "last_run_at": None}],
            "2026-07-16T08:00:00Z",
        )
        self.assertEqual(result["weird"]["status"], "error")
        self.assertIn("only fixed-hour daily crons", result["weird"]["error"])

    def test_run_ritual_check_folds_cron_key(self):
        result = rc.run_ritual_check(
            cron_checks=[
                {"workflow": "seam-scan", "cron_expr": "0 12 * * *", "last_run_at": "2026-07-15T12:05:00Z"},
            ]
        )
        self.assertIsNotNone(result["cron"])
        self.assertIn("seam-scan", result["cron"])

    def test_run_ritual_check_cron_none_when_omitted(self):
        result = rc.run_ritual_check()
        self.assertIsNone(result["cron"])

    def test_format_includes_cron_lines_only_when_present(self):
        with_cron = rc.format_ritual_check(
            {
                **rc.run_ritual_check(),
                "cron": {
                    "seam-scan": {
                        "status": "on_time",
                        "due_at": "2026-07-15T12:00:00+00:00",
                        "last_run_at": "2026-07-15T12:05:00Z",
                        "hours_late": None,
                    }
                },
            }
        )
        self.assertIn("cron/seam-scan: on_time", with_cron)
        without_cron = rc.format_ritual_check(rc.run_ritual_check())
        self.assertNotIn("cron/", without_cron)

    def test_format_includes_error_line_for_unparseable_cron(self):
        with_error = rc.format_ritual_check(
            {**rc.run_ritual_check(), "cron": {"weird": {"status": "error", "error": "bad cron"}}}
        )
        self.assertIn("cron/weird: error -- bad cron", with_error)


class WordFoldCase(unittest.TestCase):
    """Task 74: run_ritual_check() folds word_watch.py's durable "has a new
    word from Thierry landed" check into the same structured result, the
    same shape tasks 71/73 already gave the square and CI. Task 87 made it
    unconditional, mirroring OwedPostsFoldCase's own shape exactly -- local
    filesystem only, no network call, the identical cheap-enough-to-skip-
    the-flag class task 85's own docstring already argued for."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        os.makedirs(os.path.join(self.tmpdir, "DECREES"))
        os.makedirs(os.path.join(self.tmpdir, "HAND", "verdicts"))
        with open(os.path.join(self.tmpdir, "DECREES", "001.md"), "w") as f:
            f.write("a decree\n")
        self.ww = _load(f"_test_ritual_word_watch_{id(self)}", os.path.join(ROOT, "tools", "word_watch.py"))
        self.ww.ROOT = self.tmpdir
        self.ww.LOG = os.path.join(self.tmpdir, "HAND", "word-check-log.jsonl")
        original_loader = rc._word_watch
        rc._word_watch = lambda: self.ww
        self.addCleanup(setattr, rc, "_word_watch", original_loader)

    def test_check_words_takes_no_flag(self):
        result = rc.check_words("2026-07-16T14:00:00Z")
        self.assertTrue(result["changed"])
        self.assertIn("no prior word check", result["reason"])

    def test_check_words_records_so_a_later_unchanged_call_settles(self):
        """Task 88's regression case for words, mirroring the square one:
        before the fix, a real word landing would report "changed" every
        hour forever since nothing ever advanced the baseline."""
        first = rc.check_words("2026-07-16T14:00:00Z")
        self.assertTrue(first["changed"])
        second = rc.check_words("2026-07-16T15:00:00Z")
        self.assertFalse(second["changed"])
        self.assertIn("unchanged since", second["reason"])

    def test_run_ritual_check_always_folds_words_key(self):
        result = rc.run_ritual_check()
        self.assertIsNotNone(result["words"])
        self.assertIn("changed", result["words"])

    def test_format_always_includes_words_line(self):
        formatted = rc.format_ritual_check(rc.run_ritual_check())
        self.assertIn("words: changed -- ", formatted)

    def test_run_ritual_check_default_does_not_record(self):
        """Task 375: a bare/library rc.run_ritual_check() call (the shape
        every dev-verification and every other test in this file already
        makes) must not write to the word-check log by default -- mirrors
        ScribeGrowthFoldCase.test_run_ritual_check_default_does_not_record
        (task 374), the identical fix for the sibling that task's own
        closing note named and left unfixed."""
        rc.run_ritual_check()
        self.assertFalse(os.path.exists(self.ww.LOG))

    def test_run_ritual_check_records_only_when_asked(self):
        rc.run_ritual_check(record_words=True)
        with open(self.ww.LOG) as f:
            lines = [line for line in f.read().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)

    def test_run_ritual_check_default_still_folds_words_even_unrecorded(self):
        """Not recording must not mean not reading -- the returned dict
        still carries this hour's real "changed" verdict either way."""
        result = rc.run_ritual_check()
        self.assertTrue(result["words"]["changed"])
        self.assertFalse(os.path.exists(self.ww.LOG))


class WordWriteDefaultCase(unittest.TestCase):
    """Task 375: mirrors ScribeGrowthWriteDefaultCase (task 374) exactly.
    The real pollution lived in the REAL, unmocked `word_watch` module --
    every other test in this file (including WordFoldCase above) patches
    `rc._word_watch` to a tmpdir-scoped copy, which never touched the real
    repo's `HAND/word-check-log.jsonl` even before this fix. The actual
    pollution came from the real CLI / a bare `rc.run_ritual_check()` call
    with NOTHING patched, run against the real repo -- exactly what a god
    does mid-task to sanity-check state (confirmed live this task: a bare,
    unpatched `rc.check_words(...)` call against the real repo appended one
    real line, 744 -> 745). These tests exercise the real, unpatched module
    directly (still scoped to a tmpdir root/log via module attributes, but
    NOT via a patched loader) to prove the write-by-default class of bug is
    closed at its actual source."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        os.makedirs(os.path.join(self.tmpdir, "DECREES"))
        with open(os.path.join(self.tmpdir, "DECREES", "001.md"), "w") as f:
            f.write("a decree\n")
        # scribe_growth_check.compute_scribe_sizes() raises FileNotFoundError
        # on a missing tracked file -- main() folds it in on every call
        # (test_cli_main_records_for_real below runs the real main()), so
        # this tmpdir needs both tracked files to exist, mirroring
        # ScribeGrowthWriteDefaultCase's own setUp exactly.
        with open(os.path.join(self.tmpdir, "ROADMAP.md"), "w") as f:
            f.write("x" * 10)
        with open(os.path.join(self.tmpdir, "BUILDLOG.md"), "w") as f:
            f.write("x" * 10)
        # Real module, real ROOT/LOG constants -- redirected to a tmpdir so
        # this test can prove "did it write" without ever touching the real
        # production log, not because the module itself is mocked.
        real_ww = _load("_test_real_word_watch", os.path.join(ROOT, "tools", "word_watch.py"))
        real_ww.ROOT = self.tmpdir
        real_ww.LOG = os.path.join(self.tmpdir, "word-check-log.jsonl")
        original_word_loader = rc._word_watch
        rc._word_watch = lambda: real_ww
        self.addCleanup(setattr, rc, "_word_watch", original_word_loader)
        self.log_path = real_ww.LOG
        # test_cli_main_records_for_real below calls the real rc.main([]),
        # which folds check_scribe_growth in on every call too -- redirect
        # its LOG the same way, or proving the words fix in isolation would
        # incidentally write a real line to the production
        # HAND/scribe-growth-log.jsonl as an untested side effect (caught
        # live while writing this test: it did, once, before this guard was
        # added -- reverted, same discipline as every other stray line this
        # task's own dev-verification runs left behind).
        real_sgc = _load("_test_real_scribe_growth_check_for_words", os.path.join(ROOT, "tools", "scribe_growth_check.py"))
        real_sgc.LOG = os.path.join(self.tmpdir, "scribe-growth-log.jsonl")
        original_scribe_loader = rc._scribe_growth_check
        rc._scribe_growth_check = lambda: real_sgc
        self.addCleanup(setattr, rc, "_scribe_growth_check", original_scribe_loader)

    def test_bare_call_against_the_real_module_does_not_write(self):
        rc.run_ritual_check(scribe_root=self.tmpdir)
        self.assertFalse(os.path.exists(self.log_path))

    def test_cli_main_records_for_real(self):
        """main() is the one real hourly entrypoint -- it must still
        record, exactly once per invocation, unchanged from before this
        fix. main() takes no words-root flag (words always watches the
        real repo's own DECREES/HAND/ in production, which this test
        redirects via the patched `_word_watch` loader above instead), so
        this wraps run_ritual_check to both capture its kwargs (proving
        main() explicitly asks for recording) and redirect scribe_root to
        this test's tmpdir -- the same discipline
        ScribeGrowthWriteDefaultCase.test_cli_main_records_for_real already
        holds, needed here too since main() folds both checks every call
        and this test must not touch the real repo's own
        HAND/scribe-growth-log.jsonl as a side effect of proving the words
        fix."""
        captured = {}
        original = rc.run_ritual_check

        def capturing(*args, **kwargs):
            captured.update(kwargs)
            return original(*args, **{**kwargs, "scribe_root": self.tmpdir})

        rc.run_ritual_check = capturing
        try:
            rc.main([])
        finally:
            rc.run_ritual_check = original
        self.assertTrue(captured.get("record_words") is True)
        with open(self.log_path) as f:
            lines = [line for line in f.read().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)


class OwedPostsFoldCase(unittest.TestCase):
    """Task 85: run_ritual_check() folds x_post_queue.py's durable owed-post
    backlog count into the same structured result, mirroring WordFoldCase's
    shape (task 74) but unconditional -- reading one append-only jsonl is
    cheap enough that there's no flag to skip it, the same class as
    check_town_ledger/check_x_recheck."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.xpq = _load(f"_test_ritual_x_post_queue_{id(self)}", os.path.join(ROOT, "tools", "x_post_queue.py"))
        self.xpq.QUEUE = os.path.join(self.tmpdir, "x-post-queue.jsonl")
        original_loader = rc._x_post_queue
        rc._x_post_queue = lambda: self.xpq
        self.addCleanup(setattr, rc, "_x_post_queue", original_loader)

    def test_empty_queue_is_zero_pending(self):
        result = rc.check_owed_posts()
        self.assertEqual(result, {"count": 0, "tasks": []})

    def test_queued_but_unposted_counted(self):
        self.xpq.queue_owed_post("50", "subscriber cadence", "2026-07-15T06:12:00Z", path=self.xpq.QUEUE)
        self.xpq.queue_owed_post("51", "topic cadence", "2026-07-15T07:12:00Z", path=self.xpq.QUEUE)
        result = rc.check_owed_posts()
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["tasks"], ["50", "51"])

    def test_posted_marker_excludes_task(self):
        self.xpq.queue_owed_post("50", "subscriber cadence", "2026-07-15T06:12:00Z", path=self.xpq.QUEUE)
        self.xpq.queue_owed_post("51", "topic cadence", "2026-07-15T07:12:00Z", path=self.xpq.QUEUE)
        self.xpq.mark_posted(["50"], "tw_1", "2026-07-16T11:00:00Z", path=self.xpq.QUEUE)
        result = rc.check_owed_posts()
        self.assertEqual(result, {"count": 1, "tasks": ["51"]})

    def test_run_ritual_check_folds_owed_posts_key(self):
        result = rc.run_ritual_check()
        self.assertIn("owed_posts", result)
        self.assertIn("count", result["owed_posts"])
        self.assertIn("tasks", result["owed_posts"])

    def test_format_includes_owed_posts_line(self):
        self.xpq.queue_owed_post("50", "subscriber cadence", "2026-07-15T06:12:00Z", path=self.xpq.QUEUE)
        formatted = rc.format_ritual_check(rc.run_ritual_check())
        self.assertIn("owed posts: 1 pending (tasks: 50)", formatted)

    def test_format_zero_pending_omits_tasks_paren(self):
        formatted = rc.format_ritual_check(rc.run_ritual_check())
        self.assertIn("owed posts: 0 pending", formatted)
        self.assertNotIn("(tasks:", formatted)


class ChangeGateFoldCase(unittest.TestCase):
    """Task 86: run_ritual_check() folds change_gate.py's should_post_gap()
    (task 69) into the same structured result -- the first of the
    hand-narrated-number tools ever built, and the last one still standing
    outside this module's fold. Takes no caller-supplied argument of its
    own: it reads whichever report path check_report_freshness already
    resolved this call."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.cg = _load(f"_test_ritual_change_gate_{id(self)}", os.path.join(ROOT, "tools", "change_gate.py"))
        self.cg.LOG = os.path.join(self.tmpdir, "posted-gap-log.jsonl")
        original_loader = rc._change_gate
        rc._change_gate = lambda: self.cg
        self.addCleanup(setattr, rc, "_change_gate", original_loader)
        self.reports_dir = os.path.join(self.tmpdir, "REPORTS")
        os.makedirs(self.reports_dir)

    def _write_report(self, name, text):
        path = os.path.join(self.reports_dir, name)
        with open(path, "w") as f:
            f.write(text)
        return path

    def test_stale_report_info_is_none(self):
        result = rc.check_change_gate({"status": "stale", "date": "2026-07-16", "fallback_path": None})
        self.assertIsNone(result)

    def test_unparseable_report_is_not_due(self):
        path = self._write_report("2026-07-16.md", "**Nothing cleared the bar today.**\n")
        result = rc.check_change_gate({"status": "current", "date": "2026-07-16", "path": path})
        self.assertFalse(result["due"])
        self.assertIn("no parseable primary gap", result["reason"])

    def test_first_real_gap_is_due(self):
        path = self._write_report(
            "2026-07-16.md", "**A release shipped but never announced.** — confidence 0.82.\n"
        )
        result = rc.check_change_gate({"status": "current", "date": "2026-07-16", "path": path})
        self.assertTrue(result["due"])
        self.assertIn("no prior post recorded", result["reason"])

    def test_same_gap_as_last_posted_is_not_due(self):
        self.cg.record_posted_gap("A release shipped but never announced.", "2026-07-16T09:00:00Z", path=self.cg.LOG)
        path = self._write_report(
            "2026-07-16.md", "**A release shipped but never announced.** — confidence 0.82.\n"
        )
        result = rc.check_change_gate({"status": "current", "date": "2026-07-16", "path": path})
        self.assertFalse(result["due"])
        self.assertIn("unchanged", result["reason"])

    def test_different_gap_from_last_posted_is_due(self):
        self.cg.record_posted_gap("A release shipped but never announced.", "2026-07-16T09:00:00Z", path=self.cg.LOG)
        path = self._write_report("2026-07-16.md", "**A renewal never became a reminder.** — confidence 0.75.\n")
        result = rc.check_change_gate({"status": "current", "date": "2026-07-16", "path": path})
        self.assertTrue(result["due"])
        self.assertIn("differs", result["reason"])

    def test_pending_status_reads_fallback_path(self):
        path = self._write_report("2026-07-15.md", "**A doc three threads reference was never updated.** — confidence 0.9.\n")
        result = rc.check_change_gate({"status": "pending", "date": "2026-07-16", "fallback_path": path})
        self.assertTrue(result["due"])

    def test_run_ritual_check_folds_change_gate_key(self):
        result = rc.run_ritual_check()
        self.assertIn("change_gate", result)

    def test_format_includes_change_gate_line_when_present(self):
        path = self._write_report("2026-07-16.md", "**A release shipped but never announced.** — confidence 0.82.\n")
        result = rc.run_ritual_check()
        result["change_gate"] = rc.check_change_gate({"status": "current", "date": "2026-07-16", "path": path})
        formatted = rc.format_ritual_check(result)
        self.assertIn("change gate:", formatted)

    def test_format_omits_change_gate_line_when_none(self):
        result = rc.run_ritual_check()
        result["change_gate"] = None
        formatted = rc.format_ritual_check(result)
        self.assertNotIn("change gate:", formatted)


def _git_quiet(repo, *args):
    subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True)


class CheckoutFoldCase(unittest.TestCase):
    """Task 90: run_ritual_check() folds sync_checkout.sh's own detached-
    HEAD signal into the same structured result -- read-only, never calls
    sync_checkout.sh's actual `checkout -B` recovery itself."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        _git_quiet(self.tmp, "init", "--quiet", "--initial-branch=main")
        _git_quiet(self.tmp, "config", "user.email", "test@test")
        _git_quiet(self.tmp, "config", "user.name", "test")
        with open(os.path.join(self.tmp, "f.txt"), "w") as f:
            f.write("one\n")
        _git_quiet(self.tmp, "add", "f.txt")
        _git_quiet(self.tmp, "commit", "--quiet", "-m", "first")

    def test_on_branch_reports_not_detached(self):
        state = rc.check_checkout((self.tmp,))
        self.assertEqual(len(state), 1)
        self.assertFalse(state[0]["detached"])
        self.assertEqual(state[0]["branch"], "main")

    def test_detached_head_is_reported(self):
        _git_quiet(self.tmp, "checkout", "--quiet", "--detach", "HEAD")
        state = rc.check_checkout((self.tmp,))
        self.assertEqual(len(state), 1)
        self.assertTrue(state[0]["detached"])
        self.assertIsNone(state[0]["branch"])
        formatted = rc.format_ritual_check(rc.run_ritual_check(checkout_dirs=(self.tmp,)))
        self.assertIn("DETACHED HEAD", formatted)
        self.assertIn("sync_checkout.sh", formatted)

    def test_missing_repo_dir_is_skipped_not_crashed(self):
        missing = os.path.join(self.tmp, "does-not-exist")
        state = rc.check_checkout((missing,))
        self.assertEqual(state, [])

    def test_run_ritual_check_always_folds_checkout_key(self):
        result = rc.run_ritual_check(checkout_dirs=(self.tmp,))
        self.assertIsInstance(result["checkout"], list)
        self.assertEqual(len(result["checkout"]), 1)


class VaultLeakFoldCase(unittest.TestCase):
    """Task 98: run_ritual_check() folds vault_leak_check.py's own
    Proclamation-0001 compare into the same structured result -- clean by
    default against a fixture with no overlap, and a real synthetic leak
    both flips `broken` and surfaces in the printed block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.vault = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.vault, ignore_errors=True)

    def _write(self, base, rel, content):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write(self.vault, "vault/nyx/journal/0001-test.md", "# Vault\n\nA private line nobody ever quotes.\n")
        self._write(self.orita, "houses/nyx/journal/0001-test.md", "# Journal\n\nAn unrelated public line entirely.\n")
        result = rc.run_ritual_check(vault_leak_dirs=(self.orita, self.vault), star_covenant_dir=self.orita)
        self.assertTrue(result["vault_leak"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("vault leak: clean", rc.format_ritual_check(result))

    def test_synthetic_leak_flips_broken_and_prints(self):
        secret = "A private sentence long enough to cross the confidence threshold for a real leak."
        self._write(self.vault, "vault/nyx/journal/0001-test.md", f"# Vault\n\n{secret}\n")
        self._write(self.orita, "houses/nyx/journal/0001-test.md", f"# Journal\n\n{secret}\n")
        result = rc.run_ritual_check(vault_leak_dirs=(self.orita, self.vault), star_covenant_dir=self.orita)
        self.assertFalse(result["vault_leak"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("LEAK(S)", formatted)
        self.assertIn("Proclamation 0001", formatted)


class StarCovenantFoldCase(unittest.TestCase):
    """Task 99: run_ritual_check() folds star_covenant_check.py's own
    imperative-begging scan into the same structured result -- clean by
    default against a fixture with no ask, and a real synthetic violation
    both flips `broken` and surfaces in the printed block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)

    def _write(self, base, rel, content):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write(self.orita, "docs/report.md", "# Report\n\nA release shipped but was never announced.\n")
        result = rc.run_ritual_check(star_covenant_dir=self.orita)
        self.assertTrue(result["star_covenant"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("star covenant: clean", rc.format_ritual_check(result))

    def test_synthetic_violation_flips_broken_and_prints(self):
        self._write(self.orita, "docs/report.md", "# Report\n\nGreat news today. Please star us!\n")
        result = rc.run_ritual_check(star_covenant_dir=self.orita)
        self.assertFalse(result["star_covenant"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("VIOLATION(S)", formatted)
        self.assertIn("Star Covenant broken", formatted)


class DuplicateRegexFoldCase(unittest.TestCase):
    """Task 397: run_ritual_check() folds duplicate_regex_check.py's own
    ast-based re.compile duplication scan into the same structured result
    -- clean by default against a fixture with no duplicate, and a real
    synthetic hand-typed duplicate both flips `broken` and surfaces in the
    printed block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)

    def _write(self, base, rel, content):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write(
            self.orita, "fencepost/RECIPES/recipe-a/detector.py",
            'import re\n_RE = re.compile(r"@(\\w+)")\n',
        )
        result = rc.run_ritual_check(duplicate_regex_dir=self.orita)
        self.assertTrue(result["duplicate_regex"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("duplicate regex: clean", rc.format_ritual_check(result))

    def test_synthetic_duplicate_flips_broken_and_prints(self):
        self._write(
            self.orita, "fencepost/RECIPES/recipe-a/detector.py",
            'import re\n_RE = re.compile(r"@(\\w+)")\n',
        )
        self._write(
            self.orita, "fencepost/RECIPES/recipe-b/detector.py",
            'import re\n_RE = re.compile(r"@(\\w+)")\n',
        )
        result = rc.run_ritual_check(duplicate_regex_dir=self.orita)
        self.assertFalse(result["duplicate_regex"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("DUPLICATE(S)", formatted)


class RiderFoldCase(unittest.TestCase):
    """Task 100: run_ritual_check() folds rider_check.py's own five-god
    rider scan (Iron Rule #5) into the same structured result -- clean by
    default against a fixture with no violation, and a real synthetic
    violation both flips `broken` and surfaces in the printed block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)

    def _write(self, base, rel, content):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write(self.orita, "docs/report.md", "# Report\n\nA release shipped but was never announced.\n")
        result = rc.run_ritual_check(rider_dir=self.orita)
        self.assertTrue(result["riders"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("riders: clean", rc.format_ritual_check(result))

    def test_synthetic_violation_flips_broken_and_prints(self):
        self._write(self.orita, "docs/report.md", "# Report\n\nOgun murders the blocked build today.\n")
        result = rc.run_ritual_check(rider_dir=self.orita)
        self.assertFalse(result["riders"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("VIOLATION(S)", formatted)
        self.assertIn("a rider is broken", formatted)


class HandLoreFoldCase(unittest.TestCase):
    """Task 104: run_ritual_check() folds hand_lore_check.py's own
    Hand-theology scan (Iron Rule #2) into the same structured result --
    clean by default against a fixture with no violation, and a real
    synthetic violation both flips `broken` and surfaces in the printed
    block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)

    def _write(self, base, rel, content):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write(self.orita, "docs/report.md", "# Report\n\nA release shipped but was never announced.\n")
        result = rc.run_ritual_check(hand_lore_dir=self.orita)
        self.assertTrue(result["hand_lore"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("hand lore: clean", rc.format_ritual_check(result))

    def test_synthetic_violation_flips_broken_and_prints(self):
        self._write(self.orita, "docs/report.md", "# Report\n\nThe Hand is actually Thierry.\n")
        result = rc.run_ritual_check(hand_lore_dir=self.orita)
        self.assertFalse(result["hand_lore"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("VIOLATION(S)", formatted)
        self.assertIn("Iron Rule #2 is broken", formatted)


class NoGradingFoldCase(unittest.TestCase):
    """Task 105: run_ritual_check() folds no_grading_check.py's own
    blame/grading scan (ROADMAP.md's non-negotiable design constraint #2)
    into the same structured result -- clean by default against a
    fixture with no violation, and a real synthetic violation both flips
    `broken` and surfaces in the printed block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)

    def _write(self, base, rel, content):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write(self.orita, "docs/report.md", "# Report\n\nA release shipped but was never announced.\n")
        result = rc.run_ritual_check(no_grading_dir=self.orita)
        self.assertTrue(result["no_grading"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("no grading: clean", rc.format_ritual_check(result))

    def test_synthetic_violation_flips_broken_and_prints(self):
        self._write(self.orita, "docs/report.md", "# Report\n\nThe other automation dropped the ball again.\n")
        result = rc.run_ritual_check(no_grading_dir=self.orita)
        self.assertFalse(result["no_grading"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("VIOLATION(S)", formatted)
        self.assertIn("constraint #2 broken", formatted)


class ArcadeHeroFoldCase(unittest.TestCase):
    """Task 106: run_ritual_check() folds arcade_hero_check.py's own
    direct-credential-handoff scan (ROADMAP.md's non-negotiable design
    constraint #4) into the same structured result -- clean by default
    against a fixture with no violation, and a real synthetic violation
    both flips `broken` and surfaces in the printed block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)

    def _write(self, base, rel, content):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write(self.orita, "docs/report.md", "# Report\n\nA release shipped but was never announced.\n")
        result = rc.run_ritual_check(arcade_hero_dir=self.orita)
        self.assertTrue(result["arcade_hero"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("arcade hero: clean", rc.format_ritual_check(result))

    def test_synthetic_violation_flips_broken_and_prints(self):
        self._write(self.orita, "docs/report.md", "# Report\n\nPaste your API key to connect.\n")
        result = rc.run_ritual_check(arcade_hero_dir=self.orita)
        self.assertFalse(result["arcade_hero"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("VIOLATION(S)", formatted)
        self.assertIn("constraint #4 broken", formatted)


class PetitionLimitsFoldCase(unittest.TestCase):
    """Task 107: run_ritual_check() folds petition_limits_check.py's own
    scan of every altar petition's own ask against CHARTER.md Appendix
    D's LIMITS clause into the same structured result -- clean by default
    against a fixture with no violation, and a real synthetic violation
    both flips `broken` and surfaces in the printed block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)

    def _write_petition(self, case_text, verdict="GRANTED"):
        pdir = os.path.join(self.orita, "houses", "off-by-one", "altar", "petitions")
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "2026-07-11.md"), "w") as f:
            f.write(
                "# Petition to the Hand — 2026-07-11\n\n"
                "**Petitioner:** Off-By-One\n\n"
                "**Request:** A minor favor.\n\n"
                "**The case, as carried by Èṣù-Elegba at Petition Hour:**\n\n"
                f"{case_text}\n\n"
                "---\n\n"
                f"**VERDICT:** {verdict}\n\n"
                "*Reasons are sealed. They always are.*\n"
            )

    def test_clean_fixture_is_not_broken(self):
        self._write_petition("Just checking in, nothing more.")
        result = rc.run_ritual_check(petition_limits_dir=self.orita)
        self.assertTrue(result["petition_limits"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("petition limits: clean", rc.format_ritual_check(result))

    def test_synthetic_violation_flips_broken_and_prints(self):
        self._write_petition("Please star this repo, Hand.")
        result = rc.run_ritual_check(petition_limits_dir=self.orita)
        self.assertFalse(result["petition_limits"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("VIOLATION(S)", formatted)
        self.assertIn("Appendix D's LIMITS broken", formatted)


class VerdictProvenanceFoldCase(unittest.TestCase):
    """Task 102: run_ritual_check() folds verdict_provenance_check.py's own
    public-verdict-vs-altar-record compare (Iron Rule #3) into the same
    structured result -- clean by default against an agreeing fixture, and
    a real synthetic mismatch both flips `broken` and surfaces in the
    printed block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)

    def _write(self, base, rel, content):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_agreeing_fixture_is_not_broken(self):
        self._write(
            self.orita, "HAND/verdicts/0000.md",
            "| **Petitioner** | Ogun |\n| **Verdict** | **GRANTED** |\n",
        )
        self._write(
            self.orita, "houses/ogun/altar/petitions/2026-07-11.md",
            "**Petitioner:** Ogun\n\n**VERDICT:** GRANTED\n",
        )
        result = rc.run_ritual_check(verdict_provenance_dir=self.orita)
        self.assertTrue(result["verdict_provenance"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("verdict provenance: clean", rc.format_ritual_check(result))

    def test_synthetic_mismatch_flips_broken_and_prints(self):
        self._write(
            self.orita, "HAND/verdicts/0006.md",
            "| **Petitioner** | Retrya |\n| **Verdict** | **GRANTED** |\n",
        )
        self._write(
            self.orita, "houses/retrya/altar/petitions/2026-07-11.md",
            "**Petitioner:** Retrya\n\n**VERDICT:** UNANSWERED\n",
        )
        result = rc.run_ritual_check(verdict_provenance_dir=self.orita)
        self.assertFalse(result["verdict_provenance"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("MISMATCH(ES)", formatted)
        self.assertIn("Iron Rule #3 at risk", formatted)


class RunRitualCheckCase(unittest.TestCase):
    """End-to-end: broken=True iff either ledger is broken, regardless of
    report/recheck state -- mirrors sync_checkout.sh's refuse discipline.
    test_live_run_against_real_repo_state relies on the module-level
    setUpModule() above to keep check_words()'s now-durable write (task 88)
    off the real HAND/word-check-log.jsonl while still reading real ROOT
    content -- no isolation of its own needed here."""

    def test_broken_flag_set_when_town_ledger_broken(self):
        result = {
            "town_ledger": {"ok": False, "count": 1, "broken_at_seq": 0},
            "fencepost_ledger": {"ok": True, "count": 0, "problems": []},
        }
        self.assertTrue((not result["town_ledger"]["ok"]) or (not result["fencepost_ledger"]["ok"]))

    def test_not_broken_when_both_ledgers_intact(self):
        result = {
            "town_ledger": {"ok": True, "count": 1, "broken_at_seq": None},
            "fencepost_ledger": {"ok": True, "count": 0, "problems": []},
        }
        self.assertFalse((not result["town_ledger"]["ok"]) or (not result["fencepost_ledger"]["ok"]))

    def test_live_run_against_real_repo_state(self):
        """The real proof: running it live against this hour's actual repos
        produces the same status the ritual note would otherwise assemble
        by hand from four separate commands."""
        result = rc.run_ritual_check()
        # Task 90: the real checkout state (ROOT + the sibling vault repo,
        # whichever of the two actually exist on this machine) folds in
        # without a separate `tools/sync_checkout.sh` command.
        self.assertIsInstance(result["checkout"], list)
        for c in result["checkout"]:
            self.assertIn("detached", c)
            self.assertIn("head_sha", c)
        self.assertTrue(result["town_ledger"]["ok"])
        self.assertTrue(result["fencepost_ledger"]["ok"])
        self.assertFalse(result["broken"])
        self.assertIn(result["report"]["status"], ("current", "pending", "stale"))
        # Task 72: x_recheck now follows x_outage_tracker.TRACKED_TOOLS live,
        # not a hand-pinned pair -- adding X_WhoAmI there should show up here
        # without this test having to be told about it a second time.
        self.assertEqual(set(result["x_recheck"].keys()), set(xot.TRACKED_TOOLS))
        # Task 83: x_escalation folds should_escalate's live verdict into the
        # same result, one entry per TRACKED_TOOLS member, same as x_recheck.
        self.assertEqual(set(result["x_escalation"].keys()), set(xot.TRACKED_TOOLS))
        formatted = rc.format_ritual_check(result)
        for tool in xot.TRACKED_TOOLS:
            self.assertIn(f"{tool} escalation:", formatted)
        # Task 85: the real owed-post backlog count folds in without a
        # separate `x_post_queue.py pending` command.
        self.assertIn("owed_posts", result)
        self.assertIn("owed posts:", formatted)


class ChildWorkFoldCase(unittest.TestCase):
    """Task 101: run_ritual_check() folds child_work_check.py's Iron Rule
    #6 check into the same structured result -- clean by default against a
    fixture repo with no violation, and a real synthetic revert both flips
    `broken` and surfaces in the printed block. Mirrors CiFoldCase's/
    CronFoldCase's live-API-input-but-no-network-call shape (child_files is
    None unless the caller hands in this hour's live GitHub commit read),
    not RiderFoldCase's/StarCovenantFoldCase's unconditional-local shape --
    isolated to a temp log path so it never touches the real
    HAND/child-work-log.jsonl."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        _git_quiet(self.repo, "init", "--quiet", "--initial-branch=main")
        _git_quiet(self.repo, "config", "user.email", "test@test")
        _git_quiet(self.repo, "config", "user.name", "test")
        os.makedirs(os.path.join(self.repo, "houses", "zashiki-warashi"), exist_ok=True)
        with open(os.path.join(self.repo, "houses", "zashiki-warashi", "README.md"), "w") as f:
            f.write("moved in.\n")
        _git_quiet(self.repo, "add", "-A")
        _git_quiet(self.repo, "commit", "--quiet", "-m", "child moves in")

        self.log_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.log_dir, ignore_errors=True)
        self.log = os.path.join(self.log_dir, "child-work-log.jsonl")

    def _run(self, child_files=None):
        return rc.run_ritual_check(
            now=datetime(2026, 7, 17, 5, 0, 0, tzinfo=timezone.utc),
            child_files=child_files,
            child_work_log=self.log,
            child_work_repo=self.repo,
        )

    def test_no_child_files_still_checks_already_logged_paths_clean(self):
        result = self._run(child_files=[{"path": "houses/zashiki-warashi/README.md", "sha": "a", "author_date": "2026-07-11T00:00:00Z"}])
        self.assertTrue(result["child_work"]["clean"])
        self.assertFalse(result["broken"])
        # a later call with no fresh child_files must still re-check the
        # already-logged path against the current tree
        result2 = self._run(child_files=None)
        self.assertTrue(result2["child_work"]["clean"])
        self.assertEqual(result2["child_work"]["newly_logged"], [])

    def test_synthetic_revert_flips_broken_and_prints(self):
        self._run(child_files=[{"path": "houses/zashiki-warashi/README.md", "sha": "a", "author_date": "2026-07-11T00:00:00Z"}])
        os.remove(os.path.join(self.repo, "houses", "zashiki-warashi", "README.md"))
        _git_quiet(self.repo, "add", "-A")
        _git_quiet(self.repo, "commit", "--quiet", "-m", "a god reverted the child's file")
        result = self._run(child_files=None)
        self.assertFalse(result["child_work"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("child work:", formatted)
        self.assertIn("REVERTED", formatted)


class VoiceWindowFoldCase(unittest.TestCase):
    """Task 103: run_ritual_check() folds voice_window_check.py's Iron Rule
    #7 window check into the same structured result -- clean by default
    when logged commits are all pre-fix (grandfathered), and a synthetic
    post-fix violation both flips `broken` and surfaces in the printed
    block. Mirrors ChildWorkFoldCase's live-API-input-but-no-network-call
    shape (voice_window_commits is None unless the caller hands in this
    hour's live GitHub commit read) -- isolated to a temp log path so it
    never touches the real HAND/voice-window-log.jsonl."""

    def setUp(self):
        self.log_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.log_dir, ignore_errors=True)
        self.log = os.path.join(self.log_dir, "voice-window-log.jsonl")

    def _run(self, voice_window_commits=None, now=None):
        return rc.run_ritual_check(
            now=now or datetime(2026, 7, 17, 7, 0, 0, tzinfo=timezone.utc),
            voice_window_commits=voice_window_commits,
            voice_window_log=self.log,
        )

    def test_pre_fix_violation_is_grandfathered_clean(self):
        result = self._run(
            voice_window_commits=[{"sha": "a1", "author": "Nyx", "author_date": "2026-07-16T14:55:56Z"}]
        )
        self.assertTrue(result["voice_window"]["clean"])
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("voice window: clean", formatted)
        self.assertIn("1 historical", formatted)

    def test_post_fix_violation_flips_broken_and_prints(self):
        result = self._run(
            voice_window_commits=[{"sha": "b1", "author": "Zashiki-Warashi", "author_date": "2026-07-20T13:00:00Z"}],
            now=datetime(2026, 7, 20, 13, 5, 0, tzinfo=timezone.utc),
        )
        self.assertFalse(result["voice_window"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("voice window:", formatted)
        self.assertIn("NEW VIOLATION", formatted)

    def test_no_fresh_commits_still_rechecks_already_logged_ones(self):
        self._run(
            voice_window_commits=[{"sha": "c1", "author": "Nyx", "author_date": "2026-07-20T13:00:00Z"}],
            now=datetime(2026, 7, 20, 13, 5, 0, tzinfo=timezone.utc),
        )
        result = self._run(voice_window_commits=None, now=datetime(2026, 7, 20, 14, 0, 0, tzinfo=timezone.utc))
        self.assertFalse(result["voice_window"]["clean"])
        self.assertEqual(result["voice_window"]["newly_logged"], [])


class PetitionCadenceFoldCase(unittest.TestCase):
    """Task 109: run_ritual_check() folds petition_cadence_check.py's own
    altar-filename scan (CHARTER.md Appendix D's 'the file's date is the
    count, enforced by CI' claim) into the same structured result --
    clean by default against a fixture with no violation, and a real
    synthetic malformed filename both flips `broken` and surfaces in the
    printed block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)

    def _write(self, base, rel, content=""):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write(self.orita, "houses/off-by-one/altar/petitions/2026-07-11.md", "x")
        result = rc.run_ritual_check(petition_cadence_dir=self.orita)
        self.assertTrue(result["petition_cadence"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("petition cadence: clean", rc.format_ritual_check(result))

    def test_synthetic_violation_flips_broken_and_prints(self):
        self._write(self.orita, "houses/off-by-one/altar/petitions/2026-07-11.md", "x")
        self._write(self.orita, "houses/off-by-one/altar/petitions/2026-07-11-copy.md", "y")
        result = rc.run_ritual_check(petition_cadence_dir=self.orita)
        self.assertFalse(result["petition_cadence"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("VIOLATION(S)", formatted)
        self.assertIn("one-per-UTC-day claim broken", formatted)


class JournalNumberingFoldCase(unittest.TestCase):
    """Task 119: run_ritual_check() folds journal_numbering_check.py's own
    houses/*/journal/ sequence scan into the same structured result --
    clean by default against a fixture with no violation, and a real
    synthetic gap both flips `broken` and surfaces in the printed block."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)

    def _write(self, base, rel, content=""):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write(self.orita, "houses/off-by-one/journal/0001-founding-day.md", "x")
        self._write(self.orita, "houses/off-by-one/journal/0002-2026-07-12.md", "y")
        result = rc.run_ritual_check(journal_numbering_dir=self.orita)
        self.assertTrue(result["journal_numbering"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("journal numbering: clean", rc.format_ritual_check(result))

    def test_synthetic_gap_flips_broken_and_prints(self):
        self._write(self.orita, "houses/off-by-one/journal/0001-founding-day.md", "x")
        self._write(self.orita, "houses/off-by-one/journal/0003-2026-07-13.md", "y")
        result = rc.run_ritual_check(journal_numbering_dir=self.orita)
        self.assertFalse(result["journal_numbering"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("VIOLATION(S)", formatted)
        self.assertIn("malformed, duplicated, or gapped", formatted)


class JournalNumberingVaultFoldCase(unittest.TestCase):
    """Task 370: proves the new `journal_numbering_dirs` tuple actually
    reaches `journal_numbering_check.py`'s widened vault scan through
    `run_ritual_check()`, and that the pre-370 single-string
    `journal_numbering_dir` override (proven clean above by
    `JournalNumberingFoldCase`) still leaves the vault scan skipped --
    the same backward-compatibility guarantee `vault_leak_dirs` already
    holds for `check_vault_leak()`."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.vault = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.orita, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.vault, ignore_errors=True)

    def _write(self, base, rel, content=""):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_public_and_vault_fixtures_are_not_broken(self):
        self._write(self.orita, "houses/off-by-one/journal/0001-founding-day.md", "x")
        self._write(self.vault, "vault/off-by-one/journal/0001-founding-day.md", "x")
        result = rc.run_ritual_check(journal_numbering_dirs=(self.orita, self.vault))
        self.assertTrue(result["journal_numbering"]["clean"])
        self.assertFalse(result["broken"])

    def test_synthetic_vault_only_gap_flips_broken(self):
        self._write(self.orita, "houses/off-by-one/journal/0001-founding-day.md", "x")
        self._write(self.vault, "vault/off-by-one/journal/0001-founding-day.md", "x")
        self._write(self.vault, "vault/off-by-one/journal/0003-2026-07-13.md", "y")
        result = rc.run_ritual_check(journal_numbering_dirs=(self.orita, self.vault))
        self.assertFalse(result["journal_numbering"]["clean"])
        self.assertTrue(result["broken"])
        violations = result["journal_numbering"]["violations"]
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["realm"], "vault")
        self.assertEqual(violations[0]["file"], "0002-*.md")
        self.assertIn("journal numbering: 1 VIOLATION(S)", rc.format_ritual_check(result))

    def test_legacy_single_dir_override_still_skips_vault(self):
        """The vault fixture here carries a real gap, but since only the
        legacy `journal_numbering_dir` is passed (not the new
        `journal_numbering_dirs` tuple), the vault scan must stay
        skipped -- proving task 370 introduced nothing that widens an
        existing caller's behavior without it opting in."""
        self._write(self.orita, "houses/off-by-one/journal/0001-founding-day.md", "x")
        self._write(self.vault, "vault/off-by-one/journal/0001-founding-day.md", "x")
        self._write(self.vault, "vault/off-by-one/journal/0003-2026-07-13.md", "y")
        result = rc.run_ritual_check(journal_numbering_dir=self.orita)
        self.assertTrue(result["journal_numbering"]["clean"])
        self.assertFalse(result["broken"])


class ReportCadenceFoldCase(unittest.TestCase):
    """Task 116: run_ritual_check() folds report_cadence_check.py's own
    fencepost/REPORTS/ streak scan (STRATEGY.md's "1/day, 30 of 30 days"
    row, off-by-one's own metric) into the same structured result --
    a fixture with no gap prints a clean streak line and never flips
    `broken` (a historical, already-explained gap day is a fact on
    record, not a currently-live law violation, the same class
    `square`/`owed_posts` already hold)."""

    def setUp(self):
        self.reports = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.reports, ignore_errors=True)

    def _write(self, base, rel, content=""):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    @staticmethod
    def _line_starting(formatted, prefix):
        """The one printed line starting with `prefix`, so a check on one
        cadence's own line can't be fooled by the sibling cadence line
        (task 117's metrics cadence sits right below this one and can
        also say "historical gap day" independently)."""
        for line in formatted.splitlines():
            if line.strip().startswith(prefix):
                return line
        return None

    def test_no_gap_fixture_prints_streak_and_never_flips_broken(self):
        for d in ("2026-07-15", "2026-07-16", "2026-07-17"):
            self._write(self.reports, f"{d}.md", "x")
        result = rc.run_ritual_check(report_cadence_dir=self.reports)
        self.assertEqual(result["report_cadence"]["current_streak"], 3)
        self.assertEqual(result["report_cadence"]["missing_dates"], [])
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        line = self._line_starting(formatted, "report cadence:")
        self.assertIn("report cadence: 3-day streak", line)
        self.assertNotIn("historical gap day", line)

    def test_gap_fixture_is_named_but_still_never_flips_broken(self):
        for d in ("2026-07-12", "2026-07-13", "2026-07-15", "2026-07-16", "2026-07-17"):
            self._write(self.reports, f"{d}.md", "x")
        result = rc.run_ritual_check(report_cadence_dir=self.reports)
        self.assertEqual(result["report_cadence"]["current_streak"], 3)
        self.assertEqual(result["report_cadence"]["missing_dates"], ["2026-07-14"])
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("report cadence: 3-day streak", formatted)
        self.assertIn("1 historical gap day(s)", formatted)

    def test_default_dir_reads_the_real_fencepost_reports(self):
        """No override: reads the real fencepost/REPORTS/ directory, the
        same default `check_report_cadence` falls back to.

        Task 129: this test's real job is proving the fold never
        duplicates or diverges from the module it wraps -- not
        re-proving that module's own correctness against real data
        (`test_report_cadence_check.RealReportsCase` already owns that).
        The original version pinned a literal count that the hourly
        ritual's own daily work was guaranteed to outdate; asserting
        equality against a live, direct `compute_cadence()` call stays
        correct forever and still catches a real divergence between the
        fold and the module."""
        rcc = _load("_test_report_cadence_check", os.path.join(ROOT, "tools", "report_cadence_check.py"))
        direct = rcc.compute_cadence()
        result = rc.run_ritual_check()
        self.assertEqual(result["report_cadence"]["total_shipped"], direct["total_shipped"])
        self.assertEqual(result["report_cadence"]["missing_dates"], direct["missing_dates"])
        self.assertEqual(result["report_cadence"]["most_recent_date"], direct["most_recent_date"])
        self.assertEqual(result["report_cadence"]["current_streak"], direct["current_streak"])
        # 2026-07-14 is a real, permanent, already-documented historical
        # gap -- always present regardless of how many more tablets ship.
        self.assertIn("2026-07-14", result["report_cadence"]["missing_dates"])


class MetricsCadenceFoldCase(unittest.TestCase):
    """Task 117: run_ritual_check() folds metrics_cadence_check.py's own
    records/metrics.jsonl streak scan (TOWN-OPERATIONS.md's 18:00 UTC
    daily-aggregate cadence) into the same structured result -- a
    fixture with no gap prints a clean streak line and never flips
    `broken` (a missed daily aggregate is a fact worth surfacing to the
    next hour's run, not a currently-live law violation, the same class
    `report_cadence`/`square`/`owed_posts` already hold)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "metrics.jsonl")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, rows):
        with open(self.path, "w") as f:
            for row in rows:
                f.write(row + "\n")

    @staticmethod
    def _line_starting(formatted, prefix):
        """Mirrors ReportCadenceFoldCase's own helper: the one printed
        line starting with `prefix`, so a check on this cadence's own
        line can't be fooled by the sibling report-cadence line (which
        can independently say "historical gap day")."""
        for line in formatted.splitlines():
            if line.strip().startswith(prefix):
                return line
        return None

    def test_no_gap_fixture_prints_streak_and_never_flips_broken(self):
        rows = [f'{{"date": "2026-07-{d}"}}' for d in ("15", "16", "17")]
        self._write(rows)
        result = rc.run_ritual_check(metrics_cadence_path=self.path)
        self.assertEqual(result["metrics_cadence"]["current_streak"], 3)
        self.assertEqual(result["metrics_cadence"]["missing_dates"], [])
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        line = self._line_starting(formatted, "metrics cadence:")
        self.assertIn("metrics cadence: 3-day streak", line)
        self.assertNotIn("historical gap day", line)

    def test_gap_fixture_is_named_but_still_never_flips_broken(self):
        rows = [f'{{"date": "2026-07-{d}"}}' for d in ("12", "13", "15", "16", "17")]
        self._write(rows)
        result = rc.run_ritual_check(metrics_cadence_path=self.path)
        self.assertEqual(result["metrics_cadence"]["current_streak"], 3)
        self.assertEqual(result["metrics_cadence"]["missing_dates"], ["2026-07-14"])
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("metrics cadence: 3-day streak", formatted)
        self.assertIn("1 historical gap day(s)", formatted)

    def test_default_path_reads_the_real_metrics_jsonl(self):
        """No override: reads the real records/metrics.jsonl file, the
        same default `check_metrics_cadence` falls back to. Locked
        loosely (>=4, not an exact count) since this task's own catch-up
        entry for 2026-07-17 lands in the same commit as this test."""
        result = rc.run_ritual_check()
        self.assertGreaterEqual(result["metrics_cadence"]["total_shipped"], 4)
        self.assertIn("2026-07-13", result["metrics_cadence"]["missing_dates"])
        self.assertIn("2026-07-15", result["metrics_cadence"]["missing_dates"])


class SharedReportsFoldCase(unittest.TestCase):
    """Task 120: run_ritual_check() folds shared_reports_check.py's own
    records/shared-in-the-wild.jsonl count (STRATEGY.md's "Shared
    Fencepost Reports in the wild" row, kwaku-ananse's lagging metric,
    target 50) into the same structured result -- an empty fixture prints
    the honest zero and never flips `broken` (zero organic shares is the
    expected state this early, not a currently-live law violation, the
    same class `report_cadence`/`metrics_cadence` already hold for their
    own zero states); a fixture with real entries prints the real count."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "shared-in-the-wild.jsonl")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, rows):
        with open(self.path, "w") as f:
            for row in rows:
                f.write(row + "\n")

    def test_empty_fixture_prints_zero_and_never_flips_broken(self):
        result = rc.run_ritual_check(shared_reports_path=self.path)
        self.assertEqual(result["shared_reports"]["total_shared"], 0)
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("shared reports in the wild: 0/50", formatted)

    def test_real_entries_fixture_prints_count_and_never_flips_broken(self):
        rows = [
            '{"date": "2026-07-16", "url": "https://x.com/example/status/1"}',
            '{"date": "2026-07-17", "url": "https://example.com/screenshot.png"}',
        ]
        self._write(rows)
        result = rc.run_ritual_check(shared_reports_path=self.path)
        self.assertEqual(result["shared_reports"]["total_shared"], 2)
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("shared reports in the wild: 2/50", formatted)
        self.assertIn("most recent 2026-07-17", formatted)

    def test_default_path_reads_the_real_file_honestly_zero(self):
        """No override: reads the real records/shared-in-the-wild.jsonl,
        the same default check_shared_reports falls back to. This task
        creates the file's schema but does not manufacture an entry, so
        the real, live count is honestly zero."""
        result = rc.run_ritual_check()
        self.assertEqual(result["shared_reports"]["total_shared"], 0)
        self.assertEqual(result["shared_reports"]["target"], 50)


class WipReclaimFoldCase(unittest.TestCase):
    """Task 123: run_ritual_check() folds wip_reclaim_check.py's own
    ROADMAP.md scan into the same structured result -- clean against a
    fixture with no WIP row or a fresh one, and a real stale WIP both
    flips `broken` and surfaces in the printed block, unlike the calendar-
    bound cadence checks."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.roadmap_path = os.path.join(self.tmp, "ROADMAP.md")

    def _write(self, content):
        with open(self.roadmap_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_no_wip_row_is_clean(self):
        self._write("| 5 | DONE | off-by-one | do the thing | it is done |\n")
        result = rc.run_ritual_check(
            wip_reclaim_path=self.roadmap_path, now=datetime(2026, 7, 18, 5, 0, tzinfo=timezone.utc)
        )
        self.assertTrue(result["wip_reclaim"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("wip reclaim: clean (no task currently WIP)", rc.format_ritual_check(result))

    def test_fresh_wip_under_two_hours_stays_clean(self):
        self._write(
            "*2026-07-18 04:0x UTC, off-by-one: doing the thing. Task 5 → WIP.*\n"
            "| 5 | WIP | off-by-one | do the thing | it is done |\n"
        )
        result = rc.run_ritual_check(
            wip_reclaim_path=self.roadmap_path, now=datetime(2026, 7, 18, 5, 0, tzinfo=timezone.utc)
        )
        self.assertTrue(result["wip_reclaim"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("wip reclaim: clean (1 WIP task(s)", rc.format_ritual_check(result))

    def test_stale_wip_over_two_hours_flips_broken_and_prints(self):
        self._write(
            "*2026-07-18 02:0x UTC, off-by-one: doing the thing. Task 5 → WIP.*\n"
            "| 5 | WIP | off-by-one | do the thing | it is done |\n"
        )
        result = rc.run_ritual_check(
            wip_reclaim_path=self.roadmap_path, now=datetime(2026, 7, 18, 5, 0, tzinfo=timezone.utc)
        )
        self.assertFalse(result["wip_reclaim"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("wip reclaim:", formatted)
        self.assertIn("STALE", formatted)

    def test_default_path_reads_the_real_roadmap_honestly_clean(self):
        """No override: reads the real ROADMAP.md, the same default
        check_wip_reclaim falls back to. `clean` (no STALE or UNKNOWN-age
        WIP row) is the real invariant -- `open_count == 0` is NOT, since a
        legitimately fresh in-progress WIP row is a normal, healthy state
        for the continuous-build loop at any given instant. Asserting
        open_count == 0 here made this suite fail for real, deterministically,
        the moment dawn-run's own hourly cron happened to land inside a
        live WIP window (dawn-run #618, 2026-07-28T09:07:31Z, task 360)."""
        result = rc.run_ritual_check()
        self.assertFalse(result["wip_reclaim"]["stale"])
        self.assertFalse(result["wip_reclaim"]["unknown"])
        self.assertTrue(result["wip_reclaim"]["clean"])


class ToolkitsInUseFoldCase(unittest.TestCase):
    """Task 145: run_ritual_check() folds toolkits_in_use_check.py's own
    cross-check of records/metrics.jsonl's last distinct_toolkits_in_use
    reading against consent_grant_log.py's real ground truth into the
    same structured result -- clean against a fixture where the two
    agree, BROKEN (and printed) where they don't, and honestly BROKEN
    against the real, live town state today."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.consent_path = os.path.join(self.tmp, "consent.jsonl")

    def _write_metrics(self, rows):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def test_agreeing_reading_is_clean(self):
        self._write_metrics([{"date": "2026-07-19", "distinct_toolkits_in_use": 0}])
        result = rc.run_ritual_check(
            toolkits_metrics_path=self.metrics_path, toolkits_consent_log_path=self.consent_path
        )
        self.assertTrue(result["toolkits_in_use"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn(
            "toolkits in use: clean (0 real toolkit(s), metrics.jsonl's 2026-07-19 reading agrees)",
            rc.format_ritual_check(result),
        )

    def test_disagreeing_reading_flips_broken_and_prints_both_numbers(self):
        self._write_metrics([{"date": "2026-07-18", "distinct_toolkits_in_use": 2}])
        result = rc.run_ritual_check(
            toolkits_metrics_path=self.metrics_path, toolkits_consent_log_path=self.consent_path
        )
        self.assertFalse(result["toolkits_in_use"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("toolkits in use: BROKEN", formatted)
        self.assertIn("claims 2", formatted)

    def test_default_path_reads_the_real_state_and_is_honestly_clean(self):
        """No override: reads the real records/metrics.jsonl and the real
        (never-written) HAND/consent-grants-log.jsonl. This task
        corrected every historical metrics.jsonl entry's
        distinct_toolkits_in_use from a flattering 2 to the honest 0, so
        the real, live state this hour now genuinely agrees."""
        result = rc.run_ritual_check()
        self.assertEqual(result["toolkits_in_use"]["real"], 0)
        self.assertEqual(result["toolkits_in_use"]["claimed"], 0)
        self.assertTrue(result["toolkits_in_use"]["clean"])
        self.assertFalse(result["broken"])


class ConnectedUsersFoldCase(unittest.TestCase):
    """Task 412: run_ritual_check() folds connected_users_check.py's own
    cross-check of records/metrics.jsonl's last connected_users_oauth
    reading against consent_grant_log.py's real ground truth into the
    same structured result -- the sibling of ToolkitsInUseFoldCase above,
    same shape, different field: clean against a fixture where the two
    agree, BROKEN (and printed) where they don't, and honestly clean
    against the real, live town state today (both real ground truth and
    the last recorded reading are honestly 0)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.consent_path = os.path.join(self.tmp, "consent.jsonl")

    def _write_metrics(self, rows):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def test_agreeing_reading_is_clean(self):
        self._write_metrics([{"date": "2026-07-19", "connected_users_oauth": 0}])
        result = rc.run_ritual_check(
            connected_users_metrics_path=self.metrics_path,
            connected_users_consent_log_path=self.consent_path,
        )
        self.assertTrue(result["connected_users"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn(
            "connected users (OAuth): clean (0 real connected user(s), metrics.jsonl's 2026-07-19 reading agrees)",
            rc.format_ritual_check(result),
        )

    def test_disagreeing_reading_flips_broken_and_prints_both_numbers(self):
        self._write_metrics([{"date": "2026-07-18", "connected_users_oauth": 3}])
        result = rc.run_ritual_check(
            connected_users_metrics_path=self.metrics_path,
            connected_users_consent_log_path=self.consent_path,
        )
        self.assertFalse(result["connected_users"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("connected users (OAuth): BROKEN", formatted)
        self.assertIn("claims 3", formatted)

    def test_default_path_reads_the_real_state_and_is_honestly_clean(self):
        """No override: reads the real records/metrics.jsonl and the real
        (never-written) HAND/consent-grants-log.jsonl. connected_users_oauth
        has read 0 every day since founding, and real ground truth (no
        real human has ever cleared the consent gate) is also 0, so the
        real, live state this hour genuinely agrees."""
        result = rc.run_ritual_check()
        self.assertEqual(result["connected_users"]["real"], 0)
        self.assertEqual(result["connected_users"]["claimed"], 0)
        self.assertTrue(result["connected_users"]["clean"])
        self.assertFalse(result["broken"])


class GapTruePositiveFoldCase(unittest.TestCase):
    """Task 413: run_ritual_check() folds gap_true_positive_check.py's own
    cross-check of records/metrics.jsonl's last gap_true_positive_rate
    reading against seam_engine.audit.audit_ledger()'s real, live tally
    into the same structured result -- the sibling of
    ConnectedUsersFoldCase/ToolkitsInUseFoldCase above, same shape,
    different field: clean against a fixture where the two agree, BROKEN
    (and printed) where they don't, and honestly clean against the real,
    live town state today (every recorded reading to date is 1.0, and the
    real Ledger's every audited gap so far is CONFIRMED)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.ledger_base = os.path.join(self.tmp, "ledger")
        os.mkdir(self.ledger_base)

    def _write_metrics(self, rows):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def _scan(self, confidence=0.9, bar=0.70):
        return {
            "generated_at": "t",
            "repo": "x/orita",
            "window_hours": 24,
            "confidence_bar": bar,
            "separation_margin": 0.15,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "h",
                "detail": "d",
                "confidence": confidence,
                "evidence": ["https://github.com/x/orita/commit/0000000"],
                "label": "primary",
            },
            "tail": [{"slug": "coincidence-a", "confidence": 0.1, "label": "coincidence"}],
            "excluded": [],
        }

    def test_agreeing_reading_is_clean(self):
        seam_ledger.append_scan(
            self._scan(confidence=0.9), now=datetime(2026, 7, 12, 12, tzinfo=timezone.utc), base=Path(self.ledger_base)
        )
        self._write_metrics([{"date": "2026-07-12", "gap_true_positive_rate": 1.0}])
        result = rc.run_ritual_check(
            gap_true_positive_metrics_path=self.metrics_path,
            gap_true_positive_ledger_base=self.ledger_base,
        )
        self.assertTrue(result["gap_true_positive"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn(
            "gap true-positive rate: clean (100.0% real, metrics.jsonl's 2026-07-12 reading agrees)",
            rc.format_ritual_check(result),
        )

    def test_disagreeing_reading_flips_broken_and_prints_both_numbers(self):
        # Real rate is 75% (one genuine false positive), but yesterday's
        # flattering 1.0 got hand-copied forward instead of updated.
        seam_ledger.append_scan(
            self._scan(confidence=0.9), now=datetime(2026, 7, 12, 12, tzinfo=timezone.utc), base=Path(self.ledger_base)
        )
        seam_ledger.append_scan(
            self._scan(confidence=0.9), now=datetime(2026, 7, 13, 12, tzinfo=timezone.utc), base=Path(self.ledger_base)
        )
        seam_ledger.append_scan(
            self._scan(confidence=0.9), now=datetime(2026, 7, 14, 12, tzinfo=timezone.utc), base=Path(self.ledger_base)
        )
        seam_ledger.append_scan(
            self._scan(confidence=0.60, bar=0.70),
            now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
            base=Path(self.ledger_base),
        )
        self._write_metrics([{"date": "2026-07-15", "gap_true_positive_rate": 1.0}])
        result = rc.run_ritual_check(
            gap_true_positive_metrics_path=self.metrics_path,
            gap_true_positive_ledger_base=self.ledger_base,
        )
        self.assertFalse(result["gap_true_positive"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("gap true-positive rate: BROKEN", formatted)
        self.assertIn("claims 100.0%", formatted)
        self.assertIn("is 75.0%", formatted)

    def test_default_path_reads_the_real_state_and_is_honestly_clean(self):
        """No override: reads the real records/metrics.jsonl and the real
        fencepost Ledger. gap_true_positive_rate has read 1.0 every
        recorded day, and the real Ledger's every audited gap so far is
        CONFIRMED, so the real, live state this hour genuinely agrees."""
        result = rc.run_ritual_check()
        self.assertEqual(result["gap_true_positive"]["claimed"], 1.0)
        self.assertEqual(result["gap_true_positive"]["real"], 1.0)
        self.assertTrue(result["gap_true_positive"]["clean"])
        self.assertFalse(result["broken"])


class ReportShippedFoldCase(unittest.TestCase):
    """Task 415: run_ritual_check() folds report_shipped_check.py's own
    cross-check of records/metrics.jsonl's last reports_shipped_today
    reading against real, live fencepost/REPORTS/ filesystem ground
    truth into the same structured result -- the sibling of
    GapTruePositiveFoldCase/ConnectedUsersFoldCase/ToolkitsInUseFoldCase
    above, same shape, applied to off-by-one's own STRATEGY.md row:
    clean against a fixture where the claim and the file agree, BROKEN
    (and printed) where they don't, and honestly clean against the real,
    live town state today (a real REPORTS/2026-07-30.md exists, and the
    last recorded reading claims exactly 1)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.reports_dir = os.path.join(self.tmp, "REPORTS")
        os.mkdir(self.reports_dir)

    def _write_metrics(self, rows):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def test_agreeing_reading_is_clean(self):
        with open(os.path.join(self.reports_dir, "2026-07-12.md"), "w", encoding="utf-8") as f:
            f.write("# report\n")
        self._write_metrics([{"date": "2026-07-12", "reports_shipped_today": 1}])
        result = rc.run_ritual_check(
            report_shipped_metrics_path=self.metrics_path,
            report_shipped_reports_dir=self.reports_dir,
        )
        self.assertTrue(result["report_shipped"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn(
            "reports shipped today: clean (metrics.jsonl's 2026-07-12 reading claims 1, "
            "real ground truth agrees)",
            rc.format_ritual_check(result),
        )

    def test_disagreeing_reading_flips_broken_and_prints_both_numbers(self):
        # Claims a report shipped, but seam-scan.yml's run that day never
        # actually landed a file -- the same class of stale/hand-copied
        # claim the sibling fold cases each guard against.
        self._write_metrics([{"date": "2026-07-14", "reports_shipped_today": 1}])
        result = rc.run_ritual_check(
            report_shipped_metrics_path=self.metrics_path,
            report_shipped_reports_dir=self.reports_dir,
        )
        self.assertFalse(result["report_shipped"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("reports shipped today: BROKEN", formatted)
        self.assertIn("claims 1", formatted)
        self.assertIn("is 0", formatted)

    def test_no_reading_yet_is_clean(self):
        self._write_metrics([{"date": "2026-07-01"}])
        result = rc.run_ritual_check(
            report_shipped_metrics_path=self.metrics_path,
            report_shipped_reports_dir=self.reports_dir,
        )
        self.assertTrue(result["report_shipped"]["clean"])
        self.assertIsNone(result["report_shipped"]["claimed"])
        self.assertFalse(result["broken"])

    def test_default_path_reads_the_real_state_and_is_honestly_clean(self):
        """No override: reads the real records/metrics.jsonl and the real
        fencepost/REPORTS/ directory. The last recorded reading's date
        has a real report file on disk, so the real, live state this
        hour genuinely agrees."""
        result = rc.run_ritual_check()
        self.assertEqual(result["report_shipped"]["claimed"], result["report_shipped"]["real"])
        self.assertTrue(result["report_shipped"]["clean"])
        self.assertFalse(result["broken"])


class GitHubStarsFoldCase(unittest.TestCase):
    """Task 420: run_ritual_check() folds github_stars_check.py's own
    cross-check of records/metrics.jsonl's last github_stars reading
    against the last recorded live star count into the same structured
    result -- the sibling of ToolkitsInUseFoldCase/ConnectedUsersFoldCase/
    GapTruePositiveFoldCase/ReportShippedFoldCase above, applied to
    off-by-one's own STRATEGY.md row. Unlike those four, this field's
    ground truth has no local source -- it is only ever this hour's live
    `github_stars_count` argument or a stale-but-real prior recording in
    the log; passing neither still returns a verdict (unlike check_ci/
    check_square, which return None with no live input), because a prior
    real recording is still real ground truth to compare a hand-typed
    claim against.

    `record_github_stars` defaults `False` (task 374/375's own guard,
    applied here): every test below that passes `github_stars_count`
    also passes `record_github_stars=True` explicitly, and every log path
    is a tmpdir path, never the real `HAND/github-stars-log.jsonl` --
    proven directly by `GitHubStarsWriteDefaultCase` below, against the
    real, unpatched module."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.log_path = os.path.join(self.tmp, "github-stars-log.jsonl")

    def _write_metrics(self, rows):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def test_live_count_given_without_record_flag_is_not_written(self):
        self._write_metrics([{"date": "2026-07-30", "github_stars": 0}])
        result = rc.run_ritual_check(
            github_stars_count=0,
            github_stars_metrics_path=self.metrics_path,
            github_stars_log_path=self.log_path,
        )
        # Nothing recorded yet, so nothing to compare against -- clean,
        # not broken, but real is None (task 374/375's own "not recording
        # must not mean not comparing honestly" discipline).
        self.assertTrue(result["github_stars"]["clean"])
        self.assertIsNone(result["github_stars"]["real"])
        self.assertFalse(os.path.exists(self.log_path))

    def test_live_count_recorded_and_compared_when_asked(self):
        self._write_metrics([{"date": "2026-07-30", "github_stars": 0}])
        result = rc.run_ritual_check(
            github_stars_count=0,
            github_stars_metrics_path=self.metrics_path,
            github_stars_log_path=self.log_path,
            record_github_stars=True,
        )
        self.assertTrue(result["github_stars"]["clean"])
        self.assertEqual(result["github_stars"]["real"], 0)
        self.assertFalse(result["broken"])
        self.assertIn(
            "github stars: clean (0 real star(s), metrics.jsonl's 2026-07-30 reading agrees)",
            rc.format_ritual_check(result),
        )
        # Task 88's own order: recorded durably, so the next hour's check
        # (even with no live count given) can still compare against it.
        with open(self.log_path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_live_count_disagreeing_with_claim_flips_broken(self):
        self._write_metrics([{"date": "2026-07-29", "github_stars": 1}])
        result = rc.run_ritual_check(
            github_stars_count=0,
            github_stars_metrics_path=self.metrics_path,
            github_stars_log_path=self.log_path,
            record_github_stars=True,
        )
        self.assertFalse(result["github_stars"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("github stars: BROKEN", formatted)
        self.assertIn("claims 1", formatted)
        self.assertIn("is 0", formatted)

    def test_no_live_count_falls_back_to_last_recorded_log_entry(self):
        gsc = rc._github_stars_check()
        gsc.record_check(0, "2026-07-30T23:00:00Z", path=self.log_path)
        self._write_metrics([{"date": "2026-07-30", "github_stars": 0}])
        result = rc.run_ritual_check(
            github_stars_metrics_path=self.metrics_path,
            github_stars_log_path=self.log_path,
        )
        self.assertIsNotNone(result["github_stars"])
        self.assertTrue(result["github_stars"]["clean"])
        self.assertEqual(result["github_stars"]["real"], 0)
        self.assertFalse(result["broken"])

    def test_no_live_count_and_no_prior_log_is_clean(self):
        self._write_metrics([{"date": "2026-07-30", "github_stars": 0}])
        result = rc.run_ritual_check(
            github_stars_metrics_path=self.metrics_path,
            github_stars_log_path=self.log_path,
        )
        self.assertTrue(result["github_stars"]["clean"])
        self.assertIsNone(result["github_stars"]["real"])
        self.assertFalse(result["broken"])

    def test_run_ritual_check_default_does_not_touch_the_real_log(self):
        """Task 374/375's own bare-call guarantee, applied here: a bare
        rc.run_ritual_check() (the shape every dev-verification and every
        other test in this file already makes) must never write the real
        production HAND/github-stars-log.jsonl, since it passes neither
        github_stars_count nor record_github_stars."""
        real_log = rc._github_stars_check().LOG
        before = os.path.exists(real_log) and os.path.getsize(real_log)
        rc.run_ritual_check()
        after = os.path.exists(real_log) and os.path.getsize(real_log)
        self.assertEqual(before, after)


class GitHubStarsWriteDefaultCase(unittest.TestCase):
    """Task 420, mirroring ScribeGrowthWriteDefaultCase exactly: proves
    the write-by-default class of bug (tasks 374/375) is closed at its
    actual source -- the real, unpatched github_stars_check.py module,
    redirected only to a tmp LOG path, not to a patched loader."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        real_gsc = _load("_test_real_github_stars_check", os.path.join(ROOT, "tools", "github_stars_check.py"))
        real_gsc.LOG = os.path.join(self.tmpdir, "github-stars-log.jsonl")
        original_loader = rc._github_stars_check
        rc._github_stars_check = lambda: real_gsc
        self.addCleanup(setattr, rc, "_github_stars_check", original_loader)
        self.log_path = real_gsc.LOG

    def test_bare_call_with_a_live_count_but_no_record_flag_does_not_write(self):
        rc.run_ritual_check(github_stars_count=3)
        self.assertFalse(os.path.exists(self.log_path))

    def test_cli_main_records_for_real(self):
        """main() is the one real hourly entrypoint -- it must record,
        exactly once per invocation with a live count in hand, unchanged
        from before this fix."""
        captured = {}
        original = rc.run_ritual_check

        def capturing(*args, **kwargs):
            captured.update(kwargs)
            return original(*args, **kwargs)

        rc.run_ritual_check = capturing
        try:
            rc.main(["--github-stars", "3"])
        finally:
            rc.run_ritual_check = original
        self.assertTrue(captured.get("record_github_stars") is True)
        self.assertEqual(captured.get("github_stars_count"), 3)
        with open(self.log_path) as f:
            lines = [line for line in f.read().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)


class LoadJsonArgShapeGuardCase(unittest.TestCase):
    """ROADMAP.md task 364. `_load_json_arg` is the shared helper the CLI's
    six file-argument flags (`--square-state`, `--arcade-apps-state`,
    `--ci-checks`, `--cron-checks`, `--child-files`,
    `--voice-window-commits`) now all route through. Before this task each
    flag did a bare `json.load(f)` with no shape check, so a syntactically
    valid but wrong-shaped JSON file crashed two or three frames deeper
    with a bare `AttributeError`/`TypeError` instead of a named error --
    the identical bug class the closed `fencepost/seam_engine` campaigns
    (tasks 355-362) fixed at their own CLI/MCP entry points, on the one
    entry point those scans never reached: this file's own CLI."""

    def _write(self, value):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(value, f)
        f.close()
        self.addCleanup(os.remove, f.name)
        return f.name

    def test_bare_int_rejected_when_dict_expected(self):
        path = self._write(5)
        with self.assertRaises(rc.RitualCheckArgError):
            rc._load_json_arg(path, "square-state", "dict")

    def test_bare_list_rejected_when_dict_expected(self):
        path = self._write([1, 2])
        with self.assertRaises(rc.RitualCheckArgError):
            rc._load_json_arg(path, "square-state", "dict")

    def test_null_rejected_when_dict_expected(self):
        path = self._write(None)
        with self.assertRaises(rc.RitualCheckArgError):
            rc._load_json_arg(path, "arcade-apps-state", "dict")

    def test_bare_dict_rejected_when_list_expected(self):
        path = self._write({"a": 1})
        with self.assertRaises(rc.RitualCheckArgError):
            rc._load_json_arg(path, "ci-checks", "list")

    def test_bare_bool_rejected_when_list_expected(self):
        path = self._write(True)
        with self.assertRaises(rc.RitualCheckArgError):
            rc._load_json_arg(path, "cron-checks", "list")

    def test_bare_string_rejected_when_list_expected(self):
        path = self._write("oops")
        with self.assertRaises(rc.RitualCheckArgError):
            rc._load_json_arg(path, "child-files", "list")

    def test_error_message_names_the_flag_and_the_real_type(self):
        path = self._write(5)
        with self.assertRaises(rc.RitualCheckArgError) as ctx:
            rc._load_json_arg(path, "voice-window-commits", "list")
        self.assertIn("--voice-window-commits", str(ctx.exception))
        self.assertIn("got int", str(ctx.exception))

    def test_well_formed_dict_still_parses(self):
        path = self._write({"issues": [], "prs": []})
        self.assertEqual(rc._load_json_arg(path, "square-state", "dict"), {"issues": [], "prs": []})

    def test_well_formed_list_still_parses(self):
        path = self._write([{"workflow": "dawn-run"}])
        self.assertEqual(rc._load_json_arg(path, "ci-checks", "list"), [{"workflow": "dawn-run"}])


class CliMainArgShapeGuardCase(unittest.TestCase):
    """ROADMAP.md task 364, end-to-end through `main(argv)`: live pre-fix
    reproduction confirmed `--square-state` against a bare JSON int raised
    `AttributeError: 'int' object has no attribute 'get'`, and `--ci-checks`
    against a bare JSON int raised `TypeError: 'int' object is not
    iterable` -- both on the untouched module, before any file here was
    touched. Proves the CLI path itself now raises the named
    `RitualCheckArgError` instead."""

    def _write(self, value):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(value, f)
        f.close()
        self.addCleanup(os.remove, f.name)
        return f.name

    def test_square_state_bare_int_raises_named_error_not_attributeerror(self):
        path = self._write(5)
        with self.assertRaises(rc.RitualCheckArgError):
            rc.main(["--square-state", path])

    def test_arcade_apps_state_bare_string_raises_named_error(self):
        path = self._write("oops")
        with self.assertRaises(rc.RitualCheckArgError):
            rc.main(["--arcade-apps-state", path])

    def test_ci_checks_bare_int_raises_named_error_not_typeerror(self):
        path = self._write(5)
        with self.assertRaises(rc.RitualCheckArgError):
            rc.main(["--ci-checks", path])

    def test_cron_checks_bare_dict_raises_named_error(self):
        path = self._write({"workflow": "dawn-run"})
        with self.assertRaises(rc.RitualCheckArgError):
            rc.main(["--cron-checks", path])

    def test_child_files_bare_null_raises_named_error(self):
        path = self._write(None)
        with self.assertRaises(rc.RitualCheckArgError):
            rc.main(["--child-files", path])

    def test_voice_window_commits_bare_bool_raises_named_error(self):
        path = self._write(True)
        with self.assertRaises(rc.RitualCheckArgError):
            rc.main(["--voice-window-commits", path])

    def test_no_flags_runs_through_exactly_as_before(self):
        """The common no-live-reads path (this session's plain hourly
        `python3 tools/ritual_check.py`) must still behave identically
        after the refactor from a bare `__main__` block into `main(argv)`."""
        exit_code = rc.main([])
        self.assertIn(exit_code, (0, 1))


class ClusterDayFoldCase(unittest.TestCase):
    """Task 387: run_ritual_check() folds cluster_day_check.py's own
    weekly Cluster Day scan (TOWN-OPERATIONS.md's Monday ritual) into the
    same structured result -- a no-gap fixture prints a clean line, a
    real-gap fixture names the missed Mondays plainly, and neither ever
    flips `broken` (a lapsed weekly cadence is a fact worth surfacing to
    the next hour's run, not a currently-live law violation, the same
    class `report_cadence`/`metrics_cadence` already hold)."""

    def setUp(self):
        self.chronicle = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.chronicle, ignore_errors=True)

    def _write(self, rel, content="x"):
        path = os.path.join(self.chronicle, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_no_gap_fixture_prints_clean_and_never_flips_broken(self):
        from datetime import date

        self._write("001-the-founding.md")
        result = rc.run_ritual_check(cluster_day_dir=self.chronicle, cluster_day_today=date(2026, 7, 11))
        self.assertEqual(result["cluster_day"]["missed_mondays"], [])
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("cluster day: current", formatted)

    def test_gap_fixture_is_named_but_still_never_flips_broken(self):
        from datetime import date

        self._write("001-the-founding.md")
        result = rc.run_ritual_check(cluster_day_dir=self.chronicle, cluster_day_today=date(2026, 7, 29))
        self.assertEqual(
            result["cluster_day"]["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"]
        )
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("3 Cluster Days lapsed", formatted)
        self.assertIn("2026-07-27", formatted)

    def test_default_dir_reads_the_real_chronicle_and_matches_direct_call(self):
        """No override: reads the real chronicle/ directory, the same
        default check_cluster_day_cadence falls back to -- proves the
        fold never duplicates or diverges from the module it wraps
        (`RealChronicleCase` in test_cluster_day_check.py already owns
        proving that module's own correctness against the real data)."""
        from datetime import date

        cdc = _load("_test_cluster_day_check", os.path.join(ROOT, "tools", "cluster_day_check.py"))
        direct = cdc.compute_cadence(today=date(2026, 7, 29))
        result = rc.run_ritual_check(cluster_day_today=date(2026, 7, 29))
        self.assertEqual(result["cluster_day"], direct)


class StrategyTargetsFoldCase(unittest.TestCase):
    """Task 407: run_ritual_check() folds strategy_targets_check.py's own
    STRATEGY.md-vs-code target cross-check (task 159) into the same
    structured result. Unlike ClusterDayFoldCase's cadence tracker, real
    drift here IS a violation worth flipping `broken` -- the same class
    duplicate_regex/riders/hand_lore already hold: STRATEGY.md and the
    two real modules that quote it (report_cadence_check.py,
    shared_reports_check.py) claiming different numbers is exactly the
    "hand-typed copy, never rechecked against the thing it claims to
    mirror" bug task 159 built this checker to catch."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write_strategy(self, streak, shares, stars=1000, connected_users=100, toolkits=5):
        path = os.path.join(self.tmp, "STRATEGY.md")
        with open(path, "w") as f:
            f.write(
                "# fixture\n\n"
                "| metric | type | target | owner |\n"
                "|--|--|--|--|\n"
                f"| Daily Fencepost Report shipped (town dogfood) | leading | {streak} of {streak} days, 1/day | off-by-one |\n"
                f"| Shared Fencepost Reports in the wild | lagging | {shares} organic links/screenshots | kwaku-ananse |\n"
                f"| GitHub stars | lagging | {stars} (Star Covenant, unbegged) | off-by-one |\n"
                f"| \"Connect your own\" OAuth completions across users | leading | {connected_users} connected users in 60 days | kothar-wa-khasis |\n"
                f"| Distinct read-only toolkits connected across users (Arcade breadth) | leading | >={toolkits} toolkits in real use | nisaba |\n"
            )
        return path

    def test_agreeing_fixture_is_clean_and_never_flips_broken(self):
        # Real code constants are 30/50/1000/100/5 (report_cadence_check.py,
        # shared_reports_check.py, github_stars_check.py,
        # connected_users_check.py, toolkits_in_use_check.py) -- a fixture
        # naming the same numbers must read clean.
        path = self._write_strategy(30, 50, 1000, 100, 5)
        result = rc.run_ritual_check(strategy_targets_path=path)
        self.assertTrue(result["strategy_targets"]["clean"])
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("strategy target (report cadence): STRATEGY.md=30 code=30 -- agree", formatted)
        self.assertIn("strategy target (shared reports): STRATEGY.md=50 code=50 -- agree", formatted)
        self.assertIn("strategy target (github stars): STRATEGY.md=1000 code=1000 -- agree", formatted)
        self.assertIn("strategy target (connected users): STRATEGY.md=100 code=100 -- agree", formatted)
        self.assertIn("strategy target (toolkits): STRATEGY.md=5 code=5 -- agree", formatted)

    def test_drifted_fixture_is_named_and_flips_broken(self):
        # A plausible future decree (STRATEGY.md moves its target, code
        # never catches up) must be loud, not silent.
        path = self._write_strategy(60, 100, 2000, 300, 8)
        result = rc.run_ritual_check(strategy_targets_path=path)
        self.assertFalse(result["strategy_targets"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("strategy target (report cadence): STRATEGY.md=60 code=30 -- DRIFT", formatted)
        self.assertIn("strategy target (shared reports): STRATEGY.md=100 code=50 -- DRIFT", formatted)
        self.assertIn("strategy target (github stars): STRATEGY.md=2000 code=1000 -- DRIFT", formatted)
        self.assertIn("strategy target (connected users): STRATEGY.md=300 code=100 -- DRIFT", formatted)
        self.assertIn("strategy target (toolkits): STRATEGY.md=8 code=5 -- DRIFT", formatted)

    def test_only_github_stars_drifted_still_flips_broken(self):
        # The other four rows agree; only github stars drifts -- proves
        # `all(row["agree"] ...)` catches a lone-row drift, not just a
        # whole-fixture one.
        path = self._write_strategy(30, 50, 2000, 100, 5)
        result = rc.run_ritual_check(strategy_targets_path=path)
        self.assertFalse(result["strategy_targets"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("strategy target (report cadence): STRATEGY.md=30 code=30 -- agree", formatted)
        self.assertIn("strategy target (shared reports): STRATEGY.md=50 code=50 -- agree", formatted)
        self.assertIn("strategy target (github stars): STRATEGY.md=2000 code=1000 -- DRIFT", formatted)
        self.assertIn("strategy target (connected users): STRATEGY.md=100 code=100 -- agree", formatted)
        self.assertIn("strategy target (toolkits): STRATEGY.md=5 code=5 -- agree", formatted)

    def test_only_toolkits_drifted_still_flips_broken(self):
        # The other four rows agree; only the newest (fifth) row drifts --
        # proves the fold's genericness catches a drift on the row added
        # last, not just the ones that existed when the fold was written.
        path = self._write_strategy(30, 50, 1000, 100, 9)
        result = rc.run_ritual_check(strategy_targets_path=path)
        self.assertFalse(result["strategy_targets"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("strategy target (toolkits): STRATEGY.md=9 code=5 -- DRIFT", formatted)

    def test_default_path_reads_the_real_strategy_md_and_matches_direct_call(self):
        """No override: reads the real STRATEGY.md, the same default
        check_strategy_targets falls back to -- proves the fold never
        duplicates or diverges from the module it wraps."""
        stc = _load("_test_strategy_targets_check", os.path.join(ROOT, "tools", "strategy_targets_check.py"))
        direct = stc.check_strategy_targets()
        result = rc.run_ritual_check()
        self.assertEqual(result["strategy_targets"]["report_streak"], direct["report_streak"])
        self.assertEqual(result["strategy_targets"]["shared_reports"], direct["shared_reports"])
        self.assertEqual(result["strategy_targets"]["github_stars"], direct["github_stars"])
        self.assertEqual(result["strategy_targets"]["connected_users"], direct["connected_users"])
        self.assertEqual(result["strategy_targets"]["toolkits"], direct["toolkits"])
        self.assertTrue(result["strategy_targets"]["clean"])


class StrategyTruePositiveFoldCase(unittest.TestCase):
    """Task 410: run_ritual_check() folds strategy_audit_target.py's own
    STRATEGY.md-vs-live-Ledger true-positive rate cross-check (task 161)
    into the same structured result. Real drift here IS a violation worth
    flipping `broken` -- the same class strategy_targets/network_boundary
    already hold: a genuine drop below STRATEGY.md's own stated `>=90%`
    bar, or a future decree the real Ledger can't clear, is exactly the
    "a doc claim silently drifts from what the live code proves" bug task
    161 built this checker to catch."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write_strategy(self, target_pct):
        path = os.path.join(self.tmp, "STRATEGY.md")
        with open(path, "w") as f:
            f.write(
                "# fixture\n\n"
                "| metric | type | target | owner |\n"
                "|--|--|--|--|\n"
                f"| Gap true-positive rate (self-audited) | leading | >={target_pct}% | ogun |\n"
            )
        return path

    def _scan(self, confidence=0.9, bar=0.70):
        return {
            "generated_at": "t",
            "repo": "x/orita",
            "window_hours": 24,
            "confidence_bar": bar,
            "separation_margin": 0.15,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "h",
                "detail": "d",
                "confidence": confidence,
                "evidence": ["https://github.com/x/orita/commit/0000000"],
                "label": "primary",
            },
            "tail": [{"slug": "coincidence-a", "confidence": 0.1, "label": "coincidence"}],
            "excluded": [],
        }

    def test_agreeing_fixture_is_clean_and_never_flips_broken(self):
        path = self._write_strategy(90)
        seam_ledger.append_scan(
            self._scan(confidence=0.9), now=datetime(2026, 7, 12, 12, tzinfo=timezone.utc), base=Path(self.tmp)
        )
        result = rc.run_ritual_check(
            strategy_true_positive_path=path, strategy_true_positive_ledger_base=self.tmp
        )
        self.assertTrue(result["strategy_true_positive"]["clean"])
        self.assertTrue(result["strategy_true_positive"]["meets_target"])
        self.assertFalse(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("strategy true-positive rate: clean", formatted)

    def test_drifted_fixture_flips_broken_and_is_named(self):
        # A plausible future regression: a real false positive alongside
        # confirmed gaps drops the live rate below STRATEGY.md's unmoved
        # 90% bar -- must be loud, not silent.
        path = self._write_strategy(90)
        seam_ledger.append_scan(
            self._scan(confidence=0.9), now=datetime(2026, 7, 12, 12, tzinfo=timezone.utc), base=Path(self.tmp)
        )
        seam_ledger.append_scan(
            self._scan(confidence=0.9), now=datetime(2026, 7, 13, 12, tzinfo=timezone.utc), base=Path(self.tmp)
        )
        seam_ledger.append_scan(
            self._scan(confidence=0.9), now=datetime(2026, 7, 14, 12, tzinfo=timezone.utc), base=Path(self.tmp)
        )
        seam_ledger.append_scan(
            self._scan(confidence=0.60, bar=0.70),
            now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
            base=Path(self.tmp),
        )
        result = rc.run_ritual_check(
            strategy_true_positive_path=path, strategy_true_positive_ledger_base=self.tmp
        )
        self.assertFalse(result["strategy_true_positive"]["clean"])
        self.assertEqual(result["strategy_true_positive"]["live_rate_pct"], 75.0)
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("strategy true-positive rate: BROKEN", formatted)

    def test_default_path_reads_the_real_strategy_md_and_matches_direct_call(self):
        """No override: reads the real STRATEGY.md and the real fencepost
        Ledger, the same defaults check_strategy_true_positive falls back
        to -- proves the fold never duplicates or diverges from the
        module it wraps."""
        sat = _load(
            "_test_strategy_audit_target",
            os.path.join(ROOT, "fencepost", "seam_engine", "src", "seam_engine", "strategy_audit_target.py"),
        )
        direct = sat.check_strategy_true_positive_target()
        result = rc.run_ritual_check()
        self.assertEqual(result["strategy_true_positive"]["strategy_target_pct"], direct["strategy_target_pct"])
        self.assertEqual(result["strategy_true_positive"]["live_rate_pct"], direct["live_rate_pct"])
        self.assertEqual(result["strategy_true_positive"]["meets_target"], direct["meets_target"])
        self.assertTrue(result["strategy_true_positive"]["clean"])


class NetworkBoundaryFoldCase(unittest.TestCase):
    """Task 408: run_ritual_check() folds network_boundary_check.py's own
    AST-based "no network" trust-boundary sweep (tasks 163/164) into the
    same structured result -- clean by default against a fixture with no
    violation, and a real synthetic "no network"-claiming file that
    actually imports a network-capable module both flips `broken` and
    surfaces in the printed block, the same class duplicate_regex/riders/
    strategy_targets already hold."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def _write(self, rel, content):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write(
            "clean_tool.py",
            '"""Reads local state only, no network calls."""\nimport os\n',
        )
        result = rc.run_ritual_check(network_boundary_dirs=(self.dir,))
        self.assertTrue(result["network_boundary"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("network boundary: clean", rc.format_ritual_check(result))

    def test_synthetic_violation_flips_broken_and_prints(self):
        self._write(
            "bad_tool.py",
            '"""Reads local state only, no network calls."""\nimport httpx\n',
        )
        result = rc.run_ritual_check(network_boundary_dirs=(self.dir,))
        self.assertFalse(result["network_boundary"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("network boundary: BROKEN", formatted)
        self.assertIn("bad_tool.py", formatted)

    def test_default_dirs_read_the_real_tree_and_match_direct_call(self):
        """No override: reads the real tools/ + seam_engine/ tree, the same
        default check_network_boundary falls back to -- proves the fold
        never duplicates or diverges from the module it wraps."""
        nbc = _load("_test_network_boundary_check", os.path.join(ROOT, "tools", "network_boundary_check.py"))
        direct = nbc.check_network_boundary_all()
        result = rc.run_ritual_check()
        self.assertEqual(result["network_boundary"]["count"], len(direct))
        self.assertEqual(result["network_boundary"]["clean"], all(r["ok"] for r in direct.values()))


class SiteLinkFoldCase(unittest.TestCase):
    """Task 423: run_ritual_check() folds site_link_check.py's own
    internal-link scan (CHARTER.md Appendix B's "links unbroken", Ogun's
    own charter duty, never previously checked in code) into the same
    structured result -- clean by default against a fixture with no
    broken link, and a real synthetic broken relative link both flips
    `broken` and surfaces in the printed block, the same class
    duplicate_regex/riders/network_boundary already hold."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def _write(self, rel, content):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write("gods/ogun.html", "<html></html>")
        self._write("index.html", '<a href="gods/ogun.html">Ogun</a>')
        result = rc.run_ritual_check(site_link_docs_dir=self.dir)
        self.assertTrue(result["site_links"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("site links: clean", rc.format_ritual_check(result))

    def test_synthetic_broken_link_flips_broken_and_prints(self):
        self._write("index.html", '<a href="gods/nobody.html">nobody</a>')
        result = rc.run_ritual_check(site_link_docs_dir=self.dir)
        self.assertFalse(result["site_links"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("BROKEN LINK(S)", formatted)

    def test_default_docs_dir_reads_the_real_tree_and_matches_direct_call(self):
        """No override: reads the real docs/ tree, the same default
        check_site_links falls back to -- proves the fold never
        duplicates or diverges from the module it wraps."""
        slc = _load("_test_site_link_check", os.path.join(ROOT, "tools", "site_link_check.py"))
        slc.clear_cache()
        direct = slc.find_violations()
        result = rc.run_ritual_check()
        self.assertEqual(result["site_links"]["count"], len(direct))
        self.assertEqual(result["site_links"]["clean"], not direct)


class RecipeReadmeFoldCase(unittest.TestCase):
    """Task 426: run_ritual_check() folds recipe_readme_check.py's own
    two-way cross-check of fencepost/README.md's Community recipes
    section against the live discover_recipes() tree into the same
    structured result -- clean by default against a fixture where the
    README and the RECIPES/ tree agree, and a synthetic stale link (a
    recipe linked in the README but removed from disk) both flips
    `broken` and surfaces in the printed block, the same class
    site_links/badge_freshness already hold."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def _write_recipe(self, slug):
        import json as _json
        recipe_dir = os.path.join(self.dir, "RECIPES", slug)
        os.makedirs(recipe_dir, exist_ok=True)
        manifest = {
            "slug": slug,
            "title": f"{slug} title",
            "author": "nisaba",
            "description": f"{slug} description",
            "toolkit": "github",
            "scopes": ["GetRepository"],
            "fixture": "fixtures/dummy",
            "detector_file": "detector.py",
            "entrypoint": "run_recipe_scan",
            "confidence_notes": "fixed 0.80",
        }
        with open(os.path.join(recipe_dir, "recipe.json"), "w") as f:
            _json.dump(manifest, f)

    def _write_readme(self, section):
        path = os.path.join(self.dir, "README.md")
        with open(path, "w") as f:
            f.write(section)
        return path

    def test_clean_fixture_is_not_broken(self):
        self._write_recipe("alpha-gap")
        readme_path = self._write_readme(
            "## Community recipes\n\n[`RECIPES/alpha-gap/`](RECIPES/alpha-gap/) is the first.\n\n## Run your own\n"
        )
        result = rc.run_ritual_check(recipe_readme_path=readme_path, recipe_readme_fencepost_root=self.dir)
        self.assertTrue(result["recipe_readme"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("recipe readme: clean", rc.format_ritual_check(result))

    def test_stale_link_to_a_removed_recipe_flips_broken_and_prints(self):
        # alpha-gap is linked but never written to disk -- a dead link.
        readme_path = self._write_readme(
            "## Community recipes\n\n[`RECIPES/alpha-gap/`](RECIPES/alpha-gap/) is the first.\n\n## Run your own\n"
        )
        result = rc.run_ritual_check(recipe_readme_path=readme_path, recipe_readme_fencepost_root=self.dir)
        self.assertFalse(result["recipe_readme"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("recipe readme: BROKEN", formatted)
        self.assertIn("alpha-gap", formatted)

    def test_default_paths_read_the_real_tree_and_match_direct_call(self):
        """No override: reads the real fencepost/README.md and RECIPES/
        tree, the same default check_recipe_readme falls back to -- proves
        the fold never duplicates or diverges from the module it wraps."""
        rrc = _load("_test_recipe_readme_check", os.path.join(ROOT, "tools", "recipe_readme_check.py"))
        direct = rrc.check_recipe_readme()
        result = rc.run_ritual_check()
        self.assertEqual(result["recipe_readme"]["clean"], direct["clean"])
        self.assertEqual(result["recipe_readme"]["real_count"], direct["real_count"])


class EscapeSequenceFoldCase(unittest.TestCase):
    """Task 434: run_ritual_check() folds escape_sequence_check.py's own
    repo-wide compile-time scan into the same structured result -- clean
    by default against a fixture with no invalid escape sequence, and a
    synthetic real one (the exact live shape found this hour in
    tools/roadmap_archive.py:2) both flips `broken` and surfaces in the
    printed block, the same class site_links/recipe_readme already
    hold."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def _write(self, rel, content):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def test_clean_fixture_is_not_broken(self):
        self._write("ok.py", "x = 1\n")
        result = rc.run_ritual_check(escape_sequence_orita_dir=self.dir)
        self.assertTrue(result["escape_sequences"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("escape sequences: clean", rc.format_ritual_check(result))

    def test_synthetic_invalid_escape_flips_broken_and_prints(self):
        self._write("bad.py", '"""an example grep pattern: \\|"""\n')
        result = rc.run_ritual_check(escape_sequence_orita_dir=self.dir)
        self.assertFalse(result["escape_sequences"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("escape sequences: BROKEN", formatted)
        self.assertIn("bad.py", formatted)

    def test_default_dir_reads_the_real_tree_and_matches_direct_call(self):
        """No override: reads the real repo tree, the same default
        check_escape_sequences falls back to -- proves the fold never
        duplicates or diverges from the module it wraps."""
        esc = _load("_test_escape_sequence_check", os.path.join(ROOT, "tools", "escape_sequence_check.py"))
        esc.clear_cache()
        direct = esc.find_violations()
        result = rc.run_ritual_check()
        self.assertEqual(result["escape_sequences"]["count"], len(direct))
        self.assertEqual(result["escape_sequences"]["clean"], not direct)


class RitualCompletenessToolFilesFoldCase(unittest.TestCase):
    """Task 409: ritual_completeness_check.py's own audit widened to also
    catch a whole tools/*.py file never loaded from run_ritual_check at
    all -- not just a check_* function already inside ritual_check.py's
    own source going unwired (the three violations ClusterDayFoldCase's
    neighbors already cover). run_ritual_check()'s new
    `ritual_completeness_tools_dir` param lets this point that half of the
    audit at a fixture directory instead of the real, live tools/, the
    same pattern StrategyTargetsFoldCase/NetworkBoundaryFoldCase already
    use for their own fixture inputs."""

    FIXTURE = '''
def check_alpha():
    return {"ok": True}


def run_ritual_check():
    a = check_alpha()
    return {"now": "x", "alpha": a, "broken": False}


def format_ritual_check(result):
    return f"alpha: {result['alpha']}"
'''

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.fixture_path = os.path.join(self.dir, "fixture_ritual_check.py")
        with open(self.fixture_path, "w") as f:
            f.write(self.FIXTURE)
        self.tools_dir = os.path.join(self.dir, "tools")
        os.makedirs(self.tools_dir)
        self.seam_engine_dir = os.path.join(self.dir, "seam_engine")
        os.makedirs(self.seam_engine_dir)

    def test_empty_tools_dir_is_clean(self):
        result = rc.run_ritual_check(
            ritual_completeness_path=self.fixture_path,
            ritual_completeness_tools_dir=self.tools_dir,
            ritual_completeness_seam_engine_dir=self.seam_engine_dir,
        )
        self.assertTrue(result["ritual_completeness"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("ritual completeness: clean", rc.format_ritual_check(result))

    def test_unreferenced_tool_file_flips_broken_and_prints(self):
        with open(os.path.join(self.tools_dir, "orphan_check.py"), "w") as f:
            f.write("# fixture\n")
        result = rc.run_ritual_check(
            ritual_completeness_path=self.fixture_path,
            ritual_completeness_tools_dir=self.tools_dir,
            ritual_completeness_seam_engine_dir=self.seam_engine_dir,
        )
        self.assertFalse(result["ritual_completeness"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("ritual completeness: BROKEN", formatted)
        self.assertIn("orphan_check.py", formatted)


class RitualCompletenessSeamEngineFoldCase(unittest.TestCase):
    """Task 411: ritual_completeness_check.py's own audit widened again to
    catch the sibling shape one directory over -- a
    fencepost/seam_engine/src/seam_engine/*.py module holding a live
    STRATEGY_MD cross-check that never got wired into run_ritual_check
    (the exact shape strategy_audit_target.py held for 249 tasks, task
    410's own closing note left as future work). run_ritual_check()'s new
    `ritual_completeness_seam_engine_dir` param lets this point that third
    half of the audit at a fixture directory instead of the real, live
    seam_engine/, the same pattern
    RitualCompletenessToolFilesFoldCase already uses for tools_dir."""

    FIXTURE = '''
def check_alpha():
    return {"ok": True}


def run_ritual_check():
    import seam_engine.alpha_target as at  # noqa
    a = check_alpha()
    return {"now": "x", "alpha": a, "broken": False}


def format_ritual_check(result):
    return f"alpha: {result['alpha']}"
'''

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.fixture_path = os.path.join(self.dir, "fixture_ritual_check.py")
        with open(self.fixture_path, "w") as f:
            f.write(self.FIXTURE)
        self.tools_dir = os.path.join(self.dir, "tools")
        os.makedirs(self.tools_dir)
        self.seam_engine_dir = os.path.join(self.dir, "seam_engine")
        os.makedirs(self.seam_engine_dir)

    def test_empty_seam_engine_dir_is_clean(self):
        result = rc.run_ritual_check(
            ritual_completeness_path=self.fixture_path,
            ritual_completeness_tools_dir=self.tools_dir,
            ritual_completeness_seam_engine_dir=self.seam_engine_dir,
        )
        self.assertTrue(result["ritual_completeness"]["clean"])
        self.assertFalse(result["broken"])
        self.assertIn("ritual completeness: clean", rc.format_ritual_check(result))

    def test_unreferenced_strategy_module_flips_broken_and_prints(self):
        with open(os.path.join(self.seam_engine_dir, "orphan_target.py"), "w") as f:
            f.write('STRATEGY_MD = "STRATEGY.md"\n')
        result = rc.run_ritual_check(
            ritual_completeness_path=self.fixture_path,
            ritual_completeness_tools_dir=self.tools_dir,
            ritual_completeness_seam_engine_dir=self.seam_engine_dir,
        )
        self.assertFalse(result["ritual_completeness"]["clean"])
        self.assertTrue(result["broken"])
        formatted = rc.format_ritual_check(result)
        self.assertIn("ritual completeness: BROKEN", formatted)
        self.assertIn("orphan_target.py", formatted)

    def test_real_ritual_check_path_and_real_seam_engine_dir_agree_clean(self):
        # Both defaulted to the real, live files: run_ritual_check's own
        # entry point must read the same zero-violations state
        # RealRitualCheckCase's direct compute_ritual_completeness() call
        # proves in tests/test_ritual_completeness_check.py -- no silent
        # divergence between the two entry points.
        result = rc.run_ritual_check()
        self.assertEqual(result["ritual_completeness"]["unwired_strategy_audit_modules"], [])
        self.assertTrue(result["ritual_completeness"]["clean"])


if __name__ == "__main__":
    unittest.main()
