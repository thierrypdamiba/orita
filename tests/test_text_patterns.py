"""Task 418. Proves `tools/text_patterns.py`'s shared constants behave
exactly like the hand-typed `re.compile(...)` copies they replaced across
nine files (`arcade_hero_check.py`, `no_grading_check.py`, `petition_
limits_check.py`, `hand_lore_check.py`, `rider_check.py`, `star_covenant_
check.py`, `petition_cadence_check.py`, `report_cadence_check.py`,
`verdict_provenance_check.py`), and -- the real regression guard -- that
none of those nine files quietly went back to defining its own local copy
instead of importing the shared one. Mirrors `fencepost/seam_engine/tests/
test_closing_keywords.py`'s own "check the source text, not object
identity" discipline: `re.compile` memoizes identical (pattern, flags)
pairs process-wide, so an `is` check on the compiled object would pass
even if a file reverted to a local re.compile call with byte-identical
text -- only a source-text check catches that.
"""
import importlib.util
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


tp = _load("text_patterns", os.path.join(ROOT, "tools", "text_patterns.py"))

# Every file task 418 moved a local re.compile(...) definition out of, and
# the exact source line it's expected to bind now instead.
CONSUMERS = {
    "arcade_hero_check.py": "_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_LOOSE",
    "no_grading_check.py": "_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_LOOSE",
    "petition_limits_check.py": "_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_LOOSE",
    "hand_lore_check.py": "_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_TIGHT",
    "rider_check.py": "_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_TIGHT",
    "star_covenant_check.py": "_SENTENCE_BOUNDARY = text_patterns.SENTENCE_BOUNDARY_TIGHT",
    "petition_cadence_check.py": "_DATE_NAME = text_patterns.DATE_NAME_MD",
    "report_cadence_check.py": "_DATE_NAME = text_patterns.DATE_NAME_MD",
    "verdict_provenance_check.py": "_ALTAR_PETITIONER_RE = text_patterns.PETITIONER_LINE",
}

# The negation-cues constant is only actually shared by these two -- the
# other four files that also define a "_NEGATION_CUES" name each tune
# their own word list on purpose (task 418's own docstring names this) and
# must NOT be expected to import the shared one.
NEGATION_CONSUMERS = {
    "petition_limits_check.py": "_NEGATION_CUES = text_patterns.NEGATION_CUES_STANDARD",
    "star_covenant_check.py": "_NEGATION_CUES = text_patterns.NEGATION_CUES_STANDARD",
}

NON_SHARED_NEGATION_FILES = (
    "arcade_hero_check.py",
    "no_grading_check.py",
    "hand_lore_check.py",
    "rider_check.py",
)

STAR_PATTERN_CONSUMERS = {
    "text_patterns.PLEASE_STAR",
    "text_patterns.PLEASE_FOLLOW",
    "text_patterns.GIVE_US_A_STAR",
    "text_patterns.DROP_A_STAR",
    "text_patterns.LEAVE_A_STAR",
    "text_patterns.STAR_US_IF",
    "text_patterns.STAR_THIS_OUR_THE_REPO",
}


def _source(relpath: str) -> str:
    with open(os.path.join(ROOT, "tools", relpath), encoding="utf-8") as f:
        return f.read()


class SentenceBoundaryCase(unittest.TestCase):
    def test_loose_splits_on_blank_line(self):
        parts = tp.SENTENCE_BOUNDARY_LOOSE.split("first\n\nsecond")
        self.assertEqual(parts, ["first", "second"])

    def test_loose_splits_on_punctuation(self):
        parts = tp.SENTENCE_BOUNDARY_LOOSE.split("first. second")
        self.assertEqual(parts, ["first", " second"])

    def test_loose_does_not_split_on_single_newline(self):
        self.assertIsNone(tp.SENTENCE_BOUNDARY_LOOSE.search("first\nsecond"))

    def test_tight_splits_on_single_newline(self):
        parts = tp.SENTENCE_BOUNDARY_TIGHT.split("first\nsecond")
        self.assertEqual(parts, ["first", "second"])

    def test_tight_splits_on_punctuation(self):
        parts = tp.SENTENCE_BOUNDARY_TIGHT.split("first. second")
        self.assertEqual(parts, ["first", " second"])

    def test_loose_and_tight_are_genuinely_different_patterns(self):
        self.assertNotEqual(tp.SENTENCE_BOUNDARY_LOOSE.pattern, tp.SENTENCE_BOUNDARY_TIGHT.pattern)


