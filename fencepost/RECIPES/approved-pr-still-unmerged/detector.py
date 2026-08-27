"""The ninety-fourth real seam recipe (ROADMAP.md #1046): a pull request
already carries an APPROVED review, and the pull request itself still sits
open, unmerged.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads one local fixture file (`pull_requests.json`),
shaped like what `ListPullRequests` (with each PR's own review decision)
would actually return. The one scope already sits on `SCOPES.md`'s cleared
oath table -- no new scope is asked for anywhere in this recipe.

The seam: `pr-checklist-complete-still-open` (task 579) already proved the
shape -- a completeness promise nothing ever compares against the thing that
made it -- for a PR's own self-declared checklist. This recipe watches the
same silence from the OTHER side of the room: not what the author claimed,
but what a REVIEWER already granted. GitHub renders a green "Approved" badge
on a PR's own page the moment a reviewer approves, and does precisely
nothing with that moment -- merging is always a separate, human, forgettable
step, the identical "no trigger ever existed to fire" shape
`overdue-milestone-still-open` and `stale-branch-no-pr` already proved for
their own single-object seams. An approved PR left open is a common, mundane
failure in real teams: the approval arrives, the author gets pulled onto
something else, and the merge button just... waits.

A PR whose review_decision is not APPROVED (CHANGES_REQUESTED,
REVIEW_REQUIRED, or null/no review yet) made no approval promise at all --
excluded, named not hidden, the same precedent every prior recipe's
"nothing to have missed" branch sets. A PR that is already merged or closed
is excluded outright -- whatever its review decision says, the door already
resolved one way or the other, so there is no seam left to watch.

Confidence is age-gated on how long the PR's own `updated_at` has sat still
while `review_decision` reads APPROVED -- 24 hours, mirroring
`pr-checklist-complete-still-open`'s own bar exactly, since a pull request
carries no real "went-approved-at" timestamp either; `updated_at` is the
closest real signal the object exposes. See `recipe.json`'s
`confidence_notes` for the full reasoning.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULL_REQUESTS_FIXTURE = (
    _HERE.parents[1] / "fixtures" / "approved_pr_still_unmerged" / "pull_requests.json"
)

# A PR whose approval landed less than this many hours ago may simply not
# have been merged yet by an author still wrapping up -- not yet a settled
# gap. Matches pr-checklist-complete-still-open's own bar exactly, the
# closest real sibling shape (a self-contained state promise, checked only
# against the parent's own `updated_at`, no better timestamp exists).
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    review_decision: str | None
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
            number=r["number"], title=r["title"], state=r["state"],
            merged=r.get("merged", False), review_decision=r.get("review_decision"),
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def compute_gaps(
    pull_requests: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. A PR that is merged or closed is excluded outright: the
    door already resolved, whatever its review decision says. A PR whose
    review_decision is not APPROVED is excluded too -- no approval promise
    was ever made, so there is nothing to have missed. Everything left over
    -- an open PR already approved -- is surfaced, aged into a confidence
    score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pr in pull_requests:
        if pr.state != "open" or pr.merged:
            excluded.append(GapCandidate(
                slug=f"approved-pr-resolved-{pr.number}",
                headline=f"PR #{pr.number} is already {'merged' if pr.merged else pr.state}",
                detail=f"'{pr.title}' (#{pr.number}) is {'merged' if pr.merged else pr.state}. No seam here.",
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        if pr.review_decision != "APPROVED":
            excluded.append(GapCandidate(
                slug=f"approved-pr-not-approved-{pr.number}",
                headline=f"PR #{pr.number} carries no approving review",
                detail=(
                    f"'{pr.title}' (#{pr.number}) has review_decision="
                    f"{pr.review_decision!r}. No approval promise made, nothing missed."
                ),
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        age_hours = (now - pr.updated_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"approved-pr-still-unmerged-{pr.number}",
            headline=f"PR #{pr.number} has an approving review, but the PR itself never merged",
            detail=(
                f"'{pr.title}' (#{pr.number}) was approved; last updated "
                f"{pr.updated_at.isoformat()} ({age_hours:.1f}h ago). Still open."
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
    `ListPullRequests` read (with each PR's own review decision) and this
    one loader is swapped for a real read. The detection logic does not
    change when that happens."""
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
