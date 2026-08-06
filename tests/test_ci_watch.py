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

    def test_accepts_every_real_github_terminal_conclusion(self):
        # Task 580: GitHub Actions' own documented conclusion vocabulary is
        # wider than bare success/failure -- this repo's own real incident
        # (pages run 31119308176) hit "cancelled" live. Every one of these
        # must record without raising, or an honest recheck of a real run
        # crashes the whole ritual instead of recording the real outcome.
        for i, conclusion in enumerate(ciw.CONCLUSIONS):
            ciw.record_check("dawn-run", conclusion, i, f"2026-07-14T{i:02d}:00:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), len(ciw.CONCLUSIONS))

    def test_cancelled_is_not_conflated_with_failure_in_a_streak(self):
        # A cancelled run is a genuinely different outcome from a failed
        # one -- it must not silently extend (or count toward) a "failure"
        # streak, the exact mislabeling task 577's BUILDLOG entry was
        # forced into by this tuple's old binary-only shape.
        import json

        ciw.record_check("dawn-run", "failure", 1, "2026-07-14T00:00:00Z", path=self.path)
        ciw.record_check("dawn-run", "cancelled", 2, "2026-07-14T01:00:00Z", path=self.path)
        with open(self.path) as f:
            entries = [json.loads(ln) for ln in f if ln.strip()]
        self.assertEqual(ciw.current_streak(entries, "dawn-run", "failure"), 0)
        self.assertEqual(ciw.current_streak(entries, "dawn-run", "cancelled"), 1)

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
        # Task 501: each call now needs its own real checked_at -- three
        # byte-identical repeats of the same moment would dedup to one line
        # under the new guard, same as a real caller re-submitting the same
        # already-recorded observation. Three genuinely different real
        # moments landing on the same conclusion must still all count.
        entries = []
        for conclusion, checked_at in [
            ("success", "2026-07-14T00:00:00Z"),
            ("failure", "2026-07-14T01:00:00Z"),
            ("failure", "2026-07-14T02:00:00Z"),
            ("failure", "2026-07-14T03:00:00Z"),
        ]:
            ciw.record_check("dawn-run", conclusion, 1, checked_at, path=self.path)
        with open(self.path) as f:
            import json

            entries = [json.loads(ln) for ln in f if ln.strip()]
        self.assertEqual(ciw.current_streak(entries, "dawn-run", "failure"), 3)

    def test_streak_broken_by_a_success_resets_to_zero(self):
        import json

        for conclusion, checked_at in [
            ("failure", "2026-07-14T00:00:00Z"),
            ("failure", "2026-07-14T01:00:00Z"),
            ("success", "2026-07-14T02:00:00Z"),
        ]:
            ciw.record_check("dawn-run", conclusion, 1, checked_at, path=self.path)
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


class TestRecordCheckDedup(_TempLogCase):
    """Task 501: the real `HAND/ci-watch-log.jsonl` carries 84 byte-for-byte
    duplicate lines out of 431 -- task 495 found and named this live, then
    deliberately deferred fixing it. `record_check` now refuses to write an
    exact resubmission of the already-last-recorded entry for a workflow,
    while still writing every genuinely new observation, even one that
    repeats the same conclusion at a real new `checked_at` (the whole point
    of `current_streak`)."""

    def test_no_prior_check_always_writes(self):
        wrote = ciw.record_check("dawn-run", "success", 1, "2026-07-14T00:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 1)

    def test_exact_duplicate_is_skipped(self):
        ciw.record_check("dawn-run", "success", 111, "2026-07-14T21:00:00Z", path=self.path)
        wrote = ciw.record_check("dawn-run", "success", 111, "2026-07-14T21:00:00Z", path=self.path)
        self.assertFalse(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 1)

    def test_same_conclusion_and_run_id_but_a_new_checked_at_still_writes(self):
        # The exact case current_streak depends on: a real check an hour
        # later that happens to name the same already-completed run_id and
        # the same conclusion is still a genuinely new observation.
        ciw.record_check("dawn-run", "success", 111, "2026-07-14T21:00:00Z", path=self.path)
        wrote = ciw.record_check("dawn-run", "success", 111, "2026-07-14T22:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 2)

    def test_exact_duplicate_is_skipped_even_when_run_id_type_differs(self):
        # Task 541: reproduced live in HAND/ci-watch-log.jsonl. ritual_check.py's
        # check_ci feeds record_check a run_id straight off a JSON-decoded
        # --ci-checks file (a bare number parses as a Python int), while the
        # bare `ci_watch.py record` CLI always hands sys.argv's run_id through
        # as a str -- two entry points, same real GitHub run, two different
        # Python types. Task 501's dedup compared entry dicts with `==`, and
        # `{"run_id": 111} == {"run_id": "111"}` is False in Python even
        # though both name the identical real run, so the same real moment
        # recorded once via each entry point wrote two lines instead of one.
        ciw.record_check("dawn-run", "success", 111, "2026-07-14T21:00:00Z", path=self.path)
        wrote = ciw.record_check("dawn-run", "success", "111", "2026-07-14T21:00:00Z", path=self.path)
        self.assertFalse(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 1)

    def test_a_real_change_after_a_duplicate_still_writes(self):
        ciw.record_check("dawn-run", "failure", 1, "2026-07-14T00:00:00Z", path=self.path)
        skipped = ciw.record_check("dawn-run", "failure", 1, "2026-07-14T00:00:00Z", path=self.path)
        wrote = ciw.record_check("dawn-run", "success", 2, "2026-07-14T01:00:00Z", path=self.path)
        self.assertFalse(skipped)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 2)

    def test_dedup_is_scoped_per_workflow(self):
        # An exact duplicate for "pages" must not be suppressed just because
        # "dawn-run" happens to hold an identical-looking last entry.
        ciw.record_check("dawn-run", "success", 1, "2026-07-14T00:00:00Z", path=self.path)
        wrote = ciw.record_check("pages", "success", 1, "2026-07-14T00:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 2)

    def test_a_malformed_line_elsewhere_does_not_block_a_real_write(self):
        # Reading (current_streak/last_check) refuses to guess past a
        # corrupted log -- writing must not inherit that refusal, or a
        # single bad hand-edit anywhere in the log would permanently wedge
        # every future real check for every workflow.
        ciw.record_check("dawn-run", "success", 1, "2026-07-14T00:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write('{"type": "check", broken <<<< not json\n')
        wrote = ciw.record_check("dawn-run", "failure", 2, "2026-07-14T01:00:00Z", path=self.path)
        self.assertTrue(wrote)
        with open(self.path) as f:
            self.assertEqual(len(f.readlines()), 3)

    def test_return_value_is_a_bool_not_none(self):
        wrote = ciw.record_check("dawn-run", "success", 1, "2026-07-14T00:00:00Z", path=self.path)
        self.assertIs(wrote, True)
        wrote_again = ciw.record_check("dawn-run", "success", 1, "2026-07-14T00:00:00Z", path=self.path)
        self.assertIs(wrote_again, False)


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


class TestTamperedLog(_TempLogCase):
    def test_entries_marks_a_malformed_line_instead_of_raising(self):
        # A hand-edit, stray merge-conflict marker, or truncated write can
        # leave a line that isn't valid JSON at all -- _entries() must name
        # it, not crash with an uncaught json.JSONDecodeError (the exact
        # crash tools/ledger.py's _entries() had before task 238's fix).
        ciw.record_check("dawn-run", "success", 1, "2026-07-14T00:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write('{"type": "check", broken <<<< not json\n')
        entries = ciw._entries(path=self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_raises_tampered_error_when_a_malformed_line_exists_anywhere(self):
        # Unlike change_gate.py/word_watch.py's tip-only check, a malformed
        # entry here has lost its "workflow" field, so it could be silently
        # dropped from ANY workflow's view -- refuse rather than guess which
        # workflow's streak it belonged to, even if it isn't the last line.
        ciw.record_check("dawn-run", "success", 1, "2026-07-14T00:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write('{"type": "check", broken <<<< not json\n')
        ciw.record_check("dawn-run", "failure", 2, "2026-07-14T01:00:00Z", path=self.path)
        entries = ciw._entries(path=self.path)
        with self.assertRaises(ciw.CIWatchTamperedError):
            ciw.current_streak(entries, "dawn-run", "failure")
        with self.assertRaises(ciw.CIWatchTamperedError):
            ciw.last_check(entries, "dawn-run")
        with self.assertRaises(ciw.CIWatchTamperedError):
            ciw.format_status_line(entries, "dawn-run")

    def test_entries_marks_a_non_dict_json_value_as_malformed_too(self):
        # task 312: a line that parses cleanly to a non-dict JSON value (a
        # bare number, null, list, or string -- e.g. a hand-tampered or
        # truncated write that still happens to be syntactically valid)
        # must not be treated as a real logged entry, the same gap tasks
        # 309-311 closed in change_gate.py/child_work_check.py/arcade_app_watch.py.
        ciw.record_check("dawn-run", "success", 1, "2026-07-14T00:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("5\n")
        entries = ciw._entries(path=self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])

    def test_workflow_entries_raises_tampered_error_on_a_non_dict_json_line(self):
        # pre-fix this crashed with an uncaught AttributeError
        # ('int' object has no attribute 'get') instead of the named error.
        ciw.record_check("dawn-run", "success", 1, "2026-07-14T00:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("5\n")
        entries = ciw._entries(path=self.path)
        with self.assertRaises(ciw.CIWatchTamperedError):
            ciw.current_streak(entries, "dawn-run", "success")


class TestTrackedWorkflows(unittest.TestCase):
    def test_dawn_run_and_pages_are_tracked(self):
        self.assertIn("dawn-run", ciw.TRACKED_WORKFLOWS)
        self.assertIn("pages", ciw.TRACKED_WORKFLOWS)

    def test_seam_scan_and_oracle_cadence_are_tracked(self):
        """Task 80: the two workflows that actually fail in production were
        never watched -- dawn-run/pages essentially never do. This is the
        identical gap task 72 closed for x_outage_tracker.py's
        TRACKED_TOOLS, applied here."""
        self.assertIn("seam-scan", ciw.TRACKED_WORKFLOWS)
        self.assertIn("oracle-cadence", ciw.TRACKED_WORKFLOWS)

    def test_status_cli_output_includes_all_four_workflows(self):
        import subprocess
        import sys

        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(path)
        try:
            ciw.record_check("seam-scan", "success", 1, "2026-07-15T13:39:54Z", path=path)
            ciw.record_check("oracle-cadence", "failure", 2, "2026-07-15T14:43:50Z", path=path)
            script = (
                "import sys; sys.path.insert(0, %r); import importlib.util as u; "
                "spec = u.spec_from_file_location('ci_watch', %r); m = u.module_from_spec(spec); "
                "spec.loader.exec_module(m); entries = m._entries(%r); "
                "[print(m.format_status_line(entries, w)) for w in m.TRACKED_WORKFLOWS]"
            ) % (ROOT, os.path.join(ROOT, "tools", "ci_watch.py"), path)
            out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
            self.assertIn("seam-scan:", out.stdout)
            self.assertIn("oracle-cadence:", out.stdout)
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
