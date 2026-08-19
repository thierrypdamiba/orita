"""The shared "blocked by #N" / "blocked on #N" marker law.

`unblocked-issue-still-open/detector.py` (task 593, the sixty-first real
recipe) first wrote the regex that reads an issue's own body for a
"blocked by #N" / "blocked on #N" marker -- pure prose, no GitHub
auto-anything behind it at all, the same "no auto-close mechanism exists
for this at all" absence `duplicate_markers.py` already proved for a
different claim word. `unblocked-pr-still-open/detector.py` (ROADMAP.md
#869) needs the identical grammar for a second data source (a pull
request's own body instead of an issue's) -- the exact "second file,
second hand-typed copy" shape `tools/duplicate_regex_check.py` (task 397)
exists to catch, this time for the blocker-marker family rather than the
duplicate-marker one it was first written against.

This module is the one real place the marker grammar lives. Both
recipes' detectors import `BLOCKER_MARKER_RE`/`named_blocker_of` from
here and bind them to their own module-level `_named_blocker_of` names,
so neither recipe's own code, its `recipe.json`, nor its existing tests
-- which call `detector._named_blocker_of(...)` directly -- have to
change shape. Mirrors `duplicate_markers.py`'s own extraction exactly:
"write it here first, extract to a shared module only once a second
recipe needs the identical grammar" -- `unblocked-issue-still-open`'s own
docstring named that discipline explicitly the day it shipped as the
grammar's first (and, until now, only) user.

Pure, no I/O, no seam-engine imports of its own besides `negation` --
the same small-boring-depended-on-by-everything shape as
`duplicate_markers.py`, `references.py`, and `pr_claims.py`.

The negation handling (`_NEGATION_PREFIX_WINDOW`, the `finditer`-and-skip
loop) is copied in shape, not in code, from `duplicate_markers.py`'s own
fix for task 612's false-positive: a body that explicitly denies still
being blocked ("not blocked by #10 anymore", "no longer blocked by #10")
must not be read as naming a live blocker anyway. `unblocked-issue-still-
open/detector.py` already carried this fix locally before this
extraction; moving it here changes no behavior, only where the one real
copy lives.
"""
from __future__ import annotations

import re

from seam_engine.negation import is_negated

# "Blocked by #900" / "blocked on #903" / "Blocked: #905" / "blocked #905"
# all match, mirroring `duplicate_markers.DUPLICATE_MARKER_RE`'s own shape
# for a genuinely different claim word. The leading `\b` means "unblocked
# #N" (a real, opposite-meaning word that contains "blocked" as a literal
# substring) never matches -- there is no word boundary between "un" and
# "blocked" for `\b` to catch, so this never fires on it.
BLOCKER_MARKER_RE = re.compile(r"\bblocked\s*(?:by|on|:)?\s+#(\d+)\b", re.IGNORECASE)

# "isn't " / "no longer " are the longest realistic negated prefixes a
# mortal types right in front of "blocked"; a little extra slack covers a
# comma too, without reaching back so far it starts catching a negation
# that belongs to an earlier, unrelated clause -- the identical window
# `duplicate_markers.py` and `unblocked-issue-still-open/detector.py`
# (pre-extraction) both already used for their own negated-marker checks.
_NEGATION_PREFIX_WINDOW = 16


def named_blocker_of(body: str) -> int | None:
    """The number named as this body's own blocker, or None if it names no
    (unnegated) blocker marker at all. A blocker marker whose immediately
    preceding words negate it ("not blocked by #10 anymore", "no longer
    blocked by #10") is skipped, and the search continues to the next
    candidate -- see this module's own docstring for the reasoning
    `unblocked-issue-still-open/detector.py` first worked out live."""
    for match in BLOCKER_MARKER_RE.finditer(body):
        if is_negated(body, match.start(), _NEGATION_PREFIX_WINDOW):
            continue
        return int(match.group(1))
    return None
