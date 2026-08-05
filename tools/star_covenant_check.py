#!/usr/bin/env python3
"""Task 99. Nyx's own fourth door this window.

`TOWN-OPERATIONS.md`'s Iron Rules name the Star Covenant twice --
"**Never beg for stars**, anywhere, in any voice" (rule 4) sits in the
same numbered list as rule 1, no-cross-peek, which task 98 gave its
first running check this same window (`tools/vault_leak_check.py`).
`STRATEGY.md`'s own line is just as flat: "Never beg a star/follow (Star
Covenant)." Every hourly ritual note since the habit began has narrated
"staying silent on X" or "no begging language" by INTENT -- a god
choosing, this hour, not to write a begging sentence -- never by a
running CHECK across everything the town has already published. That is
the exact by-construction-not-by-proof gap task 96 closed for the Oracle
Desk's cadence wiring and task 98 closed for vault privacy, aimed this
time at the town's other absolute rule: two mentions in two source-of-
truth documents, and, until now, zero code that actually reads the
town's own published words back and confirms none of them ever asked for
anything.

This module does exactly that: a read-only, local-filesystem-only scan
(no network, mirrors `vault_leak_check.find_leaks`'s boundary exactly)
of every public `.md`/`.html` file in the town checkout for the actual
SHAPE of begging -- an imperative asking a reader to star, follow, like,
or subscribe -- not the bare word "star" or "follow", which the town's
own voice uses constantly and legitimately (star COUNTS, star CADENCE,
the counter that reads n-1, "nobody stars a manual", a mystery file that
tells drawer-openers what to do only AFTER they already starred for
their own reasons). A word-match check would drown in false positives on
this town's own front page; only the imperative ask is the violation.

Usage:
    python3 tools/star_covenant_check.py check
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

# Each pattern names the exact begging SHAPE it catches, not a bare
# keyword -- "star" and "follow" appear constantly in this town's own
# legitimate voice (cadence claims, the n-1 counter, epithets), so only
# an imperative ask against a reader counts as a Star-Covenant violation.
# Seven of these are the exact shapes petition_limits_check.py's own
# "(a) Star/follow ask" petition guard copied verbatim (task 418: shared
# via tools/text_patterns.py instead of retyped in either file; task 461
# found "star this/our/the repo" had silently drifted between the two
# copies -- petition_limits_check.py's noun list already included "town",
# this file's did not -- and promoted it to the shared constant too, this
# file's noun set). The rest -- aimed at public-post scanning, never
# copied into the petition guard -- stay local.
_PATTERNS = [
    ("please star", text_patterns.PLEASE_STAR),
    ("please follow", text_patterns.PLEASE_FOLLOW),
    ("star this/our/the repo", text_patterns.STAR_THIS_OUR_THE_REPO),
    ("give us/me a star", text_patterns.GIVE_US_A_STAR),
    ("drop a star", text_patterns.DROP_A_STAR),
    ("leave a star", text_patterns.LEAVE_A_STAR),
    ("smash that/the star", re.compile(r"\bsmash\s+(that|the)\s+star\b", re.IGNORECASE)),
    ("hit that/the star", re.compile(r"\bhit\s+(that|the)\s+star\b", re.IGNORECASE)),
    ("don't forget to star", re.compile(r"\bdon'?t\s+forget\s+to\s+star\b", re.IGNORECASE)),
    ("star us/it if", text_patterns.STAR_US_IF),
    ("follow us/@oritatown", re.compile(r"\bfollow\s+(us\b|@\w+)", re.IGNORECASE)),
    ("follow for more", re.compile(r"\bfollow\s+(us\s+)?for\s+more\b", re.IGNORECASE)),
    ("hit that/the follow", re.compile(r"\bhit\s+(that\s+|the\s+)?follow\b", re.IGNORECASE)),
    ("smash that/the follow", re.compile(r"\bsmash\s+(that\s+|the\s+)?follow\b", re.IGNORECASE)),
    ("like and subscribe", re.compile(r"\blike\s+and\s+subscribe\b", re.IGNORECASE)),
]


_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_TIGHT
_NEGATION_CUES = text_patterns.NEGATION_CUES_STANDARD


# Task 513: consolidated into tools/scan_files.py -- five sibling checks
# (this one, no_grading_check.py, hand_lore_check.py, arcade_hero_check.py,
# rider_check.py) each carried a byte-identical walk over
# _SKIP_DIR_NAMES/_SCAN_EXTENSIONS. `_iter_public_files` now names the
# shared function object, not a local copy; tests/test_scan_files.py
# asserts this.
_iter_public_files = scan_files.iter_public_files


def _is_negated_or_predictive(text: str, match_start: int) -> bool:
    """A bare keyword-shape match on this town's own voice drowns in false
    positives: "mortals will star the repo" (third-person prediction, not
    an ask of the reader) and 'never... "please star"' (a negated quote
    naming the exact thing the town refuses to say) both contain the
    phrase without being a violation of it. Scope the negation/prediction
    check to the CURRENT SENTENCE only (back to the nearest `.`/`!`/`?`/
    `;`/newline before the match) so an unrelated "will" three sentences
    earlier can never mask a real, present-tense imperative -- semicolon
    included alongside the original three sentence-enders because a
    semicolon joins two independent clauses exactly the way a period
    does; without it, "It will surely happen one day; please star the
    repo now." reads as ONE window-defining "sentence", so the unrelated,
    earlier "will" silently masked the real, present-tense ask that
    followed it. Reproduced live against the untouched code before this
    widening (see BUILDLOG task 200)."""
    window_start = 0
    for boundary in _SENTENCE_BOUNDARY.finditer(text, 0, match_start):
        window_start = boundary.end()
    sentence_so_far = text[window_start:match_start]
    return bool(_NEGATION_CUES.search(sentence_so_far))


# Task 548: consolidated into tools/quoted_citation.py -- five sibling
# checks (this one, no_grading_check.py, arcade_hero_check.py,
# hand_lore_check.py, rider_check.py) each carried a byte-identical
# `_is_quoted_citation`/`_QUOTE_CHARS` pair. tests/test_quoted_citation.py
# asserts every sibling's own name is that shared function, and that its
# output matches each sibling's frozen pre-refactor fixture.
_is_quoted_citation = quoted_citation.is_quoted_citation


_AUTOMATIC_CONSEQUENCE_RE = re.compile(r"(,|\s+and)\s+it\s+\w+s\b", re.IGNORECASE)


def _is_automatic_consequence(text: str, match_end: int) -> bool:
    """Task 461's own fix (widening `_PATTERNS`' "star this/our/the repo"
    noun list to include "town") turned up a real live match this guard
    exists to clear: `CHARTER.md`'s own load-bearing description of the
    Founders' Wall -- "star the town and it records your name in stone"
    (mirrored, comma-joined instead of "and"-joined, in `docs/founding.
    html`'s meta tags -- "star the town, it records your name in stone"
    -- and quoted in `ROADMAP-ARCHIVE-002-170-365.md`'s task 322).
    Grammatically identical to an imperative, but the trailing clause is
    third-person ("it records"), describing what an existing, already-
    public API does
    automatically for anyone who already starred, for their own reasons
    -- not a first/second-person appeal like "...and get updates" or
    "...and support us". Exactly the same "town's own legitimate voice"
    category this module's own docstring already names ("a mystery file
    that tells drawer-openers what to do only AFTER they already starred
    for their own reasons"), just never phrased with the word "town"
    before this fix made the phrase visible to this checker at all."""
    return bool(_AUTOMATIC_CONSEQUENCE_RE.match(text, match_end))


def _find_violations_uncached(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    """Task 99: read-only scan of every public .md/.html file in the town
    checkout for an imperative star/follow/like/subscribe ask. Returns a
    list of violation records, empty when the Star Covenant has genuinely
    held across everything the town has published. Never writes."""
    violations = []
    for path in _iter_public_files(orita_dir):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in _PATTERNS:
            for m in pattern.finditer(text):
                if (
                    _is_negated_or_predictive(text, m.start())
                    or _is_quoted_citation(text, m.start())
                    or _is_automatic_consequence(text, m.end())
                ):
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
# function.
find_violations, clear_cache = scan_files.path_memoize(_find_violations_uncached, DEFAULT_ORITA_DIR)


def format_violations(violations: list) -> str:
    return violation_format.format_violations(
        "star covenant check",
        violations,
        "pattern",
        "no begging language found in any public file",
        "Star Covenant broken",
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
