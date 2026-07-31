"""The eleventh real seam recipe: a milestone reads closed, but one of its
own pull requests never did.

The PR-side mirror of `milestone-closed-issue-still-open` (task 379), the
same pairing shape `merged-pr-issue-still-open`/`issue-closed-pr-still-open`
already established: an issue-side recipe gets a pull-request-side twin
watching the identical underlying seam on a different GitHub record type.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads two local fixture files (`milestones.json`,
`pull_requests.json`), shaped like what `ListMilestones`/`ListPullRequests`
would return. Both scopes are already declared elsewhere in this repo
(`milestone-closed-issue-still-open` and every PR-reading recipe before it
respectively) -- no new scope needed anywhere for this recipe.

The seam: closing a milestone on GitHub is a pure label operation. It never
touches the state of a single pull request assigned to it, any more than it
touches an issue's -- there is no auto-close wiring here at all, not even a
broken one. A human (or a god) closes the milestone believing the work
inside it is done; a pull request left open inside a closed milestone is
the exact seam this recipe watches, and it exists only by holding the
milestone record and the pull request record at the same instant -- neither
alone shows it.

Confidence is age-gated on how long the milestone has been closed while the
pull request still sits open -- see `recipe.json`'s `confidence_notes` for
the full reasoning, matching `milestone-closed-issue-still-open`'s own bar
exactly (the same seam shape, applied to a different record type, does not
get a different threshold just because the record type changed).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_MILESTONES_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_closed_pr_still_open" / "milestones.json"
DEFAULT_PULL_REQUESTS_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_closed_pr_still_open" / "pull_requests.json"

# A milestone closed under this age may not have had its pull requests swept
# yet -- not yet a gap. Matches milestone-closed-issue-still-open's own bar.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    closed_at: datetime | None
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    milestone_number: int | None
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_milestones(path: Path | None = None) -> list[Milestone]:
    rows = _load_rows(path or DEFAULT_MILESTONES_FIXTURE)
    return [
        Milestone(
            number=r["number"], title=r["title"], state=r["state"],
            closed_at=_parse_ts(r["closed_at"]) if r.get("closed_at") else None,
            url=r["url"],
        )
        for r in rows
    ]


def load_pull_requests(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULL_REQUESTS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"],
            merged=bool(r.get("merged", False)),
            milestone_number=r.get("milestone_number"), url=r["url"],
        )
        for r in rows
    ]


def _find_milestone(number: int, milestones: list[Milestone]) -> Milestone | None:
    for m in milestones:
        if m.number == number:
            return m
    return None


def compute_gaps(
    milestones: list[Milestone], pull_requests: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Only pull requests still in the `open` state are
    considered at all -- a pull request that closed itself (merged or not)
    has no gap left to surface, whatever its milestone reads. An open pull
    request is excluded, named not hidden, the moment it carries no
    milestone at all, names a milestone this fixture doesn't carry, or that
    milestone is itself still open (no seam yet -- there is nothing for this
    pull request to have missed). Everything left over -- an open pull
    request inside an already-closed milestone -- is surfaced, aged into a
    confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pr in pull_requests:
        if pr.state != "open":
            continue

        if pr.milestone_number is None:
            excluded.append(GapCandidate(
                slug=f"no-milestone-{pr.number}",
                headline=f"Pull request #{pr.number} carries no milestone",
                detail=f"'{pr.title}' is open with no milestone assigned. No seam here.",
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        milestone = _find_milestone(pr.milestone_number, milestones)
        if milestone is None:
            excluded.append(GapCandidate(
                slug=f"nonexistent-target-{pr.number}-{pr.milestone_number}",
                headline=f"Pull request #{pr.number} names milestone #{pr.milestone_number}, which does not exist",
                detail=(
                    f"'{pr.title}' is assigned to milestone #{pr.milestone_number}, but no such "
                    "milestone exists. A broken link, not a resolved promise."
                ),
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        if milestone.state != "closed":
            excluded.append(GapCandidate(
                slug=f"milestone-still-open-{pr.number}-{pr.milestone_number}",
                headline=f"Pull request #{pr.number}'s milestone #{pr.milestone_number} is still open",
                detail=(
                    f"'{pr.title}' is assigned to milestone #{pr.milestone_number}; "
                    "that milestone has not closed yet. No seam here."
                ),
                confidence=0.0,
                evidence=[pr.url, milestone.url],
            ))
            continue

        if milestone.closed_at is None:
            excluded.append(GapCandidate(
                slug=f"milestone-closed-no-timestamp-{pr.number}-{pr.milestone_number}",
                headline=f"Pull request #{pr.number}'s milestone #{pr.milestone_number} closed with no timestamp",
                detail=(
                    f"'{pr.title}' is assigned to milestone #{pr.milestone_number}; that milestone "
                    "reads closed but carries no close timestamp -- a malformed record, not an unresolved seam."
                ),
                confidence=0.0,
                evidence=[pr.url, milestone.url],
            ))
            continue

        age_hours = (now - milestone.closed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"milestone-closed-pr-still-open-{pr.number}-{milestone.number}",
            headline=(
                f"Milestone '{milestone.title}' closed, but pull request #{pr.number} "
                "inside it is still open"
            ),
            detail=(
                f"Milestone #{milestone.number} ('{milestone.title}') closed "
                f"{milestone.closed_at.isoformat()} ({age_hours:.1f}h ago); "
                f"'{pr.title}' (#{pr.number}) still reads open inside it."
            ),
            confidence=confidence,
            evidence=[milestone.url, pr.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    milestones_path: Path | None = None,
    pull_requests_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListMilestones`/`ListPullRequests` read and these two loaders are
    swapped for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    milestones = load_milestones(milestones_path)
    pull_requests = load_pull_requests(pull_requests_path)
    surfaced, excluded = compute_gaps(milestones, pull_requests, now=now)
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
