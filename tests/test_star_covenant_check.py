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


if __name__ == "__main__":
    unittest.main()
