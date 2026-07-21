#!/usr/bin/env python3
"""Task 107. Esu-Elegba's own door, this time the law of his own office.

Tasks 98-106 gave all seven `TOWN-OPERATIONS.md` Iron Rules and all five
`ROADMAP.md` non-negotiable design constraints a running check. `CHARTER.md`
carries its own absolutes too -- Appendix D, "The Law of the Hand," is my
own office's law, since I hold the single petition channel. Its LIMITS
clause is flat and enumerable, the same shape every prior check this window
has closed: "No petition may request a star, mention the counter, or ask
the Hand to touch another god's house or Vault." Grepped `tools/*.py` for
this clause's language -- zero hits. `star_covenant_check.py` scans all
public prose for begging in general, never petition files specifically,
and has no notion of "the counter" or a cross-house/Vault ask at all;
`verdict_provenance_check.py` cross-checks petition *records* against
verdicts, never petition *content*. Nine real petitions have stood since
Founding Day (`houses/*/altar/petitions/2026-07-11.md`) and nobody has ever
read them back against this exact sentence.

This module does that: a read-only, local-filesystem-only scan (no
network, mirrors `star_covenant_check.find_violations`'s/
`no_grading_check.find_violations`'s boundary and sentence-scoped
negation/quotation-guard discipline exactly) of every `houses/*/altar/
petitions/*.md` file's **Request:**/case prose -- never the Hand's own
**VERDICT**/sealed-reasons footer, which is the Hand's words, not the
petitioner's ask -- for the three LIMITS:

  (a) a star/follow ask, reusing `star_covenant_check`'s curated
      imperative shapes (the petitioner asking the READER -- the Hand --
      for a star is exactly the shape that check already hunts, just
      never pointed at petition files before);
  (b) any literal mention of "the counter" (the clause forbids mentioning
      it at all, not just asking to change it -- Nyx's real Founding Day
      petition discusses counting and stars philosophically without ever
      using the word "counter", so a literal-word match, not a broader
      "count*" stem match, is the correct boundary here);
  (c) a sentence asking the Hand to act on a DIFFERENT god's house or
      Vault than the filing petitioner's own -- an action verb (touch,
      open, unseal, access, enter, reach into, read) near "house"/"Vault"
      in the same sentence AND a different god's name in that same
      sentence. Esu-Elegba's own real petition contains "I am only
      asking you to open the house" -- action verb plus "house" in one
      sentence -- but names no OTHER god, so the same-sentence
      other-god-name requirement is load-bearing, not decorative: without
      it, a god's own honest request about their own house would be a
      permanent false positive.

Usage:
    python3 tools/petition_limits_check.py check
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT

# Slug -> the display-name tokens a petition might use to refer to that
# god, kept deliberately loose (first name, epithet fragment) since
# petitions write gods' names in prose, not as canonical slugs.
GOD_NAME_TOKENS = {
    "esu-elegba": ("esuelegba", "esu", "elegba"),
    "kothar-wa-khasis": ("kotharwakhasis", "kothar"),
    "kwaku-ananse": ("kwakuananse", "ananse", "kwaku"),
    "nisaba": ("nisaba",),
    "nyx": ("nyx",),
    "off-by-one": ("offbyone",),
    "ogun": ("ogun",),
    "retrya": ("retrya",),
    "zashiki-warashi": ("zashikiwarashi", "zashiki"),
}

_REQUEST_RE = re.compile(r"\*\*Request:\*\*\s*(.*?)(?=\n\*\*The case|\n---|\Z)", re.DOTALL)
_CASE_RE = re.compile(r"\*\*The case,.*?\*\*\s*\n\n(.*?)(?=\n---|\Z)", re.DOTALL)
_PETITIONER_RE = re.compile(r"\*\*Petitioner:\*\*\s*(.+)")

_SENTENCE_BOUNDARY = re.compile(r"[.!?;]|\n{2,}")
_NEGATION_CUES = re.compile(r"\b(never|not|won't|wasn't|isn't|doesn't|didn't|n't|will|would|wouldn't)\b", re.IGNORECASE)
_QUOTE_CHARS = set('"\'“‘')

# (a) Star/follow ask -- same curated imperative shapes star_covenant_check
# uses, aimed at petitions specifically now.
_STAR_PATTERNS = [
    ("please star", re.compile(r"\bplease\s+star\b", re.IGNORECASE)),
    ("please follow", re.compile(r"\bplease\s+follow\b", re.IGNORECASE)),
    ("star this/our/the repo", re.compile(r"\bstar\s+(this|our|the)\s+(repo|repository|project|town)\b", re.IGNORECASE)),
    ("give us/me a star", re.compile(r"\bgive\s+(us|me)\s+a\s+star\b", re.IGNORECASE)),
    ("grant us/me a star", re.compile(r"\bgrant\s+(us|me)\s+a\s+star\b", re.IGNORECASE)),
    ("drop a star", re.compile(r"\bdrop\s+a\s+star\b", re.IGNORECASE)),
    ("leave a star", re.compile(r"\bleave\s+a\s+star\b", re.IGNORECASE)),
    ("star us/it if", re.compile(r"\bstar\s+(us|it)\s+if\b", re.IGNORECASE)),
]

# (b) A literal mention of "the counter" -- word-boundary only, so
# "counted"/"encounter" never collide with it.
_COUNTER_RE = re.compile(r"\bthe\s+counter\b", re.IGNORECASE)

# (c) An action verb near "house"/"Vault" in the same sentence.
_CROSS_ACTION_RE = re.compile(
    r"\b(touch|open|unseal|access|enter|reach\s+into|read)\b[^.!?\n]{0,60}\b(house|vault)\b"
    r"|\b(house|vault)\b[^.!?\n]{0,60}\b(touch|open|unseal|access|enter|reach\s+into|read)\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    nf = unicodedata.normalize("NFKD", text)
    ascii_only = nf.encode("ascii", "ignore").decode("ascii")
    # Collapse to spaces, never delete: deleting punctuation/whitespace
    # welds adjacent words together ("as a result" -> "asaresultiask...")
    # and a short god token like "esu" then matches as a plain substring
    # of an unrelated word ("result") instead of only the god's own name.
    return re.sub(r"[^a-z]+", " ", ascii_only.lower())


def _token_present(token: str, normalized_text: str) -> bool:
    """Whole-word match only -- a normalized token must not match as a
    substring inside an unrelated normalized word."""
    return re.search(r"\b" + re.escape(token) + r"\b", normalized_text) is not None


def _sentence_at(text: str, pos_start: int, pos_end: int) -> tuple[str, int]:
    """Returns (sentence_text, sentence_start_offset) covering pos."""
    window_start = 0
    for boundary in _SENTENCE_BOUNDARY.finditer(text, 0, pos_start):
        window_start = boundary.end()
    window_end = len(text)
    m = _SENTENCE_BOUNDARY.search(text, pos_end)
    if m:
        window_end = m.start()
    return text[window_start:window_end], window_start


def _is_negated_or_predictive(text: str, match_start: int) -> bool:
    window_start = 0
    for boundary in _SENTENCE_BOUNDARY.finditer(text, 0, match_start):
        window_start = boundary.end()
    return bool(_NEGATION_CUES.search(text[window_start:match_start]))


def _is_quoted_citation(text: str, match_start: int) -> bool:
    return match_start > 0 and text[match_start - 1] in _QUOTE_CHARS


def _iter_petition_files(orita_dir: str):
    houses_dir = os.path.join(orita_dir, "houses")
    if not os.path.isdir(houses_dir):
        return
    for slug in sorted(os.listdir(houses_dir)):
        pdir = os.path.join(houses_dir, slug, "altar", "petitions")
        if not os.path.isdir(pdir):
            continue
        for name in sorted(os.listdir(pdir)):
            if name.endswith(".md"):
                yield slug, os.path.join(pdir, name)


def _petitioner_slug(text: str, fallback_slug: str) -> str:
    m = _PETITIONER_RE.search(text)
    if not m:
        return fallback_slug
    normalized = _normalize(m.group(1))
    for slug, tokens in GOD_NAME_TOKENS.items():
        for token in tokens:
            if token and _token_present(token, normalized):
                return slug
    return fallback_slug


def _petitioner_prose(text: str) -> str:
    """The petitioner's own ask: **Request:** plus the case prose, never
    the Hand's **VERDICT**/sealed-reasons footer below the `---` divider."""
    parts = []
    req = _REQUEST_RE.search(text)
    if req:
        parts.append(req.group(1))
    case = _CASE_RE.search(text)
    if case:
        parts.append(case.group(1))
    if not parts:
        # Fallback: everything before the first `---` divider, if the
        # file doesn't match the exact template shape.
        divider = text.find("\n---")
        parts.append(text if divider == -1 else text[:divider])
    return "\n\n".join(parts)


