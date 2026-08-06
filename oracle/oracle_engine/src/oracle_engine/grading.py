"""The self-scoring pass — sealing an outcome against a prediction. (ROADMAP #32)

A prediction (task 31) is sealed before its outcome exists. This module is
what happens once the outcome *is* knowable: a `grade` entry, chained onto
the same ledger, that names the original call's `seq` and nothing else about
it changes. Ogun's law, stated in ROADMAP.md: "no quietly moving a loss into
a 'didn't count' pile." Two guarantees make that true in code, not just prose:

1. **A grade must name a real call.** `seal_grade` reads the chain and
   refuses to write a grade whose `call_seq` does not point at an existing
   `predict` entry. A grade of nothing is not a grade.
2. **A call cannot be re-graded once its outcome is terminal.** `correct`
   and `incorrect` are terminal; `pending` is not. Once a call has a
   terminal grade on the chain, `seal_grade` refuses a second grade for the
   same `call_seq` — the one door a "didn't count" pile would need is
   welded shut. (A `pending` grade may be followed by exactly one terminal
   grade, recording the wait honestly instead of pretending the outcome was
   known immediately.)

Like `prediction.py`, sealing is delegated to `tools/ledger.py`'s own
`append()` — a tampered grade breaks `ledger.py verify()` exactly like a
tampered prediction, and this module defines no function shaped like an
edit of a sealed entry.
"""
from __future__ import annotations

import json
from types import ModuleType
from typing import Any

from oracle_engine.prediction import PREDICTION_ACT, load_ledger_module

GRADE_ACT = "grade"

TERMINAL_OUTCOMES = ("correct", "incorrect")
VALID_OUTCOMES = TERMINAL_OUTCOMES + ("pending",)


class GradingError(ValueError):
    """A grade that does not meet the schema, or would regrade away a
    terminal outcome. Refused before it is sealed."""


def validate_actor(actor: str) -> None:
    if not isinstance(actor, str) or not actor.strip():
        raise GradingError("actor must be a non-empty string")


def validate_outcome(outcome: str) -> None:
    if outcome not in VALID_OUTCOMES:
        raise GradingError(
            f"outcome must be one of {VALID_OUTCOMES!r}, not {outcome!r} — "
            "there is no 'didn't count' pile"
        )


def _chain_entries(ledger_module: ModuleType) -> list[dict]:
    return ledger_module._entries()


def find_call(call_seq: Any, entries: list[dict]) -> dict:
    """Locate the original prediction a grade would reference. Raises
    `GradingError` if `call_seq` does not point at a real, existing
    `predict` entry on the chain — a grade of nothing is not a grade."""
    if isinstance(call_seq, bool) or not isinstance(call_seq, int) or call_seq < 0:
        raise GradingError(f"call_seq must be a non-negative integer, not {call_seq!r}")
    for entry in entries:
        if entry.get("seq") == call_seq:
            if entry.get("act") != PREDICTION_ACT:
                raise GradingError(
                    f"call_seq {call_seq} refers to a {entry.get('act')!r} entry, "
                    f"not a {PREDICTION_ACT!r} — a grade must reference a real prediction"
                )
            return entry
    raise GradingError(f"call_seq {call_seq} does not exist on the chain — cannot grade a non-existent call")


