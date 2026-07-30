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
import text_patterns  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

_SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".safeword", ".claude", ".agents"}
_SCAN_EXTENSIONS = (".md", ".html")

# Each pattern names the exact begging SHAPE it catches, not a bare
# keyword -- "star" and "follow" appear constantly in this town's own
# legitimate voice (cadence claims, the n-1 counter, epithets), so only
# an imperative ask against a reader counts as a Star-Covenant violation.
# Six of these are the exact shapes petition_limits_check.py's own
# "(a) Star/follow ask" petition guard copied verbatim (task 418: shared
# via tools/text_patterns.py instead of retyped in either file). The
# rest -- aimed at public-post scanning, never copied into the petition
# guard -- stay local.
_PATTERNS = [
    ("please star", text_patterns.PLEASE_STAR),
    ("please follow", text_patterns.PLEASE_FOLLOW),
    ("star this/our/the repo", re.compile(r"\bstar\s+(this|our|the)\s+(repo|repository|project)\b", re.IGNORECASE)),
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
_QUOTE_CHARS = set('"\'“‘')


def _iter_public_files(base_dir: str):
    if not os.path.isdir(base_dir):
        return
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES]
        for name in filenames:
            if name.endswith(_SCAN_EXTENSIONS):
                yield os.path.join(dirpath, name)


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


def _is_quoted_citation(text: str, match_start: int) -> bool:
    """Documentation ABOUT this check (this module's own docstring,
    ROADMAP.md's task text, a test file) legitimately lists the exact
    begging phrases it hunts for as quoted examples -- e.g. `("please
    star", "give us a star", ...)`. A phrase opening immediately on a
    quote mark is a cited example, not a live ask of a reader."""
    return match_start > 0 and text[match_start - 1] in _QUOTE_CHARS


_VIOLATIONS_CACHE: dict[str, list] = {}


def clear_cache() -> None:
    """Task 367: drop every memoized `find_violations()` result -- same
    fix, same rationale as `vault_leak_check.py`'s `clear_cache()`. Only
    real callers are tests that want a forced fresh scan; production's
    one-call-per-process shape never needs this."""
    _VIOLATIONS_CACHE.clear()


def find_violations(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    """Task 367: memoized per `orita_dir` for the lifetime of the process
    -- same fix, same rationale as `vault_leak_check.py`'s `find_leaks()`.
    `ritual_check.py`'s own loader now reuses one module instance per
    check across repeated `run_ritual_check()` calls in one process (its
    own fix, same task); this memoization is what lets that reuse
    actually pay off instead of re-scanning the whole public tree on
    every call regardless of module identity."""
    key = os.path.realpath(orita_dir)
    if key not in _VIOLATIONS_CACHE:
        _VIOLATIONS_CACHE[key] = _find_violations_uncached(orita_dir)
    return list(_VIOLATIONS_CACHE[key])


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


def format_violations(violations: list) -> str:
    if not violations:
        return "star covenant check: clean -- no begging language found in any public file"
    lines = [f"star covenant check: {len(violations)} VIOLATION(S) FOUND -- Star Covenant broken"]
    for v in violations:
        lines.append(f"  {v['file']}:{v['line']} [{v['pattern']}] :: {v['snippet']!r}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
