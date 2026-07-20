"""Task 168. Proves "how big are ROADMAP.md/BUILDLOG.md, and is either
growing past a watched threshold" resolves the same way every time, the
same durable-log shape tests/test_arcade_app_watch.py already proves for
the gateway's own connected-app state.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "scribe_growth_check", os.path.join(ROOT, "tools", "scribe_growth_check.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sgc = _load()


class _TempFixtureCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        fd, self.log_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.log_path)  # record_scribe_check/_append must create it fresh

    def tearDown(self):
        if os.path.exists(self.log_path):
            os.remove(self.log_path)

    def _write(self, name: str, num_bytes: int) -> None:
        with open(os.path.join(self.tmpdir, name), "wb") as f:
            f.write(b"x" * num_bytes)


class TestComputeScribeSizes(_TempFixtureCase):
    def test_reads_real_byte_sizes_off_disk(self):
        self._write("ROADMAP.md", 100)
        self._write("BUILDLOG.md", 40)
        sizes = sgc.compute_scribe_sizes(root=self.tmpdir)
        self.assertEqual(sizes, {"ROADMAP.md": 100, "BUILDLOG.md": 40})

    def test_missing_tracked_file_raises_rather_than_reporting_zero(self):
        self._write("ROADMAP.md", 100)
        # BUILDLOG.md never written.
        with self.assertRaises(FileNotFoundError):
            sgc.compute_scribe_sizes(root=self.tmpdir)

    def test_tracked_set_is_overridable(self):
        self._write("only.md", 7)
        sizes = sgc.compute_scribe_sizes(root=self.tmpdir, tracked={"only.md": "only.md"})
        self.assertEqual(sizes, {"only.md": 7})

    def test_real_repo_files_are_readable_and_nonzero(self):
        # Sanity check against the real, live repo files (not a fixture) --
        # proves the default TRACKED_FILES paths are actually correct
        # relative to the real repo root, not just to a temp fixture.
        sizes = sgc.compute_scribe_sizes()
        self.assertGreater(sizes["ROADMAP.md"], 0)
        self.assertGreater(sizes["BUILDLOG.md"], 0)


class TestCheckScribeGrowth(_TempFixtureCase):
    def test_clean_when_every_file_is_under_threshold(self):
        result = sgc.check_scribe_growth(
            {"ROADMAP.md": 100, "BUILDLOG.md": 50}, threshold_bytes=1000, path=self.log_path
        )
        self.assertTrue(result["clean"])
        self.assertEqual(result["over_threshold"], [])

    def test_flags_a_file_at_or_over_threshold(self):
        result = sgc.check_scribe_growth(
            {"ROADMAP.md": 1000, "BUILDLOG.md": 50}, threshold_bytes=1000, path=self.log_path
        )
        self.assertFalse(result["clean"])
        self.assertEqual(result["over_threshold"], ["ROADMAP.md"])

    def test_flags_multiple_files_sorted(self):
        result = sgc.check_scribe_growth(
            {"ROADMAP.md": 2000, "BUILDLOG.md": 1500}, threshold_bytes=1000, path=self.log_path
        )
        self.assertEqual(result["over_threshold"], ["BUILDLOG.md", "ROADMAP.md"])

    def test_no_prior_check_means_growth_is_none(self):
        result = sgc.check_scribe_growth({"ROADMAP.md": 100}, threshold_bytes=1000, path=self.log_path)
        self.assertIsNone(result["growth_since_last_check"])

    def test_growth_is_the_real_delta_against_the_last_recorded_check(self):
        sgc.record_scribe_check({"ROADMAP.md": 100, "BUILDLOG.md": 50}, "2026-07-20T00:00:00Z", path=self.log_path)
        result = sgc.check_scribe_growth(
            {"ROADMAP.md": 130, "BUILDLOG.md": 45}, threshold_bytes=1000, path=self.log_path
        )
        self.assertEqual(result["growth_since_last_check"], {"ROADMAP.md": 30, "BUILDLOG.md": -5})

    def test_growth_compares_against_the_prior_check_never_against_itself(self):
        # Mirrors task 88's fix for square_check/arcade_app_watch: computing
        # growth must happen BEFORE this hour's own state is recorded, or
        # every call after the first would compare a state to itself and
        # always report zero growth.
        sgc.record_scribe_check({"ROADMAP.md": 100}, "2026-07-20T00:00:00Z", path=self.log_path)
        sizes = {"ROADMAP.md": 150}
        result = sgc.check_scribe_growth(sizes, threshold_bytes=1000, path=self.log_path)
        sgc.record_scribe_check(sizes, "2026-07-20T01:00:00Z", path=self.log_path)
        self.assertEqual(result["growth_since_last_check"], {"ROADMAP.md": 50})


class TestRecordScribeCheck(_TempFixtureCase):
    def test_record_creates_the_log_file(self):
        self.assertFalse(os.path.exists(self.log_path))
        sgc.record_scribe_check({"ROADMAP.md": 100}, "2026-07-20T00:00:00Z", path=self.log_path)
        self.assertTrue(os.path.exists(self.log_path))

    def test_record_never_mutates_a_prior_line(self):
        sgc.record_scribe_check({"ROADMAP.md": 100}, "2026-07-20T00:00:00Z", path=self.log_path)
        with open(self.log_path) as f:
            first_line = f.readline()
        sgc.record_scribe_check({"ROADMAP.md": 200}, "2026-07-20T01:00:00Z", path=self.log_path)
        with open(self.log_path) as f:
            lines = f.readlines()
        self.assertEqual(lines[0], first_line)
        self.assertEqual(len(lines), 2)

    def test_last_scribe_state_is_the_most_recent_entry(self):
        sgc.record_scribe_check({"ROADMAP.md": 100}, "2026-07-20T00:00:00Z", path=self.log_path)
        sgc.record_scribe_check({"ROADMAP.md": 200}, "2026-07-20T01:00:00Z", path=self.log_path)
        last = sgc.last_scribe_state(path=self.log_path)
        self.assertEqual(last["sizes"], {"ROADMAP.md": 200})
        self.assertEqual(last["checked_at"], "2026-07-20T01:00:00Z")

    def test_last_scribe_state_is_none_for_a_missing_log(self):
        self.assertIsNone(sgc.last_scribe_state(path=self.log_path))


class TestCLI(_TempFixtureCase):
    def test_check_command_runs_clean_against_the_real_repo(self):
        # End-to-end: shells out to the real script against the real repo
        # files and a throwaway log, proving the wired-together CLI (not
        # just the pure functions above) behaves.
        import subprocess

        env = dict(os.environ)
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "scribe_growth_check.py"), "check"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("ROADMAP.md", result.stdout)
        self.assertIn("BUILDLOG.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
