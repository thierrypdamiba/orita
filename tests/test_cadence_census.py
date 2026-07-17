"""ROADMAP #96: every prior Oracle Desk task (30-95) added one more cadence
source by hand, checked by eye against the ones before it ("no new Arcade
tool, no new scope" -- confirmed by rereading, never by a test that runs
itself). Twenty-six sources deep, nothing has ever asserted the shape holds
across ALL of them at once: that every `*_cadence.py` has a matching
`*_autograde.py`, that both are actually wired into `oracle-cadence.yml`,
and that the wiring's own snapshot path matches the module's name -- the
same class of silently-drifting invariant `test_wall.py` (ROADMAP #95) and
`tools/ritual_check.py`'s own fold (#69-91) each closed one instance of.
This is the census: add a twenty-seventh cadence tomorrow without wiring
its autograde, or without adding it to the workflow, or with a copy-pasted
wrong snapshot filename, and this file catches it the same hour, not the
next time someone happens to reread the whole workflow by hand.
"""

import os
import re
import unittest

import yaml

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
ORACLE_ENGINE_SRC = os.path.join(
    REPO_ROOT, "oracle", "oracle_engine", "src", "oracle_engine"
)
WORKFLOW_PATH = os.path.join(REPO_ROOT, ".github", "workflows", "oracle-cadence.yml")

# oracle_engine.cadence / oracle_engine.autograde (ROADMAP #36) is the one
# self-referential source: it reads the town's own BUILDLOG.md/ROADMAP.md,
# not an external endpoint, so it has no oracle/*_snapshots.jsonl of its
# own -- every other source does. Excluded from the snapshot-path check
# only; still required to exist and to be wired, like every other source.
SELF_REFERENTIAL_BASE = ""


def _cadence_base_names():
    """Every '<base>_cadence.py' under oracle_engine, as '<base>'."""
    bases = []
    for name in sorted(os.listdir(ORACLE_ENGINE_SRC)):
        m = re.fullmatch(r"(.+)_cadence\.py", name)
        if m:
            bases.append(m.group(1))
    return bases


def _load_workflow_text():
    with open(WORKFLOW_PATH) as f:
        return f.read()


def _load_steps():
    with open(WORKFLOW_PATH) as f:
        doc = yaml.safe_load(f)
    job = next(iter(doc["jobs"].values()))
    return job["steps"]


class CadenceCensusCase(unittest.TestCase):
    def setUp(self):
        self.bases = _cadence_base_names()
        self.workflow_text = _load_workflow_text()

    def test_at_least_the_known_cadence_family_is_present(self):
        # A floor, not a ceiling -- guards against the glob itself silently
        # matching nothing (e.g. a path typo) and every other test in this
        # file passing vacuously as a result.
        self.assertGreaterEqual(
            len(self.bases),
            24,
            "expected at least the 24 cadence sources shipped through "
            "ROADMAP #93; found fewer -- check ORACLE_ENGINE_SRC resolves",
        )

    def test_every_cadence_module_has_a_matching_autograde_module(self):
        for base in self.bases:
            with self.subTest(base=base):
                path = os.path.join(ORACLE_ENGINE_SRC, f"{base}_autograde.py")
                self.assertTrue(
                    os.path.isfile(path),
                    f"{base}_cadence.py has no matching {base}_autograde.py",
                )

    def test_bare_cadence_module_has_a_matching_bare_autograde_module(self):
        cadence_py = os.path.join(ORACLE_ENGINE_SRC, "cadence.py")
        autograde_py = os.path.join(ORACLE_ENGINE_SRC, "autograde.py")
        self.assertTrue(os.path.isfile(cadence_py))
        self.assertTrue(
            os.path.isfile(autograde_py),
            "the self-referential oracle_engine.cadence has no matching "
            "oracle_engine.autograde",
        )

    def test_every_cadence_module_is_invoked_in_the_workflow(self):
        for base in self.bases:
            with self.subTest(base=base):
                pattern = rf"python3 -m oracle_engine\.{re.escape(base)}_cadence\b"
                self.assertRegex(
                    self.workflow_text,
                    pattern,
                    f"oracle_engine.{base}_cadence is never invoked in "
                    "oracle-cadence.yml",
                )

    def test_every_autograde_module_is_invoked_in_the_workflow(self):
        for base in self.bases:
            with self.subTest(base=base):
                pattern = rf"python3 -m oracle_engine\.{re.escape(base)}_autograde\b"
                self.assertRegex(
                    self.workflow_text,
                    pattern,
                    f"oracle_engine.{base}_autograde is never invoked in "
                    "oracle-cadence.yml",
                )

    def test_every_cadence_seal_step_precedes_its_own_autograde_step(self):
        steps = _load_steps()
        runs = [s.get("run", "").strip() for s in steps]
        for base in self.bases:
            with self.subTest(base=base):
                cadence_run = f"python3 -m oracle_engine.{base}_cadence"
                autograde_run = f"python3 -m oracle_engine.{base}_autograde"
                cadence_idx = next(
                    (i for i, r in enumerate(runs) if r == cadence_run), None
                )
                autograde_idx = next(
                    (i for i, r in enumerate(runs) if r == autograde_run), None
                )
                self.assertIsNotNone(cadence_idx, f"{base}_cadence step missing")
                self.assertIsNotNone(autograde_idx, f"{base}_autograde step missing")
                self.assertLess(
                    cadence_idx,
                    autograde_idx,
                    f"{base}_cadence must seal before {base}_autograde grades it",
                )

    def test_every_cadence_snapshot_path_matches_its_own_base_name(self):
        for base in self.bases:
            with self.subTest(base=base):
                expected = f"oracle/{base}_snapshots.jsonl"
                self.assertIn(
                    expected,
                    self.workflow_text,
                    f"{base}_cadence's expected snapshot path {expected!r} "
                    "never appears in oracle-cadence.yml -- likely a typo'd "
                    "or copy-pasted-wrong snapshot filename in its commit step",
                )
