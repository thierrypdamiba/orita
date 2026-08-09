#!/usr/bin/env python3
"""Task 109. Off-By-One audits the one clause the charter dared him to.

`CHARTER.md` Appendix D says, in one sentence: "One petition per god per
UTC day -- the file's date is the count, and the count is enforced by
CI, which Off-By-One is invited to audit and forbidden to adjust." Tasks
98-107 gave every Iron Rule and every ROADMAP.md design constraint a
running check; task 107 (`petition_limits_check.py`) even reads every
altar petition's own prose for the LIMITS clause one paragraph away from
this one. Nobody has yet taken the charter up on the audit it names by
office. Grepped `.github/workflows/` and `tools/*.py` for anything that
enforces one-file-per-day: zero hits. The claim is false as written --
there is no CI job of that name, and no local check either. Read the
mechanism the charter is actually leaning on: "the file's date is the
count" means the cadence is enforced by the filename alone matching the
day it was filed, one file per calendar day, forever. A filesystem
trivially prevents two files sharing the exact same name -- but nothing
stops a second, differently-spelled file for the same day
("2026-07-11b.md", "2026-07-11-copy.md", a stray ".MD" on a
case-insensitive filesystem) from sitting beside the first, silently
doubling a god's cadence while every existing check stays blind to it,
since none of them read `houses/*/altar/petitions/` for filename shape
at all.

This module closes exactly that gap: a read-only, local-filesystem-only
scan (no network, mirrors `star_covenant_check.find_violations`'s/
`no_grading_check.find_violations`'s boundary exactly) of every entry
directly inside every `houses/<god>/altar/petitions/` directory, flagging
any entry whose name is not exactly `YYYY-MM-DD.md` for a real calendar
date. Every non-conforming or duplicate-date entry is the one shape that
would let a god file twice in a day while "the file's date is the count"
keeps reading true by construction. Nine real petitions (Founding Day,
`houses/*/altar/petitions/2026-07-11.md`) checked live before any fix was
written -- all nine already conform.

Usage:
    python3 tools/petition_cadence_check.py check
"""
from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import text_patterns  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

_DATE_NAME = text_patterns.DATE_NAME_MD


def _petition_dirs(orita_dir: str) -> list:
    houses_dir = os.path.join(orita_dir, "houses")
    if not os.path.isdir(houses_dir):
        return []
    dirs = []
    for house in sorted(os.listdir(houses_dir)):
        petitions_dir = os.path.join(houses_dir, house, "altar", "petitions")
        if os.path.isdir(petitions_dir):
            dirs.append((house, petitions_dir))
    return dirs


def find_violations(orita_dir: str | None = None) -> list:
    """Returns a list of violation dicts. Each names the house, the exact
    filename, and why: either the name doesn't match `YYYY-MM-DD.md` for
    a real calendar date (malformed), or it does but a different entry in
    the same house already claims that same date (duplicate)."""
    orita_dir = orita_dir or DEFAULT_ORITA_DIR
    violations = []
    for house, petitions_dir in _petition_dirs(orita_dir):
        seen_dates: dict[str, str] = {}
        for name in sorted(os.listdir(petitions_dir)):
            full = os.path.join(petitions_dir, name)
            if not os.path.isfile(full):
                continue
            m = _DATE_NAME.match(name)
            if not m:
                violations.append({
                    "house": house,
                    "file": name,
                    "reason": "malformed",
                    "detail": "name is not exactly YYYY-MM-DD.md -- 'the file's date is the count' "
                    "only holds if every petition filename obeys the convention",
                })
                continue
            year, month, day = (int(g) for g in m.groups())
            try:
                parsed = date(year, month, day)
            except ValueError:
                violations.append({
                    "house": house,
                    "file": name,
                    "reason": "invalid_date",
                    "detail": f"{year:04d}-{month:02d}-{day:02d} is not a real calendar date",
                })
                continue
            key = parsed.isoformat()
            if key in seen_dates:
                violations.append({
                    "house": house,
                    "file": name,
                    "reason": "duplicate_date",
                    "detail": f"{key} already claimed by {seen_dates[key]!r} in the same house -- "
                    "one petition per god per UTC day is broken",
                })
                continue
            seen_dates[key] = name
    return violations


def format_violations(violations: list) -> str:
    if not violations:
        return "petition cadence check: clean -- every altar petition filename is a real, unique YYYY-MM-DD.md"
    lines = [
        f"petition cadence check: {len(violations)} VIOLATION(S) FOUND -- "
        "CHARTER.md's 'one petition per god per UTC day' claim broken"
    ]
    for v in violations:
        lines.append(f"  houses/{v['house']}/altar/petitions/{v['file']} [{v['reason']}] :: {v['detail']}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
