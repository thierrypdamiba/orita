"""The eighty-third real seam recipe: a Slack channel message invokes a
real "milestone #N" claim phrase, but no milestone with that number
exists at all.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`messages.json`,
`milestones.json`), shaped like what a real `SearchChannelMessages`/
`ListMilestones` read would return. `ListMilestones` already sits on
`SCOPES.md`'s cleared oath table under the `github` row, used by every
milestone-claim recipe already in this engine. `SearchChannelMessages`
is the same scope `slack-message-claims-unfixed-issue` (task 599) and
`slack-message-claims-open-milestone` (task 601) already cleared through
`seam_engine.recipes.validate_recipe`'s oath (it matches the allowed
`Search*` prefix and contains none of the forbidden write words) -- this
recipe asks Arcade for nothing new. See `SCOPES.md`'s own WIP note for
the `slack` toolkit: the-hand gateway holds a real, live, upstream
`arcade-slack` connection today, but exposes zero Slack-capable tools on
the live gateway -- the identical "connected upstream, not wired into the
gateway" shape `SCOPES.md`'s Gmail/Calendar and Linear WIP notes already
document for two other toolkits.

`slack-message-claims-open-milestone` (task 601, the sixty-ninth real
recipe) was the first to pair a Slack channel message with
`ListMilestones`, and its own docstring drew the line precisely: a
claimed milestone number that names no real milestone at all is excluded
there, named not hidden -- "a broken reference is a future Slack-side
dangling-reference recipe's own seam, not this one's." This recipe is
that seam, on the one surface that named it -- the Slack-sourced sibling
of `commit-claims-dangling-milestone` (task 649, the seventy-sixth real
recipe), `issue-comment-claims-dangling-milestone` (task 865, the
eighty-first), and `review-comment-claims-dangling-milestone` (task 866,
the eighty-second), which closed the identical seam for a commit
message, an issue/PR timeline comment, and a pull request's own inline
review comment respectively. Deliberately reuses
`seam_engine.milestone_claims.claimed_milestone_numbers` verbatim -- the
same shared grammar all three of those recipes already import -- rather
than a tenth independently retyped copy of the identical pattern.

Not `slack-message-dangling-reference`'s seam wearing a new name: that
recipe (task 601, the seventy-fifth real recipe) watches a bare `#N`
posted to a Slack channel against BOTH the issue list and the PR list --
GitHub's shared issue/PR number sequence -- and never once opens
`ListMilestones`. A milestone lives in its own, separate number space
that issues and pull requests never touch, so a `#N` that resolves
cleanly as an issue could still be a dangling MILESTONE claim, and a
`#N` that is a real milestone could just as easily collide with a real
issue number. Confusing the two spaces would be exactly the false-
positive failure Ogun's law calls fatal -- so this recipe reads
`claimed_milestone_numbers`'s own "milestone #N" phrase grammar, never
the bare-`#N` grammar `slack-message-dangling-reference` already owns.

The claim stays narrow, the same no-grading law every sibling holds: a
message that merely mentions a bare `#N` in passing ("same root cause as
#4105") makes no milestone claim at all, and is excluded, not guessed
into either bucket -- that bare shape is `slack-message-dangling-
reference`'s own seam, not this one's. A claimed milestone number that
DOES resolve to a real milestone is excluded too, named not hidden,
regardless of whether that milestone is open or closed -- whether the
claim is TRUE is `slack-message-claims-open-milestone`'s own seam, not
this one's; this recipe only ever asks whether the name resolves to
anything at all.

Confidence is flat (0.8), not age-gated -- mirrors `commit-claims-
dangling-milestone`'s, `issue-comment-claims-dangling-milestone`'s, and
`review-comment-claims-dangling-milestone`'s own reasoning rather than
`slack-message-claims-open-milestone`'s 24-hour edit-grace bar. That bar
exists because an OPEN milestone could close at any moment, so a fresh
claim about it might just be a race the message hasn't caught up to yet;
a milestone number that does not exist right now will not spontaneously
start existing later no matter how long the message sits, so there is no
grace period that means anything here.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "slack_message_claims_dangling_milestone"
DEFAULT_MESSAGES_FIXTURE = _FIXTURE_DIR / "messages.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors
# commit-claims-dangling-milestone's/issue-comment-claims-dangling-
# milestone's/review-comment-claims-dangling-milestone's own
# _DANGLING_CONFIDENCE exactly (0.8): a nonexistent milestone number will
# not spontaneously start existing, whatever the age of the message
# naming it.
_DANGLING_CONFIDENCE = 0.8


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


def load_messages(path: Path | None = None) -> list[Message]:
    rows = _load_rows(path or DEFAULT_MESSAGES_FIXTURE)
    return [
        Message(
            id=r["id"], channel=r["channel"], author=r["author"],
            text=r.get("text") or "",
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
    own `compute_gaps`. A message with no text at all is never examined
    at all -- it claims nothing, so there is no seam to weigh. A message
    naming no 'milestone #N' claim phrase is excluded, named not hidden.
    A claimed milestone is excluded, named not hidden, the moment it
    names a real milestone (open or closed, this recipe does not care
    which) -- everything left over (a claimed milestone number with no
    real milestone behind it at all) is surfaced at a flat confidence.

    `now` is accepted, unused -- kept for interface parity with every
    other recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_
    scan` always threads one through), the identical "unused today, kept
    for the shape" choice `issue-comment-claims-dangling-milestone/
    detector.py` already makes and explains for the identical reason:
    this recipe's confidence is flat, not age-gated, so there is nothing
    here for `now` to weigh against."""
    del now  # unused today; kept for interface parity, see docstring above.
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for message in sorted(messages, key=lambda m: m.id):
        if not message.text:
            continue

        numbers = _claimed_milestone_numbers(message.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{message.id}",
                headline=f"{message.channel}'s message {message.id} names no milestone claim",
                detail=f"'{message.text}' ({message.url}) carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[message.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a message naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN, the same
        # guard every dangling-milestone sibling already holds.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-{message.id}-{number}",
                    headline=f"{message.channel}'s message {message.id}'s claimed milestone #{number} is real",
                    detail=(
                        f"'{message.text}' ({message.url}) claims milestone #{number} "
                        f"('{milestone.title}', state '{milestone.state}'); the milestone "
                        "exists. Whether the claim itself is TRUE is a different recipe's "
                        "seam (slack-message-claims-open-milestone), not this one's. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[message.url, milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"slack-message-claims-dangling-milestone-{message.id}-{number}",
                headline=f"{message.channel}'s message {message.id} claims milestone #{number}, which doesn't exist",
                detail=(
                    f"'{message.text}' ({message.url}) claims milestone #{number}, but no "
                    "milestone with that number exists at all. Slack renders the number as "
                    "plain text regardless; nothing on either platform ever checks a "
                    "'milestone #N' claim phrase posted to a channel against the real "
                    "milestone tracker."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[message.url],
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
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the-hand's gateway carries a
    live `SearchChannelMessages`/`ListMilestones` read for a connected
    Slack workspace and these two loaders are swapped for real calls.
    The detection logic does not change one line when that happens."""
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
