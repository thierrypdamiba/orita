#!/usr/bin/env python3
"""Task 548 (second half). The sentence-splitter and prefix-negation guard
`hand_lore_check.py` and `rider_check.py` each defined as `_sentences` and
`_is_negated` -- byte-for-byte identical bodies in both files, confirmed
by direct diff (only the docstrings differ, and only in which sibling
they claim to mirror). The same "same code, different `_SENTENCE_BOUNDARY`/
`_NEGATION_CUES` module globals baked in by closure" shape
`quoted_citation.py` (this task's first half) and task 546's
`violation_format.py` both already closed for their own sibling families;
this is that shape's third instance, found by the same AST-hash sweep
(constants normalized before hashing) that found the first two, this time
pointed past `_is_quoted_citation` at the two functions sitting right next
to it in both files.

Unlike `quoted_citation.is_quoted_citation`, these two genuinely need a
parameter per call: `_SENTENCE_BOUNDARY` and `_NEGATION_CUES` are
deliberately tuned per file (task 467's documented on-purpose divergence,
the same reason `_is_negated_or_predictive` in `no_grading_check.py`/
`star_covenant_check.py`/`arcade_hero_check.py` was left untouched by this
task -- three-way divergent word lists AND a different calling shape,
sentence-boundary-scan-over-full-text rather than slice-a-pre-cut-
sentence, a larger and riskier refactor than one hour should reach for
alongside this one). `hand_lore_check.py`/`rider_check.py` share the
narrower shape exactly: split text into sentences up front, then check a
negation cue only in the prefix of one already-cut sentence.

Usage: import and call directly.
    from sentence_negation import iter_sentences, is_negated_prefix
"""
from __future__ import annotations


def iter_sentences(text: str, sentence_boundary):
    """Yield (start, end) offsets of each sentence in text, split on
    `sentence_boundary`'s own boundary matches -- the exact loop
    `hand_lore_check._sentences`/`rider_check._sentences` each ran
    independently over their own (deliberately different)
    `_SENTENCE_BOUNDARY` regex."""
    start = 0
    for boundary in sentence_boundary.finditer(text):
        yield start, boundary.end()
        start = boundary.end()
    if start < len(text):
        yield start, len(text)


def is_negated_prefix(sentence: str, match_start: int, negation_cues) -> bool:
    """Scope the negation check to the text BEFORE the match, within the
    current (already-cut) sentence only -- the exact one-liner
    `hand_lore_check._is_negated`/`rider_check._is_negated` each carried
    independently over their own (deliberately different)
    `_NEGATION_CUES` regex. An unrelated negation cue AFTER the match,
    elsewhere in the same sentence, must never mask a real, present-tense
    violation."""
    return bool(negation_cues.search(sentence[:match_start]))
