"""The seventeenth real seam recipe: an issue closed long ago, but no
release published since has ever claimed it.

The issue-side twin of `merged-pr-never-released` (task 381, PR) and
`milestone-closed-never-released` (task 383, milestone) -- the third and
last leg of the same shape, completing the set across all three GitHub
record types a release's own body can claim credit for. Where those two
recipes each named their own claim phrase (the PR family's
ships/includes/merges/via #N, the milestone family's own milestone #N),
this one reuses `release-claims-unfixed-issue`'s (task 382) own real
GitHub closing-keyword grammar verbatim (fixes/closes/resolves #N, both
tenses, `tools/closing_keyword_guard.py`'s own regex) -- an issue is
neither a PR nor a milestone, and GitHub already gives it a real,
canonical claim-of-credit phrase; there is no reason to invent a second
one.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`issues.json`,
`releases.json`), shaped like what `ListIssues` and repeated
`GetLatestRelease` reads over time (the same "recent-releases history"
convention `merged-pr-never-released`/`milestone-closed-never-released`
already established) would actually return. Both scopes already sit on
SCOPES.md's cleared oath table -- this recipe asks Arcade for nothing new.

The seam: an issue's own number never appears inside any release's
closing-keyword claim, across every release read so far, not only the
newest one. An issue that is still open has nothing for a release to have
missed yet -- excluded, not a gap. An issue that IS claimed by at least
one release's closing-keyword phrase, at any point in the read-so-far
history, kept its promise -- excluded, named not hidden. Everything left
over -- a closed issue no release has ever claimed credit for -- is the
gap, aged by how long it has sat uncredited.
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
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_closed_never_released" / "issues.json"
DEFAULT_RELEASES_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_closed_never_released" / "releases.json"

# Mirrors tools/closing_keyword_guard.py's CLOSING_KEYWORD_RE verbatim (the
# same regex release-claims-unfixed-issue's own detector already reuses):
# both tenses, an optional colon, one or more spaces, then the number.
# "closing #N" (present participle) does not match either form -- Iron
# Rule #8's prescribed safe phrasing.
CLAIM_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#(\d+)\b",
    re.IGNORECASE,
)

# An issue closed under this age, with no release having claimed it yet,
# may simply be waiting on the project's own release cadence to catch up --
# not yet a settled gap. Matches merged-pr-never-released's and
# milestone-closed-never-released's own bar exactly.
_STALE_HOURS = 96.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Issue:
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


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
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


def _claimed_issue_numbers(body: str) -> list[int]:
    return [int(n) for n in CLAIM_RE.findall(body)]


def _claims_by_number(releases: list[Release]) -> dict[int, list[Release]]:
    """Every release, across the whole read-so-far history, that claims a
    given issue number -- not just the newest one. An issue only needs ONE
    release to have ever claimed it to be cleared."""
    claims: dict[int, list[Release]] = {}
    for release in releases:
        for number in _claimed_issue_numbers(release.body):
            claims.setdefault(number, []).append(release)
    return claims


def compute_gaps(
    issues: list[Issue], releases: list[Release], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. An issue is excluded, named not hidden, the moment
    it is still open, or at least one release across the whole history
    read so far has already claimed it with a real closing keyword.
    Everything left over -- a closed issue no release has ever named --
    is surfaced, aged into a confidence score `rank()` can honestly
    weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []
    claims = _claims_by_number(releases)

    for issue in issues:
        if issue.state != "closed" or issue.closed_at is None:
            excluded.append(GapCandidate(
                slug=f"issue-not-closed-{issue.number}",
                headline=f"Issue #{issue.number} is still open",
                detail=f"'{issue.title}' reads state={issue.state}. No seam here.",
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        claiming_releases = claims.get(issue.number, [])
        if claiming_releases:
            release = claiming_releases[0]
            excluded.append(GapCandidate(
                slug=f"issue-claimed-{issue.number}",
                headline=f"Issue #{issue.number} is already claimed by release {release.tag}",
                detail=(
                    f"'{issue.title}' (#{issue.number}) closed "
                    f"{issue.closed_at.isoformat()}; release {release.tag} "
                    f"('{release.title}') claims it fixed. No seam here."
                ),
                confidence=0.0,
                evidence=[issue.url, release.url],
            ))
            continue

        age_hours = (now - issue.closed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"issue-closed-never-released-{issue.number}",
            headline=f"Issue #{issue.number} closed, but no release has ever claimed it",
            detail=(
                f"'{issue.title}' (#{issue.number}) closed "
                f"{issue.closed_at.isoformat()} ({age_hours:.1f}h ago); "
                "no release read so far claims it with a fixes/closes/resolves "
                "#N keyword."
            ),
            confidence=confidence,
            evidence=[issue.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    issues_path: Path | None = None,
    releases_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListIssues`/`GetLatestRelease` read and these two loaders are swapped
    for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    issues = load_issues(issues_path)
    releases = load_releases(releases_path)
    surfaced, excluded = compute_gaps(issues, releases, now=now)
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
