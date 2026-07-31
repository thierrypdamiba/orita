"""The twelfth real seam recipe: a pull request merged long ago, but no
release published since has ever claimed it.

`release-claims-unmerged-pr` (task 378, the ninth real recipe) watches a
release's own body making a FALSE claim about a PR that exists but never
merged -- a single record's claim contradicted by a second record's real
state. This recipe watches the mirror seam: a PR that genuinely merged,
sitting stale, that no release has ever bothered to claim at all -- a
single record's own silence about a second record whose state is true and
uncontested. Where `release-claims-unmerged-pr` checks one release's body
against the PR tracker, this recipe checks the PR tracker against EVERY
release read so far -- a PR can go uncredited across several releases in a
row, not only the newest one, so the newest release alone is not enough to
clear it.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`pull_requests.json`,
`releases.json`), shaped like what repeated `GetLatestRelease` reads over
time (the same "recent-releases history" convention
`release-claims-unmerged-pr/recipe.json` already established for its own
fixture) and `ListPullRequests` would actually return. Both scopes already
sit on SCOPES.md's cleared oath table under the `github` row -- this
recipe asks Arcade for nothing new.

The seam: a merged pull request's number never appears inside any release's
own claim phrase ("ships #N" / "includes #N" / "merges #N" / "via #N",
case-insensitive -- the identical regex `release-claims-unmerged-pr` already
uses, deliberately reused rather than redrifted, the same "one law, not two
copies of it" discipline the isinstance-guard and memoization campaigns
already paid for). A PR that never merged at all has nothing for a release
to have missed yet -- excluded, not a gap. A PR that IS named by at least
one release's claim phrase kept its promise -- excluded, named not hidden.
Everything left over -- a merged PR no release has ever claimed -- is the
gap, aged by how long it has sat uncredited.

That "identical regex, deliberately reused" claim above was not actually
backed by an import when this recipe shipped: `_CLAIM_RE` was retyped a
second time here, with nothing connecting it to `release-claims-unmerged-
pr`'s own copy -- the same "two copies that happen to agree today, nothing
stopping them from drifting apart" shape task 389 found and fixed for `#N`
extraction and task 390 found and fixed a second time for the "milestone
#N" claim phrase. Found here a third time (task 393) and fixed the same
way: both PR-claim detectors now import `claimed_pr_numbers` from the new
`seam_engine.pr_claims` module.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.pr_claims import claimed_pr_numbers as _claimed_pr_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULL_REQUESTS_FIXTURE = _HERE.parents[1] / "fixtures" / "merged_pr_never_released" / "pull_requests.json"
DEFAULT_RELEASES_FIXTURE = _HERE.parents[1] / "fixtures" / "merged_pr_never_released" / "releases.json"

# A merged pull request younger than this, with no release having claimed
# it yet, may simply be waiting on the project's own release cadence to
# catch up -- not yet a settled gap.
_STALE_HOURS = 96.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    merged_at: datetime | None
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


def load_pull_requests(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULL_REQUESTS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"],
            merged=bool(r.get("merged", False)),
            merged_at=_parse_ts(r["merged_at"]) if r.get("merged_at") else None,
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
    given PR number -- not just the newest one. A PR only needs ONE release
    to have ever claimed it to be cleared; this builds that lookup once."""
    claims: dict[int, list[Release]] = {}
    for release in releases:
        for number in _claimed_pr_numbers(release.body):
            claims.setdefault(number, []).append(release)
    return claims


def compute_gaps(
    pull_requests: list[PullRequest], releases: list[Release], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    own `compute_gaps`. A pull request is excluded, named not hidden, the
    moment it never merged at all, or at least one release across the
    whole history read so far has already claimed it. Everything left
    over -- a merged pull request no release has ever named -- is
    surfaced, aged into a confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []
    claims = _claims_by_number(releases)

    for pr in pull_requests:
        if not pr.merged:
            excluded.append(GapCandidate(
                slug=f"pr-not-merged-{pr.number}",
                headline=f"Pull request #{pr.number} never merged",
                detail=f"'{pr.title}' reads state={pr.state}, merged={pr.merged}. No seam here.",
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        if pr.merged_at is None:
            excluded.append(GapCandidate(
                slug=f"pr-merged-no-timestamp-{pr.number}",
                headline=f"Pull request #{pr.number} merged with no merge timestamp",
                detail=(
                    f"'{pr.title}' reads merged=True but carries no merged_at timestamp -- "
                    "a malformed record, not an unmerged PR."
                ),
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        claiming_releases = claims.get(pr.number, [])
        if claiming_releases:
            release = claiming_releases[0]
            excluded.append(GapCandidate(
                slug=f"pr-claimed-{pr.number}",
                headline=f"Pull request #{pr.number} is already claimed by release {release.tag}",
                detail=(
                    f"'{pr.title}' (#{pr.number}) merged {pr.merged_at.isoformat()}; "
                    f"release {release.tag} ('{release.title}') names it. No seam here."
                ),
                confidence=0.0,
                evidence=[pr.url, release.url],
            ))
            continue

        age_hours = (now - pr.merged_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"merged-pr-never-released-{pr.number}",
            headline=f"Pull request #{pr.number} merged, but no release has ever claimed it",
            detail=(
                f"'{pr.title}' (#{pr.number}) merged {pr.merged_at.isoformat()} "
                f"({age_hours:.1f}h ago); no release read so far names it in a "
                "ships/includes/merges/via claim."
            ),
            confidence=confidence,
            evidence=[pr.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pull_requests_path: Path | None = None,
    releases_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListPullRequests`/`GetLatestRelease` read and these two loaders are
    swapped for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pull_requests = load_pull_requests(pull_requests_path)
    releases = load_releases(releases_path)
    surfaced, excluded = compute_gaps(pull_requests, releases, now=now)
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
