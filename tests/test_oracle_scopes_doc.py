"""ROADMAP #131. Off-By-One rereads `oracle/SCOPES.md` against the desk
it now describes -- task 130's own discipline, one file over.

Task 93 shipped `commit_comment_cadence.py` with its live call honestly
`**PENDING:**` -- this sandbox could not reach `api.github.com` and no
loaded MCP tool exposed a repo-wide commit-comments read. The very next
scheduled `oracle-cadence.yml` run (2026-07-17T14:28:37Z, unrestricted
egress) sealed it for real: `oracle/commit_comment_snapshots.jsonl` holds
a real reading and `records/ledger.jsonl` holds a matching prediction.
Nobody came back to flip the note from PENDING to RESOLVED -- the exact
shape of drift task 130 found in `docs/oracle-desk.md`, just for this
doc's own comments-family section.

This module cross-checks the corrected doc against the same two live
facts its old PENDING claim depended on, and generalizes the check so the
same drift can't reopen unnoticed in either direction:

1. The stale literal PENDING sentence for commit-comment-cadence is gone.
2. The new RESOLVED paragraph's cited snapshot content and ledger seq are
   read live from `oracle/commit_comment_snapshots.jsonl` and
   `records/ledger.jsonl` -- never a second hardcoded copy -- and both
   actually match what the doc claims.
3. Every section in the doc still marked `**PENDING:**` names a cadence
   whose snapshot file is genuinely absent from disk right now.
4. Every section in the doc marked `**RESOLVED (corrected` names a
   cadence whose snapshot file genuinely exists on disk right now.
"""

import importlib.util
import json
import os
import re
import sys
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DOC_PATH = os.path.join(REPO_ROOT, "oracle", "SCOPES.md")
ORACLE_DIR = os.path.join(REPO_ROOT, "oracle")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ledger_module = _load("_test_oracle_scopes_doc_ledger", os.path.join(REPO_ROOT, "tools", "ledger.py"))

STALE_PENDING_SENTENCE = (
    "the first live call is honestly unsealed as of this writing"
)

COMMIT_COMMENT_SNAPSHOT = os.path.join(ORACLE_DIR, "commit_comment_snapshots.jsonl")


def _read_doc():
    with open(DOC_PATH, encoding="utf-8") as f:
        return f.read()


def _snapshot_path_for(base: str) -> str:
    return os.path.join(ORACLE_DIR, f"{base}_snapshots.jsonl")


