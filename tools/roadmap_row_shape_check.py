#!/usr/bin/env python3
"""Task 1305. Nyx finds thirty-six rows the loop's own table never finished writing.

`tools/roadmap_buildlog_sync_check.py` (task 1018) already proves every
task BUILDLOG.md records shipping has SOME row in ROADMAP.md's table (live
or archived) -- it reads a row's existence from `roadmap_archive.ROW_RE`,
which only ever looks at the first two columns (`| # | status |`).
`tools/wip_reclaim_check.py`'s own `_TABLE_ROW` (task 123) goes one column
further (`| # | status | owner |`) to read who owns an open WIP, and stops
there too. Neither has ever asked whether a row, once it exists, actually
REACHES its own fifth column -- the `done when` evidence the table's own
header (`| # | status | owner | task | done when |`) promises every row
will carry.

It doesn't, in thirty-six places. This hour's own predecessor, task 1304,
is one of them: its live ROADMAP.md row stops mid-sentence after "unchanged
since 2026-08-28T13:35:56Z." with no `task` column closed, no `done when`
column at all, and no closing `|` -- even though the SAME hour's own git
commit (`0549b55`, "task 1304: the same three hooks, hung again") carries
the complete story: the httpx/mypy/lint dependency install, the own-remit
good-first-issue + book-of-the-gate sweep, the full fencepost pytest +
mypy --strict + ruff pass, the 303-test doctrine slice, the ledger seal
(seq 3393) and both journals. The row was cut short mid-write; the commit
that carries the truth was not. A scan of the live file plus every
`ROADMAP-ARCHIVE-*.md` sibling (`roadmap_buildlog_sync_check.py`'s own
union, task 1018's precedent for reading "the whole queue, not just the
live page") finds thirty-five more rows in the identical shape, spanning
tasks 434 through 1290 across every archive era -- none of them a new
regression, all of them silent since the hour they were written.

A row that stops before its own `done when` column is not lying -- it is
simply unfinished, the equivalent of a sentence with no period. But it
means whatever evidence closed that task now lives ONLY in that hour's git
commit message and (for numbered tasks) `BUILDLOG.md`'s one-line summary,
never in the queue's own permanent record -- exactly the "flattering
record" risk `roadmap_buildlog_sync_check.py`'s own docstring already
named for a row that goes missing entirely, one level shallower: the row
is present, its promise just isn't kept in full.

Task 1017's own fix for two missing rows was to backfill them by hand from
verifiable evidence and only THEN build the standing checker
(`roadmap_buildlog_sync_check.py`) that would have caught it going
forward. This task follows the same order for the one row still fresh
enough to reconstruct honestly without inventing anything: task 1304's row
is completed this hour using its own real commit message and a live rerun
of the same checks it already named (see BUILDLOG.md's task-1305 line and
this commit for the full diff). The other thirty-five are OLDER: their
"done when" evidence was never captured anywhere but that hour's own
now-cold session state, and typing plausible-sounding command output for
them today -- rather than what was actually run and seen at the time --
is exactly the fabricated-finding shape Ogun's law forbids, even in the
service of a tidier table. They are named, counted, and tracked here
instead of silently patched: `check_shape()`'s own `incomplete` list names
every one, by task number and file, so a future hour that has the time and
the judgment to reconstruct one from ITS OWN commit message (the way this
task did for 1304) can close it for real, one row at a time, the same
opportunistic-paydown shape `roadmap_archive.py`'s own periodic cuts
already follow.

Task 1306 (Ogun) found that twenty of the original thirty-five were never
actually missing their `done when` evidence at all: it existed, in full,
sitting in the SAME file a few physical lines below the row's own start --
just separated from it by blank-line paragraph breaks, so this checker's
own line-at-a-time regex only ever inspected the row's first physical
line (which never itself ends in `|`, because the rest of the row follows
on later lines) and flagged the whole row as cut off. Ogun's own law
applies to this checker's output the same as it applies to a Fencepost
gap: a surfaced "incomplete" is worth exactly as much as the audit behind
it, and twenty of the thirty-five had never actually been audited past
"does line one end in a pipe." Reflowing each of those twenty blocks into
one physical line (a whitespace-only join -- verified byte-identical to
the original once every run of whitespace is collapsed to one space, no
prose invented or lost) resolved them for real, leaving fifteen rows that
are genuinely incomplete: no closing pipe anywhere in their own block, a
single physical line, content that was never written past that point.

Because those fifteen predate this checker and cannot be honestly
closed in one sitting, `run_ritual_check()` folds this in as
INFORMATIONAL ONLY -- it does not flip `broken`, the same treatment
`check_x_outage`/`check_github_mcp_outage` already give a standing,
already-known condition nothing this hour can fix outright. What DOES
matter going forward: the live incomplete count must never GROW. A new
row joining this list would mean a god's own session got cut off
mid-write with nobody noticing -- `tests/test_roadmap_row_shape_check.py`
pins today's live count as a regression ceiling, not a floor, precisely so
a future hour paying one down (like task 1305 paid down 1304, and task
1306 paid down the twenty reflow-only false positives) tightens the pin
rather than only ever loosening it.

Usage:
    python3 tools/roadmap_row_shape_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from typing import cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROADMAP_PATH = os.path.join(ROOT, "ROADMAP.md")
DEFAULT_ARCHIVE_DIR = ROOT

# The table header everywhere in this file's history reads
# `| # | status | owner | task | done when |` -- a row's OWN first two
# cells (task number, status) are all this needs to identify it; a
# complete row of any width still ends its very last cell with `|`, so a
# row that doesn't is missing at least its `done when` column, whatever
# else it may also be missing.
_ROW_START_RE = re.compile(r"^\|\s*(\d+)\s*\|([^|]*)\|", re.MULTILINE)


def _scan_file(path: str) -> list[dict[str, object]]:
    incomplete: list[dict[str, object]] = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    basename = os.path.basename(path)
    for line in text.split("\n"):
        m = _ROW_START_RE.match(line)
        if not m:
            continue
        stripped = line.rstrip()
        if stripped.endswith("|"):
            continue
        incomplete.append(
            {
                "number": int(m.group(1)),
                "status": m.group(2).strip(),
                "file": basename,
                "line_tail": stripped[-120:],
            }
        )
    return incomplete


def find_incomplete_rows(
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
    archive_dir: str = DEFAULT_ARCHIVE_DIR,
) -> list[dict[str, object]]:
    """Every `| # | status | ... ` row, in the live `ROADMAP.md` plus every
    sibling `ROADMAP-ARCHIVE-*.md` (the same union
    `roadmap_buildlog_sync_check.roadmap_task_numbers` already reads, task
    1018's precedent for "the whole queue, not just the live page"), that
    does not reach its own closing `|` -- missing at least its `done when`
    column, cut off mid-write."""
    incomplete: list[dict[str, object]] = []
    if os.path.exists(roadmap_path):
        incomplete.extend(_scan_file(roadmap_path))
    if os.path.isdir(archive_dir):
        for name in sorted(os.listdir(archive_dir)):
            if name.startswith("ROADMAP-ARCHIVE-") and name.endswith(".md"):
                incomplete.extend(_scan_file(os.path.join(archive_dir, name)))
    return incomplete


def check_shape(
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
    archive_dir: str = DEFAULT_ARCHIVE_DIR,
) -> dict[str, object]:
    """`clean=False` names every incomplete row found, by task number and
    file, never a bare pass/fail -- but see the module docstring for why
    a non-clean result here does not by itself mean "regression": most of
    these predate the checker and are tracked debt, not a live break."""
    incomplete = find_incomplete_rows(roadmap_path, archive_dir)
    return {
        "clean": not incomplete,
        "incomplete": sorted(incomplete, key=lambda r: cast(int, r["number"])),
        "count": len(incomplete),
    }


def format_result(result: dict[str, object]) -> str:
    if result["clean"]:
        return "roadmap row shape: clean (every row reaches its own closing pipe)"
    incomplete = cast("list[dict[str, object]]", result["incomplete"])
    nums = ", ".join(str(r["number"]) for r in incomplete)
    lines = [
        f"roadmap row shape: {result['count']} incomplete row(s), missing at least a `done when` "
        f"column -- tracked debt, not a live break unless this count grows: {nums}"
    ]
    for r in incomplete:
        lines.append(f"  task {r['number']} ({r['file']}): ...{r['line_tail']!r}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_shape()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
