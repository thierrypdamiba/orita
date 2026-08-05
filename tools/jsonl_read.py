#!/usr/bin/env python3
"""Task 540. The read-a-JSONL-log helper fourteen checkers each carried a
private copy of.

`arcade_app_watch.py`, `change_gate.py`, `child_work_check.py`,
`ci_watch.py`, `consent_grant_log.py`, `gateway_toolset_check.py`,
`github_stars_check.py`, `ledger.py`, `scribe_growth_check.py`,
`square_check.py`, `voice_window_check.py`, `word_watch.py`,
`x_outage_tracker.py`, and `x_post_queue.py` each defined their own
`_entries(path=...)`: not even valid JSON any more (a bad hand-edit, a
stray merge-conflict marker, a truncated write) comes back marked
{"_malformed": True, "_error": ...} instead of crashing the caller with
an uncaught json.JSONDecodeError; a line that parses cleanly but not to a
JSON object gets the same sentinel. `tools/jsonl_append.py` (task 510)
already consolidated the WRITE half of these same fourteen logs
(append_jsonl()) -- the READ half was never given the same treatment,
so every one of those ten sibling docstrings has spent months narrating
"mirrors tools/ledger.py's own _entries()" without a single line of
code ever actually being shared, the identical disease task 510 named
for _append before it was fixed.

Found live by the same AST-hash duplicate-function sweep tasks 508-528
have used all week, this time pointed at `tools/*.py` with string/number
constants normalized before hashing (the malformed-non-object branch
carries three cosmetically different message phrasings across the
fourteen copies -- "not a JSON object: {v!r}" vs "parsed to {type},
not an object" vs "line parsed to {type}, not a JSON object" -- which is
exactly why a bare byte-identical hash only ever caught 2-3 of the
fourteen at a time). Grepped `tests/*.py` for any read of the `_error`
field before consolidating on one canonical message: zero hits -- every
real caller only ever checks the boolean `_malformed` sentinel, so the
exact wording was never a contract.

Every real call site across all fourteen files already passes `path`
explicitly or relies on its own module-level default (`LOG`/`QUEUE`/
`LEDGER`), so this shared function takes no default of its own -- same
discipline `append_jsonl()` uses, avoiding the same silent-divergence
trap on that axis. `ledger.py`'s own `_entries()` takes no `path`
argument at all (hardcoded to its own `LEDGER` global); its wrapper
below passes `LEDGER` through explicitly rather than exposing a new
parameter no real caller has ever needed.

Every sibling's `_entries` now delegates to `read_jsonl_entries` below
instead of carrying its own copy; `tests/test_jsonl_read.py` proves each
wrapper genuinely calls through to it (patch-and-observe, the same
"wrapper-with-its-own-default" identity guarantee task 523's
`LoadSnapshotsDelegatesCase` used for `time_utils.load_snapshots`, not a
bare `assertIs` -- each wrapper is a distinct function object by
necessity).

Usage: not run directly; imported by tools/*.py.
"""
from __future__ import annotations

import json
import os


def read_jsonl_entries(path: str) -> list[dict]:
    """Read every line in a JSONL log at `path`, tolerant of a corrupted
    tail. A line that isn't valid JSON, or that parses to something other
    than a JSON object (a bare number, null, list, or string), comes back
    marked {"_malformed": True, "_error": ...} instead of raising -- every
    real caller already checks entries[-1].get("_malformed") for its own
    tampered-tablet handling. A missing file is an empty log, not an
    error (mirrors every one of the fourteen prior copies)."""
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                entries.append({"_malformed": True, "_error": str(exc)})
                continue
            if not isinstance(parsed, dict):
                entries.append({
                    "_malformed": True,
                    "_error": f"parsed to {type(parsed).__name__}, not a JSON object",
                })
                continue
            entries.append(parsed)
    return entries
