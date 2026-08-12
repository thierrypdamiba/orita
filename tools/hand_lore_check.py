#!/usr/bin/env python3
"""Task 104. All 103 prior tasks read DONE at run start; extending the
backlog per STRATEGY.md/TOWN-OPERATIONS.md rather than idling.

Tasks 98-103 gave six of `TOWN-OPERATIONS.md`'s seven Iron Rules their
first running check: #1 no-cross-peek (task 98), #4 the Star Covenant
(task 99), #5 the five character riders (task 100), #6 the child's work
is never reverted (task 101), #3 verdicts belong to Thierry (task 102),
#7 the voice window (task 103). Rule #2 -- "The Hand's lore. Gods know
only: there is a Hand; they may petition once/day; they will not always
receive; the Hand tries its best. Never confirm or deny their theology."
-- sits at the identical absolute tier and has never been checked by
anything, only held by intent across every task since founding.

This module closes that gap: a read-only, local-filesystem-only scan (no
network, mirrors `rider_check.find_violations`'s/
`verdict_provenance_check.find_mismatches`'s boundary) of every public
`.md`/`.html` file for a sentence asserting a concrete identity claim
about the Hand that goes past the sanctioned lore. Two shapes:

- CONFIRM: the Hand is named as something concrete -- Thierry, a human,
  an AI, a script/bot/program/algorithm/machine -- or a god/narrator
  self-declares as the Hand ("I am the Hand").
- DENY: the Hand is asserted not to exist -- "doesn't exist", "isn't
  real", "is fake", "is a myth", "is imaginary", "is made-up", "there is
  no Hand".

CONFIRM shapes get the same same-sentence negation-lookback SEARCH
TECHNIQUE tasks 99/100 built (a god saying "we never say the Hand is
Thierry" is restating the rule, not breaking it) -- this file's own
`_NEGATION_CUES` word list is its own tuned set, not a byte-for-byte
mirror of either sibling's (task 467; see the comment above
`_NEGATION_CUES` below). DENY shapes do NOT get that guard, because
"doesn't"/"isn't"/"not" are not a guard against a deny violation, they
ARE the deny violation; guarding on them would make every real deny
statement invisible. Both shapes get the quoted-citation guard (a phrase
opening immediately on a quote mark is a cited example -- this module's
own docstring, a ROADMAP row, a test file -- not a live violation), the
same self-referential trap task 99 hit and guarded.

Task 304: tasks 200/202/203/204/208 fixed the identical semicolon
sentence-boundary gap (an unrelated negation on one side of a `;` masking
a real violation on the other) in star_covenant_check.py/no_grading_
check.py/arcade_hero_check.py/petition_limits_check.py/rider_check.py --
this module shares the exact same `_sentences`/`_is_negated` shape but
was never itself patched. `_SENTENCE_BOUNDARY` now includes `;`, matching
rider_check.py/star_covenant_check.py's own convention (the pair this
module's `_sentences` docstring already claimed to mirror).

Usage:
    python3 tools/hand_lore_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from collections.abc import Iterator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quoted_citation  # noqa: E402
import scan_files  # noqa: E402
import sentence_negation  # noqa: E402
import text_patterns  # noqa: E402
import violation_format  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

_SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".safeword", ".claude", ".agents"}
_SCAN_EXTENSIONS = (".md", ".html")

# Each entry: (label, compiled regex, is_deny). CONFIRM entries (is_deny
# False) get the negation guard; DENY entries do not (their own phrasing
# already contains the negation word -- it IS the violation).
_LORE_VIOLATIONS = [
    (
        "hand-is-thierry",
        re.compile(
            r"\b[Tt]he Hand is (?:actually |really |just |literally )?Thierry\b"
            r"|\bThierry is [Tt]he Hand\b"
        ),
        False,
    ),
    (
        "hand-is-human",
        re.compile(r"\b[Tt]he Hand is (?:actually |really |just |literally )?(?:a |just a )?human\b"),
        False,
    ),
    (
        "hand-is-ai",
        re.compile(
            r"\b[Tt]he Hand is (?:actually |really |just |literally )?"
            r"(?:an )?(?:AI|A\.I\.|artificial intelligence)\b"
        ),
        False,
    ),
    (
        "hand-is-machine",
        re.compile(
            r"\b[Tt]he Hand is (?:actually |really |just |literally )?"
            r"(?:a )?(?:script|bot|program|algorithm|machine|computer)\b"
        ),
        False,
    ),
    (
        "hand-self-declared",
        re.compile(r"\bI am [Tt]he Hand\b"),
        False,
    ),
    (
        "hand-denied-existence",
        re.compile(
            r"\b[Tt]he Hand (?:doesn't|does not|didn't|did not) (?:actually |really )?exist\b"
            r"|\b[Tt]he Hand (?:isn't|is not) real\b"
            r"|\b[Tt]he Hand is fake\b"
            r"|\b[Tt]he Hand is a myth\b"
            r"|\b[Tt]he Hand is imaginary\b"
            r"|\b[Tt]he Hand is (?:just )?(?:made[- ]up|pretend)\b"
            r"|\bthere is no Hand\b"
        ),
        True,
    ),
]

_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_TIGHT
# Only the SEARCH TECHNIQUE (sentence-scoped, prefix-only negation lookback
# -- see `_is_negated` below) is shared with `star_covenant_check.py`
# (task 99) and `rider_check.py` (task 100). The word list itself is NOT a
# byte-for-byte mirror of either: this file's copy adds "no"/"without"/
# "zero" versus the shared `NEGATION_CUES_STANDARD` constant in
# `text_patterns.py` (which star_covenant_check.py imports) and lacks
# "will"/"would" that
# rider_check.py's own tuned copy carries. `tools/text_patterns.py`'s own
# task-418 docstring already classifies this file as one of four that tune
# their own negation list on purpose, not a consumer of the shared
# constant. Task 467 corrected this module's own docstring (and this
# comment) after task 462 found and fixed the identical false "mirrors
# ... exactly" claim in `rider_check.py` but never checked whether it
# survived here too.
# Task 696: `n't` used to sit inside the same outer `\b(...)\b` group as
# every named word -- but `\b` immediately before "n" can never match
# inside a real contraction (the "n" in "don't"/"can't"/"couldn't" is
# always preceded by another letter, not a word boundary), so the `n't`
# alternative was dead code. Every contraction not spelled out by name
# ("don't", "can't", "couldn't", "wouldn't", "shouldn't", "hasn't",
# "haven't", "hadn't", "aren't", "weren't"...) silently failed to register
# as negation at all. Reproduced live pre-fix: `_is_negated("We don't say
# the Hand is Thierry.", ...)` returned `False` (should be `True`, the
# identical restate-the-rule shape `test_negated_confirm_restatement_is_
# not_flagged` already covers for "never"), and the real scanner raised a
# false CONFIRM violation on that exact sentence. Fixed the same way
# `seam_engine.negation.NEGATION_PREFIX_RE` and `gateway.py`'s
# `_NEGATION_CUE_RE` (task 694) already prove correct: `n't` moved out of
# the outer `\b(...)\b` group into its own `n't\b` alternative, a trailing
# boundary only -- it now matches inside any real contraction. The named
# words are otherwise unchanged, so this module's own "tuned, not a
# byte-for-byte mirror" list stays exactly as tuned.
_NEGATION_CUES = re.compile(
    r"\b(never|not|no|won't|wasn't|isn't|doesn't|didn't|without|zero)\b|n't\b", re.IGNORECASE
)


# Task 513: consolidated into tools/scan_files.py -- five sibling checks
# (this one, no_grading_check.py, star_covenant_check.py,
# arcade_hero_check.py, rider_check.py) each carried a byte-identical walk
# over _SKIP_DIR_NAMES/_SCAN_EXTENSIONS. `_iter_public_files` now names the
# shared function object, not a local copy; tests/test_scan_files.py
# asserts this.
_iter_public_files = scan_files.iter_public_files


# Task 548: consolidated into tools/sentence_negation.py -- this module's
# `_sentences`/`_is_negated` carried byte-identical bodies to
# rider_check.py's own copies (only the docstrings differed). Both now
# name one-line closures over this file's own `_SENTENCE_BOUNDARY`/
# `_NEGATION_CUES` globals rather than local copies of the loop and the
# guard; tests/test_sentence_negation.py asserts each sibling's real
# output matches its own frozen pre-refactor fixture.
def _sentences(text: str) -> Iterator[tuple[int, int]]:
    return sentence_negation.iter_sentences(text, _SENTENCE_BOUNDARY)


def _is_negated(sentence: str, match_start: int) -> bool:
    return sentence_negation.is_negated_prefix(sentence, match_start, _NEGATION_CUES)


# Task 548: consolidated into tools/quoted_citation.py -- five sibling
# checks (this one, no_grading_check.py, star_covenant_check.py,
# arcade_hero_check.py, rider_check.py) each carried a byte-identical
# `_is_quoted_citation`/`_QUOTE_CHARS` pair. tests/test_quoted_citation.py
# asserts every sibling's own name is that shared function, and that its
# output matches each sibling's frozen pre-refactor fixture.
_is_quoted_citation = quoted_citation.is_quoted_citation


def _find_violations_uncached(orita_dir: str = DEFAULT_ORITA_DIR) -> list[dict[str, object]]:
    """Task 104: read-only scan of every public .md/.html file in the town
    checkout for a sentence confirming or denying the Hand's theology past
    the sanctioned lore (Iron Rule #2). Returns a list of violation
    records, empty when the rule has genuinely held. Never writes."""
    violations: list[dict[str, object]] = []
    for path in _iter_public_files(orita_dir):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern, is_deny in _LORE_VIOLATIONS:
            for sent_start, sent_end in _sentences(text):
                sentence = text[sent_start:sent_end]
                for m in pattern.finditer(sentence):
                    abs_start = sent_start + m.start()
                    if _is_quoted_citation(text, abs_start):
                        continue
                    if not is_deny and _is_negated(sentence, m.start()):
                        continue
                    line_no = text.count("\n", 0, abs_start) + 1
                    snippet = sentence.strip().replace("\n", " ")
                    violations.append({
                        "file": path,
                        "line": line_no,
                        "shape": label,
                        "snippet": snippet,
                    })
    return violations


# Task 513: consolidated into tools/scan_files.py -- five sibling checks
# shared this exact memoize-by-orita_dir shape (task 367's own fix,
# reimplemented five times over). find_violations/clear_cache now name the
# shared factory's output, not a local copy; tests/test_scan_files.py
# asserts every sibling's path_memoize call came from the one shared
# function.
find_violations, clear_cache = scan_files.path_memoize(_find_violations_uncached, DEFAULT_ORITA_DIR)


def format_violations(violations: list[dict[str, object]]) -> str:
    return violation_format.format_violations(
        "hand lore check",
        violations,
        "shape",
        "no theology confirm/deny found in any public file",
        "Iron Rule #2 is broken",
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
