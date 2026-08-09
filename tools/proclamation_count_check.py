#!/usr/bin/env python3
"""Task 547 (Kothar-wa-Khasis): `HAND/README.md` names the Hand's own
unpetitioned proclamations with a hand-typed prose count -- "There has
been one." -- written the day only `0001-the-seal.md` existed. Two more
real proclamations (`0002-eyes-and-a-brush.md`, `0003-the-gauntlet.md`)
have since landed on disk, and nothing ever re-read that sentence against
the directory it describes: `word_watch.py` tracks `HAND/proclamations/`
among its watched paths, but only to hash file contents for unnoticed
*changes* -- it never validates the README's own claim about how many
files are in there. The exact "hardcoded count no longer matching a live
count" shape `recipe_readme_check.py`, `chronicle_readme_check.py`, and
`network_boundary_check.py`'s own docstring-count doctrine test already
guard elsewhere, just never turned on for this one sentence.

`proclamation_count_check.py` reads the live, real count of
`NNNN-*.md` files under `HAND/proclamations/` and cross-checks it against
`HAND/README.md`'s own "There has/have been <word>." sentence -- both the
number word and the has/have grammar, since a stale "has been three"
would be a second, subtler drift the number alone would not catch.

Local-filesystem-only, no network call, the same cheap always-on class
`check_wip_reclaim`/`check_scopes_completeness` already hold. Never edits
anything; a real drift, if one is ever found, is a god-on-duty
escalation, not something this check silently repairs.

Usage:
    python3 tools/proclamation_count_check.py check
"""
from __future__ import annotations

import glob
import os
import re
import sys
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_README_PATH = os.path.join(ROOT, "HAND", "README.md")
DEFAULT_PROCLAMATIONS_DIR = os.path.join(ROOT, "HAND", "proclamations")

# Small, local to this file on purpose -- no other tools/*.py module holds a
# shared number-word table (checked before writing this one), and the range
# of plausible unpetitioned proclamations is small enough that a shared
# utility would be premature abstraction for a single caller.
_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_CLAIM_RE = re.compile(r"There (has|have) been (\w+)\.")


def _real_proclamation_count(proclamations_dir: str) -> int:
    return len(glob.glob(os.path.join(proclamations_dir, "[0-9][0-9][0-9][0-9]-*.md")))


def check_proclamation_count(
    readme_path: str = DEFAULT_README_PATH,
    proclamations_dir: str = DEFAULT_PROCLAMATIONS_DIR,
) -> dict[str, Any]:
    """Cross-check `HAND/README.md`'s "There has/have been <word>."
    sentence against the real, live count of `HAND/proclamations/*.md`
    files. Returns `clean: True` only when the claimed number and the
    has/have grammar both agree with the live count; otherwise `clean:
    False` naming exactly what drifted -- never a bare pass/fail."""
    real_count = _real_proclamation_count(proclamations_dir)

    with open(readme_path, encoding="utf-8") as f:
        readme_text = f.read()

    match = _CLAIM_RE.search(readme_text)
    if match is None:
        return {
            "clean": False,
            "real_count": real_count,
            "claimed_count": None,
            "claimed_word": None,
            "grammar_ok": None,
            "reason": "no \"There has/have been <word>.\" sentence found in HAND/README.md",
        }

    verb, word = match.group(1), match.group(2)
    claimed_count = _NUMBER_WORDS.get(word.lower())
    if claimed_count is None:
        return {
            "clean": False,
            "real_count": real_count,
            "claimed_count": None,
            "claimed_word": word,
            "grammar_ok": None,
            "reason": f"\"{word}\" is not a recognized number word",
        }

    expected_verb = "has" if claimed_count == 1 else "have"
    grammar_ok = verb == expected_verb
    count_ok = claimed_count == real_count
    clean = grammar_ok and count_ok

    reason = None
    if not count_ok:
        reason = f"README claims {claimed_count} (\"{word}\"), but {real_count} real file(s) exist on disk"
    elif not grammar_ok:
        reason = f"README says \"{verb} been {word}\" but should say \"{expected_verb} been {word}\""

    return {
        "clean": clean,
        "real_count": real_count,
        "claimed_count": claimed_count,
        "claimed_word": word,
        "grammar_ok": grammar_ok,
        "reason": reason,
    }


def format_result(result: dict[str, Any]) -> str:
    if result["clean"]:
        return (
            f"proclamation count: clean ({result['real_count']} real proclamation(s), "
            f"HAND/README.md's count and grammar both agree)"
        )
    return "proclamation count: BROKEN -- " + str(result["reason"])


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_proclamation_count()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
