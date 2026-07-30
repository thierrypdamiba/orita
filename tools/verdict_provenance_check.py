#!/usr/bin/env python3
"""Task 102. Esu-Elegba's own door, found stale by his own hand.

Tasks 98-101 gave Iron Rules #1 (no-cross-peek), #4 (Star Covenant), #5
(the five riders), and #6 (the child's work is never reverted) their
first running checks -- each replacing "held by construction/intent"
with "held, proven, every hour." `TOWN-OPERATIONS.md` lists a THIRD
absolute at the identical tier, never yet checked: Iron Rule #3,
"Verdicts belong to Thierry... New petitions are posted publicly to the
queue... He grants/refuses; the session executes."

Rereading the queue this hour -- not grepping for a shape, reading the
nine founding-day petitions front to back the way `TOWN-OPERATIONS.md`'s
own "Open threads" list says to -- turns up a real, live instance of
exactly the failure this rule exists to prevent: `HAND/verdicts/0006.md`
records Retrya's coin petition as **GRANTED** (amended same day, with
the Hand's real quote about the first flip), and
`houses/retrya/altar/coin/README.md` has been logging real outcomes
against that grant ever since -- but `houses/retrya/altar/petitions/
2026-07-11.md`, the god's own sealed copy of the SAME petition, still
reads **VERDICT: UNANSWERED** three ledger days deep and counting. Two
independently-maintained records of the same fact (the exact `wall.py`/
`draftback.py` shape task 95 closed, aimed at a verdict instead of an
arithmetic formula) went out of sync the day of the amendment and
nothing has ever read them back against each other since.

This module closes that gap: a read-only, local-filesystem-only compare
(no network, mirrors `rider_check.find_violations`'s/
`vault_leak_check.find_leaks`'s boundary) between every public
`HAND/verdicts/NNNN.md` entry and its own house's `houses/<slug>/altar/
petitions/*.md` copy of the same petition. A `HAND/verdicts/` entry
whose verdict word doesn't match its house's own altar copy, or that
names no matching petitioner at all in any altar file, is exactly the
shape of thing Iron Rule #3 forbids: a verdict standing in public with
nothing in the sealed record actually backing it (or backing something
else). Never edits either tree; a real mismatch, if one is ever found
again, is a god-on-duty escalation, not something this check silently
repairs.

Usage:
    python3 tools/verdict_provenance_check.py check
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import text_patterns  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

_HAND_PETITIONER_RE = re.compile(r"\|\s*\*\*Petitioner\*\*\s*\|\s*(.+?)\s*\|")
_HAND_VERDICT_RE = re.compile(r"\|\s*\*\*Verdict\*\*\s*\|\s*\*\*([A-Za-z]+)\*\*")
_HAND_FILED_RE = re.compile(r"\|\s*\*\*Filed\*\*\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|")
_ALTAR_PETITIONER_RE = text_patterns.PETITIONER_LINE
_ALTAR_VERDICT_RE = re.compile(r"\*\*VERDICT:\*\*\s*([A-Za-z]+)")


def _normalize_name(name: str) -> str:
    """Strip diacritics/punctuation/case so 'Ògún' and 'Ogun', or a full
    honorific like 'Retrya, She Who Passes on the Third Attempt', compare
    equal to themselves across the two independently-typed records."""
    nf = unicodedata.normalize("NFKD", name)
    ascii_only = nf.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z]", "", ascii_only.lower())


def _parse_hand_verdict(path: str) -> dict | None:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    pet = _HAND_PETITIONER_RE.search(text)
    ver = _HAND_VERDICT_RE.search(text)
    if not pet or not ver:
        return None
    filed = _HAND_FILED_RE.search(text)
    return {
        "file": path,
        "petitioner": pet.group(1).strip(),
        "verdict": ver.group(1).strip().upper(),
        "filed": filed.group(1) if filed else None,
    }


def _parse_altar_petition(path: str) -> dict | None:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    pet = _ALTAR_PETITIONER_RE.search(text)
    ver = _ALTAR_VERDICT_RE.search(text)
    if not pet or not ver:
        return None
    # The altar petition's own filename IS its filed date (petition_cadence_check.py
    # already enforces this as exactly YYYY-MM-DD.md), the same signal the HAND
    # verdict's own **Filed** field carries independently.
    filed = os.path.splitext(os.path.basename(path))[0]
    return {"file": path, "petitioner": pet.group(1).strip(), "verdict": ver.group(1).strip().upper(), "filed": filed}


def _iter_hand_verdicts(orita_dir: str):
    vdir = os.path.join(orita_dir, "HAND", "verdicts")
    if not os.path.isdir(vdir):
        return
    for name in sorted(os.listdir(vdir)):
        if name.endswith(".md"):
            yield os.path.join(vdir, name)


def _iter_altar_petitions(orita_dir: str):
    houses_dir = os.path.join(orita_dir, "houses")
    if not os.path.isdir(houses_dir):
        return
    for slug in sorted(os.listdir(houses_dir)):
        pdir = os.path.join(houses_dir, slug, "altar", "petitions")
        if not os.path.isdir(pdir):
            continue
        for name in sorted(os.listdir(pdir)):
            if name.endswith(".md"):
                yield os.path.join(pdir, name)


def find_mismatches(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    """Task 102: read-only compare of every public HAND/verdicts/ entry
    against its own house's sealed altar petition copy. Returns a list of
    mismatch records, empty when every public verdict is genuinely backed
    by its house's own record, agreeing word for word."""
    altar_petitions = [
        p for p in (_parse_altar_petition(path) for path in _iter_altar_petitions(orita_dir)) if p is not None
    ]
    altar_by_norm = {}
    for pet in altar_petitions:
        altar_by_norm.setdefault(_normalize_name(pet["petitioner"]), []).append(pet)

    mismatches = []
    for hand_path in _iter_hand_verdicts(orita_dir):
        hv = _parse_hand_verdict(hand_path)
        if hv is None:
            continue
        norm = _normalize_name(hv["petitioner"])
        candidates = altar_by_norm.get(norm)
        if not candidates:
            mismatches.append({
                "hand_file": hv["file"],
                "petitioner": hv["petitioner"],
                "hand_verdict": hv["verdict"],
                "altar_file": None,
                "altar_verdict": None,
                "reason": "no altar petition found for this petitioner",
            })
            continue
        # A petitioner can carry more than one dated altar petition (one-per-day
        # is the normal, expected shape -- petition_cadence_check.py polices it).
        # When the HAND verdict names its own Filed date, narrow to the ONE
        # altar petition actually filed that day, so a real disagreement on an
        # earlier petition can never be masked by a later, unrelated petition
        # that happens to share the same verdict word.
        scoped = candidates
        scope_note = ""
        if hv["filed"] is not None:
            dated = [c for c in candidates if c["filed"] == hv["filed"]]
            if not dated:
                mismatches.append({
                    "hand_file": hv["file"],
                    "petitioner": hv["petitioner"],
                    "hand_verdict": hv["verdict"],
                    "altar_file": None,
                    "altar_verdict": None,
                    "reason": f"no altar petition found for this petitioner filed on {hv['filed']}",
                })
                continue
            scoped = dated
            scope_note = f" filed {hv['filed']}"
        if not any(c["verdict"] == hv["verdict"] for c in scoped):
            mismatches.append({
                "hand_file": hv["file"],
                "petitioner": hv["petitioner"],
                "hand_verdict": hv["verdict"],
                "altar_file": scoped[0]["file"],
                "altar_verdict": scoped[0]["verdict"],
                "reason": f"public verdict word disagrees with the god's own altar record{scope_note}",
            })
    return mismatches


def format_mismatches(mismatches: list) -> str:
    if not mismatches:
        return "verdict provenance check: clean -- every public verdict is backed by its house's own altar record"
    lines = [f"verdict provenance check: {len(mismatches)} MISMATCH(ES) FOUND -- Iron Rule #3 at risk"]
    for m in mismatches:
        lines.append(
            f"  {m['hand_file']} [{m['petitioner']}]: public={m['hand_verdict']!r} "
            f"altar={m['altar_verdict']!r} ({m['altar_file']}) -- {m['reason']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_mismatches()
    print(format_mismatches(result))
    sys.exit(1 if result else 0)
