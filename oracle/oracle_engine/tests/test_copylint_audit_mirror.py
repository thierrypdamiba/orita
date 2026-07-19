"""ROADMAP backlog (unclosed as of task 145). `oracle_engine/copylint.py`'s
`lint_claim` docstring makes a direct claim about a sibling module it has
never been cross-checked against:

    "Mirrors `fencepost/seam_engine/audit.py`'s discipline exactly: a pure,
    deterministic function that grades a claim against a fixed law, returns
    a `checks` list of `(label, passed)` pairs, and a caller (`render_call`)
    that refuses to produce any output at all if the claim doesn't clear
    the bar"

and, on `lint_claim` itself:

    "same shape as `audit.py`'s `_audit_primary`"

`test_copylint.py` (task 33) is thorough about the lint outcomes (which
claims get rejected, which pass) but never once opens `audit.py` -- the
actual sibling this module swears to mirror. The claim happens to be true
today (confirmed by hand below) but nothing tied it to `audit.py`'s live
text, exactly the "claims a mirror, never checked against the thing it
mirrors" shape tasks 136/137/141 already closed twice in Fencepost and once
in Fencepost's own combined_scan.py -- found here for the first time in the
Oracle Desk's copylint module.

This module cross-checks, structurally, straight off both files' live
source (never a second hand-typed copy of either function's shape):

1. `_audit_primary` (fencepost/seam_engine/src/seam_engine/audit.py) and
   `lint_claim` (oracle_engine/copylint.py) each build a local `checks`
   list literal whose every element is a 2-tuple -- the literal
   `(label, passed)` pairs the docstring names.
2. Both derive their overall pass/fail the same way: `all(x for _, x in
   <that checks list>)` -- inline in `_audit_primary` (feeding its
   `verdict`), and in `LintResult.ok` for `lint_claim` (`checks` is
   returned on the dataclass and reduced by its caller instead of inline,
   the one structural difference between "audit after the fact" and
   "lint before it renders" -- but the reduction expression itself is
   character-for-character the same shape).
3. `render_call` validates before it builds a single character of output:
   its first statement is a bare call to `enforce_copy`, never anything
   that could produce a partial render first.

Plus mutation-based hand-verification (the same before/after discipline
tasks 135-142 already hold their own checkers to): each structural check is
run against a deliberately mutated COPY of the real source text and proven
to flip from clean to broken, then the real, unmutated file is proven to
still pass clean.
"""
from __future__ import annotations

import ast
import os
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine
_ORACLE_ROOT = os.path.dirname(_ORACLE_ENGINE_ROOT)  # oracle
_REPO_ROOT = os.path.dirname(_ORACLE_ROOT)  # repo root

COPYLINT_PATH = os.path.join(_ORACLE_ENGINE_ROOT, "src", "oracle_engine", "copylint.py")
AUDIT_PATH = os.path.join(
    _REPO_ROOT, "fencepost", "seam_engine", "src", "seam_engine", "audit.py"
)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _function_node(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise LookupError(f"no top-level function named {name!r}")


def _property_node(tree: ast.AST, class_name: str, member_name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == member_name:
                    return item
    raise LookupError(f"no {class_name}.{member_name} found")


def _checks_list_arities(func_node: ast.FunctionDef):
    """Find a local `checks = [...]` (bare or annotated) assignment inside
    func_node's body and return the tuple-arity of every element (an int,
    or None for a non-tuple element). Returns None if no such assignment
    exists at all -- distinct from "found but empty"."""
    for node in ast.walk(func_node):
        target = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        if isinstance(target, ast.Name) and target.id == "checks" and isinstance(value, ast.List):
            return [len(elt.elts) if isinstance(elt, ast.Tuple) else None for elt in value.elts]
    return None


def _all_reduction_source(node: ast.AST):
    """Search node for an `all(<x> for _, <x> in <iterable>)`-shaped
    generator reduction and return the unparsed source text of <iterable>,
    or None if no such reduction is present."""
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Name)
            and sub.func.id == "all"
            and len(sub.args) == 1
            and isinstance(sub.args[0], ast.GeneratorExp)
        ):
            gen = sub.args[0]
            comp = gen.generators[0]
            if isinstance(comp.target, ast.Tuple) and len(comp.target.elts) == 2:
                return ast.unparse(comp.iter)
    return None


