"""The fifty-fourth real seam recipe. A pull request's own inline code
REVIEW comment invokes a real GitHub closing keyword against an issue
("fixes #N" / "closes #N" / "resolves #N", both tenses), but the named
issue never actually closed.

The review-comment-side leg the claims-unfixed-issue family had never
grown. `readme-claims-unfixed-issue`, `release-claims-unfixed-issue`,
`milestone-claims-unfixed-issue`, `tweet-claims-unfixed-issue`, and
`mention-claims-unfixed-issue` cover every text surface this family has
ever checked -- README, a release, a milestone description, a tweet, and
a stranger's own X mention -- and `test_recipe_ordinal_doctrine.py`'s own
history calls that grid closed at fifteen legs (five sources times three
claim types). None of those five ever read a GitHub-native surface at
all: every one of them lives on the town's own text (README/release/
milestone/tweet) or an inbound X mention. This recipe reads a genuinely
different, sixth source the claims-X grid never touched: `RECIPES/review-
comment-dangling-reference/` (the forty-fourth real recipe) proved
`ListReviewCommentsInARepository` is a real, live, read-only tool on
the-hand gateway and used it to check whether a review comment's own
`#N` reference merely EXISTS; this recipe reuses the identical fixture
shape and live scope to ask the claims-X family's own sharper question
of the same surface instead -- does a review comment's own closing-
keyword CLAIM actually hold, not just whether the number it names is
real.

The seam is sharper here than on any of the five existing claims-X
sources: a closing keyword only ever auto-closes an issue when it
appears in a PULL REQUEST'S OWN BODY or a commit message merged to the
default branch (`commit-closes-keyword-issue-still-open`'s and
`merged-pr-issue-still-open`'s own seam) -- GitHub has never once, in
its history, honored a closing keyword typed into an ordinary review
comment. A reviewer writing "this also fixes #2101" inline, believing
(or implying to a later reader) that the parent PR's merge will close
it, is stating something GitHub was never going to act on regardless of
whether the PR merges -- a more durable false promise than a claim on a
surface that at least COULD have triggered a real close.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`review_comments.json`,
`issues.json`), shaped like what `ListReviewCommentsInARepository` and
`ListIssues` would actually return. Both scopes already sit on
`SCOPES.md`'s cleared oath table -- `ListReviewCommentsInARepository` live
since `review-comment-dangling-reference`; `ListIssues` used by nearly
every recipe in this engine. No new scope is asked for anywhere in this
recipe.

Deliberately reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE`
verbatim -- the same shared grammar `mention-claims-unfixed-issue`,
`tweet-claims-unfixed-issue`, `release-claims-unfixed-issue`,
`commit-closes-keyword-issue-still-open`, and `issue-closed-never-released`
already import from there -- rather than a sixth independently retyped
copy of the identical pattern. "Closing #N" (present participle, Iron
Rule #8's own prescribed safe form) never matches either tense here
either, same as everywhere else this grammar is used. Deliberately checks
only the issue list, never the PR list -- the identical scope every other
`*-claims-unfixed-issue` sibling holds itself to; a closing-keyword claim
that actually names a real pull request is out of this recipe's own
remit, the same "not this seam" boundary those siblings already draw
around `*-claims-unmerged-pr`.

The seam: a closing-keyword phrase inside a review comment names an
issue by number. If that issue does not exist at all, it is excluded here
-- that broken reference is `issue-body-dangling-reference`'s/`review-
comment-dangling-reference`'s own seam, not this one's. If it exists and
is closed, the claim was simply true -- excluded, named not hidden. A
review comment with no body at all (`null` or empty) is never examined,
the identical "not a claim at all" exclusion `review-comment-dangling-
reference.compute_gaps` already makes for a body-free comment. If the
claimed issue exists and is still open, a reviewer's own permanent
inline claim already disagrees with GitHub's own record, and nothing on
either surface ever compares the two.

Confidence is age-gated off the review comment's own `updated_at`,
mirroring `review-comment-dangling-reference`'s own reasoning rather than
`mention-claims-unfixed-issue`'s: a review comment, like an issue/PR body
or a milestone description, is a text surface its author can still edit
at any time, unlike a mention or a tweet, which is posted once and stands.
0.55 within 24 hours of the comment's own last update (the claim, or the
comment carrying it, may simply not have caught up yet); 0.85 at or past
24 hours (nobody is coming back to fix it). See `recipe.json`'s
`confidence_notes` for the full reasoning.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.closing_keywords import CLOSING_KEYWORD_RE
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_REVIEW_COMMENTS_FIXTURE = _HERE.parents[1] / "fixtures" / "review_comment_claims_unfixed_issue" / "review_comments.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "review_comment_claims_unfixed_issue" / "issues.json"

# A claim checked within this many hours of the review comment's own
# updated_at may simply not have caught up yet -- the same editable-text-
# surface grace window review-comment-dangling-reference's own
# _EDIT_GRACE_WINDOW_HOURS already holds, applied here to a claims-X seam
# instead of a dangling-reference one.
_EDIT_GRACE_WINDOW_HOURS = 24.0


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
class ReviewComment:
    id: int
    pull_request_number: int
    body: str
    updated_at: datetime
    url: str


@dataclass
class Issue:
    number: int
    title: str
    state: str
    url: str


def load_review_comments(path: Path | None = None) -> list[ReviewComment]:
    rows = _load_rows(path or DEFAULT_REVIEW_COMMENTS_FIXTURE)
    return [
        ReviewComment(
            id=r["id"], pull_request_number=r["pull_request_number"],
            body=r.get("body") or "",
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"])
        for r in rows
    ]


def _claimed_issue_numbers(text: str) -> list[int]:
    return [int(n) for n in CLOSING_KEYWORD_RE.findall(text)]


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    comments: list[ReviewComment], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A review comment with no body at all is never
    examined at all -- it claims nothing about a second record, so there
    is no seam to weigh, the identical "not an invite at all" exclusion
    `review-comment-dangling-reference.compute_gaps` already makes for a
    body-free review comment. A comment naming no closing-keyword claim is
    excluded, named not hidden. A claimed issue is excluded, named not
    hidden, the moment it names no real issue at all, or the issue it
    names is already closed -- everything left over (a fix-claim the
    issue tracker itself contradicts) is surfaced, aged into a confidence
    score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for c in sorted(comments, key=lambda c: c.id):
        if not c.body:
            continue

        numbers = _claimed_issue_numbers(c.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{c.id}",
                headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) names no fixes/closes/resolves issue claim",
                detail=f"'{c.body}' ({c.url}) carries no closing-keyword reference. No seam here.",
                confidence=0.0,
                evidence=[c.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a comment naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN (task 442).
        for number in dict.fromkeys(numbers):
            issue = _find_issue(number, issues)
            if issue is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-issue-not-found-{c.id}-{number}",
                    headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) claims fixing #{number}, which doesn't exist",
                    detail=f"'{c.body}' ({c.url}) claims #{number} fixed, but no such issue exists. "
                           f"No seam here (see issue-body-dangling-reference/review-comment-dangling-reference).",
                    confidence=0.0,
                    evidence=[c.url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{c.id}-{number}",
                    headline=f"Review comment #{c.id}'s claim about #{number} holds",
                    detail=f"'{c.body}' ({c.url}) claims #{number} fixed; issue #{number} "
                           f"('{issue.title}') is closed. No seam here.",
                    confidence=0.0,
                    evidence=[c.url, issue.url],
                ))
                continue

            confidence = _confidence_for(c.updated_at, now=now)
            age_hours = (now - c.updated_at).total_seconds() / 3600.0
            surfaced.append(GapCandidate(
                slug=f"review-comment-claims-unfixed-issue-{c.id}-{number}",
                headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) claims #{number} fixed, but #{number} is still open",
                detail=(
                    f"'{c.body}' ({c.url}, last updated {c.updated_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{issue.title}') fixed; the "
                    f"issue's real state is '{issue.state}'. GitHub never auto-closes on a "
                    f"review comment's own closing keyword regardless -- this claim was never "
                    f"going to resolve itself."
                ),
                confidence=confidence,
                evidence=[c.url, issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    review_comments_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListReviewCommentsInARepository`/`ListIssues` read for a connected
    account and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    comments = load_review_comments(review_comments_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(comments, issues, now=now)
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
