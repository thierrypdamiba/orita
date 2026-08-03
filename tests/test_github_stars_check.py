"""Task 420. Proves tools/github_stars_check.py cross-checks
records/metrics.jsonl's last github_stars reading against the last
recorded live star count in HAND/github-stars-log.jsonl -- and confirms
the real, live town state: metrics.jsonl's most recent reading (0, dated
2026-07-30) DOES match a real live Github_CountStargazers read taken
this hour (also 0).
"""
import importlib.util
import json
import os
import shutil
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


gsc = _load("github_stars_check", os.path.join(ROOT, "tools", "github_stars_check.py"))


def _write_metrics(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


class _TempLogCase(unittest.TestCase):
    def setUp(self):
        fd, self.log_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.log_path)  # record_check/_append must create it fresh
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")

    def tearDown(self):
        if os.path.exists(self.log_path):
            os.remove(self.log_path)


class RecordCheckCase(_TempLogCase):
    def test_records_a_line(self):
        gsc.record_check(3, "2026-07-31T00:00:00Z", path=self.log_path)
        with open(self.log_path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_rejects_a_negative_count(self):
        with self.assertRaises(ValueError):
            gsc.record_check(-1, "2026-07-31T00:00:00Z", path=self.log_path)
        self.assertFalse(os.path.exists(self.log_path))

    def test_rejects_a_bool_as_count(self):
        # bool is a subclass of int in Python -- True/False must never
        # silently pass as a star count.
        with self.assertRaises(ValueError):
            gsc.record_check(True, "2026-07-31T00:00:00Z", path=self.log_path)

    def test_never_edits_a_prior_line(self):
        gsc.record_check(1, "2026-07-30T10:00:00Z", path=self.log_path)
        with open(self.log_path) as f:
            before = f.readlines()
        gsc.record_check(2, "2026-07-31T00:00:00Z", path=self.log_path)
        with open(self.log_path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)

    def test_return_value_is_a_bool_not_none(self):
        wrote = gsc.record_check(1, "2026-07-30T10:00:00Z", path=self.log_path)
        self.assertIs(wrote, True)


class RecordCheckDedupCase(_TempLogCase):
    """Task 502: this was the one `record_*` sibling (tools/ci_watch.py,
    tools/scribe_growth_check.py, tools/word_watch.py,
    tools/square_check.py, tools/arcade_app_watch.py,
    tools/gateway_toolset_check.py) the tasks 487/497/498/501 dedup
    campaign never reached -- `record_check` recorded unconditionally on
    every call, so a repeat same-hour `ritual_check.py` run (task 487's
    own named ordinary case) with an unchanged live star count would have
    grown `HAND/github-stars-log.jsonl` with a byte-identical line, same
    shape as the six siblings already fixed. Live production log carried
    zero duplicates at the time this was found (2026-07-31/08-01) --
    fixed anyway, as the identical latent bug, rather than waiting for a
    real duplicate to appear."""

    def test_no_prior_check_always_writes(self):
        wrote = gsc.record_check(3, "2026-07-31T00:00:00Z", path=self.log_path)
        self.assertTrue(wrote)
        with open(self.log_path) as f:
            self.assertEqual(len(f.readlines()), 1)

    def test_unchanged_count_is_skipped(self):
        gsc.record_check(3, "2026-07-31T00:00:00Z", path=self.log_path)
        wrote = gsc.record_check(3, "2026-07-31T00:05:00Z", path=self.log_path)
        self.assertFalse(wrote)
        with open(self.log_path) as f:
            self.assertEqual(len(f.readlines()), 1)

    def test_changed_count_still_writes(self):
        gsc.record_check(3, "2026-07-31T00:00:00Z", path=self.log_path)
        wrote = gsc.record_check(4, "2026-07-31T00:05:00Z", path=self.log_path)
        self.assertTrue(wrote)
        with open(self.log_path) as f:
            self.assertEqual(len(f.readlines()), 2)

    def test_a_real_change_after_a_would_be_duplicate_still_writes(self):
        gsc.record_check(3, "2026-07-31T00:00:00Z", path=self.log_path)
        skipped = gsc.record_check(3, "2026-07-31T00:05:00Z", path=self.log_path)
        wrote = gsc.record_check(5, "2026-07-31T00:10:00Z", path=self.log_path)
        self.assertFalse(skipped)
        self.assertTrue(wrote)
        with open(self.log_path) as f:
            self.assertEqual(len(f.readlines()), 2)

    def test_a_malformed_line_elsewhere_does_not_block_a_real_write(self):
        gsc.record_check(3, "2026-07-31T00:00:00Z", path=self.log_path)
        with open(self.log_path, "a") as f:
            f.write("not even json {{{\n")
        # last_check() would raise on this corrupted tip -- recording must
        # still be able to repair the log by appending a fresh valid line,
        # never propagate the tamper error onto the write path.
        wrote = gsc.record_check(3, "2026-07-31T00:05:00Z", path=self.log_path)
        self.assertTrue(wrote)
        with open(self.log_path) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(json.loads(lines[-1])["count"], 3)


class LastCheckCase(_TempLogCase):
    def test_no_log_returns_none(self):
        self.assertIsNone(gsc.last_check(self.log_path))

    def test_returns_the_most_recent_entry(self):
        gsc.record_check(1, "2026-07-30T10:00:00Z", path=self.log_path)
        gsc.record_check(2, "2026-07-31T00:00:00Z", path=self.log_path)
        self.assertEqual(gsc.last_check(self.log_path)["count"], 2)

    def test_malformed_tail_line_raises(self):
        with open(self.log_path, "w") as f:
            f.write("not even json {{{\n")
        with self.assertRaises(gsc.GitHubStarsTamperedError):
            gsc.last_check(self.log_path)


class CrossCheckCase(_TempLogCase):
    def test_no_metrics_and_no_log_is_clean(self):
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed"])
        self.assertIsNone(result["real"])

    def test_metrics_reading_but_no_live_check_is_clean(self):
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "github_stars": 1}])
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed"], 1)
        self.assertIsNone(result["real"])

    def test_live_check_but_no_metrics_reading_is_clean(self):
        gsc.record_check(5, "2026-07-31T00:00:00Z", path=self.log_path)
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed"])
        self.assertEqual(result["real"], 5)

    def test_agreeing_reading_is_clean(self):
        _write_metrics(self.metrics_path, [{"date": "2026-07-30", "github_stars": 0}])
        gsc.record_check(0, "2026-07-31T00:03:00Z", path=self.log_path)
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed"], 0)
        self.assertEqual(result["real"], 0)
        self.assertIn("clean", gsc.format_result(result))

    def test_disagreeing_reading_flips_clean_false_and_names_both(self):
        _write_metrics(self.metrics_path, [{"date": "2026-07-29", "github_stars": 1}])
        gsc.record_check(0, "2026-07-31T00:03:00Z", path=self.log_path)
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertFalse(result["clean"])
        self.assertEqual(result["claimed"], 1)
        self.assertEqual(result["real"], 0)
        formatted = gsc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("claims 1", formatted)
        self.assertIn("is 0", formatted)

    def test_only_the_most_recent_metrics_reading_is_checked(self):
        _write_metrics(
            self.metrics_path,
            [
                {"date": "2026-07-28", "github_stars": 99},  # would mismatch if checked
                {"date": "2026-07-30", "github_stars": 0},
            ],
        )
        gsc.record_check(0, "2026-07-31T00:03:00Z", path=self.log_path)
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-30")

    def test_only_the_most_recent_live_check_is_used(self):
        _write_metrics(self.metrics_path, [{"date": "2026-07-30", "github_stars": 0}])
        gsc.record_check(9, "2026-07-30T12:00:00Z", path=self.log_path)
        gsc.record_check(0, "2026-07-31T00:03:00Z", path=self.log_path)
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 0)


