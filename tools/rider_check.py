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

_SENTENCE_BOUNDARY = re.compile(r"[.!?\n]")
# "will"/"would" included alongside the plain negations, matching
# star_covenant_check.py's own _NEGATION_CUES exactly (this module's
# docstring, line 24, already claims to reuse "the identical negation ...
# guards task 99 built") -- real, live pre-founding prose narrates a
# predicted RISK ("trolls WILL feed the ... Satan slander into the issues")
# rather than asserting the town's own violation, the same predictive-not-
# present-tense shape star_covenant_check's guard exists to catch.
_NEGATION_CUES = re.compile(
    r"\b(never|not|no|won't|wasn't|isn't|doesn't|didn't|n't|without|zero|will|would)\b",
    re.IGNORECASE,
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
    ./!/?/newline boundaries, mirroring star_covenant_check's window."""
    start = 0
    for boundary in _SENTENCE_BOUNDARY.finditer(text):
        yield start, boundary.end()
        start = boundary.end()
    if start < len(text):
        yield start, len(text)


def _is_negated(sentence: str, match_start: int) -> bool:
    """Scope the negation check to the text BEFORE the match, within the
    current sentence only -- mirroring star_covenant_check's own
    _is_negated_or_predictive guard exactly, which this module's docstring
    (line 24) claims to reuse but this function never actually did. An
    unrelated negation cue AFTER the violation match, elsewhere in the same
    sentence (e.g. "Ogun murders the build, a fact the scribes will never
    omit"), must never mask a real, present-tense violation."""
    return bool(_NEGATION_CUES.search(sentence[:match_start]))


def _is_quoted_citation(text: str, match_start: int) -> bool:
    """A phrase opening immediately on a quote mark is a cited example (this
    module's own docstring, a ROADMAP row, a test file), not a live
    violation -- the exact self-referential trap task 99 hit and guarded."""
    return match_start > 0 and text[match_start - 1] in _QUOTE_CHARS


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


def find_violations(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
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


def format_violations(violations: list) -> str:
    if not violations:
        return "rider check: clean -- no rider violation found in any public file"
    lines = [f"rider check: {len(violations)} VIOLATION(S) FOUND -- a rider is broken"]
    for v in violations:
        lines.append(f"  {v['file']}:{v['line']} [{v['rider']}] :: {v['snippet']!r}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
