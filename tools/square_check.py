#!/usr/bin/env python3
"""Task 70. Èṣù-Elegba's own door, made a rule instead of a memory.

`tools/ritual_check.py` (task 61) drew its own boundary honestly: "Does NOT
touch the square (GitHub issues/PRs) -- that stays a live API read, out of
scope for a local script." Every hourly BUILDLOG line since has still closed
that one live read the same way task 61 left it -- a human reads the live
`list_issues`/`list_pull_requests` result and writes "4 open issues
#1/#2/#3/#5, unchanged since 2026-07-12T06:43:35Z" from memory of what the
number was last hour, not from a durable comparison. That is the exact
re-derived-from-recall shape tasks 57 (the outage streak) and 69 (the
change-gate) already closed elsewhere, just never turned on the one live
read that happens every single hour without fail.

This tool still makes no network call of its own -- the caller (the god on
duty, holding this hour's real `list_issues`/`list_pull_requests` read)
folds that read into a state dict and hands it in, mirroring
`ritual_check.py`'s own local-only boundary exactly. What this tool adds is
durable memory: record what was actually seen, and compare instead of
recall.

Task 124 closed the one gap this left: `record` trusted whatever
`state.json` it was handed, so a malformed or empty payload (missing
`issues`/`prs` keys) got written into the real durable log as if it were a
genuine all-clear square. `record_square_check` now refuses an all-empty
state over a non-empty prior baseline unless `force=True` (CLI: `--force`).

Usage:
    python3 tools/square_check.py check <state.json>
    python3 tools/square_check.py record <state.json> <checked_at> [--force]

<state.json> shape: {"issues": [{"number": 1, "updated_at": "..."}, ...],
                      "prs":    [{"number": 7, "updated_at": "..."}, ...]}
"""
import json
import os

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "square-check-log.jsonl")


def compute_square_state(issues, prs):
    """Fold a live issues/PRs read into the durable comparison shape.

    `issues`/`prs` are lists of dicts, each carrying at least `number` and
    `updated_at` (ISO-8601 string) -- the same fields every GitHub list-issue
    /list-PR read already returns. Never makes a network call itself.
    """
    issue_numbers = sorted(i["number"] for i in issues)
    pr_numbers = sorted(p["number"] for p in prs)
    updated_ats = [i["updated_at"] for i in issues] + [p["updated_at"] for p in prs]
    max_updated_at = max(updated_ats) if updated_ats else None
    return {
        "issue_numbers": issue_numbers,
        "pr_numbers": pr_numbers,
        "max_updated_at": max_updated_at,
    }


def _entries(path=LOG):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append(entry, path=LOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def last_square_state(path=LOG):
    """The most recently recorded real square check, or None."""
    entries = _entries(path)
    return entries[-1] if entries else None


class DegenerateSquareStateError(ValueError):
    """Raised when a caller tries to record an all-empty square state (no
    open issues, no open PRs) over a real, non-empty prior baseline. Almost
    always a malformed or missing `state.json` payload (e.g. `{"issues":
    []}` from a caller error), not a real GitHub read -- a live square
    genuinely collapsing from N>0 open issues to zero with no corresponding
    real close events in between is the rare case, not the common one."""


def record_square_check(state: dict, checked_at: str, path=LOG, *, force: bool = False) -> None:
    """Append one real observed square state. Never edits or removes a prior line.

    Refuses to record an all-empty state when the last recorded real check
    was non-empty, unless `force=True` -- see `DegenerateSquareStateError`.
    """
    is_empty = not state["issue_numbers"] and not state["pr_numbers"]
    if is_empty and not force:
        last = last_square_state(path)
        if last is not None and (last["issue_numbers"] or last["pr_numbers"]):
            raise DegenerateSquareStateError(
                "refusing to record an empty square state over a non-empty "
                f"prior baseline (issues {last['issue_numbers']}, prs {last['pr_numbers']}) "
                "-- pass force=True if every issue/PR was genuinely closed this hour"
            )
    entry = dict(state)
    entry["checked_at"] = checked_at
    _append(entry, path)


def square_delta(state: dict, path=LOG):
    """Whether this hour's live square read differs from the last recorded check.

    Returns (changed: bool, reason: str). No prior check recorded: due (first
    check). Open-issue set changed: due, names the sets. Open-PR set changed:
    due, names the sets. `max_updated_at` moved forward (a comment or edit
    landed on an existing thread, even with the same issue/PR numbers): due.
    Otherwise: not due, and the reason names the real `max_updated_at` as the
    honest "since" -- the exact line the hourly ritual note has been
    hand-recalling.
    """
    last = last_square_state(path)
    if last is None:
        return True, "no prior square check recorded -- due"
    if state["issue_numbers"] != last["issue_numbers"]:
        return True, (
            f"open issue set changed ({last['issue_numbers']} -> {state['issue_numbers']})"
        )
    if state["pr_numbers"] != last["pr_numbers"]:
        return True, (
            f"open PR set changed ({last['pr_numbers']} -> {state['pr_numbers']})"
        )
    if state["max_updated_at"] != last["max_updated_at"]:
        return True, (
            "activity on an existing issue/PR (updated_at moved "
            f"{last['max_updated_at']} -> {state['max_updated_at']})"
        )
    return False, f"unchanged since {state['max_updated_at']}"


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, state_path = argv[1], argv[2]
    with open(state_path) as f:
        raw = json.load(f)
    state = compute_square_state(raw.get("issues", []), raw.get("prs", []))
    if cmd == "check":
        changed, reason = square_delta(state, path=LOG)
        print(f"{'changed' if changed else 'unchanged'} -- {reason}")
        return 0
    elif cmd == "record":
        if len(argv) < 4:
            print("usage: record <state.json> <checked_at> [--force]")
            return 1
        force = "--force" in argv[4:]
        try:
            record_square_check(state, argv[3], path=LOG, force=force)
        except DegenerateSquareStateError as e:
            print(f"refused: {e}")
            return 1
        print(f"recorded: {state}")
        return 0
    print(f"unknown command: {cmd!r}")
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv))
