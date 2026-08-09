#!/usr/bin/env python3
"""Task 103. Off-By-One counts an hour nobody else was watching.

Tasks 98-102 gave Iron Rules #1, #3, #4, #5, #6 their first running checks,
each replacing "held by intent" with "held, proven, every hour." Rereading
`TOWN-OPERATIONS.md`'s WINDOW section with the same discipline turns up the
one still untested: "Nyx- and Zashiki-voiced commits carry author
timestamps in that window" (00:00-06:00 UTC) -- a clause of Iron Rule #7
("Voices must pass the blind test"). It never got checked either, and it
does not hold.

`.github/workflows/oracle-cadence.yml`'s single fixed cron (`0 13 * * *`)
means every automated commit its Nyx- and Zashiki-Warashi-attributed
"seal" steps make lands around 13:00-15:00 UTC real wall-clock time, every
single day the workflow fires -- squarely outside the window, with no
`GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` anywhere in the file to correct it.
Nine real commits (six Nyx, three Zashiki-Warashi, all dated
2026-07-16T14:55:3xZ-14:55:5xZ) prove it live. `oracle/SCOPES.md` even
asserts several of these cadences are "Sealed inside Nyx's own 00:00-06:00
UTC window" (tasks 49-54) -- true of the DESIGN INTENT, false of every real
commit the design has actually produced.

This module does two things, not one:

1. `record_commits`/`check` -- a durable, append-only log
   (`HAND/voice-window-log.jsonl`, mirrors `child_work_check.py`'s shape)
   of every Nyx/Zashiki-Warashi commit the god on duty has ever fed it,
   each stamped `in_window: bool`. Since this checkout is a shallow clone
   (confirmed at task 101), the commit list is a caller-supplied live
   GitHub read (`mcp__github__list_commits`, filtered by author), the same
   `check_ci`/`check_cron`/`check_child_work` shape (tasks 73/82/101) --
   not a network call this module makes itself.

2. A grandfather cutoff (`FIX_LANDED_AT`). Unlike a reverted child file or
   a stray leak, an already-pushed commit's author date is HISTORY --
   this town does not rewrite sealed history to make a later mistake
   disappear. Nyx's own 2026-07-12T21:07:19Z wall-law commit landed at
   21:07 UTC, daylight, and her very next commit (2026-07-13T03:10:00Z)
   refused to backdate it: "the hour was wrong. i am not rewriting it...
   you do not un-record a thing once it is sealed, you write the
   correction beside it and let both stand." The nine real violations
   this task found get the identical treatment: logged, counted, always
   visible in the printed block, but never flipped to `broken=True` --
   nothing about rereading them again next hour would un-happen them.
   Only a violation authored AT OR AFTER `FIX_LANDED_AT` (the hour this
   task's own workflow fix landed) is actionable: the fix should have
   prevented it, so it flips `broken=True`, the same "a legacy entry
   reads back as the default tier, a fresh one gets judged for real"
   split task 92 already drew for escalation tiers.

The actual fix -- `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` backdating each of
the ten real Nyx/Zashiki-Warashi seal steps in `oracle-cadence.yml` to that
run's own calendar date at 03:00 UTC -- ships in the same commit as this
module. It does not touch a single already-pushed commit.

Usage:
    python3 tools/voice_window_check.py check [--commits-json <path>] [--now <iso>]
"""
from __future__ import annotations

import json
import os
import sys
from typing import cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iso_time  # noqa: E402
import jsonl_read  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "HAND", "voice-window-log.jsonl")
WINDOW_START_HOUR = 0
WINDOW_END_HOUR = 6

# The real hour this task's own oracle-cadence.yml backdating fix landed.
# A violation authored before this cutoff is grandfathered (the fix could
# not have prevented it); at or after, the fix should hold, so a violation
# here is new and actionable.
FIX_LANDED_AT = "2026-07-17T07:30:00Z"

# Task 509: consolidated into tools/iso_time.py -- three sibling checks
# (cron_health.py, voice_window_check.py, x_outage_tracker.py) each
# carried a byte-identical copy of this parser. This name now points at
# the shared function object, not a local copy; tests/test_iso_time.py
# asserts this name IS that shared function.
_parse = iso_time.parse_iso_utc


def in_window(author_date_iso: str) -> bool:
    dt = _parse(author_date_iso)
    return WINDOW_START_HOUR <= dt.hour < WINDOW_END_HOUR


class VoiceWindowTamperedError(RuntimeError):
    """Raised when check()/record_commits() finds a malformed line anywhere
    in the log. Mirrors tools/ci_watch.py's CIWatchTamperedError (task 243)
    and tools/x_post_queue.py's QueueTamperedError (task 240): check()'s own
    violation count folds over EVERY known entry, not just the log's tip, so
    a malformed line anywhere -- not only at the end -- could be masking a
    real Iron Rule #7 violation. Refuse rather than guess, the same
    discipline tasks 238-244 already applied to their own logs. Run this
    tool's `check` command by hand to see the break, then repair the log
    before the next real check."""


