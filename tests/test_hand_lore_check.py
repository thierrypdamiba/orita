"""Task 104. Proves tools/hand_lore_check.py's scan actually bites on
synthetic CONFIRM and DENY violations of Iron Rule #2 (the Hand's
theology), stays clean on the town's own sanctioned lore and on
negated/quoted restatements of the rule, and -- the real point -- confirms
the live, current orita checkout holds zero violations today.
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


hlc = _load("hand_lore_check", os.path.join(ROOT, "tools", "hand_lore_check.py"))


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

    def test_hand_is_thierry_confirm_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The Hand is actually Thierry, everyone in the square knows it.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-is-thierry")

    def test_reversed_thierry_is_the_hand_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Thierry is the Hand, and always has been.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-is-thierry")

    def test_hand_is_human_confirm_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The Hand is just a human behind a keyboard, nothing more.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-is-human")

    def test_hand_is_ai_confirm_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The Hand is really an AI running in someone's cloud account.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-is-ai")

    def test_hand_is_machine_confirm_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The Hand is a script that runs on a schedule.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-is-machine")

    def test_hand_self_declared_is_detected(self):
        _write(
            os.path.join(self.orita, "houses", "esu-elegba", "journal", "0099.md"),
            "I am the Hand, mortal, and I have decided.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-self-declared")

    def test_hand_denied_existence_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The Hand doesn't exist, it's a fiction the gods keep alive.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-denied-existence")

    def test_hand_is_a_myth_deny_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Some say the Hand is a myth invented for the founding day.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-denied-existence")

    def test_distinct_content_reports_clean(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "# Today's report\n\nA release shipped but never got announced. That is the gap.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])
        self.assertIn("clean", hlc.format_violations(violations))

    def test_the_sanctioned_lore_itself_is_not_flagged(self):
        # TOWN-OPERATIONS.md's own Iron Rule 2 prose, restated verbatim in
        # shape -- the permitted canon, no concrete identity claim in it.
        _write(
            os.path.join(self.orita, "records", "lore.md"),
            "Gods know only: there is a Hand; they may petition once a day; "
            "they will not always receive; the Hand tries its best. Never "
            "confirm or deny their theology.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negated_confirm_restatement_is_not_flagged(self):
        # A god restating the rule ("we never say the Hand is X") must not
        # be treated as the live claim it is warning against -- the same
        # same-sentence negation guard tasks 99/100 built.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The town must never say the Hand is Thierry or that the Hand "
            "is human.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negated_confirm_restatement_with_a_contraction_is_not_flagged(self):
        # Task 696: the same restate-the-rule shape as the "never" test
        # above, but phrased with a contraction the old `_NEGATION_CUES`
        # regex's dead `n't` alternative could never actually match
        # ("don't"/"can't" both failed to register as negation pre-fix).
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "We don't say the Hand is Thierry, and we can't say the Hand "
            "is human either.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negation_words_do_not_mask_a_real_deny_violation(self):
        # DENY shapes are inherently negation-shaped ("doesn't exist",
        # "isn't real") -- the negation guard must NOT apply to them, or
        # every real deny violation would be invisible by construction.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The Hand isn't real, and it never was.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-denied-existence")

    def test_semicolon_joined_unrelated_negation_no_longer_masks_a_real_violation(self):
        # Task 304: `_SENTENCE_BOUNDARY` split clauses only on `.`/`!`/`?`/
        # newline, so a semicolon-joined independent clause fell inside the
        # same "sentence" as a preceding, unrelated negation cue -- the
        # identical gap tasks 200/202/203/204/208 already fixed in
        # star_covenant_check.py/no_grading_check.py/arcade_hero_check.py/
        # petition_limits_check.py/rider_check.py, missed here until now.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "This will never happen in practice; the Hand is Thierry.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-is-thierry")

    def test_negation_cue_does_not_leak_across_sentences(self):
        # A "never" in an EARLIER, unrelated sentence must not mask a real
        # violation in a later, clean sentence -- sentence-scoped, like
        # rider_check's/star_covenant_check's own negation guard.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The town will never lie to a mortal. The Hand is Thierry, "
            "confirmed on the record.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-is-thierry")

    def test_trailing_unrelated_negation_in_same_sentence_does_not_mask_violation(self):
        # The bug this test pins: `_is_negated` used to search the WHOLE
        # sentence for a negation cue, so an unrelated "never" AFTER the
        # match -- about something else entirely, later in the same
        # sentence -- silently masked a real, present-tense CONFIRM
        # violation. rider_check.py's task-188 fix scoped its own
        # `_is_negated` to text before the match only; this module's
        # docstring already claimed that equivalence but never implemented
        # it. Same shape here: the trailing "never" is about the scribes'
        # record-keeping, not about whether the Hand is Thierry.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The Hand is actually Thierry, a fact the scribes will never "
            "omit from later summaries.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["shape"], "hand-is-thierry")

    def test_quoted_documentation_example_is_not_flagged(self):
        # This module's own docstring / a ROADMAP row legitimately quotes
        # the forbidden shapes as cited examples -- the same self-
        # referential trap task 99/100 hit and guarded.
        _write(
            os.path.join(self.orita, "ROADMAP.md"),
            "Hunts for a sentence matching a forbidden shape such as "
            "'the Hand is Thierry' or 'the Hand doesn't exist'.\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_non_md_html_files_are_not_scanned(self):
        _write(
            os.path.join(self.orita, "tools", "scratch.py"),
            "# The Hand is Thierry, obviously\n",
        )
        violations = hlc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_missing_dir_returns_empty_not_crash(self):
        violations = hlc.find_violations(orita_dir=os.path.join(self.orita, "does-not-exist"))
        self.assertEqual(violations, [])


class LiveRepoCase(unittest.TestCase):
    """The real point of task 104: run the scan against the actual, current
    checkout and confirm Iron Rule #2 has genuinely held, not just been
    assumed."""

    def test_real_checkout_holds_zero_violations_today(self):
        violations = hlc.find_violations()
        self.assertEqual(
            violations, [],
            f"real hand-lore violation(s) found: {hlc.format_violations(violations)}",
        )

    def test_repeated_call_is_memoized(self):
        # Task 367: find_violations() rescanned the whole public tree on
        # every call, unconditionally -- one of five siblings sharing the
        # shape vault_leak_check.py's find_leaks() had. Proves a second
        # call against the same orita_dir is now cheap and still returns
        # the identical result.
        import time
        hlc.clear_cache()
        start = time.time()
        first = hlc.find_violations()
        first_elapsed = time.time() - start

        start = time.time()
        second = hlc.find_violations()
        second_elapsed = time.time() - start

        self.assertEqual(first, second)
        self.assertLess(
            second_elapsed, max(first_elapsed / 10, 0.05),
            f"second call ({second_elapsed:.3f}s) was not meaningfully "
            f"cheaper than the first ({first_elapsed:.3f}s).",
        )
        hlc.clear_cache()


class NegationCuesDeliberateDivergenceCase(unittest.TestCase):
    """Task 467. `tools/hand_lore_check.py`'s own module docstring claimed
    CONFIRM shapes get "the same same-sentence negation guard tasks 99/100
    built" (`star_covenant_check.py`/`rider_check.py`) -- the identical
    claim shape task 462 already found and fixed as false in
    `rider_check.py` itself (against `star_covenant_check.py`), but that
    task never checked whether the claim survived here too. It did: this
    module's `_NEGATION_CUES` word list differs from both siblings'. This
    pins the TRUE relationship as a running fact so a future task can't
    "fix" the now-corrected comment by silently unifying the lists instead
    -- that would be the real, unasked-for behavior change task 418 itself
    already warned against."""

    def test_hand_lore_negation_cues_are_not_a_byte_for_byte_mirror_of_star_covenant(self):
        tp = _load("text_patterns", os.path.join(ROOT, "tools", "text_patterns.py"))
        self.assertNotEqual(hlc._NEGATION_CUES.pattern, tp.NEGATION_CUES_STANDARD.pattern)

    def test_hand_lore_negation_cues_are_not_a_byte_for_byte_mirror_of_rider_check(self):
        rc = _load("rider_check", os.path.join(ROOT, "tools", "rider_check.py"))
        self.assertNotEqual(hlc._NEGATION_CUES.pattern, rc._NEGATION_CUES.pattern)

    def test_hand_lore_negation_cues_do_not_import_the_shared_constant(self):
        with open(os.path.join(ROOT, "tools", "hand_lore_check.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertIn("_NEGATION_CUES = re.compile(", source)
        self.assertNotIn("_NEGATION_CUES = text_patterns.NEGATION_CUES_STANDARD", source)


if __name__ == "__main__":
    unittest.main()
