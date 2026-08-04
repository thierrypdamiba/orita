"""The forty-fourth real seam recipe, and a seventh leg of the
dangling-reference family -- a family that has now called itself
"final" twice and been wrong both times. `RECIPES/milestone-body-
dangling-reference/` (task 522) named itself "the fifth and final leg";
`RECIPES/own-tweet-dangling-reference/` (task 527) superseded that as
"the sixth and final leg" one hour later. This recipe does not repeat
the word. GitHub simply has more editable text surfaces that invite the
same "#N in ordinary prose" mistake than any one docstring has ever
correctly enumerated in one sitting.

`RECIPES/dangling-issue-reference/` (task 368) watches this seam inside
a commit message; `RECIPES/mention-dangling-reference/` (task 388)
watches it inside a mortal's X mention; `RECIPES/release-note-dangling-
reference/` (task 401) watches it inside a release body;
`RECIPES/issue-body-dangling-reference/` (task 504) watches it inside an
issue or pull request's own body; `RECIPES/milestone-body-dangling-
reference/` (task 522) watches it inside a milestone's own description;
`RECIPES/own-tweet-dangling-reference/` (task 527) watches it inside the
connected X account's own outbound tweets. None of the six ever read a
pull request's own REVIEW comments -- the inline, per-line code-review
thread a real `ListReviewCommentsInARepository` call returns, a
genuinely different GitHub object from the PR body `issue-body-
dangling-reference` already covers. A reviewer routinely writes "same
root cause as #501", "isn't this the same bug as #N", "blocked on #N"
directly into a review thread, and GitHub renders every `#N` there as a
clickable link with zero validation that it resolves to anything.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files
(`review_comments.json`, `issues.json`, `pulls.json`), shaped like what
`ListReviewCommentsInARepository`, `ListIssues`, and `ListPullRequests`
would actually return. `ListIssues` and `ListPullRequests` already sit
on `SCOPES.md`'s cleared oath table; `ListReviewCommentsInARepository`
is a real, currently-live, read-only tool on the-hand gateway, added to
the table by this same task -- no WIP-scope asterisk needed, unlike
Gmail/Calendar.

The seam: `#N` inside a review comment's own body is checked against
BOTH the issue list and the PR list, the same "one shared number
sequence" discipline every sibling in this family already established --
checking only one would misfire on a perfectly good reference to a
merged PR sitting inside a review thread. A cross-repo `owner/repo#N`
reference is never even extracted as a candidate -- that names a
different repo's own number space on purpose. This recipe imports
`seam_engine.references.referenced_numbers` rather than writing a
seventh copy of the same extraction regex -- the identical "one law, not
a seventh copy of it" discipline this whole family already pays for.

Confidence mirrors `issue-body-dangling-reference` and `milestone-body-
dangling-reference`, for the same reason: a review comment, like an
issue/PR body or a milestone description, is a text surface its author
can edit at any time -- unlike a permanent commit, someone else's tweet,
or a published release note, there is a real "may simply not have
caught up yet" grace period that means something here. A dangling
reference inside a comment touched less than 24h ago scores 0.55 (still
might get fixed any minute); one that has sat, uncorrected, for at least
24h since the comment's own `updated_at` scores 0.85 (nobody is coming
back to fix it). A review comment with no body at all (`null` or empty)
is excluded outright -- there is no claim to have broken.
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
DEFAULT_REVIEW_COMMENTS_FIXTURE = _HERE.parents[1] / "fixtures" / "review_comment_dangling_reference" / "review_comments.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "review_comment_dangling_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "review_comment_dangling_reference" / "pulls.json"

# A dangling reference in a review comment touched less than this many
# hours ago is not yet scored as a confirmed gap -- it may simply not
# have been fixed yet. Same 24-hour shape as issue-body-dangling-
# reference's and milestone-body-dangling-reference's own
# _EDIT_GRACE_WINDOW_HOURS, applied here for the identical reason: a
# review comment is a text surface its author can still edit at any time.
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
    url: str


@dataclass
class PullRequest:
    number: int
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
    return [Issue(number=r["number"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], url=r["url"]) for r in rows]


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    comments: list[ReviewComment], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A review comment with no body at all
    is never examined -- it claims nothing about a second record, so
    there is no seam to weigh, the identical "not an invite at all"
    exclusion `dangling-issue-reference.compute_gaps` already makes for a
    reference-free commit."""
    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for c in sorted(comments, key=lambda c: c.id):
        if not c.body:
            continue

        # dict.fromkeys dedupes, order-preserving: a comment naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN (task 442).
        for n in dict.fromkeys(_referenced_numbers(c.body)):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"review-comment-ref-matched-{c.id}-{n}",
                    headline=f"Review comment #{c.id}'s reference to #{n} matches a real issue or PR",
                    detail=f"'{c.body}' ({c.url}) references #{n}; a real issue or pull "
                           f"request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[c.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"review-comment-dangling-reference-{c.id}-{n}",
                headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) references #{n}, "
                         f"but no issue or PR #{n} exists here",
                detail=f"'{c.body}' ({c.url}) references #{n}; ListReviewCommentsInARepository + "
                       f"ListIssues + ListPullRequests found no issue or pull request with that "
                       f"number in this repo. Likely a typo, a reference to something deleted, or a "
                       f"number meant for a different repo, sitting in a review thread anyone can "
                       f"still edit but nobody has.",
                confidence=_confidence_for(c.updated_at, now=now),
                evidence=[c.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    review_comments_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the Hand's gateway carries a
    live `ListReviewCommentsInARepository`/`ListIssues`/`ListPullRequests`
    read for a connected account and these three loaders are swapped for
    real reads. The detection logic does not change one line when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    comments = load_review_comments(review_comments_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(comments, issues, pulls, now=now)
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
