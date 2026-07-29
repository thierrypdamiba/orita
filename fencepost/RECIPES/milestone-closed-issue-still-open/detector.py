"""The tenth real seam recipe: a milestone reads closed, but one of its own

issues never did.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads two local fixture files (`milestones.json`,
`issues.json`), shaped like what `ListMilestones`/`ListIssues` would return.
`ListMilestones` is a new line on SCOPES.md's GitHub row (read-only, a plain
list-read, cleared through the same oath process task 371 already
established for `GetFileContents`) -- no other new scope.

The seam: closing a milestone on GitHub is a pure label operation. It never
touches the state of a single issue assigned to it -- there is no auto-close
wiring here at all, not even a broken one (the identical "no trigger ever
existed to fire" shape `duplicate-issue-still-open`, task 376, already
named for a duplicate marker). A human (or a god) closes the milestone
believing the work inside it is done; an issue left open inside a closed
milestone is the exact seam this recipe watches, and it exists only by
holding the milestone record and the issue record at the same instant --
neither alone shows it.

Confidence is age-gated on how long the milestone has been closed while the
issue still sits open -- see `recipe.json`'s `confidence_notes` for the
full reasoning behind the 24-hour bar, matching `merged-pr-issue-still-open`
and `duplicate-issue-still-open`'s own bar exactly.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_MILESTONES_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_closed_issue_still_open" / "milestones.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_closed_issue_still_open" / "issues.json"

# A milestone closed under this age may not have had its issues swept yet --
# not yet a gap.
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
class Issue:
    number: int
    title: str
    state: str
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


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
            number=r["number"], title=r["title"], state=r["state"],
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
    milestones: list[Milestone], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Only issues still in the `open` state are considered at
    all -- an issue that closed itself has no gap left to surface, whatever
    its milestone reads. An open issue is excluded, named not hidden, the
    moment it carries no milestone at all, names a milestone this fixture
    doesn't carry, or that milestone is itself still open (no seam yet --
    there is nothing for this issue to have missed). Everything left over --
    an open issue inside an already-closed milestone -- is surfaced, aged
    into a confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for issue in issues:
        if issue.state != "open":
            continue

        if issue.milestone_number is None:
            excluded.append(GapCandidate(
                slug=f"no-milestone-{issue.number}",
                headline=f"Issue #{issue.number} carries no milestone",
                detail=f"'{issue.title}' is open with no milestone assigned. No seam here.",
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        milestone = _find_milestone(issue.milestone_number, milestones)
        if milestone is None or milestone.state != "closed" or milestone.closed_at is None:
            excluded.append(GapCandidate(
                slug=f"milestone-still-open-{issue.number}-{issue.milestone_number}",
                headline=f"Issue #{issue.number}'s milestone #{issue.milestone_number} is still open",
                detail=(
                    f"'{issue.title}' is assigned to milestone #{issue.milestone_number}; "
                    "that milestone has not closed yet. No seam here."
                ),
                confidence=0.0,
                evidence=[issue.url] + ([milestone.url] if milestone else []),
            ))
            continue

        age_hours = (now - milestone.closed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"milestone-closed-issue-still-open-{issue.number}-{milestone.number}",
            headline=(
                f"Milestone '{milestone.title}' closed, but issue #{issue.number} "
                "inside it is still open"
            ),
            detail=(
                f"Milestone #{milestone.number} ('{milestone.title}') closed "
                f"{milestone.closed_at.isoformat()} ({age_hours:.1f}h ago); "
                f"'{issue.title}' (#{issue.number}) still reads open inside it."
            ),
            confidence=confidence,
            evidence=[milestone.url, issue.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    milestones_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListMilestones` read and these two loaders are swapped for real reads.
    The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    milestones = load_milestones(milestones_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(milestones, issues, now=now)
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