def _first_statement_is_bare_call_to(func_node: ast.FunctionDef, callee_name: str) -> bool:
    """True iff the first REAL statement in func_node's body (skipping a
    leading docstring, if any) is a bare call to callee_name -- i.e. the
    validation runs before anything else, docstrings aside."""
    body = func_node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    if not body:
        return False
    first = body[0]
    return (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Call)
        and isinstance(first.value.func, ast.Name)
        and first.value.func.id == callee_name
    )


class RealFilesShareTheClaimedShapeCase(unittest.TestCase):
    """`lint_claim` docstring: 'same shape as `audit.py`'s `_audit_primary`'
    -- checked against the two real, live files, not trusted as prose."""

    def setUp(self):
        self.audit_tree = ast.parse(_read(AUDIT_PATH))
        self.copylint_tree = ast.parse(_read(COPYLINT_PATH))
        self.audit_primary = _function_node(self.audit_tree, "_audit_primary")
        self.lint_claim = _function_node(self.copylint_tree, "lint_claim")

    def test_audit_primary_builds_a_checks_list_of_2_tuples(self):
        arities = _checks_list_arities(self.audit_primary)
        self.assertIsNotNone(arities, "_audit_primary must build a local `checks` list")
        self.assertGreater(len(arities), 0)
        self.assertTrue(
            all(a == 2 for a in arities),
            f"_audit_primary's checks list must be all (label, passed) 2-tuples, got arities {arities}",
        )

    def test_lint_claim_builds_a_checks_list_of_2_tuples(self):
        arities = _checks_list_arities(self.lint_claim)
        self.assertIsNotNone(arities, "lint_claim must build a local `checks` list")
        self.assertGreater(len(arities), 0)
        self.assertTrue(
            all(a == 2 for a in arities),
            f"lint_claim's checks list must be all (label, passed) 2-tuples, got arities {arities}",
        )

    def test_both_checks_lists_agree_on_the_2_tuple_shape(self):
        # Cross-check, not a repeated assertion: each side is independently
        # extracted from its own live file above; here they are compared to
        # each other, the literal "same shape" claim in the docstring.
        audit_arities = set(_checks_list_arities(self.audit_primary))
        lint_arities = set(_checks_list_arities(self.lint_claim))
        self.assertEqual(
            audit_arities,
            lint_arities,
            "_audit_primary and lint_claim no longer build checks lists of "
            "the same tuple shape -- the docstring's 'same shape' claim no "
            "longer holds against the live files",
        )

    def test_audit_primary_reduces_its_verdict_via_all_over_its_own_checks(self):
        iterable_text = _all_reduction_source(self.audit_primary)
        self.assertEqual(
            iterable_text,
            "checks",
            "_audit_primary must derive its verdict via all(x for _, x in checks) "
            "over the exact checks list it just built",
        )

    def test_lint_result_ok_reduces_via_all_over_self_checks(self):
        ok_property = _property_node(self.copylint_tree, "LintResult", "ok")
        iterable_text = _all_reduction_source(ok_property)
        self.assertEqual(
            iterable_text,
            "self.checks",
            "LintResult.ok must derive pass/fail via all(x for _, x in self.checks) "
            "-- the same all()-over-checks reduction _audit_primary uses inline",
        )

    def test_render_call_validates_before_building_any_output(self):
        render_call = _function_node(self.copylint_tree, "render_call")
        self.assertTrue(
            _first_statement_is_bare_call_to(render_call, "enforce_copy"),
            "render_call's first statement must be a bare call to enforce_copy -- "
            "'rejected before it can render' checked structurally, not just claimed",
        )


