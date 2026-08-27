#!/usr/bin/env python3
"""Task 163. Zashiki-Warashi's first real module.

A phrase ran through eighteen files in `tools/` when this module first
swept them at task 163; thirty-two carry it today -- fourteen more `tools/
*_check.py` files (`duplicate_regex_check.py`, `gateway_toolset_check.py`,
`good_first_issue_check.py`, `metrics_field_completeness_check.py`,
`nyx_traffic_check.py`, `recipe_readme_check.py`, `site_link_check.py`,
`chronicle_readme_check.py`, `proclamation_count_check.py`,
`site_recipe_check.py`, `duplicate_function_check.py`, `tithe_check.py`,
`one_action_check.py`, `consent_template_scope_check.py`) have
independently repeated the same "no network" claim since, each caught by
this module's own live discovery with no docstring edit required --
which is the whole point of never hand-typing the list below.
The original eighteen's genealogy is almost
identical in shape to task 147's `DEFAULT_ACTOR` chain: `vault_leak_check.
py` claims to mirror `check_checkout`'s "boundary" exactly ("no network");
`star_covenant_check.py` claims to mirror `vault_leak_check.find_leaks`'s
boundary exactly; `petition_cadence_check.py` and `petition_limits_check.py`
both claim to mirror `star_covenant_check.find_violations`'s; `journal_
numbering_check.py` claims to mirror `petition_cadence_check.find_
violations`'s; `report_cadence_check.py` claims to mirror `petition_
cadence_check.py`'s own boundary; `rider_check.py`, `verdict_provenance_
check.py`, `hand_lore_check.py` each claim the identical "read-only,
local-filesystem-only... no network" shape; `scopes_completeness_check.py`,
`word_watch.py`, `child_work_check.py`, `square_check.py`, `wip_reclaim_
check.py`, `arcade_app_watch.py`, `ci_watch.py`, and `ritual_check.py`
itself all repeat some form of the same sentence about individual
functions or the whole module: "makes no network call of its own."

Every one of these claims is true today (confirmed by grep: none of the
now-thirty-two files import a network-capable module). None of them has ever
been checked structurally -- the same "claims a mirror, never checked
against the thing it mirrors" pattern tasks 136/137/141/146/147/160/162
already closed elsewhere in this codebase, found here for the first time
in `tools/`'s own boundary claims. If a future edit to any of these files
(a "just add a quick live lookup" patch, the same shape every prior
mirror-drift regression in this repo has taken) ever imports `requests`,
`httpx`, `socket`, or another network-capable module while its own
docstring keeps swearing "no network," nothing today would catch it --
these are security/trust-boundary claims (Iron Rule enforcement tools
reading the town's own public record), not cosmetic ones, so a silent
drift here is worse than most.

This module discovers every claiming file structurally -- a live scan of
`tools/*.py` for the phrase "no network" (tolerant of a mid-phrase line
wrap, the way `petition_limits_check.py`'s own docstring happens to wrap
it) in its own source, never a second hand-typed list of filenames
(eighteen at task 163, thirty-two today) that could itself go stale --
and checks each one's real, live-loaded AST: no `import` or
`from ... import` statement anywhere in the file names a module on the
network-capable deny-list. A module that imports
`os`/`re`/`sys`/`json`/`subprocess`/`hashlib`/`datetime`/
`importlib.util` (everything these thirty-two files actually use today)
passes; a module that imports `requests`, `httpx`, `urllib.request`,
`urllib3`, `http.client`, `socket`, `aiohttp`, `ftplib`, `smtplib`,
`telnetlib`, `poplib`, `imaplib`, or `nntplib` does not.

ROADMAP task 164: `tools/*.py` was never the only place this exact claim
lives. `fencepost/seam_engine/src/seam_engine/consent.py` (the double-
checked consent gate -- "This module reads nothing and writes nothing
itself... it is pure judgment, not action") and `draftback.py` (the
write-back module -- "No adapter, no network, by default... this file
cannot reach a real account on its own, because it does not know how to")
both carry the identical "no network" trust-boundary claim, true today
(grepped), and -- until this task -- checked by nothing: this module's own
`find_claiming_files`/`check_network_boundary` only ever globbed
`tools/*.py`, so the eighteen-file sweep task 163 shipped never actually
reached Fencepost's own safety-critical source, the two files load-bearing
for STRATEGY.md's "read-only scopes only" and "the final action is ALWAYS
the human's" guarantees -- a quieter version of the exact "claims a
boundary, the checker built to guard it doesn't actually reach that far"
gap this module exists to close. `find_claiming_files`/`check_network_
boundary` already took a directory argument, so no signature changed; this
task adds `SEAM_ENGINE_SRC_DIR` and the multi-directory `find_claiming_
files_all`/`check_network_boundary_all` that scan `tools/` AND `fencepost/
seam_engine/src/seam_engine/` together, keyed by path relative to the repo
root so a same-named file in two directories could never silently collide.
The CLI now runs the combined check; every existing single-directory
function keeps its original default and behavior, so nothing that already
called `check_network_boundary()` (unqualified, tools/-only) changes.

Task 446: the two-directory sweep still never reached `oracle/oracle_
engine/src/oracle_engine/` -- the Oracle Desk's own 58-file cadence/
autograde engine, built in the same "mirror this sibling verbatim" style
`duplicate_regex_check.py` was widened for at task 445, and the exact
directory `duplicate_regex_check.py` now scans but this checker did not.
A same-line `grep -rl "no network"` over the directory (tried first, by
hand) reported zero hits -- but `CLAIM_PATTERN` below is `r"no\\s+network"`,
and `\\s` matches a newline: `copylint.py`'s real docstring wraps exactly
there ("makes no...network call, writes nothing..."), so a plain grep
missed a real, structural "no network" trust-boundary claim this checker
exists to catch. `find_claiming_files()` itself -- not a hand-typed grep
-- is what actually surfaced it once `ORACLE_ENGINE_SRC_DIR` was added to
`SEARCH_DIRS`. The claim holds true (`copylint.py` imports only `re` and
`dataclasses`), so this closes a real, previously-unchecked blind spot
rather than catching an active violation -- but unlike task 445's own
"widened the scan, found nothing" outcome, this one found a real claiming
file that had been running unchecked since the Oracle Desk shipped.

Usage:
    python3 tools/network_boundary_check.py check
"""
from __future__ import annotations

