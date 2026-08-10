"""Seventy-eighth real seam recipe: a git tag was pushed to the repository,
but no GitHub Release object was ever published for it.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files
(`tags.json`, `releases.json`), shaped like what `ListTags` and
`ListReleases` would actually return. Neither scope sat on SCOPES.md's
cleared oath table before this recipe -- both are added in the same
commit as this file, with a WIP note explaining why (both clear the
allow-list's `Get*`/`List*` prefix check and name no forbidden write verb,
the identical naming-check every scope in this engine clears; neither is
exposed live on the-hand gateway today, confirmed the same way the
Slack/Linear notes above it already were).

This is the first recipe in the tree to read a git tag as its own object
at all -- grepped every prior recipe's docstring, README, and fixture for
`ListTags`/`GetTag`/"tag": zero hits outside ordinary release `tag_name`
fields already used for MATCHING, never for a tag's own existence. Pushing
a tag and publishing a release are two structurally independent GitHub
actions: `git push origin v1.1.0` creates a ref, full stop -- it fires no
webhook a Release listener would catch, appears nowhere on the Releases
page, and GitHub's own UI never once suggests turning it into one. A repo
can accumulate any number of tags that never become releases, silently,
forever.

Genuinely distinct from the closest sibling,
`../example-release-vs-changelog/` (the reference recipe CONTRIBUTING.md
points new contributors at): that recipe starts from a Release that
already exists and asks whether CHANGELOG.md caught up to it -- one level
downstream of this one. This recipe starts one level further upstream, at
the raw tag, and asks whether a Release was ever created for it in the
first place; a tag that never becomes a release also, definitionally,
never gets a chance to reach `example-release-vs-changelog`'s own seam.
It is also distinct from the `*-never-released` family
(`merged-pr-never-released`, `milestone-closed-never-released`,
`issue-closed-never-released`): those three read a Release's own BODY TEXT
for a later claim phrase ("ships #N", "milestone #N") about a different
object; this recipe never reads release body text at all -- it is a
structural, no-prose-marker existence check, matching a tag's own `name`
against a release's own `tag_name` field, the same "no keyword fuzziness
to misfire on" shape `example-release-vs-changelog` already established
for its own exact-tag match.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_TAGS_FIXTURE = _HERE.parents[1] / "fixtures" / "tag_never_released" / "tags.json"
DEFAULT_RELEASES_FIXTURE = _HERE.parents[1] / "fixtures" / "tag_never_released" / "releases.json"

# A tag younger than this may just be a human mid-release, not yet a gap --
# matches duplicate-milestone-still-open's own 24h bar for the identical
# reason: a clear, easily-verified structural signal deserves a short grace
# window, not a long one.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Tag:
    name: str
    sha: str
    pushed_at: datetime
    url: str


@dataclass
class Release:
    tag_name: str
    name: str
    id: str
    published_at: datetime
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_tags(path: Path | None = None) -> list[Tag]:
    rows = _load_rows(path or DEFAULT_TAGS_FIXTURE)
    return [
        Tag(name=r["name"], sha=r["sha"], pushed_at=_parse_ts(r["pushed_at"]), url=r["url"])
        for r in rows
    ]


def load_releases(path: Path | None = None) -> list[Release]:
    rows = _load_rows(path or DEFAULT_RELEASES_FIXTURE)
    return [
        Release(
            tag_name=r["tag_name"], name=r["name"], id=r["id"],
            published_at=_parse_ts(r["published_at"]), url=r["url"],
        )
        for r in rows
    ]


def _find_release(tag: Tag, releases: list[Release]) -> Release | None:
    for r in releases:
        if r.tag_name == tag.name:
            return r
    return None


def compute_gaps(
    tags: list[Tag], releases: list[Release], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. A tag is excluded, named not hidden, the moment an
    exact tag_name match is found among the releases; everything left over
    is age-gated on how long the tag has sat unreleased, mirroring
    duplicate-milestone-still-open's own 24h grace window rather than
    inventing a new number for a structurally similar "no prose marker"
    seam."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for tag in tags:
        release = _find_release(tag, releases)
        if release is not None:
            excluded.append(GapCandidate(
                slug=f"tag-released-{tag.name}",
                headline=f"Tag '{tag.name}' already has a matching GitHub Release",
                detail=f"Tag {tag.name!r} matches release {release.name!r} exactly by tag_name. No seam here.",
                confidence=0.0,
                evidence=[tag.url, release.url],
            ))
            continue

        age_hours = (now - tag.pushed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"tag-never-released-{tag.name}",
            headline=f"Tag '{tag.name}' was pushed but no GitHub Release was ever published for it",
            detail=(
                f"Tag {tag.name!r} (commit {tag.sha[:7]}) was pushed "
                f"{tag.pushed_at.isoformat()}, {age_hours:.1f}h ago -- no release in the "
                "record carries a matching tag_name. Pushing a tag and publishing a release "
                "are independent GitHub actions; nothing in the API or UI ever flags the gap."
            ),
            confidence=confidence,
            evidence=[tag.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    tags_path: Path | None = None,
    releases_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListTags`/`ListReleases` read and these two loaders are swapped for
    real reads. The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    tags = load_tags(tags_path)
    releases = load_releases(releases_path)
    surfaced, excluded = compute_gaps(tags, releases, now=now)
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
