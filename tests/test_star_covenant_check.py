"""Task 99. Proves tools/star_covenant_check.py's scan actually bites on a
synthetic begging sentence, stays clean on the town's own legitimate
star/follow vocabulary (cadence counts, the n-1 epithet, negated quotes,
third-person predictions), and -- the real point -- confirms the live,
current orita checkout holds zero violations today.
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


scc = _load("star_covenant_check", os.path.join(ROOT, "tools", "star_covenant_check.py"))


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

    def test_synthetic_begging_sentence_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "# Today's report\n\nWe found a great gap. Please star us to see more!\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "please star")
        formatted = scc.format_violations(violations)
        self.assertIn("VIOLATION(S) FOUND", formatted)
        self.assertIn("Star Covenant broken", formatted)

    def test_star_the_town_is_detected(self):
        # Task 461: "town" is this project's own dominant self-referential
        # noun (CHARTER.md:93: "star the town and it records your name in
        # stone") -- the exact noun this check's "star this/our/the repo"
        # pattern never covered pre-fix, unlike the sibling copy in
        # petition_limits_check.py, which already included it.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "This project is worth a look. Star the town if you enjoy it!\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        patterns = {v["pattern"] for v in violations}
        self.assertIn("star this/our/the repo", patterns)

    def test_follow_begging_is_detected(self):
        _write(
            os.path.join(self.orita, "houses", "kwaku-ananse", "journal", "0099-test.md"),
            "# Journal\n\nA great story today. Follow us for the next chapter!\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "follow us/@oritatown")

    def test_distinct_content_reports_clean(self):
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "# Today's report\n\nA release shipped but never got announced. That is the gap.\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])
        self.assertIn("clean", scc.format_violations(violations))

    def test_bare_star_and_follow_words_are_not_flagged(self):
        # This town's own voice uses "star"/"follow" constantly and
        # legitimately -- cadence claims, the n-1 counter, epithets. Only
        # an imperative ASK is a violation, not the bare word.
        _write(
            os.path.join(self.orita, "houses", "off-by-one", "journal", "0099-test.md"),
            "# Journal\n\nThe star count sits at 41 today. The counter reads n-1, "
            "as it always has. I followed the thread of the bug to its root.\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negated_quote_is_not_flagged(self):
        # "The CTA is never 'please star'" names the exact refused phrase
        # inside a negation -- the real shape STRATEGY.md's own line takes.
        _write(
            os.path.join(self.orita, "STRATEGY.md"),
            'The CTA is never "please star" -- it is "connect your own and we\'ll find yours."\n',
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_third_person_prediction_is_not_flagged(self):
        # "mortals will star the repo" describes what mortals may choose
        # to do, in the third person -- not an ask of the reader. The real
        # shape docs/gods/off-by-one.html and records/founding/visions.md
        # both hold live today.
        _write(
            os.path.join(self.orita, "docs", "gods", "off-by-one.html"),
            "<p>Mortals will star the repo specifically to be the one that ends it.</p>\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_real_imperative_still_caught_despite_unrelated_will_elsewhere(self):
        # A negation cue in an EARLIER, unrelated sentence must never mask
        # a real violation in a later, clean sentence -- the negation
        # check is scoped to the current sentence only.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "The town will ship more tomorrow. Drop a star before you go!\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "drop a star")

    def test_semicolon_joined_unrelated_will_no_longer_masks_a_real_ask(self):
        # Task 200: the "current sentence" window used to end only at
        # `.`/`!`/`?`/newline, so a semicolon-joined independent clause
        # counted as the SAME sentence as an earlier, unrelated "will" --
        # masking a real, present-tense imperative that followed the
        # semicolon. A period-joined version of the identical shape
        # (test_real_imperative_still_caught_despite_unrelated_will_elsewhere,
        # above) was already caught correctly; only the semicolon variant
        # was the live gap.
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "It will surely happen one day; please star the repo now.\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        patterns = {v["pattern"] for v in violations}
        self.assertIn("please star", patterns)

    def test_quoted_documentation_example_is_not_flagged(self):
        # The check's own docs/ROADMAP text legitimately lists the exact
        # phrase-shapes it hunts for as quoted examples -- the real false
        # positive this task's own first live run hit against ROADMAP.md
        # once task 99's row was written and scanned by its own checker.
        _write(
            os.path.join(self.orita, "ROADMAP.md"),
            'Hunts for an ask ("please star", "give us a star", "follow us", "smash that follow", etc).\n',
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_non_md_html_files_are_not_scanned(self):
        _write(
            os.path.join(self.orita, "tools", "scratch.py"),
            "# please star this repo\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_missing_dir_returns_empty_not_crash(self):
        violations = scc.find_violations(orita_dir=os.path.join(self.orita, "does-not-exist"))
        self.assertEqual(violations, [])

    def test_automatic_consequence_and_form_is_not_flagged(self):
        # Task 461: closing the real "town" noun gap made this checker see,
        # for the first time, CHARTER.md's own load-bearing description of
        # the Founders' Wall -- a real live match this test proves stays
        # clean. Third-person "it records" describes an automatic
        # consequence of an existing public API, not an appeal to the
        # reader.
        _write(
            os.path.join(self.orita, "CHARTER.md"),
            "renders a Founders' Wall from the stargazers API: "
            "star the town and it records your name in stone.\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_automatic_consequence_comma_form_is_not_flagged(self):
        # The same sentence, comma-joined instead of "and"-joined -- the
        # exact shape docs/founding.html's meta tags use.
        _write(
            os.path.join(self.orita, "docs", "founding.html"),
            "<meta name=\"description\" content=\"the Founders' Wall — "
            "star the town, it records your name in stone.\">\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_automatic_consequence_guard_does_not_mask_real_begging(self):
        # The guard is scoped to third-person "it <verb>s" specifically --
        # it must never swallow an actual ask phrased with a similar
        # "star X and <benefit>" shape that doesn't use "it".
        _write(
            os.path.join(self.orita, "docs", "report.md"),
            "Star this repo and get notified of every release!\n",
        )
        violations = scc.find_violations(orita_dir=self.orita)
        patterns = {v["pattern"] for v in violations}
        self.assertIn("star this/our/the repo", patterns)


class LiveRepoCase(unittest.TestCase):
    """The real point of task 99: run the scan against the actual, current
    checkout and confirm the Star Covenant has genuinely held, not just
    been asserted in prose."""

    def test_real_checkout_holds_zero_violations_today(self):
        violations = scc.find_violations()
        self.assertEqual(
            violations, [],
            f"real Star Covenant violation(s) found: {scc.format_violations(violations)}",
        )

    def test_repeated_call_is_memoized(self):
        # Task 367: find_violations() rescanned the whole public tree on
        # every call, unconditionally -- one of five siblings sharing the
        # shape vault_leak_check.py's find_leaks() had. Proves a second
        # call against the same orita_dir is now cheap and still returns
        # the identical result.
        import time
        scc.clear_cache()
        start = time.time()
        first = scc.find_violations()
        first_elapsed = time.time() - start

        start = time.time()
        second = scc.find_violations()
        second_elapsed = time.time() - start

        self.assertEqual(first, second)
        self.assertLess(
            second_elapsed, max(first_elapsed / 10, 0.05),
            f"second call ({second_elapsed:.3f}s) was not meaningfully "
            f"cheaper than the first ({first_elapsed:.3f}s).",
        )
        scc.clear_cache()


if __name__ == "__main__":
    unittest.main()
