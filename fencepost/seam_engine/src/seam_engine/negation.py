"""The shared negation-prefix law used by every claim/marker grammar in
this package.

Task 609 (`gateway.py`'s `is_read_only_capabilities`), task 610
(`thanks.py`'s `thanked_handle`), and task 612 (`duplicate_markers.py`'s
`named_duplicate_of`) each independently found and fixed the same false-
positive shape in a different module this shift: an unnegated claim
laundered past a nearby `not`/`never`/`no`/`n't` sitting right in front of
it. Task 613 found the same bug a fourth and fifth time, in
`pr_claims.py` and `milestone_claims.py`, and this time wrote the fix once
instead of a third time: `duplicate_markers.py`'s own
`_NEGATION_PREFIX_RE = re.compile(r"\\b(?:not|never|no)\\b|n't\\b", ...)`
got hand-retyped, byte-for-byte, into both new call sites -- caught live
by `tools/duplicate_regex_check.py` the moment this task ran it, the exact
"two [now three] independently written regexes... drifting apart" shape
that checker exists to catch, in this task's own new code before it ever
shipped. Rather than leave a fourth/fifth hand-typed copy standing next to
the checker that flags them, this module became the one real place the
negation grammar lives, and `duplicate_markers.py`, `pr_claims.py`, and
`milestone_claims.py` now all import it.

Each caller keeps its OWN window size (`duplicate_markers.py`'s 16,
`pr_claims.py`'s and `milestone_claims.py`'s 20) -- the window is a plain
`int`, not a `re.compile(...)` pattern, so it is not the thing
`duplicate_regex_check.py` polices, and different grammars legitimately
need different amounts of slack in front of their own claim word (see
each caller's own docstring for why its window is sized the way it is).

Pure, no I/O, no seam-engine imports of its own -- same shape as
`references.py`, `milestone_claims.py`, `pr_claims.py`,
`closing_keywords.py`, and `checklist.py`.
"""
from __future__ import annotations

import re

# A negation word (or an "n't" contraction: isn't/wasn't/doesn't/...)
# anywhere in a candidate's immediately-preceding window turns a genuine-
# looking claim/marker into a denial rather than a claim -- see this
# module's own docstring for the live history of where this grammar was
# first written and why it moved here.
NEGATION_PREFIX_RE = re.compile(r"\b(?:not|never|no)\b|n't\b", re.IGNORECASE)


def is_negated(text: str, match_start: int, window: int) -> bool:
    """True if the `window` characters immediately before `match_start` in
    `text` carry a negation word/token -- the shared prefix-window check
    every caller of `NEGATION_PREFIX_RE` performs identically; only the
    window size differs caller to caller."""
    prefix = text[max(0, match_start - window) : match_start]
    return bool(NEGATION_PREFIX_RE.search(prefix))
