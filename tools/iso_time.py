#!/usr/bin/env python3
"""Task 509. The one-line parser three checkers each carried a private copy of.

`cron_health.py`, `voice_window_check.py`, and `x_outage_tracker.py` each
defined their own byte-identical `_parse(ts)` -- `datetime.fromisoformat`
on a `Z`-suffixed UTC timestamp, normalized to an aware `datetime` via
`.astimezone(timezone.utc)`. This is the exact same shape task 508 named
and closed one file over (`metrics_reader.py`, six duplicated readers):
a duplicated ordinary function, invisible to `tools/duplicate_regex_
check.py` (which only ever inspects `re.compile(...)` call sites, never
duplicated function bodies), sitting unguarded by the one doctrine tool
whose entire purpose is "stop finding drifted copies one at a time."
Found live by an Explore sweep of `tools/*.py` this hour; verified by
diffing all three bodies byte-for-byte (identical).

Consolidated here as the one place this parser is defined. Every sibling
check now imports `parse_iso_utc` from this module instead of carrying
its own copy; `tests/test_iso_time.py` asserts each sibling's `_parse`
name is the identical function object (not just identical source), so a
future edit to one is an edit to all three by construction -- the same
guarantee `metrics_reader.py` gives its own six siblings.

Usage: not run directly; imported by tools/*.py.
"""
from __future__ import annotations

from datetime import datetime, timezone


def parse_iso_utc(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp (`Z`-suffixed or otherwise) into an
    aware `datetime` normalized to UTC. The one shape every call site in
    this repo actually needs -- no timezone-naive input reaches a caller,
    no non-UTC offset preserved past the call.

    A timestamp with no `Z` and no explicit offset (a hand-typed value
    missing the `Z` this repo's own convention always appends -- exactly
    the "a contributor's laptop" risk cron_health.py's own docstring
    names) is assumed UTC, never the machine's local timezone: calling
    `.astimezone(timezone.utc)` directly on a naive `datetime` presumes
    it already represents *local* system time (Python's own documented
    behavior for naive `astimezone()`), so the same input string silently
    parsed to a different instant depending on which machine happened to
    run it -- a canonical UTC parser giving a non-canonical answer.
    `oracle_engine.time_utils.parse_ts` (this repo's sibling parser for
    the identical class of input) already holds the naive-means-UTC line
    explicitly; this now matches it instead of silently disagreeing on
    the one input shape that actually distinguishes the two."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
