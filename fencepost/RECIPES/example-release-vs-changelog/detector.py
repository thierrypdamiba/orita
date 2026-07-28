"""Example seam recipe: a GitHub release shipped, but this project's own
CHANGELOG.md never got the matching entry.

This is the reference implementation CONTRIBUTING.md points a first-time
contributor at — copy this directory's shape (`recipe.json` + `detector.py`,
a MOCK ONLY fixture under `fencepost/fixtures/<slug>/`) for a new recipe.

Read-only in spirit, MOCK ONLY in practice: this module only ever reads two
local fixture files (`releases.json`, `changelog.json`), the same "fixture
today, live scope tomorrow" shape as `gmail_calendar.py`. `recipe.json`
declares the GitHub scopes (`GetRepository`, `ListRepoCommits`) this detector
would lean on once it reads live data instead of a fixture — both already
sit on SCOPES.md's oath table, so this recipe asks for nothing new.

Matching by exact release tag, not keyword overlap, on purpose: a release's
own tag either has a changelog entry with that exact `version` or it does
not — no fuzzy matching to misfire on, which is why `recipe.json`'s
confidence_notes can honestly claim a flat, un-inflated score.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_RELEASES_FIXTURE = _HERE.parents[1] / "fixtures" / "example_recipe" / "releases.json"
DEFAULT_CHANGELOG_FIXTURE = _HERE.parents[1] / "fixtures" / "example_recipe" / "changelog.json"


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Release:
    id: str
    title: str
    tag: str
    published_at: datetime
    url: str


@dataclass
class ChangelogEntry:
    version: str
    text: str
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_releases(path: Path | None = None) -> list[Release]:
    rows = _load_rows(path or DEFAULT_RELEASES_FIXTURE)
    return [
        Release(
            id=r["id"], title=r["title"], tag=r["tag"],
            published_at=_parse_ts(r["published_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_changelog(path: Path | None = None) -> list[ChangelogEntry]:
    rows = _load_rows(path or DEFAULT_CHANGELOG_FIXTURE)
    return [ChangelogEntry(version=r["version"], text=r["text"], url=r["url"]) for r in rows]


def _find_entry(release: Release, changelog: list[ChangelogEntry]) -> ChangelogEntry | None:
    for entry in changelog:
        if entry.version == release.tag:
            return entry
    return None


def compute_gaps(
    releases: list[Release], changelog: list[ChangelogEntry]
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) — same shape as `scan.compute_candidates`
    and `gmail_calendar.compute_gaps`. A release is excluded, named not
    hidden, the moment an exact-tag changelog entry is found for it;
    everything left over is the gap this recipe exists to name."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for r in releases:
        entry = _find_entry(r, changelog)
        if entry is not None:
            excluded.append(GapCandidate(
                slug=f"changelog-matched-{r.tag}",
                headline=f"'{r.title}' already has a CHANGELOG.md entry",
                detail=f"Release {r.tag} matches changelog entry {entry.version!r} exactly. No seam here.",
                confidence=0.0,
                evidence=[r.url, entry.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"release-vs-changelog-{r.tag}",
            headline=f"Release '{r.title}' shipped but CHANGELOG.md was never updated",
            detail=f"Published {r.published_at.isoformat()}; no changelog entry carries tag {r.tag!r}.",
            confidence=0.80,
            evidence=[r.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    releases_path: Path | None = None,
    changelog_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as
    `gmail_calendar.run_gmail_calendar_scan` — `source: "fixture"` is the
    honest WIP marker every recipe carries until the Hand connects a live
    account and this detector's loaders are swapped for real reads, the same
    way task 16's Gmail/Calendar detector is built to graduate."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    releases = load_releases(releases_path)
    changelog = load_changelog(changelog_path)
    surfaced, excluded = compute_gaps(releases, changelog)
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
