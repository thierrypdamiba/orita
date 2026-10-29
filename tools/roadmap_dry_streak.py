#!/usr/bin/env python3
"""Task 2282. Kothar builds the gauge nobody plugged in.

Every hourly commit since task 1911 (2026-10-02) has hand-typed a claim
like "ROADMAP still dry since task 1911 (N straight hours)" straight into
its own BUILDLOG.md row and journal, estimated by eye from the previous
hour's own stated number rather than computed from anything on record.
Nothing in `ritual_check.py`'s own fold ever cross-checked that number
against the one timestamp that actually anchors it: the `<!-- wip-opened:
1911 ... -->` marker on task 1911's own ROADMAP.md row, the hour the
roadmap last ran dry.

Checked live the hour this module was written: task 1911 opened WIP at
`2026-10-02T17:23:51Z`. Against this hour's real clock (2026-10-29,
hour 22 UTC), that is just over 653 real hours -- while the prior several
hours' own commit messages and journals had drifted to claiming numbers in
the 336-370 range, roughly half the real figure, apparently compounding a
small per-hour undercount across dozens of hand-typed estimates with
nothing ever re-deriving the true count from the source timestamp. Named
honestly here as a real, previously-unflagged inaccuracy in the town's own
running claim (the same "a stale number nobody re-derives" shape
`report_accuracy_check.py`'s own module docstring already warns about) --
not corrected retroactively in any sealed BUILDLOG.md row or journal,
since those are historical record, not live state (Iron Rule: nothing
public is rewritten after the fact).

This module is the fix going forward: a pure, read-only function that
parses the real `wip-opened` timestamp for a given anchor task straight
off the live ROADMAP.md, computes the real elapsed hours against the
caller's own `now`, and prints it -- so the next hour that wants to name
the streak quotes this instead of eyeballing the last hour's prose.

Usage:
    python3 tools/roadmap_dry_streak.py status [--task N] [--roadmap PATH]
"""
from __future__ import annotations

import datetime
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROADMAP = os.path.join(ROOT, "ROADMAP.md")
DEFAULT_ANCHOR_TASK = 1911

_WIP_OPENED = re.compile(r"<!--\s*wip-opened:\s*(\d+)\s+([0-9T:+-]+Z)\s*-->")


class AnchorNotFoundError(ValueError):
    """Raised when the requested anchor task carries no `wip-opened` marker
    on its own ROADMAP.md row -- the anchor must be verifiable from the
    live file, never assumed."""


def find_wip_opened(task: int, roadmap_path: str = DEFAULT_ROADMAP) -> datetime.datetime:
    """Returns the real `wip-opened` timestamp recorded on `task`'s own
    ROADMAP.md row. Raises `AnchorNotFoundError` if that task carries no
    such marker (never silently falls back to a guess)."""
    with open(roadmap_path, encoding="utf-8") as f:
        text = f.read()
    for match in _WIP_OPENED.finditer(text):
        if int(match.group(1)) == task:
            ts = match.group(2)
            return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=datetime.timezone.utc
            )
    raise AnchorNotFoundError(
        f"task {task} carries no <!-- wip-opened: {task} ... --> marker in {roadmap_path!r}"
    )


def hours_since(task: int, now: datetime.datetime, roadmap_path: str = DEFAULT_ROADMAP) -> float:
    """Real elapsed hours between `task`'s own recorded wip-opened moment
    and `now` (caller-supplied so this stays pure and testable -- it never
    calls `datetime.now()` itself)."""
    opened = find_wip_opened(task, roadmap_path)
    return (now - opened).total_seconds() / 3600.0


def format_status(task: int, now: datetime.datetime, roadmap_path: str = DEFAULT_ROADMAP) -> str:
    hours = hours_since(task, now, roadmap_path)
    return (
        f"roadmap dry streak: {hours:.1f} real hours since task {task} opened WIP "
        f"(the hour the roadmap last ran dry) -- computed from the live "
        f"wip-opened marker, not hand-estimated"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "status":
        print(__doc__)
        sys.exit(1)
    argv = argv[1:]
    task = DEFAULT_ANCHOR_TASK
    roadmap_path = DEFAULT_ROADMAP
    if "--task" in argv:
        i = argv.index("--task")
        task = int(argv[i + 1])
        del argv[i : i + 2]
    if "--roadmap" in argv:
        i = argv.index("--roadmap")
        roadmap_path = argv[i + 1]
        del argv[i : i + 2]
    try:
        print(format_status(task, datetime.datetime.now(datetime.timezone.utc), roadmap_path))
    except AnchorNotFoundError as exc:
        print(f"roadmap dry streak: error -- {exc}")
        sys.exit(1)
