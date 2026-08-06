"""The forty-eighth real seam recipe: a mortal's own X mention of the
connected account claims a milestone shipped ("milestone #N"), but the
named milestone is not actually closed.

The mention-side leg the claims-open-milestone family had never grown.
`readme-claims-open-milestone`, `release-claims-open-milestone`, and
`tweet-claims-open-milestone` already cover every text surface the town
itself controls -- its own README, its own release notes, its own tweets
-- but all three only ever check a "shipped it" claim the town made ABOUT
itself. This recipe checks the identical milestone-claim grammar against
the one inbound surface none of those three ever read: a stranger's own
mention of the account, sourced from `GetMyMentions` rather than
`GetUserTweets` -- the same tweet-vs-mention split
`mention-claims-unfixed-issue` (the forty-seventh real recipe) already
opened against `tweet-claims-unfixed-issue` for the sibling
claims-unfixed-issue family, applied here to the claims-open-milestone
family instead. `milestone-claims-unfixed-issue` (the forty-fifth) closed
the milestone-BODY leg of claims-unfixed-issue; this recipe closes the
mention leg of claims-open-milestone -- two different open corners of the
same claims-X grid, not a repeat of either.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim -- the same shared grammar `milestone-closed-never-released`,
`release-claims-open-milestone`, `milestone-closed-not-tweeted`, and
`tweet-claims-open-milestone` already import from there (task 389
centralized what had been two independently retyped copies, and every
milestone-claim recipe since has bound to the one shared name) -- rather
than a fifth copy of the identical pattern drifting apart from the rest.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`mentions.json`,
`milestones.json`), shaped like what `GetMyMentions` and `ListMilestones`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared
oath table (`GetMyMentions` since founding, first used by
`mention-dangling-reference`; `ListMilestones` used by every milestone-
claim recipe already in this engine). No new scope is asked for anywhere
in this recipe.

The seam: a `milestone #N` claim phrase inside a mortal's own mention
names a milestone by number. If that milestone does not exist at all, it
is excluded here -- that broken reference is a dangling-reference-family
seam, not this one's. If it exists and is closed, the claim was simply
true -- excluded, named not hidden. If it exists and is still open, a
stranger's own permanent public claim about the project, sitting on X,
already disagrees with GitHub's own record -- and nothing on either
platform ever compares the two.

Confidence is age-gated by the mention's own `created_at`, mirroring
`tweet-claims-open-milestone`'s identical reasoning -- not a discounted
copy of it. A claim checked within 24 hours of posting might still be a
race (the milestone actually closing out moments after the mention went
out) rather than a settled overclaim. Like `mention-claims-unfixed-issue`'s
own reasoning (and unlike `mention-dangling-reference`'s deliberately
lower, flat score), the check this recipe makes is objective: the claimed
milestone's own live `state` field, verified against `ListMilestones`,
not the mortal's guess at the repo's number space. A mortal cannot be
"wrong about the number space" and still land a real, existing milestone
number attached to a real `milestone #N` claim -- so this recipe holds
`tweet-claims-open-milestone`'s own 0.85/0.5 bar exactly, no independently
re-reasoned number.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "mention_claims_open_milestone"
DEFAULT_MENTIONS_FIXTURE = _FIXTURE_DIR / "mentions.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A claim checked within this window of the mention's own created_at may
# just be a race rather than a genuine, settled public overclaim -- the
# identical bar tweet-claims-open-milestone holds itself to.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Mention:
    id: str
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


def load_mentions(path: Path | None = None) -> list[Mention]:
    rows = _load_rows(path or DEFAULT_MENTIONS_FIXTURE)
    return [
        Mention(
            id=r["id"], author=r["author"], text=r["text"],
            created_at=_parse_ts(r["created_at"]), url=r["url"],
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
    mentions: list[Mention], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed milestone is excluded, named not hidden,
    the moment it names no real milestone at all, or the milestone it
    names is already closed -- everything left over (a shipped-it claim
    the milestone tracker itself contradicts) is surfaced, aged into a
    confidence score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for mention in mentions:
        numbers = _claimed_milestone_numbers(mention.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{mention.id}",
                headline=f"@{mention.author}'s mention {mention.id} names no milestone claim",
                detail=f"'{mention.text}' carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[mention.url],
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
                    slug=f"claimed-milestone-not-found-{mention.id}-{number}",
                    headline=f"@{mention.author}'s mention {mention.id} claims milestone #{number}, which doesn't exist",
                    detail=f"'{mention.text}' claims milestone #{number} shipped, but no such milestone exists. No seam here.",
                    confidence=0.0,
                    evidence=[mention.url],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{mention.id}-{number}",
                    headline=f"@{mention.author}'s mention {mention.id}'s claim about milestone #{number} holds",
                    detail=f"'{mention.text}' claims milestone #{number} ('{milestone.title}') shipped; the milestone is closed. No seam here.",
                    confidence=0.0,
                    evidence=[mention.url, milestone.url],
                ))
                continue

            age_hours = (now - mention.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"mention-claims-open-milestone-{mention.id}-{number}",
                headline=f"@{mention.author}'s mention {mention.id} claims milestone #{number} shipped, but it's still open",
                detail=(
                    f"'{mention.text}' (posted {mention.created_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims milestone #{number} ('{milestone.title}') "
                    f"shipped; the milestone's real state is '{milestone.state}'."
                ),
                confidence=confidence,
                evidence=[mention.url, milestone.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    mentions_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetMyMentions`/`ListMilestones` read for a connected account and these
    two loaders are swapped for real calls. The detection logic does not
    change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    mentions = load_mentions(mentions_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(mentions, milestones, now=now)
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
