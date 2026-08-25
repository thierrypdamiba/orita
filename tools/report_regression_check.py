#!/usr/bin/env python3
"""Task 773. Kwaku-Ananse checks that the story doesn't quietly walk itself back.

Every sealed `fencepost/REPORTS/<date>.md` that names the
`milestone-unannounced` gap phrases its number as a running total: "N
milestone commit(s) since 2026-07-12". A count framed "since a fixed date"
reads as cumulative to anyone following the daily arc -- merged commits
don't un-merge, so day N+1's number should never read lower than day N's.

An honest Explore sweep of this remit (the daily Report cadence, the
serialized arc, the n-1 counter) found TWO places across all 32 sealed
tablets where that promise silently broke, both in the town's first
week: `2026-07-12.md` read 13, the very next tablet `2026-07-13.md` read
11; then `2026-07-13.md`'s 11 fell again to `2026-07-18.md`'s 4 (the
three days between, 07-15/16/17, sealed a different gap that day and
carry no milestone sentence at all -- see `read_report_counts`).
`fencepost/AUDIT.md` grades every one of these entries CONFIRMED because
it only checks a single day's own confidence bar/margin/evidence, never a
day's number against the day before it -- so both dips shipped,
unnoticed, for over a month.

Investigating rather than assuming: `scan.py`'s own `account_live_since`
is derived from `min(x_post_objs.ts)` (see `run_scan`), not a hardcoded
constant -- only its *date* is rendered in the report text ("since
2026-07-12"), never its time-of-day. Two tablets can both legitimately
print "since 2026-07-12" while the real cutoff moment shifted later
within that same day between scans, silently excluding milestone commits
that had counted the day before. `scan.py`'s own history (see the
`check_prior_milestones` note) already names and closes the same bug
SHAPE for a later, more visible instance (2026-07-18 -> 2026-07-19,
evidence vanishing outright, caught and fixed live on task 128/task-19)
-- both of these are that bug's earlier, smaller, never-written-up
occurrences, from before the fix matured. `X_PostTweet`/`X_GetUserTweets`
have been forbidden since 2026-07-14 (`tools/x_outage_tracker.py`'s own
log), so neither drop can be explained by a real announcement legitimately
retiring milestone commits from the "still unannounced" pool either.

This checker doesn't rewrite sealed history (the Ledger's own append-only
law: "edit it and the seal breaks") and doesn't reach for the network --
it reads every already-sealed `fencepost/REPORTS/*.md` in date order,
extracts each day's milestone-commit count via
`report_accuracy_check.extract_milestone_count` (the one place that
pattern is allowed to live -- `duplicate_regex_check.py`'s own doctrine),
and flags any day-over-day decrease that isn't already named in
`SEEDED_EXCEPTIONS` below. A future undocumented regression fails loud;
the one historical case stays documented, not silently exempted.

Usage:
    python3 tools/report_regression_check.py check
"""
from __future__ import annotations

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REPORTS_DIR = os.path.join(ROOT, "fencepost", "REPORTS")

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
import report_accuracy_check  # noqa: E402

_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")

# Every known, already-explained day-over-day drop in the sealed
# milestone-commit count, as (from_date, to_date). Explained in this
# module's own docstring above -- NOT in fencepost/AUDIT.md (task 1002
# corrected this comment: AUDIT.md is regenerated in full by
# `seam_engine.audit --write` every day, straight off the Ledger, and its
# own docstring says so -- "never hand-edited" -- so a prose section
# added there would be silently wiped by the next noon-UTC seam-scan
# run; it was never a real, durable home for this explanation, and no
# such section has ever survived on disk). Add to this list only
# alongside a docstring paragraph here explaining the new case --
# never to silence a fresh, real regression.
SEEDED_EXCEPTIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("2026-07-12", "2026-07-13"),
        ("2026-07-13", "2026-07-18"),
    }
)


def read_report_counts(reports_dir: str = DEFAULT_REPORTS_DIR) -> list[tuple[str, int]]:
    """Every sealed `<date>.md` in `reports_dir` that carries a milestone-
    commit sentence, as `(date, count)` pairs sorted chronologically. Days
    whose primary gap wasn't `milestone-unannounced` (no sentence to
    extract) are simply absent -- not a zero, not a gap in the sequence a
    caller needs to explain."""
    out: list[tuple[str, int]] = []
    for path in sorted(glob.glob(os.path.join(reports_dir, "*.md"))):
        m = _DATE_RE.match(os.path.basename(path))
        if m is None:
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        count = report_accuracy_check.extract_milestone_count(text)
        if count is not None:
            out.append((m.group(1), count))
    return out


