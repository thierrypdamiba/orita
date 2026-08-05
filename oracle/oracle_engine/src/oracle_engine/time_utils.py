"""Shared helpers twenty-five-plus Oracle Desk cadence modules each once
carried a private, byte-identical copy of.

`parse_ts`: parse an ISO-8601 string, and if it names no timezone, assume
it means UTC (the same assumption every snapshot writer in this package
already makes when it stamps `ts` with
`datetime.now(timezone.utc).isoformat()`).

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

`load_snapshots`: task 516's own AST-hash sweep of this package caught
`_parse_ts` and `_default_http_get` but missed a third byte-identical
function living in the same 25 `*_cadence.py` files (task 523 caught it,
a live re-run of the identical method one function further than task 516
took it) — read every line of a JSONL snapshot log, marking any line that
isn't valid JSON, or valid JSON but not an object, as `{"_malformed":
True, ...}` rather than raising. Unlike `parse_ts`, this one can't be a
bare name rebinding (`load_snapshots = time_utils.load_snapshots`):
every sibling module's own `load_snapshots(path=DEFAULT_SNAPSHOT_PATH)`
default differs (each cadence writes its own snapshot file), and
`load_snapshots()` is called bare, relying on that default, all over
each cadence module's own scan functions. So each sibling keeps a
thin wrapper with its own default that delegates to `load_snapshots`
below — `tests/test_time_utils.py` asserts every sibling's wrapper
actually calls through to this shared function (not a reinlined copy),
by patching this module's `load_snapshots` and observing every sibling
call it.

`record_snapshot`: task 559's own re-run of the identical AST-hash sweep,
carried one directory over from `tools/*.py` (where it had already run
dry six times running — tasks 546/548/551/552/555/558) into
`oracle_engine/*_cadence.py` for the first time, found this package's own
FOURTH byte-identical function, still standing after `_parse_ts` and
`load_snapshots` were both pulled out: append one `{"ts", "count"}`
snapshot line, refusing a bool/non-int/negative count. Every one of the
25 siblings carried its own copy, differing only in which module-specific
`*CadenceError` subclass it raised on bad input and a few words of
docstring — the write logic itself (`json.dumps(..., sort_keys=True)`,
`os.makedirs(parent, exist_ok=True)`, append-only) was byte-identical
across all 25. Same shape as `load_snapshots` above and for the same
reason: not a bare name rebinding, since each sibling's own
`record_snapshot(count, ts, path=DEFAULT_SNAPSHOT_PATH)` default and
error class both differ. Each sibling keeps a thin wrapper with its own
default and its own `error_cls`, delegating the actual validate-and-write
to `record_snapshot` below — `tests/test_time_utils.py`'s
`RecordSnapshotDelegatesCase` proves every wrapper genuinely calls
through (by patching this module's `record_snapshot` and observing every
sibling call it) and that the right error class still surfaces on bad
input.

Usage: not run directly; imported by oracle_engine's cadence modules.
"""
from __future__ import annotations

import datetime
import json
import os


def parse_ts(ts: str) -> datetime.datetime:
    """Parse an ISO-8601 timestamp; a naive result (no tzinfo) is assumed
    UTC, never local time — every snapshot in this package is written in
    UTC, so a bare `2026-08-03T12:00:00` here means UTC, not "whatever
    timezone this machine happens to be in."""
    dt = datetime.datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def load_snapshots(path: str) -> list[dict]:
    """Every snapshot line, in file order. Read-only: never touches the
    file, takes its path and hands back plain dicts. A line that is not
    even valid JSON any more (a bad hand-edit, a stray merge-conflict
    marker, a truncated write) is not allowed to crash the caller with an
    uncaught json.JSONDecodeError -- it comes back marked
    {"_malformed": True, "_error": ...} instead, the same convention
    tools/ledger.py's _entries() established (task 238) and tasks 239-249
    mirrored across every tools/*.py sibling. A line that parses cleanly
    as JSON but is not itself an object (a bare int/float/bool/null/list/
    string -- a truncated write landing mid-value) is marked the same way
    instead of sailing through unmarked, the second half of the guard
    task 328 closed for tools/toolkits_in_use_check.py."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                out.append({"_malformed": True, "_error": str(exc)})
                continue
            if not isinstance(value, dict):
                out.append({"_malformed": True, "_error": "not a JSON object"})
                continue
            out.append(value)
    return out


def record_snapshot(
    count: int, ts: str, path: str, error_cls: type[Exception] = ValueError
) -> dict:
    """Append one `{"ts", "count"}` snapshot. Append-only — no caller
    rewrites a prior line. `count` must be a non-negative, non-bool int;
    on a bad value this raises `error_cls` (each cadence sibling passes
    its own `*CadenceError` subclass here, so a caller sees the same
    exception type it always has, not a generic one from a shared
    module it may not import)."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise error_cls("count must be a non-negative integer")
    entry = {"ts": ts, "count": int(count)}
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry
