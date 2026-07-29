"""Seventh real seam recipe: an issue that names itself a duplicate of
another issue, whose original has since closed, while the duplicate itself
still sits open.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads one local fixture file (`issues.json`),
shaped like what `ListIssues`/`GetIssue` would return. Both scopes already
sit on SCOPES.md's cleared oath table -- this recipe asks Arcade for
nothing new.

The seam: a mortal (or a god) marks issue B "duplicate of #A" in its body,
meaning B's own fix arrives however A gets resolved. When A closes, B's own
promise is done too -- but GitHub never closes B automatically just because
its body mentions A (that auto-close wiring only exists for PRs naming a
closing keyword, which is exactly `merged-pr-issue-still-open` and
`issue-closed-pr-still-open`'s seam, not this one's). B is left open,
orphaned, referencing a seam that already closed without it. Neither A
alone nor B alone shows this -- only holding both at once does.

This is the same *shape* of gap `issue-closed-pr-still-open` (task 373)
already watches -- something named a resolution path to a since-closed
issue and never itself closed -- but the *actor* is different (an issue
marking a duplicate, not a PR naming a closing keyword) and GitHub gives
this one no auto-close mechanism at all, not even a broken one: a duplicate
marker is pure prose, so this gap can persist forever with no trigger ever
having existed to fire.

Confidence is age-gated on how long the original has been closed while the
duplicate still sits open -- see `recipe.json`'s `confidence_notes` for the
full reasoning behind the 24-hour bar.
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
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "duplicate_issue_still_open" / "issues.json"

# "Duplicate of #700" / "dup of #703" / "Duplicate: #705" / "duplicate #705"
# all match. A `\b` boundary right after "dup" rules out "dupe"/"duping" so
# a false positive on ordinary prose never becomes a candidate at all -- the
# same "no fuzzy matching to misfire on" discipline every recipe before this
# one holds.
_DUP_RE = re.compile(r"\bdup(?:licate)?\s*(?:of|:)?\s+#(\d+)\b", re.IGNORECASE)

# An original closed under this age may not have been noticed yet by
# whoever filed the duplicate -- not yet a gap.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Issue:
    number: int
    title: str
    state: str
    body: str
    closed_at: datetime | None
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
            number=r["number"], title=r["title"], state=r["state"], body=r.get("body", ""),
            closed_at=_parse_ts(r["closed_at"]) if r.get("closed_at") else None,
            url=r["url"],
        )
        for r in rows
    ]


def _named_duplicate_of(body: str) -> int | None:
    match = _DUP_RE.search(body)
    return int(match.group(1)) if match else None


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def compute_gaps(
    issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Only issues still in the `open` state are considered at
    all -- an issue that closed itself (whether via the duplicate marking
    or any other route) has no gap left to surface, the ordinary,
    unremarkable case. An open issue is excluded, named not hidden, the
    moment it names no duplicate marker, names an original this fixture
    doesn't carry at all, or names an original that is itself still open
    (no seam yet -- there is nothing for this issue to have missed).
    Everything left over -- an open issue whose named original already
    closed -- is surfaced, aged into a confidence score `rank()` can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for issue in issues:
        if issue.state != "open":
            continue

        number = _named_duplicate_of(issue.body)
        if number is None:
            excluded.append(GapCandidate(
                slug=f"no-duplicate-marker-{issue.number}",
                headline=f"Issue #{issue.number} names no duplicate marker",
                detail=f"'{issue.title}' is open with no 'duplicate of #N' reference. No seam here.",
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        original = _find_issue(number, issues)
        if original is None or original.state != "closed" or original.closed_at is None:
            excluded.append(GapCandidate(
                slug=f"original-still-open-{issue.number}-{number}",
                headline=f"Issue #{issue.number}'s named original #{number} is still open",
                detail=f"'{issue.title}' names #{number} as its original; that issue has not closed yet. No seam here.",
                confidence=0.0,
                evidence=[issue.url] + ([original.url] if original else []),
            ))
            continue

        age_hours = (now - original.closed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"duplicate-issue-still-open-{issue.number}-{number}",
            headline=f"Issue #{issue.number} names #{number} as its original, which already closed",
            detail=(
                f"'{issue.title}' names #{number} ('{original.title}') as its original, "
                f"closed {original.closed_at.isoformat()} ({age_hours:.1f}h ago). "
                f"The duplicate still reads open."
            ),
            confidence=confidence,
            evidence=[issue.url, original.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListIssues` read and this one loader is swapped for a real read. The
    detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(issues, now=now)
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