def compute_report_regression(
    counts: list[tuple[str, int]],
    seeded_exceptions: frozenset[tuple[str, str]] = SEEDED_EXCEPTIONS,
) -> dict[str, object]:
    """Walk consecutive (date, count) pairs -- consecutive in the list,
    not necessarily calendar-adjacent, since a "nothing cleared the bar"
    day simply has no entry -- and flag any decrease not named in
    `seeded_exceptions`. `clean: True` with an empty `regressions` list
    when every step held or was seeded; `clean: False` naming every
    unseeded drop otherwise (there can be more than one)."""
    regressions: list[dict[str, object]] = []
    for (prev_date, prev_count), (date, count) in zip(counts, counts[1:]):
        if count >= prev_count:
            continue
        if (prev_date, date) in seeded_exceptions:
            continue
        regressions.append(
            {
                "from_date": prev_date,
                "from_count": prev_count,
                "to_date": date,
                "to_count": count,
            }
        )
    if not regressions:
        return {
            "clean": True,
            "reason": f"{len(counts)} sealed report(s) carrying a milestone count, "
            f"non-decreasing at every unseeded step ({len(seeded_exceptions)} seeded historical exception(s))",
        }
    first = regressions[0]
    return {
        "clean": False,
        "reason": (
            f"{len(regressions)} unseeded milestone-count regression(s), first "
            f"{first['from_date']} ({first['from_count']}) -> {first['to_date']} ({first['to_count']})"
        ),
        "regressions": regressions,
    }


def precheck_seal(
    candidate_text: str,
    candidate_date: str,
    reports_dir: str = DEFAULT_REPORTS_DIR,
    seeded_exceptions: frozenset[tuple[str, str]] = SEEDED_EXCEPTIONS,
) -> dict[str, object]:
    """Task 964. Off-By-One closes the one gap `compute_report_regression`
    could only ever catch AFTER the fact: every regression this module has
    ever explained -- the two seeded exceptions above, and the 2026-08-23
    incident this function exists to stop recurring -- reached disk before
    anything re-read `fencepost/REPORTS/` to notice. `read_report_counts`/
    `compute_report_regression` are a smoke detector, sound only once the
    room already burned; this is the hand on the stove, meant to be called
    BEFORE `seam_engine.report --write` (or the ledger seal that precedes
    it) commits a number to disk at all.

    2026-08-23's own incident: the hourly hand-dogfood ritual sealed that
    day's FIRST entry using `github_events_source: "override"` (this
    sandbox's own accumulated `github-events-cache.json`, always a subset
    of the real history -- `report_accuracy_check.py`'s own docstring
    names this exact gap) at 250 -- a real regression from 2026-08-22's
    sealed 272 -- six minutes before `seam-scan.yml`'s noon-UTC automatic
    cron overwrote it for real with the authoritative direct-sourced 273
    (272 -> 273, no regression). `compute_report_regression` caught the
    transient 250 in CI exactly as designed (`dawn-run` failed on both
    commits sealed in between), but only after it was already committed
    and pushed; nothing had stopped it from being written in the first
    place, and `seam_engine.report.main`'s own `--write` path carries no
    such guard.

    Takes the CANDIDATE report text about to be written for
    `candidate_date` (not yet on disk) and asks: folded into every report
    already sealed under `reports_dir`, does the resulting sequence
    introduce an unseeded regression? Reuses `read_report_counts`/
    `compute_report_regression` verbatim -- no new regex,
    `duplicate_regex_check.py`'s own doctrine intact -- by building the
    same `(date, count)` list a live seal would produce, with the
    candidate replacing any already-sealed entry for the same date (an
    intra-day reseal) or taking its place in order (a new day).
    `report_accuracy_check.extract_milestone_count` returning `None` (the
    candidate names a different gap, not `milestone-unannounced`) reads
    clean -- nothing to compare, the same discipline
    `compute_report_regression` already holds for a quiet day."""
    count = report_accuracy_check.extract_milestone_count(candidate_text)
    if count is None:
        return {
            "clean": True,
            "reason": "candidate report names no milestone-commit sentence -- nothing to compare",
        }
    counts = [(d, c) for d, c in read_report_counts(reports_dir) if d != candidate_date]
    counts.append((candidate_date, count))
    counts.sort()
    return compute_report_regression(counts, seeded_exceptions=seeded_exceptions)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) >= 3 and argv[0] == "precheck":
        candidate_path, candidate_date = argv[1], argv[2]
        text = sys.stdin.read() if candidate_path == "-" else open(candidate_path, encoding="utf-8").read()
        result = precheck_seal(text, candidate_date)
        print(result["reason"])
        sys.exit(0 if result["clean"] else 1)
    if len(argv) < 1 or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = compute_report_regression(read_report_counts())
    print(result["reason"])
    sys.exit(0 if result["clean"] else 1)
