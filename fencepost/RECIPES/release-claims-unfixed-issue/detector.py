"""Thirteenth real seam recipe: a GitHub release's own body text claims a
real closing keyword against an issue ("fixes #N" / "closes #N" /
"resolves #N", both tenses), but the issue never actually closed.

The issue-side twin of `release-claims-unmerged-pr` (task 378), which
watches the identical release-makes-a-permanent-false-claim shape but
against a pull request's merge state. This recipe watches the same shape
against an issue's open/closed state instead, using a real GitHub
closing-keyword (not the looser ships/includes/merges/via claim-phrase
`release-claims-unmerged-pr` uses for PRs) -- a release body saying "fixes
#N" is invoking the exact same auto-close grammar GitHub honors on a
commit or PR body, just never checked against reality once published.

Deliberately reuses `tools/closing_keyword_guard.py`'s own
`CLOSING_KEYWORD_RE` grammar verbatim, the same discipline
`commit-closes-keyword-issue-still-open` (task 377) already established:
one law, not a second copy of it drifting apart. "closing #N" (present
participle, Iron Rule #8's own prescribed safe form) never matches either
tense -- proven live, not just claimed.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`releases.json`,
`issues.json`), shaped like what repeated `GetLatestRelease` reads over
time and `ListIssues` would actually return. Both scopes already sit on
SCOPES.md's cleared oath table -- this recipe asks Arcade for nothing new.

The seam: a closing-keyword phrase inside a release's body names an issue
by number. If that issue does not exist at all, it is excluded here --
that broken reference is `dangling-issue-reference`'s own seam. If it
exists and is closed, the claim was simply true -- excluded, named not
hidden. If it exists and is still open, the release's own permanent record
disagrees with reality: that is the gap.

Confidence is age-gated by the release's own publish time, mirroring
`release-claims-unmerged-pr`'s reasoning: a claim checked within a few
hours of publish might still be a race (release published moments before
the real fix lands) rather than a settled documentation error.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "release_claims_unfixed_issue"
DEFAULT_RELEASES_FIXTURE = _FIXTURE_DIR / "releases.json"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"

# Mirrors tools/closing_keyword_guard.py's CLOSING_KEYWORD_RE verbatim (see
# the module docstring for why): both tenses, an optional colon, one or
# more spaces, then the number. "closing #N" (present participle) does not
# match either form -- Iron Rule #8's prescribed safe phrasing.
CLOSING_KEYWORD_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#(\d+)\b",
    re.IGNORECASE,
)

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
class Issue:
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


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"])
        for r in rows
    ]


def _claimed_issue_numbers(body: str) -> list[int]:
    return [int(n) for n in CLOSING_KEYWORD_RE.findall(body)]


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def compute_gaps(
    releases: list[Release], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed issue is excluded, named not hidden, the
    moment it names no real issue at all, or the issue it names is already
    closed -- everything left over (a fix-claim the issue tracker itself
    contradicts) is surfaced, aged into a confidence score rank() can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for release in releases:
        numbers = _claimed_issue_numbers(release.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{release.tag}",
                headline=f"Release {release.tag} names no fixes/closes/resolves issue claim",
                detail=f"'{release.title}' carries no closing-keyword reference. No seam here.",
                confidence=0.0,
                evidence=[release.url],
            ))
            continue

        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)

            issue = _find_issue(number, issues)
            if issue is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-issue-not-found-{release.tag}-{number}",
                    headline=f"Release {release.tag} claims fixing #{number}, which doesn't exist",
                    detail=f"'{release.title}' claims #{number} fixed, but no such issue exists. No seam here (see dangling-issue-reference).",
                    confidence=0.0,
                    evidence=[release.url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{release.tag}-{number}",
                    headline=f"Release {release.tag}'s claim about #{number} holds",
                    detail=f"'{release.title}' claims #{number} fixed; issue #{number} ('{issue.title}') is closed. No seam here.",
                    confidence=0.0,
                    evidence=[release.url, issue.url],
                ))
                continue

            age_hours = (now - release.published_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"release-claims-unfixed-issue-{release.tag}-{number}",
                headline=f"Release {release.tag} claims #{number} fixed, but #{number} is still open",
                detail=(
                    f"'{release.title}' (published {release.published_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{issue.title}') fixed; "
                    f"the issue's real state is '{issue.state}'."
                ),
                confidence=confidence,
                evidence=[release.url, issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    releases_path: Path | None = None,
    issues_path: Path | None = None,
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
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(releases, issues, now=now)
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
