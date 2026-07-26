"""Task 74. The last hand-recalled ritual number, made testable: proves
the "has anything landed in DECREES/, HAND/queue.md, HAND/verdicts/, or
HAND/proclamations/ since last hour" call -- made by hand in every
BUILDLOG ritual line since the daily Report existed -- resolves the same
way every time, instead of by recall.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "word_watch", os.path.join(ROOT, "tools", "word_watch.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ww = _load()


class _TempTownCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "DECREES"))
        os.makedirs(os.path.join(self.tmp, "HAND", "verdicts"))
        os.makedirs(os.path.join(self.tmp, "HAND", "proclamations"))
        with open(os.path.join(self.tmp, "DECREES", "001-door.md"), "w") as f:
            f.write("the door in the mortal sky\n")
        with open(os.path.join(self.tmp, "HAND", "queue.md"), "w") as f:
            f.write("# The Petition Queue\n\nempty\n")
        with open(os.path.join(self.tmp, "HAND", "verdicts", "0001.md"), "w") as f:
            f.write("verdict 1\n")
        self.log = os.path.join(self.tmp, "HAND", "word-check-log.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestComputeWordState(_TempTownCase):
    def test_walks_all_four_tracked_places(self):
        state = ww.compute_word_state(root=self.tmp)
        rels = set(state["files"])
        self.assertIn("DECREES/001-door.md", rels)
        self.assertIn("HAND/queue.md", rels)
        self.assertIn(os.path.join("HAND", "verdicts", "0001.md"), rels)

    def test_missing_tracked_path_contributes_nothing(self):
        # proclamations/ dir exists but empty; no error, just absent from files
        state = ww.compute_word_state(root=self.tmp)
        self.assertFalse(any(p.startswith("HAND/proclamations") for p in state["files"]))

    def test_state_is_sorted_and_deterministic(self):
        state1 = ww.compute_word_state(root=self.tmp)
        state2 = ww.compute_word_state(root=self.tmp)
        self.assertEqual(list(state1["files"]), sorted(state1["files"]))
        self.assertEqual(state1, state2)


class TestRecordWordCheck(_TempTownCase):
    def test_records_a_line(self):
        state = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state, "2026-07-15T01:00:00Z", path=self.log)
        with open(self.log) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_never_edits_a_prior_line(self):
        state = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state, "2026-07-15T00:00:00Z", path=self.log)
        with open(self.log) as f:
            before = f.readlines()
        ww.record_word_check(state, "2026-07-15T01:00:00Z", path=self.log)
        with open(self.log) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)


class TestLastWordState(_TempTownCase):
    def test_none_when_never_checked(self):
        self.assertIsNone(ww.last_word_state(path=self.log))

    def test_returns_the_most_recent_not_the_first(self):
        state1 = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state1, "2026-07-15T00:00:00Z", path=self.log)
        with open(os.path.join(self.tmp, "HAND", "queue.md"), "a") as f:
            f.write("a new petition\n")
        state2 = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state2, "2026-07-15T01:00:00Z", path=self.log)
        last = ww.last_word_state(path=self.log)
        self.assertEqual(last["checked_at"], "2026-07-15T01:00:00Z")

    def test_entries_marks_a_malformed_line_instead_of_raising(self):
        # A hand-edit, stray merge-conflict marker, or truncated write can
        # leave a line that isn't valid JSON at all -- _entries() must name
        # it, not crash with an uncaught json.JSONDecodeError (the exact
        # crash tools/ledger.py's _entries() had before task 238's fix).
        state = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state, "2026-07-15T00:00:00Z", path=self.log)
        with open(self.log, "a") as f:
            f.write('{"files": {}, "checked_at": broken <<<< not json\n')
        entries = ww._entries(path=self.log)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_raises_tampered_error_on_a_malformed_tip_instead_of_crashing(self):
        state = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state, "2026-07-15T00:00:00Z", path=self.log)
        with open(self.log, "a") as f:
            f.write('{"files": {}, "checked_at": broken <<<< not json\n')
        # Pre-fix this raised an uncaught json.JSONDecodeError; it must now
        # raise the named, catchable WordWatchTamperedError instead.
        with self.assertRaises(ww.WordWatchTamperedError):
            ww.last_word_state(path=self.log)

    def test_entries_marks_a_non_dict_line_instead_of_crashing(self):
        # A line can parse cleanly as JSON but not be an object at all (a
        # bare number, null, list, or stray string) -- _entries() must name
        # it the same as a decode failure, not hand back the raw value for
        # a caller's unconditional .get("_malformed") to crash on.
        state = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state, "2026-07-15T00:00:00Z", path=self.log)
        with open(self.log, "a") as f:
            f.write("5\n")
        entries = ww._entries(path=self.log)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_raises_tampered_error_on_a_non_dict_tip_instead_of_crashing(self):
        # Pre-fix this raised an uncaught AttributeError ('int' object has
        # no attribute 'get'); it must now raise the named, catchable
        # WordWatchTamperedError instead, same as a decode failure.
        state = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state, "2026-07-15T00:00:00Z", path=self.log)
        with open(self.log, "a") as f:
            f.write("5\n")
        with self.assertRaises(ww.WordWatchTamperedError):
            ww.last_word_state(path=self.log)

    def test_a_valid_tip_after_a_malformed_earlier_line_is_unaffected(self):
        # Only the TIP matters for last_word_state's guess-refusal -- an
        # older malformed line sitting earlier in the log (already surfaced
        # by _entries(), just not at the tip) must not block a real read.
        state1 = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state1, "2026-07-15T00:00:00Z", path=self.log)
        with open(self.log, "a") as f:
            f.write('{"broken <<<< not json\n')
        with open(os.path.join(self.tmp, "HAND", "queue.md"), "a") as f:
            f.write("a new petition\n")
        state2 = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state2, "2026-07-15T01:00:00Z", path=self.log)
        last = ww.last_word_state(path=self.log)
        self.assertEqual(last["checked_at"], "2026-07-15T01:00:00Z")


class TestWordDelta(_TempTownCase):
    def test_due_when_never_checked_before(self):
        state = ww.compute_word_state(root=self.tmp)
        changed, reason = ww.word_delta(state, path=self.log)
        self.assertTrue(changed)
        self.assertIn("no prior word check", reason)

    def test_not_due_when_fully_unchanged(self):
        state = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state, "2026-07-15T00:00:00Z", path=self.log)
        changed, reason = ww.word_delta(state, path=self.log)
        self.assertFalse(changed)
        self.assertIn("unchanged since 2026-07-15T00:00:00Z", reason)

    def test_due_when_a_decree_file_is_added(self):
        state1 = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state1, "2026-07-15T00:00:00Z", path=self.log)
        with open(os.path.join(self.tmp, "DECREES", "002-new.md"), "w") as f:
            f.write("a new decree\n")
        state2 = ww.compute_word_state(root=self.tmp)
        changed, reason = ww.word_delta(state2, path=self.log)
        self.assertTrue(changed)
        self.assertIn("new word(s) landed", reason)
        self.assertIn("DECREES/002-new.md", reason)

    def test_due_when_queue_md_is_edited(self):
        state1 = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state1, "2026-07-15T00:00:00Z", path=self.log)
        with open(os.path.join(self.tmp, "HAND", "queue.md"), "a") as f:
            f.write("## 2026-07-15 -- a new petition\n")
        state2 = ww.compute_word_state(root=self.tmp)
        changed, reason = ww.word_delta(state2, path=self.log)
        self.assertTrue(changed)
        self.assertIn("tracked file(s) changed", reason)
        self.assertIn("HAND/queue.md", reason)

    def test_due_when_a_verdict_is_added(self):
        state1 = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state1, "2026-07-15T00:00:00Z", path=self.log)
        with open(os.path.join(self.tmp, "HAND", "verdicts", "0002.md"), "w") as f:
            f.write("verdict 2\n")
        state2 = ww.compute_word_state(root=self.tmp)
        changed, reason = ww.word_delta(state2, path=self.log)
        self.assertTrue(changed)
        self.assertIn("new word(s) landed", reason)

    def test_due_when_a_tracked_file_is_removed(self):
        state1 = ww.compute_word_state(root=self.tmp)
        ww.record_word_check(state1, "2026-07-15T00:00:00Z", path=self.log)
        os.remove(os.path.join(self.tmp, "HAND", "verdicts", "0001.md"))
        state2 = ww.compute_word_state(root=self.tmp)
        changed, reason = ww.word_delta(state2, path=self.log)
        self.assertTrue(changed)
        self.assertIn("removed", reason)


if __name__ == "__main__":
    unittest.main()
