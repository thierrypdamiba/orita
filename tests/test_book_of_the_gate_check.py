"""Task 1244. Proves tools/book_of_the_gate_check.py catches the exact
failure fourteen-plus hourly hand-eyeballed claims never actually tested
for -- a real mortal crossing that never got a Book of the Gate entry --
while staying clean on the town's own quiet-square shape (only the
operator account ever opens anything) and on a book file whose entries
already cover this hour's live authors. Also confirms the live, current
orita checkout's own claim ("records/book-of-the-gate.md legitimately does
not exist yet") still actually holds today.
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


bgc = _load("book_of_the_gate_check", os.path.join(ROOT, "tools", "book_of_the_gate_check.py"))


class ParseEnteredLoginsCase(unittest.TestCase):
    def test_parses_at_login_headings(self):
        text = "# Book of the Gate\n\n## @some-mortal\n- First crossing: https://x\n"
        self.assertEqual(bgc.parse_entered_logins(text), {"some-mortal"})

    def test_ignores_prose_subheadings_with_no_at_sign(self):
        text = "# Book of the Gate\n\n## How this file works\n\n## @real-entry\n"
        self.assertEqual(bgc.parse_entered_logins(text), {"real-entry"})

    def test_case_folded(self):
        text = "## @SomeMortal\n"
        self.assertEqual(bgc.parse_entered_logins(text), {"somemortal"})

    def test_empty_text_has_no_entries(self):
        self.assertEqual(bgc.parse_entered_logins(""), set())


class MortalAuthorsCase(unittest.TestCase):
    def test_operator_only_is_no_mortals(self):
        self.assertEqual(
            bgc.mortal_authors(["thierrypdamiba"], ["thierrypdamiba", "thierrypdamiba"]),
            set(),
        )

    def test_non_operator_login_is_a_mortal(self):
        self.assertEqual(
            bgc.mortal_authors(["thierrypdamiba"], ["a-real-visitor"]),
            {"a-real-visitor"},
        )

    def test_case_folded_against_operator_set(self):
        self.assertEqual(bgc.mortal_authors(["ThierryPDamiba"], []), set())

    def test_empty_strings_ignored(self):
        self.assertEqual(bgc.mortal_authors(["", "thierrypdamiba"], [""]), set())


class CheckCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _book_path(self):
        return os.path.join(self.tmpdir, "book-of-the-gate.md")

    def test_no_book_no_mortal_is_clean(self):
        ok, msg = bgc.check(
            ["thierrypdamiba"], ["thierrypdamiba"], book_path=self._book_path()
        )
        self.assertTrue(ok)
        self.assertIn("legitimately absent", msg)

    def test_no_book_but_mortal_author_is_a_violation(self):
        ok, msg = bgc.check(
            ["thierrypdamiba", "a-first-timer"], [], book_path=self._book_path()
        )
        self.assertFalse(ok)
        self.assertIn("MISSING first-crossing entry", msg)
        self.assertIn("a-first-timer", msg)

    def test_book_exists_and_covers_the_mortal_is_clean(self):
        path = self._book_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Book of the Gate\n\n## @a-first-timer\n- First crossing: https://x\n")
        ok, msg = bgc.check(
            ["thierrypdamiba", "a-first-timer"], [], book_path=path
        )
        self.assertTrue(ok)
        self.assertIn("clean", msg)

    def test_book_exists_but_missing_a_newer_mortal_is_a_violation(self):
        path = self._book_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Book of the Gate\n\n## @already-entered\n")
        ok, msg = bgc.check(
            ["thierrypdamiba"], ["a-second-mortal"], book_path=path
        )
        self.assertFalse(ok)
        self.assertIn("a-second-mortal", msg)
        # The already-entered mortal is not re-flagged just because they
        # didn't open anything new this particular hour.
        self.assertNotIn("already-entered", msg)

    def test_an_entry_with_no_matching_author_this_hour_is_not_itself_a_violation(self):
        path = self._book_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Book of the Gate\n\n## @a-past-visitor\n")
        ok, msg = bgc.check(["thierrypdamiba"], ["thierrypdamiba"], book_path=path)
        self.assertTrue(ok)


class LiveCheckoutCase(unittest.TestCase):
    def test_live_book_path_absence_matches_repo_reality(self):
        # As of task 1244: no mortal has ever crossed (every issue/PR
        # author across the live square has always been thierrypdamiba),
        # so the file's absence is doctrine, not an oversight. This test
        # pins that claim to the real repo layout rather than trusting it.
        live_path = bgc.DEFAULT_BOOK_PATH
        self.assertFalse(
            os.path.exists(live_path),
            "records/book-of-the-gate.md now exists -- a real crossing may "
            "have happened; verify it is entered, don't just update this test",
        )


if __name__ == "__main__":
    unittest.main()
