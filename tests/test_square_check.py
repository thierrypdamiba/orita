"""Task 70. The square's own read, made testable: proves the "has anything
in the open issues/PRs changed since last hour" call -- made by hand in
every BUILDLOG ritual line since `ritual_check.py` explicitly scoped the
square out -- resolves the same way every time, instead of by recall.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "square_check", os.path.join(ROOT, "tools", "square_check.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sc = _load()
LOG_DEFAULT = sc.LOG

ISSUES_BASE = [
    {"number": 1, "updated_at": "2026-07-11T10:58:21Z"},
    {"number": 2, "updated_at": "2026-07-11T10:58:22Z"},
    {"number": 3, "updated_at": "2026-07-11T10:58:24Z"},
    {"number": 5, "updated_at": "2026-07-12T06:43:35Z"},
]
PRS_NONE = []


class _TempLogCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.path)  # record_square_check/_append must create it fresh

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)


class TestComputeSquareState(unittest.TestCase):
    def test_folds_issue_and_pr_numbers(self):
        state = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        self.assertEqual(state["issue_numbers"], [1, 2, 3, 5])
        self.assertEqual(state["pr_numbers"], [])

    def test_max_updated_at_is_the_latest_across_issues_and_prs(self):
        state = sc.compute_square_state(
            ISSUES_BASE, [{"number": 7, "updated_at": "2026-07-14T20:00:00Z"}]
        )
        self.assertEqual(state["max_updated_at"], "2026-07-14T20:00:00Z")

    def test_max_updated_at_is_none_when_the_square_is_empty(self):
        state = sc.compute_square_state([], [])
        self.assertIsNone(state["max_updated_at"])

    def test_sorts_issue_numbers_regardless_of_input_order(self):
        shuffled = [ISSUES_BASE[2], ISSUES_BASE[0], ISSUES_BASE[3], ISSUES_BASE[1]]
        state = sc.compute_square_state(shuffled, PRS_NONE)
        self.assertEqual(state["issue_numbers"], [1, 2, 3, 5])


class TestRecordSquareCheck(_TempLogCase):
    def test_records_a_line(self):
        state = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(state, "2026-07-14T21:00:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_never_edits_a_prior_line(self):
        state = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(state, "2026-07-14T20:00:00Z", path=self.path)
        with open(self.path) as f:
            before = f.readlines()
        sc.record_square_check(state, "2026-07-14T21:00:00Z", path=self.path)
        with open(self.path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)


class TestRecordSquareCheckDegenerateGuard(_TempLogCase):
    """Task 124: an all-empty state must never silently overwrite a real,
    non-empty prior baseline -- the exact way four bogus lines landed in the
    real HAND/square-check-log.jsonl on 2026-07-18."""

    def test_refuses_empty_over_non_empty_baseline(self):
        real = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(real, "2026-07-18T02:11:15Z", path=self.path)
        empty = sc.compute_square_state([], [])
        with self.assertRaises(sc.DegenerateSquareStateError):
            sc.record_square_check(empty, "2026-07-18T04:02:23Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)  # nothing new was written

    def test_force_true_still_allows_it(self):
        real = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(real, "2026-07-18T02:11:15Z", path=self.path)
        empty = sc.compute_square_state([], [])
        sc.record_square_check(empty, "2026-07-18T04:02:23Z", path=self.path, force=True)
        last = sc.last_square_state(path=self.path)
        self.assertEqual(last["issue_numbers"], [])

    def test_empty_over_no_prior_check_is_allowed(self):
        empty = sc.compute_square_state([], [])
        sc.record_square_check(empty, "2026-07-18T04:02:23Z", path=self.path)
        last = sc.last_square_state(path=self.path)
        self.assertEqual(last["issue_numbers"], [])

    def test_empty_over_empty_prior_baseline_is_allowed(self):
        empty = sc.compute_square_state([], [])
        sc.record_square_check(empty, "2026-07-18T02:00:00Z", path=self.path)
        sc.record_square_check(empty, "2026-07-18T03:00:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 2)

    def test_ordinary_non_empty_record_is_unaffected(self):
        state1 = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(state1, "2026-07-18T02:11:15Z", path=self.path)
        state2 = sc.compute_square_state(
            ISSUES_BASE + [{"number": 6, "updated_at": "2026-07-18T05:00:00Z"}],
            PRS_NONE,
        )
        sc.record_square_check(state2, "2026-07-18T05:00:00Z", path=self.path)
        last = sc.last_square_state(path=self.path)
        self.assertEqual(last["issue_numbers"], [1, 2, 3, 5, 6])


class TestCliRecordRefusal(_TempLogCase):
    def _write_state(self, path, payload):
        with open(path, "w") as f:
            json.dump(payload, f)

    def test_cli_record_refuses_malformed_state_json(self):
        real = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(real, "2026-07-18T02:11:15Z", path=self.path)
        sc.LOG = self.path
        try:
            fd, state_path = tempfile.mkstemp(suffix=".json")
            os.close(fd)
            self._write_state(state_path, {})  # missing issues/prs entirely
            rc = sc.main(["square_check.py", "record", state_path, "2026-07-18T04:02:23Z"])
            self.assertEqual(rc, 1)
            with open(self.path) as f:
                lines = [ln for ln in f if ln.strip()]
            self.assertEqual(len(lines), 1)  # still just the real entry
        finally:
            sc.LOG = LOG_DEFAULT
            os.remove(state_path)

    def test_cli_record_force_flag_allows_malformed_state_json(self):
        real = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(real, "2026-07-18T02:11:15Z", path=self.path)
        sc.LOG = self.path
        try:
            fd, state_path = tempfile.mkstemp(suffix=".json")
            os.close(fd)
            self._write_state(state_path, {})
            rc = sc.main(
                ["square_check.py", "record", state_path, "2026-07-18T04:02:23Z", "--force"]
            )
            self.assertEqual(rc, 0)
            with open(self.path) as f:
                lines = [ln for ln in f if ln.strip()]
            self.assertEqual(len(lines), 2)
        finally:
            sc.LOG = LOG_DEFAULT
            os.remove(state_path)


class TestLastSquareState(_TempLogCase):
    def test_none_when_never_checked(self):
        self.assertIsNone(sc.last_square_state(path=self.path))

    def test_returns_the_most_recent_not_the_first(self):
        state1 = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(state1, "2026-07-14T20:00:00Z", path=self.path)
        state2 = sc.compute_square_state(
            ISSUES_BASE + [{"number": 6, "updated_at": "2026-07-14T21:00:00Z"}],
            PRS_NONE,
        )
        sc.record_square_check(state2, "2026-07-14T21:00:00Z", path=self.path)
        last = sc.last_square_state(path=self.path)
        self.assertEqual(last["issue_numbers"], [1, 2, 3, 5, 6])


class TestSquareDelta(_TempLogCase):
    def test_due_when_never_checked_before(self):
        state = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        changed, reason = sc.square_delta(state, path=self.path)
        self.assertTrue(changed)
        self.assertIn("no prior square check", reason)

    def test_not_due_when_fully_unchanged(self):
        state = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(state, "2026-07-14T20:00:00Z", path=self.path)
        changed, reason = sc.square_delta(state, path=self.path)
        self.assertFalse(changed)
        self.assertIn("unchanged since 2026-07-12T06:43:35Z", reason)

    def test_due_when_issue_set_changed(self):
        state1 = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(state1, "2026-07-14T20:00:00Z", path=self.path)
        state2 = sc.compute_square_state(
            ISSUES_BASE + [{"number": 6, "updated_at": "2026-07-14T21:00:00Z"}],
            PRS_NONE,
        )
        changed, reason = sc.square_delta(state2, path=self.path)
        self.assertTrue(changed)
        self.assertIn("open issue set changed", reason)

    def test_due_when_pr_set_changed(self):
        state1 = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(state1, "2026-07-14T20:00:00Z", path=self.path)
        state2 = sc.compute_square_state(
            ISSUES_BASE, [{"number": 7, "updated_at": "2026-07-14T21:00:00Z"}]
        )
        changed, reason = sc.square_delta(state2, path=self.path)
        self.assertTrue(changed)
        self.assertIn("open PR set changed", reason)

    def test_due_when_max_updated_at_moved_with_the_same_numbers(self):
        state1 = sc.compute_square_state(ISSUES_BASE, PRS_NONE)
        sc.record_square_check(state1, "2026-07-14T20:00:00Z", path=self.path)
        commented = [dict(i) for i in ISSUES_BASE]
        commented[0]["updated_at"] = "2026-07-14T21:30:00Z"  # a new comment on #1
        state2 = sc.compute_square_state(commented, PRS_NONE)
        changed, reason = sc.square_delta(state2, path=self.path)
        self.assertTrue(changed)
        self.assertIn("activity on an existing issue/PR", reason)


if __name__ == "__main__":
    unittest.main()
