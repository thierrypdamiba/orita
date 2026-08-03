"""The fortieth real seam recipe: a pull request reached a terminal state
(merged or closed), but its own head branch was never deleted.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads two local fixture files
(`pull_requests.json`, `activities.json`), shaped like what
`ListPullRequests`/`ListRepositoryActivities` would actually return. Both
scopes already sit on SCOPES.md's cleared oath table -- this recipe asks
Arcade for nothing new.

The third leg of a branch-lifecycle trio this engine now covers end to end:
`stale-branch-no-pr` watches a branch survive with no PR ever pointing at
it; `deleted-branch-pr-still-open` watches a branch's promise (an open PR)
survive after the branch itself is gone; this one watches the branch
survive AFTER its own promise (the PR) has already resolved. GitHub's merge
UI offers a "Delete branch" button, but nothing forces it -- a PR merges (or
closes without merging) and its head ref just sits in the branch list
forever unless a human happens to click that button or remembers to clean
up by hand. Neither the pull-request list alone (a resolved PR's head_ref
reads the same whether the branch behind it is alive or already gone) nor
the Activity feed alone (a `branch_deletion` event names a ref, not a PR
number, and its *absence* proves nothing on its own) shows this -- only
holding both at the same instant does, the same "the gap lives only in the
seam" shape every recipe in this engine already watches for some other
pair of records.

A pull request still open is excluded, named not hidden -- it has not
resolved yet, so there is no cleanup promise to have missed. A resolved
pull request whose head branch already carries a matching `branch_deletion`
event is excluded too -- the ordinary, unremarkable case (most branches get
deleted exactly because their PR just merged, the ones this recipe is NOT
about).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULL_REQUESTS_FIXTURE = _HERE.parents[1] / "fixtures" / "merged_pr_branch_not_deleted" / "pull_requests.json"
DEFAULT_ACTIVITIES_FIXTURE = _HERE.parents[1] / "fixtures" / "merged_pr_branch_not_deleted" / "activities.json"

# A PR resolved under this age may just be mid-cleanup -- a merge-queue tool
# or a human about to click "Delete branch" -- not yet a gap. Mirrors
# deleted-branch-pr-still-open's own 24h grace window on the same lifecycle.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _parse_ts_or_none(s: str | None) -> datetime | None:
    return _parse_ts(s) if s else None


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    head_ref: str
    url: str
    resolved_at: datetime | None


@dataclass
class Activity:
    type: str
    ref: str
    actor: str
    created_at: datetime
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
            number=r["number"], title=r["title"], state=r["state"], head_ref=r["head_ref"],
            url=r["url"], resolved_at=_parse_ts_or_none(r.get("resolved_at")),
        )
        for r in rows
    ]


def load_activities(path: Path | None = None) -> list[Activity]:
    rows = _load_rows(path or DEFAULT_ACTIVITIES_FIXTURE)
    return [
        Activity(
            type=r["type"], ref=r["ref"], actor=r["actor"],
            created_at=_parse_ts(r["created_at"]), url=r["url"],
        )
        for r in rows
    ]


def _branch_deletion_for_ref(ref: str, activities: list[Activity]) -> Activity | None:
    for activity in activities:
        if activity.type == "branch_deletion" and activity.ref == ref:
            return activity
    return None


def compute_gaps(
    pull_requests: list[PullRequest], activities: list[Activity], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Only resolved (`merged` or `closed`) pull requests are
    considered at all -- a PR still `open` names no cleanup promise yet and
    is excluded, not surfaced, the same "not this seam yet" precedent
    `deleted-branch-pr-still-open/detector.py` sets for a PR already
    resolved some other way. A resolved PR whose head branch already
    carries a matching `branch_deletion` event is excluded too -- everything
    left over -- a resolved PR whose own head branch is confirmed still
    alive -- is surfaced, aged into a confidence score `rank()` can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pr in pull_requests:
        if pr.state == "open":
            excluded.append(GapCandidate(
                slug=f"pr-not-yet-resolved-{pr.number}",
                headline=f"PR #{pr.number}'s branch '{pr.head_ref}' is still open, not yet resolved",
                detail=f"'{pr.title}' reads open -- no cleanup promise exists until it merges or closes. No seam here.",
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        deletion = _branch_deletion_for_ref(pr.head_ref, activities)
        if deletion is not None:
            excluded.append(GapCandidate(
                slug=f"branch-already-deleted-{pr.number}",
                headline=f"PR #{pr.number}'s branch '{pr.head_ref}' was already deleted",
                detail=f"'{pr.title}' resolved {pr.state}; its branch was deleted {deletion.created_at.isoformat()}. No seam here.",
                confidence=0.0,
                evidence=[pr.url, deletion.url],
            ))
            continue

        resolved_at = pr.resolved_at
        age_hours = (now - resolved_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"merged-pr-branch-not-deleted-{pr.number}",
            headline=f"PR #{pr.number} {pr.state}, but its branch '{pr.head_ref}' was never deleted",
            detail=(
                f"'{pr.title}' resolved ({pr.state}) {resolved_at.isoformat()} "
                f"({age_hours:.1f}h ago); no matching branch_deletion event for {pr.head_ref!r} "
                "in the Activity feed -- the branch still sits in the branch list."
            ),
            confidence=confidence,
            evidence=[pr.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pull_requests_path: Path | None = None,
    activities_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListRepositoryActivities` read and this one loader is swapped for a
    real read. The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pull_requests = load_pull_requests(pull_requests_path)
    activities = load_activities(activities_path)
    surfaced, excluded = compute_gaps(pull_requests, activities, now=now)
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
