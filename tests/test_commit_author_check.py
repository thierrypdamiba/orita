"""Task 2507. Proves tools/commit_author_check.py finds a task-ritual
commit authored as the generic harness identity instead of its own god,
stays clean on a properly-authored one, ignores non-ritual commits
entirely, grandfathers a pre-fix drift instead of flagging it live, and
-- the real point -- names the live task-2506 drift this check was
built to catch as grandfathered sealed history, not a live violation.
"""
import importlib.util
import os
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


cac = _load("commit_author_check", os.path.join(ROOT, "tools", "commit_author_check.py"))

_BEFORE_FIX = "2026-01-01T00:00:00+00:00"
_AFTER_FIX = "2026-12-01T00:00:00+00:00"


def _git(repo, *args, env=None):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=env)


def _commit(repo, name, email, message, author_date):
    with open(os.path.join(repo, "f.txt"), "a", encoding="utf-8") as fh:
        fh.write(message + "\n")
    _git(repo, "add", "f.txt")
    env = dict(os.environ, GIT_AUTHOR_DATE=author_date, GIT_COMMITTER_DATE=author_date)
    _git(
        repo,
        "-c", f"user.name={name}",
        "-c", f"user.email={email}",
        "commit", "-m", message,
        env=env,
    )


class _TempRepoCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        _git(self.repo, "init", "-q", "-b", "main")

    def tearDown(self):
        self._tmp.cleanup()


class FindAuthorDriftCase(_TempRepoCase):
    def test_clean_when_every_ritual_commit_is_god_authored(self):
        _commit(self.repo, "Nisaba", "nisaba@orita.gods", "task 1: WIP -- hour 00 UTC", _AFTER_FIX)
        _commit(self.repo, "Ogun", "ogun@orita.gods", "task 1: close DONE -- hour 00 UTC", _AFTER_FIX)
        drift = cac.find_author_drift(repo_root=self.repo, fix_landed_at=_AFTER_FIX)
        self.assertEqual(drift["violations"], [])
        self.assertEqual(drift["grandfathered"], [])

    def test_flags_a_post_fix_drift_as_a_live_violation(self):
        _commit(self.repo, "Nisaba", "nisaba@orita.gods", "task 1: WIP -- hour 00 UTC", _AFTER_FIX)
        _commit(
            self.repo, "Claude", "noreply@anthropic.com",
            "task 1: close DONE -- hour 00 UTC, a drifted author", _AFTER_FIX,
        )
        drift = cac.find_author_drift(repo_root=self.repo, fix_landed_at=_BEFORE_FIX)
        self.assertEqual(len(drift["violations"]), 1)
        self.assertTrue(drift["violations"][0]["subject"].startswith("task 1: close DONE"))
        self.assertEqual(drift["violations"][0]["author_email"], "noreply@anthropic.com")
        self.assertEqual(drift["grandfathered"], [])

    def test_grandfathers_a_pre_fix_drift_instead_of_flagging_it_live(self):
        _commit(
            self.repo, "Claude", "noreply@anthropic.com",
            "task 1: close DONE -- hour 00 UTC, an old pre-fix drift", _BEFORE_FIX,
        )
        drift = cac.find_author_drift(repo_root=self.repo, fix_landed_at=_AFTER_FIX)
        self.assertEqual(drift["violations"], [])
        self.assertEqual(len(drift["grandfathered"]), 1)
        self.assertTrue(drift["grandfathered"][0]["subject"].endswith("an old pre-fix drift"))

    def test_ignores_non_ritual_commits_with_the_generic_identity(self):
        _commit(
            self.repo, "Claude", "noreply@anthropic.com",
            "scaffold: initial repository layout", _AFTER_FIX,
        )
        drift = cac.find_author_drift(repo_root=self.repo, fix_landed_at=_BEFORE_FIX)
        self.assertEqual(drift["violations"], [])
        self.assertEqual(drift["grandfathered"], [])

    def test_respects_max_commits(self):
        _commit(
            self.repo, "Claude", "noreply@anthropic.com",
            "task 1: close DONE -- old drift, outside the window", _AFTER_FIX,
        )
        for i in range(2, 5):
            _commit(self.repo, "Ogun", "ogun@orita.gods", f"task {i}: close DONE -- clean", _AFTER_FIX)
        drift = cac.find_author_drift(repo_root=self.repo, max_commits=3, fix_landed_at=_BEFORE_FIX)
        self.assertEqual(drift["violations"], [])
        self.assertEqual(drift["grandfathered"], [])


class FormatDriftCase(unittest.TestCase):
    def test_clean_message_shape(self):
        self.assertIn("clean", cac.format_drift({"violations": [], "grandfathered": []}))

    def test_clean_message_names_grandfathered_count(self):
        msg = cac.format_drift({"violations": [], "grandfathered": [{}, {}]})
        self.assertIn("2 grandfathered", msg)

    def test_drifted_message_names_the_commit(self):
        msg = cac.format_drift({
            "violations": [
                {"sha": "abc123def456", "author_name": "Claude",
                 "author_email": "noreply@anthropic.com",
                 "subject": "task 2506: close DONE -- hour 07 UTC"},
            ],
            "grandfathered": [],
        })
        self.assertIn("abc123def456"[:12], msg)
        self.assertIn("1 DRIFT", msg)


class RealCheckoutCase(unittest.TestCase):
    def test_the_live_task_2506_drift_is_grandfathered_not_a_live_violation(self):
        # Full history, not a small window -- this hour's own WIP+close
        # commits land after the known drift and must not push it out of
        # whatever window a future caller happens to pick.
        drift = cac.find_author_drift(repo_root=ROOT, max_commits=1_000_000)
        grandfathered_shas = {d["sha"] for d in drift["grandfathered"]}
        violation_shas = {d["sha"] for d in drift["violations"]}
        self.assertIn("edb2cd4619c62a04de01546c96fd25987d7e934f", grandfathered_shas)
        self.assertNotIn("edb2cd4619c62a04de01546c96fd25987d7e934f", violation_shas)


if __name__ == "__main__":
    unittest.main()
