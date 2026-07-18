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
        idx = doc.index("ROADMAP.md #93: a twenty-sixth cadence")
        section = doc[idx : idx + 2000]
        self.assertIn("**RESOLVED (corrected 2026-07-18, task 131)", section)

    def test_resolved_paragraph_cites_live_snapshot_content(self):
        doc = _read_doc()
        idx = doc.index("RESOLVED (corrected 2026-07-18, task 131)")
        paragraph = doc[idx : idx + 1000]

        live = _snapshot_lines(COMMIT_COMMENT_SNAPSHOT)
        self.assertEqual(
            len(live), 1, "expected exactly one real sealed commit-comment reading"
        )
        live_entry = live[0]

        cited = json.loads(
            re.search(r"holds `(\{.*?\})`", paragraph).group(1)
        )
        self.assertEqual(cited, live_entry)

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
