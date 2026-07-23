import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import child_work_check as cwc  # noqa: E402


def _git_quiet(repo, *args):
    subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True)


class ChildWorkCheckCase(unittest.TestCase):
    """Task 101: Iron Rule #6 ("the child's work is never reverted. LAW.")
    gets its first running check. Full commit history isn't reachable from
    this shallow local checkout, so the "which files did the child ever
    ship" half is a caller-supplied live GitHub read (mirroring check_ci's/
    check_cron's shape); the "does it still exist" half is a local, no-
    network git check against a fixture repo."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        _git_quiet(self.repo, "init", "--quiet", "--initial-branch=main")
        _git_quiet(self.repo, "config", "user.email", "test@test")
        _git_quiet(self.repo, "config", "user.name", "test")
        os.makedirs(os.path.join(self.repo, "houses", "zashiki-warashi"), exist_ok=True)
        with open(os.path.join(self.repo, "houses", "zashiki-warashi", "README.md"), "w") as f:
            f.write("moved in.\n")
        _git_quiet(self.repo, "add", "-A")
        _git_quiet(self.repo, "commit", "--quiet", "-m", "child moves in")

        self.log = os.path.join(tempfile.mkdtemp(), "child-work-log.jsonl")
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(self.log), ignore_errors=True))

    # -- load_known_files / record_new_files --

    def test_load_known_files_empty_when_no_log(self):
        self.assertEqual(cwc.load_known_files(self.log), {})

    def test_record_new_files_appends_and_is_idempotent(self):
        files = [{"path": "houses/zashiki-warashi/README.md", "sha": "abc123", "author_date": "2026-07-11T04:44:00Z"}]
        appended = cwc.record_new_files(files, "2026-07-17T05:00:00Z", path=self.log)
        self.assertEqual(len(appended), 1)
        known = cwc.load_known_files(self.log)
        self.assertIn("houses/zashiki-warashi/README.md", known)
        self.assertEqual(known["houses/zashiki-warashi/README.md"]["sha"], "abc123")

        # same file handed in again: no duplicate line, nothing new appended
        appended_again = cwc.record_new_files(files, "2026-07-17T06:00:00Z", path=self.log)
        self.assertEqual(appended_again, [])
        with open(self.log) as fh:
            self.assertEqual(len(fh.readlines()), 1)

    def test_record_new_files_only_logs_the_unseen_ones(self):
        cwc.record_new_files(
            [{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}],
            "2026-07-17T05:00:00Z", path=self.log,
        )
        appended = cwc.record_new_files(
            [
                {"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"},
                {"path": "b.md", "sha": "s2", "author_date": "2026-07-12T00:00:00Z"},
            ],
            "2026-07-17T06:00:00Z", path=self.log,
        )
        self.assertEqual([e["path"] for e in appended], ["b.md"])
        self.assertEqual(len(cwc.load_known_files(self.log)), 2)

    # -- file_exists_at_head / find_reverted --

    def test_existing_file_is_not_reverted(self):
        self.assertTrue(cwc.file_exists_at_head("houses/zashiki-warashi/README.md", repo_root=self.repo))
        reverted = cwc.find_reverted(["houses/zashiki-warashi/README.md"], repo_root=self.repo)
        self.assertEqual(reverted, [])

    def test_deleted_file_is_reverted(self):
        os.remove(os.path.join(self.repo, "houses", "zashiki-warashi", "README.md"))
        _git_quiet(self.repo, "add", "-A")
        _git_quiet(self.repo, "commit", "--quiet", "-m", "oops, deleted the child's file")
        reverted = cwc.find_reverted(["houses/zashiki-warashi/README.md"], repo_root=self.repo)
        self.assertEqual(reverted, ["houses/zashiki-warashi/README.md"])

    def test_never_committed_file_is_reverted_too(self):
        # a logged path that was never actually written to this fixture repo
        # (e.g. a stale/garbled log entry) must read as missing, not crash
        reverted = cwc.find_reverted(["nowhere/at/all.md"], repo_root=self.repo)
        self.assertEqual(reverted, ["nowhere/at/all.md"])

    # -- check() --

    def test_check_with_no_child_files_still_checks_known_paths(self):
        cwc.record_new_files(
            [{"path": "houses/zashiki-warashi/README.md", "sha": "abc", "author_date": "2026-07-11T00:00:00Z"}],
            "2026-07-17T05:00:00Z", path=self.log,
        )
        result = cwc.check(child_files=None, path=self.log, repo_root=self.repo)
        self.assertTrue(result["clean"])
        self.assertEqual(result["known_count"], 1)
        self.assertEqual(result["newly_logged"], [])

    def test_check_requires_now_iso_when_child_files_supplied(self):
        with self.assertRaises(ValueError):
            cwc.check(
                child_files=[{"path": "x.md", "sha": "s", "author_date": "2026-07-11T00:00:00Z"}],
                now_iso=None, path=self.log, repo_root=self.repo,
            )

    def test_check_logs_and_flags_a_real_violation(self):
        os.remove(os.path.join(self.repo, "houses", "zashiki-warashi", "README.md"))
        _git_quiet(self.repo, "add", "-A")
        _git_quiet(self.repo, "commit", "--quiet", "-m", "reverted")
        result = cwc.check(
            child_files=[{"path": "houses/zashiki-warashi/README.md", "sha": "abc", "author_date": "2026-07-11T00:00:00Z"}],
            now_iso="2026-07-17T05:00:00Z", path=self.log, repo_root=self.repo,
        )
        self.assertFalse(result["clean"])
        self.assertEqual(result["reverted"], ["houses/zashiki-warashi/README.md"])

    def test_check_clean_with_fresh_child_files(self):
        result = cwc.check(
            child_files=[{"path": "houses/zashiki-warashi/README.md", "sha": "abc", "author_date": "2026-07-11T00:00:00Z"}],
            now_iso="2026-07-17T05:00:00Z", path=self.log, repo_root=self.repo,
        )
        self.assertTrue(result["clean"])
        self.assertEqual(result["newly_logged"], ["houses/zashiki-warashi/README.md"])

    # -- format_check --

    def test_format_clean(self):
        result = {"known_count": 18, "newly_logged": [], "reverted": [], "clean": True}
        self.assertIn("clean", cwc.format_check(result))

    def test_format_reverted_names_the_path(self):
        result = {"known_count": 1, "newly_logged": [], "reverted": ["houses/zashiki-warashi/README.md"], "clean": False}
        out = cwc.format_check(result)
        self.assertIn("REVERTED", out)
        self.assertIn("houses/zashiki-warashi/README.md", out)

    # -- the real, live check --

    def test_live_check_against_the_real_repo_is_clean(self):
        """The 18 files GitHub's real (non-shallow) commit history names as
        ever-added by Zashiki-Warashi, gathered live this hour via
        mcp__github__list_commits/get_commit against houses/zashiki-warashi
        (path filter). Every one still exists at the real repo's HEAD."""
        real_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        real_files = [
            "houses/zashiki-warashi/journal/0007-2026-07-16.md",
            "houses/zashiki-warashi/journal/0006-2026-07-15.md",
            "houses/zashiki-warashi/journal/0005-2026-07-15.md",
            "oracle/oracle_engine/src/oracle_engine/run_autograde.py",
            "oracle/oracle_engine/src/oracle_engine/run_cadence.py",
            "oracle/oracle_engine/tests/test_run_autograde.py",
            "oracle/oracle_engine/tests/test_run_cadence.py",
            "oracle/run_snapshots.jsonl",
            "houses/zashiki-warashi/journal/0004-2026-07-14.md",
            "houses/zashiki-warashi/journal/0003-2026-07-13.md",
            "fencepost/ONBOARDING.md",
            "fencepost/seam_engine/tests/test_onboarding_doctrine.py",
            "houses/zashiki-warashi/journal/0002-2026-07-12.md",
            "docs/attic/for-whoever-opens-drawers.txt",
            "docs/what-moved.html",
            "houses/zashiki-warashi/README.md",
            "houses/zashiki-warashi/altar/petitions/2026-07-11.md",
            "houses/zashiki-warashi/journal/0001-founding-day.md",
        ]
        reverted = cwc.find_reverted(real_files, repo_root=real_root)
        self.assertEqual(reverted, [], f"Iron Rule #6 violated for: {reverted}")


