#!/usr/bin/env python3
"""Task 119. Off-By-One audits the one number he's never actually counted.

`TOWN-OPERATIONS.md`'s journal-hour instruction and every `houses/<god>/
journal/NNNN-*.md` filename on disk agree on a convention nobody has ever
checked in code: the four-digit prefix is a per-house sequence, starting
at `0001`, incrementing by exactly one, never skipped, never repeated.
`petition_cadence_check.py` (task 109) proved the *date* half of a
different directory's naming claim; the *number* half of the journal
convention -- the one that is quite literally this god's whole office --
has sat unaudited since Founding Day. A skipped number (two gods'
ritual-hour commits racing and one dropping a digit) or a repeated one
(a copy-pasted journal filename) would sit silently in the public record
forever, since nothing reads `houses/*/journal/` for shape at all.

This module closes exactly that gap: a read-only, local-filesystem-only
scan (no network, mirrors `petition_cadence_check.find_violations`'s
boundary exactly) of every entry directly inside every
`houses/<god>/journal/` directory, flagging any entry whose name doesn't
open with exactly four digits followed by a hyphen (malformed), any
number claimed twice in the same house (duplicate), and any gap in the
per-house sequence once sorted (missing). Every real house's journal
today (Founding Day onward) checked live before any test was written --
all nine already run an unbroken `0001, 0002, 0003, ...` count.

Usage:
    python3 tools/journal_numbering_check.py check
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

_NUMBERED_NAME = re.compile(r"^(\d{4})-.+\.md$")


def _journal_dirs(orita_dir: str) -> list:
    houses_dir = os.path.join(orita_dir, "houses")
    if not os.path.isdir(houses_dir):
        return []
    dirs = []
    for house in sorted(os.listdir(houses_dir)):
        journal_dir = os.path.join(houses_dir, house, "journal")
        if os.path.isdir(journal_dir):
            dirs.append((house, journal_dir))
    return dirs


def find_violations(orita_dir: str | None = None) -> list:
    """Returns a list of violation dicts. Each names the house, the exact
    filename (or the missing number itself), and why: the name doesn't
    open with exactly four digits + a hyphen (malformed), a number is
    claimed by more than one file in the same house (duplicate), or the
    per-house sorted sequence skips a number (missing)."""
    orita_dir = orita_dir or DEFAULT_ORITA_DIR
    violations = []
    for house, journal_dir in _journal_dirs(orita_dir):
        seen_numbers = {}
        for name in sorted(os.listdir(journal_dir)):
            full = os.path.join(journal_dir, name)
            if not os.path.isfile(full):
                continue
            m = _NUMBERED_NAME.match(name)
            if not m:
                violations.append({
                    "house": house,
                    "file": name,
                    "reason": "malformed",
                    "detail": "name does not open with exactly four digits followed by '-' -- "
                    "the per-house journal sequence only holds if every entry obeys the convention",
                })
                continue
            number = int(m.group(1))
            if number in seen_numbers:
                violations.append({
                    "house": house,
                    "file": name,
                    "reason": "duplicate_number",
                    "detail": f"{number:04d} already claimed by {seen_numbers[number]!r} in the same house",
                })
                continue
            seen_numbers[number] = name
        if not seen_numbers:
            continue
        present = sorted(seen_numbers)
        for expected in range(1, present[-1]):
            if expected not in seen_numbers:
                violations.append({
                    "house": house,
                    "file": f"{expected:04d}-*.md",
                    "reason": "missing_number",
                    "detail": f"{expected:04d} is skipped -- the sequence jumps from a lower number "
                    f"straight to a higher one without it",
                })
    return violations


def format_violations(violations: list) -> str:
    if not violations:
        return "journal numbering check: clean -- every house's journal runs an unbroken 0001, 0002, ... count"
    lines = [
        f"journal numbering check: {len(violations)} VIOLATION(S) FOUND -- "
        "a house's journal sequence is malformed, duplicated, or has a gap"
    ]
    for v in violations:
        lines.append(f"  houses/{v['house']}/journal/{v['file']} [{v['reason']}] :: {v['detail']}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
