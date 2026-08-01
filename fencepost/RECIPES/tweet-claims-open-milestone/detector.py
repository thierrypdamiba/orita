"""Twenty-ninth real seam recipe: a tweet from the connected X account
claims a milestone shipped ("milestone #N"), but the named milestone is
not actually closed.

The tweet-side twin of `release-claims-open-milestone` (task 385), which
watches the identical single-record-makes-a-permanent-false-claim shape
but inside a release's own body. This recipe watches the same shape
against the OTHER place the town makes a public, unedited "shipped it"
claim -- a tweet, mirroring `tweet-claims-unmerged-pr` (task 450) and
`tweet-claims-unfixed-issue` (task 451) one leg over: those two recipes
cover the PR-claim and issue-claim halves of the release-vs-tweet split
this family already has; this recipe closes the matching milestone-claim
half.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim -- the same shared grammar `release-claims-open-milestone` and
`milestone-closed-not-tweeted` already import from there (task 389
centralized what had been two independently retyped copies) -- rather
than a third copy of the identical pattern drifting apart from the other
two.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`tweets.json`,
`milestones.json`), shaped like what `GetUserTweets` and `ListMilestones`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared
oath table -- this recipe asks Arcade for nothing new.

The seam: a `milestone #N` claim phrase inside a tweet's own text names a
milestone by number. If that milestone does not exist at all, it is
excluded here -- a broken reference is `dangling-issue-reference`'s own
seam (over issues/PRs), not this one's (over milestones). If it exists
and is closed, the claim was simply true -- excluded, named not hidden.
If it exists and is still open, the tweet's own permanent public record
disagrees with reality: that is the gap.

Confidence is age-gated by the tweet's own `created_at`, mirroring
`release-claims-open-milestone`'s and `tweet-claims-unfixed-issue`'s
identical reasoning: a claim checked within a few hours of posting might
still be a race (tweet posted moments before the milestone is actually
closed out) rather than a settled overclaim.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "tweet_claims_open_milestone"
DEFAULT_TWEETS_FIXTURE = _FIXTURE_DIR / "tweets.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A claim checked within this window of the tweet's own created_at may just
# be a race rather than a genuine, settled public overclaim.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Tweet:
    id: str
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


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = _load_rows(path or DEFAULT_TWEETS_FIXTURE)
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
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
    tweets: list[Tweet], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed milestone is excluded, named not hidden,
    the moment it names no real milestone at all, or the milestone it
    names is already closed -- everything left over (a shipped-it claim
    the milestone tracker itself contradicts) is surfaced, aged into a
    confidence score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for tweet in tweets:
        numbers = _claimed_milestone_numbers(tweet.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{tweet.id}",
                headline=f"Tweet {tweet.id} names no milestone claim",
                detail=f"'{tweet.text}' carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[tweet.url],
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
                    slug=f"claimed-milestone-not-found-{tweet.id}-{number}",
                    headline=f"Tweet {tweet.id} claims milestone #{number}, which doesn't exist",
                    detail=f"'{tweet.text}' claims milestone #{number} shipped, but no such milestone exists. No seam here.",
                    confidence=0.0,
                    evidence=[tweet.url],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{tweet.id}-{number}",
                    headline=f"Tweet {tweet.id}'s claim about milestone #{number} holds",
                    detail=f"'{tweet.text}' claims milestone #{number} ('{milestone.title}') shipped; the milestone is closed. No seam here.",
                    confidence=0.0,
                    evidence=[tweet.url, milestone.url],
                ))
                continue

            age_hours = (now - tweet.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"tweet-claims-open-milestone-{tweet.id}-{number}",
                headline=f"Tweet {tweet.id} claims milestone #{number} shipped, but it's still open",
                detail=(
                    f"'{tweet.text}' (posted {tweet.created_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims milestone #{number} ('{milestone.title}') "
                    f"shipped; the milestone's real state is '{milestone.state}'."
                ),
                confidence=confidence,
                evidence=[tweet.url, milestone.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    tweets_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    tweet read and these loaders are swapped for real calls. The detection
    logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    tweets = load_tweets(tweets_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(tweets, milestones, now=now)
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
