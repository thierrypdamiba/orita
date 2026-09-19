"""Hundred-eleventh real seam recipe: the project's own version manifest
(`pyproject.toml`, `package.json`, `Cargo.toml`, or any sibling file that
carries a `version` field) was bumped, but no git tag was ever pushed for
that version — the release that shipped in code and never became a
release at all.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files
(`manifest_versions.json`, `tags.json`), shaped like what `GetFileContents`
(read a version manifest at its current HEAD) and `ListTags` would
actually return. Neither scope is new — both already sit on `SCOPES.md`'s
cleared oath table under the `github` row (`GetFileContents` reads
`example-release-vs-changelog`'s own `CHANGELOG.md`; `ListTags` reads
`../tag-never-released/`'s own tags). No new scope is asked for anywhere
in this recipe.

Distinct from the closest sibling, `../tag-never-released/`: that recipe
starts from a tag that already exists and asks whether a GitHub Release
object was ever published for it — one level downstream. This recipe
starts one level further UPSTREAM, at the version string a human (or a
bot) already typed into a committed file, and asks whether a tag was ever
pushed for it at all. A version bump that never becomes a tag also,
definitionally, never gets a chance to reach `tag-never-released`'s own
seam — `git push origin main` moves the manifest; nothing about that push
creates a ref, fires a tag-shaped webhook, or nudges anyone to run
`git tag`. A repo can accumulate any number of version bumps that never
became a tag, silently, forever — the exact "shipped in code, never
became a release" gap Fencepost exists to name.

Matching is by NORMALIZED exact version string, not keyword overlap —
the same "no fuzziness to misfire on" discipline
`example-release-vs-changelog` and `tag-never-released` already hold for
their own exact-match seams. Git tags conventionally carry a leading `v`
(`v1.4.0`); manifest `version` fields conventionally do not (`1.4.0`) —
`_normalize_version` strips an optional leading `v`/`V` from both sides
before comparing, so the two ordinary spelling conventions never register
as a false gap.

A version string carrying a pre-release/build-metadata suffix (`-rc.1`,
`-alpha`, `-beta`, `-dev`, `-SNAPSHOT`, `+build`) is excluded outright,
named not hidden — the suffix is itself the author's own explicit "not
released yet" marker (semver's own vocabulary for exactly this), so
flagging it as a missing tag would be the precise crying-wolf false
positive Ògún's law forbids: the human already said, in the version
string itself, that this one is not done.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_MANIFESTS_FIXTURE = _HERE.parents[1] / "fixtures" / "manifest_version_never_tagged" / "manifest_versions.json"
DEFAULT_TAGS_FIXTURE = _HERE.parents[1] / "fixtures" / "manifest_version_never_tagged" / "tags.json"

# semver's own vocabulary for "not released yet," spelled out explicitly by
# whoever wrote the version string -- a pre-release/build-metadata suffix
# is excluded on sight, never scored as a gap. Matches case-insensitively,
# anywhere after a `-` or `+` separator, the same "named exception, not a
# guess" shape `gmail_calendar._is_invite` uses for its own ICS-required gate.
_PRERELEASE_MARKER_RE = re.compile(
    r"[-+](rc|alpha|beta|dev|snapshot|pre|nightly|build)\b", re.IGNORECASE
)


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _normalize_version(v: str) -> str:
    """Strip a single optional leading `v`/`V` -- `v1.4.0` and `1.4.0` name
    the same release under the two ordinary spelling conventions a tag and
    a manifest field each tend to use. Nothing else about the string is
    touched: a genuine difference anywhere past that one leading letter
    (`1.4.0` vs `1.4.0-rc.1`) still counts as two different versions, on
    purpose -- see `_PRERELEASE_MARKER_RE` for how a suffix is judged
    separately, before this normalization is ever reached."""
    return v[1:] if v and v[0] in ("v", "V") else v


@dataclass
class ManifestVersion:
    path: str
    version: str
    url: str


@dataclass
class Tag:
    name: str
    sha: str
    pushed_at: datetime
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_manifest_versions(path: Path | None = None) -> list[ManifestVersion]:
    """Read-only: load version-manifest rows from the fixture (or a real
    `GetFileContents` read of the same shape, once this recipe's scopes
    graduate off the fixture -- see `tag-never-released`'s own WIP
    doctrine for how that graduation happens without changing a line of
    `compute_gaps` below)."""
    rows = _load_rows(path or DEFAULT_MANIFESTS_FIXTURE)
    return [ManifestVersion(path=r["path"], version=r["version"], url=r["url"]) for r in rows]


def load_tags(path: Path | None = None) -> list[Tag]:
    rows = _load_rows(path or DEFAULT_TAGS_FIXTURE)
    return [
        Tag(name=r["name"], sha=r["sha"], pushed_at=_parse_ts(r["pushed_at"]), url=r["url"])
        for r in rows
    ]


def _find_tag(manifest: ManifestVersion, tags: list[Tag]) -> Tag | None:
    target = _normalize_version(manifest.version)
    for tag in tags:
        if _normalize_version(tag.name) == target:
            return tag
    return None


def compute_gaps(
    manifests: list[ManifestVersion], tags: list[Tag]
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. A manifest version is excluded, named not hidden,
    either because its own suffix already declares it unreleased, or
    because a normalized-exact tag match was found for it; everything left
    over is a version that shipped in a committed file with no tag ever
    pushed for it -- the gap this recipe exists to name."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in manifests:
        if _PRERELEASE_MARKER_RE.search(m.version):
            excluded.append(GapCandidate(
                slug=f"manifest-prerelease-{m.path}-{m.version}",
                headline=f"'{m.path}' declares {m.version}, marked pre-release -- not a gap",
                detail=(
                    f"{m.path} carries version {m.version!r}, which names its own "
                    "pre-release/build-metadata suffix. The author already said, in "
                    "the version string itself, that this one is not released yet."
                ),
                confidence=0.0,
                evidence=[m.url],
            ))
            continue

        tag = _find_tag(m, tags)
        if tag is not None:
            excluded.append(GapCandidate(
                slug=f"manifest-tagged-{m.path}-{m.version}",
                headline=f"'{m.path}' version {m.version} already has a matching tag",
                detail=(
                    f"{m.path} declares {m.version!r}, which matches tag {tag.name!r} "
                    "exactly once both are normalized. No seam here."
                ),
                confidence=0.0,
                evidence=[m.url, tag.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"manifest-version-never-tagged-{m.path}-{m.version}",
            headline=f"'{m.path}' declares {m.version}, but no git tag was ever pushed for it",
            detail=(
                f"{m.path} declares version {m.version!r}; no tag in the record "
                f"normalizes to the same string. Bumping a manifest and pushing a tag "
                "are independent actions -- nothing in the API or the UI ever flags the gap."
            ),
            confidence=0.75,
            evidence=[m.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    manifests_path: Path | None = None,
    tags_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetFileContents`/`ListTags` read and these two loaders are swapped
    for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    manifests = load_manifest_versions(manifests_path)
    tags = load_tags(tags_path)
    surfaced, excluded = compute_gaps(manifests, tags)
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
