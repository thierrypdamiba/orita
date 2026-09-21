"""The hundred-thirteenth real seam recipe: the README's own hardcoded
prose star-count claim ("900+ stars", "⭐ 900 GitHub stars") has fallen
behind the live count -- a number a human typed by hand once, that nothing
on either platform ever comes back to update.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files
(``readme.json``, ``stargazers.json``), shaped like what ``GetFileContents``
(read the README at its current HEAD) and ``CountStargazers`` would
actually return. Neither scope is new -- both already sit on ``SCOPES.md``'s
cleared oath table (``GetFileContents`` reads
``example-release-vs-changelog``'s own ``CHANGELOG.md``; ``CountStargazers``
reads ``../star-milestone-not-announced/``'s own live count). No new scope
is asked for anywhere in this recipe.

Distinct from the closest sibling, ``../star-milestone-not-announced/``:
that recipe watches whether a crossed round-number star threshold (10, 100,
1000, ...) ever got announced in a tweet -- an EVENT that may or may not
have been spoken. This recipe watches a different seam entirely: a number
already written down, in prose, inside the README itself, that the live
count has since outgrown -- a STATEMENT that used to be true and quietly
stopped being. A repo can cross a round-number milestone with a live tweet
announcing it (satisfying the sibling recipe) while its own README still
says "900+ stars" underneath a live count of 1400 -- two entirely
independent gaps, on two entirely independent surfaces, neither implying
the other.

A trailing ``+`` on a claimed number ("900+ stars") is read as an
at-least claim, not an exact one -- it is not exempted outright, but the
threshold below only surfaces a gap once the live count has moved a real
distance past even a ``+``-qualified claim, so an honest "at least 900"
sitting under a live count of 910 is correctly left alone.
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
DEFAULT_README_FIXTURE = _HERE.parents[1] / "fixtures" / "readme_star_count_stale" / "readme.json"
DEFAULT_STARGAZERS_FIXTURE = _HERE.parents[1] / "fixtures" / "readme_star_count_stale" / "stargazers.json"

# Matches "900 stars", "900+ stars", "⭐ 900 GitHub stars", "900 ⭐" -- a
# star emoji or the word "star(s)" sitting within a few characters of a
# plain integer (commas allowed), captured with its own optional trailing
# '+'. Two directions (number-then-word, word-then-number) because README
# prose writes both ways in the wild.
_STAR_CLAIM_RE = re.compile(
    r"(?:⭐️?\s*)?(\d[\d,]*)(\+?)\s*(?:⭐️?\s*)?(?:GitHub\s+)?stars?\b",
    re.IGNORECASE,
)


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _parse_int(digits: str) -> int:
    return int(digits.replace(",", ""))


@dataclass
class ReadmeFile:
    path: str
    text: str
    url: str


@dataclass
class StarCount:
    count: int
    checked_at: datetime
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_readme_files(path: Path | None = None) -> list[ReadmeFile]:
    """Read-only: load README-shaped rows from the fixture (or a real
    ``GetFileContents`` read of the same shape, once this recipe's scopes
    graduate off the fixture)."""
    rows = _load_rows(path or DEFAULT_README_FIXTURE)
    return [ReadmeFile(path=r["path"], text=r["text"], url=r["url"]) for r in rows]


def load_star_count(path: Path | None = None) -> StarCount:
    raw = json.loads(Path(path or DEFAULT_STARGAZERS_FIXTURE).read_text())
    return StarCount(count=raw["count"], checked_at=_parse_ts(raw["checked_at"]), url=raw["url"])


def _staleness_threshold(claimed: int) -> int:
    """The minimum (live - claimed) gap this recipe treats as a real,
    surfaceable staleness -- never a one- or two-star clock-skew flag.
    Matches ``star-milestone-not-announced``'s own discipline of never
    crying wolf over ordinary noise: a flat floor of 25 stars, or 5% of the
    claimed number, whichever is larger, so a small repo's small claim
    still gets a proportionate bar rather than always needing 25 stars of
    drift to ever surface at all."""
    return max(25, round(claimed * 0.05))


def compute_gaps(
    readmes: list[ReadmeFile], star_count: StarCount
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    ``compute_gaps``. Only the FIRST star-count claim found in each
    README's text is evaluated -- a file repeating the same claim twice
    names one gap, not two."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for r in readmes:
        match = _STAR_CLAIM_RE.search(r.text)
        if not match:
            excluded.append(GapCandidate(
                slug=f"readme-no-star-claim-{r.path}",
                headline=f"'{r.path}' makes no hardcoded star-count claim -- not a gap",
                detail=f"{r.path} carries no prose sentence naming a star count. Nothing to compare.",
                confidence=0.0,
                evidence=[r.url],
            ))
            continue

        claimed = _parse_int(match.group(1))
        is_at_least = match.group(2) == "+"
        threshold = _staleness_threshold(claimed)

        if star_count.count <= claimed:
            # Live count has not moved past the claim at all.
            excluded.append(GapCandidate(
                slug=f"readme-star-claim-current-{r.path}",
                headline=f"'{r.path}' claims {claimed}{'+' if is_at_least else ''} stars, live count is {star_count.count} -- still true",
                detail=(
                    f"{r.path} claims {claimed}{'+' if is_at_least else ''} stars; the live "
                    f"count ({star_count.count}) has not moved meaningfully past it."
                ),
                confidence=0.0,
                evidence=[r.url, star_count.url],
            ))
            continue

        drift = star_count.count - claimed
        if drift < threshold:
            excluded.append(GapCandidate(
                slug=f"readme-star-claim-within-tolerance-{r.path}",
                headline=f"'{r.path}' claims {claimed}{'+' if is_at_least else ''} stars, live count is {star_count.count} -- drift under the noise floor",
                detail=(
                    f"{r.path} claims {claimed}{'+' if is_at_least else ''} stars; live count "
                    f"{star_count.count} is only {drift} above it, under this recipe's own "
                    f"{threshold}-star staleness floor."
                ),
                confidence=0.0,
                evidence=[r.url, star_count.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"readme-star-count-stale-{r.path}",
            headline=f"'{r.path}' still says {claimed}{'+' if is_at_least else ''} stars -- live count is {star_count.count}",
            detail=(
                f"{r.path} claims {claimed}{'+' if is_at_least else ''} stars in prose; the "
                f"live count is now {star_count.count}, {drift} past the claim. Nothing on "
                "either platform ever flags a hand-typed number as it goes stale."
            ),
            confidence=0.7,
            evidence=[r.url, star_count.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    readme_path: Path | None = None,
    stargazers_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's ``entrypoint``. Same output shape as every prior
    recipe's ``run_recipe_scan`` -- ``source: "fixture"`` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    ``GetFileContents``/``CountStargazers`` read and these two loaders are
    swapped for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    readmes = load_readme_files(readme_path)
    star_count = load_star_count(stargazers_path)
    surfaced, excluded = compute_gaps(readmes, star_count)
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
