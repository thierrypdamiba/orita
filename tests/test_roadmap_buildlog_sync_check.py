"""Task 1018. Proves tools/roadmap_buildlog_sync_check.py finds a real
BUILDLOG.md task number missing from ROADMAP.md's own table (the exact
shape task 1017 found and backfilled for rows 1015/1016), stays clean
when every number is present -- whether live or in an archive -- and
confirms the real, live town state is currently clean.
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


rbsc = _load("roadmap_buildlog_sync_check", os.path.join(ROOT, "tools", "roadmap_buildlog_sync_check.py"))


class RoadmapTaskNumbersCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.roadmap_path = os.path.join(self.tmp, "ROADMAP.md")

    def _write_roadmap(self, content):
        with open(self.roadmap_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_reads_numbers_from_the_live_file(self):
        self._write_roadmap(
            "| 5 | DONE | off-by-one | do the thing | it is done |\n"
            "| 6 | TODO | nisaba | do another | it is done |\n"
        )
        nums = rbsc.roadmap_task_numbers(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertEqual(nums, {5, 6})

    def test_also_reads_numbers_from_sibling_archive_files(self):
        self._write_roadmap("| 200 | DONE | nisaba | recent thing | it is done |\n")
        with open(os.path.join(self.tmp, "ROADMAP-ARCHIVE-001-1-169.md"), "w", encoding="utf-8") as f:
            f.write("| 1 | DONE | nyx | old thing | it is done |\n")
        nums = rbsc.roadmap_task_numbers(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertEqual(nums, {1, 200})

    def test_a_file_not_matching_the_archive_naming_pattern_is_ignored(self):
        self._write_roadmap("| 5 | DONE | off-by-one | do the thing | it is done |\n")
        with open(os.path.join(self.tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write("| 999 | DONE | nisaba | not a real roadmap row |\n")
        nums = rbsc.roadmap_task_numbers(roadmap_path=self.roadmap_path, archive_dir=self.tmp)
        self.assertEqual(nums, {5})


class BuildlogTaskNumbersCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.buildlog_path = os.path.join(self.tmp, "BUILDLOG.md")

    def _write(self, content):
        with open(self.buildlog_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_reads_a_plain_numbered_row(self):
        self._write("2026-08-25 01:29 UTC | nyx | 995 | did a thing\n")
        nums = rbsc.buildlog_task_numbers(self.buildlog_path)
        self.assertIn(995, nums)
        self.assertIn("did a thing", nums[995])

    def test_a_multi_task_cell_yields_both_numbers(self):
        self._write("2026-07-29 10:00 UTC | retrya | 360/361 | closed two at once\n")
        nums = rbsc.buildlog_task_numbers(self.buildlog_path)
        self.assertEqual(set(nums), {360, 361})

    def test_a_housekeeping_marker_row_yields_no_task_numbers(self):
        self._write("2026-08-25 18:3x UTC | ogun | daily | 18:00 UTC daily-aggregate bookkeeping\n")
        nums = rbsc.buildlog_task_numbers(self.buildlog_path)
        self.assertEqual(nums, {})

    def test_the_first_line_a_number_appears_on_wins(self):
        self._write(
            "2026-08-25 22:2x UTC | kwaku-ananse | 1016 | WIP opened\n"
            "2026-08-25 22:5x UTC | kwaku-ananse | 1016 | DONE\n"
        )
        nums = rbsc.buildlog_task_numbers(self.buildlog_path)
        self.assertIn("WIP opened", nums[1016])


class CheckSyncCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.roadmap_path = os.path.join(self.tmp, "ROADMAP.md")
        self.buildlog_path = os.path.join(self.tmp, "BUILDLOG.md")

    def _write(self, path, content):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_every_buildlog_task_present_in_roadmap_is_clean(self):
        self._write(self.roadmap_path, "| 5 | DONE | off-by-one | do the thing | it is done |\n")
        self._write(self.buildlog_path, "2026-08-25 01:29 UTC | off-by-one | 5 | did the thing\n")
        result = rbsc.check_sync(
            roadmap_path=self.roadmap_path, buildlog_path=self.buildlog_path, archive_dir=self.tmp
        )
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["missing"], [])

    def test_a_buildlog_task_missing_from_roadmap_is_named_not_silently_passed(self):
        # The exact shape task 1017 found for real: rows 1015/1016 shipped
        # and were logged to BUILDLOG.md, but never got a matching row
        # written into ROADMAP.md's own task table.
        self._write(self.roadmap_path, "| 1014 | DONE | nisaba | prior thing | it is done |\n")
        self._write(
            self.buildlog_path,
            "2026-08-25 20:3x UTC | nisaba | 1014 | prior thing shipped\n"
            "2026-08-25 21:2x UTC | kothar-wa-khasis | 1015 | a thing shipped with no roadmap row\n",
        )
        result = rbsc.check_sync(
            roadmap_path=self.roadmap_path, buildlog_path=self.buildlog_path, archive_dir=self.tmp
        )
        self.assertFalse(result["clean"], result)
        self.assertEqual(len(result["missing"]), 1)
        self.assertEqual(result["missing"][0]["number"], 1015)
        self.assertIn("a thing shipped with no roadmap row", result["missing"][0]["buildlog_line"])

    def test_a_number_only_present_in_an_archive_file_is_not_missing(self):
        self._write(self.roadmap_path, "| 200 | DONE | nisaba | recent thing | it is done |\n")
        self._write(
            os.path.join(self.tmp, "ROADMAP-ARCHIVE-001-1-169.md"),
            "| 1 | DONE | nyx | old thing | it is done |\n",
        )
        self._write(self.buildlog_path, "2026-07-01 01:29 UTC | nyx | 1 | old thing shipped\n")
        result = rbsc.check_sync(
            roadmap_path=self.roadmap_path, buildlog_path=self.buildlog_path, archive_dir=self.tmp
        )
        self.assertTrue(result["clean"], result)

    def test_no_buildlog_file_at_all_is_clean(self):
        self._write(self.roadmap_path, "| 5 | DONE | off-by-one | do the thing | it is done |\n")
        result = rbsc.check_sync(
            roadmap_path=self.roadmap_path,
            buildlog_path=os.path.join(self.tmp, "does-not-exist.md"),
            archive_dir=self.tmp,
        )
        self.assertTrue(result["clean"], result)


class FormatResultCase(unittest.TestCase):
    def test_clean_reads_clean_with_counts(self):
        line = rbsc.format_result(
            {"clean": True, "missing": [], "roadmap_task_count": 10, "buildlog_task_count": 12}
        )
        self.assertIn("clean (12 BUILDLOG.md task(s)", line)

    def test_missing_is_named_and_escalated(self):
        result = {
            "clean": False,
            "missing": [{"number": 1015, "buildlog_line": "2026-08-25 21:2x UTC | kothar-wa-khasis | 1015 | x"}],
            "roadmap_task_count": 10,
            "buildlog_task_count": 12,
        }
        line = rbsc.format_result(result)
        self.assertIn("1 MISSING", line)
        self.assertIn("task 1015", line)
        self.assertIn("escalate now", line)


class CliCase(unittest.TestCase):
    SCRIPT = os.path.join(ROOT, "tools", "roadmap_buildlog_sync_check.py")

    def test_check_subcommand_runs_against_the_real_repo(self):
        result = subprocess.run(
            [sys.executable, self.SCRIPT, "check"],
            capture_output=True,
            text=True,
        )
        self.assertIn(result.returncode, (0, 1), result)
        self.assertIn("roadmap/buildlog sync:", result.stdout, result)

    def test_no_subcommand_prints_usage_and_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, self.SCRIPT],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1, result)


class RealLiveStateCase(unittest.TestCase):
    def test_real_live_roadmap_and_buildlog_currently_agree(self):
        result = rbsc.check_sync()
        self.assertTrue(result["clean"], result)


if __name__ == "__main__":
    unittest.main()
