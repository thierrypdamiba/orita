"""Task 415. Proves tools/report_shipped_check.py cross-checks
records/metrics.jsonl's last reports_shipped_today reading against real,
live fencepost/REPORTS/ filesystem ground truth -- and confirms the
real, live town state: metrics.jsonl's most recent reading (1) DOES
match the real ground truth, since fencepost/REPORTS/2026-07-30.md
actually exists on disk.
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


rsc = _load("report_shipped_check", os.path.join(ROOT, "tools", "report_shipped_check.py"))


def _write_metrics(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


class NoMetricsReadingCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.reports_dir = os.path.join(self.tmp, "REPORTS")
        os.mkdir(self.reports_dir)

    def test_missing_metrics_file_is_clean_nothing_to_contradict(self):
        result = rsc.check_report_shipped(self.metrics_path, self.reports_dir)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed"])
        self.assertIsNone(result["real"])

    def test_reading_missing_the_field_entirely_is_clean(self):
        _write_metrics(self.metrics_path, [{"date": "2026-07-12"}])
        result = rsc.check_report_shipped(self.metrics_path, self.reports_dir)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed"])


class AgreementCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.reports_dir = os.path.join(self.tmp, "REPORTS")
        os.mkdir(self.reports_dir)

    def test_claimed_1_with_a_real_file_present_is_clean(self):
        with open(os.path.join(self.reports_dir, "2026-07-12.md"), "w", encoding="utf-8") as f:
            f.write("# report\n")
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "reports_shipped_today": 1}])
        result = rsc.check_report_shipped(self.metrics_path, self.reports_dir)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 1)
        self.assertEqual(result["claimed"], 1)

    def test_claimed_0_with_no_real_file_is_clean(self):
        # An honest zero-state -- the dogfood ritual genuinely didn't ship
        # that day (e.g. a real seam-scan.yml failure), named plainly,
        # not a mismatch.
        _write_metrics(self.metrics_path, [{"date": "2026-07-14", "reports_shipped_today": 0}])
        result = rsc.check_report_shipped(self.metrics_path, self.reports_dir)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 0)
        self.assertEqual(result["claimed"], 0)


class MismatchCase(unittest.TestCase):
    """The mutation-based proof: a synthetic metrics.jsonl claiming a
    report shipped that day when no such file exists on disk (or vice
    versa) is flagged, named exactly."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.reports_dir = os.path.join(self.tmp, "REPORTS")
        os.mkdir(self.reports_dir)

    def test_claimed_1_but_no_real_file_flips_broken_and_names_both(self):
        # seam-scan.yml is claimed to have shipped that day's tablet
        # (e.g. yesterday's "1" hand-copied forward) but no file landed.
        _write_metrics(self.metrics_path, [{"date": "2026-07-14", "reports_shipped_today": 1}])
        result = rsc.check_report_shipped(self.metrics_path, self.reports_dir)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 0)
        self.assertEqual(result["claimed"], 1)
        self.assertEqual(result["claimed_date"], "2026-07-14")
        formatted = rsc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("claims 1", formatted)
        self.assertIn("is 0", formatted)

    def test_claimed_0_but_a_real_file_exists_flips_broken(self):
        # The inverse mistake: the file actually landed but the hand-typed
        # reading under-claims it.
        with open(os.path.join(self.reports_dir, "2026-07-16.md"), "w", encoding="utf-8") as f:
            f.write("# report\n")
        _write_metrics(self.metrics_path, [{"date": "2026-07-16", "reports_shipped_today": 0}])
        result = rsc.check_report_shipped(self.metrics_path, self.reports_dir)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 1)
        self.assertEqual(result["claimed"], 0)

    def test_only_the_most_recent_reading_is_checked_not_every_historical_one(self):
        with open(os.path.join(self.reports_dir, "2026-07-12.md"), "w", encoding="utf-8") as f:
            f.write("# report\n")
        _write_metrics(
            self.metrics_path,
            [
                {"date": "2026-07-11", "reports_shipped_today": 1},  # would mismatch if checked
                {"date": "2026-07-12", "reports_shipped_today": 1},
            ],
        )
        result = rsc.check_report_shipped(self.metrics_path, self.reports_dir)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-12")


class MalformedLastLineCase(unittest.TestCase):
    """Mirrors gap_true_positive_check.py's own guard (task 413, itself
    following tasks 306/328/412): a truncated/malformed trailing line in
    metrics.jsonl must be skipped, not fatal."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.reports_dir = os.path.join(self.tmp, "REPORTS")
        os.mkdir(self.reports_dir)

    def test_malformed_last_line_does_not_raise(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "reports_shipped_today": 1}) + "\n")
            f.write('{"date": "2026-07-21", "reports_shipped_today"\n')  # truncated, invalid JSON
        entry = rsc._last_metrics_entry(self.metrics_path)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["date"], "2026-07-20")

    def test_malformed_last_line_falls_through_check(self):
        with open(os.path.join(self.reports_dir, "2026-07-20.md"), "w", encoding="utf-8") as f:
            f.write("# report\n")
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "reports_shipped_today": 1}) + "\n")
            f.write("not even json at all {{{\n")
        result = rsc.check_report_shipped(self.metrics_path, self.reports_dir)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-20")

    def test_every_line_malformed_returns_none(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write("not json\n")
            f.write("{also not json\n")
        self.assertIsNone(rsc._last_metrics_entry(self.metrics_path))

    def test_trailing_non_dict_json_does_not_raise(self):
        with open(os.path.join(self.reports_dir, "2026-07-20.md"), "w", encoding="utf-8") as f:
            f.write("# report\n")
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "reports_shipped_today": 1}) + "\n")
            f.write("true\n")
        result = rsc.check_report_shipped(self.metrics_path, self.reports_dir)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-20")


class RealLiveStateCase(unittest.TestCase):
    """The real point of this task: records/metrics.jsonl's own
    reports_shipped_today field claims 1 for 2026-07-30, and ground truth
    (fencepost/REPORTS/2026-07-30.md's own existence) also reads 1 -- the
    real, live state this hour agrees, proven live rather than assumed."""

    def test_the_real_live_metrics_file_now_agrees_with_ground_truth(self):
        result = rsc.check_report_shipped()
        self.assertEqual(result["claimed"], result["real"])
        self.assertTrue(result["clean"])


if __name__ == "__main__":
    unittest.main()
