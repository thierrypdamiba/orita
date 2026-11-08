"""Task 2508. `test_commit_author_check.py`'s
`test_the_live_task_2506_drift_is_grandfathered_not_a_live_violation`
(task 2507) reads `max_commits=1_000_000` of real git history to prove a
known drift commit is grandfathered sealed history, not a live
violation. `actions/checkout@v4`'s default `fetch-depth: 1` gives the
job running it a single-commit checkout -- the grandfathered commit is
unreachable, `find_author_drift` returns an empty set regardless of
which sha it is asked about, and the assertion fails on a premise
(deep history being present) that was never true in that job. Broke
`dawn-run`'s `the-oath` job live the same hour `commit_author_check.py`
shipped (task 2507); closed task 2508 by giving that job's checkout
`fetch-depth: 0`.

Guarded structurally the same way `test_oracle_cadence_workflow.py`
already guards a step property on a sibling workflow file: parse the
real YAML, don't just re-assert English prose about it.
"""
import os
import unittest

import yaml

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
WORKFLOW_PATH = os.path.join(REPO_ROOT, ".github", "workflows", "dawn-run.yml")


def _the_oath_checkout_step():
    with open(WORKFLOW_PATH) as f:
        doc = yaml.safe_load(f)
    steps = doc["jobs"]["the-oath"]["steps"]
    return next(s for s in steps if s.get("uses", "").startswith("actions/checkout@"))


class TestDawnRunFetchDepth(unittest.TestCase):
    def test_the_oath_checkout_requests_full_history(self):
        step = _the_oath_checkout_step()
        self.assertEqual(step.get("with", {}).get("fetch-depth"), 0)

    def test_a_shallow_checkout_would_genuinely_break_the_live_regression_test(self):
        # Proof the fix addresses a real failure mode, not a stylistic
        # nitpick: with the depth-1 default this job used to carry, any
        # max_commits window the caller picks sees at most one commit
        # (HEAD itself), so a known-grandfathered sha from history can
        # never be found -- exactly the live break this task closes.
        import importlib.util
        import sys
        import tempfile
        import subprocess

        spec = importlib.util.spec_from_file_location(
            "commit_author_check",
            os.path.join(REPO_ROOT, "tools", "commit_author_check.py"),
        )
        cac = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cac
        spec.loader.exec_module(cac)

        with tempfile.TemporaryDirectory() as shallow:
            # A plain local-path source makes git ignore --depth entirely
            # ("--depth is ignored in local clones; use file:// instead.")
            # -- the file:// form is required to actually reproduce the
            # depth-1 checkout actions/checkout@v4 gives dawn-run.
            subprocess.run(
                ["git", "clone", "--depth", "1", f"file://{REPO_ROOT}", shallow],
                capture_output=True, text=True, check=True,
            )
            drift = cac.find_author_drift(repo_root=shallow, max_commits=1_000_000)
            self.assertEqual(len(drift["grandfathered"]) + len(drift["violations"]), 0)


if __name__ == "__main__":
    unittest.main()