class OmittedFieldOnExistingReadingCase(_TempLogCase):
    """Task 456: the same bug shape task 453/454/455 found and fixed in
    gap_true_positive_check.py/toolkits_in_use_check.py/report_shipped_
    check.py -- a reading that EXISTS and carries a `date` but omits
    `github_stars` itself used to collapse into the identical
    unconditional-clean branch as "no reading at all", even when the
    last live count already carries a real, nonzero star count. Proves
    both the honest-omission (no live check, or a live check reading
    honestly 0) and the broken-omission (a real nonzero live count
    exists and went unrecorded) shapes."""

    def test_omitted_field_with_no_live_check_is_honestly_clean(self):
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "connected_users_oauth": 5}])
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["real"])
        self.assertIsNone(result["claimed"])
        self.assertEqual(result["claimed_date"], "2026-07-20")
        formatted = gsc.format_result(result)
        self.assertIn("clean", formatted)
        self.assertIn("no live check recorded yet", formatted)

    def test_omitted_field_with_a_real_zero_live_check_is_honestly_clean(self):
        gsc.record_check(0, "2026-07-20T00:03:00Z", path=self.log_path)
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "connected_users_oauth": 5}])
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 0)
        self.assertIsNone(result["claimed"])
        formatted = gsc.format_result(result)
        self.assertIn("clean", formatted)
        self.assertIn("nothing omitted", formatted)

    def test_omitted_field_with_a_real_nonzero_live_check_is_broken(self):
        gsc.record_check(7, "2026-07-20T00:03:00Z", path=self.log_path)
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "connected_users_oauth": 5}])
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 7)
        self.assertIsNone(result["claimed"])
        self.assertEqual(result["claimed_date"], "2026-07-20")
        formatted = gsc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("already 7", formatted)

    def test_reading_with_no_date_at_all_stays_clean_unconditionally(self):
        """The genuinely-nothing-to-contradict shape (no reading at all)
        must not be affected by this fix -- only a dated reading that
        omits the field changes behavior."""
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed_date"])


