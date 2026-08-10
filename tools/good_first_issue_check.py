#!/usr/bin/env python3
"""Task 477. Ogun's other named job, checked for the first time.

CHARTER.md Appendix B ("The Iron Ledger and the Sworn-on-Iron Badge --
Ogun") names his job plainly: "when the crowd lands, everything works --
site under two seconds, links unbroken, good-first-issues stocked, badge
green." Three of those four clauses already had a running hourly check
(`check_site_links`/`check_house_links`, `check_badge_freshness`) --
"stocked" never did. It was a claim resting on nobody having checked it,
the same "named in the Charter, never turned into a check" shape
`site_link_check.py` (task 423) already closed for "links unbroken."

Live read confirms the gap was real, not theoretical: GitHub's own
default `good first issue` label (7057ff, "Good for newcomers") has
existed on this repo the whole time and has never once been attached to
a single issue -- open or closed -- since founding. The shelf existed;
nothing was ever put on it.

This tool makes no network call of its own -- the caller (the god on
duty, holding this hour's live `list_issues` read) folds the open
issues' labels into a list and hands it in, mirroring
`square_check.py`/`gateway_toolset_check.py`'s own local-only boundary.
Unlike those two, there is no "change since last hour" worth tracking
here -- only "is the shelf stocked right now" -- so this holds no durable
log, the same simpler shape `badge_freshness_check.py` already holds for
a check with no history to keep.

Usage:
    python3 tools/good_first_issue_check.py check <open-issues.json>

<open-issues.json> shape: [{"number": 1, "labels": ["house:off-by-one"]}, ...]
"""
from __future__ import annotations

import json
import sys
from typing import cast

GOOD_FIRST_ISSUE_LABEL = "good first issue"


def compute_good_first_issue_state(open_issues: list[dict[str, object]]) -> dict[str, object]:
    """Pure function: which open issues carry the `good first issue` label.

    `open_issues` is a list of dicts, each carrying at least `number` and
    `labels` (a list of label-name strings) -- the same shape a live
    `list_issues` read already returns. Label matching is case-insensitive
    and whitespace-tolerant (GitHub label names are case-preserving, not
    case-sensitive, for matching purposes) but never substring -- a label
    named "not a good first issue" must not falsely count, the same
    exact-match-only discipline `rider_check.py`'s siblings hold for their
    own cue words.
    """
    stocked = sorted(
        cast(int, issue["number"])
        for issue in open_issues
        if any(
            cast(str, label).strip().lower() == GOOD_FIRST_ISSUE_LABEL
            for label in cast(list[object], issue.get("labels", []))
        )
    )
    return {"count": len(stocked), "issue_numbers": stocked}


def check_good_first_issues(open_issues: list[dict[str, object]] | None) -> dict[str, object] | None:
    """Returns None if the caller didn't hold a live `list_issues` read this
    hour -- informational-only, never blocks the rest of the ritual on a
    missing live read, the same optional-input shape `check_square`/
    `check_arcade_apps`/`check_gateway_toolset` already hold. Also
    informational when a read WAS held: an empty shelf is a real, named
    gap (CHARTER.md Appendix B), not a doctrine violation the way a vault
    leak or a scope drift is -- the same class `report_cadence`/
    `cluster_day`/`thegap` already hold for their own real-but-not-fatal
    cadence gaps."""
    if open_issues is None:
        return None
    state = compute_good_first_issue_state(open_issues)
    return {"clean": cast(int, state["count"]) >= 1, **state}


def format_good_first_issues(result: dict[str, object] | None) -> str:
    if result is None:
        return "good first issues: not read this hour (no live list_issues held)"
    if result["clean"]:
        return f"good first issues: stocked ({result['count']} open, {result['issue_numbers']})"
    return (
        "good first issues: EMPTY -- CHARTER.md Appendix B names this Ogun's "
        'job ("good-first-issues stocked"), zero currently open'
    )


class GoodFirstIssueArgError(ValueError):
    """<open-issues.json> parsed as valid JSON but not into a list -- the
    same valid-JSON-wrong-shape guard `square_check.py`'s own
    `SquareCheckArgError` holds for its dict-shaped argument."""


def _load_state_json(path: str) -> list[dict[str, object]]:
    with open(path) as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise GoodFirstIssueArgError(f"{path}: expected a JSON list, got {type(raw).__name__}")
    return raw


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "check":
        print(__doc__)
        return 1
    open_issues = _load_state_json(argv[2])
    result = check_good_first_issues(open_issues)
    print(format_good_first_issues(result))
    return 0 if result is None or result["clean"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
