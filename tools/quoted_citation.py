#!/usr/bin/env python3
"""Task 548 (widened task 561). The one-line guard six doctrine checkers
each carried a private copy of.

`no_grading_check.py`, `star_covenant_check.py`, `arcade_hero_check.py`,
`hand_lore_check.py`, `rider_check.py`, and `petition_limits_check.py`
each defined their own `_is_quoted_citation(text, match_start)` and
`_QUOTE_CHARS = set('"\\'\u201c\u2018')` -- byte-for-byte identical in every
one of the six, confirmed by direct diff before writing this, not assumed
from the AST-hash sweep alone. Task 546's own ROADMAP row had already
named all six siblings in this family one hour before task 548 shipped,
but task 548's migration only actually touched five of them --
`petition_limits_check.py` kept its local copy for 13 more tasks until
task 561 found the sixth still standing and finished the migration.

Every sibling's own docstring already narrates this as a shared "SEARCH
TECHNIQUE" borrowed from `star_covenant_check.py` (task 99) or
`no_grading_check.py` (task 105), but -- the same disease task 510 named
for `_append`, task 540 named for `_entries`, and task 546 named for
`format_violations` -- the prose called it shared for hundreds of tasks
running without one line of code ever actually being the same object.

Unlike `_is_negated_or_predictive`/`_is_negated` (genuinely NOT
byte-identical across these same five files -- each module's own
`_NEGATION_CUES` word list is deliberately tuned per file, task 467's own
documented on-purpose divergence), `_is_quoted_citation` has no per-file
variation at all: the quote-character set is the same set in every
caller, so this module takes it as a default argument, not a required
one, exactly like `scan_files.iter_public_files`'s own bare shared call.

Usage: import and call directly.
    from quoted_citation import is_quoted_citation
    if is_quoted_citation(text, match_start):
        ...
"""
from __future__ import annotations

DEFAULT_QUOTE_CHARS = set('"\'\u201c\u2018')


def is_quoted_citation(text: str, match_start: int, quote_chars=DEFAULT_QUOTE_CHARS) -> bool:
    """A phrase opening immediately on a quote mark is a cited example
    (a module's own docstring, a ROADMAP row, a test file), not a live
    violation -- the self-referential trap task 99 first hit and guarded,
    reproduced identically by every sibling that copied its shape."""
    return match_start > 0 and text[match_start - 1] in quote_chars
