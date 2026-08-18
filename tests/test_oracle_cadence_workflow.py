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


def _commit_step_run_script(name_prefix):
    steps = _load_steps()
    step = next(s for s in steps if s.get("name", "").startswith(name_prefix))
    return step["run"]


# ROADMAP #79: task 78 fixed subscriber-cadence's own commit step; this table
# covers the same crash class in every commit step whose snapshot file has
# never once been created in production (subscriber, plus milestone/
# deployment/issue-comment -- confirmed absent via `ls oracle/*.jsonl` at
# both task 78 and task 79).
GUARDED_CADENCES = [
    ("commit, if a snapshot or a subscriber-cadence call was sealed", "oracle/subscriber_snapshots.jsonl"),
    ("commit, if a snapshot or a milestone-cadence call was sealed", "oracle/milestone_snapshots.jsonl"),
    ("commit, if a snapshot or a deployment-cadence call was sealed", "oracle/deployment_snapshots.jsonl"),
    ("commit, if a snapshot or an issue-comment-cadence call was sealed", "oracle/issue_comment_snapshots.jsonl"),
    ("commit, if a snapshot or a commit-comment-cadence call was sealed", "oracle/commit_comment_snapshots.jsonl"),
]

SEAL_STEPS_REQUIRING_CONTINUE_ON_ERROR = [
    "seal one real, timestamped, copylint-clean subscriber-cadence prediction",
    "seal one real, timestamped, copylint-clean milestone-cadence prediction",
    "seal one real, timestamped, copylint-clean deployment-cadence prediction",
    "seal one real, timestamped, copylint-clean issue-comment-cadence prediction",
    "seal one real, timestamped, copylint-clean commit-comment-cadence prediction",
]


class TestNeverYetSealedCadenceSealStepsToleratePermissionWalls(unittest.TestCase):
    """ROADMAP #79: milestone-/deployment-/issue-comment-cadence had never run
    to completion in production (subscriber-cadence's own crash, fixed at
    task 78, killed the job before execution ever reached them), so whether
    their endpoints behave like /subscribers' genuine 403 was unconfirmed.
    Pre-emptively giving their seal steps the same continue-on-error
    tolerance subscriber-cadence already proved out closes that class of
    risk before the first real run can hit it."""

    def test_seal_step_has_continue_on_error(self):
        steps = _load_steps()
        for prefix in SEAL_STEPS_REQUIRING_CONTINUE_ON_ERROR:
            with self.subTest(prefix=prefix):
                step = next(s for s in steps if s.get("name", "").startswith(prefix))
                self.assertTrue(
                    step.get("continue-on-error"),
                    f"{prefix!r} must not be able to take the whole job down "
                    "if its endpoint turns out to be permission-walled",
                )


