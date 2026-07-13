"""The self-scoring pass, automated. (ROADMAP #37, machinery for #32's law)

`grading.py` (task 32) is the hand that seals a grade; it needs a caller who
knows WHEN a call's outcome has become knowable and WHAT the real outcome
was. Task 37 cannot ship the actual grade for seq 80 before its window
closes on calendar time (2026-07-14T11:12:14Z) — the same shape as task 19's
seven-day streak. What CAN ship now is the machinery that fires the moment
that window passes, so no god has to remember to come back and count by
hand.

This module closes that loop for the cadence predictions `cadence.py`
(task 36) seals:

1. **Find due calls.** Read the chain for `predict` entries whose claim
   parses to a `cadence`-shaped target timestamp that has already passed,
   and that carry no terminal grade yet.
2. **Score against reality.** Re-run the exact same `recent_task_velocity`
   reader cadence.py used to BUILD the claim, but windowed on the call's
   own [sealed_ts, target_ts] instead of "now" — the same public,
   append-only `BUILDLOG.md` record, nobody's word taken for it.
3. **Seal, once.** `grading.seal_grade` already refuses a second terminal
   grade for the same call_seq (Ogun's law); this module additionally
   skips a call it can already see has a terminal grade, so a normal run
   is a no-op rather than a caught exception.

A call whose window has NOT yet closed is left alone — grading early would
mean grading against an incomplete window, exactly the "didn't count pile"
Ogun's law forbids in the other direction.
"""
from __future__ import annotations

import datetime
import re
from types import ModuleType

from oracle_engine import grading
from oracle_engine.cadence import (
    DEFAULT_BUILDLOG_PATH,
    load_buildlog_entries,
    recent_task_velocity,
)
from oracle_engine.prediction import PREDICTION_ACT, load_ledger_module

AUTOGRADE_ACTOR = "ogun"

_CADENCE_CLAIM_RE = re.compile(
    r"^By (?P<target>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z), BUILDLOG\.md will record at least "
    r"(?P<threshold>\d+) distinct numbered ROADMAP task\(s\) newly shipped between now and then "
)


class AutogradeError(ValueError):
    """A due call could not be parsed or scored. Raised before any seal —
    a malformed claim is skipped, never guessed at."""


def parse_cadence_claim(claim: str) -> tuple[datetime.datetime, int]:
    """Pull the target timestamp and threshold back out of a claim built by
    `cadence.build_prediction`. Raises `AutogradeError` if `claim` is not
    shaped like a cadence claim at all — this module only ever grades the
    kind of call it knows how to re-derive, never guesses at a shape it
    doesn't recognize."""
    m = _CADENCE_CLAIM_RE.match(claim)
    if not m:
        raise AutogradeError(f"not a cadence-shaped claim: {claim!r}")
    target = datetime.datetime.strptime(
        m.group("target"), "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=datetime.timezone.utc)
    return target, int(m.group("threshold"))


def _parse_ts(ts: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def find_due_calls(entries: list[dict], now: datetime.datetime) -> list[dict]:
    """Every `predict` entry, cadence-shaped, whose target has already
    passed and that carries no terminal grade yet. Skips (never raises on)
    entries that aren't cadence-shaped — this reader only ever touches the
    calls it knows how to score."""
    due = []
    for entry in entries:
        if entry.get("act") != PREDICTION_ACT:
            continue
        try:
            payload = _load_claim_payload(entry["detail"])
            target, _ = parse_cadence_claim(payload["claim"])
        except (AutogradeError, KeyError, ValueError):
            continue
        if target > now:
            continue
        if grading.existing_grades(entry["seq"], entries):
            prior_outcomes = [
                grading.parse_grade_detail(g["detail"])["outcome"]
                for g in grading.existing_grades(entry["seq"], entries)
            ]
            if any(o in grading.TERMINAL_OUTCOMES for o in prior_outcomes):
                continue
        due.append(entry)
    return due


def _load_claim_payload(detail: str) -> dict:
    import json

    return json.loads(detail)


def score_call(
    entry: dict,
    buildlog_entries: list[dict],
) -> str:
    """`correct` if the real BUILDLOG.md velocity between the call's own
    sealed timestamp and its stated target meets or beats the threshold it
    named, `incorrect` otherwise. Windowed on the call's OWN span, never on
    "now" — a call is scored against exactly the window it claimed, nothing
    wider or narrower."""
    payload = _load_claim_payload(entry["detail"])
    target, threshold = parse_cadence_claim(payload["claim"])
    sealed_at = _parse_ts(entry["ts"])
    window_hours = (target - sealed_at).total_seconds() / 3600.0
    actual = recent_task_velocity(buildlog_entries, now=target, window_hours=window_hours)
    return "correct" if actual >= threshold else "incorrect"


def autograde_due_predictions(
    now: datetime.datetime,
    ts: str,
    actor: str = AUTOGRADE_ACTOR,
    buildlog_path: str = DEFAULT_BUILDLOG_PATH,
    ledger_module: ModuleType | None = None,
) -> list[dict]:
    """Grade every due, ungraded cadence prediction on the live chain and
    seal each grade. Returns the sealed grade entries (empty if nothing was
    due — a quiet run is not an error). `now` and `ts` are always passed in
    by the caller, same discipline as `cadence.seal_cadence_prediction`."""
    if now.tzinfo is None:
        raise AutogradeError("now must be timezone-aware")

    mod = ledger_module or load_ledger_module()
    entries = mod._entries()
    due = find_due_calls(entries, now)
    if not due:
        return []

    buildlog_entries = load_buildlog_entries(buildlog_path)
    sealed = []
    for entry in due:
        outcome = score_call(entry, buildlog_entries)
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
        print("no due predictions — quiet run, nothing sealed")
    else:
        for _g in _sealed:
            print(_g["hash"])
