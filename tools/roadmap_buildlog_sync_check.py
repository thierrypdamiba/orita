#!/usr/bin/env python3
"""Task 1018. Nisaba/Retrya close the gap task 1017 named honestly.

Task 1017 (`esu-elegba`) found ROADMAP.md rows 1015 and 1016 missing
entirely -- real, shipped, journaled, BUILDLOG-logged work under those
numbers that never got a matching row written into ROADMAP.md's own task
table. It backfilled both rows from verifiable evidence and named the gap
rather than patch it silently: "build a standing ROADMAP/BUILDLOG sync
checker" (this task), the same way `tools/wip_reclaim_check.py` (task 123)
already reads ROADMAP.md's WIP state live and `tools/journal_numbering_check.py`
(task 119) already reads each house's journal sequence live. A work queue
that silently drops a row is exactly the "flattering record" doctrine task
145 already named and closed elsewhere (`toolkits_in_use_check.py`,
`connected_users_check.py`, ...); this closes the same shape here, one
level up -- the queue itself, not a metric inside it.

BUILDLOG.md is the ground truth for "what actually shipped": one line per
task, `YYYY-MM-DD HH:MM UTC | <god> | <task#> | <one line>`, and -- unlike
ROADMAP.md -- it is never archived out from under itself
(`tools/tasks_shipped_check.py`'s own task 416 note already confirmed
zero references to BUILDLOG.md anywhere in `tools/roadmap_archive.py`).
ROADMAP.md IS archived: `tools/roadmap_archive.py` (task 169) periodically
cuts a fully-DONE prefix out of the live file into a dated
`ROADMAP-ARCHIVE-NNN-<first>-<last>.md`, so a task number BUILDLOG.md
mentions from months ago will correctly be absent from the live
ROADMAP.md and present only in one of the archive files -- this module
reads the live file PLUS every `ROADMAP-ARCHIVE-*.md` sibling before
calling a number missing, the identical union
`tests/test_wip_reclaim_check.py`'s own
`test_real_roadmap_has_no_row_number_gaps_up_to_its_own_highest_task`
already builds for its own, narrower row-numbering-gap check.

A BUILDLOG row's task-field cell is not always a single bare number:
multi-task rows exist (`360/361`, one hour closing two tasks) and
housekeeping rows carry a non-numeric marker (`ritual`, `daily`, `hourly`,
`ledger`, `reconcile`, `roadmap` -- never a real ROADMAP task, never
counted by any prior ground-truth reader either, `tasks_shipped_check.py`'s
own precedent). Every run of digits in that cell is pulled out and
compared against the ROADMAP union independently, the same `_NUM_RE`
approach `tasks_shipped_check.py` already established for the identical
column -- a housekeeping row with no digits at all contributes nothing to
check, never a false miss.

Task 1018's own first draft hand-typed these same three patterns as new
local `re.compile(...)` literals -- exactly the "claimed mirror with
nothing backing it" shape `tools/duplicate_regex_check.py` (task 397)
exists to catch, and it caught this file the moment it was wired into
`ritual_check.py`'s live sweep. Fixed the same way that campaign's own
docstring prescribes: import the real, already-defined pattern objects
from the files that own them (`roadmap_archive.ROW_RE`,
`tasks_shipped_check._ROW_RE`/`_NUM_RE`) instead of retyping their text.

Usage:
    python3 tools/roadmap_buildlog_sync_check.py check
"""
from __future__ import annotations

import os
import sys
from typing import cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import roadmap_archive  # noqa: E402
import tasks_shipped_check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROADMAP_PATH = os.path.join(ROOT, "ROADMAP.md")
DEFAULT_BUILDLOG_PATH = os.path.join(ROOT, "BUILDLOG.md")
DEFAULT_ARCHIVE_DIR = ROOT

# Task 169's `roadmap_archive.py` own `ROW_RE`: group 1 is the task number,
# read the same way from both the live file and every archive it produces.
_ROADMAP_ROW_RE = roadmap_archive.ROW_RE
# Task 416's `tasks_shipped_check.py` own `_ROW_RE`: group 3 is the raw
# task-field cell, which may hold a plain number, a multi-task cell, or a
# non-numeric housekeeping marker.
_BUILDLOG_ROW_RE = tasks_shipped_check._ROW_RE
_NUM_RE = tasks_shipped_check._NUM_RE