class MutationHandVerificationCase(unittest.TestCase):
    """Prove each structural check above actually bites: run it against a
    deliberately mutated COPY of the real source text and show it flips
    from clean to broken, then confirm the real, unmutated file still
    passes clean."""

    def setUp(self):
        self.copylint_src = _read(COPYLINT_PATH)
        self.audit_src = _read(AUDIT_PATH)

    def test_mutating_lint_claims_checks_tuple_arity_breaks_the_shape_match(self):
        real_snippet = (
            '        (\n'
            '            "confidence is labeled",\n'
            '            confidence is not None,\n'
            '        ),\n'
            '    ]'
        )
        mutated_snippet = (
            '        (\n'
            '            "confidence is labeled",\n'
            '            confidence is not None,\n'
            '            None,\n'
            '        ),\n'
            '    ]'
        )
        self.assertEqual(
            self.copylint_src.count(real_snippet),
            1,
            "expected exactly one occurrence of the real 3-line checks-tuple "
            "tail to mutate -- copylint.py's source has moved out from under "
            "this test",
        )
        mutated_src = self.copylint_src.replace(real_snippet, mutated_snippet, 1)

        mutated_tree = ast.parse(mutated_src)
        mutated_lint_claim = _function_node(mutated_tree, "lint_claim")
        mutated_arities = _checks_list_arities(mutated_lint_claim)
        self.assertIn(
            3,
            mutated_arities,
            "the mutated checks list should now carry a 3-tuple element",
        )
        self.assertFalse(
            all(a == 2 for a in mutated_arities),
            "the mutated checks list should no longer be all 2-tuples -- the "
            "checker must flag the drift",
        )

        # And the real, unmutated file still passes clean.
        real_tree = ast.parse(self.copylint_src)
        real_arities = _checks_list_arities(_function_node(real_tree, "lint_claim"))
        self.assertTrue(all(a == 2 for a in real_arities))

    def test_mutating_lint_results_ok_reduction_breaks_the_all_over_checks_match(self):
        real_snippet = "return all(passed for _, passed in self.checks)"
        mutated_snippet = "return any(passed for _, passed in self.checks)"
        self.assertEqual(self.copylint_src.count(real_snippet), 1)
        mutated_src = self.copylint_src.replace(real_snippet, mutated_snippet, 1)

        mutated_tree = ast.parse(mutated_src)
        mutated_ok = _property_node(mutated_tree, "LintResult", "ok")
        self.assertIsNone(
            _all_reduction_source(mutated_ok),
            "an `any(...)`-reworded LintResult.ok must no longer be detected "
            "as an all()-over-checks reduction",
        )

        real_tree = ast.parse(self.copylint_src)
        real_ok = _property_node(real_tree, "LintResult", "ok")
        self.assertEqual(_all_reduction_source(real_ok), "self.checks")

    def test_mutating_audit_primarys_verdict_reduction_breaks_the_match(self):
        real_snippet = "all(ok for _, ok in checks)"
        mutated_snippet = "all(ok for _, ok in checks[:1])"
        self.assertEqual(
            self.audit_src.count(real_snippet),
            1,
            "expected exactly one occurrence of _audit_primary's real verdict "
            "reduction to mutate -- audit.py's source has moved out from "
            "under this test",
        )
        mutated_src = self.audit_src.replace(real_snippet, mutated_snippet, 1)

        mutated_tree = ast.parse(mutated_src)
        mutated_primary = _function_node(mutated_tree, "_audit_primary")
        self.assertNotEqual(
            _all_reduction_source(mutated_primary),
            "checks",
            "an all(...checks[:1]) rewording must no longer reduce over the "
            "plain checks list -- the checker must see the iterable changed",
        )

        real_tree = ast.parse(self.audit_src)
        real_primary = _function_node(real_tree, "_audit_primary")
        self.assertEqual(_all_reduction_source(real_primary), "checks")

    def test_mutating_render_call_to_build_output_before_validating_breaks_the_order_check(self):
        real_snippet = (
            "    enforce_copy(claim, confidence)\n"
            '    return f"[{ts}] {actor}: \\"{claim}\\" (confidence {confidence:.2f})"'
        )
        mutated_snippet = (
            '    text = f"[{ts}] {actor}: \\"{claim}\\" (confidence {confidence:.2f})"\n'
            "    enforce_copy(claim, confidence)\n"
            "    return text"
        )
        self.assertEqual(
            self.copylint_src.count(real_snippet),
            1,
            "expected exactly one occurrence of render_call's real body to "
            "mutate -- copylint.py's source has moved out from under this test",
        )
        mutated_src = self.copylint_src.replace(real_snippet, mutated_snippet, 1)

        mutated_tree = ast.parse(mutated_src)
        mutated_render_call = _function_node(mutated_tree, "render_call")
        self.assertFalse(
            _first_statement_is_bare_call_to(mutated_render_call, "enforce_copy"),
            "a render_call that builds its output text before validating must "
            "fail the 'validates before it renders' structural check",
        )

        real_tree = ast.parse(self.copylint_src)
        real_render_call = _function_node(real_tree, "render_call")
        self.assertTrue(_first_statement_is_bare_call_to(real_render_call, "enforce_copy"))


if __name__ == "__main__":
    unittest.main()
