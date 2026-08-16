"""Task 782. Proves tools/one_action_check.py catches STRATEGY.md's own
"The One Action, Left to You" law breaking in a sealed
`fencepost/REPORTS/<date>.md` tablet -- either a report that doesn't carry
exactly one "Your move" line, or one whose move line reads as something
Fencepost itself already did or is about to do, rather than something the
reader does next. Mirrors `tests/test_report_regression_check.py`'s own
fixture/live-sweep shape for the identical `fencepost/REPORTS/` directory.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from types import ModuleType

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name: str, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


src = _load("one_action_check", os.path.join(ROOT, "tools", "one_action_check.py"))


def _write_report(dirpath: str, date: str, body: str) -> str:
    path = os.path.join(dirpath, f"{date}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


_GOOD_MOVE = "**Your move.** Post about it yourself — a single line linking it is enough."
_TWO_MOVES = _GOOD_MOVE + "\n\n" + _GOOD_MOVE
_NO_MOVE = "**The count.** 5 fenceposts named to date.\n"
_EXECUTED_MOVE = "**Your move.** Fencepost has posted about it already."
_EXECUTED_MOVE_I = "**Your move.** I posted about it for you."


class SealedReportDatesAndPathsCase(unittest.TestCase):
    def test_skips_non_dated_files(self):
        with tempfile.TemporaryDirectory() as d:
            _write_report(d, "2026-07-12", _GOOD_MOVE)
            with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
                f.write("not a dated tablet")
            pairs = src._sealed_report_dates_and_paths(d)
            self.assertEqual([date for date, _ in pairs], ["2026-07-12"])

    def test_sorted_chronologically(self):
        with tempfile.TemporaryDirectory() as d:
            _write_report(d, "2026-07-20", _GOOD_MOVE)
            _write_report(d, "2026-07-12", _GOOD_MOVE)
            _write_report(d, "2026-07-15", _GOOD_MOVE)
            pairs = src._sealed_report_dates_and_paths(d)
            self.assertEqual([date for date, _ in pairs], ["2026-07-12", "2026-07-15", "2026-07-20"])


class MoveLinesCase(unittest.TestCase):
    def test_finds_a_single_move_line(self):
        self.assertEqual(len(src._move_lines(_GOOD_MOVE)), 1)

    def test_finds_no_move_line(self):
        self.assertEqual(src._move_lines(_NO_MOVE), [])

    def test_finds_two_move_lines(self):
        self.assertEqual(len(src._move_lines(_TWO_MOVES)), 2)

    def test_captures_the_trailing_text_not_the_marker(self):
        lines = src._move_lines(_GOOD_MOVE)
        self.assertTrue(lines[0].startswith("Post about it yourself"))
        self.assertNotIn("**Your move.**", lines[0])


class FirstPersonViolationCase(unittest.TestCase):
    def test_reader_verb_is_clean(self):
        self.assertIsNone(src._first_person_violation("Post about it yourself."))

    def test_fencepost_has_posted_is_flagged(self):
        self.assertEqual(src._first_person_violation("Fencepost has posted about it."), "fencepost has posted")

    def test_first_person_i_posted_is_flagged(self):
        self.assertEqual(src._first_person_violation("I posted about it for you."), "i posted")

    def test_first_person_we_ve_added_is_flagged(self):
        self.assertEqual(src._first_person_violation("We've added it to the README."), "we've added")

    def test_mentioning_fencepost_by_name_without_an_executed_verb_is_clean(self):
        # Every real rule's own trailing sentence names Fencepost by name
        # ("Fencepost only found the seam; it does not cross it") -- that
        # must never itself trip the checker; only an executed-action verb
        # paired with its own subject should.
        line = "Post about it yourself. Fencepost only found the seam; it does not cross it."
        self.assertIsNone(src._first_person_violation(line))

    def test_case_insensitive(self):
        self.assertEqual(src._first_person_violation("FENCEPOST WILL post this for you."), "fencepost will")


class CheckOneActionInvariantCase(unittest.TestCase):
    def test_empty_directory_reads_clean(self):
        with tempfile.TemporaryDirectory() as d:
            result = src.check_one_action_invariant(d)
            self.assertTrue(result["clean"])
            self.assertEqual(result["checked"], 0)

    def test_every_report_with_exactly_one_reader_verb_move_reads_clean(self):
        with tempfile.TemporaryDirectory() as d:
            _write_report(d, "2026-07-12", _GOOD_MOVE)
            _write_report(d, "2026-07-13", _GOOD_MOVE)
            result = src.check_one_action_invariant(d)
            self.assertTrue(result["clean"], result["reason"])
            self.assertEqual(result["checked"], 2)

    def test_a_report_with_no_move_line_flips_dirty(self):
        with tempfile.TemporaryDirectory() as d:
            _write_report(d, "2026-07-12", _GOOD_MOVE)
            _write_report(d, "2026-07-13", _NO_MOVE)
            result = src.check_one_action_invariant(d)
            self.assertFalse(result["clean"])
            self.assertEqual(len(result["wrong_count"]), 1)
            self.assertEqual(result["wrong_count"][0]["date"], "2026-07-13")
            self.assertEqual(result["wrong_count"][0]["count"], 0)

    def test_a_report_with_two_move_lines_flips_dirty(self):
        with tempfile.TemporaryDirectory() as d:
            _write_report(d, "2026-07-12", _TWO_MOVES)
            result = src.check_one_action_invariant(d)
            self.assertFalse(result["clean"])
            self.assertEqual(result["wrong_count"][0]["count"], 2)

    def test_a_report_whose_move_reads_as_fencepost_s_own_action_flips_dirty(self):
        with tempfile.TemporaryDirectory() as d:
            _write_report(d, "2026-07-12", _EXECUTED_MOVE)
            result = src.check_one_action_invariant(d)
            self.assertFalse(result["clean"])
            self.assertEqual(len(result["first_person"]), 1)
            self.assertEqual(result["first_person"][0]["date"], "2026-07-12")
            self.assertEqual(result["first_person"][0]["phrase"], "fencepost has posted")

    def test_a_report_whose_move_reads_as_the_first_person_flips_dirty(self):
        with tempfile.TemporaryDirectory() as d:
            _write_report(d, "2026-07-12", _EXECUTED_MOVE_I)
            result = src.check_one_action_invariant(d)
            self.assertFalse(result["clean"])
            self.assertEqual(result["first_person"][0]["phrase"], "i posted")

    def test_a_wrong_count_report_is_not_double_counted_as_first_person_too(self):
        """A report with zero or multiple move lines has no single line to
        check for first-person phrasing -- it's counted once, under
        wrong_count, never twice."""
        with tempfile.TemporaryDirectory() as d:
            _write_report(d, "2026-07-12", _NO_MOVE)
            result = src.check_one_action_invariant(d)
            self.assertEqual(len(result["wrong_count"]), 1)
            self.assertEqual(len(result["first_person"]), 0)

    def test_multiple_violations_all_reported(self):
        with tempfile.TemporaryDirectory() as d:
            _write_report(d, "2026-07-12", _NO_MOVE)
            _write_report(d, "2026-07-13", _EXECUTED_MOVE)
            _write_report(d, "2026-07-14", _GOOD_MOVE)
            result = src.check_one_action_invariant(d)
            self.assertFalse(result["clean"])
            self.assertEqual(result["checked"], 3)
            self.assertEqual(len(result["wrong_count"]), 1)
            self.assertEqual(len(result["first_person"]), 1)

    def test_non_dated_files_are_ignored_entirely(self):
        with tempfile.TemporaryDirectory() as d:
            _write_report(d, "2026-07-12", _GOOD_MOVE)
            with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
                f.write("Some prose that never carries a Your move line at all.")
            result = src.check_one_action_invariant(d)
            self.assertTrue(result["clean"])
            self.assertEqual(result["checked"], 1)


class FormatResultCase(unittest.TestCase):
    def test_clean_line_names_the_count(self):
        result = {"clean": True, "reason": "34 sealed report(s), each carries exactly one reader-phrased 'Your move' line"}
        line = src.format_result(result)
        self.assertIn("clean", line)
        self.assertIn("34 sealed report", line)

    def test_broken_line_names_broken(self):
        result = {"clean": False, "reason": "1 report with != 1 'Your move' line: 2026-07-13 (0)"}
        line = src.format_result(result)
        self.assertIn("BROKEN", line)
        self.assertIn("2026-07-13", line)


class LiveRealReportsSweepCase(unittest.TestCase):
    """The actual point: proves every real, already-sealed
    `fencepost/REPORTS/*.md` tablet in the live checkout holds the
    invariant this checker exists to enforce -- a future hour that ships
    a report violating it fails this exact assertion."""

    def test_real_sealed_reports_directory_is_clean(self):
        result = src.check_one_action_invariant()
        self.assertTrue(result["clean"], result["reason"])
        self.assertGreater(result["checked"], 20)

    def test_default_reports_dir_points_at_the_real_directory(self):
        self.assertTrue(src.DEFAULT_REPORTS_DIR.endswith(os.path.join("fencepost", "REPORTS")))
        self.assertTrue(os.path.isdir(src.DEFAULT_REPORTS_DIR))


class MainCliCase(unittest.TestCase):
    def test_no_args_prints_docstring_and_exits_1(self):
        import subprocess

        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "one_action_check.py")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Retrya audits", proc.stdout)

    def test_check_arg_exits_0_on_the_real_clean_directory(self):
        import subprocess

        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "one_action_check.py"), "check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("one action invariant: clean", proc.stdout)


if __name__ == "__main__":
    unittest.main()
