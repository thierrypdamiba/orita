#!/usr/bin/env python3
"""Task 145. Nisaba cross-checks her own ledger against the gate's memory.

STRATEGY.md's own metrics table names one leading metric in plain words:
"Distinct read-only toolkits connected across users (Arcade breadth) --
>=5 toolkits in real use -- owner nisaba." `records/metrics.jsonl` is
where that reading is supposed to land every day (the 18:00 UTC daily
aggregate), under the field `distinct_toolkits_in_use`. Every reading
recorded there from 2026-07-12 through 2026-07-18 said `2` -- and per
`tools/consent_grant_log.py`'s own docstring (which quotes
`arcade_app_watch.py` task 122's clarification verbatim), the honest
ground truth was, and still is, 0: no real outside human has ever cleared
Esu's consent gate for any toolkit. `2` was never even the town's own
dogfood counted honestly -- it was a flattering number nobody had ever
checked against anything, self-contradicted by several of those same
entries' own prose ("no outside OAuth connections yet"). This task
corrected every historical entry's `distinct_toolkits_in_use` field to
the honest 0 (not a backfill -- the true value was already knowable and
unchanging the day each entry was written, since the whole consent-
recording machinery this module now provides simply did not exist yet)
and annotated each one's `notes` field with the correction, in the open.

This module is the missing cross-check that keeps it honest going
forward: it reads the REAL ground truth off `consent_grant_log.py`'s
durable, gate-verified log (never a second hand-typed guess) and compares
it to the most recently recorded `distinct_toolkits_in_use` reading in
`records/metrics.jsonl`. A mismatch is a live, standing misreport of the
flagship's own adoption metric -- the same class of real regression
`check_scopes_completeness`/`check_wip_reclaim` already flip `broken` on,
not an honest zero-state waiting on the calendar. It never rewrites a
past metrics.jsonl entry itself (`metrics_cadence_check.py`'s own law:
never backfill or guess a number you cannot show for a day already gone)
-- it only tells the next real writer, honestly, whether the LAST
recorded reading currently agrees with the truth, so today's 18:00 UTC
aggregate (and every one after it) can call
`consent_grant_log.real_distinct_toolkit_count()` directly instead of
copying yesterday's guess forward.

Usage:
    python3 tools/toolkits_in_use_check.py check
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adoption_metric_format  # noqa: E402
import consent_grant_log  # noqa: E402
import metrics_reader  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_METRICS_PATH = os.path.join(ROOT, "records", "metrics.jsonl")
DEFAULT_CONSENT_LOG_PATH = consent_grant_log.LOG

# STRATEGY.md: "Distinct read-only toolkits connected across users (Arcade
# breadth) | leading | >=5 toolkits in real use | nisaba" -- task 428,
# cross-checked against the live doc text (never a second hand-typed copy)
# by tools/strategy_targets_check.py, the same doctrine tasks 159/421
# already hold for report cadence/shared reports/github stars.
TARGET_TOOLKITS = 5


# Task 508: consolidated into tools/metrics_reader.py -- six sibling
# checks each carried a byte-identical copy of this reader, invisible to
# duplicate_regex_check.py (which only scans `re.compile()` call sites).
# tests/test_metrics_reader.py asserts this name IS that shared function.
_last_metrics_entry = metrics_reader.last_metrics_entry


def check_toolkits_in_use(
    metrics_path: str = DEFAULT_METRICS_PATH,
    consent_log_path: str = DEFAULT_CONSENT_LOG_PATH,
) -> dict[str, object]:
    """Cross-check the last recorded `distinct_toolkits_in_use` reading
    against ground truth. Returns `clean: True` when the two agree, or
    when nothing has been recorded yet (a fresh log has nothing to
    contradict); otherwise `clean: False` naming the exact claimed vs.
    real numbers, never a bare pass/fail.

    Task 453 found and fixed this exact bug shape one field over
    (`gap_true_positive_check.py`'s `gap_true_positive_rate`): a
    `last is None or FIELD not in last` single branch collapses two
    different "nothing recorded" shapes into one unconditional clean --
    no reading has ever existed at all (genuinely nothing to contradict,
    stays clean unconditionally), versus a reading that DOES exist (has
    a `date`, other fields present) but happens to omit THIS field, which
    is the same "claims a number ground truth cannot back" failure this
    whole sibling class of checks exists to catch, just from the
    omission side. Unlike `gap_true_positive_rate` (a `float | None`,
    genuinely absent until the first gap is ever audited),
    `distinct_toolkits_in_use`'s ground truth
    (`consent_grant_log.real_distinct_toolkit_count`) is always a
    definite `int`, never `None` -- so the omission-with-an-existing-
    reading case is clean only when that real count is honestly `0`
    (nothing yet to have omitted), and `BROKEN` the moment a real
    connected toolkit exists and a dated reading failed to record it."""
    real = consent_grant_log.real_distinct_toolkit_count(consent_log_path)
    last = _last_metrics_entry(metrics_path)
    if last is None:
        return {
            "clean": True,
            "real": real,
            "claimed": None,
            "claimed_date": None,
        }
    if "distinct_toolkits_in_use" not in last:
        return {
            "clean": real == 0,
            "real": real,
            "claimed": None,
            "claimed_date": last.get("date"),
        }
    claimed = last["distinct_toolkits_in_use"]
    return {
        "clean": claimed == real,
        "real": real,
        "claimed": claimed,
        "claimed_date": last.get("date"),
    }


def format_result(result: dict[str, object]) -> str:
    return adoption_metric_format.format_adoption_result(
        "toolkits in use", result, "distinct_toolkits_in_use", "real toolkit(s)"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_toolkits_in_use()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
