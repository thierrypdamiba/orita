#!/usr/bin/env python3
"""Task 418. `duplicate_regex_check.py`'s own campaign, one directory over.

Tasks 389, 390, 393, 394, 396, and 397 built and proved a running check for
one shape of bug: a `re.compile(...)` pattern hand-typed into a
`fencepost/RECIPES/*/detector.py` or `fencepost/seam_engine/src/seam_engine/
*.py` file, its own comment often claiming to "mirror" or "reuse" a pattern
defined elsewhere, with nothing actually importing it. `duplicate_regex_
check.py`'s own `_iter_scanned_files()` hard-codes exactly those two globs
and never once scans `tools/*.py` -- the very directory it lives in --  so
the identical bug shape survived there, undetected, the whole time. A live
`ast` sweep of `tools/*.py` (task 418's own gap-finding pass) found several
real, byte-identical duplicates with no import relationship between the
files:

  - a "split text into rough sentences" splitter, defined two different
    ways, three files each: `[.!?;]|\\n{2,}` in `arcade_hero_check.py`,
    `no_grading_check.py`, `petition_limits_check.py`; and `[.!?;\\n]` in
    `hand_lore_check.py`, `rider_check.py`, `star_covenant_check.py`;
  - one negation-cue word list, byte-identical between `petition_limits_
    check.py` and `star_covenant_check.py` (the other four files that
    also define a `_NEGATION_CUES` each tune their own word list on
    purpose and are untouched here -- unifying those would be a real
    behavior change nobody asked for, not a duplicate-text fix);
  - a bare `YYYY-MM-DD.md` filename matcher, byte-identical between
    `petition_cadence_check.py` and `report_cadence_check.py`;
  - a `**Petitioner:** <name>` line matcher, byte-identical between
    `petition_limits_check.py`'s own `_PETITIONER_RE` and `verdict_
    provenance_check.py`'s own `_ALTAR_PETITIONER_RE` (same text, two
    different local names);
  - six of `star_covenant_check.py`'s own curated star/follow-begging
    shapes, copied verbatim into `petition_limits_check.py`'s narrower
    petition-scoped guard (which says so explicitly in its own comment:
    "same curated imperative shapes star_covenant_check uses"). The
    shapes that were never copied (e.g. "smash that star", "like and
    subscribe" -- aimed at public-post scanning, not petition text) stay
    local to `star_covenant_check.py`, untouched.

This module is the fix's other half: one real definition per pattern that
actually is duplicated, here, that every one of those files now imports
instead of retyping. Nothing here changes any check's live behavior --
every constant is the exact regex text it replaces, verified byte-for-byte
against the pre-fix source before this file was written.

Usage: imported only, never run directly.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import text_patterns
"""
from __future__ import annotations

import re

# Splits free text into rough sentences for negation/quote-window scanning.
# Two genuinely different definitions survived across the six files that
# use one of these -- kept as two distinct constants, not unified, since
# unifying them would be a live behavior change no task has asked for.
SENTENCE_BOUNDARY_LOOSE = re.compile(r"[.!?;]|\n{2,}")
SENTENCE_BOUNDARY_TIGHT = re.compile(r"[.!?;\n]")

# The one negation-cue list two files happen to define byte-identically.
NEGATION_CUES_STANDARD = re.compile(
    r"\b(never|not|won't|wasn't|isn't|doesn't|didn't|n't|will|would|wouldn't)\b",
    re.IGNORECASE,
)

# A bare `YYYY-MM-DD.md` filename.
DATE_NAME_MD = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")

# `**Petitioner:** <name>` line.
PETITIONER_LINE = re.compile(r"\*\*Petitioner:\*\*\s*(.+)")

# The next top-level markdown `## ` header, used to bound a doc section
# read starting after some other header match -- byte-identical between
# `scopes_completeness_check.py`'s `_NEXT_HEADER` (task 135) and
# `recipe_readme_check.py`'s own bounded-section reader (task 426), which
# both walk a `## <name>` ... next `## ` window the same way.
NEXT_MARKDOWN_HEADER = re.compile(r"^## ", re.MULTILINE)

# The six star/follow-begging shapes petition_limits_check.py copied
# verbatim out of star_covenant_check.py's own curated list (task 99).
PLEASE_STAR = re.compile(r"\bplease\s+star\b", re.IGNORECASE)
PLEASE_FOLLOW = re.compile(r"\bplease\s+follow\b", re.IGNORECASE)
GIVE_US_A_STAR = re.compile(r"\bgive\s+(us|me)\s+a\s+star\b", re.IGNORECASE)
DROP_A_STAR = re.compile(r"\bdrop\s+a\s+star\b", re.IGNORECASE)
LEAVE_A_STAR = re.compile(r"\bleave\s+a\s+star\b", re.IGNORECASE)
STAR_US_IF = re.compile(r"\bstar\s+(us|it)\s+if\b", re.IGNORECASE)
