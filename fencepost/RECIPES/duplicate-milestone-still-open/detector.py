"""Thirty-second real seam recipe: two open milestones share the exact same
title, and nothing on GitHub ever flags it.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads one local fixture file (`milestones.json`),
shaped like what `ListMilestones` would return. That scope already sits on
SCOPES.md's cleared oath table -- this recipe asks Arcade for nothing new.

This is the third leg of the `duplicate-*-still-open` family alongside
`duplicate-issue-still-open` (task 376, the seventh real recipe) and
`duplicate-pr-still-open` (task 400, the twenty-second). Both of those watch
an explicit PROMISE: a mortal (or a god) writes "duplicate of #N" in an
issue or PR's own body, and that promise never gets honored because GitHub
gives it no auto-close wiring at all. Milestones have no equivalent
convention -- nobody writes "duplicate of milestone #N" in a milestone's
description in practice, so there is no prose marker to extract here.

The seam is structural instead of textual, and arguably more surprising:
GitHub enforces NO uniqueness constraint on milestone titles whatsoever.
Two, three, any number of open milestones in the same repository can carry
the byte-identical title forever, and nothing in GitHub's own UI or API
ever warns anyone. A milestone gets created, forgotten, and re-created
under the same name weeks later -- now the same body of work is tracked in
two open places at once, issues and PRs split between them, and neither
milestone alone shows this. Only holding the full milestone list at once
does.

Confidence is age-gated on how long the later (duplicate) milestone has
existed, mirroring both siblings' own 24-hour bar rather than inventing a
new number: a title collision younger than a day may just be a human
mid-cleanup, not yet a gap; past a day it is unambiguous. See
`recipe.json`'s `confidence_notes` for the full reasoning.

Only OPEN milestones are ever compared against each other for a live
duplicate pair -- a title reused after the first milestone with that title
already closed is the ordinary, unremarkable case (the redundancy already
resolved itself, or the name was deliberately reused for the next cycle of
work), not this recipe's seam. A title that names only one milestone in the
whole repo, open or closed, is excluded too, named not hidden -- there is
nothing to collide with.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_MILESTONES_FIXTURE = _HERE.parents[1] / "fixtures" / "duplicate_milestone_still_open" / "milestones.json"

# A duplicate title younger than this may just be a human mid-cleanup, not
# yet a gap -- matches duplicate-issue-still-open's and duplicate-pr-still-
# open's own 24h bar (a clear, easily-verified structural signal deserves a
# short grace window, not a long one).
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    created_at: datetime
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
            created_at=_parse_ts(r["created_at"]), url=r["url"],
        )
        for r in rows
    ]


def compute_gaps(
    milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Milestones are grouped by their exact, trimmed title.
    A title naming only one milestone is excluded outright -- there is no
    second record to collide with. A title shared by two or more milestones
    but currently open on at most one of them is excluded too -- whatever
    redundancy existed already resolved (the earlier one closed, or the
    name was deliberately reused). Everything left over -- a title held by
    two or more OPEN milestones at once -- is surfaced: the earliest-created
    one stands as the original, and every later one sharing its title is its
    own aged, ranked candidate."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    by_title: dict[str, list[Milestone]] = {}
    for m in milestones:
        by_title.setdefault(m.title.strip(), []).append(m)

    for title in sorted(by_title):
        group = by_title[title]

        if len(group) < 2:
            m = group[0]
            excluded.append(GapCandidate(
                slug=f"no-duplicate-title-{m.number}",
                headline=f"Milestone #{m.number} ('{title}') names no other milestone sharing its title",
                detail=f"Only one milestone in this repo is titled '{title}'. No seam here.",
                confidence=0.0,
                evidence=[m.url],
            ))
            continue

        open_group = sorted((m for m in group if m.state == "open"), key=lambda m: m.created_at)
        if len(open_group) < 2:
            ordered = sorted(group, key=lambda m: m.number)
            numbers = ", ".join(f"#{m.number}" for m in ordered)
            excluded.append(GapCandidate(
                slug=f"not-live-duplicate-{'-'.join(str(m.number) for m in ordered)}",
                headline=f"'{title}' is shared by {numbers}, but fewer than two currently read open",
                detail=(
                    f"Milestone(s) {numbers} all carry the title '{title}', but at most one of "
                    "them currently reads open. Whichever redundancy existed here has already "
                    "resolved -- either the earlier one closed, or the title was deliberately "
                    "reused for a later cycle of work."
                ),
                confidence=0.0,
                evidence=[m.url for m in ordered],
            ))
            continue

        original = open_group[0]
        for dup in open_group[1:]:
            age_hours = (now - dup.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"duplicate-milestone-still-open-{dup.number}-{original.number}",
                headline=f"Milestone #{dup.number} duplicates #{original.number}'s title ('{title}'), both still open",
                detail=(
                    f"'{title}' names both #{original.number} (opened "
                    f"{original.created_at.isoformat()}) and #{dup.number} (opened "
                    f"{dup.created_at.isoformat()}, {age_hours:.1f}h ago). Both currently read "
                    "open -- the same body of work is being tracked in two places at once, and "
                    "GitHub's own uniqueness-free milestone titles never once flagged it."
                ),
                confidence=confidence,
                evidence=[dup.url, original.url],
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