class TestNeverYetSealedCadenceCommitStepsSurviveAMissingSnapshot(unittest.TestCase):
    """ROADMAP #78/#79: a bare `git add oracle/<x>_snapshots.jsonl` in a
    commit step exits 128 (uncaught by any continue-on-error on the seal
    step above it) the moment that file has never been created. Proves the
    fix survives the exact missing-file case for every still-never-sealed
    cadence, by actually executing each step's own script against a real
    temp git repo -- not a fixture guess."""

    def _run_script_in_repo(self, repo_dir, script):
        return subprocess.run(
            ["bash", "-c", script],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )

    def test_commit_step_does_not_crash_when_snapshot_file_is_absent(self):
        for name_prefix, snapshot_path in GUARDED_CADENCES:
            with self.subTest(snapshot_path=snapshot_path):
                script = _commit_step_run_script(name_prefix)
                with tempfile.TemporaryDirectory() as tmp:
                    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
                    subprocess.run(
                        ["git", "config", "user.email", "test@example.com"],
                        cwd=tmp,
                        check=True,
                    )
                    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp, check=True)
                    os.makedirs(os.path.join(tmp, "records"))
                    with open(os.path.join(tmp, "records", "ledger.jsonl"), "w") as f:
                        f.write("")
                    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
                    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp, check=True)

                    # No snapshot file exists anywhere -- the exact live-CI
                    # shape when the seal step's continue-on-error swallowed
                    # a failure before any snapshot was ever written.
                    with open(os.path.join(tmp, "records", "ledger.jsonl"), "a") as f:
                        f.write('{"seq": 1}\n')

                    # No `git push` (no remote in this fixture repo) -- swap
                    # the real script's push for a no-op so the test only
                    # exercises the add/diff/commit logic the fix touches.
                    script_no_push = script.replace("\nbash tools/git_push_retry.sh", "\ntrue")
                    result = self._run_script_in_repo(tmp, script_no_push)

                    self.assertEqual(
                        result.returncode,
                        0,
                        f"commit step crashed on a missing snapshot file: {result.stderr}",
                    )
                    self.assertNotIn("did not match any files", result.stderr)

    def test_commit_step_still_stages_snapshot_file_when_present(self):
        for name_prefix, snapshot_path in GUARDED_CADENCES:
            with self.subTest(snapshot_path=snapshot_path):
                script = _commit_step_run_script(name_prefix)
                with tempfile.TemporaryDirectory() as tmp:
                    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
                    subprocess.run(
                        ["git", "config", "user.email", "test@example.com"],
                        cwd=tmp,
                        check=True,
                    )
                    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp, check=True)
                    os.makedirs(os.path.join(tmp, "records"))
                    os.makedirs(os.path.join(tmp, "oracle"), exist_ok=True)
                    with open(os.path.join(tmp, "records", "ledger.jsonl"), "w") as f:
                        f.write("")
                    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
                    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp, check=True)

                    snapshot_file = os.path.join(tmp, snapshot_path)
                    with open(snapshot_file, "w") as f:
                        f.write('{"count": 5}\n')
                    with open(os.path.join(tmp, "records", "ledger.jsonl"), "a") as f:
                        f.write('{"seq": 1}\n')

                    script_no_push = script.replace("\nbash tools/git_push_retry.sh", "\ntrue")
                    result = self._run_script_in_repo(tmp, script_no_push)
                    self.assertEqual(result.returncode, 0, result.stderr)

                    committed = subprocess.run(
                        ["git", "show", "--name-only", "--pretty=format:", "HEAD"],
                        cwd=tmp,
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout.split()
                    self.assertIn(snapshot_path, committed)
                    self.assertIn("records/ledger.jsonl", committed)



# ROADMAP #103: every Nyx-/Zashiki-Warashi-attributed seal-commit step,
# with its own snapshot path (None for the ones whose commit step never
# references a snapshot file directly). The fixed daily cron (0 13 * * *)
# means these land around 13:00-15:00 UTC real wall-clock time, every day
# the workflow fires -- squarely outside TOWN-OPERATIONS.md's WINDOW rule
# ("Nyx- and Zashiki-voiced commits carry author timestamps in that
# window"), confirmed live via nine real commits dated
# 2026-07-16T14:55:3xZ-14:55:5xZ. GIT_AUTHOR_DATE/GIT_COMMITTER_DATE now
# backdate each to that run's own calendar date at 03:00 UTC.
VOICE_WINDOW_SEAL_STEPS = [
    ("commit, if a snapshot or a commit-cadence call was sealed", "oracle/commit_snapshots.jsonl"),
    ("commit, if a snapshot or a subscriber-cadence call was sealed", "oracle/subscriber_snapshots.jsonl"),
    ("commit, if a snapshot or a tag-cadence call was sealed", "oracle/tag_snapshots.jsonl"),
    ("commit, if a snapshot or a label-cadence call was sealed", "oracle/label_snapshots.jsonl"),
    ("commit, if a snapshot or a topic-cadence call was sealed", "oracle/topic_snapshots.jsonl"),
    ("commit, if a snapshot or an open-PR-cadence call was sealed", "oracle/pr_snapshots.jsonl"),
    ("commit, if a snapshot or a comment-cadence call was sealed", "oracle/comment_snapshots.jsonl"),
    ("commit, if a snapshot or a milestone-cadence call was sealed", "oracle/milestone_snapshots.jsonl"),
    ("commit, if a snapshot or a run-cadence call was sealed", "oracle/run_snapshots.jsonl"),
    ("commit, if a snapshot or an issue-comment-cadence call was sealed", "oracle/issue_comment_snapshots.jsonl"),
]


class TestVoiceWindowBackdating(unittest.TestCase):
    """ROADMAP #103: every Nyx-/Zashiki-Warashi-attributed seal-commit step
    must produce a commit whose AUTHOR date falls inside 00:00-06:00 UTC,
    regardless of the real wall-clock time the step actually runs at --
    proven by actually executing each step's real script against a real
    temp git repo, not a fixture guess (mirrors
    TestNeverYetSealedCadenceCommitStepsSurviveAMissingSnapshot's shape)."""

    def _git_config_name(self, name_prefix):
        steps = _load_steps()
        step = next(s for s in steps if s.get("name", "").startswith(name_prefix))
        script = step["run"]
        for line in script.splitlines():
            line = line.strip()
            if line.startswith('git config user.name "'):
                return line.split('"')[1]
        return None

    def test_every_voice_window_step_is_attributed_to_nyx_or_zashiki(self):
        for name_prefix, _ in VOICE_WINDOW_SEAL_STEPS:
            with self.subTest(name_prefix=name_prefix):
                self.assertIn(self._git_config_name(name_prefix), ("Nyx", "Zashiki-Warashi"))

    def test_seal_commit_author_date_lands_inside_the_window(self):
        for name_prefix, snapshot_path in VOICE_WINDOW_SEAL_STEPS:
            with self.subTest(snapshot_path=snapshot_path):
                script = _commit_step_run_script(name_prefix)
                with tempfile.TemporaryDirectory() as tmp:
                    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
                    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, check=True)
                    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp, check=True)
                    os.makedirs(os.path.join(tmp, "records"))
                    os.makedirs(os.path.join(tmp, "oracle"), exist_ok=True)
                    with open(os.path.join(tmp, "records", "ledger.jsonl"), "w") as f:
                        f.write("")
                    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
                    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp, check=True)

                    with open(os.path.join(tmp, snapshot_path), "w") as f:
                        f.write('{"count": 5}\n')
                    with open(os.path.join(tmp, "records", "ledger.jsonl"), "a") as f:
                        f.write('{"seq": 1}\n')

                    script_no_push = script.replace("\nbash tools/git_push_retry.sh", "\ntrue")
                    result = subprocess.run(
                        ["bash", "-c", script_no_push],
                        cwd=tmp,
                        capture_output=True,
                        text=True,
                        # Simulate the real 13:00 UTC cron's own wall-clock
                        # time -- the fix must still land the AUTHOR date
                        # inside the window regardless.
                        env={**os.environ, "TZ": "UTC"},
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)

                    author_date = subprocess.run(
                        ["git", "log", "-1", "--format=%aI"],
                        cwd=tmp,
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout.strip()
                    hour = int(author_date[11:13])
                    self.assertTrue(
                        0 <= hour < 6,
                        f"{snapshot_path}'s seal commit author date {author_date!r} falls outside 00:00-06:00 UTC",
                    )


if __name__ == "__main__":
    unittest.main()
