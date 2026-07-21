"""Task 105. Proves tools/no_grading_check.py's scan actually bites on a
synthetic blame/grading sentence -- including inside a community recipe's
detector.py and recipe.json, the one surface CONTRIBUTING.md says "the code
cannot check for you" -- stays clean on the town's own legitimate
self-critique vocabulary ("worse than", negated quotes, quoted citations),
proves the hard-wrap negation-boundary fix actually bites, and -- the real
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


ngc = _load("no_grading_check", os.path.join(ROOT, "tools", "no_grading_check.py"))


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

    def test_dropped_the_ball_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "# Today's report\n\nThe integration dropped the ball on the release.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "dropped the ball")
        formatted = ngc.format_violations(violations)
        self.assertIn("VIOLATION(S) FOUND", formatted)
        self.assertIn("constraint #2 broken", formatted)

    def test_fault_is_detected(self):
        _write(
            os.path.join(self.orita, "fencepost", "REPORTS", "2099-01-01.md"),
            "# Report\n\nThe missed reminder was its fault, plainly.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "pronoun's fault")

    def test_to_blame_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The other automation is to blame for this gap.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "to blame")

    def test_failed_to_ship_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The bot failed to ship the promised update on time.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "failed to ship/post/catch/notice/update/announce")

    def test_let_someone_down_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The scheduler let everyone down this week.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "let ... down")

    def test_recipe_detector_headline_is_scanned(self):
        """The one surface CONTRIBUTING.md names explicitly: a community
        recipe's headline/detail prose lives in detector.py, not a .md
        file -- and the manifest gate (`recipes.py`'s own docstring) never
        reads it. This check has to, or the gap CONTRIBUTING.md names
        stays open."""
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "some-recipe", "detector.py"),
            'headline = "The other tool dropped the ball on this one"\n',
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertTrue(violations[0]["file"].endswith("detector.py"))

    def test_recipe_json_confidence_notes_is_scanned(self):
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "some-recipe", "recipe.json"),
            '{"confidence_notes": "high, because the other integration is to blame here"}\n',
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertTrue(violations[0]["file"].endswith("recipe.json"))


class CleanFixtureCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_worse_than_self_critique_is_not_flagged(self):
        """The town's own constant idiom -- comparing an approach to
        itself, never naming or ranking another tool. `houses/*/journal/
        *.md` uses this shape honestly, a dozen times, this week alone."""
        _write(
            os.path.join(self.orita, "houses", "off-by-one", "journal", "0099-test.md"),
            "A false alarm that never resets is worse than a stale audit trail.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_better_than_self_critique_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "houses", "retrya", "journal", "0099-test.md"),
            "I like this framing better than the one I started with.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negated_dropped_the_ball_on_one_line_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "It never says anyone dropped the ball.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_quoted_citation_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            'The rule quotes itself: never says anyone "drops the ball."\n',
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_hard_wrapped_negation_across_a_line_break_is_not_flagged(self):
        """The real bug the first live run against the actual checkout
        surfaced: `fencepost/CONTRIBUTING.md` hard-wraps its prose, so its
        own "No grading, ever" section's negation cue ("never") lands on
        the line ABOVE the match, not the same physical line. A bare `\\n`
        sentence boundary (star_covenant_check's original shape) would cut
        the negation window off right there and miss it. Proves the fix
        bites: reverting `_SENTENCE_BOUNDARY` to the original `[.!?\\n]`
        makes this exact fixture fail (checked by hand before writing this
        test -- see the module's own docstring)."""
        _write(
            os.path.join(self.orita, "fencepost", "CONTRIBUTING.md"),
            "It never names or ranks the human, the account, or any other\n"
            "tool or automation as having dropped the ball -- the same law\n"
            "every detector in this engine already keeps.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_semicolon_joined_unrelated_will_no_longer_masks_a_real_ask(self):
        """The sibling gap task 200 already found and fixed in
        `star_covenant_check.py` (the checker this module's own docstring
        says it mirrors "exactly"): a semicolon joins two independent
        clauses the same way a period does, but `_SENTENCE_BOUNDARY` never
        included `;`, so an unrelated, earlier future-tense clause on the
        near side of a semicolon from a real, present-tense blame sentence
        on the far side still fell inside the same negation window and
        silently suppressed it."""
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "This approach will improve over time; the vendor dropped the "
            "ball on the migration.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "dropped the ball")

    def test_double_newline_paragraph_break_still_ends_the_window(self):
        """The other half of the same fix: a real paragraph break (blank
        line) between an unrelated negation cue and a real, present-tense
        violation must still let the violation through -- widening the
        boundary must not swallow whole documents into one giant
        "sentence" and blind the guard entirely."""
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "It never says anyone dropped the ball, historically.\n"
            "\n"
            "The scheduler dropped the ball on today's release.\n",
        )
        violations = ngc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertIn("today's release", violations[0]["snippet"])


class LiveRepoCase(unittest.TestCase):
    def test_live_run_against_the_real_repo_is_clean(self):
        violations = ngc.find_violations(orita_dir=ROOT)
        self.assertEqual(
            violations, [],
            f"real, current checkout has {len(violations)} no-grading violation(s): {violations}",
        )


if __name__ == "__main__":
    unittest.main()
