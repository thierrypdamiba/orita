"""The eighty-ninth real seam recipe: a GitHub release's own body claims a
"milestone #N" that doesn't exist at all.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`releases.json`,
`milestones.json`), shaped like what repeated `GetLatestRelease` reads
over time (the same "recent-releases history" convention
`release-claims-open-milestone/recipe.json` already established) and a
single `ListMilestones` call would actually return. Both scopes already
sit on `SCOPES.md`'s cleared oath table under the `github` row -- this
recipe asks Arcade for nothing new.

`release-claims-open-milestone` (task 385, the sixteenth real recipe) was
the first to pair a release's own body with `ListMilestones`, and its own
docstring drew the line precisely: a claimed milestone number that names
no real milestone at all is excluded there, named not hidden -- "a broken
reference is `dangling-issue-reference`'s own seam (over issues/PRs), not
this one's (over milestones)." That deferral pointed at a door that was
never actually built for the milestone number space: `release-note-
dangling-reference` (the twenty-third real recipe) already reads a
release body for a bare `#N`, but strictly against the shared issue/PR
number sequence, and never once opens `ListMilestones`. This recipe is
that seam, on the fourth of the five sources task 870 named and left open
-- the release-sourced sibling of `commit-claims-dangling-milestone`
(task 649, the seventy-sixth), `issue-comment-claims-dangling-milestone`
(task 865, the eighty-first), `review-comment-claims-dangling-milestone`
(task 866, the eighty-second), `slack-message-claims-dangling-milestone`
(task 867, the eighty-third), `linear-comment-claims-dangling-milestone`
(task 868, the eighty-fourth), `mention-claims-dangling-milestone` (task
870, the eighty-sixth), `milestone-claims-dangling-milestone` (task 871,
the eighty-seventh), and `readme-claims-dangling-milestone` (task 872,
the eighty-eighth), which closed the identical seam for a commit message,
an issue/PR timeline comment, a pull request's own inline review comment,
a Slack channel message, a Linear issue comment, a mortal's own X
mention, a milestone's own description, and README.md respectively.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_
numbers` verbatim -- the same shared grammar every `*-claims-dangling-
milestone` sibling already imports, negation check included -- rather
than a ninth independently retyped copy of the identical pattern.

Not `release-note-dangling-reference`'s seam wearing a new name: that
recipe watches a bare `#N` inside a release body against GitHub's shared
issue/PR number sequence and never once opens `ListMilestones`. A
milestone lives in its own, separate number space that issues and pull
requests never touch, so a `#N` that resolves cleanly as an issue could
still be a dangling MILESTONE claim, and a `#N` that is a real milestone
could just as easily collide with a real issue number. Confusing the two
spaces would be exactly the false-positive failure Ogun's law calls
fatal -- so this recipe reads `claimed_milestone_numbers`'s own
"milestone #N" phrase grammar, never the bare-`#N` grammar `release-note-
dangling-reference` already owns. Nor is it `release-claims-open-
milestone`'s seam wearing a new name: that recipe and this one are exact
inverses on one surface, and the boundary between them is the whole
point. There, a claimed number resolving to no real milestone is EXCLUDED
at 0.0 and a claim contradicted by a still-open milestone is surfaced;
here, the resolution failure IS the seam and a claimed number that DOES
resolve is excluded at 0.0, open or closed alike -- whether the claim is
TRUE is `release-claims-open-milestone`'s own remit, not this one's.

A release's body is GitHub's own permanent, published-once public record
-- the same "never gets a second edit pass" property `release-note-
dangling-reference`'s own `_DANGLING_CONFIDENCE` note already relies on --
so a broken milestone claim sitting inside one is exactly as durable, and
exactly as costly, as the one `commit-claims-dangling-milestone` already
guards against in a commit message.

Confidence is flat (0.8), not age-gated -- mirrors every prior claims-
dangling-milestone sibling's own reasoning, and lands where `release-
claims-open-milestone`'s own 24-hour edit-grace bar does NOT apply here:
that recipe age-gates because an OPEN milestone could close at any
moment, so a fresh claim about it might just be a race the milestone
tracker hasn't caught up to yet -- but a milestone number that does not
exist right now will not spontaneously start existing later, so no grace
period would mean anything here, the identical reasoning `commit-claims-
dangling-milestone`'s own docstring already gives for the same shape.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "release_claims_dangling_milestone"
DEFAULT_RELEASES_FIXTURE = _FIXTURE_DIR / "releases.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors every prior
# claims-dangling-milestone sibling's own _DANGLING_CONFIDENCE exactly
# (0.8): a nonexistent milestone number will not spontaneously start
# existing, whatever the age of the release naming it, and a release body
# never gets a second edit pass any more than a commit message does.
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
class Release:
    id: str
    title: str
    tag: str
    body: str
    published_at: datetime
    url: str


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def load_releases(path: Path | None = None) -> list[Release]:
    rows = _load_rows(path or DEFAULT_RELEASES_FIXTURE)
    return [
        Release(
            id=r["id"], title=r["title"], tag=r["tag"], body=r["body"],
            published_at=_parse_ts(r["published_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_milestones(path: Path | None = None) -> list[Milestone]:
    rows = _load_rows(path or DEFAULT_MILESTONES_FIXTURE)
    return [
        Milestone(number=r["number"], title=r["title"], state=r["state"], url=r["url"])
        for r in rows
    ]


def _find_milestone(number: int, milestones: list[Milestone]) -> Milestone | None:
    for milestone in milestones:
        if milestone.number == number:
            return milestone
    return None


def compute_gaps(
    releases: list[Release], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A claim is excluded, named not hidden,
    the moment a release makes no 'milestone #N' claim at all, or the
    milestone it names IS real (open or closed, this recipe does not care
    which) -- everything left over (a claimed milestone number with no
    real milestone behind it at all) is surfaced at a flat confidence.

    `now` is accepted, unused -- kept for interface parity with every
    other recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_
    scan` always threads one through), the identical "unused today, kept
    for the shape" choice `commit-claims-dangling-milestone/detector.py`
    already makes and explains for the identical reason: this recipe's
    confidence is flat, not age-gated, so there is nothing here for `now`
    to weigh against."""
    del now  # unused today; kept for interface parity, see docstring above.
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for release in sorted(releases, key=lambda r: r.id):
        numbers = _claimed_milestone_numbers(release.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{release.id}",
                headline=f"{release.title} names no milestone claim",
                detail=(
                    f"'{release.body}' ({release.url}) carries no 'milestone #N' claim "
                    "phrase. No seam here."
                ),
                confidence=0.0,
                evidence=[release.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a release body naming
        # the same milestone twice must not produce two identical
        # GapCandidates that tie each other out of rank()'s
        # SEPARATION_MARGIN, the same guard every dangling-milestone
        # sibling already holds.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-{release.id}-{number}",
                    headline=f"{release.title}'s claimed milestone #{number} is real",
                    detail=(
                        f"'{release.body}' ({release.url}) claims milestone #{number} "
                        f"('{milestone.title}', state '{milestone.state}'); the milestone "
                        "exists. Whether the claim itself is TRUE is a different recipe's "
                        "seam (release-claims-open-milestone), not this one's. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[release.url, milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"release-claims-dangling-milestone-{release.id}-{number}",
                headline=f"{release.title} claims milestone #{number}, which doesn't exist",
                detail=(
                    f"'{release.body}' ({release.url}) claims milestone #{number}, but no "
                    "milestone with that number exists at all. Nothing on either platform "
                    "ever checks a 'milestone #N' claim phrase written into a release's own "
                    "permanent body against the real milestone tracker -- release-note-"
                    "dangling-reference reads the same body only against the shared "
                    "issue/PR number sequence, a different number space."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[release.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    releases_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the-hand's gateway carries a
    live `GetLatestRelease` + `ListMilestones` read for a connected
    account and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    releases = load_releases(releases_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(releases, milestones, now=now)
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
