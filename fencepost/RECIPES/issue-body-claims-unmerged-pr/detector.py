"""The ninety-seventh real seam recipe: an issue or pull request's own
OPENING BODY invokes a real GitHub closing keyword against a PULL
REQUEST ("fixes #N" / "closes #N" / "resolves #N", both tenses), but the
named pull request never actually merged.

`issue-body-claims-unfixed-issue` (the ninety-sixth) left this exact
door open on purpose, by name, in its own docstring: it "deliberately
checks only the issue list, never the PR list -- the identical scope
every other `*-claims-unfixed-issue` sibling holds itself to -- a
closing-keyword claim naming a real pull request is a future
`issue-body-claims-unmerged-pr`'s own remit, not this one's." This
recipe is that door, opened: the PR-side twin of that recipe, built the
same way `commit-closes-keyword-pr-still-open` was already built as
`commit-closes-keyword-issue-still-open`'s own twin -- same fixture
shape (one sibling fixture directory, swap the target record type from
issue to PR), same shared-module import discipline, same test rigor.

The seam is the identical shape `issue-body-claims-unfixed-issue`'s own
docstring already proved for the issue-tracker side, applied here to the
PR tracker: GitHub only ever honors a closing keyword when it reads one
inside a pull request's own body or a commit message, and only once
that PR actually merges to the default branch (`commit-closes-keyword-
pr-still-open`'s own seam, on the commit-message side). An issue's own
opening body carries no merge event of its own to trigger on at all --
GitHub never honors a closing keyword sitting there, full stop -- and a
still-open PR's own opening body is exactly as inert as an issue's,
right up until the moment (if ever) it merges. A claim sitting in either
object's still-open body naming a PR that stays open too was never
going to resolve itself while both stay open.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`issues.json`,
`pulls.json`, the identical shape `issue-body-claims-unfixed-issue`
already established for this exact surface). `ListIssues` and
`ListPullRequests` are both real, live, read-only tools on the-hand
gateway already, already cleared on SCOPES.md's oath table -- this
recipe asks Arcade for nothing new; it carries `"source": "fixture"`
only because CONTRIBUTING.md's MOCK ONLY law holds for every recipe on
the day it merges, not because the underlying scope itself is
unavailable.

Deliberately reuses `seam_engine.closing_keywords.closing_keyword_numbers`
verbatim -- the same shared grammar `issue-body-claims-unfixed-issue`
already imports from there -- rather than a second, independently
retyped copy of the identical pattern. Also reuses the exact
`Issue`/`PullRequest` dataclass shape and `load_issues`/`load_pulls`
loaders `issue-body-claims-unfixed-issue` already established for this
surface (the `PullRequest` dataclass here additionally carries `merged`,
the one field `commit-closes-keyword-pr-still-open`'s own target-side
`PullRequest` needs and the issue-tracker-side sibling never did, to
report an already-resolved claim's true outcome -- merged vs. closed
without merging -- rather than collapsing both into one undifferentiated
"resolved" message).

Deliberately checks only the pull-request list, never the issue list --
the mirror image of `issue-body-claims-unfixed-issue`'s own boundary. A
closing-keyword claim naming a real ISSUE number is out of this
recipe's remit entirely and is excluded here as not-found, exactly as a
claim naming a real PR number is excluded as not-found on the
issue-tracker-side sibling -- the two recipes never collide on the same
candidate, each covering exactly its own half of the shared number
space.

The seam: a closing-keyword phrase inside an issue or PR's own opening
body names a pull request by number. If that PR does not exist at all
(including a claim that happens to land on a real ISSUE number instead),
it is excluded here -- that broken reference is a dangling-reference
seam, not this one's. If it exists and has already resolved -- merged OR
closed without merging -- the claim was simply true (or moot), excluded
and named, not hidden, mirroring `commit-closes-keyword-pr-still-open`'s
own `_RESOLVED_STATES` reasoning. A body with no closing-keyword claim
phrase at all, or no body at all, is never examined -- it claims nothing
about a second record, so there is no seam to weigh.

Confidence is age-gated off the claiming record's own `updated_at`,
mirroring `issue-body-claims-unfixed-issue`'s identical reasoning: an
issue or PR body is a text surface its own author can still edit at any
time, so a fresh claim earns a grace period before being scored as a
confirmed gap. 0.55 within 24 hours of the record's own last update;
0.85 at or past 24 hours. See `recipe.json`'s `confidence_notes` for the
full reasoning.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "issue_body_claims_unmerged_pr"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# A claim checked within this many hours of the record's own updated_at
# may simply not have caught up yet -- the same editable-text-surface
# grace window issue-body-claims-unfixed-issue's own age-gate uses.
_EDIT_GRACE_WINDOW_HOURS = 24.0

# A PR counts as "resolved" here whether it merged or was closed without
# merging -- either way, whatever it promised is done being tracked
# under that number. Matches commit-closes-keyword-pr-still-open's own
# _RESOLVED_STATES reasoning, applied to the same shared PR-state field.
_RESOLVED_STATES = ("closed",)


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
    merged: bool
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
            number=r["number"], title=r["title"], state=r["state"], merged=r["merged"],
            body=r.get("body") or "", updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def _find_pr(number: int, pulls: list[PullRequest]) -> PullRequest | None:
    for pr in pulls:
        if pr.number == number:
            return pr
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
    its own opening body); only the pull-request list is ever matched
    against, the mirror image of `issue-body-claims-unfixed-issue`'s own
    issue-only boundary."""
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
        # issue-body-claims-unfixed-issue already applies.
        for n in dict.fromkeys(numbers):
            pr = _find_pr(n, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{source_kind}-{number}-{n}",
                    headline=f"{label} #{number} claims closing #{n}, which isn't a pull request here",
                    detail=f"'{body}' ({url}) claims #{n} closed, but no such pull request "
                           f"exists. Out of this recipe's remit either way (a genuinely dangling "
                           f"number, or a real issue number instead of a PR).",
                    confidence=0.0,
                    evidence=[url],
                ))
                continue

            if pr.state in _RESOLVED_STATES:
                how = "merged" if pr.merged else "closed without merging"
                excluded.append(GapCandidate(
                    slug=f"claim-true-{source_kind}-{number}-{n}",
                    headline=f"{label} #{number}'s claim about #{n} holds",
                    detail=f"'{body}' ({url}) claims #{n} ('{pr.title}') closed; "
                           f"pull request #{n} is {how}. No seam here.",
                    confidence=0.0,
                    evidence=[url, pr.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"issue-body-claims-unmerged-pr-{source_kind}-{number}-{n}",
                headline=f"{label} #{number} claims #{n} closed, but #{n} is still open, unmerged",
                detail=(
                    f"{label} #{number}'s own body ('{body}', {url}) claims #{n} "
                    f"('{pr.title}') closed; the pull request's real state is '{pr.state}', "
                    f"not merged. Neither an issue's opening body nor a still-open PR's own "
                    f"body has a merge event to trigger on -- this claim was never going to "
                    f"resolve itself while #{n} stays open."
                ),
                confidence=_confidence_for(updated_at, now=now),
                evidence=[url, pr.url],
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