def roadmap_task_numbers(
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
    archive_dir: str = DEFAULT_ARCHIVE_DIR,
) -> set[int]:
    """Every task number appearing in a `| # | ... |` row anywhere the town
    keeps its work queue: the live `ROADMAP.md` plus every sibling
    `ROADMAP-ARCHIVE-*.md` file task 169's archiver has ever cut out of it.
    A number archived out of the live file is not a missing number -- it
    moved, it did not vanish."""
    numbers: set[int] = set()
    if os.path.exists(roadmap_path):
        with open(roadmap_path, encoding="utf-8") as f:
            numbers.update(int(n) for n, _status in _ROADMAP_ROW_RE.findall(f.read()))
    if os.path.isdir(archive_dir):
        for name in sorted(os.listdir(archive_dir)):
            if name.startswith("ROADMAP-ARCHIVE-") and name.endswith(".md"):
                with open(os.path.join(archive_dir, name), encoding="utf-8") as f:
                    numbers.update(int(n) for n, _status in _ROADMAP_ROW_RE.findall(f.read()))
    return numbers


def buildlog_task_numbers(buildlog_path: str = DEFAULT_BUILDLOG_PATH) -> dict[int, str]:
    """{task_number: first BUILDLOG.md line it was mentioned on} for every
    real numbered task BUILDLOG.md records shipping. A row's task-field
    cell can name more than one task (`360/361`) or none at all
    (`ritual`, `daily`, `hourly`, `ledger`, `reconcile`, `roadmap` --
    housekeeping markers, never a real task number); every run of digits
    found in that cell is its own entry. The FIRST line a number appears
    on wins (usually its own WIP-open or DONE row), kept only so a
    mismatch can be reported against something a human can go read, never
    used to decide clean/missing itself."""
    numbers: dict[int, str] = {}
    if not os.path.exists(buildlog_path):
        return numbers
    with open(buildlog_path, encoding="utf-8") as f:
        for line in f:
            m = _BUILDLOG_ROW_RE.match(line)
            if not m:
                continue
            for n in _NUM_RE.findall(m.group(3)):
                num = int(n)
                if num not in numbers:
                    numbers[num] = line.rstrip("\n")
    return numbers


def check_sync(
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
    buildlog_path: str = DEFAULT_BUILDLOG_PATH,
    archive_dir: str = DEFAULT_ARCHIVE_DIR,
) -> dict[str, object]:
    """Every numbered task BUILDLOG.md records shipping must have a
    matching row somewhere in ROADMAP.md's own task table (live or
    archived) -- the exact invariant task 1017 found broken for rows
    1015/1016 and backfilled by hand. `clean=False` names each missing
    task number and the real BUILDLOG.md line it was found on, never a
    bare pass/fail."""
    roadmap_nums = roadmap_task_numbers(roadmap_path, archive_dir)
    buildlog_map = buildlog_task_numbers(buildlog_path)
    missing = sorted(n for n in buildlog_map if n not in roadmap_nums)
    return {
        "clean": not missing,
        "missing": [{"number": n, "buildlog_line": buildlog_map[n]} for n in missing],
        "roadmap_task_count": len(roadmap_nums),
        "buildlog_task_count": len(buildlog_map),
    }


def format_result(result: dict[str, object]) -> str:
    if result["clean"]:
        return (
            f"roadmap/buildlog sync: clean ({result['buildlog_task_count']} BUILDLOG.md task(s), "
            f"all present in ROADMAP.md live+archived)"
        )
    missing = cast("list[dict[str, object]]", result["missing"])
    lines = [f"roadmap/buildlog sync: {len(missing)} MISSING ROADMAP ROW(S)"]
    for m in missing:
        lines.append(
            f"  task {m['number']}: shipped per BUILDLOG.md but no row in ROADMAP.md "
            f"(live or archived) -- backfill it, escalate now\n"
            f"    {m['buildlog_line']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_sync()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
