"""Third real seam recipe: a GitHub release shipped, but no tweet from the
connected X account ever mentioned it.

The first CROSS-TOOLKIT recipe. `example-release-vs-changelog/` (task 22)
and `merged-pr-issue-still-open/` (task 108) both watch a seam that lives
entirely inside GitHub. This one watches the seam STRATEGY.md names by hand
as Fencepost's own worked example — "a release shipped but never tweeted" —
proving RECIPES/ can hold a detector that reads across two toolkits at once,
not just two files inside one.

Read-only in spirit, MOCK ONLY in practice, same as both recipes before it:
this module only ever reads two local fixture files (`releases.json`,
`tweets.json`), shaped like what a releases-list call and `GetUserTweets`
would actually return. All three declared scopes already sit on SCOPES.md's
cleared oath table under their own toolkit rows (GitHub's `GetRepository`/
`ListRepoCommits` — the same releases-representing pair
`example-release-vs-changelog/recipe.json` already claims; X's
`GetUserTweets`). No new scope is asked for anywhere in this recipe.

Matching by exact tag substring, not keyword overlap, on purpose — the same
"no fuzzy matching to misfire on" discipline the reference recipe's own
confidence_notes leans on: a release's tag either appears verbatim
somewhere in a tweet's text or it does not.

Confidence is age-gated, mirroring merged-pr-issue-still-open's reasoning:
a release with no matching tweet within `_ANNOUNCE_WINDOW_HOURS` of publish
is not yet a gap (a human may simply not have tweeted yet, and X_PostTweet
carries its own outage on this desk some hours); past the window with still
no match, it is.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_RELEASES_FIXTURE = _HERE.parents[1] / "fixtures" / "release_not_tweeted" / "releases.json"
DEFAULT_TWEETS_FIXTURE = _HERE.parents[1] / "fixtures" / "release_not_tweeted" / "tweets.json"

# A release announced within this window of publish is not yet a gap --
# auto-post lag or a human simply hasn't tweeted yet.
_ANNOUNCE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Release:
    id: str
    title: str
    tag: str
    published_at: datetime
    url: str


@dataclass
class Tweet:
    id: str
    text: str
    created_at: datetime
    url: str


def load_releases(path: Path | None = None) -> list[Release]:
    rows = json.loads(Path(path or DEFAULT_RELEASES_FIXTURE).read_text())
    return [
        Release(
            id=r["id"], title=r["title"], tag=r["tag"],
            published_at=_parse_ts(r["published_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = json.loads(Path(path or DEFAULT_TWEETS_FIXTURE).read_text())
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
        for r in rows
    ]


def _find_announcing_tweet(tag: str, tweets: list[Tweet]) -> Tweet | None:
    for tweet in tweets:
        if tag.lower() in tweet.text.lower():
            return tweet
    return None


def compute_gaps(
    releases: list[Release], tweets: list[Tweet], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as `scan.compute_candidates`
    and both recipes before this one. A release is excluded, named not
    hidden, the moment a tweet's text contains its exact tag; everything
    left over (never mentioned) is surfaced, aged into a confidence score
    `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for release in releases:
        tweet = _find_announcing_tweet(release.tag, tweets)
        if tweet is not None:
            excluded.append(GapCandidate(
                slug=f"release-tweeted-{release.tag}",
                headline=f"{release.tag} was tweeted",
                detail=f"'{release.title}' ({release.tag}) is named in {tweet.url}. No seam here.",
                confidence=0.0,
                evidence=[release.url, tweet.url],
            ))
            continue

        age_hours = (now - release.published_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _ANNOUNCE_WINDOW_HOURS else 0.55
        surfaced.append(GapCandidate(
            slug=f"release-not-tweeted-{release.tag}",
            headline=f"{release.tag} shipped, never tweeted",
            detail=(
                f"'{release.title}' ({release.tag}) published {release.published_at.isoformat()} "
                f"({age_hours:.1f}h ago); no tweet from the connected account names it."
            ),
            confidence=confidence,
            evidence=[release.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    releases_path: Path | None = None,
    tweets_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as both recipes before
    this one -- `source: "fixture"` is the honest WIP marker this recipe
    carries until the Hand's gateway carries a live releases-list scope and
    these two loaders are swapped for real reads. The detection logic does
    not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    releases = load_releases(releases_path)
    tweets = load_tweets(tweets_path)
    surfaced, excluded = compute_gaps(releases, tweets, now=now)
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
