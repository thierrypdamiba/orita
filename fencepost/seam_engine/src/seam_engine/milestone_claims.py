"""The shared `milestone #N` claim-phrase law.

`milestone-closed-never-released/detector.py` (task 383) first wrote the
regex that recognizes a release naming a milestone by number ("milestone
#N" -- GitHub gives a milestone no auto-close-style keyword of its own, so
this recipe invented its own claim grammar rather than overloading the
issue-side closing-keyword one or the PR-side ships/includes/merges/via
one). `release-claims-open-milestone/detector.py` (task 385) needed the
identical grammar for the inverse check and said so plainly in its own
comment -- "Mirrors milestone-closed-never-released/detector.py's own
_CLAIM_RE verbatim" -- but that comment was never backed by an import: the
regex and its `_claimed_milestone_numbers` helper were retyped a second
time, with nothing connecting either copy to the other. This is the exact
"two independently written regexes... drifting apart" shape task 389
found and fixed for `#N` extraction (see `references.py`'s own docstring)
-- found here a second time, before a third recipe could make it worse,
by reading both existing detectors side by side rather than trusting
either one's own comment about itself.

This module is the one real place the grammar now lives. Every recipe
that reads a "milestone #N" claim imports
`MILESTONE_CLAIM_RE`/`claimed_milestone_numbers` from here and binds them
to its own existing module-level names, so none of their `recipe.json`s,
fixtures, or existing tests (which call
`detector._claimed_milestone_numbers(...)` directly) have to change
shape.

Pure, no I/O, no seam-engine imports of its own -- same shape as
`references.py`.

Task 613 (Retrya): `claimed_milestone_numbers` used to be a bare
`MILESTONE_CLAIM_RE.findall`, no negation check at all -- the sibling bug
to `pr_claims.py`'s own (fixed alongside it, same task). Reproduced live
before touching anything: `claimed_milestone_numbers("We haven't hit
milestone #7 this sprint.")` returned `[7]` -- a sentence explicitly
denying a milestone was HIT read as claiming it was, the same "unnegated
claim laundered past a nearby negation" shape tasks 609 (`gateway.py`),
610 (`thanks.py`), and 612 (`duplicate_markers.py`) each already found and
fixed in a different module this shift. Real blast radius: twelve recipes
import this function across commit/issue-comment/linear-comment/mention/
milestone/readme/release/review-comment/slack/tweet surfaces, plus
`milestone-closed-never-released` and `milestone-closed-not-tweeted` --
any of them reading prose that explicitly denies a milestone being hit
would have surfaced a false gap off a denial, not a claim. Fixed the same
way `pr_claims.py` was fixed: walk every candidate (`finditer`, not
`findall`) and skip any whose immediately preceding few words carry
`not`/`never`/`no` or an `n't` contraction as a whole word/token, falling
through to the next candidate rather than dropping the whole result --
so "not milestone #7, but genuinely milestone #12" still returns `[12]`,
and "haven't hit milestone #7" now correctly returns `[]`. Deliberately
narrow, same residual-limit discipline `thanks.py`'s and
`duplicate_markers.py`'s own comments keep: the negation check only looks
at the words immediately in front of the literal word "milestone" itself,
not the whole body -- a denial separated from its own claim by more than
a few words in front of it can still slip through (a phrase like "we do
not expect to complete milestone #7 this cycle" with several words
between the negation and "milestone" is the documented residual gap, the
same shape `thanks.py`'s own comment already names for "there's no need,
but thanks @user").

The negation pattern itself lives in `seam_engine.negation`
(`NEGATION_PREFIX_RE`/`is_negated`), not a local `re.compile(...)` here --
this module and `pr_claims.py` both needed the identical pattern this
same task, and hand-retyping it a second and third time (on top of
`duplicate_markers.py`'s own copy) is exactly the shape
`tools/duplicate_regex_check.py` caught live before this task shipped.
"""
from __future__ import annotations

import re

from seam_engine.negation import is_negated

# A release/tweet/anything else "claims" a milestone by naming its number
# this way. Deliberately its own grammar, distinct from the PR-claim regex
# (ships/includes/merges/via #N) and the closing-keyword grammar
# (fixes/closes/resolves #N) the issue-side recipes reuse -- a milestone is
# neither a PR nor an issue, and GitHub gives it no auto-close-style
# keyword at all.
MILESTONE_CLAIM_RE = re.compile(r"\bmilestone\s+#(\d+)\b", re.IGNORECASE)

# "haven't hit " is a realistic negated-verb prefix mortals type right in
# front of "milestone"; a little extra slack covers a comma too without
# reaching back so far that it starts catching a negation that belongs to
# an earlier, unrelated clause -- same reasoning as `pr_claims.py`'s own
# `_NEGATION_PREFIX_WINDOW`.
_NEGATION_PREFIX_WINDOW = 20


def claimed_milestone_numbers(text: str) -> list[int]:
    """Every milestone number `text` claims via a `milestone #N` phrase, in
    the order they appear. A bare `#N` with no preceding literal word
    "milestone" never appears in the result at all -- see
    `MILESTONE_CLAIM_RE`'s own comment for why. A claim whose immediately
    preceding words negate it ("haven't hit milestone #7", "never
    milestone #12") is skipped, and the scan continues to the next
    candidate -- see this module's own docstring (task 613) for the live
    reproduction."""
    numbers = []
    for match in MILESTONE_CLAIM_RE.finditer(text):
        if is_negated(text, match.start(), _NEGATION_PREFIX_WINDOW):
            continue
        numbers.append(int(match.group(1)))
    return numbers
