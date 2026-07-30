"""The twenty-third real seam recipe: a release's own body counts on an
issue or pull request that isn't actually there.

`RECIPES/dangling-issue-reference/` (task 368) watches this exact seam
inside a commit message; `RECIPES/mention-dangling-reference/` (task 388)
watches it inside a mortal's X mention. Neither ever looked at the third
text surface this engine already reads for other reasons -- a release's
own body. A release note can mention `#N` in plain prose (background,
credit, a passing remark) with no ships/fixes/milestone claim phrase at
all -- so `release-claims-unmerged-pr`/`release-claims-unfixed-issue`/
`release-claims-open-milestone` (which only ever look AT a claim phrase's
own numbers) never examine it, and a typo or a deleted issue's number can
sit in a release note, public and permanent, same as it can in a commit.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`releases.json`,
`issues.json`, `pulls.json`), shaped like what `GetLatestRelease` (read
repeatedly over time, the same "recent-releases history" convention
`release-claims-unmerged-pr/recipe.json` already established), `ListIssues`,
and `ListPullRequests` would actually return. All three scopes already sit
on SCOPES.md's cleared oath table under the `github` row -- this recipe
asks Arcade for nothing new.

The seam: `#N` inside a release body is checked against BOTH the issue
list and the PR list, the same "one shared number sequence" discipline
`dangling-issue-reference` already established -- checking only one would
misfire on a perfectly good reference to a merged PR. A cross-repo
`owner/repo#N` reference is never even extracted as a candidate -- that
names a different repo's own number space on purpose. This recipe imports
`seam_engine.references.referenced_numbers` rather than writing a third
copy of the same extraction regex -- the identical "one law, not a third
copy of it" discipline tasks 389/390/393/394/396/400 already paid for on
five other shared patterns in this engine.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.references import referenced_numbers as _referenced_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_RELEASES_FIXTURE = _HERE.parents[1] / "fixtures" / "release_note_dangling_reference" / "releases.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "release_note_dangling_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "release_note_dangling_reference" / "pulls.json"

# Flat, not age-gated -- same reasoning as dangling-issue-reference's own
# `_DANGLING_CONFIDENCE`: a release body never gets a second edit pass any
# more than a commit message does, so there is no "give it time to catch
# up" grace period that means anything here.
_DANGLING_CONFIDENCE = 0.8


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows` holds
    (task 358/359's fix, applied here from the start)."""
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
class Issue:
    number: int
    title: str
    state: str
    url: str


@dataclass
class PullRequest:
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


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def compute_gaps(
    releases: list[Release], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A release with no `#N` reference at all
    is never examined -- it claims nothing about a second record, so there
    is no seam to weigh, the identical "not an invite at all" exclusion
    `dangling-issue-reference.compute_gaps` already makes for a reference-
    free commit."""
    del now  # unused today; kept for interface parity with every sibling recipe's compute_gaps(..., *, now=...)

    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for release in releases:
        for n in _referenced_numbers(release.body):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"release-note-ref-matched-{release.tag}-{n}",
                    headline=f"Release {release.tag}'s reference to #{n} matches a real issue or PR",
                    detail=f"'{release.body}' ({release.url}) references #{n}; a real issue or "
                           f"pull request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[release.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"release-note-dangling-reference-{release.tag}-{n}",
                headline=f"Release {release.tag} references #{n}, but no issue or PR #{n} exists here",
                detail=f"'{release.body}' ({release.url}) references #{n}; ListIssues + "
                       f"ListPullRequests found no issue or pull request with that number "
                       f"in this repo. Likely a typo, a reference to something deleted, or "
                       f"a number meant for a different repo, left standing in a public, "
                       f"permanent release note nobody proofreads a second time.",
                confidence=_DANGLING_CONFIDENCE,
                evidence=[release.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    releases_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetLatestRelease`/`ListIssues`/`ListPullRequests` read for a connected
    account and these three loaders are swapped for real reads. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    releases = load_releases(releases_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(releases, issues, pulls, now=now)
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
