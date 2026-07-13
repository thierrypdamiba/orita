"""Non-advice-shaped copy — the lint pass a call must clear before it renders. (ROADMAP #33)

`oracle/SCOPES.md` states the scope-level half of this guarantee: no tool
here can act on money, ever. This module states the other half, in code: no
*sentence* here is allowed to sound like an instruction either, even though
nothing downstream could execute one. Two independent locks on the same
door, per SCOPES.md clause 2.

Mirrors `fencepost/seam_engine/audit.py`'s discipline exactly: a pure,
deterministic function that grades a claim against a fixed law, returns a
`checks` list of `(label, passed)` pairs, and a caller (`render_call`) that
refuses to produce any output at all if the claim doesn't clear the bar —
"rejected before it can render," not rejected-but-shown-with-a-warning.

Two failure classes, mirroring the two axes named in ROADMAP.md task 33:

1. **Instruction-phrased.** "Buy," "sell," "you should," "invest in" — a
   forecaster describes what might happen; a broker tells you what to do.
   This desk is only ever the first one (SCOPES.md, `docs/oracle-desk.md`).
2. **Unlabeled certainty.** "Guaranteed," "certain," "can't lose" — language
   that claims a confidence this desk didn't actually seal a number for.
   `oracle_engine.prediction` already requires every sealed call to carry a
   `confidence` field; this catches the copy that talks past that field,
   in either direction: no number sealed at all, or words overclaiming past
   whatever number was.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Verbs and phrases a broker uses, never a forecaster. Word-boundaried so
# "seller" doesn't trip "sell" and "unguaranteed"/"uncertain" don't trip
# their bare roots — this lints the claim's phrasing, not its vocabulary.
_INSTRUCTION_PATTERNS = [
    re.compile(r"\byou should\b", re.IGNORECASE),
    re.compile(r"\byou must\b", re.IGNORECASE),
    re.compile(r"\bbuy\b", re.IGNORECASE),
    re.compile(r"\bsell\b", re.IGNORECASE),
    re.compile(r"\binvest in\b", re.IGNORECASE),
    re.compile(r"\bshort\b", re.IGNORECASE),
    re.compile(r"\bgo long\b", re.IGNORECASE),
    re.compile(r"\bnow is the time to\b", re.IGNORECASE),
]

# Certainty claimed in prose rather than in the sealed confidence field.
_CERTAINTY_PATTERNS = [
    re.compile(r"\bguaranteed?\b", re.IGNORECASE),
    re.compile(r"\bwill definitely\b", re.IGNORECASE),
    re.compile(r"\bcertain(ly)?\b", re.IGNORECASE),
    re.compile(r"\bsure thing\b", re.IGNORECASE),
    re.compile(r"\bcan'?t lose\b", re.IGNORECASE),
    re.compile(r"\b100% (chance|certain)\b", re.IGNORECASE),
    re.compile(r"\bno doubt\b", re.IGNORECASE),
]


class CopyRejected(ValueError):
    """A call phrased as an instruction, or claiming unlabeled certainty.
    Refused before a single character of it renders."""


@dataclass
class LintResult:
    claim: str
    confidence: float | None
    checks: list[tuple[str, bool]]

    @property
    def ok(self) -> bool:
        return all(passed for _, passed in self.checks)

    @property
    def reason(self) -> str:
        return "; ".join(f"{'OK' if p else 'FAIL'} {label}" for label, p in self.checks)


def _hits(patterns: list[re.Pattern], text: str) -> list[str]:
    return [p.pattern for p in patterns if p.search(text)]


def lint_claim(claim: str, confidence: float | None) -> LintResult:
    """Grade one claim against the non-advice-shaped bar. Pure: makes no
    network call, writes nothing, only reads the two values it's given —
    same shape as `audit.py`'s `_audit_primary`."""
    if not isinstance(claim, str) or not claim.strip():
        raise CopyRejected("claim must be a non-empty string")

    instruction_hits = _hits(_INSTRUCTION_PATTERNS, claim)
    certainty_hits = _hits(_CERTAINTY_PATTERNS, claim)

    checks: list[tuple[str, bool]] = [
        (
            "not phrased as an instruction (\"buy\", \"sell\", \"you should\", ...)",
            not instruction_hits,
        ),
        (
            "carries no unlabeled-certainty language (\"guaranteed\", \"certain\", ...)",
            not certainty_hits,
        ),
        (
            "confidence is labeled",
            confidence is not None,
        ),
    ]
    return LintResult(claim=claim, confidence=confidence, checks=checks)


def enforce_copy(claim: str, confidence: float | None) -> LintResult:
    """Raise `CopyRejected` if the claim fails any check; otherwise return
    the passing result. The one function every render path must call
    first."""
    result = lint_claim(claim, confidence)
    if not result.ok:
        raise CopyRejected(result.reason)
    return result


def render_call(actor: str, claim: str, confidence: float | None, ts: str) -> str:
    """Render one call's public text. `enforce_copy` runs before a single
    character of output is built — a rejected claim produces no partial
    render, no truncated string, nothing at all, only the raised
    `CopyRejected`."""
    enforce_copy(claim, confidence)
    return f"[{ts}] {actor}: \"{claim}\" (confidence {confidence:.2f})"
