"""The sixty-ninth real seam recipe: a Slack channel message claims a
milestone shipped ("milestone #N"), but the named milestone is not
actually closed.

The Slack source's second `claims-X` leg, alongside
`slack-message-claims-unfixed-issue` (task 599, the sixty-seventh real
recipe). That recipe proved the first Slack-side claim leg -- a channel
message's closing-keyword claim against the issue tracker's own state --
and left the milestone-claim leg open. `mention-claims-open-milestone`
(the forty-eighth) already proved the identical milestone-claim shape for
X's own mention surface; this recipe is that same check applied to the
Slack channel-message surface `slack-message-claims-unfixed-issue` opened,
not a new pattern independently invented for the occasion. A third leg,
`slack-message-claims-unmerged-pr`, remains open for a future hour -- this
recipe closes one cell of that grid, not all three.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim
-- the same shared "milestone #N" grammar `milestone-closed-never-
released`, `release-claims-open-milestone`, `milestone-closed-not-
tweeted`, `tweet-claims-open-milestone`, and `mention-claims-open-
milestone` already import from there (task 389 centralized what had been
independently retyped copies) -- rather than a sixth copy of the
identical pattern drifting apart from the rest.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`messages.json`,
`milestones.json`), shaped like what a real `SearchChannelMessages`/
`ListMilestones` read would return. `ListMilestones` is already cleared
on `SCOPES.md`'s oath table under the `github` row, used by every
milestone-claim recipe already in this engine. `SearchChannelMessages`
was the new scope `slack-message-claims-unfixed-issue` cleared through
`seam_engine.recipes.validate_recipe`'s oath (it matches the allowed
`Search*` prefix and contains none of the forbidden write words); this
recipe asks for nothing new. See `SCOPES.md`'s own WIP note for the
`slack` toolkit: the-hand gateway holds a real, live, upstream
`arcade-slack` connection today, but exposes zero Slack-capable tools on
the live gateway -- the identical "connected upstream, not wired into the
gateway" shape `SCOPES.md`'s Gmail/Calendar WIP note already documents
for a different toolkit.

The seam: a `milestone #N` claim phrase inside a Slack channel message
names a milestone by number. If that milestone does not exist at all, it
is excluded here -- that broken reference belongs to a future Slack-side
dangling-reference recipe, not this one. If it exists and is closed, the
claim was simply true -- excluded, named not hidden. If it exists and is
still open, a message already sitting in a Slack channel disagrees with
GitHub's own record, and nothing on either platform ever compares the
two. This never grades or blames whoever posted the message --
CONTRIBUTING.md's "No grading, ever" law, same as every recipe in this
engine: the headline names the gap between two records, not a person's
error.

Confidence is age-gated by the message's own `ts`, holding
`slack-message-claims-unfixed-issue`'s own 0.85/0.5 bar exactly -- a
message posted to a channel is exactly as durable and readable-later as a
tweet or a mention once posted, "posted once and stands", not an editable
review comment (`review-comment-claims-open-milestone`'s own 0.55/0.85
bar does not apply here, and this recipe deliberately does not re-derive
it). A claim checked within 24 hours of posting might still be a race
(the milestone actually closing out moments after the message went out)
rather than a settled overclaim. The check itself is objective: the
claimed milestone's own live `state` field, verified against
`ListMilestones`, not a guess about which tracker the poster meant --
the same reasoning `mention-claims-open-milestone`'s own docstring
already gives for holding `tweet-claims-open-milestone`'s bar exactly, no
independently re-reasoned number.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.milestone_claims import claimed_milestone_numbers as _claimed_milestone_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "slack_message_claims_open_milestone"
DEFAULT_MESSAGES_FIXTURE = _FIXTURE_DIR / "messages.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A claim checked within this window of the message's own ts may just be a
# race rather than a genuine, settled public overclaim -- the identical bar
# slack-message-claims-unfixed-issue/mention-claims-open-milestone hold
# themselves to.
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
class Milestone:
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


def load_milestones(path: Path | None = None) -> list[Milestone]:
    rows = _load_rows(path or DEFAULT_MILESTONES_FIXTURE)
    return [
        Milestone(number=r["number"], title=r["title"], state=r["state"], url=r["url"])
        for r in rows
    ]


def _find_milestone(number: int, milestones: list[Milestone]) -> Milestone | None:
    for milestone in milestones:
        if milestone.number == number:
            return milestone
    return None


def compute_gaps(
    messages: list[Message], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed milestone is excluded, named not hidden,
    the moment it names no real milestone at all, or the milestone it
    names is already closed -- everything left over (a shipped-it claim
    the milestone tracker itself contradicts) is surfaced, aged into a
    confidence score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for message in messages:
        numbers = _claimed_milestone_numbers(message.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{message.id}",
                headline=f"{message.channel}'s message {message.id} names no milestone claim",
                detail=f"'{message.text}' carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[message.url],
            ))
            continue

        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)

            milestone = _find_milestone(number, milestones)
            if milestone is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-not-found-{message.id}-{number}",
                    headline=f"{message.channel}'s message {message.id} claims milestone #{number}, which doesn't exist",
                    detail=f"'{message.text}' claims milestone #{number} shipped, but no such milestone exists. No seam here.",
                    confidence=0.0,
                    evidence=[message.url],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{message.id}-{number}",
                    headline=f"{message.channel}'s message {message.id}'s claim about milestone #{number} holds",
                    detail=f"'{message.text}' claims milestone #{number} ('{milestone.title}') shipped; the milestone is closed. No seam here.",
                    confidence=0.0,
                    evidence=[message.url, milestone.url],
                ))
                continue

            age_hours = (now - message.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"slack-message-claims-open-milestone-{message.id}-{number}",
                headline=f"{message.channel}'s message {message.id} claims milestone #{number} shipped, but it's still open",
                detail=(
                    f"'{message.text}' (posted {message.created_at.isoformat()} in "
                    f"{message.channel}, {age_hours:.1f}h ago) claims milestone #{number} "
                    f"('{milestone.title}') shipped; the milestone's real state is "
                    f"'{milestone.state}'."
                ),
                confidence=confidence,
                evidence=[message.url, milestone.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    messages_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `SearchChannelMessages`/`ListMilestones` read for a connected Slack
    workspace and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    messages = load_messages(messages_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(messages, milestones, now=now)
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
