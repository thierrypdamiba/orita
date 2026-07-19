"""ROADMAP #143. Nisaba rereads her own arithmetic.

`docs/story-so-far.md` closes every retelling with a self-graded receipt:
"*285 words. Nisaba's limit is 287. The two spare are a courtesy to
whoever writes the next sentence.*" Nobody had ever recounted the four
paragraphs above that line against the number it claims -- the same "a
doc states a number about itself that nothing ever checked against the
live thing it describes" shape tasks 130/131/133/136/137/138/141/142 have
already closed elsewhere in the town, found this time in the one file
that is supposed to be the town's own arithmetic conscience.

The file has exactly one commit in its history (`70e2284`) and was wrong
from the start: the real body (title and footer both excluded -- the
convention the footer's own math implies, since body+title would run 288
words, over the footer's own stated 287 limit) is 284 words, not 285, and
287-284 is three spare, not two.

This module reads the doc's own body live (never a second hand-typed copy
of the prose) and its own footer claim live (a structural regex, never a
hardcoded 285/two), proves the two agree for the real, corrected file, and
proves -- via two independent mutations -- that the same checker would
have caught both the real historical bug and a synthetic one, before
trusting its clean read of today's file.
"""

from __future__ import annotations

import os
import re
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
STORY_PATH = os.path.join(REPO_ROOT, "docs", "story-so-far.md")

_META_RE = re.compile(
    r"^\*(?P<count>\d+) words\. Nisaba's limit is (?P<limit>\d+)\. "
    r"The (?P<spare_word>\w+) spare\b",
    re.MULTILINE,
)

_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _body_word_count(text: str) -> int:
    """The prose the footer's own count claims to describe: every non-empty
    line that is neither the '# ' title nor the '*...*' footer itself,
    whitespace-split. Never a second hardcoded copy of the story."""
    words: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("*"):
            continue
        words.extend(stripped.split())
    return len(words)


def _parse_footer(text: str) -> tuple[int, int, int] | None:
    """(stated_count, limit, spare_number) parsed live off the doc's own
    footer line, or None if the footer is missing or doesn't match the
    expected shape."""
    match = _META_RE.search(text)
    if match is None:
        return None
    spare_word = match.group("spare_word").lower()
    if spare_word not in _NUMBER_WORDS:
        return None
    return (
        int(match.group("count")),
        int(match.group("limit")),
        _NUMBER_WORDS[spare_word],
    )


def _footer_agrees_with_body(text: str) -> tuple[bool, str]:
    """True iff the footer's claimed count, limit-compliance, and spare
    arithmetic all match the body actually computed live from the same
    text. Returns (ok, reason) so a failing assertion names what broke."""
    parsed = _parse_footer(text)
    if parsed is None:
        return False, "footer line missing or unparseable"
    stated_count, limit, spare = parsed
    actual = _body_word_count(text)
    if stated_count != actual:
        return False, f"footer claims {stated_count} words, body actually has {actual}"
    if actual > limit:
        return False, f"body has {actual} words, over its own stated limit of {limit}"
    if spare != limit - stated_count:
        return False, f"footer says {spare} spare, but {limit}-{stated_count}={limit - stated_count}"
    return True, "ok"


class StorySoFarExistsCase(unittest.TestCase):
    def test_story_so_far_exists(self):
        self.assertTrue(os.path.isfile(STORY_PATH), "docs/story-so-far.md is missing")


class FooterArithmeticCase(unittest.TestCase):
    def setUp(self):
        self.text = _read(STORY_PATH)

    def test_footer_parses(self):
        self.assertIsNotNone(_parse_footer(self.text), "story-so-far.md's footer line didn't parse")

    def test_footer_word_count_matches_the_real_body(self):
        ok, reason = _footer_agrees_with_body(self.text)
        self.assertTrue(ok, reason)

    def test_body_word_count_is_284(self):
        # Names the real number so a future prose rewrite that forgets to
        # touch the footer trips a second, independent assertion, not just
        # the cross-check above.
        self.assertEqual(_body_word_count(self.text), 284)


class MutationBitesCase(unittest.TestCase):
    """Proves the checker actually catches drift, on two independent axes,
    before trusting its clean read of the real file -- the mutation
    discipline tasks 135-142 already hold, applied here for the first time
    to this file."""

    def test_the_files_own_real_prior_footer_is_caught_against_todays_body(self):
        # The file's actual state before this task shipped: the same prose,
        # the old (wrong) footer. This is not a synthetic mutation -- it is
        # the real historical bug, reconstructed to prove the checker would
        # have caught it.
        stale = _read(STORY_PATH).replace(
            "*284 words. Nisaba's limit is 287. The three spare",
            "*285 words. Nisaba's limit is 287. The two spare",
        )
        self.assertNotEqual(stale, _read(STORY_PATH), "mutation was a no-op -- fixture drifted")
        ok, reason = _footer_agrees_with_body(stale)
        self.assertFalse(ok, "the old, wrong footer (285/two) should not agree with the real body")
        self.assertIn("284", reason)

    def test_added_prose_without_a_footer_update_is_caught(self):
        real = _read(STORY_PATH)
        mutated = real.replace("Nine gods run a town", "Nine loud gods run a town", 1)
        self.assertNotEqual(mutated, real, "mutation was a no-op -- fixture drifted")
        ok, _reason = _footer_agrees_with_body(mutated)
        self.assertFalse(ok, "adding a word to the body without updating the footer must fail")

    def test_the_real_current_file_passes_clean(self):
        ok, reason = _footer_agrees_with_body(_read(STORY_PATH))
        self.assertTrue(ok, reason)


if __name__ == "__main__":
    unittest.main()
