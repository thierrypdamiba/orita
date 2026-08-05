"""Task 416. Proves tools/tasks_shipped_check.py cross-checks
records/metrics.jsonl's last tasks_shipped_today reading against real,
live BUILDLOG.md ground truth -- and confirms the real, live town state:
metrics.jsonl's most recent reading (17, dated 2026-07-30) DOES match the
real ground truth (distinct numbered tasks logged before that day's own
daily-aggregate row, task 414).
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


tsc = _load("tasks_shipped_check", os.path.join(ROOT, "tools", "tasks_shipped_check.py"))


def _write_metrics(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _write_buildlog(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Build Log\n\n")
        f.write("*Append-only. One line per shipped task: "
                 "`YYYY-MM-DD HH:MM UTC | <god> | <task#> | <one line>`.*\n\n")
        for line in lines:
            f.write(line + "\n")


class NoMetricsReadingCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.buildlog_path = os.path.join(self.tmp, "BUILDLOG.md")

    def test_missing_metrics_file_is_clean_nothing_to_contradict(self):
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed"])
        self.assertIsNone(result["real"])

    def test_reading_missing_the_field_entirely_is_clean(self):
        _write_metrics(self.metrics_path, [{"date": "2026-07-12"}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed"])


class NoAggregateRowCase(unittest.TestCase):
    """A reading exists but that date's own BUILDLOG.md carries no literal
    "daily aggregate" row (the shape task 117/275's own catch-up hours
    left behind) -- nothing to honestly cross-check, not a guessed
    cutoff."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.buildlog_path = os.path.join(self.tmp, "BUILDLOG.md")

    def test_no_aggregate_row_for_the_date_is_clean_with_no_real_value(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-12 09:00 UTC | ogun | 1 | shipped something ordinary",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "tasks_shipped_today": 21}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["real"])
        self.assertEqual(result["claimed"], 21)


class AgreementCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.buildlog_path = os.path.join(self.tmp, "BUILDLOG.md")

    def test_claimed_count_matching_tasks_before_the_aggregate_row_is_clean(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-12 09:00 UTC | ogun | 1 | shipped something ordinary",
            "2026-07-12 10:00 UTC | ogun | ritual | routine hourly check, nothing shipped",
            "2026-07-12 11:00 UTC | nisaba | 2 | shipped another thing",
            "2026-07-12 18:00 UTC | nisaba | 3 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "tasks_shipped_today": 2}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 2)
        self.assertEqual(result["claimed"], 2)

    def test_aggregate_task_itself_is_never_counted(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-12 09:00 UTC | ogun | 1 | shipped something ordinary",
            "2026-07-12 18:00 UTC | nisaba | 2 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "tasks_shipped_today": 1}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 1)

    def test_tasks_after_the_aggregate_row_the_same_day_are_not_counted(self):
        # Precedent: task 415 shipped the same day as task 414's own
        # daily-aggregate reading and correctly is not part of its "17".
        _write_buildlog(self.buildlog_path, [
            "2026-07-12 09:00 UTC | ogun | 1 | shipped something ordinary",
            "2026-07-12 18:00 UTC | nisaba | 2 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
            "2026-07-12 19:00 UTC | off-by-one | 3 | shipped after the aggregate, same day",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "tasks_shipped_today": 1}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 1)

    def test_multi_task_cell_counts_each_number_once(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-12 09:00 UTC | ogun/off-by-one | 10/11 | closed a leftover WIP then shipped the next",
            "2026-07-12 18:00 UTC | nisaba | 12 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "tasks_shipped_today": 2}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 2)

    def test_non_numeric_task_cells_are_excluded_from_the_count(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-12 09:00 UTC | ogun | 1 | shipped something ordinary",
            "2026-07-12 10:00 UTC | ogun | ritual | routine hourly check, nothing shipped",
            "2026-07-12 11:00 UTC | ogun | roadmap | scan only, no idle branch",
            "2026-07-12 18:00 UTC | nisaba | 2 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "tasks_shipped_today": 1}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 1)


class MismatchCase(unittest.TestCase):
    """The mutation-based proof: a synthetic BUILDLOG.md whose real
    distinct-task count before the aggregate row disagrees with the
    claimed metrics.jsonl reading is flagged, named exactly."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.buildlog_path = os.path.join(self.tmp, "BUILDLOG.md")

    def test_overclaim_flips_broken_and_names_both(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-12 09:00 UTC | ogun | 1 | shipped something ordinary",
            "2026-07-12 18:00 UTC | nisaba | 2 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "tasks_shipped_today": 5}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 1)
        self.assertEqual(result["claimed"], 5)
        formatted = tsc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("claims 5", formatted)
        self.assertIn("is 1", formatted)

    def test_underclaim_flips_broken(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-12 09:00 UTC | ogun | 1 | shipped something ordinary",
            "2026-07-12 10:00 UTC | ogun | 2 | shipped another",
            "2026-07-12 18:00 UTC | nisaba | 3 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "tasks_shipped_today": 1}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 2)
        self.assertEqual(result["claimed"], 1)

    def test_only_the_most_recent_reading_is_checked_not_every_historical_one(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-11 09:00 UTC | ogun | 1 | shipped something ordinary",
            "2026-07-11 18:00 UTC | nisaba | 2 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
            "2026-07-12 09:00 UTC | ogun | 3 | shipped something ordinary",
            "2026-07-12 18:00 UTC | nisaba | 4 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
        ])
        _write_metrics(
            self.metrics_path,
            [
                {"date": "2026-07-11", "tasks_shipped_today": 99},  # would mismatch if checked
                {"date": "2026-07-12", "tasks_shipped_today": 1},
            ],
        )
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-12")


class MalformedLastLineCase(unittest.TestCase):
    """Mirrors report_shipped_check.py's own guard (task 415, itself
    following tasks 306/328/412/413): a truncated/malformed trailing line
    in metrics.jsonl must be skipped, not fatal."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.buildlog_path = os.path.join(self.tmp, "BUILDLOG.md")
        _write_buildlog(self.buildlog_path, [
            "2026-07-20 09:00 UTC | ogun | 1 | shipped something ordinary",
            "2026-07-20 18:00 UTC | nisaba | 2 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
        ])

    def test_malformed_last_line_does_not_raise(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "tasks_shipped_today": 1}) + "\n")
            f.write('{"date": "2026-07-21", "tasks_shipped_today"\n')  # truncated, invalid JSON
        entry = tsc._last_metrics_entry(self.metrics_path)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["date"], "2026-07-20")

    def test_malformed_last_line_falls_through_check(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "tasks_shipped_today": 1}) + "\n")
            f.write("not even json at all {{{\n")
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-20")

    def test_every_line_malformed_returns_none(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write("not json\n")
            f.write("{also not json\n")
        self.assertIsNone(tsc._last_metrics_entry(self.metrics_path))

    def test_trailing_non_dict_json_does_not_raise(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "tasks_shipped_today": 1}) + "\n")
            f.write("true\n")
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-20")


