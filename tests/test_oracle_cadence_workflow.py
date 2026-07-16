import os
import subprocess
import tempfile
import unittest

import yaml

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
WORKFLOW_PATH = os.path.join(REPO_ROOT, ".github", "workflows", "oracle-cadence.yml")

# A crashing "seal" step with no continue-on-error takes the whole job down
# with it, silently skipping every step declared after it in file order --
# exactly what happened live this hour (ROADMAP #64): subscriber-cadence's
# permanent 403 killed tag/label/topic/pr/workflow-cadence too.
DOWNSTREAM_CADENCE_MARKERS = [
    "seal one real, timestamped, copylint-clean tag-cadence prediction",
    "seal one real, timestamped, copylint-clean label-cadence prediction",
    "seal one real, timestamped, copylint-clean topic-cadence prediction",
    "seal one real, timestamped, copylint-clean open-PR-cadence prediction",
    "seal one real, timestamped, copylint-clean workflow-cadence prediction",
]


def _load_steps():
    with open(WORKFLOW_PATH) as f:
        doc = yaml.safe_load(f)
    jobs = doc["jobs"]
    job = next(iter(jobs.values()))
    return job["steps"]


class TestSubscriberCadenceIsGuarded(unittest.TestCase):
    def test_subscriber_cadence_seal_step_has_continue_on_error(self):
        steps = _load_steps()
        subscriber_seal = next(
            s
            for s in steps
            if s.get("name", "").startswith(
                "seal one real, timestamped, copylint-clean subscriber-cadence prediction"
            )
        )
        self.assertTrue(
            subscriber_seal.get("continue-on-error"),
            "subscriber-cadence's seal step must not be able to take the whole "
            "job down -- its endpoint is proven (2026-07-14T14:44Z live run) to "
            "403 even with an authenticated GITHUB_TOKEN.",
        )

    def test_downstream_cadence_steps_still_present_in_order(self):
        # The fix must unblock the downstream steps, not remove or reorder them.
        steps = _load_steps()
        names = [s.get("name", "") for s in steps]
        found_positions = []
        for marker in DOWNSTREAM_CADENCE_MARKERS:
            matches = [i for i, n in enumerate(names) if marker in n]
            self.assertEqual(
                len(matches),
                1,
                f"expected exactly one seal step containing {marker!r}",
            )
            found_positions.append(matches[0])
        self.assertEqual(
            found_positions,
            sorted(found_positions),
            "downstream cadence seal steps must stay in their original file order",
        )

    def test_subscriber_cadence_precedes_all_downstream_cadences(self):
        steps = _load_steps()
        names = [s.get("name", "") for s in steps]
        subscriber_idx = next(
            i
            for i, n in enumerate(names)
            if n.startswith(
                "seal one real, timestamped, copylint-clean subscriber-cadence prediction"
            )
        )
        for marker in DOWNSTREAM_CADENCE_MARKERS:
            downstream_idx = next(i for i, n in enumerate(names) if marker in n)
            self.assertLess(
                subscriber_idx,
                downstream_idx,
                f"expected subscriber-cadence to precede {marker!r} in file order",
            )


def _commit_step_run_script():
    steps = _load_steps()
    step = next(
        s
        for s in steps
        if s.get("name", "").startswith(
            "commit, if a snapshot or a subscriber-cadence call was sealed"
        )
    )
    return step["run"]


class TestSubscriberCadenceCommitSurvivesAMissingSnapshot(unittest.TestCase):
    """ROADMAP #78: task 64's continue-on-error on the SEAL step wasn't enough --
    the COMMIT step right after it did `git add oracle/subscriber_snapshots.jsonl`
    unconditionally, and that file has never once been created (every real run
    of subscriber_cadence.py crashes on the endpoint's genuine 403 before it can
    write one). `git add` on a nonexistent pathspec exits 128, uncaught by any
    continue-on-error, and killed the whole job -- silently skipping every
    cadence step declared after it in file order (tag-51 through
    issue-comment-77, ten sources) on every single real CI run since task 64
    shipped. This proves the fix survives the exact missing-file case live CI
    hit (run 29424866577, 2026-07-15T14:44Z), by actually executing the
    step's own script against a real temp git repo -- not a fixture guess."""

    def _run_script_in_repo(self, repo_dir, script):
        return subprocess.run(
            ["bash", "-c", script],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )

    def test_commit_step_does_not_crash_when_snapshot_file_is_absent(self):
        script = _commit_step_run_script()
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=tmp, check=True
            )
            subprocess.run(["git", "config", "user.name", "test"], cwd=tmp, check=True)
            os.makedirs(os.path.join(tmp, "records"))
            with open(os.path.join(tmp, "records", "ledger.jsonl"), "w") as f:
                f.write("")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp, check=True)

            # No oracle/subscriber_snapshots.jsonl exists anywhere -- the exact
            # live-CI shape when the seal step's continue-on-error swallowed a
            # 403 before any snapshot was ever written.
            with open(os.path.join(tmp, "records", "ledger.jsonl"), "a") as f:
                f.write('{"seq": 1}\n')

            # No `git push` (no remote in this fixture repo) -- swap the real
            # script's push for a no-op so the test only exercises the add/
            # diff/commit logic the fix actually touches.
            script_no_push = script.replace("\ngit push", "\ntrue")
            result = self._run_script_in_repo(tmp, script_no_push)

            self.assertEqual(
                result.returncode,
                0,
                f"commit step crashed on a missing snapshot file: {result.stderr}",
            )
            self.assertNotIn("did not match any files", result.stderr)

    def test_commit_step_still_stages_snapshot_file_when_present(self):
        script = _commit_step_run_script()
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=tmp, check=True
            )
            subprocess.run(["git", "config", "user.name", "test"], cwd=tmp, check=True)
            os.makedirs(os.path.join(tmp, "records"))
            os.makedirs(os.path.join(tmp, "oracle"))
            with open(os.path.join(tmp, "records", "ledger.jsonl"), "w") as f:
                f.write("")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp, check=True)

            with open(os.path.join(tmp, "oracle", "subscriber_snapshots.jsonl"), "w") as f:
                f.write('{"count": 5}\n')
            with open(os.path.join(tmp, "records", "ledger.jsonl"), "a") as f:
                f.write('{"seq": 1}\n')

            script_no_push = script.replace("\ngit push", "\ntrue")
            result = self._run_script_in_repo(tmp, script_no_push)
            self.assertEqual(result.returncode, 0, result.stderr)

            committed = subprocess.run(
                ["git", "show", "--name-only", "--pretty=format:", "HEAD"],
                cwd=tmp,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.split()
            self.assertIn("oracle/subscriber_snapshots.jsonl", committed)
            self.assertIn("records/ledger.jsonl", committed)


if __name__ == "__main__":
    unittest.main()
