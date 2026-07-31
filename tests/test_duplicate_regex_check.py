"""Task 397 (widened by task 418). Proves tools/duplicate_regex_check.py
actually bites on a synthetic hand-typed duplicate, stays clean when a
file imports a shared name instead of redefining it, does not flag either
seeded/documented exception (`_CLOSES_RE`, and task 418's `tools/closing_
keyword_guard.py`/`seam_engine/closing_keywords.py` mirror), and -- the
real point -- confirms the live, current orita checkout holds zero real
violations today. Task 418 also proves the checker's own `tools/*.py`
glob (added this task, having never scanned its own directory before) is
actually wired in, not just documented.
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


drc = _load("duplicate_regex_check", os.path.join(ROOT, "tools", "duplicate_regex_check.py"))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _rm(path):
    shutil.rmtree(path, ignore_errors=True)


class FixtureViolationCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_two_recipes_with_hand_typed_duplicate_are_flagged(self):
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-a", "detector.py"),
            'import re\n'
            '_MENTION_RE = re.compile(r"@(\\w[\\w-]*)", re.IGNORECASE)\n',
        )
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-b", "detector.py"),
            'import re\n'
            '# mirrors recipe-a\'s own _MENTION_RE verbatim\n'
            '_MENTION_RE = re.compile(r"@(\\w[\\w-]*)", re.IGNORECASE)\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], r"@(\w[\w-]*)")
        files = {rel for rel, _lineno in violations[0]["locations"]}
        self.assertEqual(
            files,
            {
                os.path.join("fencepost", "RECIPES", "recipe-a", "detector.py"),
                os.path.join("fencepost", "RECIPES", "recipe-b", "detector.py"),
            },
        )
        formatted = drc.format_violations(violations)
        self.assertIn("DUPLICATE PATTERN(S) FOUND", formatted)

    def test_import_instead_of_redefinition_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "fencepost", "seam_engine", "src", "seam_engine", "shared.py"),
            'import re\n'
            'MENTION_RE = re.compile(r"@(\\w[\\w-]*)", re.IGNORECASE)\n',
        )
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-a", "detector.py"),
            'from seam_engine.shared import MENTION_RE\n',
        )
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-b", "detector.py"),
            'from seam_engine.shared import MENTION_RE\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_different_patterns_under_the_same_name_are_not_flagged(self):
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-a", "detector.py"),
            'import re\n'
            '_RE = re.compile(r"foo")\n',
        )
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-b", "detector.py"),
            'import re\n'
            '_RE = re.compile(r"bar")\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_seeded_exception_pair_is_not_flagged(self):
        pattern = r"\b(?:closes?|fix(?:es)?|resolves?)\s+#(\d+)\b"
        allowed = drc._ALLOWED_DUPLICATES[pattern]
        for rel in allowed:
            _write(os.path.join(self.orita, rel), f'import re\n_CLOSES_RE = re.compile(r"{pattern}", re.IGNORECASE)\n')
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_exception_pair_widened_to_a_third_file_is_still_flagged(self):
        # Task 397: the exception is seeded to an EXACT file set. A third
        # file independently defining the same "allowed" pattern is a new
        # fact the town never actually decided to allow -- must still bite.
        pattern = r"\b(?:closes?|fix(?:es)?|resolves?)\s+#(\d+)\b"
        allowed = drc._ALLOWED_DUPLICATES[pattern]
        for rel in allowed:
            _write(os.path.join(self.orita, rel), f'import re\n_CLOSES_RE = re.compile(r"{pattern}", re.IGNORECASE)\n')
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-c", "detector.py"),
            f'import re\n_CLOSES_RE = re.compile(r"{pattern}", re.IGNORECASE)\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], pattern)

    def test_non_literal_pattern_is_ignored(self):
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-a", "detector.py"),
            'import re\n'
            'suffix = "x"\n'
            '_RE = re.compile("@" + suffix)\n',
        )
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-b", "detector.py"),
            'import re\n'
            'suffix = "x"\n'
            '_RE = re.compile("@" + suffix)\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_init_files_are_skipped(self):
        _write(
            os.path.join(self.orita, "fencepost", "seam_engine", "src", "seam_engine", "__init__.py"),
            'import re\n_RE = re.compile(r"@(\\w+)")\n',
        )
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-a", "detector.py"),
            'import re\n_RE = re.compile(r"@(\\w+)")\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_tools_glob_is_actually_scanned(self):
        # Task 418: _iter_scanned_files() hard-coded exactly two globs and
        # never scanned tools/*.py -- the directory this checker itself
        # lives in -- so a hand-typed duplicate there went undetected.
        # Proves the fix is real (the glob is wired in), not just claimed
        # in the docstring: two tools/*.py files with no import between
        # them, sharing a hand-typed pattern, must be flagged.
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_a.py"),
            'import re\n_MENTION_RE = re.compile(r"@(\\w[\\w-]*)", re.IGNORECASE)\n',
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_b.py"),
            '# mirrors fixture_tool_a\'s own _MENTION_RE verbatim\n'
            'import re\n_MENTION_RE = re.compile(r"@(\\w[\\w-]*)", re.IGNORECASE)\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], r"@(\w[\w-]*)")
        files = {rel for rel, _lineno in violations[0]["locations"]}
        self.assertEqual(
            files,
            {
                os.path.join("tools", "fixture_tool_a.py"),
                os.path.join("tools", "fixture_tool_b.py"),
            },
        )

    def test_tools_file_importing_a_shared_name_is_not_flagged(self):
        # Mirrors test_import_instead_of_redefinition_is_not_flagged, but
        # for the tools/*.py glob specifically -- proves the fix's other
        # half (tools/text_patterns.py, task 418) reads clean under the
        # newly-widened scan, not just that the scan finds a synthetic bug.
        _write(
            os.path.join(self.orita, "tools", "fixture_shared.py"),
            'import re\nSHARED_RE = re.compile(r"@(\\w[\\w-]*)", re.IGNORECASE)\n',
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_consumer_a.py"),
            'import os, sys\n'
            'sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n'
            'import fixture_shared\n'
            '_RE = fixture_shared.SHARED_RE\n',
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_consumer_b.py"),
            'import os, sys\n'
            'sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n'
            'import fixture_shared\n'
            '_RE = fixture_shared.SHARED_RE\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_seeded_closing_keyword_guard_mirror_is_not_flagged(self):
        # The second seeded exception (task 418): tools/closing_keyword_
        # guard.py and seam_engine/closing_keywords.py define the
        # identical grammar on purpose -- seam_engine's own docstring
        # rules it must NOT import the parent repo's tools/ directory, to
        # stay portable/forkable. This pair only became visible once the
        # tools/*.py glob existed at all.
        pattern = r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#(\d+)\b"
        allowed = drc._ALLOWED_DUPLICATES[pattern]
        self.assertEqual(
            allowed,
            {
                os.path.join("tools", "closing_keyword_guard.py"),
                os.path.join("fencepost", "seam_engine", "src", "seam_engine", "closing_keywords.py"),
            },
        )
        for rel in allowed:
            _write(os.path.join(self.orita, rel), f'import re\nCLOSING_KEYWORD_RE = re.compile(r"{pattern}", re.IGNORECASE)\n')
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_closing_keyword_guard_exception_widened_to_a_third_file_is_still_flagged(self):
        pattern = r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#(\d+)\b"
        allowed = drc._ALLOWED_DUPLICATES[pattern]
        for rel in allowed:
            _write(os.path.join(self.orita, rel), f'import re\nCLOSING_KEYWORD_RE = re.compile(r"{pattern}", re.IGNORECASE)\n')
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_c.py"),
            f'import re\nCLOSING_KEYWORD_RE = re.compile(r"{pattern}", re.IGNORECASE)\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], pattern)


class LiveRepoCase(unittest.TestCase):
    """The real point of task 397: run the scan against the actual,
    current checkout and confirm the only remaining duplicate-text pair
    in the live tree is the one the town already decided, in writing, to
    keep -- not a sixth unfound instance of the bug tasks 389/390/393/
    394/396 kept finding by hand."""

    def test_real_checkout_holds_zero_unseeded_violations_today(self):
        violations = drc.find_violations()
        self.assertEqual(
            violations, [],
            f"real duplicate regex violation(s) found: {drc.format_violations(violations)}",
        )

    def test_seeded_exception_still_describes_a_real_duplicate(self):
        # Guards against the exception list going stale in the other
        # direction: if the pair it names ever stops being a real
        # duplicate (one side gets extracted into a shared import), the
        # seed itself should be trimmed, not left as dead allowlist.
        drc.clear_cache()
        cleared = dict(drc._ALLOWED_DUPLICATES)
        drc._ALLOWED_DUPLICATES.clear()
        drc.clear_cache()
        try:
            violations = drc.find_violations()
        finally:
            drc._ALLOWED_DUPLICATES.clear()
            drc._ALLOWED_DUPLICATES.update(cleared)
            drc.clear_cache()
        patterns_found = {v["pattern"] for v in violations}
        for pattern in cleared:
            self.assertIn(
                pattern, patterns_found,
                f"seeded exception {pattern!r} no longer describes a real duplicate in the live tree -- trim it",
            )

    def test_repeated_call_is_memoized(self):
        import time
        drc.clear_cache()
        start = time.time()
        first = drc.find_violations()
        first_elapsed = time.time() - start

        start = time.time()
        second = drc.find_violations()
        second_elapsed = time.time() - start

        self.assertEqual(first, second)
        self.assertLess(
            second_elapsed, max(first_elapsed / 10, 0.05),
            f"second call ({second_elapsed:.3f}s) was not meaningfully "
            f"cheaper than the first ({first_elapsed:.3f}s).",
        )
        drc.clear_cache()


if __name__ == "__main__":
    unittest.main()
