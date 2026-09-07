"""Task 1305. Proves tools/roadmap_row_shape_check.py finds a ROADMAP.md row
that stops before its own closing pipe (the exact shape task 1304's own row
shipped in, missing a `done when` column entirely), stays clean when every
row reaches its own close, and pins the real live legacy-debt count so it
can shrink over time but never silently grow.
"""
import importlib.util
import os
import shutil
import subprocess
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


rrsc = _load("roadmap_row_shape_check", os.path.join(ROOT, "tools", "roadmap_row_shape_check.py"))

# The live, known legacy-debt count as of task 1306 (task 1305's own 35
# included twenty rows that were never actually missing content: their
# `done when` column existed all along, just split across blank-line
# paragraph breaks into several physical lines, so the shape check's
# line-at-a-time regex only ever saw the row's FIRST line -- which never
# itself ends in "|" -- and flagged the whole row as cut off. Task 1306
# reflowed those twenty (847, 965, 1043, 1044, 1045, 1047, 1077, 1098,
# 1099, 1108, 1211, 1281, 1282, 1283, 1284, 1285, 1286, 1290 in
# ROADMAP.md; 679, 687 in ROADMAP-ARCHIVE-004-482-797.md) into single
# physical lines -- a whitespace-only join verified byte-identical to the
# original once all runs of whitespace are collapsed, no prose invented
# or lost -- leaving 15 rows that are genuinely incomplete (no closing
# pipe anywhere in their own block, real content never written past that
# point). A future hour that honestly backfills one of those 15 (from
# THAT row's own commit message, per this checker's own docstring) should
# lower this ceiling in the same commit that closes it; a rise past it
# means a fresh row got cut off mid-write and nobody noticed.
KNOWN_LEGACY_INCOMPLETE_CEILING = 15


class FindIncompleteRowsCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.roadmap_path = os.path.join(self.tmp, "ROADMAP.md")

    def _write(self, content):
        with open(self.roadmap_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_a_complete_row_is_not_flagged(self):
        self._write("| 5 | DONE | off-by-one | do the thing | it is done |\n")
        incomplete = rrsc.find_incomplete_rows(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertEqual(incomplete, [])

    def test_a_row_missing_its_done_when_column_is_flagged(self):
        # The exact shape task 1304's own row shipped in: cut off after
        # the `task` column's prose, no `done when` column, no closing `|`.
        self._write("| 1304 | DONE | zashiki-warashi | some unfinished narrative that just stops\n")
        incomplete = rrsc.find_incomplete_rows(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(incomplete[0]["number"], 1304)
        self.assertEqual(incomplete[0]["status"], "DONE")
        self.assertIn("just stops", incomplete[0]["line_tail"])

    def test_a_row_with_a_literal_pipe_inside_prose_but_a_real_close_is_not_flagged(self):
        # Real rows in this repo's own history do contain literal `|`
        # characters inside their prose (an "or" between two states, a
        # code snippet) -- a naive pipe-COUNT check would false-positive
        # on those. Only the row's own trailing character decides.
        self._write("| 847 | DONE | ogun | a thing that reads TODO | WIP as one state | it is done |\n")
        incomplete = rrsc.find_incomplete_rows(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertEqual(incomplete, [])

    def test_also_reads_incomplete_rows_from_sibling_archive_files(self):
        self._write("| 200 | DONE | nisaba | recent, complete thing | it is done |\n")
        with open(os.path.join(self.tmp, "ROADMAP-ARCHIVE-001-1-169.md"), "w", encoding="utf-8") as f:
            f.write("| 100 | DONE | nyx | an old row cut short\n")
        incomplete = rrsc.find_incomplete_rows(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(incomplete[0]["number"], 100)
        self.assertEqual(incomplete[0]["file"], "ROADMAP-ARCHIVE-001-1-169.md")

    def test_a_file_not_matching_the_archive_naming_pattern_is_ignored(self):
        self._write("| 5 | DONE | off-by-one | complete thing | it is done |\n")
        with open(os.path.join(self.tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write("| 999 | DONE | nisaba | not a real roadmap row, no close\n")
        incomplete = rrsc.find_incomplete_rows(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertEqual(incomplete, [])


class CheckShapeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.roadmap_path = os.path.join(self.tmp, "ROADMAP.md")

    def _write(self, content):
        with open(self.roadmap_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_every_row_complete_is_clean(self):
        self._write(
            "| 5 | DONE | off-by-one | do the thing | it is done |\n"
            "| 6 | TODO | nisaba | do another | it is done |\n"
        )
        result = rrsc.check_shape(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["count"], 0)

    def test_an_incomplete_row_is_named_not_silently_passed(self):
        self._write(
            "| 5 | DONE | off-by-one | do the thing | it is done |\n"
            "| 6 | DONE | nisaba | cut off mid narrative\n"
        )
        result = rrsc.check_shape(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertFalse(result["clean"], result)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["incomplete"][0]["number"], 6)

    def test_results_are_sorted_by_task_number(self):
        self._write(
            "| 20 | DONE | nisaba | cut off first\n"
            "| 6 | DONE | nyx | cut off second\n"
        )
        result = rrsc.check_shape(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertEqual([r["number"] for r in result["incomplete"]], [6, 20])


class FormatResultCase(unittest.TestCase):
    def test_clean_reads_clean(self):
        line = rrsc.format_result({"clean": True, "incomplete": [], "count": 0})
        self.assertIn("clean", line)
        self.assertIn("closing pipe", line)

    def test_incomplete_is_named_but_framed_as_tracked_debt_not_alarm(self):
        result = {
            "clean": False,
            "count": 1,
            "incomplete": [{"number": 1304, "status": "DONE", "file": "ROADMAP.md", "line_tail": "...cut off"}],
        }
        line = rrsc.format_result(result)
        self.assertIn("1 incomplete row", line)
        self.assertIn("task 1304", line)
        self.assertIn("tracked debt", line)


class CliCase(unittest.TestCase):
    SCRIPT = os.path.join(ROOT, "tools", "roadmap_row_shape_check.py")

    def test_check_subcommand_runs_against_the_real_repo(self):
        result = subprocess.run(
            [sys.executable, self.SCRIPT, "check"],
            capture_output=True,
            text=True,
        )
        self.assertIn(result.returncode, (0, 1), result)
        self.assertIn("roadmap row shape:", result.stdout, result)

    def test_no_subcommand_prints_usage_and_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, self.SCRIPT],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1, result)


class RealLiveStateCase(unittest.TestCase):
    def test_real_live_incomplete_count_never_exceeds_the_known_ceiling(self):
        # Not "clean" -- thirty-five legacy rows genuinely predate this
        # checker and are tracked debt, not a live regression (see module
        # docstring). What must hold is that the count never GROWS: a new
        # incomplete row would mean a fresh session got cut off mid-write
        # with nobody noticing. A future hour that backfills one more (the
        # way task 1305 backfilled 1304, from that row's own real commit)
        # should lower KNOWN_LEGACY_INCOMPLETE_CEILING in the same commit.
        result = rrsc.check_shape()
        self.assertLessEqual(
            result["count"],
            KNOWN_LEGACY_INCOMPLETE_CEILING,
            f"incomplete row count grew past the known ceiling: {result['incomplete']}",
        )

    def test_task_1304_itself_is_no_longer_in_the_live_incomplete_list(self):
        # The one row this task actually backfilled -- proves the fix
        # landed, not just that the ceiling number was edited.
        result = rrsc.check_shape()
        numbers = {r["number"] for r in result["incomplete"]}
        self.assertNotIn(1304, numbers)

    def test_task_1306_reflowed_rows_are_no_longer_in_the_live_incomplete_list(self):
        # The twenty rows task 1306 proved were never actually missing
        # content (just split across blank-line paragraph breaks) --
        # proves the reflow landed for real, not just that the ceiling
        # number was edited down.
        result = rrsc.check_shape()
        numbers = {r["number"] for r in result["incomplete"]}
        reflowed = {
            847, 965, 1043, 1044, 1045, 1047, 1077, 1098, 1099, 1108,
            1211, 1281, 1282, 1283, 1284, 1285, 1286, 1290, 679, 687,
        }
        self.assertFalse(
            reflowed & numbers,
            f"reflowed row(s) still flagged incomplete: {reflowed & numbers}",
        )


if __name__ == "__main__":
    unittest.main()