import ast
import glob
import os
import re
import sys
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT, "tools")
SEAM_ENGINE_SRC_DIR = os.path.join(ROOT, "fencepost", "seam_engine", "src", "seam_engine")
ORACLE_ENGINE_SRC_DIR = os.path.join(ROOT, "oracle", "oracle_engine", "src", "oracle_engine")

# Every real source directory this repo's own "no network" trust-boundary
# claims live in today -- tools/'s eighteen (task 163), Fencepost's own
# consent.py/draftback.py (task 164), and the Oracle Desk's own engine
# (task 446 -- the identical "checker never scanned the sibling directory
# built in the same mirror-this-sibling style" shape task 164 first closed
# for seam_engine and task 445 closed for duplicate_regex_check.py, found
# here for network_boundary_check.py itself). A future fourth directory
# only needs adding here; find_claiming_files_all/check_network_boundary_all
# already fold over however many are listed.
SEARCH_DIRS = (TOOLS_DIR, SEAM_ENGINE_SRC_DIR, ORACLE_ENGINE_SRC_DIR)

# Matches "no network" even when line-wrapped inside a docstring (e.g.
# petition_limits_check.py's own "...scan (no\nnetwork, mirrors...") --
# a bare substring test would silently miss exactly the files whose prose
# happened to wrap at that word, which is not a reason to skip them.
CLAIM_PATTERN = re.compile(r"no\s+network")

# A module counts as network-capable if any top-level import names it
# exactly, or -- for dotted submodules like `urllib.request` -- if the
# imported dotted path exactly matches or the `ast.ImportFrom` module is
# exactly this string. Deliberately narrow: `urllib.parse` (no network
# capability of its own) must NOT be flagged just because it starts with
# "urllib", so this is an exact-match set, not a prefix test.
NETWORK_MODULES = frozenset({
    "requests",
    "httpx",
    "aiohttp",
    "urllib.request",
    "urllib3",
    "http.client",
    "socket",
    "ftplib",
    "smtplib",
    "telnetlib",
    "poplib",
    "imaplib",
    "nntplib",
})


class NetworkBoundaryError(ValueError):
    """Raised when a claiming file can't be read/parsed at all -- never
    silently skipped, the same fail-loud discipline `strategy_targets_
    check.StrategyTargetError` already holds for a missing/malformed doc
    row."""


def find_claiming_files(tools_dir: str = TOOLS_DIR) -> list[str]:
    """Every `tools/*.py` file whose own source literally contains the
    phrase "no network" -- a live filesystem scan, never a hardcoded list,
    the same discipline `test_cadence_census.py`'s `_cadence_base_names`
    and `strategy_targets_check`'s live STRATEGY.md read already hold.
    Returns basenames, sorted, so the result is stable and readable."""
    hits = []
    for path in sorted(glob.glob(os.path.join(tools_dir, "*.py"))):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if CLAIM_PATTERN.search(text):
            hits.append(os.path.basename(path))
    return hits


