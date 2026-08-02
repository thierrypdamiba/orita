"""The thirty-first real seam recipe (ROADMAP.md #486): a repository crosses
a round-number star milestone, but no tweet from the connected X account
ever announces it.

`CountStargazers` has sat on `SCOPES.md`'s cleared oath table since the
first day (`fencepost/SCOPES.md` line 15) alongside `GetLatestRelease` and
`ListMilestones`, yet no shipped recipe before this one ever read it --
every prior star-related mention in this codebase is about the town's own
lagging `github_stars` metric (`tools/github_stars_check.py`), never a
detector. GitHub+X, the same cross-toolkit shape `release-not-tweeted`
(task 110) established first: a count on one timeline, an announcement on
the other, neither alone showing the gap.

The seam: crossing a round number of stars (10, 100, 1000, ...) is exactly
the kind of "milestone-class work that stays silent" `seam_engine/ranking.py`'s
own docstring names as a real gap, not volume -- a screenshotable, one-line
fact that is easy to simply forget to post, the same way a merged PR or a
closed issue is (`merged-pr-not-tweeted`, `issue-closed-not-tweeted`). Only
the single HIGHEST milestone the live count has crossed is ever considered:
a repo sitting at 267 stars crossed 250, not 100 or 50 too, and only the
biggest round number actually earns the announcement -- the same "salience,
not every threshold passed through" judgment a human would make.

Matching is digit-boundary-guarded on both spellings a round number this
size gets written with in ordinary prose ("1000" and "1,000"), mirroring
every sibling recipe's own short-inside-long collision guard, AND requires
the word "star" to appear somewhere in the same tweet -- so a tweet naming
an unrelated "250" (an issue number, a commit count) is never mistaken for
a star-milestone announcement.

Unlike every prior recipe in the not-tweeted family, this one carries no
age-gate: `CountStargazers` returns a live snapshot, not a timestamped
crossing event, so there is no "may simply not have tweeted yet within N
hours" grace window to compute against -- a crossed-and-silent milestone is
either announced or it is not, at flat confidence 0.85, the same
unambiguous "exact match, nothing fuzzy" confidence
`deleted-branch-pr-still-open` already assigns its own exact ref match.

MOCK ONLY, same as every recipe before this one: this module only ever
reads two local fixture files (`stargazers.json`, `tweets.json`), shaped
like what `CountStargazers`/`GetUserTweets` would return. Both scopes
already sit on `SCOPES.md`'s cleared oath table -- this recipe asks Arcade
for nothing new.
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
DEFAULT_STARGAZERS_FIXTURE = _HERE.parents[1] / "fixtures" / "star_milestone_not_announced" / "stargazers.json"
DEFAULT_TWEETS_FIXTURE = _HERE.parents[1] / "fixtures" / "star_milestone_not_announced" / "tweets.json"

# Round numbers worth a screenshot -- Ogun's law made numeric (ranking.py:
# "milestone-class work that stays silent" is a gap; background noise is
# not). Ordinary, human-legible round-number cadence, the same doubling-ish
# spacing a changelog or a growth chart would use.
MILESTONES: tuple[int, ...] = (10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000)


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class StarCount:
    count: int
    checked_at: datetime
    url: str


@dataclass
class Tweet:
    id: str
    text: str
    created_at: datetime
    url: str


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text())


def load_star_count(path: Path | None = None) -> StarCount:
    row = _load_json(path or DEFAULT_STARGAZERS_FIXTURE)
    if not isinstance(row, dict):
        raise ValueError(f"{path}: expected a JSON object, got {type(row).__name__}")
    return StarCount(count=row["count"], checked_at=_parse_ts(row["checked_at"]), url=row["url"])


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = _load_json(path or DEFAULT_TWEETS_FIXTURE)
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
        for r in rows
    ]


def _highest_crossed_milestone(count: int) -> int | None:
    crossed = [m for m in MILESTONES if m <= count]
    return max(crossed) if crossed else None


def _format_variants(n: int) -> list[str]:
    """A round number this size is written both ways in ordinary prose --
    "1000" and "1,000" -- and a regex anchored to only one spelling would
    silently miss an announcement that used the other. Below 1000 there is
    only one spelling to check."""
    plain = str(n)
    if n < 1000:
        return [plain]
    return [plain, f"{n:,}"]


def _find_announcing_tweet(milestone: int, tweets: list[Tweet]) -> Tweet | None:
    patterns = [
        re.compile(r"(?<!\d)" + re.escape(variant) + r"(?!\d)")
        for variant in _format_variants(milestone)
    ]
    for tweet in tweets:
        if "star" not in tweet.text.lower():
            continue
        if any(p.search(tweet.text) for p in patterns):
            return tweet
    return None


def compute_gaps(stars: StarCount, tweets: list[Tweet]) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape every prior recipe's
    `compute_gaps` returns. A count that hasn't crossed the smallest
    tracked milestone yet, or a crossed milestone a tweet already names, is
    excluded, named not hidden; the one case left over -- the highest
    crossed milestone, unannounced -- is surfaced at flat confidence 0.85
    (no age-gate: see module docstring for why)."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    milestone = _highest_crossed_milestone(stars.count)
    if milestone is None:
        excluded.append(GapCandidate(
            slug="no-star-milestone-crossed",
            headline=f"{stars.count} stars has not crossed the first milestone ({MILESTONES[0]})",
            detail=(
                f"Live count is {stars.count}, checked {stars.checked_at.isoformat()}; "
                f"the smallest tracked milestone is {MILESTONES[0]}. No seam here."
            ),
            confidence=0.0,
            evidence=[stars.url],
        ))
        return surfaced, excluded

    tweet = _find_announcing_tweet(milestone, tweets)
    if tweet is not None:
        excluded.append(GapCandidate(
            slug=f"star-milestone-{milestone}-announced",
            headline=f"{milestone} stars was tweeted",
            detail=f"{stars.count} stars crossed the {milestone} milestone; {tweet.url} already names it. No seam here.",
            confidence=0.0,
            evidence=[stars.url, tweet.url],
        ))
        return surfaced, excluded

    surfaced.append(GapCandidate(
        slug=f"star-milestone-{milestone}-not-announced",
        headline=f"{milestone} stars, never announced",
        detail=(
            f"Live count is {stars.count} (checked {stars.checked_at.isoformat()}), "
            f"past the {milestone}-star milestone; no tweet from the connected "
            "account names it."
        ),
        confidence=0.85,
        evidence=[stars.url],
    ))
    return surfaced, excluded


def run_recipe_scan(
    stargazers_path: Path | None = None,
    tweets_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every recipe before
    this one -- `source: "fixture"` is the honest WIP marker this recipe
    carries until the Hand's gateway carries a live `CountStargazers`/
    `GetUserTweets` read wired into the real daily run and these two
    loaders are swapped for real reads. The detection logic does not
    change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    stars = load_star_count(stargazers_path)
    tweets = load_tweets(tweets_path)
    surfaced, excluded = compute_gaps(stars, tweets)
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
