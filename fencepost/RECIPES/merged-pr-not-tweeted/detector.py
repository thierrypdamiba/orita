"""The twentieth real seam recipe: a pull request merges into `main`, but no
tweet from the connected X account ever names its number.

`release-not-tweeted` (task 110) and `milestone-closed-not-tweeted` (task
390) both watch "shipped work never announced" -- but both gate the check
behind a second GitHub record (a release, a milestone) that a merged PR
does not have to acquire at all. Most merged PRs in this town's own history
never get wrapped in either: STRATEGY.md's own metrics table already names
"a release shipped but never tweeted" as the worked example, and the two
existing recipes above cover exactly that when a release or milestone
exists. This recipe watches the seam underneath both of them -- the PR
itself, the moment it merges -- so a real shipped change with no release
and no milestone around it is never invisible to this desk just because
nobody wrapped it in one.

GitHub+X, the same cross-toolkit shape `release-not-tweeted` established
first. Both scopes already sit on `SCOPES.md`'s cleared oath table under
their own toolkit rows (`ListPullRequests`, `GetUserTweets`) -- no new
scope wiring anywhere in this recipe, matching the last several recipes'
own "reuse, don't widen" discipline.

Matching is by exact PR-number substring (`#<N>`), not title-keyword
overlap, mirroring `release-not-tweeted`'s own "exact tag, not fuzzy
matching" doctrine: a PR's number either appears in a tweet's text, on its
own, digit-bounded, or it does not. The same collision class
`release-not-tweeted` fixed once already (a short tag matching inside a
longer one) exists here in numeral form -- `#13` must not be considered a
mention of PR #1301 just because "1301" is a substring of "13010" -- so
the match is digit-boundary-guarded on both sides, not bare substring
containment.

A PR that never merged (still open, or closed without merging) is not in
scope at all -- there is nothing shipped yet to announce, the same
exclusion `merged-pr-never-released`/`merged-pr-issue-still-open` already
draw at their own front door.

Confidence is age-gated, mirroring `release-not-tweeted`'s own reasoning:
a merge with no matching tweet within `_ANNOUNCE_WINDOW_HOURS` is not yet a
gap (a human may simply not have tweeted yet); past the window with still
no match, it is.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "merged_pr_not_tweeted" / "pulls.json"
DEFAULT_TWEETS_FIXTURE = _HERE.parents[1] / "fixtures" / "merged_pr_not_tweeted" / "tweets.json"

# A merge announced within this window of merging is not yet a gap --
# auto-post lag or a human simply hasn't tweeted yet.
_ANNOUNCE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class MergedPull:
    id: str
    number: int
    title: str
    merged_at: datetime
    url: str


@dataclass
class Tweet:
    id: str
    text: str
    created_at: datetime
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_merged_pulls(path: Path | None = None) -> list[MergedPull]:
    """Only rows whose `state` reads `merged` become candidates at all --
    an open or closed-unmerged PR has nothing shipped yet to announce, the
    same front-door exclusion every merged-PR recipe before this one draws."""
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        MergedPull(
            id=r["id"], number=r["number"], title=r["title"],
            merged_at=_parse_ts(r["merged_at"]), url=r["url"],
        )
        for r in rows
        if r.get("state") == "merged" and r.get("merged_at")
    ]


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = _load_rows(path or DEFAULT_TWEETS_FIXTURE)
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
        for r in rows
    ]


def _find_announcing_tweet(number: int, tweets: list[Tweet]) -> Tweet | None:
    # Digit-boundary match on both sides -- "#1301" must not be considered
    # mentioned by a tweet naming the unrelated, longer "#13010", the same
    # short-inside-long collision release-not-tweeted's own tag matcher
    # already guards against, in numeral form instead of version-string form.
    pattern = re.compile(r"(?<!\d)#" + re.escape(str(number)) + r"(?!\d)")
    for tweet in tweets:
        if pattern.search(tweet.text):
            return tweet
    return None


def compute_gaps(
    pulls: list[MergedPull], tweets: list[Tweet], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape every recipe before this
    one returns. A merged PR is excluded, named not hidden, the moment a
    tweet's text names its number; everything left over (never mentioned)
    is surfaced, aged into a confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pull in pulls:
        tweet = _find_announcing_tweet(pull.number, tweets)
        if tweet is not None:
            excluded.append(GapCandidate(
                slug=f"merged-pr-tweeted-{pull.number}",
                headline=f"#{pull.number} was tweeted",
                detail=f"'{pull.title}' (#{pull.number}) is named in {tweet.url}. No seam here.",
                confidence=0.0,
                evidence=[pull.url, tweet.url],
            ))
            continue

        age_hours = (now - pull.merged_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _ANNOUNCE_WINDOW_HOURS else 0.55
        surfaced.append(GapCandidate(
            slug=f"merged-pr-not-tweeted-{pull.number}",
            headline=f"#{pull.number} merged, never tweeted",
            detail=(
                f"'{pull.title}' (#{pull.number}) merged {pull.merged_at.isoformat()} "
                f"({age_hours:.1f}h ago); no tweet from the connected account names it."
            ),
            confidence=confidence,
            evidence=[pull.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pulls_path: Path | None = None,
    tweets_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every recipe before
    this one -- `source: "fixture"` is the honest WIP marker this recipe
    carries until the Hand's gateway carries a live PR-list scope wired into
    the real daily run and these two loaders are swapped for real reads. The
    detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pulls = load_merged_pulls(pulls_path)
    tweets = load_tweets(tweets_path)
    surfaced, excluded = compute_gaps(pulls, tweets, now=now)
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
