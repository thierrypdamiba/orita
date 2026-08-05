#!/usr/bin/env python3
"""Task 412. Nisaba's ledger claims a second real number it never checks.

Task 145 found that `records/metrics.jsonl`'s `distinct_toolkits_in_use`
field had recorded a flattering `2` every day from 2026-07-12 through
2026-07-18, against an honest ground truth of `0` (no real outside human
had ever cleared the consent gate), and built `toolkits_in_use_check.py`
as the running cross-check that keeps that one field honest going
forward. That module's own docstring names the field it fixed and the
field it did NOT touch in the same breath: `tools/shared_reports_check.py`
independently confirms `records/metrics.jsonl`'s own
`connected_users_oauth`/`distinct_toolkits_in_use` fields are "both real,
both honestly 0/2 since founding" -- but "honestly recorded so far" is a
claim about the past, not a running guarantee, and the exact same "nobody
cross-checks this field against ground truth" shape task 145 closed for
`distinct_toolkits_in_use` was still open, unnoticed, one field over, on
`connected_users_oauth`. STRATEGY.md's own metrics table names it as its
own row with its own owner: "'Connect your own' OAuth completions across
users | leading | 100 connected users in 60 days | kothar-wa-khasis" --
a distinct metric from toolkit breadth (one human connecting Gmail AND
Calendar is one connected user, not two), with nothing in code ever
telling the two apart before this task's `consent_grant_log.
real_distinct_human_count()`.

This module is that missing cross-check, built to the identical shape
`toolkits_in_use_check.py` (task 145) already proved: it reads the REAL
ground truth off `consent_grant_log.py`'s durable, gate-verified log
(never a second hand-typed guess) and compares it to the most recently
recorded `connected_users_oauth` reading in `records/metrics.jsonl`. A
mismatch is a live, standing misreport of the flagship's own adoption
metric -- the same class of real regression `check_toolkits_in_use`/
`check_scopes_completeness` already flip `broken` on. It never rewrites a
past metrics.jsonl entry itself (`metrics_cadence_check.py`'s own law:
never backfill or guess a number you cannot show for a day already gone)
-- it only tells the next real writer, honestly, whether the LAST
recorded reading currently agrees with the truth.

Usage:
    python3 tools/connected_users_check.py check
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

# STRATEGY.md: "'Connect your own' OAuth completions across users | leading |
# 100 connected users in 60 days | kothar-wa-khasis" -- task 428, cross-
# checked against the live doc text (never a second hand-typed copy) by
# tools/strategy_targets_check.py, the same doctrine tasks 159/421 already
# hold for report cadence/shared reports/github stars.
TARGET_CONNECTED_USERS = 100


# Task 508: consolidated into tools/metrics_reader.py -- six sibling
# checks each carried a byte-identical copy of this reader, invisible to
# duplicate_regex_check.py (which only scans `re.compile()` call sites).
# tests/test_metrics_reader.py asserts this name IS that shared function.
_last_metrics_entry = metrics_reader.last_metrics_entry


def check_connected_users(
    metrics_path: str = DEFAULT_METRICS_PATH,
    consent_log_path: str = DEFAULT_CONSENT_LOG_PATH,
) -> dict:
    """Cross-check the last recorded `connected_users_oauth` reading
    against ground truth. Returns `clean: True` when the two agree, or
    when nothing has been recorded yet (a fresh log has nothing to
    contradict); otherwise `clean: False` naming the exact claimed vs.
    real numbers, never a bare pass/fail.

    Task 457: the identical `last is None or FIELD not in last` omitted-
    field bug tasks 453-456 already fixed on four sibling `metrics.jsonl`
    checkers (`gap_true_positive_check.py`, `toolkits_in_use_check.py`,
    `report_shipped_check.py`, `github_stars_check.py`) -- a reading that
    EXISTS (has a `date`, other fields present) but omits
    `connected_users_oauth` used to collapse into the same unconditional-
    clean branch as "no reading has ever existed at all", even while the
    real ground truth already names a nonzero connected-user count that
    reading failed to carry. `consent_grant_log.real_distinct_human_count`
    is always a definite `int`, never `None`, so the omission-with-an-
    existing-reading case is clean only when that real count is honestly
    `0` (nothing yet to have omitted), and `BROKEN` the moment a real
    connected human exists and a dated reading failed to record it."""
    real = consent_grant_log.real_distinct_human_count(consent_log_path)
    last = _last_metrics_entry(metrics_path)
    if last is None:
        return {
            "clean": True,
            "real": real,
            "claimed": None,
            "claimed_date": None,
        }
    if "connected_users_oauth" not in last:
        return {
            "clean": real == 0,
            "real": real,
            "claimed": None,
            "claimed_date": last.get("date"),
        }
    claimed = last["connected_users_oauth"]
    return {
        "clean": claimed == real,
        "real": real,
        "claimed": claimed,
        "claimed_date": last.get("date"),
    }


def format_result(result: dict) -> str:
    return adoption_metric_format.format_adoption_result(
        "connected users (OAuth)", result, "connected_users_oauth", "real connected user(s)"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_connected_users()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
