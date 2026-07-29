"""Ninth real seam recipe: a GitHub release's own body text claims a pull
request shipped in it, but the pull request never actually merged.

Every recipe before this one compared two records that were each honestly
typed on their own terms -- the gap was only ever in whether one echoed the
other (`merged-pr-issue-still-open`, `release-not-tweeted`) or in a single
record's own claim about a second, MISSING record
(`dangling-issue-reference`). This recipe watches a third shape: a single
record's own claim about a second record that DOES exist, but whose real
state contradicts the claim. A release is not a draft -- once published it
is a permanent, public statement of what a version contains, and nothing on
GitHub's side ever checks that statement against the PR tracker's own truth.
`tools/closing_keyword_guard.py` already governs the town's own commit
messages for exactly this class of overclaim; nothing governs a release
body the same way.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`releases.json`,
`pulls.json`), shaped like what repeated `GetLatestRelease` reads over time
(the recent-releases history) and `ListPullRequests` would actually return.
Both scopes already sit on SCOPES.md's cleared oath table under the
`github` row -- this recipe asks Arcade for nothing new, the same
"releases-representing" convention `release-not-tweeted/recipe.json`
already established for its own declared scopes.

The seam: a claim phrase ("ships #N" / "includes #N" / "merges #N" /
"via #N", case-insensitive) inside a release's body names a PR by number.
If that PR does not exist at all, it is excluded here -- that broken
reference is `dangling-issue-reference`'s own seam. If it exists and is
merged, the claim was simply true -- excluded, named not hidden. If it
exists and is NOT merged (still open, or closed without merging), the
release's own permanent record disagrees with reality: that is the gap.

Confidence is age-gated by the release's own publish time, mirroring
`merged-pr-issue-still-open`'s reasoning: a claim checked within a few
hours of publish might still be a race (release published moments before
the real merge lands) rather than a settled documentation error.

The claim regex itself used to live here as an independently typed copy,
with `merged-pr-never-released/detector.py` (task 381) carrying a second,
textually-identical one and merely commenting that it was "identical...
on purpose" rather than importing it -- the same "two copies that happen
to agree today, nothing stopping them from drifting apart" shape task 389
found and fixed for `#N` extraction and task 390 found and fixed a second
time for the "milestone #N" claim phrase. Found here a third time (task
393) and fixed the same way: both PR-claim detectors now import
`claimed_pr_numbers` from the new `seam_engine.pr_claims` module.
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
DEFAULT_RELEASES_FIXTURE = _HERE.parents[1] / "fixtures" / "release_claims_unmerged_pr" / "releases.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "release_claims_unmerged_pr" / "pulls.json"

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
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
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
            id=r["id"], title=r["title"], tag=r["tag"], body=r["body"],
            published_at=_parse_ts(r["published_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(number=r["number"], title=r["title"], state=r["state"], merged=r["merged"], url=r["url"])
        for r in rows
    ]


def _find_pull(number: int, pulls: list[PullRequest]) -> PullRequest | None:
    for pr in pulls:
        if pr.number == number:
            return pr
    return None


def compute_gaps(
    releases: list[Release], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed PR is excluded, named not hidden, the
    moment it names no real PR at all, or the PR it names is actually
    merged -- everything left over (a claim the PR tracker itself
    contradicts) is surfaced, aged into a confidence score rank() can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for release in releases:
        numbers = _claimed_pr_numbers(release.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{release.tag}",
                headline=f"Release {release.tag} names no ships/includes/merges/via PR claim",
                detail=f"'{release.title}' carries no claim-phrase reference. No seam here.",
                confidence=0.0,
                evidence=[release.url],
            ))
            continue

        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)

            pr = _find_pull(number, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{release.tag}-{number}",
                    headline=f"Release {release.tag} claims #{number}, which doesn't exist",
                    detail=f"'{release.title}' claims #{number} shipped, but no such PR exists. No seam here (see dangling-issue-reference).",
                    confidence=0.0,
                    evidence=[release.url],
                ))
                continue

            if pr.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-{release.tag}-{number}",
                    headline=f"Release {release.tag}'s claim about #{number} holds",
                    detail=f"'{release.title}' claims #{number} shipped; PR #{number} ('{pr.title}') is merged. No seam here.",
                    confidence=0.0,
                    evidence=[release.url, pr.url],
                ))
                continue

            age_hours = (now - release.published_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"release-claims-unmerged-pr-{release.tag}-{number}",
                headline=f"Release {release.tag} claims #{number} shipped, but #{number} never merged",
                detail=(
                    f"'{release.title}' (published {release.published_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{pr.title}') shipped; "
                    f"the PR's real state is '{pr.state}', merged={pr.merged}."
                ),
                confidence=confidence,
                evidence=[release.url, pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    releases_path: Path | None = None,
    pulls_path: Path | None = None,
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
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(releases, pulls, now=now)
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
