"""Task 459. Proves tools/metrics_field_completeness_check.py flags a
records/metrics.jsonl field that no tools/*_check.py file references as a
quoted string literal, stays clean when every field is guarded, never
counts a docstring-only/backtick mention as a real reference, excludes
its own file from the search (so it can never satisfy itself), treats
`date`/`notes` as structural (never candidates), and -- the real point --
confirms the live, current repo's real records/metrics.jsonl has zero
unguarded fields today.
"""
import importlib.util
import json
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


mfc = _load(
    "metrics_field_completeness_check",
    os.path.join(ROOT, "tools", "metrics_field_completeness_check.py"),
)


def _write_metrics(tmpdir, rows):
    path = os.path.join(tmpdir, "metrics.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return path


def _write_check_file(tmpdir, name, src):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    return path


class MetricsFieldExtractionCase(unittest.TestCase):
    def test_collects_every_field_across_multiple_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_metrics(
                tmpdir,
                [
                    {"date": "2026-08-01", "widgets_shipped": 3},
                    {"date": "2026-08-02", "widgets_shipped": 4, "gizmos_shipped": 1},
                ],
            )
            fields = mfc._metrics_fields(path)
            self.assertEqual(fields, {"widgets_shipped", "gizmos_shipped"})

    def test_date_and_notes_are_structural_never_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_metrics(tmpdir, [{"date": "2026-08-01", "notes": "some narration"}])
            fields = mfc._metrics_fields(path)
            self.assertEqual(fields, set())

    def test_malformed_line_is_skipped_not_raised(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "metrics.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"date": "2026-08-01", "widgets_shipped": 3}) + "\n")
                f.write("{not valid json at all\n")
            fields = mfc._metrics_fields(path)
            self.assertEqual(fields, {"widgets_shipped"})

    def test_missing_file_returns_empty_set_not_error(self):
        fields = mfc._metrics_fields("/tmp/does-not-exist-metrics-459.jsonl")
        self.assertEqual(fields, set())


class GuardDetectionCase(unittest.TestCase):
    def test_flags_field_no_checker_references(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = _write_metrics(tmpdir, [{"date": "2026-08-01", "widgets_shipped": 3}])
            tools_dir = os.path.join(tmpdir, "tools")
            os.makedirs(tools_dir)
            result = mfc.check_metrics_field_completeness(metrics_path=metrics_path, tools_dir=tools_dir)
            self.assertFalse(result["clean"])
            self.assertEqual(result["unguarded"], ["widgets_shipped"])

    def test_clean_when_field_referenced_as_quoted_literal_in_a_checker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = _write_metrics(tmpdir, [{"date": "2026-08-01", "widgets_shipped": 3}])
            tools_dir = os.path.join(tmpdir, "tools")
            os.makedirs(tools_dir)
            _write_check_file(
                tools_dir,
                "widgets_check.py",
                'def check(last):\n    return "widgets_shipped" in last\n',
            )
            result = mfc.check_metrics_field_completeness(metrics_path=metrics_path, tools_dir=tools_dir)
            self.assertTrue(result["clean"])
            self.assertEqual(result["unguarded"], [])
            self.assertEqual(result["guarded"], ["widgets_shipped"])

    def test_single_quoted_literal_counts_too(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = _write_metrics(tmpdir, [{"date": "2026-08-01", "widgets_shipped": 3}])
            tools_dir = os.path.join(tmpdir, "tools")
            os.makedirs(tools_dir)
            _write_check_file(tools_dir, "widgets_check.py", "FIELD = 'widgets_shipped'\n")
            result = mfc.check_metrics_field_completeness(metrics_path=metrics_path, tools_dir=tools_dir)
            self.assertTrue(result["clean"])

    def test_backtick_docstring_mention_does_not_count_as_a_guard(self):
        """A field named only in prose, in backticks, is not a real
        cross-check -- the same 'structural, not narrative' distinction
        scopes_completeness_check.py already draws."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = _write_metrics(tmpdir, [{"date": "2026-08-01", "widgets_shipped": 3}])
            tools_dir = os.path.join(tmpdir, "tools")
            os.makedirs(tools_dir)
            _write_check_file(
                tools_dir,
                "widgets_check.py",
                '"""This module has nothing to do with `widgets_shipped` yet."""\n',
            )
            result = mfc.check_metrics_field_completeness(metrics_path=metrics_path, tools_dir=tools_dir)
            self.assertFalse(result["clean"])
            self.assertEqual(result["unguarded"], ["widgets_shipped"])

    def test_only_check_dot_py_files_are_scanned_not_arbitrary_tools_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = _write_metrics(tmpdir, [{"date": "2026-08-01", "widgets_shipped": 3}])
            tools_dir = os.path.join(tmpdir, "tools")
            os.makedirs(tools_dir)
            _write_check_file(tools_dir, "widgets_helper.py", 'FIELD = "widgets_shipped"\n')
            result = mfc.check_metrics_field_completeness(metrics_path=metrics_path, tools_dir=tools_dir)
            self.assertFalse(result["clean"])

    def test_no_metrics_file_at_all_reads_clean_nothing_to_guard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = os.path.join(tmpdir, "tools")
            os.makedirs(tools_dir)
            result = mfc.check_metrics_field_completeness(
                metrics_path=os.path.join(tmpdir, "nope.jsonl"), tools_dir=tools_dir
            )
            self.assertTrue(result["clean"])
            self.assertEqual(result["fields"], [])


class SelfExclusionCase(unittest.TestCase):
    def test_this_modules_own_quoted_literals_do_not_count_as_a_guard(self):
        """`"unguarded"` appears as a quoted literal inside this very
        module's own source (its result dict's key) and nowhere else in
        tools/*_check.py -- proving this module excludes itself from the
        scan, or a field named `unguarded` would incorrectly read as
        guarded by its own presence in its own output shape."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = _write_metrics(tmpdir, [{"date": "2026-08-01", "unguarded": 1}])
            result = mfc.check_metrics_field_completeness(
                metrics_path=metrics_path, tools_dir=mfc.DEFAULT_TOOLS_DIR
            )
            self.assertFalse(result["clean"])
            self.assertIn("unguarded", result["unguarded"])


class RealRepoCase(unittest.TestCase):
    """The real point: today's real records/metrics.jsonl has zero
    fields no tools/*_check.py file guards, and hand-writing a
    synthetic unguarded field into a temp copy flips the check from
    clean to broken and names it."""

    def test_real_metrics_jsonl_has_no_unguarded_fields_today(self):
        result = mfc.check_metrics_field_completeness()
        self.assertTrue(result["clean"], msg=f"unguarded: {result['unguarded']}")
        self.assertGreater(len(result["fields"]), 0)

    def test_appending_a_synthetic_unguarded_field_flips_clean_to_broken(self):
        with open(mfc.DEFAULT_METRICS_PATH, encoding="utf-8") as f:
            real_lines = f.read()
        with tempfile.TemporaryDirectory() as tmpdir:
            broken_path = os.path.join(tmpdir, "metrics.jsonl")
            with open(broken_path, "w", encoding="utf-8") as f:
                f.write(real_lines)
                f.write(json.dumps({"date": "2099-01-01", "brand_new_never_guarded_field": 1}) + "\n")
            result = mfc.check_metrics_field_completeness(
                metrics_path=broken_path, tools_dir=mfc.DEFAULT_TOOLS_DIR
            )
            self.assertFalse(result["clean"])
            self.assertIn("brand_new_never_guarded_field", result["unguarded"])


class FormatResultCase(unittest.TestCase):
    def test_clean_message_names_the_field_count(self):
        result = {"clean": True, "fields": ["a", "b"], "guarded": ["a", "b"], "unguarded": []}
        msg = mfc.format_result(result)
        self.assertIn("clean", msg)
        self.assertIn("2 field(s)", msg)

    def test_broken_message_names_each_unguarded_field(self):
        result = {"clean": False, "fields": ["a"], "guarded": [], "unguarded": ["a"]}
        msg = mfc.format_result(result)
        self.assertIn("UNGUARDED FIELD", msg)
        self.assertIn("'a'", msg)


if __name__ == "__main__":
    unittest.main()
