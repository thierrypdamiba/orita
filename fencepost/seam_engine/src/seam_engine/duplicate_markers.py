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
"""
from __future__ import annotations

import re

# "Duplicate of #700" / "dup of #703" / "Duplicate: #705" / "duplicate #705"
# all match. A `\b` boundary right after "dup" rules out "dupe"/"duping" so
# ordinary prose never becomes a false candidate.
DUPLICATE_MARKER_RE = re.compile(r"\bdup(?:licate)?\s*(?:of|:)?\s+#(\d+)\b", re.IGNORECASE)

# A negation word (or an "n't" contraction: isn't/wasn't/doesn't/...) sitting
# immediately in front of a duplicate marker turns it into a denial rather
# than a claim -- see this module's own docstring (task 612) for the live
# reproduction.
_NEGATION_PREFIX_RE = re.compile(r"\b(?:not|never|no)\b|n't\b", re.IGNORECASE)

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
        prefix = body[max(0, match.start() - _NEGATION_PREFIX_WINDOW) : match.start()]
        if _NEGATION_PREFIX_RE.search(prefix):
            continue
        return int(match.group(1))
    return None
