"""The eighty-seventh real seam recipe: a milestone's own description
claims a "milestone #N" that doesn't exist at all.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads ONE local fixture file (`milestones.json`),
shaped like what a single `ListMilestones` call would actually return --
the same "one list plays both roles" shape `milestone-claims-open-
milestone` (the fifty-first real recipe) already established, because a
milestone claiming another milestone is a same-toolkit, same-call
comparison. That scope already sits on `SCOPES.md`'s cleared oath table;
this recipe asks Arcade for nothing new, and its `toolkit` stays
`github`-only.

`milestone-claims-open-milestone`'s own docstring drew the line
precisely: a claimed milestone number that names no real milestone at
all is excluded there, named not hidden -- "a broken reference is
`milestone-body-dangling-reference`'s own seam, not this one's." That
deferral was checked live by task 870's own-remit sweep and found never
actually built: `milestone-body-dangling-reference` watches a bare `#N`
inside a milestone's own description against the shared GitHub issue/PR
number sequence, and never once opens `ListMilestones`. A milestone
lives in its own, separate number space, so a `#N` that resolves cleanly
as a real issue could still be a dangling MILESTONE claim, and a `#N`
that is a real milestone could just as easily collide with a real issue
number -- conflating the two would misfire exactly the false-positive
failure Ogun's law calls fatal. This recipe is that seam, on the second
of the five sources task 870 named and left open (`milestone`, `readme`,
`release`, `tweet` remained after `mention-claims-dangling-milestone`
closed the first) -- the milestone-sourced sibling of `commit-claims-
dangling-milestone` (task 649, the seventy-sixth), `issue-comment-
claims-dangling-milestone` (task 865, the eighty-first), `review-
comment-claims-dangling-milestone` (task 866, the eighty-second),
`slack-message-claims-dangling-milestone` (task 867, the eighty-third),
`linear-comment-claims-dangling-milestone` (task 868, the eighty-
fourth), and `mention-claims-dangling-milestone` (task 870, the eighty-
sixth), which closed the identical seam for a commit message, an
issue/PR timeline comment, a pull request's own inline review comment, a
Slack channel message, a Linear issue comment, and a mortal's own X
mention respectively. `readme`, `release`, and `tweet` remain open,
correctly, for a future hour.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim -- the same shared grammar every `*-claims-dangling-milestone`
sibling already imports -- rather than a seventh independently retyped
copy of the identical pattern.

The claim stays narrow, the same no-grading law every sibling holds: if
a milestone claims ITSELF (`milestone #76` written inside milestone
#76's own description), that is excluded outright, the identical
self-claim exclusion `milestone-claims-open-milestone` already makes --
a milestone repeating its own number is not a claim about a second
record, so there is no seam to weigh. A claimed milestone number that
DOES resolve to a real milestone is excluded too, named not hidden,
regardless of whether that milestone is open or closed -- whether the
claim is TRUE is `milestone-claims-open-milestone`'s own seam, not this
one's; this recipe only ever asks whether the name resolves to anything
at all. A milestone with no description at all is never examined --
there is no claim to have broken.

Confidence is flat (0.8), not age-gated -- mirrors every prior claims-
dangling-milestone sibling's own reasoning rather than `milestone-
claims-open-milestone`'s 24-hour edit-grace bar. That bar exists because
an OPEN milestone could close at any moment, so a fresh claim about it
might just be a race the description hasn't caught up to yet; a
milestone number that does not exist right now will not spontaneously
start existing later no matter how long the description sits
unedited, so there is no grace period that means anything here.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.milestone_claims import claimed_milestone_numbers as _claimed_milestone_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "milestone_claims_dangling_milestone"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors every prior
# claims-dangling-milestone sibling's own _DANGLING_CONFIDENCE exactly
# (0.8): a nonexistent milestone number will not spontaneously start
# existing, whatever the age of the description naming it.
_DANGLING_CONFIDENCE = 0.8


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows`
    holds."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    description: str
    updated_at: datetime
    url: str


def load_milestones(path: Path | None = None) -> list[Milestone]:
    rows = _load_rows(path or DEFAULT_MILESTONES_FIXTURE)
    return [
        Milestone(
            number=r["number"], title=r["title"], state=r["state"],
            description=r.get("description") or "",
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def _find_milestone(number: int, milestones: list[Milestone]) -> Milestone | None:
    for milestone in milestones:
        if milestone.number == number:
            return milestone
    return None


def compute_gaps(
    milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A milestone with no description at
    all is never examined -- it claims nothing about a second record, so
    there is no seam to weigh, the identical exclusion `milestone-
    claims-open-milestone.compute_gaps` already makes. Every milestone
    in the input list plays both roles at once: the claimant AND a
    possible target for some OTHER milestone's claim -- there is only
    one list here, the same shape `milestone-claims-open-milestone`
    already established.

    `now` is accepted, unused -- kept for interface parity with every
    other recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_
    scan` always threads one through); this recipe's confidence is flat,
    not age-gated, so there is nothing here for `now` to weigh against."""
    del now  # unused today; kept for interface parity, see docstring above.
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in sorted(milestones, key=lambda m: m.number):
        if not m.description:
            continue

        numbers = _claimed_milestone_numbers(m.description)
        if not numbers:
            continue

        # dict.fromkeys dedupes, order-preserving: a description naming
        # the same "milestone #N" twice must not produce two identical
        # GapCandidates that tie each other out of rank()'s
        # SEPARATION_MARGIN, the same guard every dangling-milestone
        # sibling already holds.
        for n in dict.fromkeys(numbers):
            if n == m.number:
                excluded.append(GapCandidate(
                    slug=f"self-claim-milestone-{m.number}",
                    headline=f"Milestone #{m.number} names itself, not a seam",
                    detail=f"'{m.description}' ({m.url}) names milestone #{n}, its own "
                           f"number. A milestone naming itself is not a claim about a "
                           f"second record. No seam here.",
                    confidence=0.0,
                    evidence=[m.url],
                ))
                continue

            target = _find_milestone(n, milestones)
            if target is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-milestone-{m.number}-{n}",
                    headline=f"Milestone #{m.number}'s claimed milestone #{n} is real",
                    detail=(
                        f"'{m.description}' ({m.url}) claims milestone #{n} "
                        f"('{target.title}', state '{target.state}'); the milestone "
                        "exists. Whether the claim itself is TRUE is a different "
                        "recipe's seam (milestone-claims-open-milestone), not this "
                        "one's. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[m.url, target.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"milestone-claims-dangling-milestone-{m.number}-{n}",
                headline=f"Milestone #{m.number} claims milestone #{n}, which doesn't exist",
                detail=(
                    f"'{m.description}' ({m.url}) claims milestone #{n}, but no "
                    "milestone with that number exists at all. Nothing on either "
                    "platform ever checks a 'milestone #N' claim phrase written into "
                    "another milestone's own description against the real milestone "
                    "tracker."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[m.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the-hand's gateway carries a
    live `ListMilestones` read for a connected account and this loader
    is swapped for a real call. The detection logic does not change one
    line when that happens."""
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
