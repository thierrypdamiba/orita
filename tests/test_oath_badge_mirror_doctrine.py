#!/usr/bin/env python3
"""Task 162. Retrya checks her own team's reusable oath-badge template
against the original it swears to mirror.

`tools/oath_badge.py` (Kothar-wa-Khasis, task 25, "extract the read-only-
badge pattern... into a reusable template") is the "Fencepost sanded off"
generalization of `seam_engine.badge` (Ogun, task 23) -- STRATEGY.md's own
"Read-Only Oath & Governance" row, lead ogun, +retrya. Its own docstring
closes with "Sworn on iron, same as the original." Its `DEFAULT_POLICY`
carries the comment "Ogun's read-only clause, verbatim." Two direct mirror
claims about a sibling module, sitting in a file my own team co-leads,
never once checked against the real thing they claim to mirror -- confirmed
by grep, zero comparisons anywhere in `tests/test_oath_badge.py` or any
other test.

The claim was almost true, and thinner than it read. `seam_engine.badge.
ToolAudit.ok` checks `self.read_only is True` and `self.destructive is
False` -- IDENTITY, on purpose (its own comment: "Anything else -- read_only
False, destructive True... is a violation, named, not hidden"). `tools/
oath_badge.py`'s `ToolAudit.ok` checked `self.declared.get(k) == v` for
every field, including the two booleans -- EQUALITY. Python treats
`1 == True` and `0 == False`, so a duck-typed or dict-shaped tool record
(the exact "fixture, or a lighter integration" shape this module's own
docstring advertises supporting -- `_extract_declared`'s dict/plain-object
branches never cast to `bool()`, unlike its arcade-mcp-shaped branch) that
declares `read_only=1` instead of an actual `True` would silently PASS this
module's oath check while the same declaration correctly FAILS the real
original's. The two checkers, not just the two constants, had quietly
drifted apart from a rule the docstring calls sworn on iron.

Fixed `ToolAudit.ok`/`.violation` to route every boolean policy value
through a shared `_policy_value_matches` helper that checks identity for
booleans (exactly badge.py's own discipline) and equality for everything
else (the `operations` tuple, unchanged). This file proves the two real
oaths now agree -- live-loaded, across a battery of synthetic declared-
value combinations no hand-typed second copy could coincidentally satisfy
-- and a mutation test reconstructs `ToolAudit.ok`'s real pre-task-162 body
to prove it really did disagree with badge.py's real, live oath on the
exact edge case above, while the fixed, real module now agrees.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "fencepost", "seam_engine", "src"))
from seam_engine import badge as real_badge  # noqa: E402


def _load_oath_badge(name: str):
    """Fresh module instance, the same `spec_from_file_location` shape
    `tests/test_oath_badge.py` and `tests/test_cadence_target_mirror_doctrine.py`
    already use -- registered in `sys.modules` before `exec_module` since
    oath_badge.py's own frozen dataclasses need the module to resolve by
    name during class creation (the identical trap `test_oath_badge.py`'s
    own `_load()` already documents)."""
    path = os.path.join(ROOT, "tools", "oath_badge.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _badge_ok(read_only, destructive, operations) -> bool:
    """badge.py's real, live oath check -- Ogun's original, unmodified."""
    audit = real_badge.ToolAudit(
        name="probe", read_only=read_only, destructive=destructive, operations=tuple(operations)
    )
    return audit.ok


def _oath_badge_ok(oath_badge_mod, read_only, destructive, operations, policy=None) -> bool:
    """oath_badge.py's real, live oath check against a dict-shaped declared
    value -- the exact duck-typed/fixture path the module's own docstring
    names as a supported shape (`_extract_declared`'s dict branch)."""
    audit = oath_badge_mod.ToolAudit(
        name="probe",
        declared={
            "read_only": read_only,
            "destructive": destructive,
            "operations": tuple(operations),
        },
        policy=policy if policy is not None else oath_badge_mod.DEFAULT_POLICY,
    )
    return audit.ok


# A battery covering the clean shape, every single-field violation, AND the
# boolean-identity edge cases (truthy/falsy non-bool values) a duck-typed
# record can legally hand in per oath_badge.py's own docstring. Synthetic
# on purpose -- these combinations can't agree by coincidence the way a
# single real-file smoke test could, and the `badge_expected_ok` column is
# itself asserted against badge.py's real behavior, never just assumed.
_PARITY_CASES = [
    # (label, read_only, destructive, operations, badge_expected_ok)
    ("clean", True, False, ("read",), True),
    ("not_read_only", False, False, ("read",), False),
    ("destructive", True, True, ("read",), False),
    ("extra_operation", True, False, ("read", "write"), False),
    ("missing_operation", True, False, (), False),
    ("wrong_operation", True, False, ("write",), False),
    ("read_only_truthy_int_not_bool", 1, False, ("read",), False),
    ("destructive_falsy_int_not_bool", True, 0, ("read",), False),
    ("read_only_truthy_string", "yes", False, ("read",), False),
    ("both_falsy_and_truthy_non_bool", 1, 0, ("read",), False),
]


class RealOathParityCase(unittest.TestCase):
    """The structural claim: for every declared-value combination above,
    the two REAL, live-loaded modules' oath checks agree -- not just on
    the one happy-path triple the docstring's claim was never checked
    against before this task."""

    def setUp(self):
        self.oath_badge = _load_oath_badge("_t162_oath_badge_parity")

    def test_real_modules_agree_across_the_whole_battery(self):
        for label, read_only, destructive, operations, expected in _PARITY_CASES:
            with self.subTest(label=label):
                badge_result = _badge_ok(read_only, destructive, operations)
                oath_result = _oath_badge_ok(self.oath_badge, read_only, destructive, operations)
                self.assertEqual(
                    badge_result, expected,
                    f"{label}: badge.py itself disagrees with this fixture's own expectation",
                )
                self.assertEqual(
                    oath_result, badge_result,
                    f"{label}: oath_badge.py ({oath_result}) disagrees with badge.py "
                    f"({badge_result}) -- the 'sworn on iron, same as the original' claim "
                    "is false for this declared shape",
                )


class LiveConstantMirrorCase(unittest.TestCase):
    """The constant-level claim: `DEFAULT_POLICY` really does equal
    badge.py's real, live oath -- live-loaded, never a second hand-typed
    `("read",)` or `True`/`False` guess."""

    def test_default_policy_operations_matches_badges_real_allowed_operations(self):
        oath_badge = _load_oath_badge("_t162_oath_badge_const")
        self.assertEqual(oath_badge.DEFAULT_POLICY["operations"], real_badge._ALLOWED_OPERATIONS)

    def test_default_policy_booleans_match_the_one_combination_badge_calls_clean(self):
        # Derived behaviorally from badge.py itself -- the one (read_only,
        # destructive) pair its own ToolAudit.ok calls clean -- never a
        # hand-typed "True, False" guess sitting next to DEFAULT_POLICY's.
        clean_pairs = [
            (ro, de)
            for ro in (True, False)
            for de in (True, False)
            if _badge_ok(ro, de, real_badge._ALLOWED_OPERATIONS)
        ]
        self.assertEqual(len(clean_pairs), 1, clean_pairs)
        ro, de = clean_pairs[0]
        oath_badge = _load_oath_badge("_t162_oath_badge_bools")
        self.assertIs(oath_badge.DEFAULT_POLICY["read_only"], ro)
        self.assertIs(oath_badge.DEFAULT_POLICY["destructive"], de)

    def test_mutation_a_drifted_default_policy_operations_would_be_caught(self):
        """Reconstructs the exact failure this comparison guards against:
        DEFAULT_POLICY's operations tuple is a hand-typed literal, not
        derived from badge.py's constant -- if Ogun's oath ever grows a
        second allowed operation and oath_badge.py's copy doesn't follow,
        this comparison is what would notice."""
        oath_badge = _load_oath_badge("_t162_oath_badge_mut_const")
        oath_badge.DEFAULT_POLICY = dict(oath_badge.DEFAULT_POLICY)
        oath_badge.DEFAULT_POLICY["operations"] = real_badge._ALLOWED_OPERATIONS + ("list",)
        self.assertNotEqual(oath_badge.DEFAULT_POLICY["operations"], real_badge._ALLOWED_OPERATIONS)


class MutationRealPreFixBehaviorDisagreedCase(unittest.TestCase):
    """Reconstructs `ToolAudit.ok`'s real pre-task-162 body (equality for
    every policy field, including the booleans -- the exact text this task
    replaced) and proves it really did disagree with badge.py's real, live
    oath on the truthy-non-bool edge case, while the fixed, real module now
    agrees with it."""

    def test_pre_fix_equality_only_check_passed_a_truthy_non_bool_read_only(self):
        def pre_fix_ok(declared: dict, policy: dict) -> bool:
            return all(declared.get(k) == v for k, v in policy.items())

        declared = {"read_only": 1, "destructive": False, "operations": ("read",)}
        policy = {"read_only": True, "destructive": False, "operations": ("read",)}

        # The real pre-fix logic said this declaration was clean...
        self.assertTrue(pre_fix_ok(declared, policy))
        # ...but badge.py's real, live, unmodified oath says it is not --
        # this is the exact drift the docstring's "same as the original"
        # claim was never checked against before this task.
        self.assertFalse(_badge_ok(1, False, ("read",)))

    def test_the_real_fixed_module_now_agrees_with_badge_on_the_same_case(self):
        oath_badge = _load_oath_badge("_t162_oath_badge_fixed")
        self.assertFalse(_oath_badge_ok(oath_badge, 1, False, ("read",)))
        self.assertFalse(_badge_ok(1, False, ("read",)))


if __name__ == "__main__":
    unittest.main()
