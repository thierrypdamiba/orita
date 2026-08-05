#!/usr/bin/env python3
"""Task 106. Ogun's third door on the same wall.

ROADMAP.md's "Non-negotiable design constraints" names five rules. Tasks
23/25 (`tools/oath_badge.py`), the self-audit tally (`fencepost/seam_engine/
src/seam_engine/audit.py`), `draftback.py`'s `FORBIDDEN_DELIVERY_ACTIONS`,
and task 105 (`tools/no_grading_check.py`) gave four of the five (read-only,
false-positives-fatal, written-back, no-grading) a running check. Constraint
#4 -- "Arcade is the hero, shown safely -- per-user OAuth, least privilege,
revocable, audit-logged. This protects Arcade's look; treat it as the
point." -- never got one. STRATEGY.md's own "Safety" section names the
concrete failure mode this check exists to catch: real user data must be
"handled at the safest possible setting" and the town must never ask a
mortal to hand over a credential outside Arcade's own per-user OAuth
handshake (`fencepost/CONNECT.md` step 3: "Arcade mints a token scoped to
*you*... callable only through *your* gateway"). A page that asked a human
to paste a raw API key or password directly would be the single most
concrete way this constraint could ever be broken in public -- and, unlike
constraint #2's blame/grading prose, nothing in the codebase checked for it.

This module does what no prior check did: a read-only, local-filesystem-
only scan (mirrors `no_grading_check.find_violations`'s shape -- same
SEARCH TECHNIQUE, sentence-scoped negation lookback, same quoted-citation
guard) of every public `.md`/`.html` file for the shape of a
direct-credential-handoff ask -- "paste your API key", "share your token",
"send us your password" --
the one move that routes a human's credential around Arcade's OAuth screen
entirely instead of through it. Bare mentions of "token"/"key"/"password"
are NOT the pattern (`CONNECT.md` uses "token" honestly six times
describing what Arcade itself mints and scopes) -- only a live ask for the
human to hand one over directly is.

Usage:
    python3 tools/arcade_hero_check.py check
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan_files  # noqa: E402
import text_patterns  # noqa: E402
import violation_format  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

_SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".safeword", ".claude", ".agents"}
_SCAN_EXTENSIONS = (".md", ".html")

# The credential nouns Arcade's own OAuth handshake mints and scopes on a
# human's behalf (CONNECT.md step 3) -- never something the town should ask
# a mortal to hand over directly, in any of these shapes.
_CREDENTIAL_NOUNS = r"(?:api\s+key|password|credentials?|token|secret)"

# Each pattern names the exact CREDENTIAL-HANDOFF verb+noun shape, not a
# bare noun -- "token" alone is this repo's own constant honest vocabulary
# (CONNECT.md describes what Arcade mints/scopes six times), so only a live
# ask for a human to directly hand one over is a pattern here.
_PATTERNS = [
    (
        "paste your credential",
        re.compile(rf"\bpaste\s+(?:your|the)\s+{_CREDENTIAL_NOUNS}\b", re.IGNORECASE),
    ),
    (
        "share your credential",
        re.compile(rf"\bshare\s+(?:your|the)\s+{_CREDENTIAL_NOUNS}\b", re.IGNORECASE),
    ),
    (
        "send us your credential",
        re.compile(
            rf"\bsend\s+(?:us\s+|me\s+)?your\s+{_CREDENTIAL_NOUNS}\b", re.IGNORECASE
        ),
    ),
    (
        "email us your credential",
        re.compile(
            rf"\bemail\s+(?:us\s+|me\s+)?your\s+{_CREDENTIAL_NOUNS}\b", re.IGNORECASE
        ),
    ),
    (
        "enter your credential",
        re.compile(rf"\benter\s+your\s+{_CREDENTIAL_NOUNS}\b", re.IGNORECASE),
    ),
    (
        "give us your credential",
        re.compile(
            rf"\bgive\s+(?:us\s+|me\s+)?your\s+{_CREDENTIAL_NOUNS}\b", re.IGNORECASE
        ),
    ),
]

_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_LOOSE
# Only the SEARCH TECHNIQUE (sentence-scoped, prefix-only negation lookback
# -- see `_is_negated_or_predictive` below) is shared with
# `no_grading_check.py`. The word list itself is NOT a byte-for-byte
# mirror (this file's copy adds "nobody"/"without" and lacks
# "will"/"would"/"wouldn't") -- `tools/text_patterns.py`'s own task-418
# docstring already classifies this file as one of four that tune their
# own negation list on purpose, not a consumer of the shared
# `NEGATION_CUES_STANDARD` constant. Task 467 corrected this module's own
# docstring (and this comment) after task 462 found and fixed the
# identical false "mirrors ... exactly" claim in `rider_check.py` but
# never checked whether it survived here too.
_NEGATION_CUES = re.compile(
    r"\b(never|not|won't|wasn't|isn't|doesn't|didn't|n't|no|nobody|without)\b",
    re.IGNORECASE,
)
_QUOTE_CHARS = set('"\'“‘')


# Task 513: consolidated into tools/scan_files.py -- carried the identical
# body as `hand_lore_check.py`/`star_covenant_check.py`/`rider_check.py`'s
# own `_iter_public_files` under a different name, invisible to a
# name-sensitive AST-hash duplicate scan for that reason alone (confirmed
# byte-for-byte identical by direct diff). `_iter_scan_files` now names the
# shared function object, not a local copy; tests/test_scan_files.py
# asserts this.
_iter_scan_files = scan_files.iter_public_files


def _is_negated_or_predictive(text: str, match_start: int) -> bool:
    """Same-sentence-only guard, same spirit as
    `no_grading_check._is_negated_or_predictive`: a sentence explaining that
    the town NEVER asks for a credential ("we will never ask you to paste
    your API key") must not itself count as a violation. Scoped to the
    current sentence (or paragraph, for a hard-wrapped one) only, so an
    unrelated negation several sentences earlier can never mask a real,
    present-tense ask.

    `_SENTENCE_BOUNDARY` includes `;` alongside `[.!?]`/`\\n{2,}` -- a
    semicolon joins two independent clauses exactly the way a period does,
    and this module's own docstring already claims it mirrors
    `no_grading_check.find_violations`'s SEARCH TECHNIQUE, but it was
    copied before task 202 added `;` to that module's boundary (task 200
    first, in `star_covenant_check.py`), so this copy carried the identical
    gap forward: an earlier, unrelated negation/prediction cue joined by `;`
    instead of `.` to a real, present-tense ask on the other side still fell
    inside the same "sentence" window and silently suppressed it. (Task 467:
    the SENTENCE-SCOPING technique is shared with `no_grading_check.py` --
    the `_NEGATION_CUES` word list itself is NOT: this file's copy adds
    "nobody"/"without" and lacks "will"/"would"/"wouldn't", one of four
    files `tools/text_patterns.py`'s own task-418 docstring names as tuning
    its own negation list on purpose.)"""
    window_start = 0
    for boundary in _SENTENCE_BOUNDARY.finditer(text, 0, match_start):
        window_start = boundary.end()
    sentence_so_far = text[window_start:match_start]
    return bool(_NEGATION_CUES.search(sentence_so_far))


def _is_quoted_citation(text: str, match_start: int) -> bool:
    """Documentation ABOUT this check (this module's own docstring,
    ROADMAP.md's task text quoting the rule, a test file) legitimately
    cites the exact credential-handoff phrases it hunts for as quoted
    examples. A phrase opening immediately on a quote mark is a cited
    example, not a live ask."""
    return match_start > 0 and text[match_start - 1] in _QUOTE_CHARS


def _find_violations_uncached(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    """Task 106: read-only scan of every public .md/.html file in the town
    checkout for the direct-credential-handoff shape ROADMAP.md's constraint
    #4 forbids -- a live ask routing a human's credential around Arcade's
    own per-user OAuth screen. Returns a list of violation records, empty
    when the town has never once asked a mortal to hand over a credential
    directly. Never writes."""
    violations = []
    for path in _iter_scan_files(orita_dir):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in _PATTERNS:
            for m in pattern.finditer(text):
                if _is_negated_or_predictive(text, m.start()) or _is_quoted_citation(text, m.start()):
                    continue
                line_no = text.count("\n", 0, m.start()) + 1
                snippet = text[max(0, m.start() - 20):m.end() + 20].replace("\n", " ").strip()
                violations.append({
                    "file": path,
                    "line": line_no,
                    "pattern": label,
                    "snippet": snippet,
                })
    return violations


# Task 513: consolidated into tools/scan_files.py -- five sibling checks
# shared this exact memoize-by-orita_dir shape (task 367's own fix,
# reimplemented five times over). find_violations/clear_cache now name the
# shared factory's output, not a local copy; tests/test_scan_files.py
# asserts every sibling's path_memoize call came from the one shared
# function.
find_violations, clear_cache = scan_files.path_memoize(_find_violations_uncached, DEFAULT_ORITA_DIR)


def format_violations(violations: list) -> str:
    return violation_format.format_violations(
        "arcade hero check",
        violations,
        "pattern",
        "no direct-credential-handoff ask found in any public file "
        "(constraint #4 holds, Arcade's per-user OAuth is the only door)",
        "ROADMAP.md constraint #4 broken",
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
