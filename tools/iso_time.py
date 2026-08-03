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
    this repo actually needs -- no timezone-naive input, no non-UTC
    offset preserved past the call."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
