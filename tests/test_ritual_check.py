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


if __name__ == "__main__":
    unittest.main()
