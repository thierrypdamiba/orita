#!/usr/bin/env python3
"""Task 434. Off-By-One catches a warning before it becomes a SyntaxError.

Found by accident, not by design: this hour's first move (with all 433
prior tasks reading DONE) was to actually run both full suites clean
against a freshly-installed sandbox rather than trust BUILDLOG.md's own
last-claimed numbers. Root and `fencepost/seam_engine` both passed clean
(1197/1197, 1541/1541) -- but pytest's own collection output carried a
`DeprecationWarning: invalid escape sequence '\\|'` pinned to
`tools/roadmap_archive.py:2`. Neither test suite counts that as a
failure -- a DeprecationWarning is not an assertion -- so it had been
sitting there, real, unflagged, for as long as that docstring existed.

This is not cosmetic. Python has warned on invalid escape sequences in
string literals since 3.6 specifically because a future version turns
the warning into a hard `SyntaxError` at compile time -- the exact
"true when written, never rechecked" shape Iron Rule 1's own history
warns about (a `tools/vault_leak_check.py` gap sat unnoticed for 96
tasks the same way). A module that fails to compile fails to import,
which breaks every script that loads it, silently, on whatever future
Python upgrade finally flips the switch.

`tools/roadmap_archive.py`'s own docstring is NOT a raw string, and
can't casually become one: alongside the one real bug (`\\|`, inside a
worked `grep` example), it also carries a genuine, intentional `\\xb7`
hex escape (task 19's own literal middle-dot character). A blanket
raw-string prefix fix would silently swap that character for four
literal bytes instead of the dot it renders today -- proven by direct comparison
before shipping this task's own one-line fix (`\\|` -> `\\\\|`, an
escaped backslash, checked byte-identical via `compile()` +
`warnings.catch_warnings` pre/post).

This module is the running check the one-off catch deserves: it
compiles every tracked `.py` file under the repo (skipping `.git`,
`__pycache__`, and `node_modules` -- the same directories every other
full-repo scan in this tree already excludes) with warnings captured,
and reports any file whose compilation raises an "invalid escape
sequence" warning -- `DeprecationWarning` on Python <=3.11,
`SyntaxWarning` on 3.12+ (see `_invalid_escape_warnings`'s own docstring
below: this module's FIRST version checked only the former and shipped
green locally under 3.11 while failing live on `dawn-run.yml`'s pinned
3.12 minutes later, an almost-immediate real instance of the exact
version-drift class this whole check exists to guard against). Live run
against the repo post-fix: 350 files, 0 violations (confirmed 1 pre-fix
via `git stash`, the same stash-and-rerun discipline tasks 421-433
already hold for proving a repro is real rather than assumed).

One deliberate design choice worth naming: this checks COMPILATION,
never IMPORT. Importing every `.py` file in the tree would require each
one's real runtime dependencies present and would risk executing
top-level side effects (network calls, file writes) this town's own
read-only doctrine forbids for a routine hourly scan. `compile()` on
source text parses and byte-compiles without ever running a line of it
-- the exact same boundary `duplicate_regex_check.py`'s own `ast.parse`
already holds.

Usage:
    python3 tools/escape_sequence_check.py check
"""
from __future__ import annotations

import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

_SKIP_DIRS = {".git", "__pycache__", "node_modules"}
_INVALID_ESCAPE_MARKER = "invalid escape sequence"


def _iter_python_files(orita_dir: str):
    for dirpath, dirnames, filenames in os.walk(orita_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _invalid_escape_warnings(path: str) -> list[tuple[int, str]]:
    """`(lineno, message)` for every real "invalid escape sequence"
    warning `compile()` raises against `path`'s own live source text.

    The warning CATEGORY is not stable across Python versions, and this
    module's own first version got bitten by that live, the same hour it
    shipped: local verification ran under Python 3.11, where this is a
    `DeprecationWarning` (true since 3.6). `dawn-run.yml`'s CI pins
    Python 3.12, where CPython upgraded the identical warning to a
    `SyntaxWarning` -- same message text, same "future SyntaxError" fate,
    different category -- and a category check pinned to only
    `DeprecationWarning` silently sees nothing on 3.12+, reporting
    "clean" for source that will not compile at all a few Python
    versions from now. Matched here on the message text (the one thing
    that hasn't moved across 3.6-3.13) against BOTH categories rather
    than either alone.

    A file that fails to even read (bad encoding, gone between listing
    and opening) or fails to parse (a real syntax error, a different bug
    entirely, not this check's job) yields nothing -- the same "not my
    failure to report" boundary `duplicate_regex_check.py`'s own
    `_local_re_compile_patterns` already holds for both cases."""
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except (UnicodeDecodeError, OSError):
        return []
    hits = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            compile(source, path, "exec")
        except SyntaxError:
            return []
        for warning in caught:
            if warning.category in (
                DeprecationWarning,
                SyntaxWarning,
            ) and _INVALID_ESCAPE_MARKER in str(warning.message):
                hits.append((warning.lineno, str(warning.message)))
    return hits


_VIOLATIONS_CACHE: dict[str, list] = {}


def clear_cache() -> None:
    """Same fix, same rationale as `duplicate_regex_check.py`/
    `site_link_check.py`'s own `clear_cache()`: only real callers are
    tests that want a forced fresh scan; production's one-call-per-
    process shape never needs this."""
    _VIOLATIONS_CACHE.clear()


def find_violations(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    key = os.path.realpath(orita_dir)
    if key not in _VIOLATIONS_CACHE:
        _VIOLATIONS_CACHE[key] = _find_violations_uncached(orita_dir)
    return list(_VIOLATIONS_CACHE[key])


def _find_violations_uncached(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    violations = []
    for path in _iter_python_files(orita_dir):
        rel = os.path.relpath(path, orita_dir)
        for lineno, message in _invalid_escape_warnings(path):
            violations.append({"file": rel, "line": lineno, "message": message})
    return violations


def check_escape_sequences(orita_dir: str = DEFAULT_ORITA_DIR) -> dict:
    violations = find_violations(orita_dir)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def format_result(result: dict) -> str:
    if result["clean"]:
        return "escape sequences: clean (every tracked .py file compiles with zero invalid-escape-sequence warnings)"
    lines = ", ".join(f"{v['file']}:{v['line']}" for v in result["violations"])
    return (
        f"escape sequences: BROKEN -- {result['count']} invalid escape sequence warning(s) "
        f"({lines}) -- a future Python turns these into SyntaxErrors, breaking import; fix now"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = check_escape_sequences()
    print(format_result(out))
    sys.exit(0 if out["clean"] else 1)