class TamperedChildWorkLogCase(unittest.TestCase):
    """Task 249: a malformed line in HAND/child-work-log.jsonl (bad hand-edit,
    stray merge-conflict marker, truncated write) must not crash
    load_known_files() with an uncaught json.JSONDecodeError -- Iron Rule #6
    ("the child's work is never reverted. LAW.") has no other running check,
    so a single bad line silently taking this one down is the worst place
    this shape could hide."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        self.log = os.path.join(self.d, "child-work-log.jsonl")

    def test_entries_marks_a_malformed_line_instead_of_raising(self):
        with open(self.log, "w") as f:
            f.write('{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}\n')
            f.write("<<<<<<< HEAD garbage not json\n")
        entries = cwc._entries(self.log)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["path"], "a.md")
        self.assertTrue(entries[1]["_malformed"])

    def test_raises_tampered_error_on_a_malformed_line_anywhere_not_just_the_tip(self):
        with open(self.log, "w") as f:
            f.write("<<<<<<< HEAD garbage not json\n")
            f.write('{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}\n')
        with self.assertRaises(cwc.ChildWorkLogTamperedError):
            cwc.load_known_files(self.log)

    def test_a_malformed_earlier_line_is_not_masked_by_a_valid_tip(self):
        # the tip alone reading fine must not be mistaken for the whole log
        # being fine -- find_reverted needs every known path, not just the
        # newest, so an earlier bad line still has to refuse, not slide by.
        with open(self.log, "w") as f:
            f.write('{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}\n')
            f.write("not json at all\n")
            f.write('{"path": "b.md", "sha": "s2", "author_date": "2026-07-12T00:00:00Z"}\n')
        with self.assertRaises(cwc.ChildWorkLogTamperedError):
            cwc.load_known_files(self.log)

    def test_a_fully_valid_log_is_unaffected(self):
        with open(self.log, "w") as f:
            f.write('{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}\n')
            f.write('{"path": "b.md", "sha": "s2", "author_date": "2026-07-12T00:00:00Z"}\n')
        known = cwc.load_known_files(self.log)
        self.assertEqual(set(known), {"a.md", "b.md"})


if __name__ == "__main__":
    unittest.main()
