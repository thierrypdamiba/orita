#!/usr/bin/env python3
"""Task 397. Off-By-One stops finding these one at a time.

Tasks 389, 390, 393, 394, and 396 each found the same shape of bug by
hand -- a `re.compile(...)` pattern hand-typed into a `RECIPES/*/detector.py`
file, its own comment claiming to "mirror" or "reuse verbatim" a pattern
defined somewhere else, with nothing ever actually importing it. Five
grep-by-hand sweeps later, task 396's own private journal (`vault/off-by-
one/journal/0082`) said the honest thing: "at some point the pattern
itself is the finding, not any one instance of it." This module is that
running check -- the same graduation `star_covenant_check.py` (task 99)
and `vault_leak_check.py` (task 98) already made, from an intention
narrated each hour to a script that proves it.

It reads every `fencepost/RECIPES/*/detector.py`, every `fencepost/
seam_engine/src/seam_engine/*.py`, and every `tools/*.py` (skipping tests
and `__init__.py`) with `ast` -- no import, no execution, so a real bug in
a detector's own body can't crash the check that's supposed to catch its
regex hygiene. For every `re.compile(...)` call whose first argument is a
literal string, it records the pattern text and the file it was found in.
Any pattern text that is DEFINED LOCALLY (not merely referenced by name
after an import) in two or more distinct files is exactly the bug this
campaign kept finding: a claimed mirror with nothing backing it.

Task 418: the `tools/*.py` glob was missing entirely until this task --
this checker never scanned the very directory it lives in. A live sweep
of that blind spot turned up the identical bug shape, undetected, in
`tools/`: a sentence-boundary splitter hand-typed two different ways
across six files, a negation-cue word list byte-identical between two
files, a `YYYY-MM-DD.md` filename matcher byte-identical between two
files, a `**Petitioner:**` line matcher byte-identical between two files
under two different local names, and six of `star_covenant_check.py`'s
own star/follow-begging shapes copied verbatim into `petition_limits_
check.py`. All of it moved into `tools/text_patterns.py`, one real
definition per pattern, with every one of those files now importing it
instead of retyping it (mirrors this same campaign's own fix shape for
`fencepost/seam_engine/closing_keywords.py`, `thanks.py`, `references.py`,
etc.).

One pair is a deliberate, already-documented exception, not a bug:
`_CLOSES_RE` in `issue-closed-pr-still-open` and `merged-pr-issue-still-
open` is textually identical between those two files on purpose --
`tools/closing_keyword_guard.py`'s own docstring already names this pair
explicitly as a real, working, narrower grammar that intentionally stays
a two-copy law (task 394's own closing note ruled it out the same way).
It is seeded below as `_ALLOWED_DUPLICATES` so this check does not cry
wolf on a duplicate the town already decided, in writing, to keep.
`tools/text_patterns.py` needs no such exception: every file that now
uses one of its constants (e.g. `text_patterns.SENTENCE_BOUNDARY_LOOSE`)
references it by attribute lookup, never calls `re.compile(...)` again
locally -- `_local_re_compile_patterns()` only ever counts an actual
`re.compile(...)` call, so each of task 418's shared patterns is defined
locally in exactly one file (`text_patterns.py` itself) and correctly
never flags as a duplicate.

Usage:
    python3 tools/duplicate_regex_check.py check
"""
from __future__ import annotations

import ast
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

_RECIPES_GLOB = "fencepost/RECIPES/*/detector.py"
_SEAM_ENGINE_GLOB = "fencepost/seam_engine/src/seam_engine/*.py"
_TOOLS_GLOB = "tools/*.py"
_SKIP_BASENAMES = {"__init__.py"}

