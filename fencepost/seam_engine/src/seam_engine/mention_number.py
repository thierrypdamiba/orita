"""The shared "bare `#N` mentioned in text" digit-boundary law.

`issue-closed-not-tweeted/detector.py` (task 398's own sibling, the issue
side of the "shipped work never announced" family) first wrote
`_find_announcing_tweet`: given a specific known number, does any tweet's
text name it via a bare `#N`, digit-boundary-guarded on both sides so
`#12` is never satisfied by an unrelated, longer `#123` or a shorter `#1`
immediately followed by more digits. `merged-pr-not-tweeted/detector.py`
needed the identical grammar for the PR side of the same family and
retyped both the function and its
`re.compile(r"(?<!\\d)#" + re.escape(str(number)) + r"(?!\\d)")` pattern a
second time, byte-for-byte -- each file's own comment even names the other
as the sibling that "already guards against" the identical collision
("the same short-inside-long collision release-not-tweeted's own tag
matcher (and merged-pr-not-tweeted's own numeral-form copy) already
guards against"), the exact "two independently written regexes...
drifting apart" shape `references.py`, `milestone_claims.py`,
`pr_claims.py`, `closing_keywords.py`, and `thanks.py` were each written
to close for their own family -- found here a sixth time, in a form none
of those five modules' own regression tests could see.

`tools/duplicate_regex_check.py` never caught this one: its own
`_pattern_text` only extracts a pattern from a `re.compile(<literal>)`
call whose first argument is a plain string constant, by its own
documented design ("a concatenation built at runtime... none of those are
the 'hand-typed copy of a fixed law' shape this check hunts for"). Both
copies here build their pattern by string concatenation
(`r"(?<!\\d)#" + re.escape(str(number)) + r"(?!\\d)"`) to interpolate
`number`, so the AST scan reads both `re.compile` calls as opaque and
skips them entirely -- the check's own literal-only rule is correct for
the common case (an f-string or a name is genuinely not "a fixed law
copied by hand"), but it also silently exempts the one shape where the
literal PARTS around the interpolation, and the exact interpolation idiom
itself, are what's being hand-retyped. Reproduced live: `duplicate_regex_
check.py check` reads "clean" against the pre-fix tree even with both
copies sitting byte-identical in the two files.

This module is the one real place the grammar now lives. Both detectors
import `number_mentioned` from here and call it directly from their own
existing `_find_announcing_tweet`, so neither recipe's `recipe.json`,
fixture, nor existing test (which calls `detector._find_announcing_
tweet(...)` directly) has to change shape.

Pure, no I/O, no seam-engine imports of its own -- same shape as
`references.py`, `thanks.py`, `checklist.py`.
"""
from __future__ import annotations

import re


def number_mentioned(text: str, number: int) -> bool:
    """Whether `text` names `number` via a bare `#N`, digit-boundary
    matched on both sides: `#12` is never satisfied by an unrelated,
    longer `#123`, nor by an unrelated, shorter `#1` immediately followed
    by more digits."""
    pattern = re.compile(r"(?<!\d)#" + re.escape(str(number)) + r"(?!\d)")
    return pattern.search(text) is not None
