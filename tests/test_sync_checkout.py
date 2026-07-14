"""Task 58. Kothar-wa-Khasis's fix for the recurring detached-HEAD toil:
proves tools/sync_checkout.sh recovers all four real cases without ever
discarding a commit, and refuses rather than guesses on real divergence.
"""
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "tools", "sync_checkout.sh")


def _run(*args):
    return subprocess.run(
        ["bash", SCRIPT, *args], capture_output=True, text=True
    )


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _git_quiet(repo, *args):
    subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, check=True,
    )


class _RepoPairCase(unittest.TestCase):
    """A bare origin plus one clone, both configured for commits."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.origin = os.path.join(self.tmp.name, "origin.git")
        self.clone = os.path.join(self.tmp.name, "clone")

        _git_quiet(self.tmp.name, "init", "--bare", "--initial-branch=main", self.origin)

        seed = os.path.join(self.tmp.name, "seed")
        _git_quiet(self.tmp.name, "init", "--initial-branch=main", seed)
        _git_quiet(seed, "config", "user.email", "seed@test")
        _git_quiet(seed, "config", "user.name", "seed")
        with open(os.path.join(seed, "f.txt"), "w") as f:
            f.write("one\n")
        _git_quiet(seed, "add", "f.txt")
        _git_quiet(seed, "commit", "-m", "first")
        _git_quiet(seed, "push", self.origin, "main")

        subprocess.run(
            ["git", "clone", "--quiet", self.origin, self.clone],
            capture_output=True, text=True, check=True,
        )
        _git_quiet(self.clone, "config", "user.email", "clone@test")
        _git_quiet(self.clone, "config", "user.name", "clone")

    def tearDown(self):
        self.tmp.cleanup()

    def _commit_on_origin(self, message):
        seed = os.path.join(self.tmp.name, "seed")
        with open(os.path.join(seed, "f.txt"), "a") as f:
            f.write(message + "\n")
        _git_quiet(seed, "add", "f.txt")
        _git_quiet(seed, "commit", "-m", message)
        _git_quiet(seed, "push", self.origin, "main")

    def _commit_local_only(self, repo, message):
        with open(os.path.join(repo, "local.txt"), "a") as f:
            f.write(message + "\n")
        _git_quiet(repo, "add", "local.txt")
        _git_quiet(repo, "commit", "-m", message)

    def _detach_at_current(self, repo):
        sha = _git(repo, "rev-parse", "HEAD")
        _git_quiet(repo, "checkout", "--detach", sha)


class TestAlreadyOnBranch(_RepoPairCase):
    def test_is_a_noop(self):
        r = _run(self.clone, "main")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("nothing to recover", r.stdout)
        self.assertEqual(_git(self.clone, "symbolic-ref", "--short", "HEAD"), "main")


class TestDetachedAtOrigin(_RepoPairCase):
    def test_recovers_cleanly_with_no_local_work(self):
        self._detach_at_current(self.clone)
        self.assertRaises(
            subprocess.CalledProcessError,
            lambda: _git(self.clone, "symbolic-ref", "--short", "HEAD"),
        )
        r = _run(self.clone, "main")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(_git(self.clone, "symbolic-ref", "--short", "HEAD"), "main")
        self.assertEqual(_git(self.clone, "rev-parse", "main"), _git(self.clone, "rev-parse", "origin/main"))


class TestDetachedAheadOfOrigin(_RepoPairCase):
    def test_keeps_local_only_commit_and_rebuilds_branch_there(self):
        self._detach_at_current(self.clone)
        self._commit_local_only(self.clone, "local work not yet pushed")
        local_sha = _git(self.clone, "rev-parse", "HEAD")

        r = _run(self.clone, "main")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("nothing discarded", r.stdout)
        self.assertEqual(_git(self.clone, "symbolic-ref", "--short", "HEAD"), "main")
        self.assertEqual(_git(self.clone, "rev-parse", "main"), local_sha)
        log = _git(self.clone, "log", "--oneline", "main")
        self.assertIn("local work not yet pushed", log)


class TestDetachedBehindOrigin(_RepoPairCase):
    def test_fast_forwards_to_origin(self):
        self._detach_at_current(self.clone)
        self._commit_on_origin("origin moved on")

        r = _run(self.clone, "main")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("fast-forwarded", r.stdout)
        _git_quiet(self.clone, "fetch", "origin", "main")
        self.assertEqual(_git(self.clone, "rev-parse", "main"), _git(self.clone, "rev-parse", "origin/main"))


class TestDetachedDiverged(_RepoPairCase):
    def test_refuses_and_touches_nothing(self):
        self._detach_at_current(self.clone)
        self._commit_local_only(self.clone, "local-only divergent commit")
        diverged_sha = _git(self.clone, "rev-parse", "HEAD")
        self._commit_on_origin("origin-only divergent commit")

        r = _run(self.clone, "main")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("diverged", r.stderr)
        # Nothing touched: still detached, still at the same commit.
        self.assertRaises(
            subprocess.CalledProcessError,
            lambda: _git(self.clone, "symbolic-ref", "--short", "HEAD"),
        )
        self.assertEqual(_git(self.clone, "rev-parse", "HEAD"), diverged_sha)


if __name__ == "__main__":
    unittest.main()
