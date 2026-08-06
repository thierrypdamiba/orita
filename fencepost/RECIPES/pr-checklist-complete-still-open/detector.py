"""The fifty-second real seam recipe (ROADMAP.md #579): a pull request's own
body carries a GitHub task-list checklist, every box on it is checked, and
the pull request itself still sits open.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads one local fixture file (`pull_requests.json`),
shaped like what `ListPullRequests` (with bodies) would actually return. The
one scope already sits on `SCOPES.md`'s cleared oath table -- no new scope is
asked for anywhere in this recipe.

The seam: `issue-checklist-complete-still-open` (task 558) already proved the
shape -- a checklist promise nothing ever compares against the thing that
made it -- but for an ISSUE whose checklist names OTHER issues by number
(`- [ ] #N`). A pull request's own checklist is a different, more common
grammar in real use: a self-contained list of plain-text tasks an author
writes for themself or a reviewer ("- [ ] Add tests", "- [ ] Update docs"),
naming no other GitHub object at all. GitHub renders every box, tallies a
"3 of 5 tasks done" progress count on the PR's own page, and does precisely
nothing with the moment the count reaches N of N -- merging is always a
separate, human, forgettable step, the identical "no trigger ever existed to
fire" shape `overdue-milestone-still-open` and `stale-branch-no-pr` already
proved for their own single-object seams. This recipe watches that specific
silence: a checklist an author declared complete, on a PR that is not.

Deliberately its OWN checkbox grammar, not `seam_engine.checklist`'s shared
`CHECKLIST_RE` -- that module's own docstring is explicit about the shape it
covers ("- [ ] #N", a checkbox that NAMES another GitHub object by number)
and just as explicit that a bare checkbox with no `#N` after it is a
different recipe's seam, not its grammar's. This recipe's checklist items
are plain text with no number to resolve at all -- reusing `checklist.py`
here would silently match zero items on every real PR checklist in the wild
(none of them read "- [ ] #N"), not extend coverage. The two grammars stay
separate on purpose, each named where it is used, so a future recipe reaches
for the one its own seam actually needs instead of assuming they're
interchangeable.

A PR whose body carries no real task-list checkbox at all makes no
completeness promise -- skipped entirely, not even excluded, the same
precedent `issue-checklist-complete-still-open` already set. A PR with at
least one unchecked box is excluded, named not hidden: not complete yet,
nothing missed. A PR that is already merged or closed is excluded outright
-- whatever its checklist says, the door already resolved one way or the
other, so there is no seam left to watch.

Confidence is age-gated on how long the PR's own `updated_at` has sat still
while every box reads checked -- 24 hours, mirroring
`issue-checklist-complete-still-open`'s own bar exactly, since a pull
request carries no real "went-complete-at" timestamp either; `updated_at`
is the closest real signal the object exposes. See `recipe.json`'s
`confidence_notes` for the full reasoning.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULL_REQUESTS_FIXTURE = (
    _HERE.parents[1] / "fixtures" / "pr_checklist_complete_still_open" / "pull_requests.json"
)

# GitHub's own generic task-list checkbox syntax: "- [ ] text" / "- [x] text",
# one per line, optionally indented, no "#N" required -- deliberately
# distinct from seam_engine.checklist.CHECKLIST_RE (see module docstring for
# why the two grammars are not interchangeable). The trailing `[ \t]*\S` is
# deliberately NOT `\s*\S` -- `\s` matches a newline too, which would let an
# empty checkbox on one line "borrow" the next line's leading `-` as its own
# text and wrongly count as a real task item.
_TASK_ITEM_RE = re.compile(r"^[ \t]*-[ \t]*\[([ xX])\][ \t]*\S", re.MULTILINE)

# A PR whose checklist finished less than this many hours ago may simply not
# have been merged yet by an author still wrapping up -- not yet a settled
# gap. Matches issue-checklist-complete-still-open's own bar exactly, the
# closest real sibling shape (a self-declared completeness claim, checked
# only against the parent's own `updated_at`, no better timestamp exists).
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class PullRequest:
    number: int
    title: str
    body: str
    state: str
    merged: bool
    updated_at: datetime
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_pull_requests(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULL_REQUESTS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], body=r.get("body") or "",
            state=r["state"], merged=r.get("merged", False),
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def _checklist_marks(body: str) -> list[str]:
    """Every checkbox mark (`' '`, `'x'`, or `'X'`) a real GitHub task-list
    item in `body` carries, in the order it appears. An empty list means the
    body made no checklist promise at all -- the caller's own signal to skip
    rather than exclude."""
    return [m.lower() for m in _TASK_ITEM_RE.findall(body)]


def compute_gaps(
    pull_requests: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. A PR that is merged or closed is excluded outright: the
    door already resolved, whatever its checklist says. A PR with no real
    task-list checkbox anywhere in its body is skipped entirely -- it never
    made a completeness promise, so there is nothing to have missed. A PR
    with at least one unchecked box is excluded, named not hidden: not
    complete yet. Everything left over -- an open PR whose own checklist is
    every box checked -- is surfaced, aged into a confidence score `rank()`
    can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pr in pull_requests:
        marks = _checklist_marks(pr.body)
        if not marks:
            continue

        if pr.state != "open" or pr.merged:
            excluded.append(GapCandidate(
                slug=f"pr-resolved-{pr.number}",
                headline=f"PR #{pr.number} is already {'merged' if pr.merged else pr.state}",
                detail=f"'{pr.title}' (#{pr.number}) is {'merged' if pr.merged else pr.state}. No seam here.",
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        if any(mark != "x" for mark in marks):
            excluded.append(GapCandidate(
                slug=f"pr-checklist-incomplete-{pr.number}",
                headline=f"PR #{pr.number}'s own checklist is not complete yet",
                detail=(
                    f"'{pr.title}' (#{pr.number}) carries {len(marks)} checklist item(s); "
                    f"{sum(1 for m in marks if m != 'x')} still unchecked. Not complete yet, "
                    "nothing missed."
                ),
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        age_hours = (now - pr.updated_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"pr-checklist-complete-still-open-{pr.number}",
            headline=f"PR #{pr.number}'s own checklist is all checked off, but the PR itself never merged",
            detail=(
                f"'{pr.title}' (#{pr.number}) carries {len(marks)} checklist item(s), all "
                f"checked; last updated {pr.updated_at.isoformat()} ({age_hours:.1f}h ago). "
                "Still open."
            ),
            confidence=confidence,
            evidence=[pr.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pull_requests_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListPullRequests` read (with bodies) and this one loader is swapped for
    a real read. The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pull_requests = load_pull_requests(pull_requests_path)
    surfaced, excluded = compute_gaps(pull_requests, now=now)
    ranking = rank(surfaced)
    primary = ranking.primary

    return {
        "generated_at": now.isoformat(),
        "source": "fixture",
        "confidence_bar": ranking.confidence_bar,
        "separation_margin": ranking.separation_margin,
        "primary_gap": asdict(primary) if primary else None,
        "tail": [asdict(g) for g in ranking.tail],
        "excluded": [asdict(g) for g in excluded],
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(run_recipe_scan(), indent=2, default=str))
    sys.exit(0)
