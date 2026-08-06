"""The fifty-first real seam recipe: a milestone's own description names
a real "milestone #N" claim phrase against a SIBLING milestone, but the
named milestone is not actually closed.

The last remaining leg of the "claims-open-milestone" family. README
(`readme-claims-open-milestone`, task 419-ish), a release
(`release-claims-open-milestone`, task 385), a tweet
(`tweet-claims-open-milestone`), and a stranger's own X mention
(`mention-claims-open-milestone`, task 564) all already check a
`milestone #N` claim phrase against the milestone tracker's own live
state -- but none of them ever read a milestone's OWN `description`
field, the same text surface `milestone-claims-unfixed-issue` (task 535)
and `milestone-claims-unmerged-pr` (task 567) already opened for the
sibling claims-unfixed-issue and claims-unmerged-pr families. Those two
recipes proved the milestone-side leg is real for issue claims and PR
claims; this one closes the identical gap for the third and last claim
shape, milestone claims, completing the full 5-surface x 3-claim-type
grid (mention, milestone, readme, release, tweet) x (open-milestone,
unfixed-issue, unmerged-pr) this whole claims-X family has been filling
in one leg at a time since task 385.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim -- the same shared grammar `readme-claims-open-milestone`,
`release-claims-open-milestone`, `tweet-claims-open-milestone`, and
`mention-claims-open-milestone` already import from there (task 389
centralized what had been two independently retyped copies) -- rather
than a sixth independently-retyped copy of the identical pattern.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads ONE local fixture file (`milestones.json`),
shaped like what a single `ListMilestones` call would actually return --
unlike every other sibling in this family, both the claiming record and
the claimed-about record live in the same list, because a milestone
claiming another milestone is a same-toolkit, same-call comparison. That
scope already sits on `SCOPES.md`'s cleared oath table -- this recipe
asks Arcade for nothing new, and its `toolkit` stays `github`-only (the
total recipe count grows, the plus-joined count does not -- the same
shape `milestone-claims-unmerged-pr`'s own merge held).

The seam: a `milestone #N` claim phrase inside milestone M's own
description names a DIFFERENT milestone by number. If M claims itself,
that's excluded outright -- a milestone repeating its own number is not a
claim about a second record, so there is no seam to weigh (a shape none
of the other four claims-open-milestone siblings can even produce, since
none of them ARE a milestone). If the named milestone does not exist at
all, it is excluded here -- a broken reference is
`milestone-body-dangling-reference`'s own seam, not this one's. If it
exists and is closed, the claim was simply true -- excluded, named not
hidden. If it exists and is still open, one milestone's own free-text
description disagrees with the milestone tracker's real state for
another record: that is the gap.

Confidence is age-gated off the CLAIMING milestone's own `updated_at`,
mirroring `milestone-claims-unfixed-issue`'s and
`milestone-claims-unmerged-pr`'s identical reasoning rather than
`readme-claims-open-milestone`'s flat 0.85: a milestone description,
like an issue or PR body, is a text surface its author can still edit at
any time, so a fresh claim earns the same 24-hour grace window every
sibling editable-text recipe in this engine already uses before being
scored as a confirmed gap. A milestone with no description at all is
excluded outright -- there is no claim to have broken.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "milestone_claims_open_milestone"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A dangling claim inside a description touched less than this many hours
# ago is not yet scored as a confirmed gap -- it may simply not have been
# fixed yet. Same 24-hour shape milestone-claims-unfixed-issue's and
# milestone-claims-unmerged-pr's own age-gates already use, applied here
# for the identical reason: a milestone's description is a text surface
# its author can still edit at any time.
_EDIT_GRACE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    description: str
    updated_at: datetime
    url: str


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows` holds
    (task 358/359's fix, applied here from the start)."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


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


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A milestone with no description at all
    is never examined -- it claims nothing about a second record, so
    there is no seam to weigh, the identical "not an invite at all"
    exclusion `milestone-claims-unfixed-issue.compute_gaps` already
    makes for a description-free milestone. Every milestone in the input
    list plays both roles at once: the claimant AND a possible target for
    some OTHER milestone's claim -- there is only one list here, unlike
    every other sibling in this family."""
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
        # SEPARATION_MARGIN (task 442).
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
            if target is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-not-found-milestone-{m.number}-{n}",
                    headline=f"Milestone #{m.number} claims milestone #{n}, which doesn't exist",
                    detail=f"'{m.description}' ({m.url}) claims milestone #{n} shipped, but "
                           f"no such milestone exists in this repo. No seam here (see "
                           f"milestone-body-dangling-reference).",
                    confidence=0.0,
                    evidence=[m.url],
                ))
                continue

            if target.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-milestone-{m.number}-{n}",
                    headline=f"Milestone #{m.number}'s claim about milestone #{n} holds",
                    detail=f"'{m.description}' ({m.url}) claims milestone #{n} "
                           f"('{target.title}') shipped; that milestone is closed. "
                           f"No seam here.",
                    confidence=0.0,
                    evidence=[m.url, target.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"milestone-claims-open-milestone-{m.number}-{n}",
                headline=f"Milestone #{m.number} claims milestone #{n} shipped, but it's still open",
                detail=(
                    f"Milestone #{m.number}'s description ('{m.description}', {m.url}) claims "
                    f"milestone #{n} ('{target.title}') shipped; its real state is "
                    f"'{target.state}'."
                ),
                confidence=_confidence_for(m.updated_at, now=now),
                evidence=[m.url, target.url],
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
    WIP marker this recipe carries until the Hand's gateway carries a
    live `ListMilestones` read for a connected account and this loader is
    swapped for a real call. The detection logic does not change one line
    when that happens."""
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
