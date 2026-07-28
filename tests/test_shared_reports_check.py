"""Task 120. Proves tools/shared_reports_check.py counts real, validly-shaped
entries from records/shared-in-the-wild.jsonl -- the one STRATEGY.md
metrics-table row (kwaku-ananse's "Shared Fencepost Reports in the wild")
that had never once been instrumented -- without ever fabricating a share
that was never recorded. The real point: confirms the live, current
records/shared-in-the-wild.jsonl (which does not exist before this task)
honestly counts zero, and that zero is rendered as "not yet," not hidden.
"""
import importlib.util
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


src = _load("shared_reports_check", os.path.join(ROOT, "tools", "shared_reports_check.py"))


def _write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(row + "\n")


class FixtureSharedReportsCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "shared-in-the-wild.jsonl")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_three_real_entries_count_three(self):
        rows = [
            '{"date": "2026-07-15", "url": "https://x.com/example/status/1"}',
            '{"date": "2026-07-16", "url": "https://x.com/example/status/2"}',
            '{"date": "2026-07-17", "url": "https://example.com/screenshot.png"}',
        ]
        _write_jsonl(self.path, rows)
        result = src.compute_shared_reports(self.path)
        self.assertEqual(result["total_shared"], 3)
        self.assertEqual(result["most_recent_date"], "2026-07-17")
        self.assertEqual(result["remaining"], 47)

    def test_missing_url_is_skipped_not_counted(self):
        rows = ['{"date": "2026-07-15", "note": "no url field at all"}']
        _write_jsonl(self.path, rows)
        result = src.compute_shared_reports(self.path)
        self.assertEqual(result["total_shared"], 0)

    def test_blank_url_is_skipped_not_counted(self):
        rows = ['{"date": "2026-07-15", "url": "   "}']
        _write_jsonl(self.path, rows)
        result = src.compute_shared_reports(self.path)
        self.assertEqual(result["total_shared"], 0)

    def test_malformed_date_is_skipped_not_counted(self):
        rows = [
            '{"date": "not-a-date", "url": "https://example.com/1"}',
            '{"date": "2026-13-40", "url": "https://example.com/2"}',
            '{"url": "https://example.com/3"}',
        ]
        _write_jsonl(self.path, rows)
        result = src.compute_shared_reports(self.path)
        self.assertEqual(result["total_shared"], 0)

    def test_malformed_json_line_is_skipped_not_counted(self):
        _write_jsonl(self.path, ["not json at all", '{"date": "2026-07-15", "url": "https://example.com/1"}'])
        result = src.compute_shared_reports(self.path)
        self.assertEqual(result["total_shared"], 1)

    def test_valid_json_non_dict_line_is_skipped_not_crashed(self):
        # A line that parses cleanly to a non-dict JSON value (bare int,
        # list, string, bool, null) must not crash _read_entries() -- the
        # same valid-JSON-non-dict guard tasks 329-353 closed across every
        # oracle_engine/*_cadence.py sibling, applied here.
        _write_jsonl(
            self.path,
            [
                '{"date": "2026-07-15", "url": "https://example.com/1"}',
                "5",
                "null",
                "true",
                '"just a string"',
                "[1, 2, 3]",
            ],
        )
        result = src.compute_shared_reports(self.path)
        self.assertEqual(result["total_shared"], 1)

    def test_blank_lines_are_skipped(self):
        _write_jsonl(self.path, ['{"date": "2026-07-15", "url": "https://example.com/1"}', "", "  "])
        result = src.compute_shared_reports(self.path)
        self.assertEqual(result["total_shared"], 1)

    def test_no_file_is_empty_not_an_error(self):
        result = src.compute_shared_reports(os.path.join(self.tmp, "does-not-exist.jsonl"))
        self.assertEqual(result["total_shared"], 0)
        self.assertIsNone(result["most_recent_date"])
        self.assertEqual(result["remaining"], 50)

    def test_remaining_never_negative_past_target(self):
        rows = [f'{{"date": "2026-07-17", "url": "https://example.com/{i}"}}' for i in range(60)]
        _write_jsonl(self.path, rows)
        result = src.compute_shared_reports(self.path, target=50)
        self.assertEqual(result["total_shared"], 60)
        self.assertEqual(result["remaining"], 0)

    def test_format_zero_shared(self):
        result = src.compute_shared_reports(os.path.join(self.tmp, "does-not-exist.jsonl"))
        formatted = src.format_shared_reports(result)
        self.assertIn("0/50", formatted)
        self.assertIn("zero organic links/screenshots recorded yet", formatted)

    def test_most_recent_date_compares_calendar_order_not_string_order(self):
        # "2026-7-9" (unpadded July) is a REAL calendar date -- date(2026, 7, 9)
        # constructs fine, so _read_entries's own validation accepts it. But as
        # a plain string it sorts AFTER "2026-12-25" ('7' > '1' lexically),
        # even though December is chronologically later. most_recent_date must
        # reflect calendar order, the same discipline metrics_cadence_check.py
        # and report_cadence_check.py already hold (both sort real date()
        # objects, never raw strings).
        rows = [
            '{"date": "2026-7-9", "url": "https://example.com/a"}',
            '{"date": "2026-12-25", "url": "https://example.com/b"}',
        ]
        _write_jsonl(self.path, rows)
        result = src.compute_shared_reports(self.path)
        self.assertEqual(result["total_shared"], 2)
        self.assertEqual(result["most_recent_date"], "2026-12-25")

    def test_format_names_count_and_remaining(self):
        rows = ['{"date": "2026-07-17", "url": "https://example.com/1"}']
        _write_jsonl(self.path, rows)
        result = src.compute_shared_reports(self.path)
        formatted = src.format_shared_reports(result)
        self.assertIn("1/50", formatted)
        self.assertIn("49 to target", formatted)


class RealSharedReportsCase(unittest.TestCase):
    """The real point: the live checkout's actual
    records/shared-in-the-wild.jsonl, counted for real. This task creates
    the file's schema but deliberately does not manufacture a single entry
    -- the honest count today is zero, and this test locks that it reads
    as zero, not as an error and not as a guess."""

    def test_real_file_honestly_reads_zero_or_more_never_fabricated(self):
        result = src.compute_shared_reports(os.path.join(ROOT, "records", "shared-in-the-wild.jsonl"))
        self.assertEqual(result["total_shared"], 0)
        self.assertIsNone(result["most_recent_date"])
        self.assertEqual(result["target"], 50)


if __name__ == "__main__":
    unittest.main()
