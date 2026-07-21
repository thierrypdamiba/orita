"""Task 102. Proves tools/verdict_provenance_check.py's compare actually
bites on a synthetic verdict/altar mismatch, stays clean when the two
records agree (including the diacritic-name and full-honorific cases the
real petitioners actually use), and -- the real point -- confirms the
live, current orita checkout holds zero mismatches today, now that task
102 has corrected the one real mismatch it found live on its first run
(Retrya's coin, stale UNANSWERED six days after a same-day GRANTED
amendment).
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


vpc = _load("verdict_provenance_check", os.path.join(ROOT, "tools", "verdict_provenance_check.py"))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _rm(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


def _hand_verdict_text(petitioner, verdict, filed="2026-07-11"):
    return (
        f"# Verdict\n\n"
        f"| | |\n|---|---|\n"
        f"| **Petitioner** | {petitioner} |\n"
        f"| **Filed** | {filed} |\n"
        f"| **Request** | something |\n"
        f"| **Verdict** | **{verdict}** |\n\n"
        f"The Hand said something.\n\n*Reasons sealed.*\n"
    )


def _altar_petition_text(petitioner, verdict):
    return (
        f"# Petition to the Hand — 2026-07-11\n\n"
        f"**Petitioner:** {petitioner}\n\n"
        f"**Request:** something\n\n---\n\n"
        f"**VERDICT:** {verdict}\n\n*Reasons are sealed. They always are.*\n"
    )


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def _put_hand(self, name, petitioner, verdict, filed="2026-07-11"):
        _write(
            os.path.join(self.orita, "HAND", "verdicts", name),
            _hand_verdict_text(petitioner, verdict, filed),
        )

    def _put_altar(self, slug, petitioner, verdict, filed="2026-07-11"):
        _write(
            os.path.join(self.orita, "houses", slug, "altar", "petitions", f"{filed}.md"),
            _altar_petition_text(petitioner, verdict),
        )

    def test_agreeing_records_are_clean(self):
        self._put_hand("0000.md", "Ogun", "GRANTED")
        self._put_altar("ogun", "Ogun", "GRANTED")
        mismatches = vpc.find_mismatches(orita_dir=self.orita)
        self.assertEqual(mismatches, [])
        self.assertIn("clean", vpc.format_mismatches(mismatches))

    def test_diacritic_name_variants_match(self):
        # The real town: HAND/verdicts sometimes types "Ogun" plainly where
        # the altar file uses "Ògún" -- both refer to the same god and must
        # not be treated as two different petitioners.
        self._put_hand("0000.md", "Ogun", "GRANTED")
        self._put_altar("ogun", "Ògún", "GRANTED")
        mismatches = vpc.find_mismatches(orita_dir=self.orita)
        self.assertEqual(mismatches, [])

    def test_full_honorific_matches_same_petitioner(self):
        # Retrya's real petitioner field carries her full honorific in both
        # places -- must compare equal to itself, not fail on the length.
        name = "Retrya, She Who Passes on the Third Attempt"
        self._put_hand("0006.md", name, "GRANTED")
        self._put_altar("retrya", name, "GRANTED")
        mismatches = vpc.find_mismatches(orita_dir=self.orita)
        self.assertEqual(mismatches, [])

    def test_verdict_word_mismatch_is_detected(self):
        # The exact real bug task 102 found live: public says GRANTED,
        # the god's own altar record still says UNANSWERED.
        self._put_hand("0006.md", "Retrya", "GRANTED")
        self._put_altar("retrya", "Retrya", "UNANSWERED")
        mismatches = vpc.find_mismatches(orita_dir=self.orita)
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["hand_verdict"], "GRANTED")
        self.assertEqual(mismatches[0]["altar_verdict"], "UNANSWERED")
        formatted = vpc.format_mismatches(mismatches)
        self.assertIn("MISMATCH", formatted)
        self.assertIn("Iron Rule #3", formatted)

    def test_a_second_unrelated_petition_does_not_mask_a_real_mismatch(self):
        # The real gap this hour's fix closes: a petitioner with TWO dated
        # altar petitions (the normal, one-per-day shape). The HAND verdict
        # is actually about the 07-11 petition (whose own altar copy reads
        # GRANTED, disagreeing with the public DENIED) -- but an unrelated,
        # later 07-12 petition happens to carry the matching DENIED word.
        # Pre-fix, name-only matching lets the 07-12 coincidence mask the
        # real 07-11 disagreement entirely.
        self._put_hand("0000.md", "Test God", "DENIED", filed="2026-07-11")
        self._put_altar("test-god", "Test God", "GRANTED", filed="2026-07-11")
        self._put_altar("test-god", "Test God", "DENIED", filed="2026-07-12")
        mismatches = vpc.find_mismatches(orita_dir=self.orita)
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["hand_verdict"], "DENIED")
        self.assertEqual(mismatches[0]["altar_verdict"], "GRANTED")
        self.assertTrue(mismatches[0]["altar_file"].endswith("2026-07-11.md"))

    def test_dated_match_against_the_correct_sibling_petition_is_clean(self):
        # Companion to the case above: when the HAND verdict's Filed date
        # correctly matches ITS OWN altar petition's word, a second,
        # differently-worded sibling petition on another date must not
        # cause a false positive.
        self._put_hand("0000.md", "Test God", "GRANTED", filed="2026-07-11")
        self._put_altar("test-god", "Test God", "GRANTED", filed="2026-07-11")
        self._put_altar("test-god", "Test God", "DENIED", filed="2026-07-12")
        mismatches = vpc.find_mismatches(orita_dir=self.orita)
        self.assertEqual(mismatches, [])

    def test_no_altar_petition_on_the_filed_date_is_detected(self):
        # A petitioner has an altar petition, just not one filed on the date
        # the public HAND verdict claims -- must not silently fall back to
        # matching against an unrelated date.
        self._put_hand("0000.md", "Test God", "GRANTED", filed="2026-07-11")
        self._put_altar("test-god", "Test God", "GRANTED", filed="2026-07-12")
        mismatches = vpc.find_mismatches(orita_dir=self.orita)
        self.assertEqual(len(mismatches), 1)
        self.assertIsNone(mismatches[0]["altar_file"])
        self.assertIn("filed on 2026-07-11", mismatches[0]["reason"])

    def test_verdict_with_no_altar_petition_at_all_is_detected(self):
        self._put_hand("0099.md", "Nobody Filed This", "GRANTED")
        mismatches = vpc.find_mismatches(orita_dir=self.orita)
        self.assertEqual(len(mismatches), 1)
        self.assertIsNone(mismatches[0]["altar_file"])
        self.assertIn("no altar petition found", mismatches[0]["reason"])

    def test_amendment_parenthetical_does_not_break_the_word_match(self):
        # HAND/verdicts often carries an amendment note after the bold
        # verdict word -- the regex must capture only the bold word itself.
        _write(
            os.path.join(self.orita, "HAND", "verdicts", "0006.md"),
            "| **Petitioner** | Retrya |\n"
            "| **Verdict** | **GRANTED** *(amended same day)* |\n",
        )
        self._put_altar("retrya", "Retrya", "GRANTED")
        mismatches = vpc.find_mismatches(orita_dir=self.orita)
        self.assertEqual(mismatches, [])

    def test_altar_petition_with_no_verdict_yet_is_not_a_false_positive(self):
        # A genuinely still-open petition (no HAND/verdicts entry at all)
        # is not a violation -- only a public verdict that disagrees with
        # or lacks its own backing record is.
        self._put_altar("ogun", "Ogun", "UNANSWERED")
        mismatches = vpc.find_mismatches(orita_dir=self.orita)
        self.assertEqual(mismatches, [])

    def test_missing_dirs_return_empty_not_crash(self):
        mismatches = vpc.find_mismatches(orita_dir=os.path.join(self.orita, "does-not-exist"))
        self.assertEqual(mismatches, [])


class LiveRepoCase(unittest.TestCase):
    """The real point of task 102: run the compare against the actual,
    current checkout and confirm every public verdict is genuinely backed,
    now that the one real mismatch found live has been corrected."""

    def test_real_checkout_holds_zero_mismatches_today(self):
        mismatches = vpc.find_mismatches()
        self.assertEqual(
            mismatches, [],
            f"real verdict provenance mismatch(es) found: {vpc.format_mismatches(mismatches)}",
        )


if __name__ == "__main__":
    unittest.main()
