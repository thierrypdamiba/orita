"""Automated grading for deployment-cadence predictions. (ROADMAP #68,
mirrors #38/#39/#40/#41/#47/#48)

Every prior autograde module closed the same loop for its own cadence's
claims: find due calls, re-derive reality over the call's own window, seal
once. This module is the identical loop for `deployment_cadence.py`'s
claims, scored against the recorded deployment-snapshot log instead.

A due deployment-cadence call whose target has no snapshot at or after it
yet is left alone rather than guessed at — the next daily cadence run
records a fresh snapshot before this module runs again, so a quiet skip
today becomes a real grade tomorrow. Grading early off a stale or missing
snapshot would be exactly the "didn't count pile" Ogun's law forbids in
the other direction.
"""
from __future__ import annotations

import datetime
import json
import re
from types import ModuleType
from typing import cast

from oracle_engine import grading
from oracle_engine.deployment_cadence import (
    DEFAULT_SNAPSHOT_PATH,
    deployment_count_at_or_after,
    load_snapshots,
)
from oracle_engine.prediction import PREDICTION_ACT, load_ledger_module

AUTOGRADE_ACTOR = "ogun"

_DEPLOYMENT_CLAIM_RE = re.compile(
    r"^By (?P<target>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z), [^']+'s public GitHub "
    r"deployment count will be at least (?P<threshold>\d+) "
)


class DeploymentAutogradeError(ValueError):
    """A due deployment-cadence call could not be parsed or scored. Raised
    before any seal — a malformed or not-yet-scoreable claim is skipped,
    never guessed at."""


def parse_deployment_claim(claim: str) -> tuple[datetime.datetime, int]:
    """Pull the target timestamp and threshold back out of a claim built by
    `deployment_cadence.build_prediction`. Raises
    `DeploymentAutogradeError` if `claim` is not shaped like a
    deployment-cadence claim at all — this module only ever grades the
    kind of call it knows how to re-derive."""
    m = _DEPLOYMENT_CLAIM_RE.match(claim)
    if not m:
        raise DeploymentAutogradeError(f"not a deployment-cadence-shaped claim: {claim!r}")
    target = datetime.datetime.strptime(
        m.group("target"), "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=datetime.timezone.utc)
    return target, int(m.group("threshold"))


def _load_claim_payload(detail: str) -> dict[str, object]:
    """Thin wrapper around `grading.load_claim_payload` (this module's
    own default `error_cls`) -- see that function's own docstring for the
    25-sibling consolidation this closes."""
    return grading.load_claim_payload(detail, DeploymentAutogradeError)


def find_due_calls(entries: list[dict[str, object]], now: datetime.datetime) -> list[dict[str, object]]:
    """Every `predict` entry, deployment-cadence-shaped, whose target has
    already passed and that carries no terminal grade yet. Skips (never
    raises on) entries that aren't deployment-cadence-shaped, and skips
    (never raises on) a prior grade record that is present but
    schema-mismatched (e.g. a tampered ledger entry) -- `existing_grades`
    already tolerates a prior grade whose `detail` isn't valid JSON at
    all; this extends the same tolerance to one whose JSON parses but
    fails `grading`'s own stricter well-formedness check, the identical
    boundary `existing_grades` already owns."""
    due: list[dict[str, object]] = []
    for entry in entries:
        if entry.get("act") != PREDICTION_ACT:
            continue
        try:
            payload = _load_claim_payload(cast(str, entry["detail"]))
            target, _ = parse_deployment_claim(cast(str, payload["claim"]))
        except (DeploymentAutogradeError, KeyError, ValueError, json.JSONDecodeError):
            continue
        if target > now:
            continue
        prior_outcomes: list[object] = []
        for g in grading.existing_grades(cast(int, entry["seq"]), entries):
            try:
                prior_outcomes.append(grading.parse_grade_detail(cast(str, g["detail"]))["outcome"])
            except (grading.GradingError, KeyError, json.JSONDecodeError):
                continue
        if any(o in grading.TERMINAL_OUTCOMES for o in prior_outcomes):
            continue
        due.append(entry)
    return due


def score_call(entry: dict[str, object], snapshots: list[dict[str, object]]) -> str:
    """`correct` if the real recorded snapshot at or after the call's own
    target meets or beats the threshold it named, `incorrect` otherwise.
    Raises `DeploymentAutogradeError` if no snapshot at or after the
    target has been recorded yet — this call is due but not yet scoreable,
    the caller's job to skip and retry later, not this function's job to
    guess."""
    payload = _load_claim_payload(cast(str, entry["detail"]))
    target, threshold = parse_deployment_claim(cast(str, payload["claim"]))
    actual = deployment_count_at_or_after(snapshots, target)
    if actual is None:
        raise DeploymentAutogradeError(
            f"no snapshot recorded at or after target {target.isoformat()} yet"
        )
    return "correct" if actual >= threshold else "incorrect"


def autograde_due_predictions(
    now: datetime.datetime,
    ts: str,
    actor: str = AUTOGRADE_ACTOR,
    snapshot_path: str = DEFAULT_SNAPSHOT_PATH,
    ledger_module: ModuleType | None = None,
) -> list[dict[str, object]]:
    """Grade every due, ungraded, scoreable deployment-cadence prediction
    on the live chain and seal each grade. Returns the sealed grade
    entries (empty if nothing was due or nothing was yet scoreable — a
    quiet run is not an error)."""
    if now.tzinfo is None:
        raise DeploymentAutogradeError("now must be timezone-aware")

    mod = ledger_module or load_ledger_module()
    entries: list[dict[str, object]] = cast(list[dict[str, object]], mod._entries())
    due = find_due_calls(entries, now)
    if not due:
        return []

    snapshots = load_snapshots(snapshot_path)
    sealed: list[dict[str, object]] = []
    for entry in due:
        try:
            outcome = score_call(entry, snapshots)
        except DeploymentAutogradeError:
            continue
        sealed.append(
            grading.seal_grade(
                actor=actor,
                call_seq=cast(int, entry["seq"]),
                outcome=outcome,
                ts=ts,
                ledger_module=mod,
            )
        )
        # keep `entries` current so a second due call this run can't be
        # mis-scored against a chain that hasn't seen the prior seal yet
        entries = cast(list[dict[str, object]], mod._entries())
    return sealed


if __name__ == "__main__":
    _now = datetime.datetime.now(datetime.timezone.utc)
    _ts = _now.isoformat(timespec="seconds")
    _sealed = autograde_due_predictions(now=_now, ts=_ts)
    if not _sealed:
        print("no due, scoreable deployment-cadence predictions — quiet run, nothing sealed")
    else:
        for _g in _sealed:
            print(_g["hash"])
