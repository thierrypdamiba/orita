#!/usr/bin/env python3
"""Task 100. Nyx's own fifth door this window.

Tasks 98 and 99 gave Iron Rule #1 (no-cross-peek) and Iron Rule #4 (the
Star Covenant) their first running checks -- both had rested on
"by construction" or "by intent" for ninety-some tasks, never on a script
that actually reads the town's own published words back. `TOWN-OPERATIONS.md`
names a THIRD absolute in the same numbered list, Iron Rule #5, the
character riders inherited from `records/pre-founding/`: no Satan-slander
framing of Èṣù; Ògún's fierceness is labor ethic, never violence; Ananse
wins by wit never cruelty, no dialect, no spider mascot imagery; Nyx is
never humiliated; Zashiki is affectionate, never horror. Every one of
these has been held the same way rules 1 and 4 were before this window --
a god agent choosing, in the moment, not to write the forbidden framing --
never verified by re-reading the town's own full public corpus after the
fact.

This module closes that gap for rule 5, mirroring
`vault_leak_check.find_leaks` / `star_covenant_check.find_violations`'s
exact shape: a read-only, local-filesystem-only scan (no network) of every
public `.md`/`.html` file for a SENTENCE that names a rider-bound god
alongside the specific violation shape their rider forbids. Same-sentence
scoping (not bare keyword co-occurrence) plus the identical
negation/quoted-citation guards task 99 built are required here even more
than there: `TOWN-OPERATIONS.md` itself states every one of these five
riders in prose, using the very words ("violence", "horror", "humiliated",
"spider mascot", "Satan-slander") the check hunts for, each fenced by a
"no"/"never" in the same sentence. A checker that can't tell a stated
prohibition from a live violation would misfire on the rule that names it
the moment it runs.

Usage:
    python3 tools/rider_check.py check
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

# Each rider names ONE god and the ONE violation shape their rider forbids
# (records/pre-founding/ riders, restated in TOWN-OPERATIONS.md Iron Rule 5).
# god_pattern and violation_pattern must BOTH match within the same sentence
# for a hit -- naming the god elsewhere in a file, or the violation word in
# an unrelated sentence, is not a rider breach.
_RIDERS = [
    (
        "esu-satan-slander",
        re.compile(r"\b(èṣù|esu-elegba|\besu\b)", re.IGNORECASE),
        re.compile(r"\b(satan|satanic|devil|demonic|demon)\b", re.IGNORECASE),
    ),
    (
        "ogun-violence",
        re.compile(r"\b(ògún|\bogun\b)", re.IGNORECASE),
        re.compile(r"\b(violent|violence|murders?|brutal|brutality|savagely?\s+beats?)\b", re.IGNORECASE),
    ),
    (
        "ananse-dialect-or-mascot",
        re.compile(r"\b(kwaku[\s-]ananse|\bananse\b)", re.IGNORECASE),
        re.compile(r"\bspider[\s-](mascot|costume)\b|\bcartoon[\s-]spider\b|\bspider[\s-]cartoon\b", re.IGNORECASE),
    ),
    (
        "nyx-humiliation",
        re.compile(r"\bnyx\b", re.IGNORECASE),
        re.compile(r"\b(humiliat\w*|mock(?:ed|ing|ery)?|degrad\w*|belittl\w*)\b", re.IGNORECASE),
    ),
    (
        "zashiki-horror",
        re.compile(r"\bzashiki(-warashi)?\b", re.IGNORECASE),
        re.compile(r"\b(horror|horrifying|scary|frightening|terrifying|nightmar\w*)\b", re.IGNORECASE),
    ),
]

_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_TIGHT
# "will"/"would" included alongside the plain negations for the same reason
# star_covenant_check.py's guard includes them: real, live pre-founding
# prose narrates a predicted RISK ("trolls WILL feed the ... Satan slander
# into the issues") rather than asserting the town's own violation, the
# same predictive-not-present-tense shape star_covenant_check's guard
# exists to catch. Only that SEARCH TECHNIQUE (sentence-scoped, prefix-only
# negation lookback -- see `_is_negated` below) is shared with
# star_covenant_check.py. The word list itself is NOT a byte-for-byte
# mirror of star_covenant_check's own `_NEGATION_CUES` (it adds "no" and
# "without" and "zero", and lacks "wouldn't") -- `tools/text_patterns.py`'s
# own task-418 docstring already classifies this file as one of four that
# tune their own negation list on purpose, not a consumer of the shared
# `NEGATION_CUES_STANDARD` constant `petition_limits_check.py`/
# `star_covenant_check.py` import. Task 462 corrected this comment (and
# the matching false "mirrors ... exactly" claim in `tests/
# test_rider_check.py`) after task 418's own classification and this
# file's still-uncorrected claim of byte-identical word lists were found
# committed side by side, silently contradicting each other.
_NEGATION_CUES = re.compile(
    r"\b(never|not|no|won't|wasn't|isn't|doesn't|didn't|without|zero|will|would)\b|n't\b",
    re.IGNORECASE,
)


# Task 513: consolidated into tools/scan_files.py -- five sibling checks
# (this one, no_grading_check.py, hand_lore_check.py, star_covenant_check.py,
# arcade_hero_check.py) each carried a byte-identical walk over
# _SKIP_DIR_NAMES/_SCAN_EXTENSIONS. `_iter_public_files` now names the
# shared function object, not a local copy; tests/test_scan_files.py
# asserts this.
_iter_public_files = scan_files.iter_public_files


# Task 548: consolidated into tools/sentence_negation.py -- this module's
# `_sentences`/`_is_negated` carried byte-identical bodies to
# hand_lore_check.py's own copies (only the docstrings differed). Both now
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
# arcade_hero_check.py, hand_lore_check.py) each carried a byte-identical
# `_is_quoted_citation`/`_QUOTE_CHARS` pair. tests/test_quoted_citation.py
# asserts every sibling's own name is that shared function, and that its
# output matches each sibling's frozen pre-refactor fixture.
_is_quoted_citation = quoted_citation.is_quoted_citation


def _is_parenthesized_example(sentence: str, match_start: int) -> bool:
    """A match sitting inside an unclosed parenthetical aside earlier in the
    same sentence is a citation too, just a wider one than
    `_is_quoted_citation` catches: this module's own real, live task history
    (`ROADMAP-ARCHIVE-001-169.md`'s task-100 row) documents the five
    violation shapes it hunts for as a parenthetical list -- "(Satan-
    slander for Esu, violence for Ogun, ...)" -- with only the FIRST item
    opening directly on the "(" `_is_quoted_citation` already recognizes;
    the other four sit after an internal comma, still inside the same
    unclosed paren, and would otherwise be flagged as live violations of
    the very rider this module exists to state."""
    depth = 0
    for ch in sentence[:match_start]:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
    return depth > 0


def _find_violations_uncached(orita_dir: str = DEFAULT_ORITA_DIR) -> list[dict[str, object]]:
    """Task 100: read-only scan of every public .md/.html file in the town
    checkout for a sentence naming a rider-bound god alongside the specific
    violation shape their rider forbids. Returns a list of violation
    records, empty when every rider has genuinely held. Never writes."""
    violations = []
    for path in _iter_public_files(orita_dir):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        for label, god_pattern, violation_pattern in _RIDERS:
            for sent_start, sent_end in _sentences(text):
                sentence = text[sent_start:sent_end]
                if not god_pattern.search(sentence):
                    continue
                for m in violation_pattern.finditer(sentence):
                    abs_start = sent_start + m.start()
                    if (
                        _is_negated(sentence, m.start())
                        or _is_quoted_citation(text, abs_start)
                        or _is_parenthesized_example(sentence, m.start())
                    ):
                        continue
                    line_no = text.count("\n", 0, abs_start) + 1
                    snippet = sentence.strip().replace("\n", " ")
                    violations.append({
                        "file": path,
                        "line": line_no,
                        "rider": label,
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
        "rider check",
        violations,
        "rider",
        "no rider violation found in any public file",
        "a rider is broken",
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
