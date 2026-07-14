"""Task 27. A fork's genesis must never borrow ours — checked in code, not just claimed in docs."""
import importlib.util
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOTSTRAP = os.path.join(ROOT, "tools", "bootstrap.sh")
DOC = os.path.join(ROOT, "docs", "architecture", "fork-record.md")


def _load_ledger_module(alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(ROOT, "tools", "ledger.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestForkRecordDoctrine(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.target = os.path.join(self.tmpdir.name, "forktown")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_doc_exists_and_states_the_invariant(self):
        self.assertTrue(os.path.exists(DOC))
        with open(DOC) as f:
            text = f.read()
        self.assertIn('GENESIS = "0" * 64', text)

    def test_ledger_genesis_constant_matches_the_docs_stated_invariant(self):
        mod = _load_ledger_module("ledger_origin_check")
        self.assertEqual(mod.GENESIS, "0" * 64)

    def test_forked_ledger_starts_at_its_own_genesis_not_ours(self):
        r = subprocess.run(["bash", BOOTSTRAP, self.target], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

        origin = _load_ledger_module("ledger_origin")
        origin_hashes = {e["hash"] for e in origin._entries()}

        fork = _load_ledger_module("ledger_fork")
        fork.LEDGER = os.path.join(self.target, "records", "ledger.jsonl")
        entry = fork.append("test-god", "genesis-check", "first act in the fork", "2026-07-13T03:00:00+00:00")

        self.assertEqual(entry["seq"], 0)
        self.assertEqual(entry["prev"], fork.GENESIS)
        self.assertEqual(entry["prev"], origin.GENESIS)
        self.assertNotIn(entry["hash"], origin_hashes)
        self.assertTrue(fork.verify())


if __name__ == "__main__":
    unittest.main()
