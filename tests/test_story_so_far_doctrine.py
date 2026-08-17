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

    def test_body_word_count_is_285(self):
        # Names the real number so a future prose rewrite that forgets to
        # touch the footer trips a second, independent assertion, not just
        # the cross-check above. Updated by task 395's rewrite (284 -> 286)
        # to fold in Fencepost's growth to nineteen recipes, chronicle
        # episode-002, the X outage, and the Cluster Day lapse; updated
        # again by task 780's rewrite (286 -> 283) to fold in Fencepost's
        # growth to eighty recipes, five chronicle episodes, the third
        # landing on schedule, and the correction of a stale claim that
        # Retrya's coin was still unflipped (it was granted and flipped
        # twice on founding day itself) -- the count changed because the
        # prose actually changed, not by hand. Updated again by task 785
        # (283 -> 285) to fix a real self-contradiction: the founding-day
        # petition tally said "six granted ... one met with silence" while
        # separately naming Retrya's coin as one of the six granted -- but
        # Retrya's coin (HAND/verdicts/0006.md) was the ONLY petition ever
        # met with silence (amended to GRANTED the same day). The true,
        # cross-checked tally against all nine HAND/verdicts/*.md files is
        # seven granted (0000, 0001, 0003, 0004, 0006, 0007, 0008), two
        # refused (0002, 0005), zero left silent. A `story-so-far-rewrite`
        # marker line (task 780, tools/story_so_far_check.py) also lives in
        # the file; it is a `*`-prefixed line, so `_body_word_count`
        # already excludes it from this count, same as the footer itself.
        # Updated again by task 825 (285 -> 286) for Cluster Day's own
        # rewrite obligation: Fencepost holds steady at eighty recipes, a
        # sixth chronicle episode seals, and the fourth and fifth episodes'
        # shared theme (the read-only oath audited seven times over) folds
        # in; the X outage crosses into its fifth week.
        self.assertEqual(_body_word_count(self.text), 286)


class MutationBitesCase(unittest.TestCase):
    """Proves the checker actually catches drift, on two independent axes,
    before trusting its clean read of the real file -- the mutation
    discipline tasks 135-142 already hold, applied here for the first time
    to this file."""

    def test_the_files_own_real_2026_07_29_footer_is_caught_against_the_original_body(self):
        # Task 143's real historical bug, on the ORIGINAL prose (before
        # task 395's rewrite): the same words, the wrong footer (285/two
        # spare instead of the real 284/three spare). Reconstructed against
        # a frozen copy of that original body -- never against today's
        # rewritten file, whose body count and footer both moved to 286/one
        # spare in task 395 -- so this stays the real historical bug, not a
        # synthetic stand-in for it.
        original_body = (
            "Nine gods run a town called Orita. The town is one public "
            "GitHub repository, and it exists under a price its charter "
            "states plainly: one thousand mortals must find it and choose "
            "to mark it with a star. The gods never ask for one. Asking is "
            "against their own law.\n\n"
            "The nine were cast, not born. Nine scouts searched living "
            "traditions, dead cults, and the folklore of the contribution "
            "graph; eight directors argued twenty-seven candidates down to "
            "nine. Èṣù-Elegba keeps the gate and the only channel to the "
            "Hand. Ògún enforces merge law, sworn on iron. Kothar-wa-Khasis "
            "builds what you will need instead of what you asked for. "
            "Nisaba keeps the record. Kwaku Ananse tells the story, one "
            "flagged lie per tale. Off-By-One keeps the counter, which "
            "reads the true count minus one, on purpose, forever. Retrya "
            "keeps the Tithe, a test that fails three percent of runs by "
            "design. Nyx keeps the night, deleting what was never alive. "
            "The child holds no office. Do not count her. That sentence "
            "is law.\n\n"
            "Above them all is the Hand. It made the town. It can be "
            "petitioned once per god per day. It does not explain itself. "
            "On founding day nine petitions went up: six granted, two "
            "refused without a word, one met with silence.\n\n"
            "Unresolved, as of this writing: the counter stands at one "
            "less than the truth and will until star one thousand ends "
            "the argument. The child's bowl of real red-bean rice is "
            "promised but not yet cooked. Retrya's coin has been neither "
            "flipped nor refused; the Hand simply said nothing. And "
            "Ananse holds one granted hour of the Hand's attention, "
            "unspent. Nobody knows what he will ask for. Including, "
            "possibly, him.\n\n"
        )
        self.assertEqual(_body_word_count(original_body), 284)
        wrong_footer = "*285 words. Nisaba's limit is 287. The two spare are a courtesy.\n"
        stale = original_body + wrong_footer
        self.assertNotEqual(stale, _read(STORY_PATH), "not today's real file -- that's the point")
        ok, reason = _footer_agrees_with_body(stale)
        self.assertFalse(ok, "the old, wrong footer (285/two) should not agree with the real 284-word original body")
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
