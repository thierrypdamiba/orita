#!/usr/bin/env python3
"""Task 163. Zashiki-Warashi's first real module.

A phrase runs through eighteen files in `tools/`, a genealogy almost
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
eighteen files import a network-capable module). None of them has ever
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
it) in its own source, never a second hand-typed list of eighteen
filenames that could itself go stale -- and checks each one's real,
live-loaded AST: no `import` or `from ... import` statement anywhere in
the file names a module on the network-capable deny-list. A module that
imports `os`/`re`/`sys`/`json`/`subprocess`/`hashlib`/`datetime`/
`importlib.util` (everything these eighteen files actually use today)
passes; a module that imports `requests`, `httpx`, `urllib.request`,
`urllib3`, `http.client`, `socket`, `aiohttp`, `ftplib`, `smtplib`,
`telnetlib`, `poplib`, `imaplib`, or `nntplib` does not.

Usage:
    python3 tools/network_boundary_check.py check
"""
from __future__ import annotations

import ast
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT, "tools")

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
    import; hiding it deeper in the file must not defeat this check."""
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


def check_source_has_no_network_import(source: str) -> tuple[bool, str]:
    """True + reason iff `source` names no network-capable module in any
    `import`/`from ... import` statement anywhere in the file. False +
    a reason naming exactly which module and which real import triggered
    it, so a failure is actionable, not just a bare assertion."""
    tree = ast.parse(source)
    for name in _imported_module_names(tree):
        if name in NETWORK_MODULES:
            return False, f"imports network-capable module {name!r}"
    return True, "ok"


def check_network_boundary(tools_dir: str = TOOLS_DIR) -> dict:
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


def format_network_boundary(result: dict) -> str:
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
    out = check_network_boundary()
    print(format_network_boundary(out))
    sys.exit(0 if all(r["ok"] for r in out.values()) else 1)
