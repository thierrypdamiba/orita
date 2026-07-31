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

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import consent_grant_log  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_METRICS_PATH = os.path.join(ROOT, "records", "metrics.jsonl")
DEFAULT_CONSENT_LOG_PATH = consent_grant_log.LOG

# STRATEGY.md: "'Connect your own' OAuth completions across users | leading |
# 100 connected users in 60 days | kothar-wa-khasis" -- task 428, cross-
# checked against the live doc text (never a second hand-typed copy) by
# tools/strategy_targets_check.py, the same doctrine tasks 159/421 already
# hold for report cadence/shared reports/github stars.
TARGET_CONNECTED_USERS = 100


def _last_metrics_entry(metrics_path: str) -> dict | None:
    """The most recently recorded dated reading in `records/
    metrics.jsonl` -- one append-only file, not one file per day. Walks
    non-blank lines from the end and returns the first one that parses
    as valid JSON AND is itself a JSON object -- a truncated/malformed
    trailing line, or one that parses cleanly but isn't a dict (a bare
    `true`/`42`/`3.14`/`null`/a JSON array), is skipped, not fatal, the
    same discipline `toolkits_in_use_check.py`'s own reader holds (tasks
    306/328). `None` if no reading has ever shipped, or every line is
    malformed/non-dict (nothing to cross-check yet, not an error)."""
    if not os.path.exists(metrics_path):
        return None
    with open(metrics_path, encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def check_connected_users(
    metrics_path: str = DEFAULT_METRICS_PATH,
    consent_log_path: str = DEFAULT_CONSENT_LOG_PATH,
) -> dict:
    """Cross-check the last recorded `connected_users_oauth` reading
    against ground truth. Returns `clean: True` only when the two agree
    (or nothing has been recorded yet -- a fresh log has nothing to
    contradict); otherwise `clean: False` naming the exact claimed vs.
    real numbers, never a bare pass/fail."""
    real = consent_grant_log.real_distinct_human_count(consent_log_path)
    last = _last_metrics_entry(metrics_path)
    if last is None or "connected_users_oauth" not in last:
        return {
            "clean": True,
            "real": real,
            "claimed": None,
            "claimed_date": None,
        }
    claimed = last["connected_users_oauth"]
    return {
        "clean": claimed == real,
        "real": real,
        "claimed": claimed,
        "claimed_date": last.get("date"),
    }


def format_result(result: dict) -> str:
    if result["claimed"] is None:
        return f"connected users (OAuth): clean (no metrics.jsonl reading yet; real ground truth is {result['real']})"
    if result["clean"]:
        return f"connected users (OAuth): clean ({result['real']} real connected user(s), metrics.jsonl's {result['claimed_date']} reading agrees)"
    return (
        f"connected users (OAuth): BROKEN -- metrics.jsonl's {result['claimed_date']} reading claims "
        f"{result['claimed']}, real ground truth (HAND/consent-grants-log.jsonl, gate-verified) is "
        f"{result['real']} -- STRATEGY.md's adoption metric is misreporting live"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_connected_users()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
