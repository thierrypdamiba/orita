"""The seventy-fifth real seam recipe, and the tenth leg of the
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
own inline, per-line REVIEW comments; `RECIPES/issue-comment-dangling-
reference/` watches it inside the ordinary issue/PR timeline conversation;
`RECIPES/linear-comment-dangling-reference/` (task 645) watches it inside a
comment left on Linear. None of the nine ever read a message posted to a
Slack channel.

`RECIPES/slack-message-claims-unfixed-issue/detector.py`'s own docstring
named this seam and deliberately left it open: "If that issue does not
exist at all, it is excluded here -- that broken reference belongs to a
future Slack-side dangling-reference recipe, not this one." This is that
recipe. Same inbound surface (a message posted to a Slack channel, read via
`SearchChannelMessages`), a different claim shape: `slack-message-claims-
unfixed-issue` only ever looks at real GitHub closing-keyword phrases
(`fixes`/`closes`/`resolves #N`) and only against the issue tracker; this
recipe looks at EVERY bare `#N` reference regardless of the word in front
of it ("same root cause as #N", "blocked on #N", "the fix landed in #N")
and checks it against BOTH the issue list and the PR list -- GitHub shares
one number sequence between the two, the same "checking only one
misfires on a perfectly good reference to a merged PR" discipline every
dangling-reference sibling already holds itself to.

Reuses `seam_engine.references.referenced_numbers` verbatim -- the one
shared `#N`-extraction grammar `dangling-issue-reference` and its eight
prior dangling-reference siblings already import from the same place, so
a future tightening of the pattern (the cross-repo `owner/repo#N`
exclusion, in particular) lands in all ten detectors at once or not at
all, never an eleventh independently retyped copy.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`messages.json`,
`issues.json`, `pulls.json`), shaped like what a real
`SearchChannelMessages`/`ListIssues`/`ListPullRequests` read would return.
`ListIssues` and `ListPullRequests` already sit on `SCOPES.md`'s cleared
oath table under the `github` row. `SearchChannelMessages` is the same
scope `slack-message-claims-unfixed-issue` already asks for -- it clears
`seam_engine.recipes.validate_recipe`'s oath the same way every scope in
this engine does. See `SCOPES.md`'s own WIP note for this toolkit: the-hand
gateway holds a real, live, upstream `arcade-slack` connection today, but
exposes zero Slack-capable tools on the live gateway -- the identical
"connected upstream, not wired into the gateway" shape `SCOPES.md`'s
Gmail/Calendar and Linear WIP notes already document for two other
toolkits.

The seam: a bare `#N` reference inside a Slack channel message's own text
names a GitHub issue or PR number. If no issue or PR with that number
exists at all in either tracker, whoever posted the message has a belief
about the project that is already out of sync with GitHub's real number
space -- a typo, a reference to something deleted, or a number meant for
a different repo -- and nothing on either platform ever compares the two.
A message with no `#N` reference at all produces no candidate whatsoever,
not even an excluded one -- the identical "not an invite at all"
exclusion every dangling-reference sibling already makes for a
reference-free source. This never grades or blames whoever posted the
message -- CONTRIBUTING.md's "No grading, ever" law, same as every
recipe in this engine: the headline names the gap between two records,
not a person's error.

Confidence is age-gated by the message's own `ts`, holding `issue-comment-
dangling-reference`'s and `linear-comment-dangling-reference`'s identical
0.85/0.55 edit-grace-window bar exactly (24 hours) -- not an independently
re-reasoned number just because the toolkit is new again. A Slack message,
like an ordinary GitHub issue comment or a Linear comment and unlike an
immutable X mention, is a text surface its author can still edit at any
time, so a reference caught within the grace window may simply not have
been fixed (or corrected) yet, scoring the lower bar (0.55) rather than
the higher one (0.85) a stale, unedited reference earns.
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
DEFAULT_MESSAGES_FIXTURE = _HERE.parents[1] / "fixtures" / "slack_message_dangling_reference" / "messages.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "slack_message_dangling_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "slack_message_dangling_reference" / "pulls.json"

# A dangling reference in a Slack message touched less than this many
# hours ago is not yet scored as a confirmed gap -- it may simply not have
# been fixed yet. Same 24-hour shape as issue-comment-dangling-reference's
# and linear-comment-dangling-reference's own _EDIT_GRACE_WINDOW_HOURS,
# applied here for the identical reason: a Slack message is a text surface
# its author can still edit at any time.
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
    url: str


@dataclass
class PullRequest:
    number: int
    url: str


def load_messages(path: Path | None = None) -> list[Message]:
    rows = _load_rows(path or DEFAULT_MESSAGES_FIXTURE)
    return [
        Message(
            id=r["id"], channel=r["channel"], author=r["author"],
            text=r["text"], created_at=_parse_ts(r["ts"]), url=r["url"],
        )
        for r in rows
    ]


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], url=r["url"]) for r in rows]


def _confidence_for(created_at: datetime, *, now: datetime) -> float:
    age_hours = (now - created_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    messages: list[Message], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A message with no `#N` reference at all
    is never examined -- it claims nothing about a second record, so there
    is no seam to weigh, the identical "not an invite at all" exclusion
    `linear-comment-dangling-reference.compute_gaps` already makes for a
    reference-free comment."""
    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in messages:
        # dict.fromkeys dedupes, order-preserving: a message naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN (task 442's
        # precedent, held by every sibling in this family).
        for n in dict.fromkeys(_referenced_numbers(m.text)):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"slack-message-ref-matched-{m.id}-{n}",
                    headline=f"{m.channel}'s message {m.id} referencing #{n} matches a real issue or PR",
                    detail=f"'{m.text}' ({m.url}) references #{n}; a real issue or pull "
                           f"request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[m.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"slack-message-dangling-reference-{m.id}-{n}",
                headline=f"{m.channel}'s message {m.id} references #{n}, but no issue or PR #{n} exists here",
                detail=f"'{m.text}' ({m.url}) references #{n}; ListIssues + "
                       f"ListPullRequests found no issue or pull request with that number "
                       f"in this repo. Whoever posted this message has a belief about the "
                       f"project that is already out of sync with GitHub's real number space "
                       f"-- a typo, a reference to something deleted, or a number meant for a "
                       f"different repo.",
                confidence=_confidence_for(m.created_at, now=now),
                evidence=[m.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    messages_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `SearchChannelMessages`/`ListIssues`/`ListPullRequests` read for a
    connected Slack workspace and these three loaders are swapped for
    real calls. The detection logic does not change one line when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    messages = load_messages(messages_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(messages, issues, pulls, now=now)
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
