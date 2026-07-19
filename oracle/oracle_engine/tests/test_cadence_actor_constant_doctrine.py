"""ROADMAP task 147. `fork_cadence.py`'s docstring says `star_cadence.py`
(task 38) is mirrored "line for line on purpose", and the chain of claims
runs on from there -- `issue_cadence.py` mirrors `fork_cadence.py`,
`release_cadence.py` mirrors both, and so on through 24 modules built
after `star_cadence.py`. Every one of those 24 parameterizes
`seal_*_prediction`'s `actor` default via a module-level `DEFAULT_ACTOR`
constant. `star_cadence.py` itself -- the file the whole chain traces
back to, cited by name as the shape to copy -- hardcoded the literal
`actor: str = "off-by-one"` directly in the signature instead, right up
until task 147. `test_star_cadence.py` checks the *value* the default
resolves to (`"off-by-one"`) but never how it gets there, so the one file
everyone claims to mirror was quietly the one file *not* holding the
shape its own descendants converged on -- the "claims a mirror, never
checked against the thing it mirrors" pattern tasks 136/137/141/146
already closed elsewhere, found here for the first time between
`star_cadence.py` and its own claimed descendants.

This module cross-checks, structurally, straight off every live
`*_cadence.py` file in this package (never a second hand-typed copy of
any of it): every one of them (barring `cadence.py`, which reads
BUILDLOG.md and does not share this 9-function shape at all) defines a
module-level `DEFAULT_ACTOR = "<literal>"` assignment, and its
`seal_*_prediction` function's `actor` parameter default is a bare `Name`
node referencing that constant -- never a hardcoded string literal.

Plus mutation-based hand-verification (the same before/after discipline
tasks 135-146 already hold their own checkers to): the checker is run
against a reconstruction of `star_cadence.py`'s own real, pre-task-147
text (hardcoded literal, no `DEFAULT_ACTOR`) and proven to flag it, then
against a synthetic module whose `seal_*_prediction` references a
`DEFAULT_ACTOR` name that is never actually assigned at module level
(dangling reference) and proven to flag that too, then the real, fixed
`star_cadence.py` is proven to pass clean today.
"""
from __future__ import annotations

import ast
import glob
import os
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine
_SRC_DIR = os.path.join(_ORACLE_ENGINE_ROOT, "src", "oracle_engine")

# Every *_cadence.py module sharing the fetch/load_snapshots/record_snapshot/
# _parse_ts/*_at_or_before/*_at_or_after/build_prediction/seal_*_prediction
# 9-function shape. `cadence.py` (task 36) is deliberately excluded: it
# reads BUILDLOG.md, not a live snapshot series, and no cadence module's
# docstring ever claims it mirrors `cadence.py` line for line.
CADENCE_FAMILY_FILES = sorted(
    p for p in glob.glob(os.path.join(_SRC_DIR, "*_cadence.py"))
)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _module_level_default_actor(tree: ast.Module) -> ast.Assign | None:
    """The top-level `DEFAULT_ACTOR = ...` assignment, or None if absent."""
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "DEFAULT_ACTOR"
        ):
            return node
    return None


def _seal_function(tree: ast.Module) -> ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("seal_") and node.name.endswith("_prediction"):
            return node
    return None


def _actor_default_node(seal_func: ast.FunctionDef) -> ast.AST | None:
    """The default-value AST node bound to the `actor` parameter, or None
    if `seal_func` has no `actor` parameter at all."""
    args = seal_func.args
    positional = args.posonlyargs + args.args
    defaults = args.defaults
    # defaults align to the LAST len(defaults) positional args.
    offset = len(positional) - len(defaults)
    for i, arg in enumerate(positional):
        if arg.arg == "actor":
            default_index = i - offset
            if default_index < 0:
                return None  # actor has no default at all
            return defaults[default_index]
    return None


