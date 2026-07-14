#!/usr/bin/env python3
"""Task 69. Kwaku-Ananse's own change-gate, made a rule instead of an eyeball.

Every hourly BUILDLOG ritual line since the daily report existed has closed
with a hand-read verdict: "no gap surfaced this hour differs from the last
one posted to @oritatown, so staying silent on X per the change-gate" (or,
rarer, the opposite). That verdict is TOWN-OPERATIONS.md's own documented
law (`X posting is CHANGE-GATED`) -- @oritatown posts a Report tweet ONLY
when this hour's surfaced gap DIFFERS from the last gap already posted --
but nothing has ever checked it in code. A human reads today's Report,
recalls (or re-scrolls to) the last tweet's wording, and eyeballs whether
the two sentences describe the same seam. That is exactly the class of
by-feel judgment tasks 55-59 and 61-62 already closed elsewhere (the owed
post queue, the outage streak, the recheck cooldown, the ritual note, the
cron eyeball) -- this is the one still left standing in the change-gate
itself.

`X_GetUserTweets` has been forbidden for the whole outage this tool was
built inside of, so it cannot read @oritatown's real last tweet back to
compare against. What it CAN do durably: record, in the town's own hands,
which gap text was posted each time a post actually lands (task 55/56's
`mark_posted()` companion, one layer up -- the *content* posted, not just
that a queue entry cleared), and compare today's report's primary gap
against that record. No prior real post recorded yet: honestly due, same
"never guess" discipline every PENDING cadence source in this repo already
holds -- not backfilled from git history, because the actual tweeted text
was never durably saved anywhere this tool can trust byte-for-byte.

Usage:
    python3 tools/change_gate.py check <report_path>
    python3 tools/change_gate.py record <report_path> <posted_at>
"""
import json
import os
import re

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "posted-gap-log.jsonl")

_GAP_RE = re.compile(r"^\*\*(.+?)\*\*\s*—\s*confidence\s+([\d.]+)\.", re.MULTILINE)


def extract_primary_gap(report_text: str):
    """Pull the bolded primary-gap line out of a Fencepost Report.

    Returns the gap's description text, or None if the report carries no
    parseable primary gap (an empty-state report, a malformed one, or a
    template not yet filled in) -- never a guess at what it might have meant.
    """
    m = _GAP_RE.search(report_text)
    return m.group(1).strip() if m else None


def _entries(path=LOG):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append(entry, path=LOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def last_posted_gap(path=LOG):
    """The gap text of the most recently recorded real post, or None."""
    entries = _entries(path)
    return entries[-1]["gap"] if entries else None


def record_posted_gap(gap_text: str, posted_at: str, path=LOG) -> None:
    """Append one real posted-gap event. Never edits or removes a prior line."""
    if not gap_text:
        raise ValueError("refusing to record an empty gap text")
    _append({"type": "posted", "gap": gap_text, "posted_at": posted_at}, path)


def should_post_gap(report_text: str, path=LOG):
    """Whether this report's primary gap clears TOWN-OPERATIONS.md's change-gate.

    Returns (due: bool, reason: str). No parseable gap in the report: never
    due (nothing to post). Never posted before: due. Same gap text as the
    last real post: not due (the exact case that has been silently correct,
    by hand, every hour of this outage). Different text: due.
    """
    gap = extract_primary_gap(report_text)
    if gap is None:
        return False, "report carries no parseable primary gap"
    last = last_posted_gap(path)
    if last is None:
        return True, "no prior post recorded -- due"
    if gap == last:
        return False, "unchanged from the last posted gap"
    return True, "gap differs from the last posted gap"


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        report_path = sys.argv[2]
        with open(report_path) as f:
            text = f.read()
        due, reason = should_post_gap(text)
        print(f"{'due' if due else 'not due'} -- {reason}")
        sys.exit(0 if due else 1)
    elif cmd == "record":
        report_path, posted_at = sys.argv[2], sys.argv[3]
        with open(report_path) as f:
            text = f.read()
        gap = extract_primary_gap(text)
        if gap is None:
            print("refusing to record -- report carries no parseable primary gap")
            sys.exit(1)
        record_posted_gap(gap, posted_at)
        print(f"recorded: {gap!r}")
