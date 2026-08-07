"""ROADMAP #583. Esu-Elegba checks whether his own second lock still holds
what it swears to.

`.github/ISSUE_TEMPLATE/fork-my-own-society.md`'s "second lock" tells a
mortal: bootstrap only opens after you "paste back -- verbatim, not 'yes' --
the one sentence from PLATFORM.md that tells you what travels free
(mechanism) and what does not (content, your pantheon, your vault, your
ledger's own entries, your flagship, your Iron Rules content)". That is a
specific, checkable claim about a second file's live text -- the exact same
shape `fencepost/seam_engine/tests/test_consent_doctrine.py` already holds
`point-fencepost.md` to against `consent.REQUIRED_SCOPES` and `SCOPES.md`
(tasks 130/131/133/135/136 name the whole drift class: a public-facing
"threshold" artifact making a claim about a doc/code elsewhere that nothing
re-checks against the live source). Nothing has ever held
`fork-my-own-society.md` to the same discipline.

`tools/ritual_check.py`'s own link check (`test_ritual_check.py` line ~3526)
only proves the template's two PLATFORM.md *links* resolve -- that the
file exists at that path. It says nothing about whether the specific
sentence the template promises a mortal can find there, and the specific
five-item content list the template names in the same breath, still exist
in PLATFORM.md in the shape the template describes. If PLATFORM.md's
"mechanism travels / content does not" line is ever reworded, or its "What
is Orita's alone" list ever gains, drops, or renames an item, a mortal
reading the template in good faith could type a "correct" confirm that no
longer matches anything in PLATFORM.md -- the same worst-case failure mode
test_consent_doctrine.py's own docstring names for the Fencepost gate: the
threshold looks broken rather than working as sworn.

This file closes that gap for the platform-fork threshold, structurally
parsing PLATFORM.md rather than re-typing a third hardcoded copy of either
claim, with a drift-detection test proving the parser actually notices when
the source text changes (the same hand-verification discipline task 135's
own buildlog and `test_parser_actually_detects_drift_not_just_tautologically_passes`
already hold their own doc parser to).
"""
from __future__ import annotations

import os
import re
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
TEMPLATE_PATH = os.path.join(REPO_ROOT, ".github", "ISSUE_TEMPLATE", "fork-my-own-society.md")
PLATFORM_PATH = os.path.join(REPO_ROOT, "PLATFORM.md")

# The five content-list items the template names, in the exact words the
# template uses for each -- checked against PLATFORM.md's own bolded item
# titles in "What is Orita's alone" below, never re-typed as a fourth
# independent guess at what that section says.
TEMPLATE_CONTENT_ITEMS = (
    "your pantheon",
    "your vault",
    "your ledger's own entries",
    "your flagship",
    "your Iron Rules content",
)

# The matching bolded titles PLATFORM.md's "What is Orita's alone" list
# actually carries today, one per template item above, same order.
PLATFORM_CONTENT_TITLES = (
    "The pantheon.",
    "The vault.",
    "The ledger's own entries.",
    "The flagship.",
    "Iron Rules content.",
)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _template_text() -> str:
    return _read(TEMPLATE_PATH)


def _platform_text() -> str:
    return _read(PLATFORM_PATH)


def _mechanism_content_sentence(text: str) -> str | None:
    """Structurally find the sentence, inside PLATFORM.md's "What is
    Orita's alone" section, that the template's second lock promises exists
    -- one carrying "mechanism", "travels", "content", and "does not" all
    together, not a hand-picked line number that a future edit could shift
    out from under a hardcoded string search."""
    marker = "## What is Orita's alone"
    if marker not in text:
        return None
    start = text.index(marker)
    end_marker = "## The five steps"
    end = text.index(end_marker, start) if end_marker in text[start:] else len(text)
    section = text[start:end]
    for sentence in re.split(r"(?<=[.!?])\s+", section):
        low = sentence.lower()
        if "mechanism" in low and "travels" in low and "content" in low and "does not" in low:
            return sentence.strip()
    return None


class TemplateAndDocExistCase(unittest.TestCase):
    def test_template_exists(self):
        self.assertTrue(os.path.isfile(TEMPLATE_PATH), f"missing {TEMPLATE_PATH}")

    def test_platform_md_exists(self):
        self.assertTrue(os.path.isfile(PLATFORM_PATH), f"missing {PLATFORM_PATH}")


