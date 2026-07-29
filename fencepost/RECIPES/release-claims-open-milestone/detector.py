"""Sixteenth real seam recipe: a GitHub release's own body text claims a
milestone shipped ("milestone #N"), but the named milestone is not actually
closed.

The milestone-side third leg of the release-claims-X family, alongside
`release-claims-unmerged-pr` (task 378, a release's claim about a PR that
never merged) and `release-claims-unfixed-issue` (task 382, a release's
claim about an issue that never closed). Both existing legs watch a
release's own permanent public record disagree with a second record's real
state; this leg watches the identical shape against a milestone, reusing
`milestone-closed-never-released`'s (task 383) own `milestone #N` claim
phrase verbatim rather than inventing a fourth grammar for the same word.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`releases.json`,
`milestones.json`), shaped like what repeated `GetLatestRelease` reads over
time and `ListMilestones` would actually return. Both scopes already sit on
SCOPES.md's cleared oath table -- this recipe asks Arcade for nothing new.

The seam: a `milestone #N` claim phrase inside a release's body names a
milestone by number. If that milestone does not exist at all, it is
excluded here -- a broken reference is `dangling-issue-reference`'s own
seam (over issues/PRs), not this one's (over milestones). If it exists and
is closed, the claim was simply true -- excluded, named not hidden. If it
exists and is still open, the release's own permanent record disagrees with
reality: that is the gap.

Confidence is age-gated by the release's own publish time, mirroring
`release-claims-unmerged-pr`'s and `release-claims-unfixed-issue`'s own
reasoning: a claim checked within a few hours of publish might still be a
race (release published moments before the milestone is actually closed
out) rather than a settled documentation error.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "release_claims_open_milestone"
DEFAULT_RELEASES_FIXTURE = _FIXTURE_DIR / "releases.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A claim checked within this window of the release's own publish time may
# just be a race rather than a genuine, settled documentation error.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


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


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


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
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed milestone is excluded, named not hidden,
    the moment it names no real milestone at all, or the milestone it names
    is already closed -- everything left over (a shipped-it claim the
    milestone tracker itself contradicts) is surfaced, aged into a
    confidence score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for release in releases:
        numbers = _claimed_milestone_numbers(release.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{release.tag}",
                headline=f"Release {release.tag} names no milestone claim",
                detail=f"'{release.title}' carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[release.url],
            ))
            continue

        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)

            milestone = _find_milestone(number, milestones)
            if milestone is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-not-found-{release.tag}-{number}",
                    headline=f"Release {release.tag} claims milestone #{number}, which doesn't exist",
                    detail=f"'{release.title}' claims milestone #{number} shipped, but no such milestone exists. No seam here.",
                    confidence=0.0,
                    evidence=[release.url],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{release.tag}-{number}",
                    headline=f"Release {release.tag}'s claim about milestone #{number} holds",
                    detail=f"'{release.title}' claims milestone #{number} ('{milestone.title}') shipped; the milestone is closed. No seam here.",
                    confidence=0.0,
                    evidence=[release.url, milestone.url],
                ))
                continue

            age_hours = (now - release.published_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"release-claims-open-milestone-{release.tag}-{number}",
                headline=f"Release {release.tag} claims milestone #{number} shipped, but it's still open",
                detail=(
                    f"'{release.title}' (published {release.published_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims milestone #{number} ('{milestone.title}') "
                    f"shipped; the milestone's real state is '{milestone.state}'."
                ),
                confidence=confidence,
                evidence=[release.url, milestone.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    releases_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    release read and these loaders are swapped for real calls. The
    detection logic does not change when that happens."""
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
