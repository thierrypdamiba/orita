"""The fifty-third real seam recipe, and an eighth leg of the
dangling-reference family. `RECIPES/dangling-issue-reference/` (task 368)
watches this seam inside a commit message; `RECIPES/mention-dangling-
reference/` (task 388) watches it inside a mortal's X mention;
`RECIPES/release-note-dangling-reference/` (task 401) watches it inside a
release body; `RECIPES/issue-body-dangling-reference/` (task 504) watches
it inside an issue or pull request's own OPENING body; `RECIPES/milestone-
body-dangling-reference/` (task 522) watches it inside a milestone's own
description; `RECIPES/own-tweet-dangling-reference/` (task 527) watches it
inside the connected X account's own outbound tweets; `RECIPES/review-
comment-dangling-reference/` (task 534) watches it inside a pull request's
own inline, per-line REVIEW comments. None of the seven ever read the
ordinary TIMELINE conversation -- the comments a human or a bot leaves on
an issue or pull request's own discussion thread, not anchored to any
diff line, returned by GitHub's own issue-comments endpoint (shared
between issues and PRs, since a pull request is a special issue under the
hood -- this is why `issue_number` below can name either). "same root
cause as #501", "blocked on #N", "duplicate of #N" get typed into that
ordinary thread constantly, on both issues and PRs, and GitHub renders
every `#N` there as a clickable link with zero validation that it
resolves to anything.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files
(`issue_comments.json`, `issues.json`, `pulls.json`), shaped like what a
live issue-comments read plus `ListIssues`/`ListPullRequests` would
actually return. `ListIssues` and `ListPullRequests` already sit on
`SCOPES.md`'s cleared oath table -- but unlike `review-comment-dangling-
reference`'s `ListReviewCommentsInARepository`, no live, read-only
ordinary-issue-comments tool is exposed anywhere on the-hand gateway
today (checked live this hour: the gateway's GitHub toolset carries
`ListReviewCommentsInARepository` for inline review threads, but nothing
shaped like it for the plain timeline). `SCOPES.md` carries this recipe's
own WIP note for that reason, the same honest "detection logic is real,
the live read waits on the Hand's gateway" shape `gmail_calendar.py`
already carries for a different toolkit entirely.

The seam: `#N` inside a comment's own body is checked against BOTH the
issue list and the PR list, the same "one shared number sequence"
discipline every sibling in this family already established -- checking
only one would misfire on a perfectly good reference to a merged PR
sitting inside an issue's own comment thread. A cross-repo `owner/repo#N`
reference is never even extracted as a candidate -- that names a
different repo's own number space on purpose. This recipe imports
`seam_engine.references.referenced_numbers` rather than writing an
eighth copy of the same extraction regex -- the identical "one law, not
an eighth copy of it" discipline this whole family already pays for.

Confidence mirrors `review-comment-dangling-reference`, `issue-body-
dangling-reference`, and `milestone-body-dangling-reference`, for the
same reason: an ordinary comment, like a review comment, a body, or a
description, is a text surface its author can edit at any time -- unlike
a permanent commit, someone else's tweet, or a published release note,
there is a real "may simply not have caught up yet" grace period that
means something here. A dangling reference inside a comment touched less
than 24h ago scores 0.55 (still might get fixed any minute); one that has
sat, uncorrected, for at least 24h since the comment's own `updated_at`
scores 0.85 (nobody is coming back to fix it). A comment with no body at
all (`null` or empty) is excluded outright -- there is no claim to have
broken.
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
DEFAULT_ISSUE_COMMENTS_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_comment_dangling_reference" / "issue_comments.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_comment_dangling_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_comment_dangling_reference" / "pulls.json"

# A dangling reference in an issue/PR comment touched less than this many
# hours ago is not yet scored as a confirmed gap -- it may simply not
# have been fixed yet. Same 24-hour shape as review-comment-dangling-
# reference's own _EDIT_GRACE_WINDOW_HOURS, applied here for the
# identical reason: an ordinary comment is a text surface its author can
# still edit at any time.
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
class IssueComment:
    id: int
    issue_number: int
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


def load_issue_comments(path: Path | None = None) -> list[IssueComment]:
    rows = _load_rows(path or DEFAULT_ISSUE_COMMENTS_FIXTURE)
    return [
        IssueComment(
            id=r["id"], issue_number=r["issue_number"],
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
    comments: list[IssueComment], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A comment with no body at all is
    never examined -- it claims nothing about a second record, so there
    is no seam to weigh, the identical "not an invite at all" exclusion
    `dangling-issue-reference.compute_gaps` already makes for a
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
                    slug=f"issue-comment-ref-matched-{c.id}-{n}",
                    headline=f"Issue/PR comment #{c.id}'s reference to #{n} matches a real issue or PR",
                    detail=f"'{c.body}' ({c.url}) references #{n}; a real issue or pull "
                           f"request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[c.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"issue-comment-dangling-reference-{c.id}-{n}",
                headline=f"Comment #{c.id} (on #{c.issue_number}'s own thread) references #{n}, "
                         f"but no issue or PR #{n} exists here",
                detail=f"'{c.body}' ({c.url}) references #{n}; the issue-comments read plus "
                       f"ListIssues + ListPullRequests found no issue or pull request with that "
                       f"number in this repo. Likely a typo, a reference to something deleted, or a "
                       f"number meant for a different repo, sitting in an ordinary conversation "
                       f"thread anyone can still edit but nobody has.",
                confidence=_confidence_for(c.updated_at, now=now),
                evidence=[c.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    issue_comments_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the Hand's gateway carries a
    live read-only issue-comments tool (none exists today; see `SCOPES.md`)
    and these three loaders are swapped for real reads. The detection
    logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    comments = load_issue_comments(issue_comments_path)
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
