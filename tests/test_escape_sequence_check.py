"""Proves tools/escape_sequence_check.py actually catches a real invalid
escape sequence (the exact live shape found this hour in
tools/roadmap_archive.py:2 -- a bare `\\|` inside a non-raw docstring),
stays clean on valid escapes (`\\n`, `\\xHH`) and raw strings, skips
files that fail to parse for an unrelated reason, skips `.git`/
`__pycache__`/`node_modules`, and -- the real point -- confirms the
live, current repo holds zero real violations today.
"""
import importlib.util
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


esc = _load("escape_sequence_check", os.path.join(ROOT, "tools", "escape_sequence_check.py"))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _rm(path):
    shutil.rmtree(path, ignore_errors=True)


class FixtureViolationCase(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(_rm, self.repo)
        esc.clear_cache()

    def test_invalid_escape_sequence_is_flagged(self):
        # The exact live bug this task found: a bare `\|` inside a
        # non-raw docstring, describing a grep pattern in prose.
        _write(
            os.path.join(self.repo, "bad.py"),
            '"""an example grep pattern: \\|"""\n',
        )
        violations = esc.find_violations(orita_dir=self.repo)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["file"], "bad.py")
        self.assertEqual(violations[0]["line"], 1)
        self.assertIn("invalid escape sequence", violations[0]["message"])
        result = esc.check_escape_sequences(orita_dir=self.repo)
        self.assertFalse(result["clean"])
        self.assertEqual(result["count"], 1)
        formatted = esc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("bad.py:1", formatted)

    def test_valid_named_and_hex_escapes_are_not_flagged(self):
        # \n is a real recognized escape; \xb7 (task 19's own live
        # middle-dot rendering) is a real recognized hex escape. Neither
        # should ever be flagged -- only truly invalid sequences.
        _write(os.path.join(self.repo, "fine.py"), '"""line one\\nmid dot \\xb7 end"""\n')
        violations = esc.find_violations(orita_dir=self.repo)
        self.assertEqual(violations, [])

    def test_raw_string_with_backslash_pipe_is_not_flagged(self):
        _write(os.path.join(self.repo, "raw_ok.py"), 'PATTERN = r"a\\|b"\n')
        violations = esc.find_violations(orita_dir=self.repo)
        self.assertEqual(violations, [])

    def test_escaped_backslash_is_not_flagged(self):
        # The actual fix this task shipped for roadmap_archive.py: `\|`
        # (invalid) becomes `\\|` (a real escaped backslash, same
        # rendered text, no warning).
        _write(os.path.join(self.repo, "fixed.py"), '"""a real backslash-pipe: \\\\|"""\n')
        violations = esc.find_violations(orita_dir=self.repo)
        self.assertEqual(violations, [])

    def test_file_with_real_syntax_error_is_skipped_not_crashed(self):
        _write(os.path.join(self.repo, "broken_syntax.py"), "def f(:\n    pass\n")
        violations = esc.find_violations(orita_dir=self.repo)
        self.assertEqual(violations, [])

    def test_non_python_file_is_ignored(self):
        _write(os.path.join(self.repo, "notes.txt"), '"""bad \\| escape"""\n')
        violations = esc.find_violations(orita_dir=self.repo)
        self.assertEqual(violations, [])

    def test_git_pycache_and_node_modules_dirs_are_skipped(self):
        for skip_dir in (".git", "__pycache__", "node_modules"):
            _write(
                os.path.join(self.repo, skip_dir, "bad.py"),
                '"""bad \\| escape"""\n',
            )
        violations = esc.find_violations(orita_dir=self.repo)
        self.assertEqual(violations, [])

    def test_multiple_violations_across_files_all_counted(self):
        _write(os.path.join(self.repo, "a.py"), '"""bad \\| here"""\n')
        _write(os.path.join(self.repo, "b.py"), '"""also bad \\q here"""\n')
        result = esc.check_escape_sequences(orita_dir=self.repo)
        self.assertEqual(result["count"], 2)
        files = {v["file"] for v in result["violations"]}
        self.assertEqual(files, {"a.py", "b.py"})

    def test_clean_repo_reports_clean(self):
        _write(os.path.join(self.repo, "ok.py"), "x = 1\n")
        result = esc.check_escape_sequences(orita_dir=self.repo)
        self.assertTrue(result["clean"])
        self.assertEqual(result["count"], 0)
        self.assertIn("clean", esc.format_result(result))

    def test_clear_cache_forces_a_fresh_scan(self):
        _write(os.path.join(self.repo, "drift.py"), '"""bad \\| escape"""\n')
        first = esc.find_violations(orita_dir=self.repo)
        self.assertEqual(len(first), 1)
        _write(os.path.join(self.repo, "drift.py"), 'x = r"a\\|b"\n')
        cached = esc.find_violations(orita_dir=self.repo)
        self.assertEqual(len(cached), 1, "uncleared cache should still read stale")
        esc.clear_cache()
        fresh = esc.find_violations(orita_dir=self.repo)
        self.assertEqual(fresh, [])


class LiveTreeCase(unittest.TestCase):
    def test_the_real_live_repo_holds_zero_invalid_escape_sequences(self):
        esc.clear_cache()
        violations = esc.find_violations()
        self.assertEqual(violations, [], esc.format_result({"clean": False, "count": len(violations), "violations": violations}))


if __name__ == "__main__":
    unittest.main()
