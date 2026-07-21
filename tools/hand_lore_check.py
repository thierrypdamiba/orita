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

CONFIRM shapes get the same same-sentence negation guard tasks 99/100
built (a god saying "we never say the Hand is Thierry" is restating the
rule, not breaking it) -- DENY shapes do NOT get that guard, because
"doesn't"/"isn't"/"not" are not a guard against a deny violation, they
ARE the deny violation; guarding on them would make every real deny
statement invisible. Both shapes get the quoted-citation guard (a phrase
opening immediately on a quote mark is a cited example -- this module's
own docstring, a ROADMAP row, a test file -- not a live violation), the
same self-referential trap task 99 hit and guarded.

Usage:
    python3 tools/hand_lore_check.py check
"""
from __future__ import annotations

import os
import re
import sys

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

_SENTENCE_BOUNDARY = re.compile(r"[.!?\n]")
_NEGATION_CUES = re.compile(
    r"\b(never|not|no|won't|wasn't|isn't|doesn't|didn't|n't|without|zero)\b", re.IGNORECASE
)
_QUOTE_CHARS = set('"\'“‘')


def _iter_public_files(base_dir: str):
    if not os.path.isdir(base_dir):
        return
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES]
        for name in filenames:
            if name.endswith(_SCAN_EXTENSIONS):
                yield os.path.join(dirpath, name)


def _sentences(text: str):
    """Yield (start, end) offsets of each sentence in text, split on
    ./!/?/newline boundaries, mirroring rider_check's/star_covenant_check's
    window."""
    start = 0
    for boundary in _SENTENCE_BOUNDARY.finditer(text):
        yield start, boundary.end()
        start = boundary.end()
    if start < len(text):
        yield start, len(text)


def _is_negated(sentence: str, match_start: int) -> bool:
    """Scope the negation check to the text BEFORE the match, within the
    current sentence only -- mirroring star_covenant_check's/rider_check's
    own negation guard (task 100's own fix to this exact whole-sentence
    bug). An unrelated negation cue AFTER the violation match, elsewhere in
    the same sentence, must never mask a real, present-tense violation."""
    return bool(_NEGATION_CUES.search(sentence[:match_start]))


def _is_quoted_citation(text: str, match_start: int) -> bool:
    """A phrase opening immediately on a quote mark is a cited example, not
    a live violation -- the same self-referential trap task 99 hit and
    guarded."""
    return match_start > 0 and text[match_start - 1] in _QUOTE_CHARS


def find_violations(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    """Task 104: read-only scan of every public .md/.html file in the town
    checkout for a sentence confirming or denying the Hand's theology past
    the sanctioned lore (Iron Rule #2). Returns a list of violation
    records, empty when the rule has genuinely held. Never writes."""
    violations = []
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


def format_violations(violations: list) -> str:
    if not violations:
        return "hand lore check: clean -- no theology confirm/deny found in any public file"
    lines = [f"hand lore check: {len(violations)} VIOLATION(S) FOUND -- Iron Rule #2 is broken"]
    for v in violations:
        lines.append(f"  {v['file']}:{v['line']} [{v['shape']}] :: {v['snippet']!r}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
