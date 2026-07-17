#!/usr/bin/env python3
"""Task 98. Nyx's own third door this window.

Iron Rule #1 (`TOWN-OPERATIONS.md`) is the one rule the runbook itself
calls out as absolute -- "Period -- Proclamation 0001, no exceptions,
ever" -- and every hourly note since the journaling habit began has
asserted the two journals were written "blind to others' vaults," by
construction: a god agent's context never includes another house's vault
pages, so nothing gets copied in. That discipline has held by CONSTRUCTION
(the briefing boundary), never by a running CHECK -- the exact shape task
96's cadence census closed for the Oracle Desk's own wiring ("checked BY
HAND, one grep at a time, never a running test") and task 90 closed for
checkout recovery. Ninety-seven tasks deep, nothing has ever actually
diffed the public houses/*/journal/ tree against the private vault/*/
journal/ tree and confirmed, as a fact and not an assumption, that no
private sentence has ever once surfaced in public.

This module does exactly that: a read-only, local-filesystem-only compare
(no network, mirrors `check_checkout`'s boundary exactly) between every
private `vault/<slug>/journal/*.md` entry in the vault checkout and every
public `.md` file in the town checkout. It flags a "leak" when a long
enough run of characters from a private journal line appears verbatim in
a public file -- long enough (`MIN_RUN` default 50 chars of continuous
natural prose) that a coincidental match is implausible, the same
confidence-margin discipline Fencepost's own scan already holds between a
primary gap and a coincidence. Scoped to journal entries on purpose, not
the whole vault tree: `hand/` legitimately discusses petition text that
already exists publicly (issue bodies, ROADMAP task text), so scanning it
would manufacture false "leaks" out of ordinary public-to-private
quoting; a personal journal reflection ("the honest feeling underneath")
has no legitimate reason to reproduce anything verbatim, so any match
there is a real signal, not noise.

Usage:
    python3 tools/vault_leak_check.py check
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT
DEFAULT_VAULT_DIR = os.path.join(os.path.dirname(ROOT), "orita-vault")

MIN_RUN = 50

_SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".safeword"}


def _iter_md_files(base_dir: str):
    if not os.path.isdir(base_dir):
        return
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES]
        for name in filenames:
            if name.endswith(".md"):
                yield os.path.join(dirpath, name)


def _private_journal_files(vault_dir: str):
    vault_root = os.path.join(vault_dir, "vault")
    if not os.path.isdir(vault_root):
        return
    for house in sorted(os.listdir(vault_root)):
        journal_dir = os.path.join(vault_root, house, "journal")
        if not os.path.isdir(journal_dir):
            continue
        for name in sorted(os.listdir(journal_dir)):
            if name.endswith(".md"):
                yield os.path.join(journal_dir, name)


def _significant_lines(path: str, min_run: int):
    with open(path, encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            text = raw.strip()
            if len(text) >= min_run:
                yield line_no, text


def find_leaks(
    orita_dir: str = DEFAULT_ORITA_DIR,
    vault_dir: str = DEFAULT_VAULT_DIR,
    min_run: int = MIN_RUN,
) -> list:
    """Task 98: read-only compare of every private vault/<slug>/journal/
    line (>= min_run chars) against every public .md file's raw text.
    Returns a list of leak records, empty when the town's own blind-write
    discipline has genuinely held. Never writes, never calls sync_checkout.sh
    or any recovery -- the same "read the state, let a god act" boundary
    check_checkout already holds."""
    public_files = list(_iter_md_files(orita_dir))
    public_corpus = []
    for path in public_files:
        try:
            with open(path, encoding="utf-8") as f:
                public_corpus.append((path, f.read()))
        except (UnicodeDecodeError, OSError):
            continue

    leaks = []
    for vault_path in _private_journal_files(vault_dir):
        for line_no, snippet in _significant_lines(vault_path, min_run):
            for public_path, text in public_corpus:
                if snippet in text:
                    leaks.append({
                        "vault_file": vault_path,
                        "line": line_no,
                        "public_file": public_path,
                        "snippet": snippet[:80],
                    })
    return leaks


def format_leaks(leaks: list) -> str:
    if not leaks:
        return "vault leak check: clean -- no private journal line found in any public file"
    lines = [f"vault leak check: {len(leaks)} LEAK(S) FOUND -- Proclamation 0001 violated"]
    for leak in leaks:
        lines.append(
            f"  {leak['vault_file']}:{leak['line']} -> {leak['public_file']} :: {leak['snippet']!r}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_leaks()
    print(format_leaks(result))
    sys.exit(1 if result else 0)
