"""Task 73. Durable CI-conclusion counting for dawn-run/pages: proves the
streak fold is exact in both directions, the same discipline task 57's
test suite already proved for the X outage log, applied to the one ritual
number that has only ever been read out loud from memory -- "dawn-run/pages
both green off task N's push."
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location("ci_watch", os.path.join(ROOT, "tools", "ci_watch.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ciw = _load()


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
        ciw.record_check("dawn-run", "success", 111, "2026-07-14T23:08:01Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_rejects_an_unknown_conclusion(self):
        with self.assertRaises(ValueError):
            ciw.record_check("dawn-run", "flaky", 111, "2026-07-14T23:08:01Z", path=self.path)
        self.assertFalse(os.path.exists(self.path))

    def test_never_edits_a_prior_line(self):
        ciw.record_check("dawn-run", "success", 111, "2026-07-14T21:00:00Z", path=self.path)
        with open(self.path) as f:
            before = f.readlines()
        ciw.record_check("dawn-run", "failure", 112, "2026-07-14T22:00:00Z", path=self.path)
        with open(self.path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)


class TestCurrentStreak(_TempLogCase):
    def test_no_checks_is_zero(self):
        self.assertEqual(ciw.current_streak([], "dawn-run"), 0)

    def test_trailing_run_is_exact_not_off_by_one(self):
        entries = []
        for conclusion in ("success", "failure", "failure", "failure"):
            ciw.record_check("dawn-run", conclusion, 1, "2026-07-14T00:00:00Z", path=self.path)
        with open(self.path) as f:
            import json

            entries = [json.loads(ln) for ln in f if ln.strip()]
        self.assertEqual(ciw.current_streak(entries, "dawn-run", "failure"), 3)

    def test_streak_broken_by_a_success_resets_to_zero(self):
        import json

        for conclusion in ("failure", "failure", "success"):
            ciw.record_check("dawn-run", conclusion, 1, "2026-07-14T00:00:00Z", path=self.path)
        with open(self.path) as f:
            entries = [json.loads(ln) for ln in f if ln.strip()]
        self.assertEqual(ciw.current_streak(entries, "dawn-run", "failure"), 0)

    def test_streak_is_scoped_per_workflow(self):
        import json

        ciw.record_check("dawn-run", "failure", 1, "2026-07-14T00:00:00Z", path=self.path)
        ciw.record_check("pages", "success", 2, "2026-07-14T00:00:00Z", path=self.path)
        ciw.record_check("dawn-run", "failure", 3, "2026-07-14T01:00:00Z", path=self.path)
        with open(self.path) as f:
            entries = [json.loads(ln) for ln in f if ln.strip()]
        self.assertEqual(ciw.current_streak(entries, "dawn-run", "failure"), 2)
        self.assertEqual(ciw.current_streak(entries, "pages", "failure"), 0)


class TestFormatStatusLine(_TempLogCase):
    def test_no_checks_recorded(self):
        self.assertEqual(ciw.format_status_line([], "dawn-run"), "dawn-run: no checks recorded")

    def test_all_clear_shows_conclusion_and_run(self):
        ciw.record_check("dawn-run", "success", 999, "2026-07-14T23:08:01Z", path=self.path)
        entries = ciw._entries(self.path)
        line = ciw.format_status_line(entries, "dawn-run")
        self.assertEqual(line, "dawn-run: success as of 2026-07-14T23:08:01Z (run 999)")

    def test_failure_streak_names_since_and_last_checked(self):
        ciw.record_check("dawn-run", "success", 1, "2026-07-14T10:00:00Z", path=self.path)
        ciw.record_check("dawn-run", "failure", 2, "2026-07-14T11:00:00Z", path=self.path)
        ciw.record_check("dawn-run", "failure", 3, "2026-07-14T12:00:00Z", path=self.path)
        entries = ciw._entries(self.path)
        line = ciw.format_status_line(entries, "dawn-run")
        self.assertEqual(
            line,
            "dawn-run: 2 consecutive failure checks (since 2026-07-14T11:00:00Z, last checked 2026-07-14T12:00:00Z)",
        )


class TestTrackedWorkflows(unittest.TestCase):
    def test_dawn_run_and_pages_are_tracked(self):
        self.assertEqual(ciw.TRACKED_WORKFLOWS, ("dawn-run", "pages"))


if __name__ == "__main__":
    unittest.main()
