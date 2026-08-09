"""The sixty-first real seam recipe: an issue that names itself blocked by
another issue, whose named blocker has since closed, while the blocked
issue itself was never revisited.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads one local fixture file (`issues.json`),
shaped like what `ListIssues`/`GetIssue` would return. Both scopes already
sit on SCOPES.md's cleared oath table -- this recipe asks Arcade for
nothing new.

The seam: a mortal (or a god) marks issue B "blocked by #A" (or "blocked on
#A") in its own body, meaning B's own work cannot start, or cannot finish,
until A is done. When A closes, B's own dependency clears -- but GitHub
never revisits B just because A closed; nothing anywhere flags that a
blocked issue's blocker is now gone. B is left open, its own stated reason
for waiting already resolved, with nobody having come back to check.

This is a close cousin of `duplicate-issue-still-open` (the same
self-declared, pure-prose marker shape, the same "no auto-close mechanism
exists for this at all" absence), but the claim itself is genuinely
different, not a rename of the same one. A duplicate marker claims
EQUIVALENCE -- B is the same report as A, so closing A really should close
B too, and that recipe's own gap is exactly that missed close. A blocker
marker claims only a DEPENDENCY -- B is not the same work as A, it was
simply waiting on A, and closing A does not mean B is done; it means B's
own work just became possible again. This recipe never claims B should be
closed (that would be `duplicate-issue-still-open`'s seam, wrongly
reused) -- it claims only that a fact B's own body asserts (I am blocked
by A) has quietly stopped being true, and nothing on either record shows
that anyone noticed. The no-grading law applies exactly as it does to
every sibling: the headline names the two issue numbers and the closed
blocker's own timestamp, never a person, never a team, never a "should
have."

Confidence is age-gated on how long the blocker has been closed while the
blocked issue still sits open -- see `recipe.json`'s `confidence_notes` for
the full reasoning behind reusing `duplicate-issue-still-open`'s own
24-hour bar rather than inventing a new number for a structurally similar
self-declared-prose-marker family.

Deliberately keeps its own `_named_blocker_of`/`BLOCKER_MARKER_RE` here
rather than importing `seam_engine.duplicate_markers`: that module's own
grammar ("duplicate of #N" / "dup of #N") is a different claim on purpose,
not a spelling variant of this one, so importing it and re-purposing it
would silently blur the two seams this docstring just spent a paragraph
telling apart. This is the FIRST recipe to read a "blocked by/on #N"
marker -- the same "write it here first, extract to a shared module only
once a second recipe needs the identical grammar" discipline
`duplicate_markers.py`'s and `closing_keywords.py`'s own module docstrings
already describe for their own first user.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.negation import is_negated
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "unblocked_issue_still_open" / "issues.json"

# "Blocked by #900" / "blocked on #903" / "Blocked: #905" / "blocked #905"
# all match, mirroring `seam_engine.duplicate_markers.DUPLICATE_MARKER_RE`'s
# own shape for a genuinely different claim word. The leading `\b` means
# "unblocked #N" (a real, opposite-meaning word that contains "blocked" as
# a literal substring) never matches -- there is no word boundary between
# "un" and "blocked" for `\b` to catch, so this never fires on it.
BLOCKER_MARKER_RE = re.compile(r"\bblocked\s*(?:by|on|:)?\s+#(\d+)\b", re.IGNORECASE)

# A negation word sitting in front of "blocked" turns a genuine-looking
# marker into an explicit denial -- "This is not blocked by #10 anymore",
# "No longer blocked by #10" -- the exact false-positive shape task 612
# fixed for `duplicate_markers.py`'s own "duplicate of #N" marker: an
# unnegated claim must not survive across a nearby negation. Reproduced
# live before this fix: `_named_blocker_of("This is not blocked by #10
# anymore, we are good to go.")` returned `10` -- a body that explicitly
# denies still being blocked was read as naming a live blocker anyway,
# which would surface a false "unblocked-issue-still-open" gap the moment
# #10 itself happened to be closed. `_NEGATION_PREFIX_WINDOW` mirrors
# `duplicate_markers.py`'s own 16-char window -- enough slack for "isn't
# ", "is not ", or "no longer " sitting directly in front of "blocked"
# without reaching back far enough to catch an unrelated earlier negation.
_NEGATION_PREFIX_WINDOW = 16

# A blocker closed under this age may not have been noticed yet by whoever
# is waiting on it -- not yet a gap. Matches duplicate-issue-still-open's
# and overdue-milestone-still-open's own bar rather than inventing a new
# number for a structurally similar family.
_STALE_HOURS = 24.0


def _named_blocker_of(body: str) -> int | None:
    """The number named as this body's own blocker, or None if it names no
    (unnegated) blocker marker at all. A blocker marker whose immediately
    preceding words negate it ("not blocked by #10 anymore", "no longer
    blocked by #10") is skipped, and the search continues to the next
    candidate -- see this module's own comment above `_NEGATION_PREFIX_
    WINDOW` for the live reproduction."""
    for match in BLOCKER_MARKER_RE.finditer(body):
        if is_negated(body, match.start(), _NEGATION_PREFIX_WINDOW):
            continue
        return int(match.group(1))
    return None


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
    all -- an issue that closed itself has no gap left to surface, whatever
    its body once claimed about a blocker. An open issue is excluded, named
    not hidden, the moment it names no blocker marker, names a blocker this
    fixture doesn't carry at all, or names a blocker that is itself still
    open (no seam yet -- there is nothing this issue has missed). A
    blocker that reads closed but carries no close timestamp is excluded
    as malformed, not folded into "still open" -- the two are different
    facts about the world. Everything left over -- an open issue whose
    named blocker already closed, with a real timestamp -- is surfaced,
    aged into a confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for issue in issues:
        if issue.state != "open":
            continue

        number = _named_blocker_of(issue.body)
        if number is None:
            excluded.append(GapCandidate(
                slug=f"no-blocker-marker-{issue.number}",
                headline=f"Issue #{issue.number} names no blocker marker",
                detail=f"'{issue.title}' is open with no 'blocked by #N' reference. No seam here.",
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        blocker = _find_issue(number, issues)
        if blocker is None:
            excluded.append(GapCandidate(
                slug=f"nonexistent-blocker-{issue.number}-{number}",
                headline=f"Issue #{issue.number} names #{number} as its blocker, which does not exist in this repo",
                detail=(
                    f"'{issue.title}' names #{number} as its blocker, but no such issue "
                    "exists. A broken link, not a broken promise."
                ),
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        if blocker.state != "closed":
            excluded.append(GapCandidate(
                slug=f"blocker-still-open-{issue.number}-{number}",
                headline=f"Issue #{issue.number}'s named blocker #{number} is still open",
                detail=f"'{issue.title}' names #{number} as its blocker; that issue has not closed yet. No seam here.",
                confidence=0.0,
                evidence=[issue.url, blocker.url],
            ))
            continue

        if blocker.closed_at is None:
            excluded.append(GapCandidate(
                slug=f"blocker-closed-no-timestamp-{issue.number}-{number}",
                headline=f"Issue #{issue.number}'s named blocker #{number} closed with no timestamp",
                detail=(
                    f"'{issue.title}' names #{number} as its blocker; that issue reads closed but "
                    "carries no close timestamp -- a malformed record, not an unresolved seam."
                ),
                confidence=0.0,
                evidence=[issue.url, blocker.url],
            ))
            continue

        age_hours = (now - blocker.closed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"unblocked-issue-still-open-{issue.number}-{number}",
            headline=f"Issue #{issue.number} names #{number} as its blocker, which already closed",
            detail=(
                f"'{issue.title}' names #{number} ('{blocker.title}') as its blocker, "
                f"closed {blocker.closed_at.isoformat()} ({age_hours:.1f}h ago). "
                f"The blocked issue still reads open."
            ),
            confidence=confidence,
            evidence=[issue.url, blocker.url],
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
