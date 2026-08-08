"""The shared "duplicate of #N" marker law.

`duplicate-issue-still-open/detector.py` (task 373-area, the seventh real
recipe) first wrote the regex that reads an issue's own body for a
"duplicate of #N" / "dup of #N" marker -- pure prose, no GitHub auto-close
mechanism behind it at all. `duplicate-pr-still-open/detector.py` (task 400)
needs the identical grammar for a second data source (a pull request's body
instead of an issue's) -- the exact "second file, second hand-typed copy"
shape `tools/duplicate_regex_check.py` (task 397) now exists specifically to
catch, having already found it five times by hand across other recipe
families (tasks 389/390/393/394/396) before this pattern ever got a chance
to add a sixth instance.

This module is the one real place the marker grammar lives. Both recipes'
detectors import `DUPLICATE_MARKER_RE`/`named_duplicate_of` from here and
bind them to their own module-level `_DUP_RE`/`_named_duplicate_of` names,
so neither recipe's own code, its `recipe.json`, nor its existing tests --
which call `detector._named_duplicate_of(...)` directly -- have to change
shape.

Pure, no I/O, no seam-engine imports of its own -- the same
small-boring-depended-on-by-everything shape as `references.py` and
`pr_claims.py`.

Task 612: a negation word sitting in front of "dup(licate)" turns a
genuine-looking marker into an explicit DENIAL -- "This is not a
duplicate of #700", "isn't a dup of #12" -- the exact false-positive
shape task 610 already fixed for `thanks.py`'s "no thanks @handle": an
unnegated claim must not survive across a nearby negation. Reproduced
live before touching anything: `named_duplicate_of("This is not a
duplicate of #700, unrelated.")` returned `700` -- a body that explicitly
denies being a duplicate was read as naming one anyway, and either
`duplicate-issue-still-open` or `duplicate-pr-still-open` would have
surfaced a false gap ("this open issue/PR's named original already
closed") off a denial, not a marker -- exactly the false-positive shape
Ogun's law (STRATEGY.md) exists to catch. Fixed the same way task 610
fixed `thanks.py`: walk every candidate (`finditer`, not `search`) and
skip any whose immediately preceding few words carry `not`/`never`/`no`
or an `n't` contraction (`isn't`, `wasn't`, `doesn't`, ...) as a whole
word/token, falling through to the next candidate rather than giving up
outright -- so "not a duplicate of #12, but genuinely a duplicate of #45"
still returns 45, and "not a duplicate of #12" now correctly returns
`None`. Deliberately narrow, same residual-limit discipline
`thanks.py`'s own comment keeps: the negation check only looks at the
words immediately in front of the match, not the whole body -- a denial
separated from its own marker by more than a few words in front of it can
still slip through.

Task 613: `_NEGATION_PREFIX_RE` above used to be this module's own local
`re.compile(...)`. `pr_claims.py` and `milestone_claims.py` each needed
the identical negation fix this same task, and both got hand-retyped with
this exact pattern instead of importing it -- the very "two [now three]
independently written regexes... drifting apart" shape this whole family
of modules exists to prevent, caught live by
`tools/duplicate_regex_check.py` the moment this task ran it, in this
task's own new code before it ever shipped. Moved the pattern itself to
`seam_engine.negation` (one real definition, `is_negated()` doing the
prefix-window check too) and this module now imports both; only the
window size (`_NEGATION_PREFIX_WINDOW`, unchanged at 16) and the
`finditer`-and-skip loop stay local, since those are this module's own
tuned behavior, not the shared law. `tools/duplicate_regex_check.py`
confirmed clean after the move.
"""
from __future__ import annotations

import re

from seam_engine.negation import is_negated

# "Duplicate of #700" / "dup of #703" / "Duplicate: #705" / "duplicate #705"
# all match. A `\b` boundary right after "dup" rules out "dupe"/"duping" so
# ordinary prose never becomes a false candidate.
DUPLICATE_MARKER_RE = re.compile(r"\bdup(?:licate)?\s*(?:of|:)?\s+#(\d+)\b", re.IGNORECASE)

# "isn't a " is the longest realistic negated-article prefix mortals type
# right in front of "duplicate"/"dup"; a little extra slack covers a comma
# too ("no, not a duplicate of #12") without reaching back so far that it
# starts catching a negation that belongs to an earlier, unrelated clause --
# same reasoning as `thanks.py`'s own `_NEGATION_PREFIX_WINDOW`.
_NEGATION_PREFIX_WINDOW = 16


def named_duplicate_of(body: str) -> int | None:
    """The number named as this body's original, or None if it names no
    (unnegated) duplicate marker at all. A duplicate marker whose
    immediately preceding words negate it ("not a duplicate of #12",
    "isn't a dup of #45") is skipped, and the search continues to the next
    candidate -- see this module's own docstring (task 612) for the live
    reproduction."""
    for match in DUPLICATE_MARKER_RE.finditer(body):
        if is_negated(body, match.start(), _NEGATION_PREFIX_WINDOW):
            continue
        return int(match.group(1))
    return None