# Pattern text -> the exact set of files it is allowed to be locally
# defined in more than once. Anything not listed here that shows up
# defined locally in 2+ files is a real violation. Keyed on the pattern
# TEXT (not a file pair) because that is the actual identifying fact a
# duplicate-regex bug turns on -- two files agreeing on a name means
# nothing if their patterns differ, and two files disagreeing on a name
# means nothing if their patterns (the live behavior) are identical.
_ALLOWED_DUPLICATES: dict[str, frozenset[str]] = {
    r"\b(?:closes?|fixes?|resolves?)\s+#(\d+)\b": frozenset({
        os.path.join("fencepost", "RECIPES", "issue-closed-pr-still-open", "detector.py"),
        os.path.join("fencepost", "RECIPES", "merged-pr-issue-still-open", "detector.py"),
    }),
    # Task 418: widening the scan to tools/*.py surfaced this pair for the
    # first time. seam_engine.closing_keywords's own docstring already
    # rules deliberately does NOT import tools/closing_keyword_guard.py --
    # seam_engine must stay portable/forkable and not depend on this
    # parent repo's own tools/ directory, so it re-states the identical
    # grammar as a documented, intentional mirror instead of an import.
    # A real, working two-copy law, same shape as the pair above.
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#(\d+)\b": frozenset({
        os.path.join("tools", "closing_keyword_guard.py"),
        os.path.join("fencepost", "seam_engine", "src", "seam_engine", "closing_keywords.py"),
    }),
}


def _iter_scanned_files(orita_dir: str):
    for rel_glob in (_RECIPES_GLOB, _SEAM_ENGINE_GLOB, _TOOLS_GLOB):
        for path in sorted(glob.glob(os.path.join(orita_dir, rel_glob))):
            if os.path.basename(path) in _SKIP_BASENAMES:
                continue
            yield path


def _pattern_text(call: ast.Call) -> str | None:
    """The literal string of a `re.compile(<literal>, ...)` call, or None
    if the first argument is not a plain string literal (an f-string, a
    name, a concatenation built at runtime -- none of those are the
    "hand-typed copy of a fixed law" shape this check hunts for)."""
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _is_re_compile_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return isinstance(func, ast.Attribute) and func.attr == "compile" and isinstance(func.value, ast.Name) and func.value.id == "re"


def _local_re_compile_patterns(path: str) -> list[tuple[str, int]]:
    """Every `(pattern_text, line_number)` this file defines with its OWN
    `re.compile(...)` call -- a file that only ever IMPORTS a shared name
    (the fix this whole campaign has been applying) has none of these for
    that pattern, by construction: importing a name binds it, it does not
    call `re.compile` again."""
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except (UnicodeDecodeError, OSError):
        return []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return []
    found = []
    for node in ast.walk(tree):
        if _is_re_compile_call(node):
            text = _pattern_text(node)
            if text is not None:
                found.append((text, node.lineno))
    return found


_VIOLATIONS_CACHE: dict[str, list] = {}


def clear_cache() -> None:
    """Same fix, same rationale as `star_covenant_check.py`/`vault_leak_
    check.py`'s own `clear_cache()`: only real callers are tests that
    want a forced fresh scan; production's one-call-per-process shape
    never needs this."""
    _VIOLATIONS_CACHE.clear()


def find_violations(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    key = os.path.realpath(orita_dir)
    if key not in _VIOLATIONS_CACHE:
        _VIOLATIONS_CACHE[key] = _find_violations_uncached(orita_dir)
    return list(_VIOLATIONS_CACHE[key])


def _find_violations_uncached(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    """Read-only, local-filesystem-only `ast` scan (no import, no
    execution, no network) of every recipe detector and every
    `seam_engine` core module for a `re.compile(...)` pattern defined
    locally in two or more distinct files. Returns a list of violation
    records, empty when every duplicate pattern in the live tree is
    either a real single definition or a seeded, documented exception."""
    by_pattern: dict[str, list[tuple[str, int]]] = {}
    for path in _iter_scanned_files(orita_dir):
        rel = os.path.relpath(path, orita_dir)
        for text, lineno in _local_re_compile_patterns(path):
            by_pattern.setdefault(text, []).append((rel, lineno))

    violations = []
    for text, locations in by_pattern.items():
        files = {rel for rel, _lineno in locations}
        if len(files) < 2:
            continue
        allowed = _ALLOWED_DUPLICATES.get(text)
        if allowed is not None and files <= allowed:
            continue
        violations.append({
            "pattern": text,
            "locations": sorted(locations),
        })
    violations.sort(key=lambda v: v["pattern"])
    return violations


def format_violations(violations: list) -> str:
    if not violations:
        return "duplicate regex check: clean -- every re.compile pattern is either unique or a seeded exception"
    lines = [f"duplicate regex check: {len(violations)} DUPLICATE PATTERN(S) FOUND -- hand-typed copy, no import backing it"]
    for v in violations:
        lines.append(f"  {v['pattern']!r}")
        for rel, lineno in v["locations"]:
            lines.append(f"    {rel}:{lineno}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
