"""The forty-third real seam recipe: an issue reads closed, but its own

GitHub task-list checklist still points at a sub-issue that never did.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads a single local fixture file
(`issues.json`), shaped like what a `ListIssues` call (with bodies
included) would actually return. `ListIssues` already sits on `SCOPES.md`'s
cleared oath table -- no new scope anywhere in this recipe.

The seam: `milestone-closed-issue-still-open` (task 379) already named the
shape for milestone membership -- closing a milestone never touches the
state of a single issue assigned to it, no auto-close wiring at all. A
GitHub task-list checkbox (`- [ ] #N` / `- [x] #N`) inside an issue's own
body is the identical shape one level down: a human (or a god) writes a
checklist declaring what this issue's own sub-work is, closes the parent
believing that work is done, and GitHub's real auto-close trigger never
once looks at a checklist target's own state when the PARENT issue itself
closes (unlike a PR's closing-keyword grammar, which really does fire an
auto-close on the NAMED issue -- the direction here runs backwards: nothing
here claims the checklist item closes anything, only that the parent
claimed IT was done). The seam exists only by holding the closed parent and
the target issue's own live state at the same instant -- neither record
alone shows it.

Deliberately keyed on GitHub's own task-list checkbox syntax, not a bare
`#N` mention anywhere in the body -- a bare mention is `issue-body-dangling-
reference`'s own seam (task 372: does the number even resolve), not this
one's (does the parent's own declared sub-task still sit open). The
checkbox's own checked/unchecked mark is read only to find the reference at
all; whether a target counts as a real gap is decided by the target
issue's own live `state`, not by which box a human ticked -- the identical
"trust the record, not the label" discipline `readme-claims-unfixed-issue`
and this recipe's own milestone sibling both already hold.

Confidence is age-gated on how long the parent has been closed, mirroring
`milestone-closed-issue-still-open`'s 24-hour bar exactly -- see
`recipe.json`'s `confidence_notes` for the full reasoning.

The checkbox grammar itself (`CHECKLIST_RE` / `checklist_targets`) moved to
`seam_engine.checklist` (task 558) the day a second recipe,
`issue-checklist-complete-still-open`, needed the identical parsing for the
mirror-image seam one quadrant over -- the same "reuse the shared module,
not a second retyped copy" discipline `closing_keywords.py` already holds
for the closing-keyword family. Imported here as `_checklist_targets`, its
own pre-existing module-level name, so nothing else in this file changes
shape.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.checklist import checklist_targets as _checklist_targets
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_closed_subissue_still_open" / "issues.json"

# A parent closed under this age may not have had its own checklist swept
# yet -- not yet a gap. Mirrors milestone-closed-issue-still-open's bar.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Issue:
    number: int
    title: str
    state: str
    closed_at: datetime | None
    body: str
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
            number=r["number"], title=r["title"], state=r["state"],
            closed_at=_parse_ts(r["closed_at"]) if r.get("closed_at") else None,
            body=r.get("body", ""), url=r["url"],
        )
        for r in rows
    ]


def compute_gaps(issues: list[Issue], *, now: datetime) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Only CLOSED issues are considered at all -- an issue
    still open has made no "this is done" claim yet, so there is nothing
    for its own checklist to have missed (the same out-of-scope silent skip
    `milestone-closed-issue-still-open` gives an already-closed issue on
    its own side of the seam). A closed issue with no checklist reference
    at all is skipped the same way -- it never claimed a sub-task, so it
    cannot have left one open. Everything left over -- a real checklist
    target this parent's own closed state disagrees with -- is either
    excluded, named not hidden, or surfaced, aged into a confidence score
    `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    by_number = {i.number: i for i in issues}

    for issue in issues:
        if issue.state != "closed":
            continue

        targets = _checklist_targets(issue.body)
        if not targets:
            continue

        seen: set[int] = set()
        for t in targets:
            if t in seen:
                continue
            seen.add(t)

            target = by_number.get(t)
            if target is None:
                excluded.append(GapCandidate(
                    slug=f"checklist-target-not-found-{issue.number}-{t}",
                    headline=f"Issue #{issue.number}'s checklist names #{t}, which does not exist",
                    detail=(
                        f"'{issue.title}' (#{issue.number}) checks off a task-list item for #{t}, "
                        "but no such issue exists. A broken reference, not a resolved promise "
                        "(see issue-body-dangling-reference for that seam)."
                    ),
                    confidence=0.0,
                    evidence=[issue.url],
                ))
                continue

            if target.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{issue.number}-{t}",
                    headline=f"Issue #{issue.number}'s checklist claim about #{t} holds",
                    detail=(
                        f"'{issue.title}' (#{issue.number}) checklists #{t} "
                        f"('{target.title}'); that issue is closed. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[issue.url, target.url],
                ))
                continue

            if issue.closed_at is None:
                excluded.append(GapCandidate(
                    slug=f"issue-closed-no-timestamp-{issue.number}-{t}",
                    headline=f"Issue #{issue.number} closed with no timestamp",
                    detail=(
                        f"'{issue.title}' (#{issue.number}) reads closed but carries no close "
                        "timestamp -- a malformed record, not an unresolved seam."
                    ),
                    confidence=0.0,
                    evidence=[issue.url, target.url],
                ))
                continue

            age_hours = (now - issue.closed_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"issue-closed-subissue-still-open-{issue.number}-{t}",
                headline=(
                    f"Issue #{issue.number} closed, but its own checklist item "
                    f"#{t} is still open"
                ),
                detail=(
                    f"'{issue.title}' (#{issue.number}) closed {issue.closed_at.isoformat()} "
                    f"({age_hours:.1f}h ago); its own task-list still names #{t} "
                    f"('{target.title}'), which is still open."
                ),
                confidence=confidence,
                evidence=[issue.url, target.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(issues_path: Path | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListIssues` read (with bodies) and this loader is swapped for a real
    call. The detection logic does not change when that happens."""
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
