"""The ninety-sixth real seam recipe: an issue or pull request's own
OPENING BODY invokes a real GitHub closing keyword against an issue
("fixes #N" / "closes #N" / "resolves #N", both tenses), but the named
issue never actually closed.

The leg of the claims-unfixed-issue family the OPENING BODY surface had
never grown. `readme-claims-unfixed-issue`, `release-claims-unfixed-issue`,
`milestone-claims-unfixed-issue`, `tweet-claims-unfixed-issue`,
`mention-claims-unfixed-issue`, `review-comment-claims-unfixed-issue`,
`slack-message-claims-unfixed-issue`, `linear-comment-claims-unfixed-issue`,
and `issue-comment-claims-unfixed-issue` cover nine text surfaces --
README, a release, a milestone description, a tweet, a stranger's own X
mention, a pull request's own inline review comment, a Slack message, a
Linear comment, and an issue/PR's own ordinary TIMELINE comment -- but
none of them ever reads an issue or pull request's own OPENING BODY, the
exact surface `issue-body-dangling-reference` (the twenty-fourth real
recipe) and `issue-body-claims-open-milestone` (the ninety-second)
already proved was worth watching for two other claim shapes on this
exact surface. Neither of those two ever checks a closing-keyword claim
against the issue tracker's own state, so the unfixed-issue leg of this
surface had never actually been built anywhere until now.

The seam is as sharp here as on `issue-comment-claims-unfixed-issue`'s
own: a closing keyword only ever auto-closes an issue when GitHub reads
it in a pull request's own body or a commit message merged to the
default branch (`commit-closes-keyword-issue-still-open`'s and
`merged-pr-issue-still-open`'s own seam) -- for an ORDINARY ISSUE's own
opening body, GitHub never honors the closing keyword at all (issues
carry no merge event to trigger on), and even on a PULL REQUEST's own
opening body, the keyword only fires once that PR actually merges to the
default branch -- an open PR's own body claiming "fixes #N" is exactly
as inert as an issue's, right up until the moment it merges. A claim
sitting in either object's still-open body was never going to resolve
itself while it stays open.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`issues.json`,
`pulls.json`, the identical shape `issue-body-claims-open-milestone`
already established for this exact surface). `ListIssues` and
`ListPullRequests` are both real, live, read-only tools on the-hand
gateway already, already cleared on SCOPES.md's oath table -- this
recipe asks Arcade for nothing new; it carries `"source": "fixture"`
only because CONTRIBUTING.md's MOCK ONLY law holds for every recipe on
the day it merges, not because the underlying scope itself is
unavailable.

Deliberately reuses `seam_engine.closing_keywords.closing_keyword_numbers`
verbatim -- the same shared grammar nine prior siblings already import
from there -- rather than a tenth independently retyped copy of the
identical pattern. Also reuses the exact `Issue`/`PullRequest` dataclass
shape and `load_issues`/`load_pulls` loaders `issue-body-claims-open-
milestone` already established for this surface, rather than a second,
independently drifting copy of the same two loaders.

Deliberately checks only the issue list, never the PR list -- the
identical scope every other `*-claims-unfixed-issue` sibling holds
itself to; a closing-keyword claim naming a real pull request is a
future `issue-body-claims-unmerged-pr`'s own remit, not this one's.

The seam: a closing-keyword phrase inside an issue or PR's own opening
body names an issue by number. If that issue does not exist at all, it
is excluded here -- that broken reference is `issue-body-dangling-
reference`'s own seam, not this one's (a bare #N reference and a
closing-keyword #N claim name the same number space, but that recipe
only ever asks whether the reference resolves, never whether a
closing-keyword claim about it holds -- the two recipes never collide on
the same candidate). If it exists and is closed, the claim was simply
true -- excluded, named not hidden. A body with no closing-keyword claim
phrase at all, or no body at all, is never examined -- it claims nothing
about a second record, so there is no seam to weigh, the identical
exclusion `issue-body-claims-open-milestone.compute_gaps` already makes
for a claim-free body.

Confidence is age-gated off the claiming record's own `updated_at`,
mirroring `issue-body-dangling-reference`'s, `issue-body-claims-open-
milestone`'s, and `issue-comment-claims-unfixed-issue`'s identical
reasoning: an issue or PR body is a text surface its own author can
still edit at any time, so a fresh claim earns a grace period before
being scored as a confirmed gap. 0.55 within 24 hours of the record's
own last update; 0.85 at or past 24 hours. See `recipe.json`'s
`confidence_notes` for the full reasoning.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.closing_keywords import closing_keyword_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "issue_body_claims_unfixed_issue"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# A claim checked within this many hours of the record's own updated_at
# may simply not have caught up yet -- the same editable-text-surface
# grace window issue-body-dangling-reference's, issue-body-claims-open-
# milestone's, and issue-comment-claims-unfixed-issue's own age-gates
# already use.
_EDIT_GRACE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows`
    holds."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


@dataclass
class Issue:
    number: int
    title: str
    state: str
    body: str
    updated_at: datetime
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    body: str
    updated_at: datetime
    url: str


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
            number=r["number"], title=r["title"], state=r["state"], body=r.get("body") or "",
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"], body=r.get("body") or "",
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A body with no closing-keyword claim
    phrase at all is never examined -- it claims nothing about a second
    record, so there is no seam to weigh. Both issues and pull requests
    are scanned as sources (either can carry a closing-keyword claim in
    its own opening body); only the issue list is ever matched against,
    the identical scope every `*-claims-unfixed-issue` sibling holds."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    _SOURCE_LABEL = {"issue": "Issue", "pr": "PR"}

    def _scan(source_kind: str, number: int, body: str, updated_at: datetime, url: str) -> None:
        label = _SOURCE_LABEL[source_kind]
        if not body:
            return

        numbers = closing_keyword_numbers(body)
        if not numbers:
            return

        # dict.fromkeys dedupes, order-preserving: a body naming the same
        # #N twice must not produce two identical GapCandidates that tie
        # each other out of rank()'s SEPARATION_MARGIN, the same guard
        # issue-body-claims-open-milestone and issue-comment-claims-
        # unfixed-issue already apply.
        for n in dict.fromkeys(numbers):
            issue = _find_issue(n, issues)
            if issue is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-issue-not-found-{source_kind}-{number}-{n}",
                    headline=f"{label} #{number} claims fixing #{n}, which doesn't exist",
                    detail=f"'{body}' ({url}) claims #{n} fixed, but no such issue exists. "
                           f"No seam here (see issue-body-dangling-reference).",
                    confidence=0.0,
                    evidence=[url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{source_kind}-{number}-{n}",
                    headline=f"{label} #{number}'s claim about #{n} holds",
                    detail=f"'{body}' ({url}) claims #{n} ('{issue.title}') fixed; "
                           f"issue #{n} is closed. No seam here.",
                    confidence=0.0,
                    evidence=[url, issue.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"issue-body-claims-unfixed-issue-{source_kind}-{number}-{n}",
                headline=f"{label} #{number} claims #{n} fixed, but #{n} is still open",
                detail=(
                    f"{label} #{number}'s own body ('{body}', {url}) claims #{n} "
                    f"('{issue.title}') fixed; the issue's real state is '{issue.state}'. "
                    f"An issue's opening body carries no auto-close trigger of its own, and "
                    f"a still-open PR's body has not merged yet either -- this claim was "
                    f"never going to resolve itself while it stays open."
                ),
                confidence=_confidence_for(updated_at, now=now),
                evidence=[url, issue.url],
            ))

    for issue in issues:
        _scan("issue", issue.number, issue.body, issue.updated_at, issue.url)
    for pull in pulls:
        _scan("pr", pull.number, pull.body, pull.updated_at, pull.url)

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    MOCK ONLY marker CONTRIBUTING.md requires of every recipe on the day
    it merges, not a claim the underlying scopes are unavailable
    (`ListIssues`/`ListPullRequests` are both live, cleared tools
    already)."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(issues, pulls, now=now)
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
