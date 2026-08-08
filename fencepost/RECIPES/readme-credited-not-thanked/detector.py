"""Fifteenth real seam recipe: a contributor already credited in the repo's
own README, whose handle has never once been thanked in a tweet from the
connected X account.

The deliberate inverse of `RECIPES/contributor-thanked-not-credited/`
(task 371): that recipe watches a tweet thanking a handle the README does
not yet credit; this one watches the exact opposite direction of the same
two-toolkit seam -- a handle the README ALREADY credits that X has never
once thanked. Read-only in spirit, MOCK ONLY in practice, same as every
recipe before this one: this module only ever reads two local fixture
files (`readme.json`, `tweets.json`), shaped like what a read-only
`GetFileContents` call on this repo's own README and `GetUserTweets` would
actually return. Both scopes already sit on SCOPES.md's cleared oath
table -- no new scope needed.

Confidence is gated DIFFERENTLY from the twin recipe on purpose, not a
copy-pasted number with the label changed. The twin ages its decision
against a fixed 72h window since the thank-you TWEET itself. This recipe
has no equivalent per-contributor date to age against -- a real
`GetFileContents` read returns the README's CURRENT text, not a change
history, so there is no "when was this credit added" timestamp available
to gate on. Two different, genuinely-motivated signals stand in instead:

1. **Coverage.** `_COVERAGE_WINDOW_HOURS = 96.0` -- how far back the read
   tweet history reaches (oldest tweet's own `created_at` to `now`). A
   short read window is weak evidence of a real silence (the account may
   simply not have posted much yet); a long one is strong evidence. Wider
   than the twin's 72h on purpose: absence-of-evidence needs a longer bar
   to trust than presence-of-a-real-tweet's own lag does.
2. **Total silence vs mere non-thanks.** A credited handle that appears
   ANYWHERE in the tweet text, even without thanks-shaped language (a bare
   `@mention`), is treated as a weaker signal than a handle that never
   appears at all -- a human maintainer who has already mentioned someone
   is plausibly aware of them and simply hasn't phrased a thank-you yet;
   total silence is the stronger tell.

Only credited handles inside the README's own "## Thanks" section are ever
considered -- a repo's README commonly lists OTHER `@handle`-shaped bullets
for unrelated reasons (this one's own fixture includes a "## Houses"
section naming gods by handle, on purpose, to prove the section-scoping
actually holds and doesn't just get lucky on a small fixture).
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate
from seam_engine.thanks import THANKS_RE, thanked_handle

_HERE = Path(__file__).resolve().parent
DEFAULT_README_FIXTURE = _HERE.parents[1] / "fixtures" / "readme_credited_not_thanked" / "readme.json"
DEFAULT_TWEETS_FIXTURE = _HERE.parents[1] / "fixtures" / "readme_credited_not_thanked" / "tweets.json"

# How far back the read tweet history must reach before a credited
# handle's total silence is trusted as a real gap rather than "we simply
# haven't read enough history yet." Wider than the twin recipe's 72h
# credit-lag window on purpose -- see module docstring, point 1.
_COVERAGE_WINDOW_HOURS = 96.0

# Requires "thank(s)" or "thank you", loosely followed by an @handle, in the
# same tweet -- shared with contributor-thanked-not-credited's own
# `_THANKS_RE` via `seam_engine.thanks` (task 396), since it answers the
# same question ("is this tweet a thank-you"), just applied across the
# whole tweet history here instead of to one tweet at a time.
_THANKS_RE = THANKS_RE

# Isolates the README's own "## Thanks" section body, from that heading up
# to (but not including) the next "## " heading or end of string -- so a
# bare `@handle`-shaped bullet elsewhere in the README (this fixture's own
# "## Houses" section, on purpose) is never even read as a credit.
_THANKS_SECTION_RE = re.compile(r"^## Thanks\b(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)

# A credited bullet inside that section: "- @handle ...".
_CREDIT_LINE_RE = re.compile(r"^-\s*@(\w[\w-]*)", re.MULTILINE)


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


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


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = _load_rows(path or DEFAULT_TWEETS_FIXTURE)
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
        for r in rows
    ]


def load_readme(path: Path | None = None) -> str:
    """Load the whole-file `{"path": ..., "content": ...}` shape a
    `GetFileContents` call returns, refusing a syntactically valid but
    wrong-shaped payload with a named error -- same discipline as the
    twin recipe's own `load_readme` and every other loader in this engine."""
    p = path or DEFAULT_README_FIXTURE
    data = json.loads(p.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{p}: expected a JSON object, got {type(data).__name__}")
    content = data.get("content")
    if not isinstance(content, str):
        raise ValueError(f"{p}: expected a string 'content' field")
    return content


def credited_handles(readme_content: str) -> list[str]:
    """Every handle credited inside the README's own "## Thanks" section,
    in the order they first appear. A README with no such section at all
    credits nobody -- empty list, not an error; there is simply nothing to
    check. `dict.fromkeys` dedupes, order-preserving: a handle credited
    twice (a duplicate bullet from a merge, or crediting someone for two
    separate contributions) must not produce two identical `GapCandidate`s
    that tie each other out of `rank()`'s `SEPARATION_MARGIN` -- the exact
    false-negative shape task 442 already fixed for the four
    `*-dangling-reference` recipes, unswept here until now."""
    match = _THANKS_SECTION_RE.search(readme_content)
    if not match:
        return []
    return list(dict.fromkeys(_CREDIT_LINE_RE.findall(match.group(1))))


def _thanked_handles(tweets: list[Tweet]) -> set[str]:
    """Every handle ever thanked, across the WHOLE read tweet history --
    unlike the twin recipe, which asks this per tweet, this recipe asks it
    once, across every tweet, since what matters here is whether a thank-you
    ever happened at all, not which single tweet it came from."""
    # Task 610 (Kwaku Ananse): used to re-run `_THANKS_RE.search` here
    # directly instead of calling the shared `thanked_handle` -- the same
    # regex, reused, but the negation-scope check that function now holds
    # ("no thanks @handle" is a decline, not credit) never reached this
    # detector, because this loop never called the function it lives in.
    # See `seam_engine.thanks`'s own docstring for the live reproduction;
    # see the twin recipe's `_thanked_handle` for the mirror fix.
    thanked: set[str] = set()
    for tweet in tweets:
        handle = thanked_handle(tweet.text)
        if handle:
            thanked.add(handle.lower())
    return thanked


def _mentioned_anywhere(handle: str, tweets: list[Tweet]) -> bool:
    pattern = re.compile(r"@" + re.escape(handle) + r"(?![\w-])", re.IGNORECASE)
    return any(pattern.search(tweet.text) for tweet in tweets)


def compute_gaps(
    handles: list[str], tweets: list[Tweet], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every recipe before this
    one. A credited handle already thanked is named in `excluded`, not
    hidden. Every never-thanked handle is surfaced, ranked by the two-factor
    confidence described in the module docstring -- total silence past the
    coverage window scores highest; a mere non-thanks mention, or too short
    a read window, scores lower but is still shown, never dropped."""
    thanked = _thanked_handles(tweets)
    oldest = min((t.created_at for t in tweets), default=now)
    coverage_hours = (now - oldest).total_seconds() / 3600.0
    coverage_sufficient = coverage_hours >= _COVERAGE_WINDOW_HOURS

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for handle in handles:
        lower = handle.lower()
        if lower in thanked:
            excluded.append(GapCandidate(
                slug=f"readme-handle-already-thanked-{handle}",
                headline=f"@{handle} has already been thanked",
                detail=f"@{handle} is credited in the README and has already been thanked in a tweet. No seam here.",
                confidence=0.0,
                evidence=[],
            ))
            continue

        mentioned = _mentioned_anywhere(handle, tweets)
        if mentioned:
            confidence = 0.5
            detail = (
                f"@{handle} is credited in the README's Thanks section; the account has "
                f"mentioned them ({coverage_hours:.1f}h of tweet history read) but never in "
                "thanks-shaped language."
            )
        elif coverage_sufficient:
            confidence = 0.85
            detail = (
                f"@{handle} is credited in the README's Thanks section; {coverage_hours:.1f}h "
                "of tweet history read (past the coverage bar), and the handle never appears "
                "in any tweet at all."
            )
        else:
            confidence = 0.5
            detail = (
                f"@{handle} is credited in the README's Thanks section; only {coverage_hours:.1f}h "
                "of tweet history read so far (below the coverage bar) -- too little history yet "
                "to trust the silence."
            )

        surfaced.append(GapCandidate(
            slug=f"readme-credited-not-thanked-{handle}",
            headline=f"@{handle} is credited in the README, never thanked on X",
            detail=detail,
            confidence=confidence,
            evidence=[],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    readme_path: Path | None = None,
    tweets_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every recipe before
    this one -- `source: "fixture"` is the honest WIP marker until the Hand's
    gateway carries a live `GetFileContents` read and these two loaders are
    swapped for real calls. The detection logic does not change when it
    does."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    readme_content = load_readme(readme_path)
    tweets = load_tweets(tweets_path)
    handles = credited_handles(readme_content)
    surfaced, excluded = compute_gaps(handles, tweets, now=now)
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
