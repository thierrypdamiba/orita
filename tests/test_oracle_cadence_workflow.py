import os
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


if __name__ == "__main__":
    unittest.main()
