"""Task 184. Proves tools/closing_keyword_guard.py actually catches the
real incident that motivated it (task 183's own commit message closed
issues #1 and #2 by accident on push), stays clean on safe rephrasings
and on numbers that were never open, and covers all 9 of GitHub's real
closing-keyword forms -- not just the narrower present-tense subset
fencepost/RECIPES/merged-pr-issue-still-open/detector.py uses for its
own different job.
"""
import importlib.util
import json
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


ckg = _load("closing_keyword_guard", os.path.join(ROOT, "tools", "closing_keyword_guard.py"))

# The real task 183 commit message body (d90de9f), verbatim, minus the
# trailer -- this is the actual text that closed real issues #1 and #2.
REAL_INCIDENT_MESSAGE = (
    "task 183: merged-pr-issue-still-open only ever saw the first closing keyword\n\n"
    "_closed_issue_number used _CLOSES_RE.search(), silently dropping every\n"
    "issue after the first one a merged PR's body named (\"closes #1 and fixes\n"
    "#2\" only ever checked #1). recipe.json's own author field names this\n"
    "recipe mine -- fixed to _closed_issue_numbers via .findall(), looped\n"
    "compute_gaps over every number per PR.\n"
)

# The open issue numbers at the moment that commit was pushed (1, 2, 3, 5
# were all open; task 183 itself does not appear in this list, it is a
# roadmap task number, not a GitHub issue).
REAL_OPEN_ISSUES_AT_INCIDENT = [1, 2, 3, 5]


class RealIncidentReproductionCase(unittest.TestCase):
    """The point of this module: prove it would have caught the actual
    incident before it happened, against the actual commit text."""

    def test_flags_the_real_task_183_message(self):
        ok, dangerous = ckg.check_message(REAL_INCIDENT_MESSAGE, REAL_OPEN_ISSUES_AT_INCIDENT)
        self.assertFalse(ok)
        self.assertEqual(dangerous, [1, 2])

    def test_refs_found_in_first_seen_order_deduped(self):
        refs = ckg.find_closing_refs(REAL_INCIDENT_MESSAGE)
        self.assertEqual(refs, [1, 2])


class KeywordGrammarCase(unittest.TestCase):
    """All 9 of GitHub's real closing-keyword forms, present and past
    tense -- the narrower `closes?|fixes?|resolves?` the merged-pr-
    issue-still-open recipe uses would miss the past-tense three."""

    def test_present_tense_forms(self):
        for kw in ("close", "closes", "fix", "fixes", "resolve", "resolves"):
            with self.subTest(kw=kw):
                self.assertEqual(ckg.find_closing_refs(f"this {kw} #42"), [42])

    def test_past_tense_forms(self):
        for kw in ("closed", "fixed", "resolved"):
            with self.subTest(kw=kw):
                self.assertEqual(ckg.find_closing_refs(f"this {kw} #42"), [42])

    def test_case_insensitive(self):
        self.assertEqual(ckg.find_closing_refs("Closes #7"), [7])
        self.assertEqual(ckg.find_closing_refs("FIXES #7"), [7])

    def test_no_number_no_match(self):
        self.assertEqual(ckg.find_closing_refs("this closes the loop"), [])

    def test_unrelated_word_no_match(self):
        self.assertEqual(ckg.find_closing_refs("enclosed #7 in quotes"), [])

    def test_colon_form(self):
        # docs.github.com, "Using keywords in issues and pull requests":
        # "The keywords can be followed by colons or in uppercase. For
        # example: Closes: #10, CLOSES #10, or CLOSES: #10." GitHub
        # closes on push for this form exactly like the bare form.
        for kw in ("close", "closes", "closed", "fix", "fixes", "fixed",
                   "resolve", "resolves", "resolved"):
            with self.subTest(kw=kw):
                self.assertEqual(ckg.find_closing_refs(f"this {kw}: #42"), [42])
        self.assertEqual(ckg.find_closing_refs("CLOSES: #7"), [7])

    def test_colon_form_flagged_as_dangerous(self):
        ok, dangerous = ckg.check_message("Closes: #1", [1])
        self.assertFalse(ok)
        self.assertEqual(dangerous, [1])


class DangerScopeCase(unittest.TestCase):
    """Only currently-open numbers are a live risk; closed/nonexistent
    numbers are inert and must not be flagged."""

    def test_number_not_open_is_not_dangerous(self):
        ok, dangerous = ckg.check_message("closes #999", [1, 2, 3])
        self.assertTrue(ok)
        self.assertEqual(dangerous, [])

    def test_mixed_open_and_not_open(self):
        ok, dangerous = ckg.check_message("closes #1 and fixes #999", [1, 2, 3])
        self.assertFalse(ok)
        self.assertEqual(dangerous, [1])

    def test_empty_open_list_never_dangerous(self):
        ok, dangerous = ckg.check_message("closes #1 and fixes #2", [])
        self.assertTrue(ok)
        self.assertEqual(dangerous, [])


class SafeRephrasingCase(unittest.TestCase):
    """The actual fix this module recommends: present-participle prose
    describing the pattern, which is grammatically outside GitHub's own
    keyword list, stays clean."""

    def test_present_participle_is_safe(self):
        ok, dangerous = ckg.check_message("closing #1 and fixing #2", [1, 2])
        self.assertTrue(ok)
        self.assertEqual(dangerous, [])

    def test_no_exemption_for_quotes_or_backticks(self):
        # Deliberately proves the module does NOT trust quote marks or
        # backticks as safe -- GitHub's own commit-message parser does
        # not respect markdown, so this guard must not either.
        ok, dangerous = ckg.check_message('the phrase "closes #1"', [1])
        self.assertFalse(ok)
        ok2, dangerous2 = ckg.check_message("the phrase `closes #1`", [1])
        self.assertFalse(ok2)


class CliCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, content):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_check_mode_csv_dangerous_exits_nonzero(self):
        msg_path = self._write("msg.txt", "closes #1 and fixes #2")
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "closing_keyword_guard.py"),
             "check", msg_path, "1,2,3"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("DANGEROUS", result.stdout)

    def test_check_mode_clean_exits_zero(self):
        msg_path = self._write("msg.txt", "closing #1 and fixing #2")
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "closing_keyword_guard.py"),
             "check", msg_path, "1,2,3"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("clean", result.stdout)

    def test_check_live_mode_reads_square_state_shape(self):
        msg_path = self._write("msg.txt", "closes #1")
        state_path = self._write(
            "state.json",
            json.dumps({"issues": [{"number": 1, "updated_at": "x"}], "prs": []}),
        )
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "closing_keyword_guard.py"),
             "check-live", msg_path, state_path],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("DANGEROUS", result.stdout)


if __name__ == "__main__":
    unittest.main()
