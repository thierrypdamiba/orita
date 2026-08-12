"""Task 106. Proves tools/arcade_hero_check.py's scan actually bites on a
synthetic direct-credential-handoff sentence, stays clean on the town's own
legitimate credential vocabulary (CONNECT.md describing what Arcade itself
mints and scopes), negated/quoted restatements of the rule, and -- the real
point -- confirms the live, current orita checkout holds zero violations
today.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ahc = _load("arcade_hero_check", os.path.join(ROOT, "tools", "arcade_hero_check.py"))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _rm(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


class FixtureViolationCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_paste_your_api_key_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "onboard.md"),
            "# Quick start\n\nPaste your API key into the config file.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "paste your credential")
        formatted = ahc.format_violations(violations)
        self.assertIn("VIOLATION(S) FOUND", formatted)
        self.assertIn("constraint #4 broken", formatted)

    def test_share_your_token_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "setup.md"),
            "Just share your token with the bot and you're connected.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "share your credential")

    def test_send_us_your_password_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "If it breaks, send us your password and we'll fix it.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "send us your credential")

    def test_email_us_your_credentials_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "Email us your credentials and we'll set it up for you.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "email us your credential")

    def test_enter_your_secret_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "Enter your secret in the box below to continue.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "enter your credential")

    def test_give_us_your_api_key_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "Give us your API key and skip the OAuth screen entirely.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "give us your credential")


class CleanFixtureCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_bare_token_mention_is_not_flagged(self):
        """The town's own constant honest vocabulary -- CONNECT.md
        describes what Arcade itself mints and scopes ("Arcade mints a
        token scoped to *you*"), never asking a human to hand one over."""
        _write(
            os.path.join(self.orita, "fencepost", "CONNECT.md"),
            "Arcade mints a token scoped to you, stored under your "
            "identity, callable only through your gateway.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negated_paste_your_key_on_one_line_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "We will never ask you to paste your API key anywhere.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negated_paste_your_key_with_a_contraction_is_not_flagged(self):
        # Task 697: `_NEGATION_CUES`'s own dead `n't` alternative (the same
        # class task 696 fixed in hand_lore_check.py) meant "wouldn't" --
        # not spelled out by name in this file's tuned word list -- never
        # actually registered as negation pre-fix.
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "This project wouldn't ever paste your API key anywhere.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_quoted_citation_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            'The check hunts for phrases like "paste your API key" and flags them.\n',
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_hard_wrapped_negation_across_a_line_break_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "This project will not, under any circumstance, ask you to\n"
            "share your token with anyone -- Arcade's OAuth screen is the\n"
            "only door.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_double_newline_paragraph_break_still_ends_the_window(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "We never ask you to paste your API key, historically.\n"
            "\n"
            "Paste your API key into the box to continue.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertIn("into the box", violations[0]["snippet"])


class SemicolonJoinedRealAskCase(unittest.TestCase):
    """Task 203. arcade_hero_check.py's own docstring says it "mirrors
    `no_grading_check.find_violations`'s shape exactly -- same
    sentence-scoped negation guard" -- but it was copied before task 202
    widened that guard's `_SENTENCE_BOUNDARY` to include `;` (task 200 did
    the same for `star_covenant_check.py` first), so this copy carried the
    gap forward unfixed. A semicolon joins two independent clauses exactly
    the way a period does; an unrelated negation clause on the near side of
    a `;` must not mask a real, present-tense credential-handoff ask on the
    far side."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_semicolon_joined_unrelated_negation_no_longer_masks_a_real_ask(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "We will never ask for this without your consent; please paste "
            "your API key here to continue.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "paste your credential")
        self.assertIn("paste your API key", violations[0]["snippet"])

    def test_period_joined_mirror_of_the_same_shape_was_already_caught(self):
        """The period-joined mirror of the identical shape was already
        caught correctly before this fix -- confirming the semicolon
        variant specifically was the live gap, not the whole guard."""
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "We will never ask for this without your consent. Please paste "
            "your API key here to continue.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "paste your credential")


class LiveRepoCase(unittest.TestCase):
    def test_live_run_against_the_real_repo_is_clean(self):
        violations = ahc.find_violations(orita_dir=ROOT)
        self.assertEqual(
            violations, [],
            f"real, current checkout has {len(violations)} arcade-hero violation(s): {violations}",
        )

    def test_repeated_call_is_memoized(self):
        # Task 367: find_violations() rescanned the whole public tree on
        # every call, unconditionally -- one of five siblings sharing the
        # shape vault_leak_check.py's find_leaks() had. Proves a second
        # call against the same orita_dir is now cheap and still returns
        # the identical result.
        import time
        ahc.clear_cache()
        start = time.time()
        first = ahc.find_violations(orita_dir=ROOT)
        first_elapsed = time.time() - start

        start = time.time()
        second = ahc.find_violations(orita_dir=ROOT)
        second_elapsed = time.time() - start

        self.assertEqual(first, second)
        self.assertLess(
            second_elapsed, max(first_elapsed / 10, 0.05),
            f"second call ({second_elapsed:.3f}s) was not meaningfully "
            f"cheaper than the first ({first_elapsed:.3f}s).",
        )
        ahc.clear_cache()


class NegationCuesDeliberateDivergenceCase(unittest.TestCase):
    """Task 467. `tools/arcade_hero_check.py`'s own module/function
    docstrings claimed it "mirrors `no_grading_check.find_violations`'s
    shape exactly -- same sentence-scoped negation guard" -- the identical
    claim shape task 462 already found and fixed as false in
    `rider_check.py` (against `star_covenant_check.py`), but that task
    never checked whether the claim survived here too. It did: this
    module's `_NEGATION_CUES` word list adds "nobody"/"without" that
    `no_grading_check.py`'s own copy lacks, and lacks
    "will"/"would"/"wouldn't" that `no_grading_check.py`'s copy carries.
    This pins the TRUE relationship as a running fact so a future task
    can't "fix" the now-corrected comment by silently unifying the two
    lists instead -- that would be the real, unasked-for behavior change
    task 418 itself already warned against."""

    def test_arcade_hero_negation_cues_are_not_a_byte_for_byte_mirror(self):
        ngc = _load("no_grading_check", os.path.join(ROOT, "tools", "no_grading_check.py"))
        self.assertNotEqual(ahc._NEGATION_CUES.pattern, ngc._NEGATION_CUES.pattern)

    def test_arcade_hero_negation_cues_do_not_import_the_shared_constant(self):
        with open(os.path.join(ROOT, "tools", "arcade_hero_check.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertIn("_NEGATION_CUES = re.compile(", source)
        self.assertNotIn("_NEGATION_CUES = text_patterns.NEGATION_CUES_STANDARD", source)


if __name__ == "__main__":
    unittest.main()
