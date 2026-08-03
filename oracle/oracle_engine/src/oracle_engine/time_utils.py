"""The one-line ISO-timestamp parser twenty-six Oracle Desk cadence
modules (`branch_cadence.py` through `workflow_cadence.py`, plus
`autograde.py`) each carried a private, byte-identical copy of: parse an
ISO-8601 string, and if it names no timezone, assume it means UTC (the
same assumption every snapshot writer in this package already makes when
it stamps `ts` with `datetime.now(timezone.utc).isoformat()`).

Found live by the same AST-hash sweep `tools/iso_time.py` (task 509) and
`tools/metrics_reader.py` (task 508) already ran one directory over in
`tools/*.py` — `tools/duplicate_regex_check.py` only ever inspects
`re.compile(...)` call sites, never duplicated function bodies, so this
class of drift is invisible to it by construction, in `oracle_engine/`
exactly as it was in `tools/`.

Consolidated here as the one place this parser is defined. Every sibling
module now points its own `_parse_ts` name at `parse_ts` below (the same
function object, not a copy — `tests/test_time_utils.py` asserts identity
across every sibling), so a future fix to the parsing rule is a fix
everywhere at once instead of twenty-six separate hand-edits.

Usage: not run directly; imported by oracle_engine's cadence modules.
"""
from __future__ import annotations

import datetime


def parse_ts(ts: str) -> datetime.datetime:
    """Parse an ISO-8601 timestamp; a naive result (no tzinfo) is assumed
    UTC, never local time — every snapshot in this package is written in
    UTC, so a bare `2026-08-03T12:00:00` here means UTC, not "whatever
    timezone this machine happens to be in."""
    dt = datetime.datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt
