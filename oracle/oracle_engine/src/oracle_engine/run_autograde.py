"""Automated grading for run-cadence predictions. (ROADMAP #75, mirrors #60)

The identical due-call / re-derive-reality / seal-once loop every prior
cadence source's autograde module runs, scored against the recorded
`run_snapshots.jsonl` log instead of the workflow-definitions snapshot
log. Ogun grades this one exactly as he has graded every cadence before
it -- a call sourced by the child does not earn it a gentler read.

A due run-cadence call whose target has no snapshot at or after it yet is
left alone rather than guessed at -- the next daily cadence run records a
fresh snapshot before this module runs again, so a quiet skip today
becomes a real grade tomorrow.
"""
from __future__ import annotations

import datetime
import json
import re
from types import ModuleType

from oracle_engine import grading
from oracle_engine.prediction import PREDICTION_ACT, load_ledger_module
from oracle_engine.run_cadence import (
    DEFAULT_SNAPSHOT_PATH,
    load_snapshots,
    run_count_at_or_after,
)

AUTOGRADE_ACTOR = "ogun"

_RUN_CLAIM_RE = re.compile(
    r"^By (?P<target>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z), [^']+'s public GitHub Actions "
    r"total workflow-run count will be at least (?P<threshold>\d+) "
)


class RunAutogradeError(ValueError):
    """A due run-cadence call could not be parsed or scored. Raised before
    any seal -- a malformed or not-yet-scoreable claim is skipped, never
    guessed at."""


def parse_run_claim(claim: str) -> tuple[datetime.datetime, int]:
    """Pull the target timestamp and threshold back out of a claim built
    by `run_cadence.build_prediction`. Raises `RunAutogradeError` if
    `claim` is not shaped like a run-cadence claim at all -- this module
    only ever grades the kind of call it knows how to re-derive."""
    m = _RUN_CLAIM_RE.match(claim)
    if not m:
        raise RunAutogradeError(f"not a run-cadence-shaped claim: {claim!r}")
    target = datetime.datetime.strptime(
        m.group("target"), "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=datetime.timezone.utc)
    return target, int(m.group("threshold"))


def _load_claim_payload(detail: str) -> dict:
    """Thin wrapper around `grading.load_claim_payload` (this module's
    own default `error_cls`) -- see that function's own docstring for the
    25-sibling consolidation this closes."""
    return grading.load_claim_payload(detail, RunAutogradeError)


def find_due_calls(entries: list[dict], now: datetime.datetime) -> list[dict]:
    """Every `predict` entry, run-cadence-shaped, whose target has already
    passed and that carries no terminal grade yet. Skips (never raises on)
    entries that aren't run-cadence-shaped, and skips (never raises on) a
    prior grade record that is present but schema-mismatched (e.g. a
    tampered ledger entry) -- `existing_grades` already tolerates a prior
    grade whose `detail` isn't valid JSON at all; this extends the same
    tolerance to one whose JSON parses but fails `grading`'s own stricter
    well-formedness check, the identical boundary `existing_grades` already
    owns."""
    due = []
    for entry in entries:
        if entry.get("act") != PREDICTION_ACT:
            continue
        try:
            payload = _load_claim_payload(entry["detail"])
            target, _ = parse_run_claim(payload["claim"])
        except (RunAutogradeError, KeyError, ValueError, json.JSONDecodeError):
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
    Raises `RunAutogradeError` if no snapshot at or after the target has
    been recorded yet -- this call is due but not yet scoreable, the
    caller's job to skip and retry later, not this function's job to
    guess."""
    payload = _load_claim_payload(entry["detail"])
    target, threshold = parse_run_claim(payload["claim"])
    actual = run_count_at_or_after(snapshots, target)
    if actual is None:
        raise RunAutogradeError(
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
    """Grade every due, ungraded, scoreable run-cadence prediction on the
    live chain and seal each grade. Returns the sealed grade entries
    (empty if nothing was due or nothing was yet scoreable -- a quiet run
    is not an error)."""
    if now.tzinfo is None:
        raise RunAutogradeError("now must be timezone-aware")

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
        except RunAutogradeError:
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
        print("no due, scoreable run-cadence predictions — quiet run, nothing sealed")
    else:
        for _g in _sealed:
            print(_g["hash"])