def _imported_module_names(tree: ast.Module) -> list[str]:
    """Every top-level-or-nested module name a file's `import`/`from`
    statements name, walking the WHOLE tree (not just module level) --
    a network import guarded inside a function body is still a network
    import; hiding it deeper in the file must not defeat this check.

    For `from X import Y`, both `X` (e.g. `"urllib.request"` from
    `from urllib.request import urlopen`) AND the reconstructed `X.Y`
    dotted path (e.g. `"urllib.request"` from `from urllib import
    request`, or `"http.client"` from `from http import client`) are
    named -- `ast.ImportFrom.module` alone is `"urllib"`/`"http"` for
    those two real stdlib network-submodule-as-attribute forms, which
    never matches the deny-list's exact dotted-submodule entries on its
    own and would otherwise walk straight past NETWORK_MODULES.

    Task 536: this only ever named `ast.Import`/`ast.ImportFrom` nodes --
    a *static* import statement. `importlib.import_module("requests")`,
    `from importlib import import_module; import_module("socket")`, and
    the bare builtin `__import__("http.client")` are each an `ast.Call`,
    never either node type, so a file could carry any of the three, claim
    "no network" in its own docstring, and pass this check while genuinely
    binding a network-capable module at runtime. `_dynamic_import_targets`
    below folds those three call shapes in, reading only a first-argument
    STRING LITERAL -- a variable argument cannot be statically proven to
    name a network module, so (matching this function's own narrow,
    structural intent) it is left unflagged rather than guessed at.
    `fencepost/seam_engine/src/seam_engine/recipes.py`'s own independent
    copy of this deny-list logic had the identical gap, closed the same
    task."""
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
                for alias in node.names:
                    names.append(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Call):
            target = _dynamic_import_target(node)
            if target is not None:
                names.append(target)
    return names


def _dynamic_import_target(call: ast.Call) -> str | None:
    """If `call` is `importlib.import_module(...)`, a bare `import_module(...)`
    (reachable via `from importlib import import_module`), or `__import__(...)`,
    and its first positional argument is a literal string, return that
    string. Returns `None` for every other call shape, or when the first
    argument isn't a string literal -- never a guess at an unresolvable
    target."""
    func = call.func
    is_import_module = (
        isinstance(func, ast.Attribute) and func.attr == "import_module"
    ) or (isinstance(func, ast.Name) and func.id == "import_module")
    is_dunder_import = isinstance(func, ast.Name) and func.id == "__import__"
    if not (is_import_module or is_dunder_import):
        return None
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def check_source_has_no_network_import(source: str) -> tuple[bool, str]:
    """True + reason iff `source` names no network-capable module in any
    `import`/`from ... import` statement, or dynamic `importlib.import_
    module`/`__import__` call with a literal target, anywhere in the file.
    False + a reason naming exactly which module and which real import
    triggered it, so a failure is actionable, not just a bare assertion."""
    tree = ast.parse(source)
    for name in _imported_module_names(tree):
        if name in NETWORK_MODULES:
            return False, f"imports network-capable module {name!r}"
    return True, "ok"


def check_network_boundary(tools_dir: str = TOOLS_DIR) -> dict[str, Any]:
    """Cross-checks every real, live-discovered "no network" claim in
    `tools/*.py` against its real, live-loaded source -- never a hand-typed
    copy of either the file list or its contents."""
    results = {}
    for name in find_claiming_files(tools_dir):
        path = os.path.join(tools_dir, name)
        try:
            with open(path, encoding="utf-8") as f:
                source = f.read()
        except OSError as exc:
            raise NetworkBoundaryError(f"could not read {name}: {exc}") from exc
        ok, reason = check_source_has_no_network_import(source)
        results[name] = {"ok": ok, "reason": reason}
    return results


def find_claiming_files_all(dirs: tuple[str, ...] = SEARCH_DIRS) -> list[str]:
    """Every claiming file across every directory in `dirs`, as paths
    relative to the repo root (e.g. `tools/vault_leak_check.py`,
    `fencepost/seam_engine/src/seam_engine/consent.py`) -- relative so two
    directories can never collide on a shared basename, sorted so the
    result is stable. Delegates entirely to `find_claiming_files` per
    directory; never re-implements the discovery."""
    hits = []
    for d in dirs:
        for name in find_claiming_files(d):
            hits.append(os.path.relpath(os.path.join(d, name), ROOT))
    return sorted(hits)


def check_network_boundary_all(dirs: tuple[str, ...] = SEARCH_DIRS) -> dict[str, Any]:
    """Cross-checks every real, live-discovered "no network" claim across
    every directory in `dirs`, keyed by repo-root-relative path. Delegates
    entirely to `check_network_boundary` per directory; never re-implements
    the AST check."""
    results = {}
    for d in dirs:
        for name, r in check_network_boundary(d).items():
            key = os.path.relpath(os.path.join(d, name), ROOT)
            results[key] = r
    return results


def format_network_boundary(result: dict[str, Any]) -> str:
    total = len(result)
    broken = {name: r for name, r in result.items() if not r["ok"]}
    if not broken:
        return f"network boundary: clean -- {total} file(s) claiming \"no network\", all hold it"
    lines = [f"network boundary: BROKEN -- {len(broken)} of {total} file(s) claim \"no network\" but don't:"]
    for name, r in sorted(broken.items()):
        lines.append(f"  {name}: {r['reason']}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = check_network_boundary_all()
    print(format_network_boundary(out))
    sys.exit(0 if all(r["ok"] for r in out.values()) else 1)
