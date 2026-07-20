#!/usr/bin/env python3
"""Task 121. Off-By-One counts the tool that counts everything else.

`tools/ritual_check.py` hand-wires 33 `check_*` functions into one hourly
block: each is called inside `run_ritual_check`, its result assigned to a
dict key, and that key printed as a line in `format_ritual_check`. Three
separate places a single typo or a forgotten wire-up can silently drop a
check from the hourly block -- no traceback, no error, just a missing line
nobody's reading closely enough to notice is gone. Task 118 found exactly
this shape of drift in a README's tool count; tasks 98-106 built running
checks for five design constraints that could each go stale the same way.
The one tool every hour actually depends on had never once checked its own
wiring.

This module reads `tools/ritual_check.py`'s own source with `ast` -- no
import, no execution of the module under audit, so a check with a real bug
in its body can't crash the check that's supposed to catch it being
unwired. It proves, for every top-level `check_*` function:

1. it is actually CALLED somewhere inside `run_ritual_check`'s body
   (`missing_from_run` otherwise -- defined but never wired in);
2. the variable it's assigned to actually appears as a VALUE in
   `run_ritual_check`'s own returned dict literal (`missing_from_dict`
   otherwise -- called, but its result never makes it out);
3. the dict key it lands under is actually REFERENCED (`result["key"]`)
   somewhere inside `format_ritual_check` (`missing_from_format`
   otherwise -- wired and returned, but silently never printed).

Two dict keys are structurally exempt from rule 3: `now` (an echoed
timestamp, not a check result) and `broken` (the aggregate exit-code flag
read by `__main__`, not a printed line of its own -- every check that
contributes to it already prints its own status line).

**CORRECTED:** the "32" above was "27" from the day this module shipped
(task 121) until a later pass caught it -- five more `check_*` functions
(including this module's own `check_ritual_completeness` fold-in and, most
recently, task 145's `check_toolkits_in_use`) were added to
`tools/ritual_check.py` afterward without this docstring's own count ever
being revisited, the same "true when written, never rechecked against the
thing it describes" shape this module exists to catch in its subject.
`claimed_check_count()` below extracts this claim from the live docstring
text (never a second hand-typed copy), so `tests/test_ritual_completeness_check.py`
can cross-check it against the real count and a future addition can't let
this number go stale silently again. **Updated to 33** the same hour task
168's `check_scribe_growth` was wired in -- the first real test of whether
that promise holds.

Usage:
    python3 tools/ritual_completeness_check.py check
"""
from __future__ import annotations

import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_RITUAL_CHECK_PATH = os.path.join(ROOT, "tools", "ritual_check.py")
RUN_FUNC_NAME = "run_ritual_check"
FORMAT_FUNC_NAME = "format_ritual_check"
EXEMPT_DICT_KEYS = {"now", "broken"}

CLAIMED_COUNT_PATTERN = re.compile(r"hand-wires (\d+) `check_\*` functions")


def claimed_check_count(doc: str | None = None) -> int:
    """Extract the self-reported check_* count from this module's own
    docstring's "hand-wires N `check_*` functions" sentence (or from a
    supplied doc string, for mutation-based hand-verification) -- never a
    second hand-typed copy of the number, so a stale claim can be caught by
    comparing this against the real, live count in tools/ritual_check.py
    instead of trusting the prose."""
    doc = __doc__ if doc is None else doc
    match = CLAIMED_COUNT_PATTERN.search(doc or "")
    if match is None:
        raise ValueError(
            "could not find a 'hand-wires N `check_*` functions' claim in the docstring"
        )
    return int(match.group(1))


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _check_function_names(tree: ast.Module) -> set:
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("check_")
    }


def _called_functions(func: ast.FunctionDef, wanted: set) -> dict:
    """{function_name: assigned_variable_name} for every `var =
    check_x(...)` assignment anywhere inside `func`'s own body -- walked,
    not just top-level statements, since `run_ritual_check` calls some
    checks (e.g. `check_vault_leak`) conditionally inside an `if`/`else`
    branch rather than unconditionally at the top level."""
    called = {}
    for stmt in ast.walk(func):
        if not isinstance(stmt, ast.Assign):
            continue
        if not isinstance(stmt.value, ast.Call):
            continue
        call_func = stmt.value.func
        if not isinstance(call_func, ast.Name) or call_func.id not in wanted:
            continue
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            continue
        called[call_func.id] = stmt.targets[0].id
    return called


def _return_dict(func: ast.FunctionDef) -> dict:
    """{dict_key: variable_name_or_None} for the dict literal in the last
    top-level `return {...}` inside `func`'s own body. Non-Name values
    (e.g. a literal or expression) map to None -- nothing to cross-check
    a variable against, but still a real key."""
    result = {}
    for stmt in func.body:
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Dict):
            for key_node, val_node in zip(stmt.value.keys, stmt.value.values):
                if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                    var_name = val_node.id if isinstance(val_node, ast.Name) else None
                    result[key_node.value] = var_name
    return result


def _printed_keys(func: ast.FunctionDef) -> set:
    """Every string key subscripted off a variable literally named
    `result` anywhere inside `func` (loops, branches, comprehensions --
    walked, not just top-level statements, since format_ritual_check
    reads `result[...]` inside for-loops and if/else branches)."""
    keys = set()
    for node in ast.walk(func):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "result"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            keys.add(node.slice.value)
    return keys


def compute_ritual_completeness(source_path: str | None = None) -> dict:
    source_path = source_path or DEFAULT_RITUAL_CHECK_PATH
    with open(source_path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=source_path)

    check_functions = _check_function_names(tree)
    run_func = _find_function(tree, RUN_FUNC_NAME)
    format_func = _find_function(tree, FORMAT_FUNC_NAME)

    if run_func is None or format_func is None:
        return {
            "clean": False,
            "missing_from_run": sorted(check_functions),
            "missing_from_dict": [],
            "missing_from_format": [],
            "error": f"could not find {RUN_FUNC_NAME}/{FORMAT_FUNC_NAME} in {source_path}",
        }

    called = _called_functions(run_func, check_functions)
    missing_from_run = sorted(check_functions - called.keys())

    return_dict = _return_dict(run_func)
    var_to_key = {v: k for k, v in return_dict.items() if v is not None}
    missing_from_dict = sorted(
        fname for fname, var in called.items() if var not in var_to_key
    )

    printed = _printed_keys(format_func)
    checked_keys = {k for k in return_dict if k not in EXEMPT_DICT_KEYS}
    missing_from_format = sorted(checked_keys - printed)

    clean = not (missing_from_run or missing_from_dict or missing_from_format)
    return {
        "clean": clean,
        "missing_from_run": missing_from_run,
        "missing_from_dict": missing_from_dict,
        "missing_from_format": missing_from_format,
    }


def format_ritual_completeness(result: dict) -> str:
    if result["clean"]:
        return "ritual completeness: clean (every check_* function is called, returned, and printed)"
    parts = []
    if result["missing_from_run"]:
        parts.append(f"never called in {RUN_FUNC_NAME}: {', '.join(result['missing_from_run'])}")
    if result["missing_from_dict"]:
        parts.append(f"called but dropped from the return dict: {', '.join(result['missing_from_dict'])}")
    if result["missing_from_format"]:
        parts.append(f"returned but never printed in {FORMAT_FUNC_NAME}: {', '.join(result['missing_from_format'])}")
    return "ritual completeness: BROKEN -- " + "; ".join(parts)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = compute_ritual_completeness()
    print(format_ritual_completeness(out))
    sys.exit(0 if out["clean"] else 1)
