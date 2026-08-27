#!/usr/bin/env python3
"""Task 1057. Èṣù structures a check his own hand kept re-running by eye.

Five separate own-remit sweeps of The Threshold (tasks 1010, 1017, 1030,
1037, 1050 -- `grep -n "REQUIRED_SCOPES.*re-diffed" ROADMAP.md`) each
hand-diffed `fencepost/seam_engine/src/seam_engine/consent.py`'s
`REQUIRED_SCOPES` dict against `.github/ISSUE_TEMPLATE/point-fencepost.md`'s
scope-confirm table, toolkit by toolkit, and each one reported "byte-
identical, no drift" -- a true finding, five times, by construction-only
assertion, never a running check. That is the exact shape Iron Rule #1's
own history already names as the town's oldest recurring mistake (`tools/
vault_leak_check.py`'s founding docstring: "this rule held by construction-
only assertion for 96 tasks before a running check"). The issue template
is the SECOND lock a real human's consent depends on (`consent.py`'s own
docstring: "an explicit scope confirm... typed back verbatim against the
same table SCOPES.md swears to") -- if a future edit ever added a scope to
`REQUIRED_SCOPES` without updating the template a human actually reads and
copies from, a real petitioner would be asked to confirm a stale or
incomplete list, and `enforce_consent_gate` would then correctly refuse
their honest confirm for a table they were never shown. Nobody has hit
that yet only because five hourly sweeps happened to catch it by hand every
time; this module is what keeps catching it once nobody remembers to look.

Parses the template's own markdown table (never re-typing the scopes a
second time) and normalizes each display heading to `consent.py`'s own
toolkit keys structurally -- lowercase, spaces to underscores, a trailing
" (proposed)" marker stripped -- so a new toolkit row needs no matching
edit here, the same "grows with the source it mirrors or fails closed"
discipline `consent.py`'s own `REQUIRED_SCOPES` docstring holds itself to.

Read-only, local-filesystem-only, no network call of its own -- same
boundary `consent_grant_log.py` and every sibling `tools/*_check.py`
module already holds.

Usage:
    python3 tools/consent_template_scope_check.py check [<template_path>]
"""
from __future__ import annotations

import os
import re
import sys
from typing import NamedTuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "fencepost", "seam_engine", "src"))
from seam_engine.consent import REQUIRED_SCOPES  # noqa: E402

DEFAULT_TEMPLATE_PATH = os.path.join(
    ROOT, ".github", "ISSUE_TEMPLATE", "point-fencepost.md"
)

# Matches one scope-confirm table row: `| Display Name | \`Tool, Names\` |`.
# Deliberately excludes the header/separator rows (neither has a backtick
# span in the second column) rather than hand-counting a line offset into
# the file -- a template edit that adds a blank line above the table can't
# silently shift which rows this parses.
_ROW_RE = re.compile(r"^\|\s*([^|`]+?)\s*\|\s*`([^`]+)`\s*\|\s*$", re.MULTILINE)

_PROPOSED_SUFFIX = re.compile(r"\s*\(proposed\)\s*\Z", re.IGNORECASE)


def normalize_display_name(display: str) -> str:
    """'Google Calendar' -> 'google_calendar', 'Slack (proposed)' ->
    'slack' -- structural, not a hand-typed lookup table, so a template row
    for a toolkit this function has never seen still normalizes correctly
    the same day it's added.
    """
    stripped = _PROPOSED_SUFFIX.sub("", display).strip()
    return stripped.lower().replace(" ", "_")


class TemplateRow(NamedTuple):
    display: str
    toolkit_key: str
    scopes: frozenset[str]


def parse_template_scopes(text: str) -> list[TemplateRow]:
    """Pure text parse -- no import, no execution of anything the template
    itself might contain. Returns rows in file order; duplicates (a toolkit
    named twice) are returned as separate entries so `find_drift` can flag
    the duplicate itself rather than silently keeping only the last one.
    """
    rows = []
    for display, raw_scopes in _ROW_RE.findall(text):
        names = frozenset(s.strip() for s in raw_scopes.split(",") if s.strip())
        rows.append(TemplateRow(display, normalize_display_name(display), names))
    return rows


def find_drift(
    rows: list[TemplateRow], required: dict[str, frozenset[str]]
) -> list[str]:
    """Every problem class named plainly, never a bare boolean:
    - a template row for a toolkit `consent.py` doesn't require at all
      (dead or premature promise to a petitioner);
    - a toolkit `consent.py` requires that the template never asks for
      (a real consent could never be verbatim-confirmed against a table
      that omits it);
    - a toolkit named on both sides whose scope sets disagree (missing/
      extra tool names, either direction);
    - the same toolkit key appearing on more than one template row.
    """
    problems: list[str] = []
    seen_keys: dict[str, str] = {}
    for row in rows:
        if row.toolkit_key in seen_keys:
            problems.append(
                f"toolkit {row.toolkit_key!r} appears on more than one template "
                f"row ({seen_keys[row.toolkit_key]!r} and {row.display!r})"
            )
        seen_keys[row.toolkit_key] = row.display

        required_scopes = required.get(row.toolkit_key)
        if required_scopes is None:
            problems.append(
                f"template row {row.display!r} names toolkit {row.toolkit_key!r}, "
                "which consent.py's REQUIRED_SCOPES does not require at all"
            )
            continue
        if row.scopes != required_scopes:
            missing = sorted(required_scopes - row.scopes)
            extra = sorted(row.scopes - required_scopes)
            problems.append(
                f"toolkit {row.toolkit_key!r}: template row {row.display!r} drifts from "
                f"REQUIRED_SCOPES (missing={missing}, extra={extra})"
            )

    template_keys = {row.toolkit_key for row in rows}
    for toolkit_key in sorted(set(required) - template_keys):
        problems.append(
            f"consent.py requires toolkit {toolkit_key!r}, but no template row names it"
        )
    return problems


def check(template_path: str = DEFAULT_TEMPLATE_PATH) -> tuple[bool, str]:
    if not os.path.exists(template_path):
        return False, f"template not found: {template_path}"
    with open(template_path, encoding="utf-8") as f:
        text = f.read()
    rows = parse_template_scopes(text)
    if not rows:
        return False, f"no scope-confirm table rows parsed out of {template_path}"
    problems = find_drift(rows, REQUIRED_SCOPES)
    if problems:
        return False, "drift found:\n  - " + "\n  - ".join(problems)
    return True, (
        f"clean ({len(rows)} toolkit row(s) in {os.path.basename(template_path)}, "
        f"byte-identical to consent.py's REQUIRED_SCOPES, no drift)"
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] != "check":
        print("usage: python3 tools/consent_template_scope_check.py check [<template_path>]")
        return 2
    template_path = argv[1] if len(argv) > 1 else DEFAULT_TEMPLATE_PATH
    ok, msg = check(template_path)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