def existing_grades(call_seq: int, entries: list[dict]) -> list[dict]:
    """Every grade entry already sealed for this call_seq, oldest first.

    A `grade`-act entry whose `detail` is syntactically valid JSON but not a
    JSON *object* (a hand-corrupted ledger line reading e.g. `"[1, 2]"`,
    `"null"`, `"5"`, or `"true"`) is skipped exactly like unparseable JSON
    already is -- `payload.get(...)` below would otherwise raise an
    uncaught `AttributeError` on every non-dict JSON type, since none of
    them define `.get`. Every one of the 25 `oracle_engine/*_autograde.py`
    `find_due_calls()` implementations (tasks 276-301) calls this function
    directly, unguarded, so a crash here crashes all of them -- this is the
    one root check that protects every leaf at once.
    """
    out = []
    for entry in entries:
        if entry.get("act") != GRADE_ACT:
            continue
        try:
            payload = json.loads(entry["detail"])
        except (KeyError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("call_seq") == call_seq:
            out.append(entry)
    return out


def assert_not_already_terminal(call_seq: int, entries: list[dict]) -> None:
    """Refuse to grade a call that already carries a terminal grade. This is
    the enforcement of Ogun's law: once a loss is sealed `incorrect`, no
    later grade for the same call_seq is permitted, terminal or not."""
    for prior in existing_grades(call_seq, entries):
        prior_outcome = json.loads(prior["detail"]).get("outcome")
        if prior_outcome in TERMINAL_OUTCOMES:
            raise GradingError(
                f"call_seq {call_seq} already has a terminal grade ({prior_outcome!r} "
                f"at seq {prior['seq']}) — no quietly moving a loss into a 'didn't count' pile"
            )


def grade_payload(call_seq: int, outcome: str) -> dict:
    """The sealed detail shape. Exactly two keys, sorted, no room to grow
    an edit-shaped field in by accident."""
    return {"call_seq": call_seq, "outcome": outcome}


def seal_grade(
    actor: str,
    call_seq: int,
    outcome: str,
    ts: str | None = None,
    ledger_module: ModuleType | None = None,
) -> dict:
    """Validate and seal a grade as the next entry on the town's chain.

    Raises `GradingError` before anything is written if: the actor is
    empty, the outcome is not one of `correct`/`incorrect`/`pending`, the
    `call_seq` does not reference an existing `predict` entry, or that call
    already carries a terminal grade. Once written, the grade and the
    prediction it names both stay exactly as sealed — there is no function
    in this module that takes a `seq` and changes what an existing entry
    says.
    """
    validate_actor(actor)
    validate_outcome(outcome)

    if ts is None:
        raise GradingError("ts is required — a grade is timestamped at the moment it's sealed, never defaulted silently")

    mod = ledger_module or load_ledger_module()
    entries = _chain_entries(mod)
    find_call(call_seq, entries)
    assert_not_already_terminal(call_seq, entries)

    detail = json.dumps(grade_payload(call_seq, outcome), sort_keys=True, ensure_ascii=False)
    return mod.append(actor, GRADE_ACT, detail, ts)


def parse_grade_detail(detail: str) -> dict:
    """Read a sealed grade's detail back out. Read-only — this function
    returns a fresh dict; mutating it does not touch the chain."""
    payload = json.loads(detail)
    if not isinstance(payload, dict):
        raise GradingError(f"grade detail is not a JSON object: {payload!r}")
    if set(payload.keys()) != {"call_seq", "outcome"}:
        raise GradingError(f"not a well-formed grade payload: {sorted(payload.keys())}")
    return dict(payload)


def load_claim_payload(detail: str, error_cls: type[Exception]) -> dict:
    """Parse a `predict` entry's own `detail` (the claim payload a cadence
    module built, not a grade's) back into a dict, raising `error_cls` if it
    parses to anything other than a JSON object.

    Found live by the same AST-hash sweep that pulled `time_utils.
    parse_ts`/`load_snapshots`/`record_snapshot`/`reject_malformed` out of
    the 25 `*_cadence.py` siblings: `autograde.py` and every one of its 25
    `oracle_engine/*_autograde.py` siblings (`star_autograde.py`,
    `tag_autograde.py`, and 23 more) carried its own private
    `_load_claim_payload`, byte-identical control flow (`json.loads`, then
    reject anything that isn't a dict), differing only in which module-local
    `*AutogradeError` it raised — the same "differs only in the error class"
    shape `time_utils.record_snapshot`/`reject_malformed` already solved for
    the cadence family, via the identical fix: the varying piece becomes an
    explicit parameter (`error_cls`), not an assumed name-import. Not a bare
    name rebinding, since each sibling raises its own error class on a bad
    payload and every sibling already imports this module (`from
    oracle_engine import grading`) for `existing_grades`/`parse_grade_detail`/
    `TERMINAL_OUTCOMES`/`seal_grade`. Each sibling keeps a thin
    `_load_claim_payload(detail)` wrapper with its own default `error_cls`,
    delegating the actual parse-and-validate logic here — `tests/
    test_grading.py`'s `LoadClaimPayloadDelegatesCase` proves every sibling's
    wrapper genuinely calls through (not a reinlined copy) and that the
    right error class still surfaces on a non-dict payload."""
    payload = json.loads(detail)
    if not isinstance(payload, dict):
        raise error_cls(f"claim payload is not a JSON object: {payload!r}")
    return payload
