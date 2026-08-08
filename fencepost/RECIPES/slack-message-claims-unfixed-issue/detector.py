"""The sixty-seventh real seam recipe: a Slack channel message invokes a
real GitHub closing keyword against an issue ("fixes #N" / "closes #N" /
"resolves #N", both tenses), but the issue never actually closed.

The first recipe under RECIPES/ to read a toolkit besides `github`/`x` at
all. Before writing this file, every one of the 66 existing recipes'
`recipe.json`s was grepped for its own `toolkit` field: the live set is
exactly `{github, github+x, x+github}` -- zero `slack`, zero `gmail`, zero
anything else. That makes this recipe a genuinely new axis, not one more
cell filled in on the GitHub/X grid every prior recipe already worked
inside of. `CONTRIBUTING.md`'s own "New toolkits" section sanctions this
directly: *"toolkit does not have to be one already on SCOPES.md's table...
the same way gmail_calendar.py proposed gmail/google_calendar before either
had a live scope"* -- this recipe does the identical thing for Slack,
proposing `slack+github` rather than waiting for a live scope-confirm the
town has never held.

This is the Slack-side twin of `mention-claims-unfixed-issue` (the
X-mention leg of the claims-unfixed-issue family). Both check the
identical closing-keyword grammar against a claim posted somewhere the
town does not fully control -- `mention-claims-unfixed-issue` reads a
stranger's own mention of the connected X account; this recipe reads a
message posted to a Slack channel. Same seam shape (an inbound claim
against the issue tracker's own state), a different inbound surface
entirely -- `readme-claims-unfixed-issue`, `release-claims-unfixed-issue`,
`milestone-claims-unfixed-issue`, and `tweet-claims-unfixed-issue` already
cover every text surface the town itself controls (its own README, its
own release notes, its own milestone bodies, its own tweets); a Slack
channel is neither a surface the town controls nor a surface any prior
recipe in this family has ever read.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim -- the
same shared grammar thirteen sibling recipes already import directly
(grepped: `commit-closes-keyword-issue-still-open`,
`commit-closes-keyword-issue-closed-not-planned`,
`commit-closes-keyword-pr-still-open`, `issue-closed-never-released`,
`issue-closed-pr-still-open`, `issue-comment-claims-unfixed-issue`,
`mention-claims-unfixed-issue`, `merged-pr-issue-still-open`,
`merged-pr-pr-still-open`, `milestone-claims-unfixed-issue`,
`release-claims-unfixed-issue`, `review-comment-claims-unfixed-issue`,
`tweet-claims-unfixed-issue`) -- rather than a fourteenth independently
retyped copy of the identical pattern. "closing #N" (present participle,
Iron Rule #8's own prescribed safe form) never matches either tense here
either, same as everywhere else this grammar is used.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`messages.json`,
`issues.json`), shaped like what a real `SearchChannelMessages`/
`ListIssues` read would return. `ListIssues` is already cleared on
`SCOPES.md`'s oath table under the `github` row, used by nearly every
recipe in this engine. `SearchChannelMessages` is new -- it clears
`seam_engine.recipes.validate_recipe`'s oath the same way every other
scope in this engine does: it matches the allowed `Search*` prefix and
contains none of the forbidden write words (`Create`/`Update`/`Merge`/
`Delete`/`Post`/`Reply`/`Send`/`Modify`/`Write`/`Remove`/`Label`/`Draft`/
`Trash`/`Invite`/`Revoke`/`Publish`/`Share`). See `SCOPES.md`'s own WIP
note for this recipe: the-hand gateway holds a real, live, upstream
`arcade-slack` connection today, but exposes zero Slack-capable tools on
the live gateway -- the identical "connected upstream, not wired into the
gateway" shape `SCOPES.md`'s Gmail/Calendar WIP note already documents for
a different toolkit.

The seam: a closing-keyword phrase inside a Slack channel message names an
issue by number. If that issue does not exist at all, it is excluded here
-- that broken reference belongs to a future Slack-side dangling-reference
recipe, not this one. If it exists and is closed, the claim was simply
true -- excluded, named not hidden. If it exists and is still open, a
message already sitting in a Slack channel disagrees with GitHub's own
record, and nothing on either platform ever compares the two. This never
grades or blames whoever posted the message -- CONTRIBUTING.md's "No
grading, ever" law, same as every recipe in this engine: the headline
names the gap between two records, not a person's error.

Confidence is age-gated by the message's own `ts`, holding
`mention-claims-unfixed-issue`'s/`tweet-claims-unfixed-issue`'s identical
0.85/0.5 bar exactly -- not an independently re-reasoned number just
because the toolkit is new. A claim checked within 24 hours of posting
might still be a race (the real fix landing moments after the message went
out) rather than a settled overclaim. The check itself is objective: the
claimed issue's own live `state` field, verified against `ListIssues`, not
a guess about which tracker the poster meant -- the same reasoning
`mention-claims-unfixed-issue`'s own docstring already gives for holding
`tweet-claims-unfixed-issue`'s bar exactly, no independently re-reasoned
number.
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
DEFAULT_MESSAGES_FIXTURE = _HERE.parents[1] / "fixtures" / "slack_message_claims_unfixed_issue" / "messages.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "slack_message_claims_unfixed_issue" / "issues.json"

# A claim checked within this window of the message's own ts may just be a
# race rather than a genuine, settled public overclaim -- the identical bar
# mention-claims-unfixed-issue/tweet-claims-unfixed-issue hold themselves to.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Message:
    id: str
    channel: str
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


def load_messages(path: Path | None = None) -> list[Message]:
    rows = _load_rows(path or DEFAULT_MESSAGES_FIXTURE)
    return [
        Message(
            id=r["id"], channel=r["channel"], author=r["author"], text=r["text"],
            created_at=_parse_ts(r["ts"]), url=r["url"],
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
    messages: list[Message], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed issue is excluded, named not hidden, the
    moment it names no real issue at all, or the issue it names is already
    closed -- everything left over (a fix-claim the issue tracker itself
    contradicts) is surfaced, aged into a confidence score rank() can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for message in messages:
        numbers = _claimed_issue_numbers(message.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{message.id}",
                headline=f"{message.channel}'s message {message.id} names no fixes/closes/resolves issue claim",
                detail=f"'{message.text}' carries no closing-keyword reference. No seam here.",
                confidence=0.0,
                evidence=[message.url],
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
                    slug=f"claimed-issue-not-found-{message.id}-{number}",
                    headline=f"{message.channel}'s message {message.id} claims fixing #{number}, which doesn't exist",
                    detail=f"'{message.text}' claims #{number} fixed, but no such issue exists. No seam here.",
                    confidence=0.0,
                    evidence=[message.url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{message.id}-{number}",
                    headline=f"{message.channel}'s message {message.id}'s claim about #{number} holds",
                    detail=f"'{message.text}' claims #{number} fixed; issue #{number} ('{issue.title}') is closed. No seam here.",
                    confidence=0.0,
                    evidence=[message.url, issue.url],
                ))
                continue

            age_hours = (now - message.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"slack-message-claims-unfixed-issue-{message.id}-{number}",
                headline=f"{message.channel}'s message {message.id} claims #{number} fixed, but #{number} is still open",
                detail=(
                    f"'{message.text}' (posted {message.created_at.isoformat()} in "
                    f"{message.channel}, {age_hours:.1f}h ago) claims #{number} "
                    f"('{issue.title}') fixed; the issue's real state is '{issue.state}'."
                ),
                confidence=confidence,
                evidence=[message.url, issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    messages_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `SearchChannelMessages`/`ListIssues` read for a connected Slack
    workspace and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    messages = load_messages(messages_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(messages, issues, now=now)
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