class MalformedLastLineCase(_TempLogCase):
    """Mirrors tasks_shipped_check.py's/report_shipped_check.py's own
    guard: a truncated/malformed trailing line in metrics.jsonl must be
    skipped, not fatal."""

    def test_malformed_last_line_does_not_raise(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-30", "github_stars": 0}) + "\n")
            f.write('{"date": "2026-07-31", "github_stars"\n')  # truncated, invalid JSON
        entry = gsc._last_metrics_entry(self.metrics_path)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["date"], "2026-07-30")

    def test_trailing_non_dict_json_does_not_raise(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-30", "github_stars": 0}) + "\n")
            f.write("true\n")
        result = gsc.check_github_stars(self.metrics_path, self.log_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-30")

    def test_every_line_malformed_returns_none(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write("not json\n")
            f.write("{also not json\n")
        self.assertIsNone(gsc._last_metrics_entry(self.metrics_path))


class RealLiveStateCase(unittest.TestCase):
    """The real point of this task: records/metrics.jsonl's own
    github_stars field claims 0 for 2026-07-30, and a real, live
    Github_CountStargazers read taken this hour (2026-07-31) also reads
    0 -- proven live rather than assumed. This test records that real
    live read into a scratch copy of the log (never the real
    HAND/github-stars-log.jsonl -- a test process must never write the
    production log) and checks it against the real, live metrics.jsonl."""

    def setUp(self):
        fd, self.log_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.log_path)
        self.addCleanup(lambda: os.path.exists(self.log_path) and os.remove(self.log_path))

    def test_the_real_live_star_count_now_agrees_with_metrics_jsonl(self):
        gsc.record_check(0, "2026-07-31T00:03:00Z", path=self.log_path)
        result = gsc.check_github_stars(gsc.DEFAULT_METRICS_PATH, self.log_path)
        self.assertEqual(result["claimed"], 0)
        self.assertEqual(result["real"], 0)
        self.assertTrue(result["clean"])


if __name__ == "__main__":
    unittest.main()
