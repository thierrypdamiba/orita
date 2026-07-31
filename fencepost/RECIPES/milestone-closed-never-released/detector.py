"""The fourteenth real seam recipe: a milestone closed long ago, but no
release published since has ever claimed it.

`merged-pr-never-released` (task 381, the twelfth real recipe) watches a
merged pull request sitting stale, uncredited by any release's own
`ships`/`includes`/`merges`/`via #N` claim. This recipe watches the
identical shape one level up the same project's own record hierarchy: a
milestone -- a bundle of issues and pull requests grouped under one
release-planning label -- reads closed, but its own number never appears
inside any release's own `milestone #N` claim phrase. Where a single PR
going uncredited might be a release note's oversight, a whole milestone
going uncredited is the same oversight at the scale that actually matters
to a project's own changelog discipline.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`milestones.json`,
`releases.json`), shaped like what `ListMilestones` and repeated
`GetLatestRelease` reads over time (the same "recent-releases history"
convention `merged-pr-never-released/recipe.json` already established for
its own fixture) would actually return. Both scopes already sit on
SCOPES.md's cleared oath table -- this recipe asks Arcade for nothing new.

The seam: a milestone's own number never appears inside any release's
`milestone #N` claim phrase, across every release read so far, not only
the newest one -- a milestone can go uncredited across several releases in
a row just as easily as a single PR can. A milestone that is still open
has nothing for a release to have missed yet -- excluded, not a gap. A
milestone that IS named by at least one release's claim phrase, at any
point in the read-so-far history, kept its promise -- excluded, named not
hidden. Everything left over -- a closed milestone no release has ever
claimed -- is the gap, aged by how long it has sat uncredited.
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
DEFAULT_MILESTONES_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_closed_never_released" / "milestones.json"
DEFAULT_RELEASES_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_closed_never_released" / "releases.json"

# A milestone closed under this age, with no release having claimed it yet,
# may simply be waiting on the project's own release cadence to catch up --
# not yet a settled gap. Matches merged-pr-never-released's own bar exactly.
_STALE_HOURS = 96.0


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
class Release:
    id: str
    title: str
    tag: str
    body: str
    published_at: datetime
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


def load_releases(path: Path | None = None) -> list[Release]:
    rows = _load_rows(path or DEFAULT_RELEASES_FIXTURE)
    return [
        Release(
            id=r["id"], title=r["title"], tag=r["tag"], body=r["body"],
            published_at=_parse_ts(r["published_at"]), url=r["url"],
        )
        for r in rows
    ]


def _claims_by_number(releases: list[Release]) -> dict[int, list[Release]]:
    """Every release, across the whole read-so-far history, that claims a
    given milestone number -- not just the newest one. A milestone only
    needs ONE release to have ever claimed it to be cleared."""
    claims: dict[int, list[Release]] = {}
    for release in releases:
        for number in _claimed_milestone_numbers(release.body):
            claims.setdefault(number, []).append(release)
    return claims


def compute_gaps(
    milestones: list[Milestone], releases: list[Release], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A milestone is excluded, named not hidden, the
    moment it is still open, or at least one release across the whole
    history read so far has already claimed it. Everything left over -- a
    closed milestone no release has ever named -- is surfaced, aged into a
    confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []
    claims = _claims_by_number(releases)

    for milestone in milestones:
        if milestone.state != "closed":
            excluded.append(GapCandidate(
                slug=f"milestone-not-closed-{milestone.number}",
                headline=f"Milestone #{milestone.number} is still open",
                detail=f"'{milestone.title}' reads state={milestone.state}. No seam here.",
                confidence=0.0,
                evidence=[milestone.url],
            ))
            continue

        if milestone.closed_at is None:
            excluded.append(GapCandidate(
                slug=f"milestone-closed-no-timestamp-{milestone.number}",
                headline=f"Milestone #{milestone.number} closed with no close timestamp",
                detail=(
                    f"'{milestone.title}' reads state=closed but carries no closed_at timestamp -- "
                    "a malformed record, not an open milestone."
                ),
                confidence=0.0,
                evidence=[milestone.url],
            ))
            continue

        claiming_releases = claims.get(milestone.number, [])
        if claiming_releases:
            release = claiming_releases[0]
            excluded.append(GapCandidate(
                slug=f"milestone-claimed-{milestone.number}",
                headline=f"Milestone #{milestone.number} is already claimed by release {release.tag}",
                detail=(
                    f"'{milestone.title}' (#{milestone.number}) closed "
                    f"{milestone.closed_at.isoformat()}; release {release.tag} "
                    f"('{release.title}') names it. No seam here."
                ),
                confidence=0.0,
                evidence=[milestone.url, release.url],
            ))
            continue

        age_hours = (now - milestone.closed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"milestone-closed-never-released-{milestone.number}",
            headline=f"Milestone #{milestone.number} closed, but no release has ever claimed it",
            detail=(
                f"'{milestone.title}' (#{milestone.number}) closed "
                f"{milestone.closed_at.isoformat()} ({age_hours:.1f}h ago); "
                "no release read so far names it in a 'milestone #N' claim."
            ),
            confidence=confidence,
            evidence=[milestone.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    milestones_path: Path | None = None,
    releases_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListMilestones`/`GetLatestRelease` read and these two loaders are
    swapped for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    milestones = load_milestones(milestones_path)
    releases = load_releases(releases_path)
    surfaced, excluded = compute_gaps(milestones, releases, now=now)
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
