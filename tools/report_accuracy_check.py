#!/usr/bin/env python3
"""Task 679. Esu-Elegba checks the number at the threshold, not just the door.

`check_report_freshness` (`ritual_check.py`) only confirms today's Report
FILE exists; it says nothing about whether the number sealed inside it
still matches what a fresh scan of the live events cache would produce
right now. Caught live this hour: `fencepost/REPORTS/2026-08-11.md` (last
resealed at task 675, commit `9878992`) has read "116 milestone commit(s)"
for the primary `milestone-unannounced` gap ever since -- but a fresh
in-process scan against task 675's OWN committed events-cache snapshot,
run from that exact commit, already computes 111, not 116. The number was
never accurate, not even the hour it was written. Every hour since (676,
677, 678) correctly compared the live scan's slug and confidence against
the last sealed value and logged "primary gap unchanged ... no reseal" --
true of identity, silently untrue of the exact count the shipped, publicly
readable Report keeps repeating. That is the same "self-audit only checked
identity, not the actual number" shape Ogun's law exists to name: a
crying-wolf risk lives just as much in a stale number nobody re-derives as
in a freshly invented false gap.

Pure, no I/O of its own: the caller reads today's report text and hands in
this hour's live scan result (the same `seam_engine.scan` JSON any hourly
dogfood already produces via `--github-events`), mirroring
`--square-state`/`--ci-checks`'s existing "gather the live read, hand it
in" shape rather than this module reaching for the network or the
filesystem itself.

Usage (standalone):
    python3 tools/report_accuracy_check.py check <report.md> <scan-out.json>
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any

_MILESTONE_RE = re.compile(r"(\d+) milestone commit\(s\) since")


def extract_milestone_count(text: str) -> int | None:
    """The exact integer `scan.py`'s own
    `f"{len(milestones)} milestone commit(s) since {...}"` sentence embeds,
    wherever that sentence appears (a rendered Report's markdown body, or a
    raw scan result's `detail` field -- both come from the identical
    f-string, so one regex reads both). `None` if the sentence isn't
    present at all."""
    m = _MILESTONE_RE.search(text)
    return int(m.group(1)) if m else None


def compute_report_accuracy(
    report_text: str | None,
    live_gap: dict[str, Any] | None,
    live_source: str | None = None,
    report_source: str | None = None,
) -> dict[str, Any]:
    """Compare today's committed Report's own milestone-count claim against
    a fresh live scan's `primary_gap`, when both name the same gap
    (`milestone-unannounced`). Informational only -- like
    `check_report_freshness`/`check_metrics_freshness`, a real drift here is
    a fact worth surfacing to the next hour's run, not a currently-live law
    violation, so this never contributes to `ritual_check.py`'s `broken`.

    Every early-out (`report_text` missing, no live scan handed in this
    hour, live scan's primary gap is a different slug, either side's text
    carries no milestone sentence to compare) reads `clean: True` -- absence
    of a comparison is not evidence of drift, the same discipline
    `check_metrics_freshness`'s own gap-in-the-data handling already holds.

    Task 724: caught live this hour, a case the original version got
    backwards. `fencepost/REPORTS/2026-08-13.md` was resealed at 13:05:41Z
    by `seam-scan.yml`'s automatic cron run with `github_events_source:
    "direct"` (a real unproxied `api.github.com` fetch covering the FULL
    history) reading 146 milestone commits. The very next session's own
    live rescan, built from this sandbox's local `github-events-cache.json`
    (`github_events_source: "override"` -- this sandbox's outbound
    `api.github.com` access is 403'd, so every session here has only ever
    been able to grow that cache by small incremental deltas, never a full
    from-scratch fetch) read 135 -- a real, reproducible 11-commit
    undercount, not noise. The pre-existing logic would have called this
    "report is STALE, reseal it" and, followed literally, overwritten an
    already-correct, more-complete 146 with a wrong, smaller 135 -- the
    exact false-negative direction Ogun's law exists to catch, just one
    this checker itself was capable of causing rather than catching.
    `live_source`/`report_source` (both optional, default `None` --
    existing callers that don't pass them keep the exact old behavior)
    let a caller who has both scans' own `github_events_source` field
    name which one produced by the fuller method: a lower live count is
    only ever treated as "cache is behind the already-more-authoritative
    report, do not reseal down" when the currently-sealed report was
    itself `"direct"`-sourced and this hour's live scan was not. Every
    other shape (higher live count in either direction, both sides the
    same source class, source unknown) keeps comparing on the numbers
    alone, exactly as before -- this guard only ever prevents a downgrade,
    never blocks a real reseal upward or a same-source drift catch.
    """
    if report_text is None:
        return {
            "clean": True,
            "reason": "no report text available this hour (missing/pending -- already named by report freshness)",
        }
    if live_gap is None:
        return {"clean": True, "reason": "no live scan handed in this hour -- accuracy unchecked"}
    slug = live_gap.get("slug")
    if slug != "milestone-unannounced":
        return {
            "clean": True,
            "reason": f"live scan's primary gap is {slug!r}, not milestone-unannounced -- nothing to compare",
        }
    report_count = extract_milestone_count(report_text)
    live_count = extract_milestone_count(str(live_gap.get("detail", "")))
    if report_count is None:
        return {"clean": True, "reason": "report text carries no milestone-commit sentence to compare"}
    if live_count is None:
        return {"clean": True, "reason": "live scan's own detail text carries no milestone-commit sentence to compare"}
    if report_count == live_count:
        return {"clean": True, "reason": f"report's {report_count} matches this hour's live scan"}
    if (
        live_count < report_count
        and report_source == "direct"
        and live_source is not None
        and live_source != "direct"
    ):
        return {
            "clean": True,
            "reason": (
                f"report's {report_count} milestone commit(s) ({report_source}-sourced) exceeds this "
                f"hour's {live_count} ({live_source}-sourced) -- the local cache is behind the "
                f"already-more-authoritative direct-sourced report, not the other way around; do NOT "
                f"reseal down"
            ),
            "report_count": report_count,
            "live_count": live_count,
            "cache_behind_direct": True,
        }
    return {
        "clean": False,
        "reason": (
            f"report claims {report_count} milestone commit(s), this hour's live scan of the "
            f"current cache says {live_count} -- report is STALE, reseal it"
        ),
        "report_count": report_count,
        "live_count": live_count,
    }


def _sibling_candidates_source(report_path: str) -> str | None:
    """Task 724: a report at `.../REPORTS/<date>.md` has a sibling
    `.../candidates/<date>.json` one directory over -- read live and
    written by the same scan that sealed the report, carrying the exact
    `github_events_source` ("direct" or "override") that scan used. `None`
    on any miss (different naming, file absent, unparseable) -- the CLI
    then falls back to the old source-blind comparison rather than
    guessing."""
    import os

    reports_dir, filename = os.path.split(report_path)
    root_dir = os.path.dirname(reports_dir)
    candidates_path = os.path.join(root_dir, "candidates", filename.replace(".md", ".json"))
    try:
        with open(candidates_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    source = data.get("github_events_source")
    return source if isinstance(source, str) else None


if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) < 3 or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    with open(argv[1], encoding="utf-8") as f:
        report_text = f.read()
    with open(argv[2], encoding="utf-8") as f:
        scan_result = json.load(f)
    report_source = _sibling_candidates_source(argv[1])
    live_source = scan_result.get("github_events_source")
    out = compute_report_accuracy(
        report_text,
        scan_result.get("primary_gap"),
        live_source=live_source if isinstance(live_source, str) else None,
        report_source=report_source,
    )
    print(out["reason"])
    sys.exit(0 if out["clean"] else 1)
