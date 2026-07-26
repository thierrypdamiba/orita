#!/usr/bin/env python3
"""Task 74. Nyx's own closing of the last hand-recalled ritual number.

Tasks 69-73 closed six real hand-recalled ritual numbers one at a time:
the change-gate verdict (`change_gate.py`), the square's own read
(`square_check.py`), the ritual note's own fold (`ritual_check.py`), the
third X door (`x_outage_tracker.py`'s `X_WhoAmI`), and CI's own conclusion
(`ci_watch.py`). One number has never been anything but a human glancing
at `DECREES/`, `HAND/queue.md`, `HAND/verdicts/`, and `HAND/proclamations/`
-- the four places `TOWN-OPERATIONS.md` says Thierry's words land -- and
writing "DECREES/001 unchanged since 2026-07-12, no new words from
Thierry" from memory of what was there last hour. That is the exact
re-derived-from-recall shape every one of those five tools already closed
elsewhere, just never turned on the one check that exists to catch
Thierry's own words the moment they land.

Unlike `square_check.py`/`ci_watch.py` (which fold in a caller-supplied
live API read, because GitHub state has no local fixture), this tool
reads the real filesystem directly -- the four tracked places are local
files in this checkout, no network call needed at all, the same boundary
`sync_checkout.sh` already draws around git state.

Usage:
    python3 tools/word_watch.py check
    python3 tools/word_watch.py record <checked_at>
"""
from __future__ import annotations

import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "HAND", "word-check-log.jsonl")

TRACKED_PATHS = (
    "DECREES",
    "HAND/queue.md",
    "HAND/verdicts",
    "HAND/proclamations",
)


def _file_digest(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def compute_word_state(root: str = ROOT) -> dict:
    """Walk the four places Thierry's words land and fold them into a
    sorted {relpath: sha256} shape. Pure local filesystem read -- no
    network call, mirroring sync_checkout.sh's local-only boundary.
    A tracked path that doesn't exist yet contributes nothing (not an
    error) so a fresh fork with no DECREES/ yet still gets a valid,
    empty-honest state."""
    files = {}
    for tracked in TRACKED_PATHS:
        full = os.path.join(root, tracked)
        if os.path.isfile(full):
            files[tracked] = _file_digest(full)
        elif os.path.isdir(full):
            for dirpath, _dirnames, filenames in os.walk(full):
                for name in filenames:
                    fpath = os.path.join(dirpath, name)
                    rel = os.path.relpath(fpath, root)
                    files[rel] = _file_digest(fpath)
    return {"files": dict(sorted(files.items()))}


class WordWatchTamperedError(RuntimeError):
    """Raised by last_word_state() when the log's most recent line is not
    valid JSON. Mirrors tools/change_gate.py's PostedGapLogTamperedError:
    skipping past a corrupted tip and falling back to an older valid entry
    would let word_delta() silently guess -- and guessing wrong either
    masks real new words from Thierry (guesses "unchanged" when the last
    real check no longer reflects the tracked files) or manufactures a
    false ritual note (guesses "changed" on stale, no-longer-true state).
    Run this tool's `check` command by hand to see the break, then repair
    the log before the next real check/record."""


def _entries(path: str = LOG) -> list:
    """Every line in the word-check log, parsed.

    A line that is not even valid JSON any more (a bad hand-edit, a stray
    merge-conflict marker, a truncated write) is not allowed to crash the
    caller with an uncaught json.JSONDecodeError -- it comes back marked
    {"_malformed": True, "_error": ...} instead, the same convention
    tools/ledger.py's _entries() already uses for its own tampered-tablet
    case (mirrored since in change_gate.py and x_post_queue.py).
    """
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                entries.append({"_malformed": True, "_error": str(exc)})
                continue
            if not isinstance(parsed, dict):
                entries.append(
                    {"_malformed": True, "_error": f"not a JSON object: {parsed!r}"}
                )
                continue
            entries.append(parsed)
    return entries


def _append(entry: dict, path: str = LOG) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def last_word_state(path: str = LOG):
    """The most recently recorded real word check, or None.

    Raises WordWatchTamperedError if the log's last line isn't valid
    JSON -- word_delta() must never guess past a corrupted tip.
    """
    entries = _entries(path)
    if not entries:
        return None
    if entries[-1].get("_malformed"):
        raise WordWatchTamperedError(
            f"last_word_state(): the most recent line in {path} is not "
            f"valid JSON ({entries[-1]['_error']}) -- refusing to guess "
            "whether Thierry's words changed. Repair the log by hand, "
            "then rerun."
        )
    return entries[-1]


def record_word_check(state: dict, checked_at: str, path: str = LOG) -> None:
    """Append one real observed word state. Never edits or removes a prior line."""
    entry = dict(state)
    entry["checked_at"] = checked_at
    _append(entry, path)


def word_delta(state: dict, path: str = LOG):
    """Whether this hour's real filesystem read differs from the last
    recorded check. Returns (changed: bool, reason: str). No prior check
    recorded: due (first check). A tracked file added, removed, or its
    content changed: due, naming the path. Otherwise: not due, and the
    reason names the last real checked_at as the honest "since" -- the
    exact line the hourly ritual note has been hand-recalling."""
    last = last_word_state(path)
    if last is None:
        return True, "no prior word check recorded -- due"
    prev_files = last["files"]
    cur_files = state["files"]
    added = sorted(set(cur_files) - set(prev_files))
    removed = sorted(set(prev_files) - set(cur_files))
    changed_content = sorted(
        p for p in (set(cur_files) & set(prev_files)) if cur_files[p] != prev_files[p]
    )
    if added:
        return True, f"new word(s) landed: {added}"
    if removed:
        return True, f"tracked file(s) removed: {removed}"
    if changed_content:
        return True, f"tracked file(s) changed: {changed_content}"
    return False, f"unchanged since {last['checked_at']}"


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    state = compute_word_state()
    if cmd == "check":
        changed, reason = word_delta(state)
        print(f"{'changed' if changed else 'unchanged'} -- {reason}")
        return 0
    elif cmd == "record":
        if len(argv) < 3:
            print("usage: record <checked_at>")
            return 1
        record_word_check(state, argv[2])
        print(f"recorded: {len(state['files'])} tracked file(s)")
        return 0
    print(f"unknown command: {cmd!r}")
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv))
