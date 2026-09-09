#!/usr/bin/env python3
"""Task 1356. Èṣù structures the fork gate's second lock the same way
The Threshold's Fencepost lock was, task 1057.

`.github/ISSUE_TEMPLATE/fork-my-own-society.md`'s own second lock asks a
would-be forker to paste back "the one sentence from PLATFORM.md that
tells you what travels free (mechanism) and what does not (content, your
pantheon, your vault, your ledger's own entries, your flagship, your Iron
Rules content)" -- a hand-typed enumeration of PLATFORM.md's "What is
Orita's alone (content)" section, five items, copied out by whichever
task wrote the template and never compared against the source again
since. Task 1057's `consent_template_scope_check.py` closed this exact
construction-only-assertion shape for Fencepost's own consent gate (the
scope-confirm table against `consent.py`'s `REQUIRED_SCOPES`); the
platform-level fork gate -- the same "public issue + a second lock a
human types back verbatim" shape, one level up, guarding a fork's own
first read of PLATFORM.md's promise rather than a human's inbox -- held
to no running check at all. A future edit to PLATFORM.md's content list
(add, remove, or rename an item) could drift silently away from what the
template promises a forker they are confirming, and nothing would catch
it until a forker's own honest confirm was refused for a list they were
never shown correctly.

Parses PLATFORM.md's own "## What is Orita's alone" section for its
numbered, bold-led items (never re-typed by hand here) and the template's
own parenthetical enumeration, normalizes both ("The pantheon." / "your
pantheon" -> "pantheon") and diffs them structurally. Also confirms both
section headers the template names by prefix ("What travels free", "What
is Orita's alone") still exist in PLATFORM.md, so a renamed header is
caught too, not just a reworded list.

Read-only, local-filesystem-only, no network call of its own -- same
boundary consent_template_scope_check.py and every sibling
tools/*_check.py module already holds.

Usage:
    python3 tools/fork_gate_check.py check [<platform_path>] [<template_path>]
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_PLATFORM_PATH = os.path.join(ROOT, "PLATFORM.md")
DEFAULT_TEMPLATE_PATH = os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "fork-my-own-society.md")

MECHANISM_HEADER_PREFIX = "What travels free"
CONTENT_HEADER_PREFIX = "What is Orita's alone"

# Everything from "## What is Orita's alone..." up to (but not including)
# the next "## " header or end of file.
_CONTENT_SECTION_RE = re.compile(
    r"^##\s+" + re.escape(CONTENT_HEADER_PREFIX) + r".*?\n(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)

# One numbered, bold-led list item: "1. **The pantheon.** ...rest of line".
_NUMBERED_BOLD_ITEM_RE = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*", re.MULTILINE)

# The template's own parenthetical enumeration: "...does not (content,
# your pantheon, your vault, ...):" -- everything between "(content," and
# the matching ")".
_TEMPLATE_CONTENT_LIST_RE = re.compile(r"\(content,\s*(.+?)\)", re.DOTALL)

_TRAILING_PUNCT_RE = re.compile(r"[.\s]+\Z")
_LEADING_ARTICLE_RE = re.compile(r"^(the|your)\s+", re.IGNORECASE)


def normalize_item(label: str) -> str:
    """'The pantheon.' -> 'pantheon', 'your Iron Rules content' ->
    'iron rules content' -- structural, so neither side's exact phrasing
    ("The X." vs "your X") ever has to be hand-matched to the other."""
    stripped = _TRAILING_PUNCT_RE.sub("", label.strip())
    stripped = _LEADING_ARTICLE_RE.sub("", stripped)
    return stripped.strip().lower()


def parse_platform_content_items(text: str) -> list[str]:
    """Every numbered, bold-led item under PLATFORM.md's own "What is
    Orita's alone" section, in file order, normalized."""
    match = _CONTENT_SECTION_RE.search(text)
    if not match:
        return []
    section = match.group(1)
    return [normalize_item(label) for label in _NUMBERED_BOLD_ITEM_RE.findall(section)]


def parse_template_content_items(text: str) -> list[str]:
    """The fork template's own hand-typed enumeration, split on top-level
    commas, normalized the same way."""
    match = _TEMPLATE_CONTENT_LIST_RE.search(text)
    if not match:
        return []
    raw = match.group(1)
    return [normalize_item(part) for part in raw.split(",") if part.strip()]


def find_drift(platform_items: list[str], template_items: list[str]) -> list[str]:
    """Every problem class named plainly, never a bare boolean:
    - an item PLATFORM.md names that the template's enumeration omits;
    - an item the template names that PLATFORM.md's section does not;
    - the same item duplicated on either side.
    """
    problems: list[str] = []
    platform_set = set(platform_items)
    template_set = set(template_items)

    if len(platform_items) != len(platform_set):
        dupes = sorted({x for x in platform_items if platform_items.count(x) > 1})
        problems.append(f"PLATFORM.md's own content section repeats item(s): {dupes}")
    if len(template_items) != len(template_set):
        dupes = sorted({x for x in template_items if template_items.count(x) > 1})
        problems.append(f"the fork template's enumeration repeats item(s): {dupes}")

    missing_from_template = sorted(platform_set - template_set)
    if missing_from_template:
        problems.append(
            "PLATFORM.md names content item(s) the fork template's enumeration "
            f"omits: {missing_from_template}"
        )
    extra_in_template = sorted(template_set - platform_set)
    if extra_in_template:
        problems.append(
            "the fork template's enumeration names item(s) PLATFORM.md's content "
            f"section does not: {extra_in_template}"
        )
    return problems


def check(
    platform_path: str = DEFAULT_PLATFORM_PATH,
    template_path: str = DEFAULT_TEMPLATE_PATH,
) -> tuple[bool, str]:
    if not os.path.exists(platform_path):
        return False, f"platform doc not found: {platform_path}"
    if not os.path.exists(template_path):
        return False, f"template not found: {template_path}"
    with open(platform_path, encoding="utf-8") as f:
        platform_text = f.read()
    with open(template_path, encoding="utf-8") as f:
        template_text = f.read()

    problems: list[str] = []
    if MECHANISM_HEADER_PREFIX not in platform_text:
        problems.append(
            f"the template names a {MECHANISM_HEADER_PREFIX!r} section, but "
            "PLATFORM.md carries no such header"
        )
    if CONTENT_HEADER_PREFIX not in platform_text:
        problems.append(
            f"the template names a {CONTENT_HEADER_PREFIX!r} section, but "
            "PLATFORM.md carries no such header"
        )

    platform_items = parse_platform_content_items(platform_text)
    template_items = parse_template_content_items(template_text)
    if not platform_items:
        problems.append(
            f"no numbered content items parsed out of PLATFORM.md's {CONTENT_HEADER_PREFIX!r} section"
        )
    if not template_items:
        problems.append(f"no parenthetical content enumeration parsed out of {template_path}")

    if platform_items and template_items:
        problems.extend(find_drift(platform_items, template_items))

    if problems:
        return False, "drift found:\n  - " + "\n  - ".join(problems)
    return True, (
        f"clean ({len(platform_items)} content item(s) in PLATFORM.md, byte-identical "
        f"to {os.path.basename(template_path)}'s own enumeration, no drift)"
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] != "check":
        print("usage: python3 tools/fork_gate_check.py check [<platform_path>] [<template_path>]")
        return 2
    platform_path = argv[1] if len(argv) > 1 else DEFAULT_PLATFORM_PATH
    template_path = argv[2] if len(argv) > 2 else DEFAULT_TEMPLATE_PATH
    ok, msg = check(platform_path, template_path)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