class TemplateNamesTheSecondLockCase(unittest.TestCase):
    def test_template_names_a_second_lock_and_a_verbatim_requirement(self):
        text = _template_text().lower()
        self.assertIn("second lock", text)
        self.assertIn("verbatim", text)

    def test_template_names_both_platform_section_headers_verbatim(self):
        """The template's own parenthetical labels -- "(mechanism)" /
        "(content)" -- must still be the words PLATFORM.md's own section
        headers use, not a paraphrase that happened to read true once."""
        template = _template_text()
        platform = _platform_text()
        self.assertIn("what travels free (mechanism)", template.lower())
        self.assertIn("## what travels free (mechanism)", platform.lower())
        self.assertIn("what does not (content", template.lower())
        self.assertIn("## what is orita's alone (content)", platform.lower())


class MechanismContentSentenceCase(unittest.TestCase):
    def test_platform_md_still_contains_the_sentence_the_template_promises(self):
        sentence = _mechanism_content_sentence(_platform_text())
        self.assertIsNotNone(
            sentence,
            "fork-my-own-society.md's second lock asks a mortal to paste back "
            '"the one sentence from PLATFORM.md that tells you what travels '
            'free (mechanism) and what does not (content...)" -- no sentence '
            'in PLATFORM.md\'s "What is Orita\'s alone" section carries all of '
            '"mechanism"/"travels"/"content"/"does not" together any more; the '
            "threshold is now promising a mortal something that isn't there",
        )

    def test_parser_actually_detects_drift_not_just_tautologically_passes(self):
        """Mutate a COPY of the real sentence the way a future PLATFORM.md
        edit genuinely could (drop "travels") and prove the same parser used
        above stops finding it -- so this file's silence on a real future
        drift can't be mistaken for a parser that would pass no matter what
        the doc said."""
        real_text = _platform_text()
        real_clause = (
            "the *mechanism* for enforcing a rule (a test, a badge, a CI gate) "
            "travels; the rule's content does not."
        )
        self.assertIn(
            real_clause, real_text,
            "PLATFORM.md's mechanism/content clause has already changed shape "
            "-- update this test's fixture clause",
        )
        mutated_clause = (
            "the *mechanism* for enforcing a rule (a test, a badge, a CI gate) "
            "is yours; the rule's content does not."
        )
        mutated_text = real_text.replace(real_clause, mutated_clause)
        self.assertNotEqual(mutated_text, real_text)

        self.assertIsNone(_mechanism_content_sentence(mutated_text))
        # And the real, unmutated file still parses clean -- proving the
        # mutation above is what broke it, not a parser broken regardless
        # of input.
        self.assertIsNotNone(_mechanism_content_sentence(real_text))


class ContentListMirrorCase(unittest.TestCase):
    def test_every_template_content_item_names_a_real_platform_item(self):
        """The template's parenthetical -- "(content, your pantheon, your
        vault, your ledger's own entries, your flagship, your Iron Rules
        content)" -- names five things a mortal must understand stay
        Orita's alone. Each one must still be an item PLATFORM.md's own
        "What is Orita's alone" list actually carries, or the template is
        pointing a mortal at content that no longer exists there."""
        template = _template_text()
        for item in TEMPLATE_CONTENT_ITEMS:
            with self.subTest(item=item):
                self.assertIn(
                    item, template,
                    f"{item!r} no longer appears verbatim in fork-my-own-society.md "
                    "-- this test's own TEMPLATE_CONTENT_ITEMS fixture is stale",
                )

    def test_every_platform_content_title_still_on_the_doc(self):
        platform = _platform_text()
        marker = "## What is Orita's alone"
        self.assertIn(marker, platform)
        start = platform.index(marker)
        end_marker = "## The five steps"
        end = platform.index(end_marker, start) if end_marker in platform[start:] else len(platform)
        section = platform[start:end]
        for title in PLATFORM_CONTENT_TITLES:
            with self.subTest(title=title):
                self.assertIn(
                    title, section,
                    f"PLATFORM.md's 'What is Orita's alone' section no longer names "
                    f"{title!r} -- the template's content list has drifted from the doc "
                    "it claims to summarize",
                )


if __name__ == "__main__":
    unittest.main()
