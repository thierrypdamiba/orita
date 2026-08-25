"""The ninety-third real seam recipe: an inbound email invokes a real
GitHub closing keyword against an issue ("fixes #N" / "closes #N" /
"resolves #N", both tenses), but the issue never actually closed.

The first recipe under RECIPES/ to name `gmail` at all. Before writing
this file, every one of the 92 existing recipes' `recipe.json`s was
grepped for its own `toolkit` field: the live set is exactly `{github,
github+x, x+github, slack+github, linear+github, github+google_calendar}`
-- zero `gmail`, despite `SCOPES.md`'s own "Gmail (v0.2)" row sitting on
the cleared oath table since ROADMAP.md #16 (`gmail_calendar.py`'s own
module docstring proposed `gmail`/`google_calendar` before either had a
live scope), and despite three other non-github/x toolkits
(`slack-message-claims-unfixed-issue`, `linear-comment-claims-unfixed-
issue`, `milestone-deadline-no-calendar-event`) each already having their
first recipe. Gmail is the one toolkit named on `SCOPES.md`'s table since
its very first row that no recipe under `RECIPES/` had ever actually
used -- a genuinely new axis, not one more cell filled in on a grid
already worked inside.

This is the Gmail-side twin of `mention-claims-unfixed-issue` (the
X-mention leg), `slack-message-claims-unfixed-issue` (the Slack-channel
leg), and `linear-comment-claims-unfixed-issue` (the Linear-comment leg)
of the `claims-unfixed-issue` family. All four check the identical
closing-keyword grammar against a claim posted somewhere the town does
not fully control -- this recipe reads an inbound email's own body, a
status-update or bug-report reply landing in a connected inbox, not a
tweet, a mention, a Slack message, or a Linear comment. Same seam shape
(an inbound claim against the issue tracker's own state), a fourth
inbound surface entirely.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim -- the
same shared grammar fifteen sibling recipes already import directly
(grepped: `commit-closes-keyword-issue-still-open`,
`commit-closes-keyword-issue-closed-not-planned`,
`commit-closes-keyword-pr-still-open`, `issue-closed-never-released`,
`issue-closed-pr-still-open`, `issue-comment-claims-unfixed-issue`,
`linear-comment-claims-unfixed-issue`, `mention-claims-unfixed-issue`,
`merged-pr-issue-still-open`, `merged-pr-pr-still-open`,
`milestone-claims-unfixed-issue`, `release-claims-unfixed-issue`,
`review-comment-claims-unfixed-issue`, `slack-message-claims-unfixed-
issue`, `tweet-claims-unfixed-issue`) -- rather than a sixteenth
independently retyped copy of the identical pattern. "closing #N"
(present participle, Iron Rule #8's own prescribed safe form) never
matches either tense here either, same as everywhere else this grammar
is used.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`emails.json`,
`issues.json`), shaped like what a real `ListEmails`/`ListIssues` read
would return. `ListIssues` is already cleared on `SCOPES.md`'s oath table
under the `github` row, used by nearly every recipe in this engine.
`ListEmails` is not new to the oath -- it has sat on `SCOPES.md`'s
"Gmail (v0.2)" row since ROADMAP.md #16 -- but this is the first recipe
to actually declare it. See `SCOPES.md`'s own WIP note for
`gmail_calendar.py`: the-hand gateway's connected Google account carries
`gmail.readonly` among its granted OAuth scopes, but exposes zero
Gmail-capable tools anywhere in its live MCP toolset today -- the
identical "connected upstream, not wired into the gateway" shape the
Slack and Linear WIP notes each carry for their own toolkit. This recipe
is fixture-only, MOCK ONLY, and never attempts a live network call.

The seam: a closing-keyword phrase inside an inbound email's own body
names an issue by number. If that issue does not exist at all, it is
excluded here -- that broken reference belongs to a future email-side
dangling-reference recipe, not this one. If it exists and is closed, the
claim was simply true -- excluded, named not hidden. If it exists and is
still open, an email already sitting in an inbox disagrees with GitHub's
own record, and nothing on either platform ever compares the two. This
never grades or blames whoever sent the email -- CONTRIBUTING.md's "No
grading, ever" law, same as every recipe in this engine: the headline
names the gap between two records, not a person's error.

Confidence is age-gated by the email's own `received_at`, holding
`mention-claims-unfixed-issue`'s/`slack-message-claims-unfixed-issue`'s/
`linear-comment-claims-unfixed-issue`'s identical 0.85/0.5 bar exactly --
not an independently re-reasoned number just because the toolkit is new.
A claim checked within 24 hours of the email landing might still be a
race (the real fix landing moments after the email went out) rather than
a settled overclaim. The check itself is objective: the claimed issue's
own live `state` field, verified against `ListIssues`, not a guess about
which tracker the sender meant -- the same reasoning every sibling in
this family already gives for holding the identical bar, no
independently re-reasoned number.
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
DEFAULT_EMAILS_FIXTURE = _HERE.parents[1] / "fixtures" / "email_claims_unfixed_issue" / "emails.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "email_claims_unfixed_issue" / "issues.json"

# A claim checked within this window of the email's own received_at may
# just be a race rather than a genuine, settled overclaim -- the identical
# bar mention-claims-unfixed-issue/slack-message-claims-unfixed-issue/
# linear-comment-claims-unfixed-issue each hold themselves to.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Email:
    id: str
    sender: str
    subject: str
    body: str
    received_at: datetime


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


def load_emails(path: Path | None = None) -> list[Email]:
    rows = _load_rows(path or DEFAULT_EMAILS_FIXTURE)
    return [
        Email(
            id=r["id"], sender=r["sender"], subject=r["subject"], body=r["body"],
            received_at=_parse_ts(r["received_at"]),
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
    emails: list[Email], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed issue is excluded, named not hidden, the
    moment it names no real issue at all, or the issue it names is already
    closed -- everything left over (a fix-claim the issue tracker itself
    contradicts) is surfaced, aged into a confidence score rank() can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for email in emails:
        numbers = _claimed_issue_numbers(email.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{email.id}",
                headline=f"Email {email.id} ('{email.subject}') names no fixes/closes/resolves issue claim",
                detail=f"'{email.body}' carries no closing-keyword reference. No seam here.",
                confidence=0.0,
                evidence=[f"gmail:{email.id}"],
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
                    slug=f"claimed-issue-not-found-{email.id}-{number}",
                    headline=f"Email {email.id} ('{email.subject}') claims fixing #{number}, which doesn't exist",
                    detail=f"'{email.body}' claims #{number} fixed, but no such issue exists. No seam here.",
                    confidence=0.0,
                    evidence=[f"gmail:{email.id}"],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{email.id}-{number}",
                    headline=f"Email {email.id}'s claim about #{number} holds",
                    detail=f"'{email.body}' claims #{number} fixed; issue #{number} ('{issue.title}') is closed. No seam here.",
                    confidence=0.0,
                    evidence=[f"gmail:{email.id}", issue.url],
                ))
                continue

            age_hours = (now - email.received_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"email-claims-unfixed-issue-{email.id}-{number}",
                headline=f"Email {email.id} ('{email.subject}') claims #{number} fixed, but #{number} is still open",
                detail=(
                    f"'{email.body}' (received {email.received_at.isoformat()} from "
                    f"{email.sender}, {age_hours:.1f}h ago) claims #{number} "
                    f"('{issue.title}') fixed; the issue's real state is '{issue.state}'."
                ),
                confidence=confidence,
                evidence=[f"gmail:{email.id}", issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    emails_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `ListEmails`/`ListIssues` read for a connected Gmail account and these
    two loaders are swapped for real calls. The detection logic does not
    change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    emails = load_emails(emails_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(emails, issues, now=now)
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
