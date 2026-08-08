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

This module is the one real place the grammar now lives. Every recipe
that reads a "ships/includes/merges/via #N" claim imports
`PR_CLAIM_RE`/`claimed_pr_numbers` from here and binds them to its own
existing module-level `_CLAIM_RE`/`_claimed_pr_numbers` names, so none of
their `recipe.json`s, fixtures, or existing tests (which call
`detector._claimed_pr_numbers(...)` directly) have to change shape.

Pure, no I/O, no seam-engine imports of its own -- same shape as
`references.py` and `milestone_claims.py`.

Task 613 (Retrya): `claimed_pr_numbers` used to be a bare
`PR_CLAIM_RE.findall`, no negation check at all. Reproduced live before
touching anything: `claimed_pr_numbers("This release does not ship #45,
deferred to next cycle.")` returned `[45]` -- a body explicitly DENYING it
ships a PR was read as claiming to ship it anyway, the exact false-
positive shape STRATEGY.md's Ogun's law exists to catch, and the same
"unnegated claim laundered past a nearby negation" bug tasks 609
(`gateway.py`), 610 (`thanks.py`), and 612 (`duplicate_markers.py`) each
already found and fixed in a different module this same shift -- found
here a fourth time, in the two modules those three sweeps never touched
(this one and `milestone_claims.py`, fixed alongside it), by reading every
`.findall`/`.search` call across `seam_engine` for one with no negation
guard at all rather than assuming the earlier three fixes covered
everything. Real blast radius: eleven recipes import this function
(`release-claims-unmerged-pr`, `merged-pr-never-released`, and nine more
`*-claims-unmerged-pr` siblings across tweet/mention/commit/issue-comment/
review-comment/milestone/readme/slack/linear surfaces) -- any of them
reading a body that explicitly denies shipping/merging/including a PR
would have surfaced a false gap off a denial, not a claim. Fixed the same
way task 612 fixed `duplicate_markers.py`: walk every candidate
(`finditer`, not `findall`) and skip any whose immediately preceding few
words carry `not`/`never`/`no` or an `n't` contraction as a whole
word/token, falling through to the next candidate rather than dropping
the whole result -- so "not merges #12 but genuinely merges #45" still
returns `[45]`, and "does not ship #45" now correctly returns `[]`.
Deliberately narrow, same residual-limit discipline `thanks.py`'s and
`duplicate_markers.py`'s own comments keep: the negation check only looks
at the words immediately in front of the claim verb, not the whole body --
a denial separated from its own claim verb by more than a few words in
front of it can still slip through.

The negation pattern itself lives in `seam_engine.negation`
(`NEGATION_PREFIX_RE`/`is_negated`), not a local `re.compile(...)` here --
`milestone_claims.py` needed the identical pattern this same task, and a
first draft of both fixes hand-retyped `duplicate_markers.py`'s own
pattern a second and third time before this module existed;
`tools/duplicate_regex_check.py` caught it live and both call sites were
moved to the one shared definition before this task shipped.
"""
from __future__ import annotations

import re

from seam_engine.negation import is_negated

# A release body "claims" a PR by naming its number this way. Anchored on
# a real verb, not a bare "#N" (that broader, unanchored shape is
# references.py's own seam, watching a different question) -- a release
# body mentioning "#N" in passing prose ("see #N for background") is not a
# shipped-it claim. Deliberately its own grammar, distinct from the
# closing-keyword grammar (fixes/closes/resolves #N) the issue-side
# recipes reuse and the "milestone #N" phrase the milestone-side recipes
# reuse -- a PR is neither an issue nor a milestone.
PR_CLAIM_RE = re.compile(r"\b(?:ships?|includes?|merges?|via)\s+#(\d+)\b", re.IGNORECASE)

# "does not " is the longest realistic negated-verb prefix mortals type
# right in front of "ships"/"includes"/"merges"/"via"; a little extra slack
# covers a comma too ("no, it doesn't ship #45") without reaching back so
# far that it starts catching a negation that belongs to an earlier,
# unrelated clause -- same reasoning as `duplicate_markers.py`'s own
# `_NEGATION_PREFIX_WINDOW`.
_NEGATION_PREFIX_WINDOW = 20


def claimed_pr_numbers(text: str) -> list[int]:
    """Every PR number `text` claims via a ships/includes/merges/via #N
    phrase, in the order they appear. A bare `#N` with no preceding claim
    verb never appears in the result at all -- see `PR_CLAIM_RE`'s own
    comment for why. A claim whose immediately preceding words negate it
    ("does not ship #45", "won't merge #12") is skipped, and the scan
    continues to the next candidate -- see this module's own docstring
    (task 613) for the live reproduction."""
    numbers = []
    for match in PR_CLAIM_RE.finditer(text):
        if is_negated(text, match.start(), _NEGATION_PREFIX_WINDOW):
            continue
        numbers.append(int(match.group(1)))
    return numbers
