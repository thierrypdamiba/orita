"""Thirty-third real seam recipe: a milestone's own due date passed, and
it is still open.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads one local fixture file
(`milestones.json`), shaped like what `ListMilestones` would return
(GitHub's real milestone objects already carry a `due_on` field). That
scope already sits on SCOPES.md's cleared oath table -- this recipe asks
Arcade for nothing new.

Every recipe in the `*-still-open` family so far watches an explicit
PROMISE written by a mortal or a god: a "duplicate of #N" note
(`duplicate-issue-still-open`, `duplicate-pr-still-open`,
`duplicate-milestone-still-open`), a closing keyword in a commit
(`commit-closes-keyword-issue-still-open`,
`commit-closes-keyword-pr-still-open`), a merged PR, a released tag. This
one watches a promise GitHub itself invites you to make and then never
checks: a milestone's own due date. GitHub renders an overdue `due_on` in
red on the milestone's own page -- but that is decoration. Nothing
auto-closes the milestone, nothing notifies anyone, nothing surfaces the
breach anywhere else in the API. A milestone due last month, still
tracking open issues, looks identical to one due next month to every
other tool reading this repository. Only holding `due_on` and `state` at
once, and comparing both against the clock, shows it at all.

The seam is structural, the same shape `duplicate-milestone-still-open`
(task 488) already established for this family: no cross-account join is
needed, because GitHub's own milestone object already carries both halves
of the promise (the date, and whether the work closed) -- it simply never
compares them itself.

Confidence is age-gated on how long past `due_on` the milestone has run
while still open, mirroring every `*-still-open` sibling's own 24-hour
bar rather than inventing a new number. See `recipe.json`'s
`confidence_notes` for the full reasoning.

A milestone with no `due_on` set at all is excluded outright -- there is
no promise to have broken. A milestone already closed is excluded too --
closing it, on time or late, resolved whatever promise the date made. A
milestone whose due date has not yet arrived is excluded -- there is
nothing overdue about it yet.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_MILESTONES_FIXTURE = _HERE.parents[1] / "fixtures" / "overdue_milestone_still_open" / "milestones.json"

# A milestone younger than this past its own due date may just be a human
# closing the last issue out right now -- matches duplicate-issue-still-
# open's, duplicate-pr-still-open's, and duplicate-milestone-still-open's
# own 24h bar (a clear, easily-verified structural signal deserves a short
# grace window, not a long one).
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    due_on: datetime | None
    open_issues: int
    closed_issues: int
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
            number=r["number"],
            title=r["title"],
            state=r["state"],
            due_on=_parse_ts(r["due_on"]) if r.get("due_on") else None,
            open_issues=r.get("open_issues", 0),
            closed_issues=r.get("closed_issues", 0),
            url=r["url"],
        )
        for r in rows
    ]


def compute_gaps(
    milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Every milestone is judged independently (unlike
    `duplicate-milestone-still-open`, no grouping by title is needed here):
    closed, no due date, or not yet due are all excluded named, not
    hidden; an open milestone past its own due date is surfaced, aged by
    how far past due it runs."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in sorted(milestones, key=lambda m: m.number):
        if m.state != "open":
            excluded.append(GapCandidate(
                slug=f"not-open-{m.number}",
                headline=f"Milestone #{m.number} ('{m.title}') already reads closed",
                detail=(
                    f"Milestone #{m.number} is closed. Whether it closed on time or "
                    "late, the due-date promise is resolved -- no seam here."
                ),
                confidence=0.0,
                evidence=[m.url],
            ))
            continue

        if m.due_on is None:
            excluded.append(GapCandidate(
                slug=f"no-due-date-{m.number}",
                headline=f"Milestone #{m.number} ('{m.title}') carries no due date",
                detail=f"Milestone #{m.number} has no due_on set. No promise, no breach.",
                confidence=0.0,
                evidence=[m.url],
            ))
            continue

        if m.due_on > now:
            excluded.append(GapCandidate(
                slug=f"not-yet-due-{m.number}",
                headline=f"Milestone #{m.number} ('{m.title}') isn't due until {m.due_on.date()}",
                detail=(
                    f"Milestone #{m.number}'s due date ({m.due_on.isoformat()}) is still "
                    "in the future. Nothing overdue about it yet."
                ),
                confidence=0.0,
                evidence=[m.url],
            ))
            continue

        overdue_hours = (now - m.due_on).total_seconds() / 3600.0
        confidence = 0.85 if overdue_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"overdue-milestone-still-open-{m.number}",
            headline=(
                f"Milestone #{m.number} ('{m.title}') was due {m.due_on.date()}, "
                f"still open with {m.open_issues} open issue(s)"
            ),
            detail=(
                f"Milestone #{m.number} ('{m.title}') was due {m.due_on.isoformat()} "
                f"({overdue_hours:.1f}h ago) and still reads open, with {m.open_issues} "
                f"open issue(s) against {m.closed_issues} closed. GitHub renders the "
                "date in red on the milestone's own page but takes no action of its "
                "own -- no auto-close, no notification, nothing surfaced anywhere else "
                "in the API."
            ),
            confidence=confidence,
            evidence=[m.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListMilestones` read and this one loader is swapped for a real read.
    The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(milestones, now=now)
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
