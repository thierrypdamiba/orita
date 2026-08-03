#!/usr/bin/env python3
"""Task 508. The one reader six checkers each carried a private copy of.

`connected_users_check.py`, `gap_true_positive_check.py`,
`github_stars_check.py`, `report_shipped_check.py`, `tasks_shipped_check.py`,
and `toolkits_in_use_check.py` each defined their own byte-identical
`_last_metrics_entry()` -- walk `records/metrics.jsonl` from the end,
skip malformed/non-dict lines, return the first well-formed reading.
Every copy's own docstring narrated the drift risk ("the same discipline
X.py's own reader holds") while doing nothing to prevent it: a fix to
one copy (tasks 306, 328) had already failed to propagate to the other
five, silently, for months. `tools/duplicate_regex_check.py` exists to
catch exactly this shape of drift but only ever inspects `re.compile(...)`
call sites -- a duplicated ordinary function is structurally invisible to
its AST scan, so six copies of one reader sat completely unguarded by the
one doctrine tool whose entire purpose is "stop finding drifted copies
one at a time." Found live by an Explore sweep this hour; verified by
diffing all six bodies byte-for-byte (identical past the docstring).

Consolidated here as the one place this reader is defined. Every sibling
check now imports `last_metrics_entry` from this module instead of
carrying its own copy; `tests/test_metrics_reader.py` asserts each
sibling's `_last_metrics_entry` name is the identical function object
(not just identical source), so a future edit to one is an edit to all
six by construction -- the drift this file exists to end can't recur.

Usage: not run directly; imported by tools/*_check.py.
"""
from __future__ import annotations

import json
import os


def last_metrics_entry(metrics_path: str) -> dict | None:
    """The most recently recorded dated reading in `records/
    metrics.jsonl` -- one append-only file, not one file per day. Walks
    non-blank lines from the end and returns the first one that parses
    as valid JSON AND is itself a JSON object -- a truncated/malformed
    trailing line, or one that parses cleanly but isn't a dict (a bare
    `true`/`42`/`3.14`/`null`/a JSON array), is skipped, not fatal.
    `None` if no reading has ever shipped, or every line is
    malformed/non-dict (nothing to cross-check yet, not an error)."""
    if not os.path.exists(metrics_path):
        return None
    with open(metrics_path, encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None
