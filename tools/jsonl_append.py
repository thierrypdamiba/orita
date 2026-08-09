#!/usr/bin/env python3
"""Task 510. The append-a-JSON-line helper ten checkers each carried a
private copy of.

`arcade_app_watch.py`, `change_gate.py`, `ci_watch.py`,
`gateway_toolset_check.py`, `github_stars_check.py`,
`scribe_growth_check.py`, `square_check.py`, `word_watch.py`,
`x_outage_tracker.py`, and `x_post_queue.py` each defined their own
byte-identical `_append(entry, path)`: make the parent directory, open the
log in append mode, write one `json.dumps(...)`-encoded line. The same
disease tasks 508 (`metrics_reader.py`, six copies) and 509
(`iso_time.py`, three copies) already named and closed elsewhere in this
directory -- a duplicated ordinary function, invisible to
`tools/duplicate_regex_check.py` (which only ever inspects
`re.compile(...)` call sites, never duplicated function bodies). Found
live by an Explore sweep of `tools/*.py` this hour, the third instance of
this exact shape in three hours -- ten copies this time, the largest yet.
Every real call site in all ten files already passes both `entry` and
`path` explicitly (verified by grep before dropping each file's own
`path=LOG`/`path=QUEUE` default), so the shared function below takes no
default and cannot silently diverge on that axis either.

Consolidated here as the one place this helper is defined. Every sibling
check now imports `append_jsonl` from this module instead of carrying its
own copy; `tests/test_jsonl_append.py` asserts each sibling's `_append`
name is the identical function object (not just identical source), so a
future edit to one is an edit to all ten by construction -- the same
guarantee `metrics_reader.py` and `iso_time.py` give their own siblings.

Usage: not run directly; imported by tools/*.py.
"""
from __future__ import annotations

import json
import os
from typing import Mapping


def append_jsonl(entry: Mapping[str, object], path: str) -> None:
    """Append one JSON-encoded line for `entry` to the log at `path`,
    creating the parent directory if it does not yet exist. Takes a
    `Mapping`, not a `dict`, so a caller's own more specifically-typed
    dict literal (e.g. `dict[str, str]`) is accepted without a variance
    error -- this function only ever reads `entry`, never mutates it."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
