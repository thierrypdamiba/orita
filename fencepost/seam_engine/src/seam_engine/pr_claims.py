"""The shared "ships/includes/merges/via #N" PR-claim-phrase law.

`release-claims-unmerged-pr/detector.py` (task 378) first wrote the regex
that recognizes a release body claiming a pull request by number.
`merged-pr-never-released/detector.py` (task 381) needed the identical
grammar for the inverse check and said so plainly in its own comment -- "Identical to
release-claims-unmerged-pr's own _CLAIM_RE, on purpose: one law for what
counts as a release 'claiming' a PR, not two copies of it drifting apart
between the two recipes that both read release bodies" -- but that comment
was never backed by an import: the regex and its `_claimed_pr_numbers`
helper were retyped a second time in the second file, with nothing
connecting either copy to the other.

This is the exact "two independently written regexes... drifting apart"
shape task 389 found and fixed for `#N` extraction (`seam_engine.
references`) and task 390 found and fixed a second time for the
"milestone #N" claim phrase (`seam_engine.milestone_claims`) -- found here
a third time, in the one family neither of those two sweeps actually
touched, by reading both PR-claim detectors side by side rather than
trusting either one's own comment about itself.

This module is the one real place the grammar now lives. Both recipes
that read a "ships/includes/merges/via #N" claim --
`release-claims-unmerged-pr` and `merged-pr-never-released` -- import
`PR_CLAIM_RE`/`claimed_pr_numbers` from here and bind them to their own
existing module-level `_CLAIM_RE`/`_claimed_pr_numbers` names, so none of
their `recipe.json`s, fixtures, or existing tests (which call
`detector._claimed_pr_numbers(...)` directly) have to change shape. A
third recipe that ever needs the same PR-claim grammar reuses this module
too, rather than writing a third copy.

Pure, no I/O, no seam-engine imports of its own -- same shape as
`references.py` and `milestone_claims.py`.
"""
from __future__ import annotations

import re

# A release body "claims" a PR by naming its number this way. Anchored on
# a real verb, not a bare "#N" (that broader, unanchored shape is
# references.py's own seam, watching a different question) -- a release
# body mentioning "#N" in passing prose ("see #N for background") is not a
# shipped-it claim. Deliberately its own grammar, distinct from the
# closing-keyword grammar (fixes/closes/resolves #N) the issue-side
# recipes reuse and the "milestone #N" phrase the milestone-side recipes
# reuse -- a PR is neither an issue nor a milestone.
PR_CLAIM_RE = re.compile(r"\b(?:ships?|includes?|merges?|via)\s+#(\d+)\b", re.IGNORECASE)


def claimed_pr_numbers(text: str) -> list[int]:
    """Every PR number `text` claims via a ships/includes/merges/via #N
    phrase, in the order they appear. A bare `#N` with no preceding claim
    verb never appears in the result at all -- see `PR_CLAIM_RE`'s own
    comment for why."""
    return [int(n) for n in PR_CLAIM_RE.findall(text)]
