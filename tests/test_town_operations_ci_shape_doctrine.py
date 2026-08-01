"""ROADMAP #468. Off-By-One followed orita-vault/TOWN-OPERATIONS.md's own
`--ci-checks` line literally this hour -- "a JSON list of `{workflow,
conclusion, created_at}`" -- and it crashed: `KeyError: 'run_id'`.
`tools/ritual_check.py`'s real `check_ci()` folds each entry through
`ci_watch.record_check(workflow, conclusion, run_id, checked_at, ...)`
(task 73's own signature, unchanged since); the runbook's prose copy of
that shape had drifted the entire time, one repo over from the code it
describes, and nothing had ever proved the two against each other.

This module holds both halves of the fix accountable to real runtime
behavior rather than a second trust of prose, mirroring
`test_strategy_oracle_desk_doctrine.py`'s own discipline:

1. The corrected documented shape (`{workflow, conclusion, run_id,
   checked_at}`) is what the runbook now actually says.
2. The OLD documented shape genuinely fails against the live `check_ci()`
   -- proof the bug was real, not a stylistic nitpick.
3. The NEW documented shape genuinely succeeds against the live
   `check_ci()` -- proof the fix is actually correct, not just different.

Guarded the same way task 463's `test_thegap_check.py` and
`test_journal_numbering_check.py` already guard a claim about the private
vault sibling: `dawn-run.yml` checks out only this public repo, so a test
that reads the real `orita-vault/TOWN-OPERATIONS.md` file skips cleanly
there instead of failing on a premise (the vault checkout existing) that
was never true in that environment.
"""
import importlib.util
import os
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_ROOT = os.path.join(os.path.dirname(ROOT), "orita-vault")
TOWN_OPS_PATH = os.path.join(VAULT_ROOT, "TOWN-OPERATIONS.md")
_VAULT_CHECKED_OUT = os.path.isfile(TOWN_OPS_PATH)

REAL_KEYS = ("workflow", "conclusion", "run_id", "checked_at")
STALE_SHAPE = "{workflow, conclusion, created_at}"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _ci_checks_doc_line(text):
    m = re.search(r"^\s*-\s*`--ci-checks <path>`.*$", text, re.MULTILINE)
    return m.group(0) if m else None


class DocumentedShapeCase(unittest.TestCase):
    @unittest.skipUnless(
        _VAULT_CHECKED_OUT,
        "orita-vault not checked out alongside this repo in this environment "
        "(e.g. dawn-run.yml, which checks out only the public repo) -- "
        "nothing here to read a claim about",
    )
    def test_stale_shape_is_gone(self):
        line = _ci_checks_doc_line(_read(TOWN_OPS_PATH))
        self.assertIsNotNone(line, "TOWN-OPERATIONS.md must still document --ci-checks")
        self.assertNotIn(
            STALE_SHAPE,
            line,
            "TOWN-OPERATIONS.md still documents the wrong --ci-checks shape "
            "(missing run_id) -- this is the exact shape that crashed a live "
            "hourly run with KeyError: 'run_id'",
        )

    @unittest.skipUnless(_VAULT_CHECKED_OUT, "orita-vault not checked out")
    def test_documented_shape_names_every_real_required_key(self):
        line = _ci_checks_doc_line(_read(TOWN_OPS_PATH))
        for key in REAL_KEYS:
            self.assertIn(
                key,
                line,
                f"TOWN-OPERATIONS.md's --ci-checks line must name '{key}' -- "
                "it is a real required key of ci_watch.record_check",
            )


class LiveBehaviorGroundsTheClaimCase(unittest.TestCase):
    """Proves both the bug and the fix against the real, live check_ci() --
    not a second trust of prose, the same grounding discipline
    test_strategy_oracle_desk_doctrine.py already holds."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.rc = _load(
            f"_test_town_ops_ritual_check_{id(self)}",
            os.path.join(ROOT, "tools", "ritual_check.py"),
        )
        self.ciw = _load(
            f"_test_town_ops_ci_watch_{id(self)}",
            os.path.join(ROOT, "tools", "ci_watch.py"),
        )
        self.ciw.LOG = os.path.join(self.tmpdir, "ci-watch-log.jsonl")
        original_loader = self.rc._ci_watch
        self.rc._ci_watch = lambda: self.ciw
        self.addCleanup(setattr, self.rc, "_ci_watch", original_loader)

    def test_old_documented_shape_raises_key_error(self):
        stale_entry = [{"workflow": "dawn-run", "conclusion": "success", "created_at": "2026-08-01T22:24:15Z"}]
        with self.assertRaises(KeyError):
            self.rc.check_ci(stale_entry)

    def test_corrected_shape_succeeds(self):
        real_entry = [
            {
                "workflow": "dawn-run",
                "conclusion": "success",
                "run_id": 30721181034,
                "checked_at": "2026-08-01T23:10:00Z",
            }
        ]
        result = self.rc.check_ci(real_entry)
        self.assertIn("success", result["dawn-run"])
        self.assertIn("30721181034", result["dawn-run"])


if __name__ == "__main__":
    unittest.main()
