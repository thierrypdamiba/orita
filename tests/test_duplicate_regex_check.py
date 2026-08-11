"""Task 397 (widened by tasks 418, 445, 684). Proves tools/duplicate_regex_
check.py actually bites on a synthetic hand-typed duplicate, stays clean
when a file imports a shared name instead of redefining it, and -- the
real point -- confirms the live, current orita checkout holds zero real
violations today. Task 418 also proves the checker's own `tools/*.py`
glob (added this task, having never scanned its own directory before) is
actually wired in, not just documented. Task 445 proves the same for
`oracle/oracle_engine/src/oracle_engine/*.py` -- the Oracle Desk's own
cadence/autograde engine, scanned for the first time this task.

`_ALLOWED_DUPLICATES` is empty as of task 684 -- both seeds that used to
live here (`_CLOSES_RE`, trimmed under ROADMAP.md #543; the `tools/
closing_keyword_guard.py`/`seam_engine/closing_keywords.py` mirror,
trimmed this task once closing_keyword_guard.py's own grammar widened
past it, see that module's docstring) stopped describing real duplicates.
`LiveRepoCase.test_seeded_exception_still_describes_a_real_duplicate`
below still guards the general mechanism generically -- it holds
regardless of whether the dict is currently empty or seeded.
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

    # ROADMAP.md #543 trimmed the `_CLOSES_RE` seed from `_ALLOWED_
    # DUPLICATES`: that pair no longer exists in the live tree (both
    # `issue-closed-pr-still-open` and `merged-pr-issue-still-open` now
    # import the shared `seam_engine.closing_keywords.CLOSING_KEYWORD_RE`
    # grammar instead of carrying their own narrower local copy). The two
    # tests that used to exercise the seeded-exception mechanism against
    # that pattern (`test_seeded_exception_pair_is_not_flagged`,
    # `test_exception_pair_widened_to_a_third_file_is_still_flagged`) were
    # removed rather than repointed at the one remaining seed at the time
    # (`tools/closing_keyword_guard.py`/`seam_engine/closing_keywords.py`).
    # Task 684 trimmed that second seed too (closing_keyword_guard.py's
    # own grammar widened past the mirror, see its module docstring) --
    # `_ALLOWED_DUPLICATES` is empty as of this task, and the two tests
    # that exercised IT (`test_seeded_closing_keyword_guard_mirror_is_not_
    # flagged`, `test_closing_keyword_guard_exception_widened_to_a_third_
    # file_is_still_flagged`) are removed the identical way, for the
    # identical reason: nothing left to seed against. The general
    # seeded-exception mechanism itself stays covered generically by
    # `LiveRepoCase.test_seeded_exception_still_describes_a_real_
    # duplicate` below and by `test_two_recipes_with_hand_typed_duplicate_
    # are_flagged` above (a synthetic pair, not relying on any real seed
    # existing) -- if a future task seeds a new real exception, it earns
    # its own from-scratch pair of tests the same way this one once did.

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

    def test_oracle_engine_glob_is_actually_scanned(self):
        # Task 445: _iter_scanned_files() never included oracle/oracle_
        # engine/src/oracle_engine/*.py -- the Oracle Desk's own 25-file
        # cadence/autograde engine, built in the identical "mirror this
        # sibling's regex verbatim" style this whole campaign polices
        # (BUILDLOG.md task 134) -- so a hand-typed duplicate there went
        # undetected. Reproduced live pre-fix: this exact fixture pair
        # returned zero violations before the glob existed. Proves the
        # fix is real (the glob is wired in), not just claimed in the
        # docstring.
        _write(
            os.path.join(self.orita, "oracle", "oracle_engine", "src", "oracle_engine", "fixture_a.py"),
            'import re\n_MENTION_RE = re.compile(r"@(\\w[\\w-]*)", re.IGNORECASE)\n',
        )
        _write(
            os.path.join(self.orita, "oracle", "oracle_engine", "src", "oracle_engine", "fixture_b.py"),
            '# mirrors fixture_a\'s own _MENTION_RE verbatim\n'
            'import re\n_MENTION_RE = re.compile(r"@(\\w[\\w-]*)", re.IGNORECASE)\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], r"@(\w[\w-]*)")
        files = {rel for rel, _lineno in violations[0]["locations"]}
        self.assertEqual(
            files,
            {
                os.path.join("oracle", "oracle_engine", "src", "oracle_engine", "fixture_a.py"),
                os.path.join("oracle", "oracle_engine", "src", "oracle_engine", "fixture_b.py"),
            },
        )

    def test_oracle_engine_file_importing_a_shared_name_is_not_flagged(self):
        # Mirrors test_tools_file_importing_a_shared_name_is_not_flagged,
        # for the oracle_engine glob specifically -- proves the widened
        # scan reads the real, live oracle_engine tree clean (no false
        # positive), not just that it finds a synthetic bug.
        _write(
            os.path.join(self.orita, "oracle", "oracle_engine", "src", "oracle_engine", "fixture_shared.py"),
            'import re\nSHARED_RE = re.compile(r"@(\\w[\\w-]*)", re.IGNORECASE)\n',
        )
        _write(
            os.path.join(self.orita, "oracle", "oracle_engine", "src", "oracle_engine", "fixture_consumer_a.py"),
            'from oracle_engine.fixture_shared import SHARED_RE\n',
        )
        _write(
            os.path.join(self.orita, "oracle", "oracle_engine", "src", "oracle_engine", "fixture_consumer_b.py"),
            'from oracle_engine.fixture_shared import SHARED_RE\n',
        )
        violations = drc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

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
