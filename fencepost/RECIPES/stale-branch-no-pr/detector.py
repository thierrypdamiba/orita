"""The thirty-fourth real seam recipe (ROADMAP.md #490): a branch was
created straight on the repository, and no pull request has ever been
opened from it.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files
(`activities.json`, `pull_requests.json`), shaped like what
`ListRepositoryActivities`/`ListPullRequests` would actually return. Both
scopes already sit on `SCOPES.md`'s cleared oath table -- the exact pairing
`deleted-branch-pr-still-open` (task 485, the thirtieth real recipe)
already established for reading the repository's own Activity feed
alongside its PR list. This recipe asks Arcade for nothing new.

The seam: `deleted-branch-pr-still-open` watches the moment a branch's OWN
promise (an open PR built on it) survives after the branch itself is gone.
This recipe watches the opposite end of the same branch's life: the moment
it is CREATED and never turned into a pull request at all. GitHub's own
branch list UI shows "N commits ahead of main" for a branch like this, but
nothing in the API or the UI ever flags "no pull request has ever pointed
here" -- a branch can carry real, reviewable work (a spike, a fix, an
experiment) that nobody ever opened for review, sitting invisible next to
every branch that did. Only holding the Activity feed's own
`branch_creation` events against the live PR list at once, and checking
whether ANY pull request -- open, closed, or merged, the promise being
watched here is "was this ever turned into a PR at all," not whether that
PR is still open -- ever named that ref as its `head_ref`, surfaces it.

The repository's own default branch (`main`, and `master` for older repos)
is excluded outright, by name, even though it necessarily has a
`branch_creation` event of its own (usually the repository's first commit)
-- there is no promise a default branch ever makes to open a pull request
against itself; it IS the target every other branch's promise points at.
A `branch_creation` event whose ref already carries a matching pull
request -- in ANY state -- is excluded too: the promise here is narrower
than `deleted-branch-pr-still-open`'s ("still open"), and a merged or
closed PR already proves a human turned this branch into reviewable work,
whatever happened to it after.

Confidence is age-gated on how long the branch has existed with no PR
ever pointing at it, mirroring `merged-pr-never-released`'s and
`issue-closed-never-released`'s own 96-hour bar rather than
`deleted-branch-pr-still-open`'s shorter 24-hour one -- a branch sitting
without a PR for a day is ordinary, live, in-progress work (nobody expects
a spike branch to become a PR within hours of its first push); after four
days with nothing, it reads as forgotten rather than in flight. See
`recipe.json`'s `confidence_notes` for the full reasoning.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_ACTIVITIES_FIXTURE = _HERE.parents[1] / "fixtures" / "stale_branch_no_pr" / "activities.json"
DEFAULT_PULL_REQUESTS_FIXTURE = _HERE.parents[1] / "fixtures" / "stale_branch_no_pr" / "pull_requests.json"

# A branch younger than this with no PR yet may simply be in-progress work
# nobody has opened for review -- not yet a settled gap. Matches
# merged-pr-never-released's and issue-closed-never-released's own bar (a
# release-cadence-shaped grace window), not deleted-branch-pr-still-open's
# shorter one -- a branch's own natural time-to-first-PR runs longer than a
# deletion event's own resolution clock.
_STALE_HOURS = 96.0

# A repository's own default branch(es) never carry a "should have become a
# PR" promise -- they are the target every other branch's PR points at, not
# a candidate for one of their own. Named, not derived from a live
# `GetRepository` read (that scope is not part of this recipe's declared
# set) -- both common default-branch names are covered outright.
_DEFAULT_BRANCH_NAMES = frozenset({"main", "master"})


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _slug_ref(ref: str) -> str:
    """Branch names carry `/` (`feature/x`, `chore/y`); a GapCandidate slug
    does not -- sanitized the same way `deleted-branch-pr-still-open` already
    sanitizes its own ref-derived slugs."""
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


def _any_pr_for_ref(ref: str, pull_requests: list[PullRequest]) -> PullRequest | None:
    """Unlike `deleted-branch-pr-still-open`'s own lookup (which cares about
    a specific PR's current state), this one only needs to know whether ANY
    pull request, in any state, was ever opened from `ref` at all -- the
    first match found is returned, since the promise being checked ("was
    this branch ever turned into reviewable work") is already kept the
    moment one exists, regardless of what happened to it since."""
    for pr in pull_requests:
        if pr.head_ref == ref:
            return pr
    return None


def compute_gaps(
    activities: list[Activity], pull_requests: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Only `branch_creation` activity rows are considered at
    all -- any other activity type names no newly created branch and is
    silently skipped, the same "not this seam" precedent
    `deleted-branch-pr-still-open/detector.py` already sets for a `push`
    row. A creation event is excluded, named not hidden, the moment its ref
    is a default branch name, or the moment ANY pull request (any state) is
    already found pointing at it; everything left over -- a branch that
    exists with no pull request ever built on it -- is surfaced, aged into
    a confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for activity in activities:
        if activity.type != "branch_creation":
            continue

        if activity.ref in _DEFAULT_BRANCH_NAMES:
            excluded.append(GapCandidate(
                slug=f"default-branch-{_slug_ref(activity.ref)}",
                headline=f"'{activity.ref}' is the repository's own default branch",
                detail=f"'{activity.ref}' is a default-branch name. No pull request is ever expected to point back at it. No seam here.",
                confidence=0.0,
                evidence=[activity.url],
            ))
            continue

        pr = _any_pr_for_ref(activity.ref, pull_requests)
        if pr is not None:
            excluded.append(GapCandidate(
                slug=f"branch-has-pr-{_slug_ref(activity.ref)}",
                headline=f"Branch '{activity.ref}' already has pull request #{pr.number}",
                detail=f"'{activity.ref}' is claimed by PR #{pr.number} ('{pr.title}', state={pr.state}). No seam here.",
                confidence=0.0,
                evidence=[activity.url, pr.url],
            ))
            continue

        age_hours = (now - activity.created_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"stale-branch-no-pr-{_slug_ref(activity.ref)}",
            headline=f"Branch '{activity.ref}' exists, but no pull request has ever been opened from it",
            detail=(
                f"Activity feed shows {activity.ref!r} created {activity.created_at.isoformat()} "
                f"({age_hours:.1f}h ago); no PR in this repo's own list carries head_ref "
                f"{activity.ref!r}. Whatever work landed on that branch has never been offered "
                "for review."
            ),
            confidence=confidence,
            evidence=[activity.url],
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