def check_actor_default_is_named_constant(source: str) -> tuple[bool, str]:
    """True + reason iff `source`'s `seal_*_prediction` function's `actor`
    parameter default is a bare Name referencing a module-level
    `DEFAULT_ACTOR = "<literal>"` assignment. False + a reason string
    covering every way that can fail: no seal function, no actor param,
    a hardcoded literal default, or a dangling Name with no matching
    module-level assignment."""
    tree = ast.parse(source)
    seal_func = _seal_function(tree)
    if seal_func is None:
        return False, "no seal_*_prediction function found"
    default = _actor_default_node(seal_func)
    if default is None:
        return False, "seal_*_prediction has no actor parameter with a default"
    if not isinstance(default, ast.Name):
        return False, f"actor default is not a bare Name reference (got {ast.dump(default)})"
    if default.id != "DEFAULT_ACTOR":
        return False, f"actor default Name is {default.id!r}, not DEFAULT_ACTOR"
    assignment = _module_level_default_actor(tree)
    if assignment is None:
        return False, "actor default references DEFAULT_ACTOR but no such module-level assignment exists"
    if not (isinstance(assignment.value, ast.Constant) and isinstance(assignment.value.value, str)):
        return False, "DEFAULT_ACTOR is not assigned a bare string literal"
    return True, "ok"


class EveryCadenceFamilyModuleHoldsTheNamedConstantShape(unittest.TestCase):
    """The structural claim, checked against every live file in the
    family, not just the one pair task 147 happened to find broken."""

    def test_family_is_non_trivial(self):
        # Guard against a glob typo silently making every test below vacuous.
        self.assertGreaterEqual(len(CADENCE_FAMILY_FILES), 20)

    def test_every_family_module_uses_a_named_default_actor_constant(self):
        failures = []
        for path in CADENCE_FAMILY_FILES:
            ok, reason = check_actor_default_is_named_constant(_read(path))
            if not ok:
                failures.append(f"{os.path.basename(path)}: {reason}")
        self.assertEqual(
            failures,
            [],
            "every *_cadence.py module must define seal_*_prediction's actor "
            "default via a module-level DEFAULT_ACTOR constant:\n" + "\n".join(failures),
        )

    def test_star_cadence_default_actor_value_is_unchanged(self):
        # Regression pin: the fix backports the *pattern*, never the value.
        star_path = os.path.join(_SRC_DIR, "star_cadence.py")
        ok, reason = check_actor_default_is_named_constant(_read(star_path))
        self.assertTrue(ok, reason)
        tree = ast.parse(_read(star_path))
        assignment = _module_level_default_actor(tree)
        self.assertEqual(assignment.value.value, "off-by-one")


class MutationHandVerificationCase(unittest.TestCase):
    """Proves the checker actually bites -- against star_cadence.py's own
    real, pre-task-147 shape, and against a synthetic dangling reference --
    not just that it happens to pass the real, already-fixed files."""

    def test_checker_flags_star_cadences_real_pre_fix_shape(self):
        # Reconstructed verbatim from star_cadence.py's history before
        # task 147: no DEFAULT_ACTOR constant, actor hardcoded inline.
        pre_fix_source = '''
from __future__ import annotations

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 168
DEFAULT_CONFIDENCE = 0.6


def seal_star_prediction(
    now,
    ts,
    current_count,
    actor: str = "off-by-one",
    snapshots=None,
    ledger_module=None,
    **build_kwargs,
):
    pass
'''
        ok, reason = check_actor_default_is_named_constant(pre_fix_source)
        self.assertFalse(ok, "must flag a hardcoded literal actor default as non-conforming")
        self.assertIn("not a bare Name", reason)

    def test_checker_flags_a_dangling_default_actor_reference(self):
        # DEFAULT_ACTOR is referenced but never assigned at module level --
        # a different, subtler way the shape can be faked.
        dangling_source = '''
from __future__ import annotations


def seal_widget_prediction(
    now,
    ts,
    current_count,
    actor: str = DEFAULT_ACTOR,
    snapshots=None,
    ledger_module=None,
    **build_kwargs,
):
    pass
'''
        ok, reason = check_actor_default_is_named_constant(dangling_source)
        self.assertFalse(ok, "must flag a DEFAULT_ACTOR reference with no matching assignment")
        self.assertIn("no such module-level assignment", reason)

    def test_checker_passes_the_real_fixed_star_cadence_file(self):
        star_path = os.path.join(_SRC_DIR, "star_cadence.py")
        ok, reason = check_actor_default_is_named_constant(_read(star_path))
        self.assertTrue(ok, reason)

    def test_checker_passes_a_real_always_conforming_sibling(self):
        # fork_cadence.py never hardcoded the literal in the first place --
        # confirms the checker isn't only passing star_cadence.py by luck.
        fork_path = os.path.join(_SRC_DIR, "fork_cadence.py")
        ok, reason = check_actor_default_is_named_constant(_read(fork_path))
        self.assertTrue(ok, reason)


if __name__ == "__main__":
    unittest.main()
