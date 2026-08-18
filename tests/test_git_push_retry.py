"""Task 847. tools/git_push_retry.sh's fix for the exact race that dropped
seam-scan's 2026-08-18 report: two clones committing on the same branch,
the second one's plain `git push` gets rejected (remote moved first), and
the runner had no recovery. Proves the retry script fetches + rebases +
retries through a real non-conflicting race, and still fails loudly (not
silently) when the two sides truly conflict.
"""
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "tools", "git_push_retry.sh")


def _git_quiet(repo, *args):
    subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, check=True,
    )


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


class TestGitPushRetry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.origin = os.path.join(self.tmp.name, "origin.git")
        self.clone_a = os.path.join(self.tmp.name, "clone_a")
        self.clone_b = os.path.join(self.tmp.name, "clone_b")

        _git_quiet(self.tmp.name, "init", "--bare", "--initial-branch=main", self.origin)

        seed = os.path.join(self.tmp.name, "seed")
        _git_quiet(self.tmp.name, "init", "--initial-branch=main", seed)
        _git_quiet(seed, "config", "user.email", "seed@test")
        _git_quiet(seed, "config", "user.name", "seed")
        with open(os.path.join(seed, "shared.txt"), "w") as f:
            f.write("base\n")
        _git_quiet(seed, "add", "shared.txt")
        _git_quiet(seed, "commit", "-m", "first")
        _git_quiet(seed, "push", self.origin, "main")

        for clone in (self.clone_a, self.clone_b):
            subprocess.run(
                ["git", "clone", "--quiet", self.origin, clone],
                capture_output=True, text=True, check=True,
            )
            _git_quiet(clone, "config", "user.email", "clone@test")
            _git_quiet(clone, "config", "user.name", "clone")

    def tearDown(self):
        self.tmp.cleanup()

    def _run_retry(self, repo):
        return subprocess.run(
            ["bash", SCRIPT], cwd=repo, capture_output=True, text=True,
        )

    def test_retries_and_succeeds_when_remote_moved_but_files_do_not_conflict(self):
        # clone_a commits and pushes first, exactly like a same-hour ritual
        # commit landing before seam-scan's own run finishes.
        with open(os.path.join(self.clone_a, "a-only.txt"), "w") as f:
            f.write("a\n")
        _git_quiet(self.clone_a, "add", "a-only.txt")
        _git_quiet(self.clone_a, "commit", "-m", "clone_a change")
        _git_quiet(self.clone_a, "push")

        # clone_b, still on the now-stale base, commits a different file --
        # the real seam-scan shape: it never touches the ritual's own files.
        with open(os.path.join(self.clone_b, "b-only.txt"), "w") as f:
            f.write("b\n")
        _git_quiet(self.clone_b, "add", "b-only.txt")
        _git_quiet(self.clone_b, "commit", "-m", "clone_b change")

        result = self._run_retry(self.clone_b)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("attempt", result.stderr)

        # Both commits landed on origin/main, nothing lost.
        log = _git(self.origin, "log", "--oneline", "main")
        self.assertIn("clone_a change", log)
        self.assertIn("clone_b change", log)

    def test_fails_loudly_on_a_real_conflict_instead_of_looping_forever(self):
        with open(os.path.join(self.clone_a, "shared.txt"), "w") as f:
            f.write("base\nclone_a wins this line\n")
        _git_quiet(self.clone_a, "add", "shared.txt")
        _git_quiet(self.clone_a, "commit", "-m", "clone_a conflicting change")
        _git_quiet(self.clone_a, "push")

        with open(os.path.join(self.clone_b, "shared.txt"), "w") as f:
            f.write("base\nclone_b wins this line\n")
        _git_quiet(self.clone_b, "add", "shared.txt")
        _git_quiet(self.clone_b, "commit", "-m", "clone_b conflicting change")

        result = self._run_retry(self.clone_b)
        self.assertNotEqual(result.returncode, 0)

    def test_succeeds_immediately_with_no_retry_needed(self):
        with open(os.path.join(self.clone_a, "solo.txt"), "w") as f:
            f.write("solo\n")
        _git_quiet(self.clone_a, "add", "solo.txt")
        _git_quiet(self.clone_a, "commit", "-m", "solo change")

        result = self._run_retry(self.clone_a)
        self.assertEqual(result.returncode, 0, result.stderr)
        log = _git(self.origin, "log", "--oneline", "main")
        self.assertIn("solo change", log)


if __name__ == "__main__":
    unittest.main()
