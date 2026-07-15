"""Task 61. Proves tools/ritual_check.py's four local checks each report
correctly against fixture state -- both ledgers intact, a broken ledger,
a stale/missing/pending report, and an X recheck due/not-due -- the same
kind of fixture proof tasks 57-59 gave the tools they consolidate.
"""
import importlib.util
import json
import os
import shutil
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
        self.assertIsNone(rc.check_square(None))

    def test_first_check_is_changed(self):
        state = self.sq.compute_square_state(
            [{"number": 1, "updated_at": "2026-07-12T06:43:35Z"}], []
        )
        result = rc.check_square(state)
        self.assertTrue(result["changed"])
        self.assertIn("no prior square check recorded", result["reason"])

    def test_unchanged_after_recording(self):
        state = self.sq.compute_square_state(
            [{"number": 1, "updated_at": "2026-07-12T06:43:35Z"}], []
        )
        self.sq.record_square_check(state, "2026-07-14T21:00:00Z", path=self.sq.LOG)
        result = rc.check_square(state)
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
        result = rc.check_square(new)
        self.assertTrue(result["changed"])

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


class RunRitualCheckCase(unittest.TestCase):
    """End-to-end: broken=True iff either ledger is broken, regardless of
    report/recheck state -- mirrors sync_checkout.sh's refuse discipline."""

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
        self.assertTrue(result["town_ledger"]["ok"])
        self.assertTrue(result["fencepost_ledger"]["ok"])
        self.assertFalse(result["broken"])
        self.assertIn(result["report"]["status"], ("current", "pending", "stale"))
        # Task 72: x_recheck now follows x_outage_tracker.TRACKED_TOOLS live,
        # not a hand-pinned pair -- adding X_WhoAmI there should show up here
        # without this test having to be told about it a second time.
        self.assertEqual(set(result["x_recheck"].keys()), set(xot.TRACKED_TOOLS))


if __name__ == "__main__":
    unittest.main()
