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


if __name__ == "__main__":
    unittest.main()