def _snapshot_lines(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# Matches "`oracle/<base>_snapshots.jsonl`" anywhere in a paragraph -- the
# doc's own convention for naming a cadence's durable snapshot log, used
# identically by every PENDING and RESOLVED paragraph.
_SNAPSHOT_NAME_RE = re.compile(r"oracle/(\w+)_snapshots\.jsonl")


def _paragraphs_starting_with(doc: str, marker: str) -> list:
    return [p for p in doc.split("\n\n") if p.strip().startswith(marker)]


class CommitCommentResolvedCase(unittest.TestCase):
    def test_stale_pending_sentence_gone(self):
        doc = _read_doc()
        self.assertNotIn(STALE_PENDING_SENTENCE, doc)

    def test_commit_comment_section_now_resolved(self):
        doc = _read_doc()
        idx = doc.index("ROADMAP.md #93: a twenty-fifth cadence")
        section = doc[idx : idx + 2000]
        self.assertIn("**RESOLVED (corrected 2026-07-18, task 131)", section)

    def test_resolved_paragraph_cites_live_snapshot_content(self):
        # Task 133: this used to assert len(live) == 1 -- true the hour task
        # 131 wrote it, false the moment oracle-cadence.yml's daily cron
        # sealed a second reading, exactly the growing-real-file-vs-hardcoded
        # -cardinality mistake task 129 already fixed one file over, in
        # test_report_cadence_check.py's RealReportsCase. The doc's own
        # RESOLVED paragraph cites the FIRST sealed reading (the historic
        # "first live call" moment, ledger seq 287) -- never a claim that it
        # would stay the only one; the doc's own prose says this cadence
        # "will keep sealing on every scheduled run." So the right invariant
        # is "at least one entry exists, and the doc cites the earliest one"
        # -- true today at 2 entries, true tomorrow at 3, true forever.
        doc = _read_doc()
        idx = doc.index("RESOLVED (corrected 2026-07-18, task 131)")
        paragraph = doc[idx : idx + 1000]

        live = _snapshot_lines(COMMIT_COMMENT_SNAPSHOT)
        self.assertGreaterEqual(
            len(live), 1, "expected at least one real sealed commit-comment reading"
        )
        earliest_entry = live[0]

        cited = json.loads(
            re.search(r"holds `(\{.*?\})`", paragraph).group(1)
        )
        self.assertEqual(cited, earliest_entry)

    def test_resolved_paragraph_cites_a_real_ledger_entry(self):
        doc = _read_doc()
        idx = doc.index("RESOLVED (corrected 2026-07-18, task 131)")
        paragraph = doc[idx : idx + 1000]

        cited_seq = int(re.search(r"seq (\d+)", paragraph).group(1))
        entries = ledger_module._entries()
        matches = [e for e in entries if e.get("seq") == cited_seq]
        self.assertEqual(len(matches), 1, f"seq {cited_seq} not found exactly once")

        entry = matches[0]
        self.assertEqual(entry["actor"], "off-by-one")
        self.assertEqual(entry["act"], "predict")
        self.assertIn("commit comment count", entry["detail"])

        self.assertTrue(ledger_module.verify())


class SnapshotCardinalityGrowthSafetyCase(unittest.TestCase):
    """Task 133's regression proof: a snapshot log fed to `_snapshot_lines`
    keeps naming the same "earliest entry" as more real cadence readings
    append after it -- an isolated temp fixture, never the real log, so
    this never depends on how many readings `oracle/commit_comment_snapshots
    .jsonl` genuinely holds today."""

    def _write_jsonl(self, path, entries):
        with open(path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def test_earliest_entry_is_stable_as_the_file_grows(self):
        import tempfile

        entry_0 = {"count": 0, "ts": "2026-07-17T14:28:37+00:00"}
        entry_1 = {"count": 0, "ts": "2026-07-18T14:18:34+00:00"}
        entry_2 = {"count": 1, "ts": "2026-07-19T14:20:00+00:00"}
        entry_3 = {"count": 1, "ts": "2026-07-20T09:00:00+00:00"}

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "commit_comment_snapshots.jsonl")

            # Two lines: the exact real-world shape this task fixed.
            self._write_jsonl(path, [entry_0, entry_1])
            self.assertEqual(_snapshot_lines(path)[0], entry_0)
            self.assertEqual(len(_snapshot_lines(path)), 2)

            # A third and fourth real reading append -- the earliest entry
            # a doc paragraph would cite never moves, only the count grows.
            self._write_jsonl(path, [entry_0, entry_1, entry_2])
            self.assertEqual(_snapshot_lines(path)[0], entry_0)
            self.assertEqual(len(_snapshot_lines(path)), 3)

            self._write_jsonl(path, [entry_0, entry_1, entry_2, entry_3])
            self.assertEqual(_snapshot_lines(path)[0], entry_0)
            self.assertEqual(len(_snapshot_lines(path)), 4)

    def test_old_exactly_one_assertion_would_fail_against_todays_real_file(self):
        # Hand-verification, kept as a live assertion: proves the bug this
        # task fixes was real, not assumed. If oracle-cadence.yml's cron
        # ever gets reset to a single-entry state this would start failing
        # loudly -- exactly the kind of loud, honest failure this task's
        # whole point is to prefer over a silent one.
        live = _snapshot_lines(COMMIT_COMMENT_SNAPSHOT)
        self.assertGreater(
            len(live),
            1,
            "expected today's real commit-comment snapshot log to hold more "
            "than one reading (task 133's whole premise) -- if this fails, "
            "the old exactly-one test would currently pass and this "
            "regression test is not exercising the real bug",
        )


class PendingAndResolvedStayHonestCase(unittest.TestCase):
    """Generalizes the check: whichever cadences the doc marks PENDING or
    RESOLVED right now, their claim about the snapshot file must be true
    -- catches this exact drift reopening on any future cadence, not just
    the one this task fixed."""

    def test_every_pending_section_names_a_genuinely_absent_snapshot(self):
        doc = _read_doc()
        for paragraph in _paragraphs_starting_with(doc, "**PENDING:**"):
            names = _SNAPSHOT_NAME_RE.findall(paragraph)
            self.assertTrue(names, f"PENDING paragraph names no snapshot file: {paragraph[:120]!r}")
            for base in names:
                path = _snapshot_path_for(base)
                self.assertFalse(
                    os.path.exists(path),
                    f"doc claims {base}_snapshots.jsonl is still PENDING but it exists on disk",
                )

    def test_every_resolved_section_names_a_genuinely_present_snapshot(self):
        doc = _read_doc()
        for paragraph in _paragraphs_starting_with(doc, "**RESOLVED (corrected"):
            names = _SNAPSHOT_NAME_RE.findall(paragraph)
            self.assertTrue(names, f"RESOLVED paragraph names no snapshot file: {paragraph[:120]!r}")
            for base in names:
                path = _snapshot_path_for(base)
                self.assertTrue(
                    os.path.exists(path),
                    f"doc claims {base}_snapshots.jsonl is RESOLVED (sealed) but it is absent on disk",
                )

    def test_commit_comment_cadence_is_no_longer_pending(self):
        doc = _read_doc()
        pending_paragraphs = _paragraphs_starting_with(doc, "**PENDING:**")
        for paragraph in pending_paragraphs:
            self.assertNotIn("commit_comment_snapshots.jsonl", paragraph)


if __name__ == "__main__":
    unittest.main()
