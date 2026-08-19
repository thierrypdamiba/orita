"""The eighty-sixth real seam recipe: a mortal's own X mention of the
connected account claims a "milestone #N" that doesn't exist at all.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`mentions.json`,
`milestones.json`), shaped like what `GetMyMentions` and `ListMilestones`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared
oath table (`GetMyMentions` since founding, first used by
`mention-dangling-reference`; `ListMilestones` used by every milestone-
claim recipe already in this engine). No new scope is asked for anywhere
in this recipe.

`mention-claims-open-milestone` (the forty-eighth real recipe) was the
first to pair a mortal's own X mention with `ListMilestones`, and its own
docstring drew the line precisely: a claimed milestone number that names
no real milestone at all is excluded there, named not hidden -- "that
broken reference is a dangling-reference-family seam, not this one's."
This recipe is that seam, on the one surface that named it and never
closed it -- the mention-sourced sibling of `commit-claims-dangling-
milestone` (task 649, the seventy-sixth), `issue-comment-claims-dangling-
milestone` (task 865, the eighty-first), `review-comment-claims-dangling-
milestone` (task 866, the eighty-second), `slack-message-claims-dangling-
milestone` (task 867, the eighty-third), and `linear-comment-claims-
dangling-milestone` (task 868, the eighty-fourth), which closed the
identical seam for a commit message, an issue/PR timeline comment, a pull
request's own inline review comment, a Slack channel message, and a
Linear issue comment respectively. Task 869's own own-remit sweep named
this family "genuinely saturated" against a different axis (the claims-
unfixed-issue/claims-unmerged-pr/claims-open-milestone x 10-source grid)
without actually re-deriving the claims-dangling-milestone column's own
five real siblings against its own ten sources -- a live recheck this
hour found the mention/milestone/readme/release/tweet cells still empty,
each one's own docstring naming a "dangling-reference-family seam, not
this one's" that was never actually built for the milestone number space
specifically (`mention-dangling-reference`, `milestone-body-dangling-
reference`, `readme-dangling-reference`, `release-note-dangling-
reference`, and `own-tweet-dangling-reference` all check the shared
issue/PR number sequence only -- none of them ever opens `ListMilestones`
at all). This recipe closes the first of those five real gaps; the other
four remain open, correctly, for a future hour.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim -- the same shared grammar every `*-claims-dangling-milestone`
sibling already imports -- rather than a sixth independently retyped copy
of the identical pattern.

Not `mention-dangling-reference`'s seam wearing a new name: that recipe
(the eleventh real recipe) watches a bare `#N` inside a mortal's own
mention against GitHub's shared issue/PR number sequence and never once
opens `ListMilestones`. A milestone lives in its own, separate number
space that issues and pull requests never touch, so a `#N` that resolves
cleanly as an issue could still be a dangling MILESTONE claim, and a `#N`
that is a real milestone could just as easily collide with a real issue
number. Confusing the two spaces would be exactly the false-positive
failure Ogun's law calls fatal -- so this recipe reads
`claimed_milestone_numbers`'s own "milestone #N" phrase grammar, never
the bare-`#N` grammar `mention-dangling-reference` already owns.

The claim stays narrow, the same no-grading law every sibling holds: a
mention that merely mentions a bare `#N` in passing ("same root cause as
#6399") makes no milestone claim at all, and is excluded, not guessed
into either bucket -- that bare shape is `mention-dangling-reference`'s
own seam, not this one's. A claimed milestone number that DOES resolve to
a real milestone is excluded too, named not hidden, regardless of whether
that milestone is open or closed -- whether the claim is TRUE is
`mention-claims-open-milestone`'s own seam, not this one's; this recipe
only ever asks whether the name resolves to anything at all.

Confidence is flat (0.8), not age-gated -- mirrors `commit-claims-
dangling-milestone`'s, `issue-comment-claims-dangling-milestone`'s,
`review-comment-claims-dangling-milestone`'s, `slack-message-claims-
dangling-milestone`'s, and `linear-comment-claims-dangling-milestone`'s
own reasoning rather than `mention-claims-open-milestone`'s 24-hour
edit-grace bar. That bar exists because an OPEN milestone could close at
any moment, so a fresh claim about it might just be a race the mention
hasn't caught up to yet; a milestone number that does not exist right now
will not spontaneously start existing later no matter how long the
mention sits, so there is no grace period that means anything here.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "mention_claims_dangling_milestone"
DEFAULT_MENTIONS_FIXTURE = _FIXTURE_DIR / "mentions.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors every prior
# claims-dangling-milestone sibling's own _DANGLING_CONFIDENCE exactly
# (0.8): a nonexistent milestone number will not spontaneously start
# existing, whatever the age of the mention naming it.
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


def load_mentions(path: Path | None = None) -> list[Mention]:
    rows = _load_rows(path or DEFAULT_MENTIONS_FIXTURE)
    return [
        Mention(
            id=r["id"], author=r["author"], text=r.get("text") or "",
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
    own `compute_gaps`. A mention with no text at all is never examined at
    all -- it claims nothing, so there is no seam to weigh. A mention
    naming no 'milestone #N' claim phrase is excluded, named not hidden.
    A claimed milestone is excluded, named not hidden, the moment it
    names a real milestone (open or closed, this recipe does not care
    which) -- everything left over (a claimed milestone number with no
    real milestone behind it at all) is surfaced at a flat confidence.

    `now` is accepted, unused -- kept for interface parity with every
    other recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_
    scan` always threads one through), the identical "unused today, kept
    for the shape" choice every prior claims-dangling-milestone sibling's
    own detector already makes and explains for the identical reason:
    this recipe's confidence is flat, not age-gated, so there is nothing
    here for `now` to weigh against."""
    del now  # unused today; kept for interface parity, see docstring above.
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for mention in sorted(mentions, key=lambda m: m.id):
        if not mention.text:
            continue

        numbers = _claimed_milestone_numbers(mention.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{mention.id}",
                headline=f"@{mention.author}'s mention {mention.id} names no milestone claim",
                detail=f"'{mention.text}' ({mention.url}) carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[mention.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a mention naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN, the same
        # guard every dangling-milestone sibling already holds.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-{mention.id}-{number}",
                    headline=f"@{mention.author}'s mention {mention.id}'s claimed milestone #{number} is real",
                    detail=(
                        f"'{mention.text}' ({mention.url}) claims milestone #{number} "
                        f"('{milestone.title}', state '{milestone.state}'); the milestone "
                        "exists. Whether the claim itself is TRUE is a different recipe's "
                        "seam (mention-claims-open-milestone), not this one's. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[mention.url, milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"mention-claims-dangling-milestone-{mention.id}-{number}",
                headline=f"@{mention.author}'s mention {mention.id} claims milestone #{number}, which doesn't exist",
                detail=(
                    f"'{mention.text}' ({mention.url}) claims milestone #{number}, but no "
                    "milestone with that number exists at all. X renders the number as "
                    "plain text regardless; nothing on either platform ever checks a "
                    "'milestone #N' claim phrase posted by a stranger against the real "
                    "milestone tracker."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[mention.url],
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
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the-hand's gateway carries a
    live `GetMyMentions`/`ListMilestones` read for a connected account and
    these two loaders are swapped for real calls. The detection logic
    does not change one line when that happens."""
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
