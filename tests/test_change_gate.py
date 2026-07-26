"""Task 69. The change-gate itself, made testable: proves the "does this
hour's gap differ from the last one posted" call -- made by hand in every
BUILDLOG ritual line since the daily report existed -- resolves the same
way every time, for every god, instead of by re-reading prose.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "change_gate", os.path.join(ROOT, "tools", "change_gate.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


cg = _load()

REPORT_A = """# Fencepost Report — 2026-07-13

*The one thing that fell between accounts yesterday.*

**Milestone-level work shipped but never reached @oritatown** — confidence 0.85.

11 milestone commit(s) since 2026-07-12, none echoed in a post.

**The count.** 2 fenceposts named to date. The wall reads 1.
"""

REPORT_B = """# Fencepost Report — 2026-07-14

*The one thing that fell between accounts yesterday.*

**A release shipped but never tweeted** — confidence 0.91.

1 release since 2026-07-13, none echoed in a post.

**The count.** 3 fenceposts named to date. The wall reads 2.
"""

REPORT_EMPTY = """# Fencepost Report — 2026-07-11

*Desk has not opened.*

No gap surfaced yet.
"""

# Same category headline/confidence as REPORT_A (the milestone-gap kind
# renders this static headline every day it fires) but different evidence
# below it -- mirrors the real, live 2026-07-19 vs 2026-07-20 REPORTS/ pair
# that exposed this bug: same "Milestone-level..." headline, 15 vs 32
# commits, disjoint commit hashes.
REPORT_A_SAME_HEADLINE_DIFFERENT_EVIDENCE = """# Fencepost Report — 2026-07-14

*The one thing that fell between accounts yesterday.*

**Milestone-level work shipped but never reached @oritatown** — confidence 0.85.

32 milestone commit(s) since 2026-07-12, none echoed in a post.

