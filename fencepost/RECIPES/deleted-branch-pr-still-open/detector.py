"""The thirtieth real seam recipe (ROADMAP.md #485): a pull request's own
head branch was deleted upstream, but the PR itself was never closed.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads two local fixture files (`activities.json`,
`pull_requests.json`), shaped like what `ListRepositoryActivities`/
`ListPullRequests` would return. Both scopes already sit on SCOPES.md's
cleared oath table -- this recipe asks Arcade for nothing new.

The seam: a branch gets deleted -- a stale feature branch cleaned up, a
force-push-and-delete, a merge-queue tool that deletes on its own -- but
GitHub does not treat "the source branch is gone" as a reason to close the
pull request built on it. The PR just sits there, open, permanently
unmergeable (there is no branch left to merge), until a human happens to
notice and closes it by hand. Neither the Activity feed alone (it names a
ref, not a PR number) nor the PR list alone (an open PR's head ref reads the
same whether the branch is alive or already gone) shows this -- only holding
both at the same instant does, the same "the gap lives only in the seam"
shape every recipe in this engine already watches for some other pair of
records.

A branch-deletion event with no PR at all pointing at that ref (a stale
feature branch nobody ever opened a PR from, or already cleaned up) is
excluded, named not hidden -- there is no promise a deleted branch made to
anyone in that case. A PR whose branch was deleted only after the PR had
already merged or otherwise closed is excluded too -- the ordinary,
unremarkable case (most branches get deleted BECAUSE their PR just merged).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_ACTIVITIES_FIXTURE = _HERE.parents[1] / "fixtures" / "deleted_branch_pr_still_open" / "activities.json"
DEFAULT_PULL_REQUESTS_FIXTURE = _HERE.parents[1] / "fixtures" / "deleted_branch_pr_still_open" / "pull_requests.json"

# A branch deleted under this age may just be an in-progress rebase or a
# cleanup script that hasn't finished its own run yet -- not yet a gap.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _slug_ref(ref: str) -> str:
    """Branch names carry `/` (`feature/x`, `chore/y`); a GapCandidate slug
    does not -- sanitized the same way a filesystem path segment would be."""
    return ref.replace("/", "-")


@dataclass
class Activity:
    type: str
    ref: str
    actor: str
    created_at: datetime
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    head_ref: str
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_activities(path: Path | None = None) -> list[Activity]:
    rows = _load_rows(path or DEFAULT_ACTIVITIES_FIXTURE)
    return [
        Activity(
            type=r["type"], ref=r["ref"], actor=r["actor"],
            created_at=_parse_ts(r["created_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_pull_requests(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULL_REQUESTS_FIXTURE)
    return [
        PullRequest(number=r["number"], title=r["title"], state=r["state"], head_ref=r["head_ref"], url=r["url"])
        for r in rows
    ]


def _find_pr_by_head_ref(ref: str, pull_requests: list[PullRequest]) -> PullRequest | None:
    for pr in pull_requests:
        if pr.head_ref == ref:
            return pr
    return None


def compute_gaps(
    activities: list[Activity], pull_requests: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Only `branch_deletion` activity rows are considered at
    all -- a `push` or any other activity type names no deleted branch and
    is silently skipped, the same "not this seam" precedent
    `duplicate-issue-still-open/detector.py` already sets by skipping a
    non-open issue with no excluded record either. A deletion event is
    excluded, named not hidden, the moment its ref matches no open PR at
    all (no PR ever pointed at it, or the matching PR already merged/closed
    some other way); everything left over -- an open PR whose own head
    branch is confirmed gone -- is surfaced, aged into a confidence score
    `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for activity in activities:
        if activity.type != "branch_deletion":
            continue

        pr = _find_pr_by_head_ref(activity.ref, pull_requests)
        if pr is None:
            excluded.append(GapCandidate(
                slug=f"no-pr-for-deleted-branch-{_slug_ref(activity.ref)}",
                headline=f"Branch '{activity.ref}' was deleted, but no pull request ever pointed at it",
                detail=f"Deleted {activity.created_at.isoformat()}; no PR in this repo's own list carries head_ref {activity.ref!r}. No seam here.",
                confidence=0.0,
                evidence=[activity.url],
            ))
            continue

        if pr.state != "open":
            excluded.append(GapCandidate(
                slug=f"pr-already-{pr.state}-{pr.number}",
                headline=f"PR #{pr.number}'s branch '{activity.ref}' was deleted, but the PR was already {pr.state}",
                detail=f"'{pr.title}' reads {pr.state}; its branch deletion carries no gap once the PR itself has already resolved. No seam here.",
                confidence=0.0,
                evidence=[activity.url, pr.url],
            ))
            continue

        age_hours = (now - activity.created_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"deleted-branch-pr-still-open-{pr.number}",
            headline=f"PR #{pr.number}'s branch '{activity.ref}' was deleted, but the PR is still open",
            detail=(
                f"Activity feed shows {activity.ref!r} deleted {activity.created_at.isoformat()} "
                f"({age_hours:.1f}h ago); PR #{pr.number} ('{pr.title}') still reads open, pointing "
                "at a branch that no longer exists."
            ),
            confidence=confidence,
            evidence=[activity.url, pr.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    activities_path: Path | None = None,
    pull_requests_path: Path | None = None,
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
    activities = load_activities(activities_path)
    pull_requests = load_pull_requests(pull_requests_path)
    surfaced, excluded = compute_gaps(activities, pull_requests, now=now)
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
