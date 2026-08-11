"""Task 673 (widened task 678). Proves tools/tithe_check.py actually
bites on a synthetic hand-typed roll that fails to clear the licensed
0.03 floor, stays clean on real "cleared the floor" and "no number
stated" lines, ignores lines that never mention the Tithe at all, reads
both a bare number and a backtick-quoted one (BUILDLOG.md's and
ROADMAP.md's own differing prose styles), and -- the real point --
confirms the live, current BUILDLOG.md AND ROADMAP.md hold zero such
violations today.
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


tc = _load("tithe_check", os.path.join(ROOT, "tools", "tithe_check.py"))

# A path that never exists, so `find_violations(buildlog_path=...)` calls in
# FixtureViolationCase below exercise ONLY the fixture they build -- without
# this, `roadmap_path` would silently default to the real, live ROADMAP.md
# and every fixture assertion below would also be scanning real production
# text it never wrote and knows nothing about.
_NO_ROADMAP = os.path.join(tempfile.mkdtemp(), "missing-roadmap.md")


def _write_buildlog(content):
    fd, path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class FixtureViolationCase(unittest.TestCase):
    def setUp(self):
        self._paths = []
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        for p in self._paths:
            try:
                os.remove(p)
            except OSError:
                pass

    def _buildlog(self, content):
        path = _write_buildlog(content)
        self._paths.append(path)
        return path

    def test_roll_above_floor_is_flagged(self):
        path = self._buildlog(
            "2026-08-11 09:29 UTC | kwaku-ananse | 671 | dawn-run failed the Tithe (roll 0.0512), reran clean.\n"
        )
        violations = tc.find_violations(buildlog_path=path, roadmap_path=_NO_ROADMAP)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["offending_rolls"], [0.0512])
        self.assertEqual(violations[0]["line_number"], 1)
        formatted = tc.format_violations(violations)
        self.assertIn("CLAIM(S) FOUND", formatted)

    def test_roll_equal_to_floor_is_flagged(self):
        # test_the_tithe itself asserts roll >= 0.03 to PASS -- a claimed
        # "Tithe" roll of exactly 0.03 could not have failed the test,
        # so it is exactly as inconsistent as one above it.
        path = self._buildlog("some hour | god | 1 | Tithe (roll 0.03), incident opened.\n")
        violations = tc.find_violations(buildlog_path=path, roadmap_path=_NO_ROADMAP)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["offending_rolls"], [0.03])

    def test_roll_below_floor_is_not_flagged(self):
        path = self._buildlog("some hour | god | 1 | Tithe (roll 0.0208), replied on issue #6.\n")
        self.assertEqual(tc.find_violations(buildlog_path=path, roadmap_path=_NO_ROADMAP), [])

    def test_rolled_spelling_is_also_matched(self):
        path = self._buildlog("some hour | god | 1 | the Tithe took it: rolled 0.0512 against the floor.\n")
        violations = tc.find_violations(buildlog_path=path, roadmap_path=_NO_ROADMAP)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["offending_rolls"], [0.0512])

    def test_tithe_mention_with_no_number_is_not_flagged(self):
        path = self._buildlog(
            "some hour | god | 1 | dawn-run failed with a GitHub infra error, not the Tithe, GitHub-side.\n"
            "some hour | god | 2 | Tithe flake, unrelated file, reran clean 619/619.\n"
        )
        self.assertEqual(tc.find_violations(buildlog_path=path, roadmap_path=_NO_ROADMAP), [])

    def test_line_without_tithe_mention_is_ignored_even_with_a_number(self):
        path = self._buildlog("some hour | god | 1 | rolled the release out at 0.9999 coverage, unrelated.\n")
        self.assertEqual(tc.find_violations(buildlog_path=path, roadmap_path=_NO_ROADMAP), [])

    def test_missing_file_returns_no_violations(self):
        self.assertEqual(tc.find_violations(buildlog_path=os.path.join(tempfile.mkdtemp(), "missing.md"), roadmap_path=_NO_ROADMAP), [])

    def test_multiple_rolls_on_one_line_all_checked(self):
        path = self._buildlog(
            "some hour | god | 1 | Tithe roll 0.0208 first run, roll 0.0512 second run, both logged.\n"
        )
        violations = tc.find_violations(buildlog_path=path, roadmap_path=_NO_ROADMAP)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["offending_rolls"], [0.0512])

    def test_observed_rolls_returns_every_number_regardless_of_floor(self):
        path = self._buildlog(
            "some hour | god | 1 | Tithe (roll 0.0208), fine.\n"
            "some hour | god | 2 | Tithe (roll 0.0512), a violation.\n"
        )
        self.assertEqual(tc.observed_rolls(buildlog_path=path, roadmap_path=_NO_ROADMAP), [0.0208, 0.0512])

    def test_clean_format_names_the_sample_size(self):
        formatted = tc.format_violations([], sample_size=17)
        self.assertIn("clean", formatted)
        self.assertIn("17 roll(s) read", formatted)

    def test_backtick_quoted_roll_is_matched(self):
        # ROADMAP.md's own prose style backtick-quotes exact values more
        # often than BUILDLOG.md's bare-number style does.
        path = self._buildlog("some hour | god | 1 | the Tithe took it: rolled `0.0512` against the floor.\n")
        violations = tc.find_violations(buildlog_path=path, roadmap_path=_NO_ROADMAP)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["offending_rolls"], [0.0512])

    def test_word_between_verb_and_number_still_finds_no_claim(self):
        # ROADMAP.md task 676's own real line: "Tithe rolled below 0.03
        # once by chance" -- "below" sits between "rolled" and the
        # number, so this is correctly not a directly-adjacent claim.
        path = self._buildlog("some hour | god | 1 | Retrya's Tithe rolled below 0.03 once by chance mid-run.\n")
        self.assertEqual(tc.find_violations(buildlog_path=path, roadmap_path=_NO_ROADMAP), [])


class RoadmapFixtureCase(unittest.TestCase):
    """Mirrors FixtureViolationCase's own shape, pointed at roadmap_path
    instead of buildlog_path -- proves ROADMAP.md scanning is real, not
    just BUILDLOG.md's existing behavior coincidentally passing when a
    second unused parameter is added."""

    def setUp(self):
        self._paths = []
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        for p in self._paths:
            try:
                os.remove(p)
            except OSError:
                pass

    def _roadmap(self, content):
        path = _write_buildlog(content)
        self._paths.append(path)
        return path

    def test_roadmap_roll_above_floor_is_flagged(self):
        path = self._roadmap("| 678 | DONE | kwaku-ananse | the Tithe test rolled `0.0512` against the `0.03` floor.\n")
        violations = tc.find_violations(buildlog_path=_NO_ROADMAP, roadmap_path=path)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["source"], "ROADMAP.md")
        self.assertEqual(violations[0]["offending_rolls"], [0.0512])

    def test_roadmap_roll_below_floor_is_not_flagged(self):
        path = self._roadmap("| 671 | DONE | kwaku-ananse | rolled `0.014853192659314951` against the `0.03` floor.\n")
        self.assertEqual(tc.find_violations(buildlog_path=_NO_ROADMAP, roadmap_path=path), [])

    def test_violations_from_both_files_are_both_reported(self):
        buildlog = self._roadmap("some hour | god | 1 | Tithe (roll 0.0512), a violation.\n")
        roadmap = self._roadmap("| 1 | DONE | god | the Tithe rolled `0.09` against the `0.03` floor.\n")
        violations = tc.find_violations(buildlog_path=buildlog, roadmap_path=roadmap)
        self.assertEqual(len(violations), 2)
        self.assertEqual({v["source"] for v in violations}, {"BUILDLOG.md", "ROADMAP.md"})


class LiveRepoCase(unittest.TestCase):
    def test_real_buildlog_and_roadmap_hold_zero_violations_today(self):
        violations = tc.find_violations()
        self.assertEqual(
            violations, [],
            f"a hand-typed Tithe roll in the live BUILDLOG.md/ROADMAP.md does not clear the {tc.TITHE_FLOOR} floor it claims: {violations}",
        )

    def test_real_buildlog_has_actually_been_scanned(self):
        # Not a tautology: proves the live file exists, is readable, and
        # the regex actually matches real historical entries -- a
        # silently-empty scan (wrong path, regex typo) would also return
        # zero violations and pass the test above for the wrong reason.
        rolls = tc.observed_rolls(buildlog_path=tc.DEFAULT_BUILDLOG_PATH, roadmap_path=_NO_ROADMAP)
        self.assertGreater(len(rolls), 0, "expected at least one historical Tithe roll in the live BUILDLOG.md")
        for roll in rolls:
            self.assertLess(roll, tc.TITHE_FLOOR)

    def test_real_roadmap_has_actually_been_scanned(self):
        # Same "not a tautology" proof, isolated to ROADMAP.md alone --
        # confirms the widening in task 678 actually reads real rows,
        # not just an unused default that happens to stay empty.
        rolls = tc.observed_rolls(buildlog_path=_NO_ROADMAP, roadmap_path=tc.DEFAULT_ROADMAP_PATH)
        self.assertGreater(len(rolls), 0, "expected at least one historical Tithe roll in the live ROADMAP.md")
        for roll in rolls:
            self.assertLess(roll, tc.TITHE_FLOOR)


class CliCase(unittest.TestCase):
    def test_bad_argv_prints_docstring_and_exits_1(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "tithe_check.py")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stdout)

    def test_check_argv_against_live_repo_exits_0(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "tithe_check.py"), "check"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("tithe check: clean", result.stdout)


if __name__ == "__main__":
    unittest.main()