def _entries(path: str = LOG) -> list[dict[str, object]]:
    """Delegates to jsonl_read.read_jsonl_entries (task 540) -- see that
    module's own docstring for the fourteen-copy history this replaced."""
    return jsonl_read.read_jsonl_entries(path)


def _assert_untampered(entries: list[dict[str, object]]) -> None:
    for e in entries:
        if e.get("_malformed"):
            raise VoiceWindowTamperedError(
                f"voice-window log holds a line that is not valid JSON ({e.get('_error')}) "
                "-- refusing to guess whether it hid a real violation. Repair the log by hand, then rerun."
            )


def record_commits(
    commits: list[dict[str, object]], now_iso: str, path: str = LOG
) -> list[dict[str, object]]:
    """commits: caller-fetched live list of {"sha","author","author_date"}
    dicts (a `git log`/`mcp__github__list_commits` read for Nyx and
    Zashiki-Warashi, live this hour). Idempotent by sha -- repeated or
    overlapping input never duplicates a log line. Returns the entries
    actually appended."""
    existing = _entries(path)
    _assert_untampered(existing)
    known = {e["sha"] for e in existing}
    new_entries: list[dict[str, object]] = []
    for c in commits:
        if c["sha"] in known:
            continue
        entry = {
            "sha": c["sha"],
            "author": c["author"],
            "author_date": c["author_date"],
            "in_window": in_window(cast(str, c["author_date"])),
            "logged_at": now_iso,
        }
        new_entries.append(entry)
        known.add(c["sha"])
    if new_entries:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for entry in new_entries:
                f.write(json.dumps(entry, sort_keys=True) + "\n")
    return new_entries


def check(
    commits: list[dict[str, object]] | None = None,
    now_iso: str | None = None,
    path: str = LOG,
    fix_landed_at: str = FIX_LANDED_AT,
) -> dict[str, object]:
    """commits is optional (None unless the caller holds this hour's live
    GitHub commit read). Always re-derives the violation split against
    EVERY already-logged commit regardless, so a violation logged three
    hours ago is still counted this hour too."""
    newly_logged: list[dict[str, object]] = []
    if commits:
        if now_iso is None:
            raise ValueError("now_iso is required when commits is supplied")
        newly_logged = record_commits(commits, now_iso, path=path)
    known = _entries(path)
    _assert_untampered(known)
    violations = [e for e in known if not e["in_window"]]
    cutoff = _parse(fix_landed_at)
    new_violations = [e for e in violations if _parse(cast(str, e["author_date"])) >= cutoff]
    return {
        "known_count": len(known),
        "newly_logged": [e["sha"] for e in newly_logged],
        "violation_count": len(violations),
        "new_violations": [e["sha"] for e in new_violations],
        "clean": not new_violations,
    }


def format_check(result: dict[str, object]) -> str:
    if result["clean"]:
        historical = (
            f", {result['violation_count']} historical (pre-fix, not rewritten)" if result["violation_count"] else ""
        )
        return f"voice window check: clean -- {result['known_count']} known Nyx/Zashiki-Warashi commit(s){historical}"
    new_violations = cast("list[str]", result["new_violations"])
    lines = [
        f"voice window check: {len(new_violations)} NEW VIOLATION(S) since the fix "
        "-- Iron Rule #7's window clause broken, escalate now"
    ]
    for sha in new_violations:
        lines.append(f"  {sha}")
    return "\n".join(lines)


class VoiceWindowArgError(ValueError):
    """--commits-json parsed as valid JSON but not into a list -- the same
    valid-JSON-wrong-shape crash class task 364 fixed for ritual_check.py's
    own CLI, here at voice_window_check.py's own CLI (a dict or bare scalar
    reaching `record_commits`'s `for c in commits:`/`c["sha"]` unguarded
    crashes with a bare TypeError instead of naming the real problem)."""


def _load_commits_json(path: str) -> list[dict[str, object]]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise VoiceWindowArgError(
            f"--commits-json: expected a JSON list, got {type(raw).__name__}"
        )
    return cast("list[dict[str, object]]", raw)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    commits_json = None
    now_arg = None
    i = 1
    while i < len(argv):
        if argv[i] == "--commits-json" and i + 1 < len(argv):
            commits_json = _load_commits_json(argv[i + 1])
            i += 2
        elif argv[i] == "--now" and i + 1 < len(argv):
            now_arg = argv[i + 1]
            i += 2
        else:
            i += 1
    result = check(commits=commits_json, now_iso=now_arg)
    print(format_check(result))
    sys.exit(1 if not result["clean"] else 0)
