"""The prediction schema — the Oracle Desk's one narrow write. (ROADMAP #31)

A prediction is a call sealed to `tools/ledger.py`'s append-only chain the
moment it's made, before the outcome exists to grade against. That ordering
is the whole product: docs/oracle-desk.md promises "no hindsight edits — the
timestamp is the whole point," and oracle/SCOPES.md swears the ledger write
is bounded to "a sealed call or a sealed grade — no destination parameter,
no external account, no edit path."

This module is where that promise becomes code, not just prose:

1. **The schema is exactly three fields.** `actor`, `claim`, `confidence`.
   Nothing else — no `id` a caller could reuse to reference "the same"
   prediction differently, no status field, no free-form metadata bag that
   could smuggle in an edit under a new name.
2. **There is no edit function.** Not "an edit function that's disabled" —
   there is no function in this file whose name or shape could rewrite a
   sealed entry. `tools/test_prediction.py`'s doctrine test greps this
   module for exactly that absence, the same "prove it, don't just claim
   it" discipline `seam_engine/draftback.py` holds itself to.
3. **Sealing is delegated, not reimplemented.** `seal_prediction` calls
   `tools/ledger.py`'s own `append()` — the identical hash-chained function
   every other act in the town's history is sealed through. A tampered
   prediction breaks `ledger.py verify()` exactly like a tampered gap or a
   tampered decree; predictions get no special leniency.
4. **Grading is a different act, linked by seq, not a rewrite.** ROADMAP
   task 32 (Ogun) adds `act == "grade"` entries that reference the original
   prediction's `seq` — the sealed call itself never changes shape once
   written.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from types import ModuleType
from typing import Any

PREDICTION_ACT = "predict"

_MAX_CLAIM_LEN = 2000

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "tools"
)


class PredictionError(ValueError):
    """A call that does not meet the schema. Refused before it is sealed."""


def load_ledger_module(tools_dir: str = _TOOLS_DIR) -> ModuleType:
    """Load the town's real `tools/ledger.py` by path, fresh each call.

    Dynamic loading (not a package import) so this file never needs
    `tools/` on `sys.path` and a test can point it at a scratch ledger
    file without touching the live chain — the same pattern
    `oracle/oracle_engine/tests/test_scopes_doctrine.py` already uses to
    load `tools/oath_badge.py`.
    """
    path = os.path.join(tools_dir, "ledger.py")
    spec = importlib.util.spec_from_file_location("_oracle_ledger", path)
    if spec is None or spec.loader is None:
        raise PredictionError(f"cannot load ledger module from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def validate_claim(claim: str) -> None:
    if not isinstance(claim, str):
        raise PredictionError("claim must be a string")
    if not claim.strip():
        raise PredictionError("claim must not be empty")
    if len(claim) > _MAX_CLAIM_LEN:
        raise PredictionError(f"claim exceeds {_MAX_CLAIM_LEN} characters")


def validate_confidence(confidence: Any) -> None:
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise PredictionError("confidence must be a number")
    if not math.isfinite(confidence):
        raise PredictionError("confidence must be finite")
    if not (0.0 < float(confidence) <= 1.0):
        raise PredictionError("confidence must be in (0.0, 1.0] — a call with 0 confidence is not a call")


def validate_actor(actor: str) -> None:
    if not isinstance(actor, str) or not actor.strip():
        raise PredictionError("actor must be a non-empty string")


def prediction_payload(claim: str, confidence: float) -> dict:
    """The sealed detail shape. Exactly two keys, sorted, no room to grow
    an edit-shaped field in by accident."""
    return {"claim": claim, "confidence": float(confidence)}


def seal_prediction(
    actor: str,
    claim: str,
    confidence: float,
    ts: str | None = None,
    ledger_module: ModuleType | None = None,
) -> dict:
    """Validate and seal a prediction as the next entry on the town's chain.

    Raises `PredictionError` before anything is written if the schema is
    violated. Once written, the returned entry (and the file it was
    appended to) is the only record of this call — there is no function in
    this module that takes a `seq` and changes what it says.
    """
    validate_actor(actor)
    validate_claim(claim)
    validate_confidence(confidence)

    if ts is None:
        raise PredictionError("ts is required — a prediction is timestamped at the moment of sealing, never defaulted silently")

    mod = ledger_module or load_ledger_module()
    detail = json.dumps(prediction_payload(claim, confidence), sort_keys=True, ensure_ascii=False)
    return mod.append(actor, PREDICTION_ACT, detail, ts)


def parse_prediction_detail(detail: str) -> dict:
    """Read a sealed prediction's detail back out. Read-only — this
    function returns a fresh dict; mutating it does not touch the chain."""
    payload = json.loads(detail)
    if set(payload.keys()) != {"claim", "confidence"}:
        raise PredictionError(f"not a well-formed prediction payload: {sorted(payload.keys())}")
    return dict(payload)
