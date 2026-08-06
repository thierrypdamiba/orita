"""Automated grading for issue-cadence predictions. (ROADMAP #40, mirrors #37/#38/#39)

`fork_autograde.py` (task 39) closed the loop for `fork_cadence.py`'s
claims: find due calls, re-derive reality over the call's own window,
seal once. This module is the identical loop for `issue_cadence.py`'s
claims, scored against the recorded issue-snapshot log instead of the
fork-snapshot log.

A due issue-cadence call whose target has no snapshot at or after it yet
is left alone rather than guessed at — the next daily cadence run records
a fresh snapshot before this module runs again, so a quiet skip today
becomes a real grade tomorrow. Grading early off a stale or missing
snapshot would be exactly the "didn't count pile" Ogun's law forbids in
the other direction.
"""
from __future__ import annotations

import datetime
import json
import re
from types import ModuleType

from oracle_engine import grading
from oracle_engine.issue_cadence import (
    DEFAULT_SNAPSHOT_PATH,
    issue_count_at_or_after,
    load_snapshots,
)
from oracle_engine.prediction import PREDICTION_ACT, load_ledger_module

AUTOGRADE_ACTOR = "ogun"

_ISSUE_CLAIM_RE = re.compile(
    r"^By (?P<target>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z), [^']+'s public GitHub "
    r"open-issue count will be at least (?P<threshold>\d+) "
)


class IssueAutogradeError(ValueError):
    """A due issue-cadence call could not be parsed or scored. Raised
    before any seal — a malformed or not-yet-scoreable claim is skipped,
    never guessed at."""


def parse_issue_claim(claim: str) -> tuple[datetime.datetime, int]:
    """Pull the target timestamp and threshold back out of a claim built by
    `issue_cadence.build_prediction`. Raises `IssueAutogradeError` if
    `claim` is not shaped like an issue-cadence claim at all — this module
    only ever grades the kind of call it knows how to re-derive."""
    m = _ISSUE_CLAIM_RE.match(claim)
    if not m:
        raise IssueAutogradeError(f"not an issue-cadence-shaped claim: {claim!r}")
    target = datetime.datetime.strptime(
        m.group("target"), "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=datetime.timezone.utc)
    return target, int(m.group("threshold"))


def _load_claim_payload(detail: str) -> dict:
    """Thin wrapper around `grading.load_claim_payload` (this module's
    own default `error_cls`) -- see that function's own docstring for the
    25-sibling consolidation this closes."""
    return grading.load_claim_payload(detail, IssueAutogradeError)


def find_due_calls(entries: list[dict], now: datetime.datetime) -> list[dict]:
    """Every `predict` entry, issue-cadence-shaped, whose target has
    already passed and that carries no terminal grade yet. Skips (never
    raises on) entries that aren't issue-cadence-shaped, and skips (never
    raises on) a prior grade record that is present but schema-mismatched
    (e.g. a tampered ledger entry) -- `existing_grades` already tolerates a
    prior grade whose `detail` isn't valid JSON at all; this extends the
    same tolerance to one whose JSON parses but fails `grading`'s own
    stricter well-formedness check, the identical boundary `existing_grades`
    already owns."""
    due = []
    for entry in entries:
        if entry.get("act") != PREDICTION_ACT:
            continue
        try:
            payload = _load_claim_payload(entry["detail"])
            target, _ = parse_issue_claim(payload["claim"])
        except (IssueAutogradeError, KeyError, ValueError, json.JSONDecodeError):
            continue
        if target > now:
            continue
        prior_outcomes = []
        for g in grading.existing_grades(entry["seq"], entries):
            try:
                prior_outcomes.append(grading.parse_grade_detail(g["detail"])["outcome"])
            except (grading.GradingError, KeyError, json.JSONDecodeError):
                continue
        if any(o in grading.TERMINAL_OUTCOMES for o in prior_outcomes):
            continue
        due.append(entry)
    return due


def score_call(entry: dict, snapshots: list[dict]) -> str:
    """`correct` if the real recorded snapshot at or after the call's own
    target meets or beats the threshold it named, `incorrect` otherwise.
    Raises `IssueAutogradeError` if no snapshot at or after the target has
    been recorded yet — this call is due but not yet scoreable, the
    caller's job to skip and retry later, not this function's job to
    guess."""
    payload = _load_claim_payload(entry["detail"])
    target, threshold = parse_issue_claim(payload["claim"])
    actual = issue_count_at_or_after(snapshots, target)
    if actual is None:
        raise IssueAutogradeError(
            f"no snapshot recorded at or after target {target.isoformat()} yet"
        )
    return "correct" if actual >= threshold else "incorrect"


def autograde_due_predictions(
    now: datetime.datetime,
    ts: str,
    actor: str = AUTOGRADE_ACTOR,
    snapshot_path: str = DEFAULT_SNAPSHOT_PATH,
    ledger_module: ModuleType | None = None,
) -> list[dict]:
    """Grade every due, ungraded, scoreable issue-cadence prediction on the
    live chain and seal each grade. Returns the sealed grade entries (empty
    if nothing was due or nothing was yet scoreable — a quiet run is not an
    error)."""
    if now.tzinfo is None:
        raise IssueAutogradeError("now must be timezone-aware")

    mod = ledger_module or load_ledger_module()
    entries = mod._entries()
    due = find_due_calls(entries, now)
    if not due:
        return []

    snapshots = load_snapshots(snapshot_path)
    sealed = []
    for entry in due:
        try:
            outcome = score_call(entry, snapshots)
        except IssueAutogradeError:
            continue
        sealed.append(
            grading.seal_grade(
                actor=actor,
                call_seq=entry["seq"],
                outcome=outcome,
                ts=ts,
                ledger_module=mod,
            )
        )
        # keep `entries` current so a second due call this run can't be
        # mis-scored against a chain that hasn't seen the prior seal yet
        entries = mod._entries()
    return sealed


if __name__ == "__main__":
    _now = datetime.datetime.now(datetime.timezone.utc)
    _ts = _now.isoformat(timespec="seconds")
    _sealed = autograde_due_predictions(now=_now, ts=_ts)
    if not _sealed:
        print("no due, scoreable issue-cadence predictions — quiet run, nothing sealed")
    else:
        for _g in _sealed:
            print(_g["hash"])