**The count.** 3 fenceposts named to date. The wall reads 2.
"""


class _TempLogCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.path)  # record_posted_gap/_append must create it fresh

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)


class TestExtractPrimaryGap(unittest.TestCase):
    def test_extracts_the_bolded_gap_line(self):
        self.assertEqual(
            cg.extract_primary_gap(REPORT_A),
            "Milestone-level work shipped but never reached @oritatown",
        )

    def test_a_different_report_extracts_a_different_gap(self):
        self.assertEqual(
            cg.extract_primary_gap(REPORT_B),
            "A release shipped but never tweeted",
        )

    def test_none_when_no_parseable_gap(self):
        self.assertIsNone(cg.extract_primary_gap(REPORT_EMPTY))


class TestExtractGapIdentity(unittest.TestCase):
    def test_combines_headline_and_detail_line(self):
        self.assertEqual(
            cg.extract_gap_identity(REPORT_A),
            "Milestone-level work shipped but never reached @oritatown :: "
            "11 milestone commit(s) since 2026-07-12, none echoed in a post.",
        )

    def test_falls_back_to_bare_headline_when_no_detail_line(self):
        # A minimal report shape (headline only, nothing below it) must
        # still produce a usable identity -- unchanged from the pre-fix
        # bare-headline behavior in this case.
        report = "**A release shipped but never announced.** — confidence 0.82.\n"
        self.assertEqual(
            cg.extract_gap_identity(report),
            "A release shipped but never announced.",
        )

    def test_same_headline_different_evidence_yields_different_identity(self):
        # The real, live bug this closes: REPORT_A and this fixture share
        # the exact same bolded headline and confidence (the milestone-gap
        # kind renders a static category headline every day it fires) but
        # carry different evidence (15 vs 32 commits in the real incident,
        # 11 vs 32 here) -- extract_primary_gap alone cannot tell them
        # apart; extract_gap_identity must.
        self.assertNotEqual(
            cg.extract_gap_identity(REPORT_A),
            cg.extract_gap_identity(REPORT_A_SAME_HEADLINE_DIFFERENT_EVIDENCE),
        )

    def test_none_when_no_parseable_gap(self):
        self.assertIsNone(cg.extract_gap_identity(REPORT_EMPTY))


class TestRecordPostedGap(_TempLogCase):
    def test_records_a_line(self):
        cg.record_posted_gap("some gap", "2026-07-14T20:00:00Z", path=self.path)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_rejects_an_empty_gap(self):
        with self.assertRaises(ValueError):
            cg.record_posted_gap("", "2026-07-14T20:00:00Z", path=self.path)
        self.assertFalse(os.path.exists(self.path))

    def test_never_edits_a_prior_line(self):
        cg.record_posted_gap("first gap", "2026-07-14T01:00:00Z", path=self.path)
        with open(self.path) as f:
            before = f.readlines()
        cg.record_posted_gap("second gap", "2026-07-14T02:00:00Z", path=self.path)
        with open(self.path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)


class TestLastPostedGap(_TempLogCase):
    def test_none_when_never_posted(self):
        self.assertIsNone(cg.last_posted_gap(path=self.path))

    def test_returns_the_most_recent_not_the_first(self):
        cg.record_posted_gap("first gap", "2026-07-14T01:00:00Z", path=self.path)
        cg.record_posted_gap("second gap", "2026-07-14T02:00:00Z", path=self.path)
        self.assertEqual(cg.last_posted_gap(path=self.path), "second gap")

    def test_entries_marks_a_malformed_line_instead_of_raising(self):
        # A hand-edit, stray merge-conflict marker, or truncated write can
        # leave a line that isn't valid JSON at all -- _entries() must name
        # it, not crash with an uncaught json.JSONDecodeError (the exact
        # crash tools/ledger.py's _entries() had before task 238's fix).
        cg.record_posted_gap("first gap", "2026-07-14T01:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write('{"type": "posted", "gap": "broken <<<< not json\n')
        entries = cg._entries(path=self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_raises_tampered_error_on_a_malformed_tip_instead_of_crashing(self):
        cg.record_posted_gap("first gap", "2026-07-14T01:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write('{"type": "posted", "gap": "broken <<<< not json\n')
        # Pre-fix this raised an uncaught json.JSONDecodeError; it must now
        # raise the named, catchable PostedGapLogTamperedError instead.
        with self.assertRaises(cg.PostedGapLogTamperedError):
            cg.last_posted_gap(path=self.path)

    def test_a_valid_tip_after_a_malformed_earlier_line_is_unaffected(self):
        # Only the TIP matters for last_posted_gap's guess-refusal -- an
        # older malformed line sitting earlier in the log (already surfaced
        # by _entries(), just not at the tip) must not block a real read.
        cg.record_posted_gap("first gap", "2026-07-14T01:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write('{"broken <<<< not json\n')
        cg.record_posted_gap("second gap", "2026-07-14T02:00:00Z", path=self.path)
        self.assertEqual(cg.last_posted_gap(path=self.path), "second gap")

    def test_entries_marks_a_non_dict_valid_json_line_as_malformed_too(self):
        # A line can be syntactically valid JSON (json.loads succeeds) but
        # not an object at all -- a bare number, null, list, or string, the
        # shape a truncated-but-still-parseable write or a careless hand-
        # edit can leave behind. Every real entry this log ever writes
        # (record_posted_gap()) is a dict, so this is exactly as
        # untrustworthy as a decode failure and must get the same sentinel.
        cg.record_posted_gap("first gap", "2026-07-14T01:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("5\n")
        entries = cg._entries(path=self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_raises_tampered_error_on_a_non_dict_tip_instead_of_crashing(self):
        # Pre-fix this raised an uncaught AttributeError ('int' object has
        # no attribute 'get') from last_posted_gap()'s entries[-1].get(
        # "_malformed") call -- it must now raise the named, catchable
        # PostedGapLogTamperedError instead, same as a JSON-decode failure.
        cg.record_posted_gap("first gap", "2026-07-14T01:00:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("5\n")
        with self.assertRaises(cg.PostedGapLogTamperedError):
            cg.last_posted_gap(path=self.path)


class TestShouldPostGap(_TempLogCase):
    def test_due_when_never_posted_before(self):
        due, reason = cg.should_post_gap(REPORT_A, path=self.path)
        self.assertTrue(due)
        self.assertIn("no prior post", reason)

    def test_not_due_when_gap_unchanged_from_last_posted(self):
        cg.record_posted_gap(
            cg.extract_gap_identity(REPORT_A),
            "2026-07-13T12:00:00Z",
            path=self.path,
        )
        due, reason = cg.should_post_gap(REPORT_A, path=self.path)
        self.assertFalse(due)
        self.assertIn("unchanged", reason)

    def test_due_when_gap_differs_from_last_posted(self):
        cg.record_posted_gap(
            cg.extract_gap_identity(REPORT_A),
            "2026-07-13T12:00:00Z",
            path=self.path,
        )
        due, reason = cg.should_post_gap(REPORT_B, path=self.path)
        self.assertTrue(due)
        self.assertIn("differs", reason)

    def test_due_when_same_headline_but_evidence_differs(self):
        # The real, live bug this closes (reproduced against the actual
        # 2026-07-19/2026-07-20 REPORTS/ pair before this fix): the
        # milestone-gap kind renders the identical bolded headline every
        # day it fires, so a bare-headline comparison wrongly reported
        # "unchanged" even though the underlying evidence (commit count,
        # commit hashes) was completely different. Same category headline,
        # different evidence -- must be due, not silently suppressed.
        cg.record_posted_gap(
            cg.extract_gap_identity(REPORT_A),
            "2026-07-13T12:00:00Z",
            path=self.path,
        )
        due, reason = cg.should_post_gap(
            REPORT_A_SAME_HEADLINE_DIFFERENT_EVIDENCE, path=self.path
        )
        self.assertTrue(due)
        self.assertIn("differs", reason)

    def test_never_due_when_report_has_no_parseable_gap(self):
        cg.record_posted_gap("some prior gap", "2026-07-13T12:00:00Z", path=self.path)
        due, reason = cg.should_post_gap(REPORT_EMPTY, path=self.path)
        self.assertFalse(due)
        self.assertIn("no parseable", reason)


if __name__ == "__main__":
    unittest.main()
