"""The sixty-eighth real seam recipe: a Linear issue comment invokes a
real GitHub closing keyword against an issue ("fixes #N" / "closes #N" /
"resolves #N", both tenses), but the issue never actually closed.

The second recipe under RECIPES/ to read a toolkit besides `github`/`x` at
all -- `slack-message-claims-unfixed-issue` (the sixty-seventh real
recipe) was the first. Before writing this file, every one of the 67
existing recipes' `recipe.json`s was grepped for its own `toolkit` field:
the live set is exactly `{github, github+x, x+github, slack+github}` --
one non-github/x toolkit already live, zero `linear`, zero `gmail`, zero
anything else. That makes this recipe the second cell in a growing
family, not a repeat of the one exception `slack-message-claims-unfixed-
issue` opened. `CONTRIBUTING.md`'s own "New toolkits" section sanctions
this directly: *"toolkit does not have to be one already on SCOPES.md's
table... the same way gmail_calendar.py proposed gmail/google_calendar
before either had a live scope"* -- this recipe does the identical thing
for Linear, proposing `linear+github` the same way `slack-message-claims-
unfixed-issue` proposed `slack+github` before a live scope-confirm the
town has ever held for either.

This is the Linear-side twin of `mention-claims-unfixed-issue` (the
X-mention leg of the claims-unfixed-issue family) and `slack-message-
claims-unfixed-issue` (the Slack-channel-message leg). All three check the
identical closing-keyword grammar against a claim posted somewhere the
town does not fully control -- `mention-claims-unfixed-issue` reads a
stranger's own mention of the connected X account; `slack-message-claims-
unfixed-issue` reads a message posted to a Slack channel; this recipe
reads a comment left on a Linear issue. Same seam shape (an inbound claim
against the issue tracker's own state), a third inbound surface entirely
-- `readme-claims-unfixed-issue`, `release-claims-unfixed-issue`,
`milestone-claims-unfixed-issue`, and `tweet-claims-unfixed-issue` already
cover every text surface the town itself controls (its own README, its
own release notes, its own milestone bodies, its own tweets); a Linear
issue comment is neither a surface the town controls nor a surface any
prior recipe in this family has ever read.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim -- the
same shared grammar `slack-message-claims-unfixed-issue` and its thirteen
other siblings already import directly (grepped:
`commit-closes-keyword-issue-still-open`,
`commit-closes-keyword-issue-closed-not-planned`,
`commit-closes-keyword-pr-still-open`, `issue-closed-never-released`,
`issue-closed-pr-still-open`, `issue-comment-claims-unfixed-issue`,
`mention-claims-unfixed-issue`, `merged-pr-issue-still-open`,
`merged-pr-pr-still-open`, `milestone-claims-unfixed-issue`,
`release-claims-unfixed-issue`, `review-comment-claims-unfixed-issue`,
`tweet-claims-unfixed-issue`, `slack-message-claims-unfixed-issue`) --
this recipe is the fifteenth importer, not a fourteenth or sixteenth
independently retyped copy of the identical pattern. "closing #N" (present
participle, Iron Rule #8's own prescribed safe form) never matches either
tense here either, same as everywhere else this grammar is used.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`comments.json`,
`issues.json`), shaped like what a real `SearchIssueComments`/`ListIssues`
read would return. `ListIssues` is already cleared on `SCOPES.md`'s oath
table under the `github` row, used by nearly every recipe in this engine.
`SearchIssueComments` is new -- it clears `seam_engine.recipes.
validate_recipe`'s oath the same way every other scope in this engine
does: it matches the allowed `Search*` prefix and contains none of the
forbidden write words (`Create`/`Update`/`Merge`/`Delete`/`Post`/`Reply`/
`Send`/`Modify`/`Write`/`Remove`/`Label`/`Draft`/`Trash`/`Invite`/
`Revoke`/`Publish`/`Share`). See `SCOPES.md`'s own WIP note for this
recipe: the-hand gateway holds a real, live, upstream `arcade-linear`
connection today (confirmed connected, per `Arcade_ListApps`), but
exposes zero Linear-capable tools on the live gateway -- the identical
"connected upstream, not wired into the gateway" shape `SCOPES.md`'s
Gmail/Calendar and Slack WIP notes already document for two other
toolkits.

The seam: a closing-keyword phrase inside a Linear issue comment names an
issue by number. If that issue does not exist at all, it is excluded here
-- that broken reference belongs to a future Linear-side dangling-
reference recipe, not this one. If it exists and is closed, the claim was
simply true -- excluded, named not hidden. If it exists and is still
open, a comment already sitting on a Linear issue disagrees with GitHub's
own record, and nothing on either platform ever compares the two. This
never grades or blames whoever left the comment -- CONTRIBUTING.md's "No
grading, ever" law, same as every recipe in this engine: the headline
names the gap between two records, not a person's error.

Confidence is age-gated by the comment's own `created_at`, holding
`mention-claims-unfixed-issue`'s/`slack-message-claims-unfixed-issue`'s
identical 0.85/0.5 bar exactly -- not an independently re-reasoned number
just because the toolkit is new again. A claim checked within 24 hours of
posting might still be a race (the real fix landing moments after the
comment went out) rather than a settled overclaim. The check itself is
objective: the claimed issue's own live `state` field, verified against
`ListIssues`, not a guess about which tracker the commenter meant -- the
same reasoning `slack-message-claims-unfixed-issue`'s own docstring
already gives for holding `mention-claims-unfixed-issue`'s/`tweet-claims-
unfixed-issue`'s bar exactly, no independently re-reasoned number.
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
DEFAULT_COMMENTS_FIXTURE = _HERE.parents[1] / "fixtures" / "linear_comment_claims_unfixed_issue" / "comments.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "linear_comment_claims_unfixed_issue" / "issues.json"

# A claim checked within this window of the comment's own created_at may
# just be a race rather than a genuine, settled public overclaim -- the
# identical bar mention-claims-unfixed-issue/slack-message-claims-unfixed-
# issue hold themselves to.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Comment:
    id: str
    issue_identifier: str
    author: str
    text: str
    created_at: datetime
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


def load_comments(path: Path | None = None) -> list[Comment]:
    rows = _load_rows(path or DEFAULT_COMMENTS_FIXTURE)
    return [
        Comment(
            id=r["id"], issue_identifier=r["issue_identifier"], author=r["author"],
            text=r["text"], created_at=_parse_ts(r["ts"]), url=r["url"],
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


def compute_gaps(
    comments: list[Comment], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed issue is excluded, named not hidden, the
    moment it names no real issue at all, or the issue it names is already
    closed -- everything left over (a fix-claim the issue tracker itself
    contradicts) is surfaced, aged into a confidence score rank() can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for comment in comments:
        numbers = _claimed_issue_numbers(comment.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{comment.id}",
                headline=f"{comment.issue_identifier}'s comment {comment.id} names no fixes/closes/resolves issue claim",
                detail=f"'{comment.text}' carries no closing-keyword reference. No seam here.",
                confidence=0.0,
                evidence=[comment.url],
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
                    slug=f"claimed-issue-not-found-{comment.id}-{number}",
                    headline=f"{comment.issue_identifier}'s comment {comment.id} claims fixing #{number}, which doesn't exist",
                    detail=f"'{comment.text}' claims #{number} fixed, but no such issue exists. No seam here.",
                    confidence=0.0,
                    evidence=[comment.url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{comment.id}-{number}",
                    headline=f"{comment.issue_identifier}'s comment {comment.id}'s claim about #{number} holds",
                    detail=f"'{comment.text}' claims #{number} fixed; issue #{number} ('{issue.title}') is closed. No seam here.",
                    confidence=0.0,
                    evidence=[comment.url, issue.url],
                ))
                continue

            age_hours = (now - comment.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"linear-comment-claims-unfixed-issue-{comment.id}-{number}",
                headline=f"{comment.issue_identifier}'s comment {comment.id} claims #{number} fixed, but #{number} is still open",
                detail=(
                    f"'{comment.text}' (posted {comment.created_at.isoformat()} on "
                    f"{comment.issue_identifier}, {age_hours:.1f}h ago) claims #{number} "
                    f"('{issue.title}') fixed; the issue's real state is '{issue.state}'."
                ),
                confidence=confidence,
                evidence=[comment.url, issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    comments_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `SearchIssueComments`/`ListIssues` read for a connected Linear
    workspace and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    comments = load_comments(comments_path)
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
