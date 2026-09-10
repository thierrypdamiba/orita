"""Proves tools/task_reference_check.py actually catches a stale `(task N`
/ `(row N of ROADMAP.md` citation (a number that resolves in neither the
live ROADMAP.md nor any ROADMAP-ARCHIVE-*.md sibling), stays clean when
every citation resolves (live or archived), ignores bare "task 16" prose
that isn't a parenthetical citation, and confirms the real, currently
committed docs this checker scans are clean right now (the live find that
motivated building it -- fencepost/ONBOARDING.md's stale "row 16" pointer
-- is fixed, not just theorized about).
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


trc = _load("task_reference_check", os.path.join(ROOT, "tools", "task_reference_check.py"))


def _write(tmpdir, name, text):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _roadmap_fixture(tmp, live_rows, archive_rows=None):
    """Build a minimal ROADMAP.md (+ optional ROADMAP-ARCHIVE-001-5.md)
    fixture, shaped like the real files' `| N | status | ... |` rows."""
    live_text = "# Roadmap\n\n" + "\n".join(f"| {n} | DONE | someone | did it | ok |" for n in live_rows) + "\n"
    _write(tmp, "ROADMAP.md", live_text)
    if archive_rows:
        arc_text = "# Archive\n\n" + "\n".join(f"| {n} | DONE | someone | did it | ok |" for n in archive_rows) + "\n"
        _write(tmp, "ROADMAP-ARCHIVE-001-5.md", arc_text)


class TestKnownTaskNumbers(unittest.TestCase):
    def test_collects_rows_from_live_and_every_archive_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _roadmap_fixture(tmp, live_rows=[10, 11], archive_rows=[1, 2, 3])
            self.assertEqual(trc.known_task_numbers(root=tmp), {1, 2, 3, 10, 11})

    def test_missing_roadmap_files_is_an_empty_set_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(trc.known_task_numbers(root=tmp), set())


class TestCheckTaskReferences(unittest.TestCase):
    def test_clean_when_every_citation_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            _roadmap_fixture(tmp, live_rows=[20], archive_rows=[16])
            doc = _write(tmp, "ONBOARDING.md", "the seam (task 16, archived) isn't wired yet.\n")
            result = trc.check_task_references(root=tmp, docs=[doc])
        self.assertTrue(result["clean"], result)
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(result["stale"], [])

    def test_catches_a_citation_that_resolves_nowhere(self):
        """The exact drift that motivated this module: an archiving cut
        moves a row out of ROADMAP.md and a hand-written doc citation is
        never re-checked against where it landed."""
        with tempfile.TemporaryDirectory() as tmp:
            _roadmap_fixture(tmp, live_rows=[20], archive_rows=[])  # task 16 lives nowhere
            doc = _write(tmp, "ONBOARDING.md", "the seam (row 16 of ROADMAP.md) isn't built yet.\n")
            result = trc.check_task_references(root=tmp, docs=[doc])
        self.assertFalse(result["clean"])
        self.assertEqual(len(result["stale"]), 1)
        self.assertEqual(result["stale"][0]["task"], 16)
        self.assertIn("ONBOARDING.md", result["stale"][0]["file"])

    def test_bare_task_number_prose_is_not_a_citation(self):
        """"task 16" without a leading paren is ordinary narration (e.g. a
        BUILDLOG.md-style sentence), not a cross-reference -- must not be
        flagged even though 16 doesn't resolve in this fixture."""
        with tempfile.TemporaryDirectory() as tmp:
            _roadmap_fixture(tmp, live_rows=[20], archive_rows=[])
            doc = _write(tmp, "ONBOARDING.md", "task 16 shipped a fixture-driven detector.\n")
            result = trc.check_task_references(root=tmp, docs=[doc])
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["citations"], [])

    def test_missing_doc_file_is_skipped_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            _roadmap_fixture(tmp, live_rows=[20], archive_rows=[16])
            result = trc.check_task_references(root=tmp, docs=[os.path.join(tmp, "NOPE.md")])
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["citations"], [])


class TestFormatTaskReferences(unittest.TestCase):
    def test_clean_message_names_the_citation_count(self):
        msg = trc.format_task_references({"clean": True, "citations": [1, 2], "stale": []})
        self.assertIn("clean", msg)
        self.assertIn("2 citation", msg)

    def test_stale_message_names_file_line_and_task(self):
        result = {
            "clean": False,
            "citations": [{"file": "fencepost/ONBOARDING.md", "line": 168, "task": 16}],
            "stale": [{"file": "fencepost/ONBOARDING.md", "line": 168, "task": 16}],
        }
        msg = trc.format_task_references(result)
        self.assertIn("STALE", msg)
        self.assertIn("fencepost/ONBOARDING.md:168", msg)
        self.assertIn("task 16", msg)


class TestLiveRepoIsClean(unittest.TestCase):
    """The real find this module was built from: fencepost/ONBOARDING.md's
    citation of task 16 must resolve now, against the real, live repo."""

    def test_real_scanned_docs_have_no_stale_citation(self):
        result = trc.check_task_references()
        self.assertTrue(result["clean"], result["stale"])

    def test_task_16_is_a_real_known_task_number(self):
        self.assertIn(16, trc.known_task_numbers())
