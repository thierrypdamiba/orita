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

`reject_malformed`: task 563's own re-run of the same AST-hash sweep found
this package's own FIFTH byte-identical function, still standing after
`_parse_ts`/`load_snapshots`/`record_snapshot` were each pulled out —
raise on any snapshot line `load_snapshots` had already marked
`_malformed`, so a lookup walking the whole log never silently treats a
corrupted line as absent. All 25 siblings carried their own copy, hand-
written back in tasks 250-274 before this module existed and never
revisited when the other three were consolidated — differing only in
which module-specific `*CadenceError` subclass they raised, same shape
`record_snapshot` already had. Each sibling keeps a thin wrapper
delegating to `reject_malformed` below with its own `error_cls`, the same
discipline `record_snapshot`'s wrappers use — `tests/test_time_utils.py`'s
`RejectMalformedDelegatesCase` proves every wrapper genuinely calls
through and that the right error class still surfaces on a malformed
line.

`count_at_or_before` / `count_at_or_after`: task 578's own re-run of the
same AST-hash sweep, going one function further than task 563 stopped in
this same file, found this package's own SIXTH and SEVENTH byte-identical
functions, still standing untouched after `_parse_ts`/`load_snapshots`/
`record_snapshot`/`reject_malformed` were each pulled out (task 573's
`seal_generic_prediction` consolidation, the "sixth" by `prediction.py`'s
own count, lives in that sibling module, not this one — these two are
`time_utils.py`'s own sixth and seventh). All 25 `*_cadence.py` siblings
carried `X_count_at_or_before`/`X_count_at_or_after` -- reject malformed
lines via the sibling's own `_reject_malformed`, then scan every snapshot
for the closest one at-or-before / at-or-after `when` -- with the
executable logic byte-identical across every sibling; the only variation
anywhere was docstring wording (an em dash vs a double-hyphen, one line
wrapped differently) and the caller-name string literal, confirmed by
normalizing each sibling's function name out of its own body before
hashing (four distinct hashes for 25 files, and diffing them showed
prose only, never logic). Each sibling keeps its own `_reject_malformed`
call first (so a malformed line still raises that module's own
`*CadenceTamperedError`, not a shared-module exception) and delegates
only the scan-and-compare to `count_at_or_before`/`count_at_or_after`
below, which assume the caller already rejected malformed lines --
`tests/test_time_utils.py`'s `CountAtOrBeforeAfterDelegatesCase` proves
every sibling wrapper genuinely calls through (by patching this module's
two functions and observing every sibling reach them), not a reinlined
copy of the old loop.

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


def reject_malformed(
    snapshots: list[dict], caller: str, error_cls: type[Exception] = ValueError
) -> None:
    """Raise `error_cls` if any snapshot line came back marked
    `_malformed` by `load_snapshots()` -- every caller across the 25
    cadence siblings walks every snapshot, not just the tip, so a
    malformed line anywhere could be hiding the real closest one and
    silently skipping it would misreport the delta/baseline."""
    for s in snapshots:
        if s.get("_malformed"):
            raise error_cls(
                f"{caller}: the snapshot log holds a line that is not "
                f"valid JSON ({s.get('_error')}) -- refusing rather than "
                "silently skipping it."
            )


def count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet -- never guessed at, never
    interpolated. Assumes the caller has already rejected malformed lines
    (via `reject_malformed`) -- this function only scans and compares,
    it does not itself check for `_malformed` markers, so a caller that
    skips that step could silently read `s["ts"]`/`s["count"]` off a
    marker dict and raise a confusing `KeyError` instead of its own
    `*CadenceTamperedError`."""
    best = None
    for s in snapshots:
        ts = parse_ts(s["ts"])
        if ts <= when and (best is None or ts > parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `count_at_or_before`: once a call's window closes, the honest outcome
    is the first real observation once the window is actually over, not a
    later one that could quietly wait for a friendlier number. Same
    caller contract as `count_at_or_before` above -- malformed lines must
    already be rejected."""
    best = None
    for s in snapshots:
        ts = parse_ts(s["ts"])
        if ts >= when and (best is None or ts < parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None
