#!/usr/bin/env python3
"""Task 671. Generalizes an AST-hash sweep off-by-one and nisaba have both
run BY HAND, ad hoc, at least four separate times (BUILDLOG tasks 508, 509,
513, 515) into a running check, the same graduation `duplicate_regex_check.py`
(task 397) already made for its own narrower sibling bug shape (a hand-typed
`re.compile(...)` pattern with nothing importing it). Those four manual
sweeps found: a byte-identical `_parse(ts)` ISO-timestamp parser in three
files (509), a byte-identical `find_violations()`/`clear_cache()` memoize
pair in five files plus a `_iter_public_files` walk under a different name
in a sixth (513), two more siblings of that same shape task 513's own
same-name-only hash missed (515), and a `_is_negated_or_predictive` copy in
three more (569, cited in BUILDLOG task 569's own docstring as explicitly
deferred "riskier" work at the time). Each was real, each shipped a real
consolidation, and each was only found because someone happened to re-run
the sweep by hand that hour. `duplicate_regex_check.py`'s own docstring
already drew the lesson once, for regex literals specifically: "at some
point the pattern itself is the finding, not any one instance of it." The
identical sentence applies to whole function bodies, and nothing has ever
stood watch for it between manual sweeps.

Scope, first version: this checker scanned only `tools/*.py` (skipping
`__init__.py` and every `tests/`-shaped path) because that is exactly
where all four manual sweeps this docstring cites found their real
duplicates. `duplicate_regex_check.py`'s own `tools/*.py` and
`oracle_engine` globs were each widened in a LATER task (418, 445), not
its first -- the same earn-it-narrow-first shape this checker followed
on purpose, not a shortcut skipped by accident. `fencepost/RECIPES/*/
detector.py` stayed OUT of scope on purpose and remains out of scope
today: it is full of *legitimately* parallel functions (every recipe's
own `load_commits`/`load_issues`/`run_recipe_scan` follows the same
documented shape on purpose, per `CONTRIBUTING.md`'s own recipe template)
that would drown this checker in false positives.

Task 674 widened the scan, the deferred future task this docstring's
prior version named by name: `fencepost/seam_engine/src/seam_engine/*.py`
and `oracle/oracle_engine/src/oracle_engine/*.py` joined `tools/*.py`,
mirroring `duplicate_regex_check.py`'s own real widening (tasks 418, 445)
exactly. The live tree's first-ever cross-directory run found exactly one
real hit, immediately: `_dynamic_import_target` -- an `ast.Call` reader
that recognizes `importlib.import_module(...)`/bare `import_module(...)`/
`__import__(...)` and returns a literal string first argument -- is
defined byte-identically in both `tools/network_boundary_check.py` and
`fencepost/seam_engine/src/seam_engine/recipes.py`. Not a bug: `network_
boundary_check.py`'s own docstring already named this exact second copy
by path, from the day the underlying dynamic-import gap was closed
("`fencepost/seam_engine/src/seam_engine/recipes.py`'s own independent
copy of this deny-list logic had the identical gap, closed the same
task") -- confirmed, not discovered, that this is a deliberate two-copy
law, not an oversight. Real reason it stays two copies rather than one
shared import: `network_boundary_check.py` is itself one of the thirty
files it watches for "no network import" (its own file is in
`EXPECTED_TODAY`) and CI's lean root job (task 404's
own boundary, `.github/workflows/dawn-run.yml`'s `the-oath` job)
installs only PyYAML -- no `uv`, no `seam_engine` package on that
interpreter's path at all. Importing `seam_engine.recipes` from a
`tools/*.py` file would either break that job outright or force it to
grow a real dependency it was deliberately kept lean to avoid; reading
`fencepost/seam_engine/src/seam_engine/` by AST off the filesystem (as
`network_boundary_check.py` and this checker both already do, extensively)
crosses no such boundary. Seeded as this checker's first-ever
`_ALLOWED_DUPLICATES` entry, keyed on the real hash, named by path in the
dict's own comment -- the same citation discipline `duplicate_regex_
check.py`'s own `_CLOSES_RE`/closing-keyword-grammar exception already
set.

For every top-level and class-level `def`/`async def` in a scanned file,
hashes (sha256 hex digest, task 674 -- the raw `ast.dump` text of a real
function easily runs past a thousand characters, unreadable as an
`_ALLOWED_DUPLICATES` dict key) `ast.dump(node.body, annotate_fields=
False)` of the BODY only (the statements after the signature; a leading
bare-string docstring `Expr` is stripped first) -- never the function's
own name, since task 513's own
real finding (`arcade_hero_check.py`'s `_iter_scan_files` vs. five
siblings' `_iter_public_files`) was invisible to a name-sensitive hash by
construction. `ast.dump` with `annotate_fields=False` drops line numbers
and column offsets on its own (they are `attributes`, never `fields`), so
two functions at different lines in different files with byte-identical
control flow hash identically without any manual stripping. A minimum
body size (`_MIN_BODY_NODES`, counts every AST node in the body via `ast.
walk`, not just top-level statements) excludes trivial shapes -- a bare
`return None`, a two-line `if __name__ == "__main__":` dispatch, a single
`raise NotImplementedError` -- that are expected to recur across a house
style and were never what any of the four manual sweeps this docstring
cites were pointing at.

A second, separate exclusion (`_is_thin_delegator`) caught live on this
checker's own first real run against the live tree, before it shipped:
a single-statement `return module.func(...)` body -- exactly the shape
task 570's own `_find_violations_uncached` wrappers and task 569's own
consolidated `_is_negated_or_predictive` wrappers already are, on
purpose -- can still hash identically across files even though each
file's own local arguments (`_PATTERNS`, `_iter_scan_files`, ...) are
genuinely distinct objects, because an `ast.Name` node only ever carries
the local NAME TEXT, not what it resolves to. The first live run of this
checker (pre-fix) flagged exactly these three already-consolidated,
already-documented wrapper shapes as false positives; `_is_thin_delegator`
closes that gap by excluding any body that is nothing but one delegating
return/call, regardless of size, while never excluding a genuinely
multi-statement duplicated body (every real historical bug this checker
generalizes had more than one statement). See its own docstring for the
full reasoning. Any body at or above `_MIN_BODY_NODES` that survives both
exclusions and hashes identically across two or more distinct files,
under any name(s), is exactly the shape those four tasks kept finding by
hand.

Usage:
    python3 tools/duplicate_function_check.py check
"""
from __future__ import annotations

import ast
import glob
import hashlib
import os
import sys
from collections.abc import Iterator
from typing import TypedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan_files  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

_TOOLS_GLOB = "tools/*.py"
# Task 674: joined tools/*.py, mirroring duplicate_regex_check.py's own
# real widening history (tasks 418, 445) for its narrower sibling bug.
_SEAM_ENGINE_GLOB = "fencepost/seam_engine/src/seam_engine/*.py"
_ORACLE_ENGINE_GLOB = "oracle/oracle_engine/src/oracle_engine/*.py"
_SKIP_BASENAMES = {"__init__.py"}

# A function's body needs at least this many total AST nodes (via
# ast.walk over the body statements) before a duplicate is worth
# reporting -- below this, house-style boilerplate (a bare `return None`,
# a `raise NotImplementedError`, a two-line CLI dispatch) recurs on
# purpose and is not the bug this checker exists to catch.
_MIN_BODY_NODES = 12

# Body-hash -> the exact set of files it is allowed to be locally defined
# in more than once. Keyed on the hash (the actual identifying fact),
# same convention as duplicate_regex_check.py's own _ALLOWED_DUPLICATES.
#
# Task 674: the widened scan's first-ever cross-directory run surfaced
# this checker's first real entry, immediately. `_dynamic_import_target`
# (recognizes `importlib.import_module(...)`/bare `import_module(...)`/
# `__import__(...)` and returns a literal-string first argument) is
# defined byte-identically in `tools/network_boundary_check.py` and
# `fencepost/seam_engine/src/seam_engine/recipes.py`. Confirmed, not
# discovered: `network_boundary_check.py`'s own docstring already named
# this exact second copy by path, from the day the underlying dynamic-
# import gap was closed ("recipes.py's own independent copy of this deny-
# list logic had the identical gap, closed the same task"). Stays two
# copies on purpose: `network_boundary_check.py` is itself one of the
# thirty files it watches for "no network import," and CI's lean root
# job (task 404, `.github/workflows/dawn-run.yml`'s `the-oath` job)
# installs only PyYAML -- no `uv`, no `seam_engine` package anywhere on
# that interpreter's path. Importing `seam_engine.recipes` from a
# `tools/*.py` file would either break that job or force it to grow a
# real dependency kept lean on purpose; reading `seam_engine`'s source by
# AST off the filesystem (as both files already do, extensively) crosses
# no such boundary.
_ALLOWED_DUPLICATES: dict[str, frozenset[str]] = {
    "3182e07480f334cffbe8b59c2ce16265b134f21f15db8dbfd172d849697c2217": frozenset({
        os.path.join("tools", "network_boundary_check.py"),
        os.path.join("fencepost", "seam_engine", "src", "seam_engine", "recipes.py"),
    }),
}


def _iter_scanned_files(orita_dir: str) -> Iterator[str]:
    for rel_glob in (_TOOLS_GLOB, _SEAM_ENGINE_GLOB, _ORACLE_ENGINE_GLOB):
        for path in sorted(glob.glob(os.path.join(orita_dir, rel_glob))):
            if os.path.basename(path) in _SKIP_BASENAMES:
                continue
            yield path


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    """Drop a leading bare-string docstring `Expr` -- two functions with
    identical control flow but different explanatory docstrings are still
    the same duplicate-logic bug; keeping the docstring in the hash would
    hide that."""
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _is_thin_delegator(body: list[ast.stmt]) -> bool:
    """True when `body` is EXACTLY one `return <call>` (or a bare `<call>`
    expression statement) whose callee is `some_name.attr(...)` -- a
    single-line hand-off to an already-imported shared function, task
    570's own documented pattern (`arcade_hero_check._find_violations_
    uncached`/`no_grading_check._find_violations_uncached` both wrap
    `scan_files.find_pattern_violations(...)`, task 569's `_is_negated_or_
    predictive` wraps `sentence_negation.is_negated_or_predictive(...)`).
    Two files' delegators can hash identical even though they resolve to
    genuinely different per-file arguments (`_PATTERNS`, `_iter_scan_
    files`, ...) -- an `ast.Name` node only ever carries the LOCAL name
    text, not what it's bound to, so `_iter_scan_files` reads the same in
    both files' dumps even though each file's own `_iter_scan_files` is a
    distinct object. This is the mirror image of `duplicate_regex_check.
    py`'s own distinction ("a file that only ever IMPORTS a shared name
    has none of these... importing a name binds it, it does not call
    re.compile() again") -- there, importing proves no local duplicate
    exists; here, delegating to a shared call proves the same thing even
    though the wiring is spelled out inline rather than bound by import.
    A body with more than this one statement is never excluded here, no
    matter what its first statement is -- every real historical bug this
    checker generalizes (`_parse(ts)`, `_iter_public_files`, the pre-
    consolidation `_is_negated_or_predictive`) had multiple statements
    (loops, conditionals), not a single delegating return."""
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Return) and stmt.value is not None:
        call = stmt.value
    elif isinstance(stmt, ast.Expr):
        call = stmt.value
    else:
        return False
    return isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)


def _function_bodies(path: str) -> list[tuple[str, str, int]]:
    """Every `(name, body_hash, lineno)` this file defines for a top-level
    or class-level `def`/`async def` whose body (docstring stripped) has
    at least `_MIN_BODY_NODES` AST nodes. `body_hash` is a sha256 hex
    digest of the body's `ast.dump`, not the raw dump text itself (task
    674: the raw dump of a real function easily runs past a thousand
    characters, unreadable and unwieldy as a `_ALLOWED_DUPLICATES` dict
    key -- a real hash is exactly what this checker's own name and
    docstring already claimed it computes)."""
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except (UnicodeDecodeError, OSError):
        return []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return []

    found: list[tuple[str, str, int]] = []

    def _visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = _strip_docstring(child.body)
                if not _is_thin_delegator(body):
                    node_count = sum(1 for _ in ast.walk(ast.Module(body=body, type_ignores=[])))
                    if node_count >= _MIN_BODY_NODES:
                        dumped = ast.dump(ast.Module(body=body, type_ignores=[]), annotate_fields=False)
                        body_hash = hashlib.sha256(dumped.encode("utf-8")).hexdigest()
                        found.append((child.name, body_hash, child.lineno))
                # Nested functions (closures) count too -- task 513's own
                # `_take(flag)`-shaped closures are exactly this case.
                _visit(child)
            elif isinstance(child, ast.ClassDef):
                _visit(child)

    _visit(tree)
    return found


class Violation(TypedDict):
    body_hash: str
    locations: list[tuple[str, str, int]]


def _find_violations_uncached(orita_dir: str = DEFAULT_ORITA_DIR) -> list[Violation]:
    """Read-only, local-filesystem-only `ast` scan (no import, no
    execution, no network) of every `tools/*.py`,
    `fencepost/seam_engine/src/seam_engine/*.py`, and
    `oracle/oracle_engine/src/oracle_engine/*.py` file (task 674 widened
    past `tools/*.py` alone) for a function body (name-blind, docstring-
    stripped) defined identically in two or more distinct files. Returns
    a list of violation records, empty when every duplicate body in the
    live tree is either a real single definition or a seeded, documented
    exception."""
    by_hash: dict[str, list[tuple[str, str, int]]] = {}
    for path in _iter_scanned_files(orita_dir):
        rel = os.path.relpath(path, orita_dir)
        for name, body_hash, lineno in _function_bodies(path):
            by_hash.setdefault(body_hash, []).append((rel, name, lineno))

    violations: list[Violation] = []
    for body_hash, locations in by_hash.items():
        files = {rel for rel, _name, _lineno in locations}
        if len(files) < 2:
            continue
        allowed = _ALLOWED_DUPLICATES.get(body_hash)
        if allowed is not None and files <= allowed:
            continue
        violations.append({
            "body_hash": body_hash,
            "locations": sorted(locations),
        })
    violations.sort(key=lambda v: v["locations"])
    return violations


find_violations, clear_cache = scan_files.path_memoize(_find_violations_uncached, DEFAULT_ORITA_DIR)


def format_violations(violations: list[Violation]) -> str:
    if not violations:
        return "duplicate function check: clean -- every scanned function body (>=12 AST nodes, across tools/*.py, fencepost/seam_engine/src/seam_engine/*.py, oracle/oracle_engine/src/oracle_engine/*.py) is either unique or a seeded exception"
    lines = [f"duplicate function check: {len(violations)} DUPLICATE BODY/BODIES FOUND -- identical logic, no shared import backing it"]
    for v in violations:
        lines.append(f"  hash {v['body_hash'][:16]}...")
        for rel, name, lineno in v["locations"]:
            lines.append(f"    {rel}:{lineno} ({name})")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
