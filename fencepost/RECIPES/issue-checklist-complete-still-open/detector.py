"""Forty-sixth real seam recipe (ROADMAP.md #558, issue #7's own "good
first issue"): an issue's own GitHub task-list checklist has every named
target closed, and the issue itself never did.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads a single local fixture file (`issues.json`),
shaped like what a `ListIssues` call (with bodies) would actually return.
`ListIssues` already sits on `SCOPES.md`'s cleared oath table -- no new scope
anywhere in this recipe.

The seam: `milestone-complete-still-open` (task 493) already named this shape
for milestone membership -- a milestone's own `open_issues` count hits zero
and nothing ever closes the milestone itself, because GitHub tracks
completion but never wrap-up. `issue-closed-subissue-still-open` (task 530)
named the mirror-image seam one level down at the issue-checklist layer: a
CLOSED parent whose own checklist still points at an OPEN target. This
recipe is the missing third quadrant: an issue's own checklist (`- [ ] #N` /
`- [x] #N` in its body) names one or more other issues, every one of them is
now closed, and the parent issue -- the one that made the checklist promise
-- is still open. GitHub never auto-closes a parent when the last checklist
target closes (unlike a PR's real closing-keyword grammar, which really does
fire an auto-close on the issue it names); closing the parent is always a
separate, manual, forgettable step. The seam exists only by holding the
parent's own live `state` and every target's own live `state` at the same
instant -- neither the parent's body alone nor any single target's record
shows it.

Deliberately keyed on GitHub's own task-list checkbox syntax, not a bare
`#N` mention anywhere in the body -- identical discipline to
`issue-closed-subissue-still-open`: a bare mention is
`issue-body-dangling-reference`'s own seam, not this one's. The checkbox's
own checked/unchecked mark is read only to find the reference at all --
whether a target counts as done is decided by the target issue's own live
`state`, never by which box a human ticked, the same "trust the record, not
the label" discipline every sibling in this family already holds.

A checklist target that does not exist at all makes the parent's own
completeness claim unverifiable -- rather than guess, this recipe excludes
the whole parent, named not hidden, and surfaces nothing (Ògún's law:
false positives are the whole ballgame, so an ambiguous case is withheld,
not guessed into a gap). A parent with at least one checklist target still
open is excluded too -- not complete yet, nothing missed. Confidence on a
genuinely complete-but-open parent is age-gated on the parent's own
`updated_at`, mirroring `milestone-complete-still-open`'s 24-hour bar
exactly, since neither a milestone nor an issue carries a real
"went-complete-at" timestamp -- `updated_at` is the closest real signal
either object exposes.

The checkbox grammar itself (`checklist_targets`) lives in
`seam_engine.checklist`, shared with `issue-closed-subissue-still-open`
rather than a second retyped copy -- the same "one real source" discipline
`closing_keywords.py` already holds for the closing-keyword family. That
shared function keeps duplicates (the same target named twice is two real
matches, not one deduplicated fact); THIS recipe's own completeness check
needs the distinct set, so deduplication happens locally in
`compute_gaps`, at the call site, not inside the shared grammar.
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
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_checklist_complete_still_open" / "issues.json"

# A parent whose checklist went all-closed under this age may not have had
# its own wrap-up noticed yet -- mirrors milestone-complete-still-open's bar.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Issue:
    number: int
    title: str
    state: str
    body: str
    updated_at: datetime
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
            body=r.get("body", ""), updated_at=_parse_ts(r["updated_at"]),
            url=r["url"],
        )
        for r in rows
    ]


def compute_gaps(issues: list[Issue], *, now: datetime) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Only OPEN issues are candidates at all -- a closed
    parent has already resolved its own state, so there is nothing this
    recipe watches left to miss (the same out-of-scope silent skip
    `issue-closed-subissue-still-open` gives a still-open parent on its own
    side of the seam). An open issue with no checklist reference at all is
    skipped the same way -- it never made a completeness promise, so it
    cannot have left one unfulfilled."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    by_number = {i.number: i for i in issues}

    for issue in issues:
        if issue.state != "open":
            continue

        raw_targets = _checklist_targets(issue.body)
        if not raw_targets:
            continue

        # This recipe's own completeness check needs the DISTINCT set of
        # named targets, not the raw occurrence count -- `_checklist_targets`
        # (shared `seam_engine.checklist`) deliberately keeps duplicates, so
        # dedup happens here, at this call site, preserving first-seen order.
        targets: list[int] = []
        for t in raw_targets:
            if t not in targets:
                targets.append(t)

        broken = [t for t in targets if t not in by_number]
        if broken:
            excluded.append(GapCandidate(
                slug=f"checklist-target-not-found-{issue.number}",
                headline=(
                    f"Issue #{issue.number}'s checklist names "
                    f"{', '.join(f'#{t}' for t in broken)}, which do{'es' if len(broken) == 1 else ''} not exist"
                ),
                detail=(
                    f"'{issue.title}' (#{issue.number}) checks off a task-list item "
                    f"for {', '.join(f'#{t}' for t in broken)}, but no such issue "
                    "exists. Its own completeness claim can't be verified, so it is "
                    "withheld rather than guessed at -- a broken reference, not a "
                    "resolved (or unresolved) promise (see "
                    "issue-body-dangling-reference for that seam)."
                ),
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        targets_state = [by_number[t] for t in targets]
        still_open = [t for t in targets_state if t.state != "closed"]
        if still_open:
            excluded.append(GapCandidate(
                slug=f"not-complete-{issue.number}",
                headline=(
                    f"Issue #{issue.number}'s checklist still has "
                    f"{len(still_open)} open item(s)"
                ),
                detail=(
                    f"'{issue.title}' (#{issue.number}) checklists "
                    f"{len(targets_state)} issue(s); "
                    f"{', '.join(f'#{t.number}' for t in still_open)} still "
                    "read open. Not complete yet -- nothing missed by leaving the "
                    "parent open."
                ),
                confidence=0.0,
                evidence=[issue.url] + [t.url for t in still_open],
            ))
            continue

        age_hours = (now - issue.updated_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"issue-checklist-complete-still-open-{issue.number}",
            headline=(
                f"Issue #{issue.number} ('{issue.title}')'s checklist is all "
                "checked off, but the issue itself never closed"
            ),
            detail=(
                f"'{issue.title}' (#{issue.number}) names "
                f"{', '.join(f'#{t.number}' for t in targets_state)} in its own "
                f"task-list checklist; every one of them is now closed. The "
                f"parent last changed {issue.updated_at.isoformat()} "
                f"({age_hours:.1f}h ago) and still reads open. Closing the parent "
                "is always a separate manual step -- GitHub never auto-closes an "
                "issue when the last item on its own checklist does."
            ),
            confidence=confidence,
            evidence=[issue.url] + [t.url for t in targets_state],
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
