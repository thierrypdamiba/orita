#!/usr/bin/env python3
"""Task 1311. Èṣù checks the FIRST lock, not just the second.

`consent_template_scope_check.py` (task 1057) closed the drift risk
between `consent.py`'s `REQUIRED_SCOPES` and the issue template a
petitioner types their scope-confirm back against -- the SECOND lock the
consent gate's own docstring names. It never checked the FIRST one:
`REQUIRED_SCOPES`'s own comment says its tool names are "mirrored
verbatim from SCOPES.md's 'Fencepost uses' column" -- the table that
*is* the Read-Only Oath, the source both the template and the gate claim
to mirror. Six own-remit sweeps (tasks 1010-1057, the same series that
led to task 1057's own template checker) hand-diffed the template against
`REQUIRED_SCOPES` and called it done; none of them re-opened `SCOPES.md`
itself and diffed the OTHER direction. If a future edit ever changed
`SCOPES.md`'s table without touching `REQUIRED_SCOPES` to match (or the
reverse), the template checker would stay green -- template and
`REQUIRED_SCOPES` could drift together, in step, away from the Oath both
of them are supposed to answer to -- and nothing would notice.

Parses `SCOPES.md`'s own "Concretely, on the toolkits in use:" table
structurally (plain `| Toolkit | uses, list | never, list |` rows, no
backticks -- a different shape from the issue template's backtick-quoted
cells, so it needs its own row regex) and normalizes each display name
with `consent_template_scope_check.normalize_display_name` -- reused, not
retyped, the same "GitHub" -> "github", "Gmail (v0.2)" -> "gmail" logic
the template checker already owns (duplicating it here is exactly the
drift class `duplicate_function_check.py` exists to catch). Task 1311
also generalized that shared function to strip ANY trailing parenthetical
marker, not just "(proposed)" -- SCOPES.md's own "(v0.2)" rows were a
real normalization gap the narrower version would have silently mis-keyed.

Two directions checked, both real:
  1. `SCOPES.md`'s "Fencepost uses" column vs. `REQUIRED_SCOPES` --
     the same missing/extra/duplicate/unrequired shape the template
     checker already reports, applied to the Oath's own table instead.
  2. `SCOPES.md`'s own "Fencepost may NEVER use" column against
     `REQUIRED_SCOPES` for that same toolkit -- a name appearing on BOTH
     sides of one row would mean the Oath's own table contradicts itself,
     the exact self-defeat Ogun's "RED MEANS STOP" line exists to prevent.

Read-only, local-filesystem-only, no network call of its own -- same
boundary every sibling `tools/*_check.py` module already holds.

Usage:
    python3 tools/scopes_md_consent_sync_check.py check [<scopes_path>]
"""
from __future__ import annotations

import os
import re
import sys
from typing import NamedTuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "fencepost", "seam_engine", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seam_engine.consent import REQUIRED_SCOPES  # noqa: E402

from consent_template_scope_check import normalize_display_name  # noqa: E402

# The exact same plain three-cell table-row shape `scopes_completeness_check.py`
# already compiles as `_TOOLKIT_TABLE_ROW` for this identical SCOPES.md
# table -- reused, not retyped a second time (the duplicate-pattern drift
# `duplicate_regex_check.py` exists to catch, caught live against this
# module's own first draft before it ever shipped).
from scopes_completeness_check import _TOOLKIT_TABLE_ROW as _ROW_RE  # noqa: E402

DEFAULT_SCOPES_PATH = os.path.join(ROOT, "fencepost", "SCOPES.md")


class ScopesRow(NamedTuple):
    display: str
    toolkit_key: str
    uses: frozenset[str]
    never_use: frozenset[str]


def _split_csv(cell: str) -> frozenset[str]:
    return frozenset(s.strip() for s in cell.split(",") if s.strip())


