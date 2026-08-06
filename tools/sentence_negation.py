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

Unlike `quoted_citation.is_quoted_citation`, `iter_sentences`/
`is_negated_prefix` genuinely need a parameter per call: `_SENTENCE_
BOUNDARY` and `_NEGATION_CUES` are deliberately tuned per file (task 467's
documented on-purpose divergence). `hand_lore_check.py`/`rider_check.py`
share one narrow shape exactly: split text into sentences up front, then
check a negation cue only in the prefix of one already-cut sentence.

Task 569: this module's own docstring named a second, sibling shape at
task 548 and explicitly deferred it -- "a larger and riskier refactor than
one hour should reach for alongside this one" -- rather than leaving it
unnamed. `no_grading_check.py`/`star_covenant_check.py`/
`arcade_hero_check.py`'s own `_is_negated_or_predictive` bodies are, since
that note was written, still a fourth AST-identical instance of the exact
same control-flow (confirmed live, this task, by the same normalized-
constants AST-hash sweep): scan the FULL text backward from `match_start`
for the last sentence boundary, then search only the slice between that
boundary and `match_start` for a negation cue. A different calling shape
from `iter_sentences`/`is_negated_prefix` (one pre-cuts every sentence up
front; this one finds only the boundary immediately before one match), so
it earns its own function rather than a forced fit into the first -- but
it is one function, parameterized by `sentence_boundary`/`negation_cues`
exactly the way the first two already are, not three more independently
retyped copies. `_SENTENCE_BOUNDARY`/`_NEGATION_CUES` themselves stay
put, one set per file, genuinely tuned per file (task 467) -- only the
scan-and-slice CONTROL FLOW moves here.

Usage: import and call directly.
    from sentence_negation import (
        iter_sentences, is_negated_prefix, is_negated_or_predictive,
    )
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


def is_negated_or_predictive(text: str, match_start: int, sentence_boundary, negation_cues) -> bool:
    """Scope the negation/prediction check to the CURRENT SENTENCE only --
    the exact `window_start`/`sentence_so_far` two-liner `no_grading_
    check._is_negated_or_predictive`, `star_covenant_check._is_negated_or_
    predictive`, and `arcade_hero_check._is_negated_or_predictive` each
    carried independently, over their own (deliberately different)
    `_SENTENCE_BOUNDARY`/`_NEGATION_CUES` regex pair (task 467). Unlike
    `is_negated_prefix`, this scans the FULL `text` backward from
    `match_start` to find the nearest sentence boundary itself -- callers
    here never pre-cut sentences, so there is no already-cut `sentence` to
    slice a prefix from. An unrelated negation/prediction cue several
    sentences earlier, or anywhere after `match_start`, must never mask a
    real, present-tense violation."""
    window_start = 0
    for boundary in sentence_boundary.finditer(text, 0, match_start):
        window_start = boundary.end()
    sentence_so_far = text[window_start:match_start]
    return bool(negation_cues.search(sentence_so_far))
