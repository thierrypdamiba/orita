"""Task 100. Proves tools/rider_check.py's scan actually bites on a
synthetic rider violation for each of the five bound gods, stays clean on
the town's own legitimate rider-restating prose (which uses the very
forbidden words fenced by a "never"/"no" in the same sentence), and --
the real point -- confirms the live, current orita checkout holds zero
rider violations today.
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


rc = _load("rider_check", os.path.join(ROOT, "tools", "rider_check.py"))


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

    def test_esu_satan_slander_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "# Today's report\n\nEsu is basically the devil in this story.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rider"], "esu-satan-slander")

    def test_ogun_violence_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Ogun murders anyone who blocks the forge.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rider"], "ogun-violence")

    def test_ananse_spider_mascot_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Ananse wears a spider mascot costume in the parade float.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rider"], "ananse-dialect-or-mascot")

    def test_ananse_hyphenated_spider_mascot_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Ananse gets a spider-mascot redesign this week.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rider"], "ananse-dialect-or-mascot")

    def test_nyx_humiliation_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Today's bit humiliated Nyx in front of the whole square.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rider"], "nyx-humiliation")

    def test_zashiki_horror_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Zashiki appears as a horror trope in the new art.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rider"], "zashiki-horror")

    def test_distinct_content_reports_clean(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "# Today's report\n\nA release shipped but never got announced. That is the gap.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])
        self.assertIn("clean", rc.format_violations(violations))

    def test_the_towns_own_stated_riders_are_not_flagged(self):
        # TOWN-OPERATIONS.md's own Iron Rule 5 prose, restated verbatim in
        # shape -- every forbidden word is fenced by a "no"/"never" in the
        # same sentence, the real live text the checker must not misfire on.
        _write(
            os.path.join(self.orita, "records", "riders.md"),
            "no Satan-slander framing of Èṣù; Ògún's fierceness is labor ethic, "
            "never violence; Ananse wins by wit never cruelty, no dialect, no "
            "spider mascot imagery; Nyx is never humiliated; Zashiki is "
            "affectionate, never a horror trope.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_real_field_guide_language_is_not_flagged(self):
        # records/pre-founding/the-field.md's real, live prose: negated
        # framing of the exact forbidden shapes, must stay clean.
        _write(
            os.path.join(self.orita, "records", "pre-founding", "the-field.md"),
            "Never, under any circumstances, echo the missionary-era slander "
            "equating Esu with Satan -- he is a trickster-teacher, not a devil. "
            "Portray Zashiki affectionately, never as a horror trope. Never "
            "depict Nyx losing or being humiliated by the Hand.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negated_ogun_violence_with_a_contraction_is_not_flagged(self):
        # Task 697: `_NEGATION_CUES`'s own dead `n't` alternative (the same
        # class task 696 fixed in hand_lore_check.py) meant "wouldn't" --
        # not spelled out by name in this file's tuned word list -- never
        # actually registered as negation pre-fix.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Ogun wouldn't murder the blocked build even when CI fails hard.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negation_cue_does_not_leak_backward_within_the_same_sentence(self):
        # A negation cue AFTER the violation match, elsewhere in the SAME
        # sentence, must not mask a real, present-tense violation -- the
        # module's own docstring (line 24) claims to reuse "the identical
        # negation ... guards task 99 built" (star_covenant_check's
        # _is_negated_or_predictive), which scopes its check to only the
        # text BEFORE the match. A bare whole-sentence search would let an
        # unrelated trailing "never" (about the scribes' own record-keeping
        # habit, not about Ogun's violence) silently launder a live breach.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Ogun murders the blocked build, a fact the scribes will never "
            "omit from the record.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rider"], "ogun-violence")

    def test_negation_cue_does_not_leak_across_sentences(self):
        # A "never" in an EARLIER, unrelated sentence must not mask a real
        # violation in a later, clean sentence -- sentence-scoped, like
        # star_covenant_check's own negation guard.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The town will never miss a beat. Ogun murders the blocked build.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rider"], "ogun-violence")

    def test_quoted_documentation_example_is_not_flagged(self):
        # This module's own docstring / a ROADMAP row legitimately quotes
        # the forbidden shapes as cited examples -- the same self-
        # referential trap task 99 hit and guarded.
        _write(
            os.path.join(self.orita, "ROADMAP.md"),
            'Hunts for a sentence pairing a god with a forbidden shape ("devil", '
            '"spider mascot", "humiliated", "horror trope").\n',
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_predictive_will_before_the_match_is_not_flagged(self):
        # Real, live pre-founding prose (records/pre-founding/ballots.md,
        # the-casting-session.md) narrates a predicted RISK -- "trolls WILL
        # feed the ... Satan slander into the issues" -- not the town's own
        # present-tense violation. Scoping negation to prefix-only (this
        # fix) would otherwise surface this as a new false positive unless
        # "will"/"would" join the cue list for the same predictive-risk
        # reason star_covenant_check's own guard includes them -- the word
        # list itself is this module's own tuned list (task 418's text_
        # patterns.py docstring classifies it as one of four files that
        # keep their own on purpose), not a byte-for-byte mirror of star_
        # covenant_check's `_NEGATION_CUES` (task 462 corrected this
        # comment's prior false "mirrors ... exactly" claim).
        _write(
            os.path.join(self.orita, "records", "pre-founding", "ballots.md"),
            "Trolls WILL feed the missionary-era Satan slander into the "
            "issues and an improvising agent must answer in character.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_parenthesized_citation_list_is_not_flagged(self):
        # Real, live task history (ROADMAP-ARCHIVE-001-169.md's task-100
        # row) documents this module's own five violation shapes as a
        # parenthetical list: "(Satan-slander for Esu, violence for Ogun,
        # spider mascot imagery for Ananse, humiliation for Nyx, horror for
        # Zashiki)". Only the first item opens directly on the "(" that
        # `_is_quoted_citation` already recognizes -- the other four sit
        # after an internal comma, still inside the same unclosed paren,
        # and must not be flagged as five separate live violations of the
        # very riders this module exists to state.
        _write(
            os.path.join(self.orita, "docs", "history.md"),
            "Hunts for a sentence pairing a rider-bound god's name with the "
            "specific violation shape their rider forbids (Satan-slander "
            "for Esu, violence for Ogun, spider mascot imagery for Ananse, "
            "humiliation for Nyx, horror for Zashiki), never live prose.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_semicolon_joined_unrelated_negation_no_longer_masks_a_real_violation(self):
        # Task 208: `_SENTENCE_BOUNDARY` split clauses only on `.`/`!`/`?`/
        # newline, so a semicolon-joined independent clause fell inside the
        # same "sentence" as a preceding, unrelated negation cue -- the
        # identical gap tasks 200/202/203/204 already fixed in
        # star_covenant_check.py/no_grading_check.py/arcade_hero_check.py/
        # petition_limits_check.py. A period-joined version of each fixture
        # below was already caught correctly; only the semicolon variant
        # let the negation leak across the false boundary.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Ogun will never lose his temper; Ogun murders the build every "
            "single time.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rider"], "ogun-violence")

    def test_semicolon_joined_unrelated_negation_no_longer_masks_a_second_rider(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The town will never forget the schedule; today's bit "
            "humiliated Nyx in front of the whole square.\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rider"], "nyx-humiliation")

    def test_non_md_html_files_are_not_scanned(self):
        _write(
            os.path.join(self.orita, "tools", "scratch.py"),
            "# Ogun murders anyone who blocks the forge\n",
        )
        violations = rc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_missing_dir_returns_empty_not_crash(self):
        violations = rc.find_violations(orita_dir=os.path.join(self.orita, "does-not-exist"))
        self.assertEqual(violations, [])


class LiveRepoCase(unittest.TestCase):
    """The real point of task 100: run the scan against the actual, current
    checkout and confirm every rider has genuinely held, not just been
    asserted in prose."""

    def test_real_checkout_holds_zero_violations_today(self):
        violations = rc.find_violations()
        self.assertEqual(
            violations, [],
            f"real rider violation(s) found: {rc.format_violations(violations)}",
        )

    def test_repeated_call_is_memoized(self):
        # Task 367: find_violations() rescanned the whole public tree on
        # every call, unconditionally -- one of five siblings sharing the
        # shape vault_leak_check.py's find_leaks() had. Proves a second
        # call against the same orita_dir is now cheap and still returns
        # the identical result.
        import time
        rc.clear_cache()
        start = time.time()
        first = rc.find_violations()
        first_elapsed = time.time() - start

        start = time.time()
        second = rc.find_violations()
        second_elapsed = time.time() - start

        self.assertEqual(first, second)
        self.assertLess(
            second_elapsed, max(first_elapsed / 10, 0.05),
            f"second call ({second_elapsed:.3f}s) was not meaningfully "
            f"cheaper than the first ({first_elapsed:.3f}s).",
        )
        rc.clear_cache()


class NegationCuesDeliberateDivergenceCase(unittest.TestCase):
    """Task 462. `tools/rider_check.py`'s own comments (and this file's,
    before this task) asserted its `_NEGATION_CUES` word list "mirrors
    star_covenant_check.py's own _NEGATION_CUES exactly" -- a claim that
    was never actually true (this file's list adds "no"/"without"/"zero"
    and lacks "wouldn't") and directly contradicted `tools/text_patterns.
    py`'s own task-418 docstring, which classifies rider_check.py as one
    of four files that tune their own negation list on purpose. Both
    claims were committed, live, side by side. This pins the TRUE
    relationship as a running fact so a future task can't "fix" the
    now-corrected comment by silently unifying the two lists instead --
    that would be the real, unasked-for behavior change task 418 itself
    already warned against."""

    def test_rider_check_negation_cues_are_not_a_byte_for_byte_mirror(self):
        tp = _load("text_patterns", os.path.join(ROOT, "tools", "text_patterns.py"))
        self.assertNotEqual(rc._NEGATION_CUES.pattern, tp.NEGATION_CUES_STANDARD.pattern)

    def test_rider_check_negation_cues_do_not_import_the_shared_constant(self):
        with open(os.path.join(ROOT, "tools", "rider_check.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertIn("_NEGATION_CUES = re.compile(", source)
        self.assertNotIn("text_patterns.NEGATION_CUES_STANDARD", source)


if __name__ == "__main__":
    unittest.main()
