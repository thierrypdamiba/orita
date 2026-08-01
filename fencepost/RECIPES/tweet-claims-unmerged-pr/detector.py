"""Twenty-seventh real seam recipe: a tweet from the connected X account
claims a pull request shipped, but the pull request never actually merged.

`release-claims-unmerged-pr` (task 378) built this exact shape first: a
single record's own claim about a second record that DOES exist, but whose
real state contradicts the claim. That recipe watches a release body; this
one watches the other place the town makes the identical kind of
permanent, public "it shipped" claim -- a tweet. GitHub's release page and
X's timeline are both append-only public records nothing on either
platform ever checks against the PR tracker's own truth once posted.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`tweets.json`,
`pulls.json`), shaped like what `GetUserTweets` and `ListPullRequests`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared
oath table -- this recipe asks Arcade for nothing new.

The seam: a claim phrase ("ships #N" / "includes #N" / "merges #N" /
"via #N", case-insensitive) inside a tweet's own text names a PR by
number. If that PR does not exist at all, it is excluded here -- that
broken reference is `dangling-issue-reference`'s/`mention-dangling-
reference`'s own seam. If it exists and is merged, the claim was simply
true -- excluded, named not hidden. If it exists and is NOT merged (still
open, or closed without merging), the tweet's own permanent public record
disagrees with reality: that is the gap.

Confidence is age-gated by the tweet's own `created_at`, mirroring
`release-claims-unmerged-pr`'s reasoning exactly: a claim checked within a
few hours of posting might still be a race (tweet posted moments before
the real merge lands) rather than a settled overclaim.

Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim -- the same
"ships/includes/merges/via #N" grammar `release-claims-unmerged-pr` and
`merged-pr-never-released` already share -- rather than a third,
independently typed copy of the identical regex drifting apart from the
other two the way task 393 found and fixed once already.
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
DEFAULT_TWEETS_FIXTURE = _HERE.parents[1] / "fixtures" / "tweet_claims_unmerged_pr" / "tweets.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "tweet_claims_unmerged_pr" / "pulls.json"

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
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = _load_rows(path or DEFAULT_TWEETS_FIXTURE)
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
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
    tweets: list[Tweet], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed PR is excluded, named not hidden, the
    moment it names no real PR at all, or the PR it names is actually
    merged -- everything left over (a claim the PR tracker itself
    contradicts) is surfaced, aged into a confidence score rank() can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for tweet in tweets:
        numbers = _claimed_pr_numbers(tweet.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{tweet.id}",
                headline=f"Tweet {tweet.id} names no ships/includes/merges/via PR claim",
                detail=f"'{tweet.text}' carries no claim-phrase reference. No seam here.",
                confidence=0.0,
                evidence=[tweet.url],
            ))
            continue

        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)

            pr = _find_pull(number, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{tweet.id}-{number}",
                    headline=f"Tweet {tweet.id} claims #{number}, which doesn't exist",
                    detail=f"'{tweet.text}' claims #{number} shipped, but no such PR exists. No seam here (see dangling-issue-reference).",
                    confidence=0.0,
                    evidence=[tweet.url],
                ))
                continue

            if pr.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-{tweet.id}-{number}",
                    headline=f"Tweet {tweet.id}'s claim about #{number} holds",
                    detail=f"'{tweet.text}' claims #{number} shipped; PR #{number} ('{pr.title}') is merged. No seam here.",
                    confidence=0.0,
                    evidence=[tweet.url, pr.url],
                ))
                continue

            age_hours = (now - tweet.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"tweet-claims-unmerged-pr-{tweet.id}-{number}",
                headline=f"Tweet {tweet.id} claims #{number} shipped, but #{number} never merged",
                detail=(
                    f"'{tweet.text}' (posted {tweet.created_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{pr.title}') shipped; "
                    f"the PR's real state is '{pr.state}', merged={pr.merged}."
                ),
                confidence=confidence,
                evidence=[tweet.url, pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    tweets_path: Path | None = None,
    pulls_path: Path | None = None,
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
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(tweets, pulls, now=now)
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
