#!/usr/bin/env python3
"""Task 105. Ogun's own second door this hour.

ROADMAP.md's "Non-negotiable design constraints" list five rules; tasks
23/25 (`tools/oath_badge.py`), the self-audit tally (`fencepost/seam_engine/
src/seam_engine/audit.py`), and `draftback.py`'s `FORBIDDEN_DELIVERY_ACTIONS`
already gave three of the five (read-only, false-positives-fatal,
written-back) a running check. Constraint #2 -- "No grading/competing.
Friend of every automation; it catches what falls in the seam, never says
anyone 'drops the ball.' Name and rank no one." -- never got one, and
`fencepost/CONTRIBUTING.md`'s own "No grading, ever" section says so in
plain words: "A recipe that grades gets the same rejection treatment as a
write-shaped scope, just from a human reviewer instead of `recipes.py` --
**this one, the code cannot check for you.**" `recipes.py`'s own docstring
confirms the gap by construction: `validate_recipe` checks a manifest's
DECLARED scopes, never a detector's actual headline/detail prose ("It makes
no claim about what a recipe's Python *does* beyond what its manifest
*declares*"). Same shape as tasks 98-104's Iron Rule checks, aimed at
ROADMAP.md's OTHER absolute list instead: a rule enforced only by intent
and a human reviewer's attention, never by a running check.

This module does exactly what CONTRIBUTING.md says the code can't: a
read-only, local-filesystem-only scan (mirrors
`star_covenant_check.find_violations`'s shape -- same SEARCH TECHNIQUE,
sentence-scoped negation lookback, same quoted-citation guard) of every
public `.md`/`.html` file in the town checkout, PLUS every `fencepost/RECIPES/*/
detector.py` and `recipe.json` (the actual shipped product surface a
community recipe's prose lives in, not just the town's own voice), for the
SHAPE of grading -- blaming a specific human, account, tool, or automation
by name for a gap, the same "shape not bare keyword" discipline task 99
proved necessary ("worse than"/"better than" are this town's own constant
self-critique idiom -- houses/*/journal/*.md uses "worse than" a dozen
honest times this week alone, none of them naming or ranking another
tool -- so neither verb is a pattern here; only the specific blame/grading
shapes STRATEGY.md and CONTRIBUTING.md actually name are).

Usage:
    python3 tools/no_grading_check.py check
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quoted_citation  # noqa: E402
import scan_files  # noqa: E402
import text_patterns  # noqa: E402
import violation_format  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

_SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".safeword", ".claude", ".agents"}
_SCAN_EXTENSIONS = (".md", ".html")
# The actual shipped product surface: a community recipe's headline/detail
# prose lives in its detector.py, its title/description/confidence_notes in
# recipe.json -- neither is a .md/.html file, so both need naming here on
# top of the standard walk, the same way CONTRIBUTING.md calls out recipes
# specifically as the one place "the code cannot check for you."
_RECIPE_FILENAMES = ("detector.py", "recipe.json")

# Each pattern names the exact GRADING/BLAME shape it catches, not a bare
# keyword -- "worse than"/"better than" are this town's own constant
# self-critique idiom (a dozen honest uses in houses/*/journal/*.md alone,
# comparing an approach to itself, never naming or ranking another tool),
# so neither is a pattern. Only the shapes STRATEGY.md/CONTRIBUTING.md/
# ROADMAP.md actually name as the violation are here.
_PATTERNS = [
    ("dropped the ball", re.compile(r"\bdrop(?:s|ped)?\s+the\s+ball\b", re.IGNORECASE)),
    ("fell down on the job", re.compile(r"\bfell\s+down\s+on\s+the\s+job\b", re.IGNORECASE)),
    ("pronoun's fault", re.compile(r"\b(your|their|his|her|its)\s+fault\b", re.IGNORECASE)),
    ("to blame", re.compile(r"\bto\s+blame\b", re.IGNORECASE)),
    ("blame + target", re.compile(r"\bblame\s+(him|her|them|it)\b", re.IGNORECASE)),
    ("shame on", re.compile(r"\bshame\s+on\b", re.IGNORECASE)),
    (
        "didn't do its/their/his/her job",
        re.compile(r"\bdidn'?t\s+do\s+(its|their|his|her)\s+job\b", re.IGNORECASE),
    ),
    (
        "failed to ship/post/catch/notice/update/announce",
        re.compile(r"\bfailed\s+to\s+(ship|post|catch|notice|update|announce)\b", re.IGNORECASE),
    ),
    (
        "let ... down",
        re.compile(r"\blet\s+(you|everyone|the\s+user|the\s+human)\s+down\b", re.IGNORECASE),
    ),
    (
        "point(s)/pointed the finger at",
        re.compile(r"\bpoint(?:s|ed)?\s+(?:a\s+|the\s+)?finger\s+at\b", re.IGNORECASE),
    ),
]


_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_LOOSE
# Only the SEARCH TECHNIQUE (sentence-scoped, prefix-only negation lookback
# -- see `_is_negated_or_predictive` below) is shared with
# `star_covenant_check.py`. The word list itself is NOT a byte-for-byte
# mirror of `star_covenant_check.py`'s own `_NEGATION_CUES` (imported from
# the shared `NEGATION_CUES_STANDARD` constant in `text_patterns.py`) --
# this file's copy adds "no", which the shared standard lacks.
# `tools/text_patterns.py`'s own task-418
# docstring already classifies this file as one of four that tune their
# own negation list on purpose, not a consumer of the shared constant.
# Task 467 corrected this module's own docstring (and this comment) after
# task 462 found and fixed the identical false "mirrors ... exactly"
# claim in `rider_check.py` but never checked whether it survived here too.
_NEGATION_CUES = re.compile(
    r"\b(never|not|won't|wasn't|isn't|doesn't|didn't|n't|will|would|wouldn't|no)\b",
    re.IGNORECASE,
)


def _iter_scan_files(base_dir: str):
    if not os.path.isdir(base_dir):
        return
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES]
        for name in filenames:
            if name.endswith(_SCAN_EXTENSIONS) or name in _RECIPE_FILENAMES:
                yield os.path.join(dirpath, name)


def _is_negated_or_predictive(text: str, match_start: int) -> bool:
    """Same-sentence-only guard, same spirit as
    `star_covenant_check._is_negated_or_predictive`: "it never says anyone
    dropped the ball" (the town's own canonical, negated phrasing of this
    exact rule, published three times over) must never itself count as a
    violation. Scoped to the current sentence only so an unrelated
    negation cue several sentences earlier can never mask a real, present-
    tense grading sentence -- widened past a bare `\\n` to `\\n{2,}`
    (`_SENTENCE_BOUNDARY`, above) after the first live run against the real
    checkout found a false positive: `fencepost/CONTRIBUTING.md`'s own "No
    grading, ever" section hard-wraps its prose at ~79 columns, so the
    sentence "It never names... as having\\ndropped the ball" line-wraps
    its negation cue onto the line above the match. A bare `\\n` boundary
    (star_covenant_check's original shape) would cut the window off
    between "never" and the match and miss it; only a real sentence-ender
    or a blank-line paragraph break should end the window. Task 202 added
    `;` to the boundary too, the same fix task 200 made to
    `star_covenant_check.py`: a semicolon joins two independent clauses
    exactly the way a period does, and an unrelated cue on the near side
    of one must not mask a real violation on the far side."""
    window_start = 0
    for boundary in _SENTENCE_BOUNDARY.finditer(text, 0, match_start):
        window_start = boundary.end()
    sentence_so_far = text[window_start:match_start]
    return bool(_NEGATION_CUES.search(sentence_so_far))


# Task 548: consolidated into tools/quoted_citation.py -- five sibling
# checks (this one, star_covenant_check.py, arcade_hero_check.py,
# hand_lore_check.py, rider_check.py) each carried a byte-identical
# `_is_quoted_citation`/`_QUOTE_CHARS` pair. `_is_quoted_citation` now
# names the shared function object directly (no per-file quote-char
# variation exists, so no wrapper closure is needed); tests/
# test_quoted_citation.py asserts every sibling's own name is that shared
# function, and that its output matches each sibling's frozen pre-refactor
# fixture.
_is_quoted_citation = quoted_citation.is_quoted_citation


def _find_violations_uncached(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    """Task 105: read-only scan of every public .md/.html file plus every
    RECIPES/*/detector.py and recipe.json in the town checkout for the
    grading/blame shape ROADMAP.md's constraint #2 forbids. Returns a list
    of violation records, empty when the no-grading rule has genuinely
    held across everything the town (and every merged community recipe)
    has published. Never writes."""
    violations = []
    for path in _iter_scan_files(orita_dir):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in _PATTERNS:
            for m in pattern.finditer(text):
                if _is_negated_or_predictive(text, m.start()) or _is_quoted_citation(text, m.start()):
                    continue
                line_no = text.count("\n", 0, m.start()) + 1
                snippet = text[max(0, m.start() - 20):m.end() + 20].replace("\n", " ").strip()
                violations.append({
                    "file": path,
                    "line": line_no,
                    "pattern": label,
                    "snippet": snippet,
                })
    return violations


# Task 513: consolidated into tools/scan_files.py -- five sibling checks
# shared this exact memoize-by-orita_dir shape (task 367's own fix,
# reimplemented five times over). find_violations/clear_cache now name the
# shared factory's output, not a local copy; tests/test_scan_files.py
# asserts every sibling's path_memoize call came from the one shared
# function. (This module's own `_iter_scan_files` stays a local, genuine
# one-off -- it adds a real extra condition, `_RECIPE_FILENAMES`, the other
# four siblings' walk doesn't need.)
find_violations, clear_cache = scan_files.path_memoize(_find_violations_uncached, DEFAULT_ORITA_DIR)


def format_violations(violations: list) -> str:
    return violation_format.format_violations(
        "no grading check",
        violations,
        "pattern",
        "no blame/grading language found in any public file or recipe",
        "ROADMAP.md constraint #2 broken",
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