def parse_scopes_table(text: str) -> list[ScopesRow]:
    """Pure text parse of SCOPES.md's own table. Skips the header row (its
    first cell is literally "toolkit") and any separator row (a cell of
    all dashes) rather than hand-counting a line offset -- the same
    "a row added above can't silently shift what's parsed" discipline
    `consent_template_scope_check.parse_template_scopes` already holds.
    """
    rows = []
    for display, uses_cell, never_cell in _ROW_RE.findall(text):
        if display.strip().lower() == "toolkit":
            continue
        if re.fullmatch(r"-+", display.strip()):
            continue
        rows.append(
            ScopesRow(
                display,
                normalize_display_name(display),
                _split_csv(uses_cell),
                _split_csv(never_cell),
            )
        )
    return rows


def find_drift(
    rows: list[ScopesRow], required: dict[str, frozenset[str]]
) -> list[str]:
    """Same problem classes `consent_template_scope_check.find_drift`
    reports for the template, applied to SCOPES.md's own table, plus one
    SCOPES.md-specific check: a toolkit's own "may NEVER use" column
    naming something `REQUIRED_SCOPES` also requires for it -- the Oath
    contradicting itself on a single row.
    """
    problems: list[str] = []
    seen_keys: dict[str, str] = {}
    for row in rows:
        if row.toolkit_key in seen_keys:
            problems.append(
                f"toolkit {row.toolkit_key!r} appears on more than one SCOPES.md "
                f"table row ({seen_keys[row.toolkit_key]!r} and {row.display!r})"
            )
        seen_keys[row.toolkit_key] = row.display

        required_scopes = required.get(row.toolkit_key)
        if required_scopes is None:
            problems.append(
                f"SCOPES.md table row {row.display!r} names toolkit "
                f"{row.toolkit_key!r}, which consent.py's REQUIRED_SCOPES does "
                "not require at all"
            )
            continue
        if row.uses != required_scopes:
            missing = sorted(required_scopes - row.uses)
            extra = sorted(row.uses - required_scopes)
            problems.append(
                f"toolkit {row.toolkit_key!r}: SCOPES.md's 'Fencepost uses' column "
                f"drifts from REQUIRED_SCOPES (missing={missing}, extra={extra})"
            )

        contradiction = sorted(row.uses & row.never_use)
        if contradiction:
            problems.append(
                f"toolkit {row.toolkit_key!r}: SCOPES.md names {contradiction} in "
                "BOTH 'Fencepost uses' and 'Fencepost may NEVER use' on the same row"
            )
        self_contradiction = sorted(required_scopes & row.never_use)
        if self_contradiction:
            problems.append(
                f"toolkit {row.toolkit_key!r}: consent.py's REQUIRED_SCOPES requires "
                f"{self_contradiction}, which SCOPES.md's own row lists under "
                "'Fencepost may NEVER use'"
            )

    table_keys = {row.toolkit_key for row in rows}
    for toolkit_key in sorted(set(required) - table_keys):
        problems.append(
            f"consent.py requires toolkit {toolkit_key!r}, but no SCOPES.md table "
            "row names it"
        )
    return problems


def check(scopes_path: str = DEFAULT_SCOPES_PATH) -> tuple[bool, str]:
    if not os.path.exists(scopes_path):
        return False, f"scopes doc not found: {scopes_path}"
    with open(scopes_path, encoding="utf-8") as f:
        text = f.read()
    rows = parse_scopes_table(text)
    if not rows:
        return False, f"no toolkit table rows parsed out of {scopes_path}"
    problems = find_drift(rows, REQUIRED_SCOPES)
    if problems:
        return False, "drift found:\n  - " + "\n  - ".join(problems)
    return True, (
        f"clean ({len(rows)} toolkit row(s) in {os.path.basename(scopes_path)}, "
        "byte-identical to consent.py's REQUIRED_SCOPES both directions, no drift, "
        "no self-contradiction"
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] != "check":
        print("usage: python3 tools/scopes_md_consent_sync_check.py check [<scopes_path>]")
        return 2
    scopes_path = argv[1] if len(argv) > 1 else DEFAULT_SCOPES_PATH
    ok, msg = check(scopes_path)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
