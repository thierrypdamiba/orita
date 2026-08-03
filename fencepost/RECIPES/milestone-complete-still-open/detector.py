"""Thirty-ninth real seam recipe: every issue inside an open milestone has

closed, and the milestone itself never did.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads one local fixture file
(`milestones.json`), shaped like what `ListMilestones` would return
(GitHub's real milestone objects already carry `open_issues`,
`closed_issues`, and `updated_at`). That scope already sits on
SCOPES.md's cleared oath table -- this recipe asks Arcade for nothing
new.

This is the mirror image of `overdue-milestone-still-open` (task 489):
that recipe watches a milestone's own CLOCK promise (a due date) go
unchecked; this one watches its own COMPLETION promise go unchecked.
GitHub tracks `open_issues`/`closed_issues` on every milestone object,
live, for free -- but closing the milestone itself is always a separate,
manual action nothing ever triggers. A milestone whose last open issue
closed five minutes ago looks, to every other tool reading this
repository, identical to one that finished a month ago and was simply
never wrapped up. Only holding `open_issues` and `state` at once shows
it at all.

The seam is structural, the same shape the whole milestone family
(`milestone-closed-issue-still-open`, `duplicate-milestone-still-open`,
`overdue-milestone-still-open`) already established: no cross-account
join is needed, because GitHub's own milestone object already carries
both halves of the promise (whether the work is done, and whether the
milestone itself closed) -- it simply never compares them itself.

There is no `completed_at` field on a real milestone object -- nothing
timestamps the instant `open_issues` hit zero. `updated_at` is the
closest real signal GitHub actually exposes (it moves whenever an issue
attached to the milestone changes, including the closing of the last
one), so confidence is age-gated on how long `updated_at` has sat still
while `open_issues` reads zero, mirroring every `*-still-open` sibling's
own 24-hour bar rather than inventing a new number or a new field.

A milestone with `open_issues == 0` AND `closed_issues == 0` is excluded
outright -- nothing was ever tracked inside it, so there is no
completion to have missed, only an empty milestone. A milestone still
carrying open issues is excluded -- it isn't complete yet. A milestone
already closed is excluded too -- whatever the timing, the wrap-up
promise was kept.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_MILESTONES_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_complete_still_open" / "milestones.json"

# A milestone whose open_issues hit zero less than this long ago may just
# not have been noticed yet by the human who'd close it -- matches every
# other *-still-open sibling's own 24h bar.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    open_issues: int
    closed_issues: int
    updated_at: datetime
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
            open_issues=r.get("open_issues", 0),
            closed_issues=r.get("closed_issues", 0),
            updated_at=_parse_ts(r["updated_at"]),
            url=r["url"],
        )
        for r in rows
    ]


def compute_gaps(
    milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Every milestone is judged independently: closed, never
    tracking any issues, or still tracking open ones are all excluded
    named, not hidden; an open milestone with every issue closed is
    surfaced, aged by how long `updated_at` has sat still."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in sorted(milestones, key=lambda m: m.number):
        if m.state != "open":
            excluded.append(GapCandidate(
                slug=f"not-open-{m.number}",
                headline=f"Milestone #{m.number} ('{m.title}') already reads closed",
                detail=(
                    f"Milestone #{m.number} is closed. Whichever order the issues and "
                    "the milestone itself closed in, the wrap-up promise is kept -- no "
                    "seam here."
                ),
                confidence=0.0,
                evidence=[m.url],
            ))
            continue

        if m.open_issues == 0 and m.closed_issues == 0:
            excluded.append(GapCandidate(
                slug=f"no-issues-tracked-{m.number}",
                headline=f"Milestone #{m.number} ('{m.title}') never tracked any issues",
                detail=(
                    f"Milestone #{m.number} carries zero open and zero closed issues. "
                    "Nothing was ever assigned to it, so there is no completion to have "
                    "missed -- just an empty milestone."
                ),
                confidence=0.0,
                evidence=[m.url],
            ))
            continue

        if m.open_issues > 0:
            excluded.append(GapCandidate(
                slug=f"not-complete-{m.number}",
                headline=f"Milestone #{m.number} ('{m.title}') still has {m.open_issues} open issue(s)",
                detail=(
                    f"Milestone #{m.number} still tracks {m.open_issues} open issue(s) "
                    f"against {m.closed_issues} closed. Not complete yet -- nothing "
                    "overdue about leaving it open."
                ),
                confidence=0.0,
                evidence=[m.url],
            ))
            continue

        idle_hours = (now - m.updated_at).total_seconds() / 3600.0
        confidence = 0.85 if idle_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"milestone-complete-still-open-{m.number}",
            headline=(
                f"Milestone #{m.number} ('{m.title}') has all {m.closed_issues} issue(s) "
                "closed, but the milestone itself is still open"
            ),
            detail=(
                f"Milestone #{m.number} ('{m.title}') reads 0 open issues against "
                f"{m.closed_issues} closed, last touched {m.updated_at.isoformat()} "
                f"({idle_hours:.1f}h ago), and still reads open. Closing a milestone is "
                "always a separate manual action -- GitHub never auto-closes one when "
                "the last issue inside it does."
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