class NegationCuesCase(unittest.TestCase):
    def test_matches_never(self):
        self.assertTrue(tp.NEGATION_CUES_STANDARD.search("never do that"))

    def test_matches_wouldnt(self):
        self.assertTrue(tp.NEGATION_CUES_STANDARD.search("wouldn't ask"))

    def test_matches_a_contraction_not_spelled_out_by_name(self):
        # Task 697: the old dead `n't` alternative sat inside the same
        # outer `\b(...)\b` group as every named word, so a leading `\b`
        # right before "n" could never match inside a real contraction --
        # "can't"/"couldn't"/etc. (anything not spelled out by name, unlike
        # "wouldn't" above) silently failed to register as negation.
        self.assertTrue(tp.NEGATION_CUES_STANDARD.search("can't do that"))

    def test_no_match_on_affirmative_text(self):
        self.assertIsNone(tp.NEGATION_CUES_STANDARD.search("please star this repo"))


class DateNameMdCase(unittest.TestCase):
    def test_matches_real_date_filename(self):
        m = tp.DATE_NAME_MD.match("2026-07-30.md")
        self.assertIsNotNone(m)
        self.assertEqual(m.groups(), ("2026", "07", "30"))

    def test_rejects_non_date_filename(self):
        self.assertIsNone(tp.DATE_NAME_MD.match("README.md"))

    def test_rejects_trailing_characters(self):
        self.assertIsNone(tp.DATE_NAME_MD.match("2026-07-30.md.bak"))


class PetitionerLineCase(unittest.TestCase):
    def test_matches_petitioner_line(self):
        m = tp.PETITIONER_LINE.search("**Petitioner:** Nyx\n")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), "Nyx")

    def test_no_match_without_label(self):
        self.assertIsNone(tp.PETITIONER_LINE.search("Petitioner: Nyx"))


class StarBeggingPatternsCase(unittest.TestCase):
    def test_please_star(self):
        self.assertTrue(tp.PLEASE_STAR.search("please star the repo"))

    def test_please_follow(self):
        self.assertTrue(tp.PLEASE_FOLLOW.search("please follow us"))

    def test_give_us_a_star(self):
        self.assertTrue(tp.GIVE_US_A_STAR.search("give us a star"))

    def test_drop_a_star(self):
        self.assertTrue(tp.DROP_A_STAR.search("drop a star"))

    def test_leave_a_star(self):
        self.assertTrue(tp.LEAVE_A_STAR.search("leave a star"))

    def test_star_us_if(self):
        self.assertTrue(tp.STAR_US_IF.search("star us if you liked this"))

    def test_star_this_our_the_repo(self):
        self.assertTrue(tp.STAR_THIS_OUR_THE_REPO.search("star this repo"))

    def test_star_this_our_the_repo_matches_town(self):
        # Task 461: "town" is this project's own dominant self-referential
        # noun (CHARTER.md:93 uses it in a live sentence) -- the exact
        # noun star_covenant_check.py's pre-fix local copy of this pattern
        # never covered, unlike petition_limits_check.py's copy.
        self.assertTrue(tp.STAR_THIS_OUR_THE_REPO.search("please star the town"))

    def test_none_match_ordinary_prose(self):
        prose = "the counter reads the true count minus one"
        for pattern in (
            tp.PLEASE_STAR, tp.PLEASE_FOLLOW, tp.GIVE_US_A_STAR,
            tp.DROP_A_STAR, tp.LEAVE_A_STAR, tp.STAR_US_IF,
            tp.STAR_THIS_OUR_THE_REPO,
        ):
            self.assertIsNone(pattern.search(prose))


