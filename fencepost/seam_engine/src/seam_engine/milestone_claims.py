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

This module is the one real place the grammar now lives. All three
recipes that read a "milestone #N" claim -- `milestone-closed-never-
released`, `release-claims-open-milestone`, and `milestone-closed-not-
tweeted` -- import `MILESTONE_CLAIM_RE`/`claimed_milestone_numbers` from
here and bind them to their own existing module-level names, so none of
their `recipe.json`s, fixtures, or existing tests (which call
`detector._claimed_milestone_numbers(...)` directly) have to change
shape.

Pure, no I/O, no seam-engine imports of its own -- same shape as
`references.py`.
"""
from __future__ import annotations

import re

# A release/tweet/anything else "claims" a milestone by naming its number
# this way. Deliberately its own grammar, distinct from the PR-claim regex
# (ships/includes/merges/via #N) and the closing-keyword grammar
# (fixes/closes/resolves #N) the issue-side recipes reuse -- a milestone is
# neither a PR nor an issue, and GitHub gives it no auto-close-style
# keyword at all.
MILESTONE_CLAIM_RE = re.compile(r"\bmilestone\s+#(\d+)\b", re.IGNORECASE)


def claimed_milestone_numbers(text: str) -> list[int]:
    """Every milestone number `text` claims via a `milestone #N` phrase, in
    the order they appear. A bare `#N` with no preceding literal word
    "milestone" never appears in the result at all -- see
    `MILESTONE_CLAIM_RE`'s own comment for why."""
    return [int(n) for n in MILESTONE_CLAIM_RE.findall(text)]
