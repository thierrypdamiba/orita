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

Task 370 widens the same scan past `houses/` (public) into the vault's
own `vault/<god>/journal/` (private) -- the identical convention holds
there and nothing had ever checked it either. The vault scan is opt-in
(a new `vault_dir` argument; omit it and behavior is byte-identical to
before this task) and reads filenames only, never file content -- the
same shape/no-quote boundary `vault_leak_check.py` already draws between
"detect a structural problem" and "leak a private sentence." The first
live run past that boundary found two real, permanent clerical errors in
`vault/nisaba/journal/`: `0016` claimed by two authentic entries (dated
2026-07-17 and 2026-07-22) and `0170` skipped entirely (0169 then 0171).
Both predate this check by days; neither is a fixture bug. The vault is
sealed forever (Proclamation 0001) -- a private entry is never renumbered
or backdated after the fact just to make a checker read clean -- so these
are not silently repaired. They are named as two exact, permanent,
documented exceptions (`KNOWN_VAULT_EXCEPTIONS`), the same "historical
fact on record, not a currently-live violation" shape `ritual_check.py`'s
`check_report_cadence` already uses for the 2026-07-14 cron gap.

Usage:
    python3 tools/journal_numbering_check.py check
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT
DEFAULT_VAULT_DIR = os.path.join(os.path.dirname(ROOT), "orita-vault")

_NUMBERED_NAME = re.compile(r"^(\d{4})-.+\.md$")

# Task 370: two real, permanent clerical errors found the hour this scan
# first widened past houses/ into vault/nisaba/journal/ -- see the module
# docstring above for the full story. Each tuple is (house, reason,
# number); an exact match on all three is required, so this can never
# silently swallow an unrelated violation in the same house.
KNOWN_VAULT_EXCEPTIONS = frozenset({
    ("nisaba", "duplicate_number", 16),
    ("nisaba", "missing_number", 170),
})


def _journal_dirs(orita_dir: str) -> list[tuple[str, str]]:
    houses_dir = os.path.join(orita_dir, "houses")
    if not os.path.isdir(houses_dir):
        return []
    dirs: list[tuple[str, str]] = []
    for house in sorted(os.listdir(houses_dir)):
        journal_dir = os.path.join(houses_dir, house, "journal")
        if os.path.isdir(journal_dir):
            dirs.append((house, journal_dir))
    return dirs


def _vault_journal_dirs(vault_dir: str) -> list[tuple[str, str]]:
    """Task 370: the private-tree mirror of `_journal_dirs` -- same shape,
    rooted at `<vault_dir>/vault/<god>/journal/` instead of
    `<orita_dir>/houses/<god>/journal/`."""
    vault_root = os.path.join(vault_dir, "vault")
    if not os.path.isdir(vault_root):
        return []
    dirs: list[tuple[str, str]] = []
    for house in sorted(os.listdir(vault_root)):
        journal_dir = os.path.join(vault_root, house, "journal")
        if os.path.isdir(journal_dir):
            dirs.append((house, journal_dir))
    return dirs


def _scan_journal_dirs(dirs: list[tuple[str, str]], realm: str) -> list[dict[str, object]]:
    """Shared malformed/duplicate/missing scan, tagged with which realm
    (`"public"` for houses/, `"vault"` for vault/) each violation came
    from. Filenames only -- never opens a file to read its content."""
    violations: list[dict[str, object]] = []
    for house, journal_dir in dirs:
        seen_numbers: dict[int, str] = {}
        for name in sorted(os.listdir(journal_dir)):
            full = os.path.join(journal_dir, name)
            if not os.path.isfile(full):
                continue
            m = _NUMBERED_NAME.match(name)
            if not m:
                violations.append({
                    "realm": realm,
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
                    "realm": realm,
                    "house": house,
                    "file": name,
                    "reason": "duplicate_number",
                    "number": number,
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
                    "realm": realm,
                    "house": house,
                    "file": f"{expected:04d}-*.md",
                    "reason": "missing_number",
                    "number": expected,
                    "detail": f"{expected:04d} is skipped -- the sequence jumps from a lower number "
                    f"straight to a higher one without it",
                })
    return violations


def find_violations(
    orita_dir: str | None = None,
    vault_dir: str | None = None,
    filter_known_exceptions: bool = True,
) -> list[dict[str, object]]:
    """Returns a list of violation dicts. Each names the realm (`public`
    houses/ or `vault` vault/), the house, the exact filename (or the
    missing number itself), and why: the name doesn't open with exactly
    four digits + a hyphen (malformed), a number is claimed by more than
    one file in the same house (duplicate), or the per-house sorted
    sequence skips a number (missing).

    `vault_dir` is opt-in: omit it (the default) and this scans only
    `houses/`, byte-identical to this function's behavior before task
    370. Pass it to also scan `vault/<god>/journal/`.

    `filter_known_exceptions` (default True) drops any vault violation
    matching `KNOWN_VAULT_EXCEPTIONS` -- pass False to see the raw,
    unfiltered scan (used by this module's own tests to prove the
    exception list is neither stale nor hiding anything new)."""
    orita_dir = orita_dir or DEFAULT_ORITA_DIR
    violations = _scan_journal_dirs(_journal_dirs(orita_dir), "public")
    if vault_dir is not None:
        vault_violations = _scan_journal_dirs(_vault_journal_dirs(vault_dir), "vault")
        if filter_known_exceptions:
            vault_violations = [
                v for v in vault_violations
                if (v["house"], v["reason"], v.get("number")) not in KNOWN_VAULT_EXCEPTIONS
            ]
        violations.extend(vault_violations)
    return violations


def format_violations(violations: list[dict[str, object]]) -> str:
    if not violations:
        return "journal numbering check: clean -- every house's journal runs an unbroken 0001, 0002, ... count"
    lines = [
        f"journal numbering check: {len(violations)} VIOLATION(S) FOUND -- "
        "a house's journal sequence is malformed, duplicated, or has a gap"
    ]
    for v in violations:
        prefix = "vault" if v.get("realm") == "vault" else "houses"
        lines.append(f"  {prefix}/{v['house']}/journal/{v['file']} [{v['reason']}] :: {v['detail']}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations(vault_dir=DEFAULT_VAULT_DIR)
    print(format_violations(result))
    sys.exit(1 if result else 0)