class BoundedSectionCase(unittest.TestCase):
    """Task 552's own `bounded_section`, exercised directly -- the shared
    function `scopes_completeness_check.py`'s `_section`, `recipe_readme_
    check.py`'s `_community_recipes_section`, and `chronicle_readme_check.py`'s
    `_episodes_section` each hand-wrote independently before this task."""

    _TARGET_HEADER = re.compile(r"^## Target\s*$", re.MULTILINE)

    def test_returns_text_between_header_and_next_header(self):
        text = "intro\n## Target\nbody line\n## Next\ntail"
        result = tp.bounded_section(text, self._TARGET_HEADER)
        self.assertEqual(result, "\nbody line\n")

    def test_returns_text_to_end_of_string_when_no_next_header(self):
        text = "## Target\nbody line one\nbody line two"
        result = tp.bounded_section(text, self._TARGET_HEADER)
        self.assertEqual(result, "\nbody line one\nbody line two")

    def test_returns_empty_string_when_header_missing(self):
        text = "## Something Else\nbody"
        result = tp.bounded_section(text, self._TARGET_HEADER)
        self.assertEqual(result, "")

    def test_default_next_header_is_next_markdown_header(self):
        text = "## Target\nbody\n## Anything\ntail"
        result = tp.bounded_section(text, self._TARGET_HEADER)
        self.assertEqual(result, "\nbody\n")

    def test_custom_next_header_overrides_the_default(self):
        # A custom, narrower next-header pattern that does NOT match "## Anything"
        text = "## Target\nbody\n## Anything\ntail"
        custom_next = re.compile(r"^## STOP\s*$", re.MULTILINE)
        result = tp.bounded_section(text, self._TARGET_HEADER, next_header=custom_next)
        self.assertEqual(result, "\nbody\n## Anything\ntail")


class ConsumerRegressionCase(unittest.TestCase):
    """The real point: every file task 418 touched still imports the
    shared constant and does NOT ALSO define its own local re.compile for
    that same pattern text (which would silently re-fork the duplicate
    this task closed, since re.compile's own memoization would make an
    identity check pass even then)."""

    def test_every_consumer_binds_the_shared_constant(self):
        for relpath, expected_line in CONSUMERS.items():
            source = _source(relpath)
            self.assertIn(
                expected_line, source,
                f"{relpath} no longer binds the shared text_patterns constant",
            )

    def test_every_consumer_imports_text_patterns(self):
        for relpath in CONSUMERS:
            source = _source(relpath)
            self.assertIn(
                "import text_patterns", source,
                f"{relpath} no longer imports tools/text_patterns.py",
            )

    def test_negation_cues_shared_only_by_the_two_real_duplicates(self):
        for relpath, expected_line in NEGATION_CONSUMERS.items():
            self.assertIn(expected_line, _source(relpath))

    def test_non_shared_negation_files_keep_their_own_tuned_list(self):
        # These four each define a genuinely different word list on
        # purpose -- they must NOT reference text_patterns.NEGATION_CUES_
        # STANDARD, since that would be a real behavior change, not a
        # duplicate-text fix.
        for relpath in NON_SHARED_NEGATION_FILES:
            source = _source(relpath)
            self.assertNotIn("text_patterns.NEGATION_CUES_STANDARD", source)
            self.assertIn("_NEGATION_CUES = re.compile(", source)

    def test_no_consumer_locally_redefines_a_pattern_it_now_imports(self):
        # Belt-and-suspenders on top of duplicate_regex_check.py's own
        # live scan: for each shared constant's literal pattern text,
        # confirm no consuming file still has its OWN `re.compile(<that
        # text>)` call sitting alongside the import (which would mean the
        # import landed but the old line was never actually deleted).
        shared_texts = [
            tp.SENTENCE_BOUNDARY_LOOSE.pattern,
            tp.SENTENCE_BOUNDARY_TIGHT.pattern,
            tp.NEGATION_CUES_STANDARD.pattern,
            tp.DATE_NAME_MD.pattern,
            tp.PETITIONER_LINE.pattern,
        ]
        for relpath in CONSUMERS:
            source = _source(relpath)
            local_literals = _local_re_compile_literals(source)
            for text in shared_texts:
                self.assertNotIn(
                    text, local_literals,
                    f"{relpath} still locally defines a pattern it should only import",
                )

    def test_star_covenant_and_petition_limits_share_seven_patterns(self):
        star_source = _source("star_covenant_check.py")
        petition_source = _source("petition_limits_check.py")
        for attr in STAR_PATTERN_CONSUMERS:
            self.assertIn(attr, star_source)
            self.assertIn(attr, petition_source)


def _local_re_compile_literals(source: str) -> set:
    """Every string literal that appears as the first argument of a local
    `re.compile(...)` call in `source`, via `ast` (mirrors `duplicate_
    regex_check.py`'s own `_local_re_compile_patterns`)."""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    found = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "compile"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "re"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            found.add(node.args[0].value)
    return found


if __name__ == "__main__":
    unittest.main()
