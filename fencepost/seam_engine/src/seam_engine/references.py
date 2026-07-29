"""The shared `#N` reference-extraction law.

`dangling-issue-reference/detector.py` (task 368) first wrote the regex that
turns GitHub's own `#N` shorthand into a same-repo issue/PR number, with a
negative lookbehind that excludes `owner/repo#N` and `repo#N` — a DIFFERENT
repo's own number space, on purpose, never a candidate here. `mention-
dangling-reference/detector.py` (task 388) needed the identical grammar for
a second data source (a mortal's X mention instead of a commit message) and
its own docstring claimed the extraction was "reused verbatim ... not a
second copy of it drifting apart" — but the code that shipped did not back
that claim up: `_REF_RE` was retyped a second time in the second file, with
no import connecting the two. Two textually-identical regexes are not one
law; they are two copies that happen to agree today and have nothing
stopping them from silently diverging the next time either recipe's
extraction grammar gets tightened (the exact "two independently written
regexes... drifting apart" failure the docstring itself named and did not
actually prevent).

This module is the one real place that grammar now lives. Both recipes'
detectors import `REF_RE`/`referenced_numbers` from here and bind them to
their own module-level `_REF_RE`/`_referenced_numbers` names (so neither
recipe's own code, its `recipe.json`, nor its existing tests — which call
`detector._referenced_numbers(...)` directly — have to change shape). A
third recipe that ever needs the same `#N` extraction (a release body, an
issue comment) reuses this module too, rather than writing a fourth copy.

Pure, no I/O, no seam-engine imports of its own — the same "small, boring,
depended-on-by-everything" shape as `ranking.py`'s two constants.
"""
from __future__ import annotations

import re

# A bare `#N`, not preceded by a word character or a slash. The negative
# lookbehind is what keeps `owner/repo#42` (a real, valid cross-repo
# reference) and `repo#42` from ever being extracted at all: the character
# immediately before their `#` is a letter, caught by `\w`, or the `/`
# itself. A bare `#42` at the very start of a message, or after whitespace
# or punctuation, still matches — there is nothing word-shaped in front of
# it to exclude.
REF_RE = re.compile(r"(?<![\w/])#(\d+)\b")


def referenced_numbers(text: str) -> list[int]:
    """Every same-repo `#N` reference in `text`, in the order they appear.
    A cross-repo `owner/repo#N` or bare `repo#N` reference never appears in
    the result at all — see `REF_RE`'s own comment for why."""
    return [int(n) for n in REF_RE.findall(text)]