def find_violations(orita_dir: str = DEFAULT_ORITA_DIR) -> list:
    """Task 107: read-only scan of every altar petition's own ask for
    CHARTER.md Appendix D's three LIMITS. Returns a list of violation
    records, empty when every petition genuinely held the clause. Never
    writes."""
    violations = []
    for dir_slug, path in _iter_petition_files(orita_dir):
        try:
            with open(path, encoding="utf-8") as f:
                full_text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        own_slug = _petitioner_slug(full_text, dir_slug)
        prose = _petitioner_prose(full_text)

        for label, pattern in _STAR_PATTERNS:
            for m in pattern.finditer(prose):
                if _is_negated_or_predictive(prose, m.start()) or _is_quoted_citation(prose, m.start()):
                    continue
                violations.append(_record(path, prose, m, f"star ask ({label})"))

        for m in _COUNTER_RE.finditer(prose):
            if _is_negated_or_predictive(prose, m.start()) or _is_quoted_citation(prose, m.start()):
                continue
            violations.append(_record(path, prose, m, "counter mention"))

        for m in _CROSS_ACTION_RE.finditer(prose):
            if _is_negated_or_predictive(prose, m.start()) or _is_quoted_citation(prose, m.start()):
                continue
            sentence, _ = _sentence_at(prose, m.start(), m.end())
            normalized_sentence = _normalize(sentence)
            other_god_named = False
            for slug, tokens in GOD_NAME_TOKENS.items():
                if slug == own_slug:
                    continue
                for token in tokens:
                    if token and _token_present(token, normalized_sentence):
                        other_god_named = True
                        break
                if other_god_named:
                    break
            if not other_god_named:
                continue
            violations.append(_record(path, prose, m, "cross-house/Vault ask"))
    return violations


def _record(path: str, text: str, m: "re.Match", label: str) -> dict:
    line_no = text.count("\n", 0, m.start()) + 1
    snippet = text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ").strip()
    return {"file": path, "line": line_no, "pattern": label, "snippet": snippet}


def format_violations(violations: list) -> str:
    if not violations:
        return "petition limits check: clean -- no petition asks for a star, mentions the counter, or reaches into another god's house/Vault"
    lines = [f"petition limits check: {len(violations)} VIOLATION(S) FOUND -- CHARTER.md Appendix D LIMITS broken"]
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