class OmittedFieldOnExistingReadingCase(unittest.TestCase):
    """Task 458: the identical bug shape tasks 453-457 already fixed on
    five sibling metrics.jsonl checkers -- a reading that EXISTS (has a
    `date`) but omits `tasks_shipped_today` used to collapse into the same
    unconditional-clean branch as "no reading has ever existed at all",
    even when real, live ground truth (BUILDLOG.md's own dated rows before
    that date's aggregate row) already names a nonzero count the reading
    failed to carry. Proves the honest-omission shape (real is 0, nothing
    yet to have missed), the broken-omission shape (real is nonzero, a
    real count went unrecorded), and that the omission stays clean when
    no aggregate row exists for that date at all (nothing to honestly
    cross-check, same as every other shape in this file)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.buildlog_path = os.path.join(self.tmp, "BUILDLOG.md")

    def test_omitted_field_against_zero_real_is_honestly_clean(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-20 18:00 UTC | nisaba | 1 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "reports_shipped_today": 1}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 0)
        self.assertIsNone(result["claimed"])
        self.assertEqual(result["claimed_date"], "2026-07-20")
        formatted = tsc.format_result(result)
        self.assertIn("clean", formatted)
        self.assertIn("nothing omitted", formatted)

    def test_omitted_field_against_a_real_nonzero_count_is_broken(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-20 09:00 UTC | ogun | 1 | shipped something ordinary",
            "2026-07-20 10:00 UTC | ogun | 2 | shipped another thing",
            "2026-07-20 18:00 UTC | nisaba | 3 | 18:00 UTC daily aggregate: metrics.jsonl reading recorded",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "reports_shipped_today": 1}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 2)
        self.assertIsNone(result["claimed"])
        formatted = tsc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("not recorded", formatted)

    def test_omitted_field_with_no_aggregate_row_stays_clean(self):
        _write_buildlog(self.buildlog_path, [
            "2026-07-20 09:00 UTC | ogun | 1 | shipped something ordinary",
        ])
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "reports_shipped_today": 1}])
        result = tsc.check_tasks_shipped(self.metrics_path, self.buildlog_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["real"])
        self.assertIsNone(result["claimed"])


class RealLiveStateCase(unittest.TestCase):
    """The real point of this task: records/metrics.jsonl's own
    tasks_shipped_today field claims 16 for 2026-08-05 (task 556's own
    daily-aggregate reading, tasks 540-555), and ground truth (BUILDLOG.md's
    own distinct numbered rows dated 2026-08-05 before task 556's aggregate
    row) also reads 16 -- proven live rather than assumed, and stable even
    as later same-day tasks keep appending further rows."""

    def test_the_real_live_buildlog_now_agrees_with_ground_truth(self):
        result = tsc.check_tasks_shipped()
        self.assertEqual(result["claimed"], result["real"])
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-08-05")
        self.assertEqual(result["claimed"], 16)


if __name__ == "__main__":
    unittest.main()
