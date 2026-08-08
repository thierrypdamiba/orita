"""The seventy-second real seam recipe: a message posted to a Slack channel
claims a pull request shipped ("ships/includes/merges/via #N"), but the
named PR is not actually merged.

The Slack source's third and final `claims-X` leg, alongside
`slack-message-claims-unfixed-issue` (task 599, the sixty-seventh real
recipe, the closing-keyword leg against the issue tracker) and
`slack-message-claims-open-milestone` (task 601, the sixty-ninth real
recipe, the milestone-claim leg against the milestone tracker). That
second recipe's own docstring named this exact boundary before anyone
built it -- "a third leg, `slack-message-claims-unmerged-pr`, remains
open for a future hour." This recipe is that future hour, built -- and
the Slack-side twin of `linear-comment-claims-unmerged-pr` (task 603, the
seventy-first real recipe), which closed the identical PR-claim leg for
the Linear issue-comment surface and named this exact recipe as the
claims-X grid's one remaining genuinely open cell. With this recipe
shipped, the claims-X grid (ten sources -- mention, tweet, issue-comment,
review-comment, milestone, readme, release, commit, slack-message,
linear-comment -- times three targets -- open-milestone, unfixed-issue,
unmerged-pr) has zero genuinely open cells left. `commit-claims-unfixed-
issue` and `commit-claims-unmerged-pr` remain the two structurally-
unfillable cells task 599's own history already named --
`commit-closes-keyword-issue-still-open` and `commit-closes-keyword-pr-
still-open` already cover that identical semantic space under a
different recipe name, so filling those two cells a second time under
the `claims-X` name would be the same fact asserted twice, not a new one.

Same seam shape as every PR-claim sibling (an inbound "shipped it" claim
against the PR tracker's own state), a different inbound surface entirely
-- `mention-claims-unmerged-pr`, `tweet-claims-unmerged-pr`, `review-
comment-claims-unmerged-pr`, `milestone-claims-unmerged-pr`, `release-
claims-unmerged-pr`, and `linear-comment-claims-unmerged-pr` already
cover every other surface this family reads. Reuses `seam_engine.
pr_claims.claimed_pr_numbers` verbatim -- the same shared "ships/
includes/merges/via #N" grammar every one of those siblings already
imports from there -- rather than an eighth independently retyped copy
of the identical pattern.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`messages.json`,
`pulls.json`), shaped like what a real `SearchChannelMessages`/
`ListPullRequests` read would return. `ListPullRequests` is already
cleared on `SCOPES.md`'s oath table under the `github` row, used by
nearly every recipe in this engine that reads the PR tracker.
`SearchChannelMessages` is the same scope `slack-message-claims-unfixed-
issue` (task 599) and `slack-message-claims-open-milestone` (task 601)
already cleared through `seam_engine.recipes.validate_recipe`'s oath --
this recipe asks for nothing new, and `slack+github` is not a new
toolkit pair either -- both of this recipe's own Slack siblings already
proposed it. See `SCOPES.md`'s own WIP note for the `slack` toolkit: the
-hand gateway holds a real, live, upstream `arcade-slack` connection
today, but exposes zero Slack-capable tools on the live gateway -- the
identical "connected upstream, not wired into the gateway" shape
`SCOPES.md`'s Gmail/Calendar and Linear WIP notes already document for
two other toolkits.

The seam: a `ships #N`/`includes #N`/`merges #N`/`via #N` claim phrase
inside a Slack channel message names a pull request by number. If that
PR does not exist at all, it is excluded here -- that broken reference
belongs to a future Slack-side dangling-reference recipe, not this one.
If it exists and is merged, the claim was simply true -- excluded, named
not hidden. If it exists and is NOT merged (still open, or closed
without merging), a message already sitting in a Slack channel disagrees
with GitHub's own record, and nothing on either platform ever compares
the two -- GitHub never auto-merges anything off a Slack message's own
text regardless of what it says. This never grades or blames whoever
posted the message -- CONTRIBUTING.md's "No grading, ever" law, same as
every recipe in this engine: the headline names the gap between two
records, not a person's error.

Confidence is age-gated by the message's own `ts`, holding `slack-
message-claims-open-milestone`'s/`linear-comment-claims-unmerged-pr`'s
own 0.85/0.5 bar exactly -- NOT `review-comment-claims-unmerged-pr`'s
0.55/0.85 editable-surface bar. A Slack channel message, like a Linear
issue comment, a tweet, or a mention, is posted once and stands; unlike
a GitHub review comment, it is not a surface its own author can quietly
edit out from under the claim, so the "may simply not have caught up
yet" grace window that justifies review-comment-claims-unmerged-pr's
higher floor does not apply here -- the identical "posted once and
stands" reasoning `slack-message-claims-open-milestone`'s own docstring
already gives for holding `mention-claims-unmerged-pr`'s bar exactly
rather than re-deriving one of its own. A claim checked within 24 hours
of posting might still be a race (the PR actually merging moments after
the message went out) rather than a settled overclaim (0.5, below the
confidence bar, shown as a weighed coincidence, not hidden). At or past
24 hours with the named PR still unmerged, it is unambiguous (flat
0.85). The check itself is objective: the claimed PR's own live
`merged`/`state` fields, verified against `ListPullRequests`, not a
guess about which tracker the poster meant.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.pr_claims import claimed_pr_numbers as _claimed_pr_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "slack_message_claims_unmerged_pr"
DEFAULT_MESSAGES_FIXTURE = _FIXTURE_DIR / "messages.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# A claim checked within this window of the message's own ts may just be a
# race rather than a genuine, settled public overclaim -- the identical bar
# slack-message-claims-open-milestone/linear-comment-claims-unmerged-pr
# hold themselves to.
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
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    url: str


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows`
    holds."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_messages(path: Path | None = None) -> list[Message]:
    rows = _load_rows(path or DEFAULT_MESSAGES_FIXTURE)
    return [
        Message(
            id=r["id"], channel=r["channel"], author=r["author"],
            text=r["text"], created_at=_parse_ts(r["ts"]), url=r["url"],
        )
        for r in rows
    ]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(number=r["number"], title=r["title"], state=r["state"], merged=r["merged"], url=r["url"])
        for r in rows
    ]


def _find_pull(number: int, pulls: list[PullRequest]) -> PullRequest | None:
    for pr in pulls:
        if pr.number == number:
            return pr
    return None


def compute_gaps(
    messages: list[Message], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed PR is excluded, named not hidden, the
    moment it names no real PR at all, or the PR it names is already
    merged -- everything left over (a shipped-it claim the PR tracker
    itself contradicts) is surfaced, aged into a confidence score rank()
    can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for message in messages:
        numbers = _claimed_pr_numbers(message.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{message.id}",
                headline=f"{message.channel}'s message {message.id} names no ships/includes/merges/via PR claim",
                detail=f"'{message.text}' carries no claim-phrase reference. No seam here.",
                confidence=0.0,
                evidence=[message.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a message naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN, the same
        # dedup discipline linear-comment-claims-unmerged-pr's own
        # compute_gaps already holds (task 603).
        for number in dict.fromkeys(numbers):
            pr = _find_pull(number, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{message.id}-{number}",
                    headline=f"{message.channel}'s message {message.id} claims #{number} shipped, which doesn't exist",
                    detail=f"'{message.text}' claims #{number} shipped, but no such PR exists. No seam here.",
                    confidence=0.0,
                    evidence=[message.url],
                ))
                continue

            if pr.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-{message.id}-{number}",
                    headline=f"{message.channel}'s message {message.id}'s claim about #{number} holds",
                    detail=f"'{message.text}' claims #{number} ('{pr.title}') shipped; PR #{number} is merged. No seam here.",
                    confidence=0.0,
                    evidence=[message.url, pr.url],
                ))
                continue

            age_hours = (now - message.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"slack-message-claims-unmerged-pr-{message.id}-{number}",
                headline=f"{message.channel}'s message {message.id} claims #{number} shipped, but #{number} never merged",
                detail=(
                    f"'{message.text}' (posted {message.created_at.isoformat()} in "
                    f"{message.channel}, {age_hours:.1f}h ago) claims #{number} "
                    f"('{pr.title}') shipped; the PR's real state is '{pr.state}', "
                    f"merged={pr.merged}."
                ),
                confidence=confidence,
                evidence=[message.url, pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    messages_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `SearchChannelMessages`/`ListPullRequests` read for a connected Slack
    workspace and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    messages = load_messages(messages_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(messages, pulls, now=now)
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
