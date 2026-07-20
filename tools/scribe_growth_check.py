#!/usr/bin/env python3
"""Task 168. Nisaba watches her own hand grow.

`ROADMAP.md` and `BUILDLOG.md` are append-only narrative logs that grow
every single task, forever, on purpose (the loop's own step 6: "TRACK THE
THOUGHT EVERY TASK" law) -- and nothing in the town's own operations has
ever read, recorded, or reported either file's real byte size. A system
built to run hourly, forever, with an append-only scribal record needs to
SEE that record's own growth before it becomes a real operational problem
(a GitHub soft file-size warning, a slower checkout, a table too large for
a single context window to hold) -- the identical "recalled, not recorded"
gap `arcade_app_watch.py` (task 122), `x_outage_tracker.py` (task 57),
`square_check.py` (task 70), and `word_watch.py` (task 74) each already
closed for a different unwatched number. Checked live at the hour this
module shipped: `ROADMAP.md` sat at 648,609 bytes and `BUILDLOG.md` at
328,759 bytes, both climbing every task, and neither number had ever once
been durably recorded anywhere before now.

This module makes no judgement about WHEN to archive either file -- it
only makes the real, live byte count of each tracked scribal file visible,
durably recorded (`HAND/scribe-growth-log.jsonl`, append-only, never
edited), and comparable hour over hour, the same "read the state, let a
god act on it" boundary `check_checkout` already draws for detached-HEAD
recovery. A file crossing `WARN_BYTES` is flagged `over_threshold`
(informational only, like `arcade_apps`/`square` in `ritual_check.py` --
crossing it is not itself a rule violation, just a number worth a god's
attention) so the day someone needs to decide whether to archive
`ROADMAP.md`'s history, they are deciding off a real recorded trend, not a
hunch about how big the file "feels" like it has gotten.

Unlike `arcade_app_watch.py`/`square_check.py`, this makes its OWN read --
a tracked file's byte size is local filesystem state, not a live API call
behind this sandbox's proxy wall, so there is no caller-supplied-state door
to thread through `ritual_check.py`; `compute_scribe_sizes` runs
unconditionally, every hour, on its own.

Usage:
    python3 tools/scribe_growth_check.py check
    python3 tools/scribe_growth_check.py record <checked_at>
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LOG = os.path.join(ROOT, "HAND", "scribe-growth-log.jsonl")

# Informational warn line, chosen with wide headroom under GitHub's own
# per-file push guidance (a 50MB warning, a 100MB hard block) -- not a hard
# limit of any kind. Crossing it does not fail ritual_check; it just stops
# the number from being invisible.
WARN_BYTES = 5_000_000

TRACKED_FILES = {
    "ROADMAP.md": "ROADMAP.md",
    "BUILDLOG.md": "BUILDLOG.md",
}


def compute_scribe_sizes(root: str = ROOT, tracked: dict | None = None) -> dict:
    """Real, live byte size of each tracked scribal file via os.path.getsize
    -- never a cached or remembered number. Raises FileNotFoundError if a
    tracked file is missing: a scribal file the town depends on existing
    should fail loudly, not be silently recorded as zero."""
    tracked = TRACKED_FILES if tracked is None else tracked
    sizes = {}
    for name, rel_path in tracked.items():
        full = os.path.join(root, rel_path)
        sizes[name] = os.path.getsize(full)
    return sizes


def _entries(path=LOG):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append(entry, path=LOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def last_scribe_state(path=LOG):
    """The most recently recorded real scribe-size snapshot, or None."""
    entries = _entries(path)
    return entries[-1] if entries else None


def record_scribe_check(sizes: dict, checked_at: str, path=LOG) -> None:
    """Append one real observed scribe-size snapshot. Never edits or removes a prior line."""
    _append({"sizes": sizes, "checked_at": checked_at}, path)


def check_scribe_growth(sizes: dict, threshold_bytes: int = WARN_BYTES, path=LOG) -> dict:
    """Pure judgement over an already-computed sizes dict: which tracked
    files (if any) have crossed threshold_bytes, and -- if a prior
    recorded check exists -- how many bytes each grew since then. Never
    reads a file or a clock itself; the caller holds this hour's real
    `compute_scribe_sizes()` result."""
    over_threshold = sorted(name for name, size in sizes.items() if size >= threshold_bytes)
    last = last_scribe_state(path)
    growth_since_last_check = None
    if last is not None:
        prev_sizes = last["sizes"]
        growth_since_last_check = {
            name: size - prev_sizes[name] for name, size in sizes.items() if name in prev_sizes
        }
    return {
        "sizes": sizes,
        "over_threshold": over_threshold,
        "clean": not over_threshold,
        "growth_since_last_check": growth_since_last_check,
    }


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    sizes = compute_scribe_sizes()
    if cmd == "check":
        result = check_scribe_growth(sizes)
        status = "clean" if result["clean"] else f"OVER THRESHOLD: {result['over_threshold']}"
        print(f"{status} -- sizes: {result['sizes']}, growth: {result['growth_since_last_check']}")
        return 0
    elif cmd == "record":
        if len(argv) < 3:
            print("usage: record <checked_at>")
            return 1
        record_scribe_check(sizes, argv[2])
        print(f"recorded: {sizes}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
