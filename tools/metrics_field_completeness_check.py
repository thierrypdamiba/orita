#!/usr/bin/env python3
"""Task 459. Ogun closes the loop his own task 453 opened.

Task 453 named one bug shape living across `records/metrics.jsonl`'s own
cross-checkers: `last is None or "FIELD" not in last` collapsed two
distinct facts into a single unconditional clean -- "no reading has ever
existed" (genuinely nothing to contradict) and "a reading exists but
silently drops the one field it exists to guard" (the real gap). Tasks
454-458 (Off-By-One, Nisaba) found and fixed all six live instances by
hand, one grep at a time (`gap_true_positive_check.py`,
`toolkits_in_use_check.py`, `report_shipped_check.py`,
`github_stars_check.py`, `connected_users_check.py`,
`tasks_shipped_check.py`), and task 458's own closing note confirmed the
shape absent repo-wide by direct grep. What none of those six tasks
built is a standing guarantee that a SEVENTH field -- one that does not
exist yet -- gets a cross-checker the day it is ever added to
`records/metrics.jsonl`. Every field happening to have one today is a
fact about today, not a law enforced in code; the next field added
without a matching checker would sit silently unguarded exactly as long
as `tasks_shipped_today` did between task 416 (which recorded it) and
task 458 (which first guarded it) -- 42 tasks, unnoticed until a
background sweep went looking on purpose.

This module is the third of its family: `ritual_completeness_check.py`
(task 121, Off-By-One) proves every `check_*` function in
`ritual_check.py` is actually wired and printed; `scopes_completeness_
check.py` (task 135, Ogun) proves every app connected on the shared
gateway is named in the Oath's own accounting table. This one proves
every field ever recorded in `records/metrics.jsonl` is guarded by a
real cross-check.

Structural, not a hardcoded list of expected field names (a hardcoded
list would itself go stale the same way the six checkers' own omitted
guard once did): reads every field key that has ever appeared in any
`records/metrics.jsonl` line (excluding `date` and `notes`, the two
structural fields every row carries that are not themselves a tracked
metric), then greps every `tools/*_check.py` file's own source (other
than this one) for that field name appearing as a quoted Python string
literal -- `"field_name"` or `'field_name'` -- the exact shape every one
of the six real cross-checkers already uses to read the field back out
of a parsed JSON line (e.g. `toolkits_in_use_check.py`'s own
`"distinct_toolkits_in_use" not in last`). A field named only in a
docstring's prose, in backticks, never as an actual quoted-string code
reference, does not count -- the same "structural, not narrative"
discipline `scopes_completeness_check.py`'s own docstring already draws
between a real accounted-for table row and a passing mention.

Local-filesystem-only, no network call of its own, the same read-only
boundary `duplicate_regex_check.py`/`ritual_completeness_check.py`
already hold.

Usage:
    python3 tools/metrics_field_completeness_check.py check
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_METRICS_PATH = os.path.join(ROOT, "records", "metrics.jsonl")
DEFAULT_TOOLS_DIR = os.path.join(ROOT, "tools")

# The two fields every real metrics.jsonl row carries that are not
# themselves a tracked metric needing its own cross-checker: `date` keys
# the row, `notes` is free-text narration. Neither is a candidate for an
# "unguarded field" violation.
STRUCTURAL_FIELDS = frozenset({"date", "notes"})

_SELF_PATH = os.path.abspath(__file__)


def _metrics_fields(metrics_path: str) -> set:
    """Every non-structural field key that has ever appeared in any line
    of `records/metrics.jsonl`. A malformed line is skipped, not raised
    -- this check exists to name unguarded fields, not to duplicate a
    JSONL-integrity check some other module already owns. Missing file
    returns an empty set (nothing recorded yet is not a violation)."""
    fields = set()
    if not os.path.isfile(metrics_path):
        return fields
    with open(metrics_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                fields |= set(row.keys())
    return fields - STRUCTURAL_FIELDS


def _quoted_literal_pattern(field: str) -> re.Pattern:
    escaped = re.escape(field)
    return re.compile(rf"""(["']){escaped}\1""")


def _guarded_fields(tools_dir: str, fields: set) -> set:
    """The subset of `fields` that appear as a quoted string literal
    somewhere in a `tools/*_check.py` file's own source. This module's
    own file is excluded so it can never satisfy its own check merely by
    naming a field in this docstring or its `STRUCTURAL_FIELDS`/test
    fixtures."""
    guarded = set()
    remaining = set(fields)
    if not remaining:
        return guarded
    check_files = sorted(glob.glob(os.path.join(tools_dir, "*_check.py")))
    for path in check_files:
        if not remaining:
            break
        if os.path.abspath(path) == _SELF_PATH:
            continue
        with open(path, encoding="utf-8") as f:
            src = f.read()
        for field in list(remaining):
            if _quoted_literal_pattern(field).search(src):
                guarded.add(field)
                remaining.discard(field)
    return guarded


def check_metrics_field_completeness(
    metrics_path: str = DEFAULT_METRICS_PATH,
    tools_dir: str = DEFAULT_TOOLS_DIR,
) -> dict:
    """Returns `clean: True` with the guarded field set when every
    non-structural field ever recorded in `records/metrics.jsonl` is
    referenced as a quoted string literal in some `tools/*_check.py` file
    other than this one; otherwise `clean: False` and the specific
    unguarded field name(s) -- never a pass/fail without saying which
    field is exposed."""
    fields = _metrics_fields(metrics_path)
    guarded = _guarded_fields(tools_dir, fields)
    unguarded = sorted(fields - guarded)
    return {
        "clean": not unguarded,
        "fields": sorted(fields),
        "guarded": sorted(guarded),
        "unguarded": unguarded,
    }


def format_result(result: dict) -> str:
    if result["clean"]:
        return (
            f"metrics field completeness: clean ({len(result['fields'])} field(s) ever recorded in "
            "records/metrics.jsonl, every one guarded by a tools/*_check.py cross-check)"
        )
    lines = [
        f"metrics field completeness: {len(result['unguarded'])} UNGUARDED FIELD(S) -- "
        "recorded in records/metrics.jsonl but never referenced as a quoted literal by any "
        "tools/*_check.py cross-check"
    ]
    for field in result["unguarded"]:
        lines.append(f"  {field!r}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_metrics_field_completeness()
    print(format_result(result))
    sys.exit(1 if result["unguarded"] else 0)
