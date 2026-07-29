"""The nineteenth real seam recipe: a milestone closed, but no tweet from
the connected X account ever named it.

The milestone-side twin of `release-not-tweeted` (task 110, the third real
recipe and the first cross-toolkit one): that recipe watches a GitHub
release with no matching tweet within `release-not-tweeted`'s own 24-hour
announce window, matched by an exact tag substring. A milestone has no
tag, so this recipe reuses the "milestone #N" claim phrase
`milestone-closed-never-released` (task 383) and `release-claims-open-
milestone` (task 385) already established for milestones, checked against
a tweet's own text instead of a release's own body -- the same claim
grammar, a third data source.

That claim phrase used to live as two textually-identical, independently
typed copies (`milestone-closed-never-released/detector.py`'s own
`_CLAIM_RE`, and `release-claims-open-milestone/detector.py`'s comment-
only "mirrors ... verbatim" copy of it) -- the exact "two copies that
happen to agree today, nothing stopping them from drifting apart" shape
task 389 found and fixed for `#N` extraction (see `references.py`'s own
docstring). Rather than writing a THIRD copy for this recipe and repeating
that mistake a second time, both existing detectors now import
`claimed_milestone_numbers` from the new `seam_engine.milestone_claims`
module, and this recipe imports the same function from the start.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`milestones.json`,
`tweets.json`), shaped like what `ListMilestones` and `GetUserTweets`
would actually return. Both scopes already sit on SCOPES.md's cleared
oath table -- this recipe asks Arcade for nothing new.

The seam: a milestone closes, but no tweet from the connected account's
own read-so-far history ever names it in a "milestone #N" claim. A
milestone that is still open has nothing for a tweet to have missed yet --
excluded, not a gap. A milestone that IS named by at least one tweet, at
any point in the read-so-far history, was announced -- excluded, named
not hidden. Everything left over -- a closed milestone no tweet has ever
named -- is the gap, aged by how long it has sat unannounced.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "milestone_closed_not_tweeted"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"
DEFAULT_TWEETS_FIXTURE = _FIXTURE_DIR / "tweets.json"

# A milestone closed under this age, with no tweet having named it yet, may
# simply be waiting on someone to post -- not yet a settled gap. Matches
# release-not-tweeted's own announce window exactly.
_ANNOUNCE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    closed_at: datetime | None
    url: str


@dataclass
class Tweet:
    id: str
    text: str
    created_at: datetime
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_milestones(path: Path | None = None) -> list[Milestone]:
    rows = _load_rows(path or DEFAULT_MILESTONES_FIXTURE)
    return [
        Milestone(
            number=r["number"], title=r["title"], state=r["state"],
            closed_at=_parse_ts(r["closed_at"]) if r.get("closed_at") else None,
            url=r["url"],
        )
        for r in rows
    ]


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = _load_rows(path or DEFAULT_TWEETS_FIXTURE)
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
        for r in rows
    ]


def _announcing_tweets_by_number(tweets: list[Tweet]) -> dict[int, list[Tweet]]:
    """Every tweet, across the whole read-so-far history, that names a
    given milestone number via a 'milestone #N' claim -- not just the
    newest one. A milestone only needs ONE tweet to have ever named it to
    be cleared."""
    announced: dict[int, list[Tweet]] = {}
    for tweet in tweets:
        for number in _claimed_milestone_numbers(tweet.text):
            announced.setdefault(number, []).append(tweet)
    return announced


def compute_gaps(
    milestones: list[Milestone], tweets: list[Tweet], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A milestone is excluded, named not hidden, the
    moment it is still open, or at least one tweet across the whole
    history read so far has already named it. Everything left over -- a
    closed milestone no tweet has ever named -- is surfaced, aged into a
    confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []
    announced = _announcing_tweets_by_number(tweets)

    for milestone in milestones:
        if milestone.state != "closed" or milestone.closed_at is None:
            excluded.append(GapCandidate(
                slug=f"milestone-not-closed-{milestone.number}",
                headline=f"Milestone #{milestone.number} is still open",
                detail=f"'{milestone.title}' reads state={milestone.state}. No seam here.",
                confidence=0.0,
                evidence=[milestone.url],
            ))
            continue

        announcing_tweets = announced.get(milestone.number, [])
        if announcing_tweets:
            tweet = announcing_tweets[0]
            excluded.append(GapCandidate(
                slug=f"milestone-tweeted-{milestone.number}",
                headline=f"Milestone #{milestone.number} was already tweeted",
                detail=(
                    f"'{milestone.title}' (#{milestone.number}) is named in "
                    f"{tweet.url}. No seam here."
                ),
                confidence=0.0,
                evidence=[milestone.url, tweet.url],
            ))
            continue

        age_hours = (now - milestone.closed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _ANNOUNCE_WINDOW_HOURS else 0.55
        surfaced.append(GapCandidate(
            slug=f"milestone-closed-not-tweeted-{milestone.number}",
            headline=f"Milestone #{milestone.number} closed, but no tweet has ever named it",
            detail=(
                f"'{milestone.title}' (#{milestone.number}) closed "
                f"{milestone.closed_at.isoformat()} ({age_hours:.1f}h ago); "
                "no tweet read so far names it in a 'milestone #N' claim."
            ),
            confidence=confidence,
            evidence=[milestone.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    milestones_path: Path | None = None,
    tweets_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListMilestones`/`GetUserTweets` read and these two loaders are swapped
    for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    milestones = load_milestones(milestones_path)
    tweets = load_tweets(tweets_path)
    surfaced, excluded = compute_gaps(milestones, tweets, now=now)
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
