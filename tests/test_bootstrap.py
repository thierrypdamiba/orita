"""Task 24. Off-By-One counted every file this script writes. Twice."""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOTSTRAP = os.path.join(ROOT, "tools", "bootstrap.sh")


def _load_ledger_module():
    spec = importlib.util.spec_from_file_location("ledger", os.path.join(ROOT, "tools", "ledger.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestBootstrap(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.target = os.path.join(self.tmpdir.name, "newtown")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, target):
        return subprocess.run(["bash", BOOTSTRAP, target], capture_output=True, text=True)

    def test_scaffolds_a_content_free_skeleton(self):
        r = self._run(self.target)
        self.assertEqual(r.returncode, 0, r.stderr)
        for rel in ("houses", "records/pre-founding", "records/ledger.jsonl",
                    "ROADMAP.md", "BUILDLOG.md", "STRATEGY.md"):
            self.assertTrue(os.path.exists(os.path.join(self.target, rel)), rel)

    def test_houses_tree_has_no_god_dirs_no_orita_lore_copied(self):
        self._run(self.target)
        houses = os.path.join(self.target, "houses")
        entries = os.listdir(houses)
        self.assertEqual(entries, ["README.md"])

    def test_ledger_starts_at_zero_entries(self):
        self._run(self.target)
        ledger_path = os.path.join(self.target, "records", "ledger.jsonl")
        self.assertEqual(os.path.getsize(ledger_path), 0)

    def test_casting_record_is_a_blank_template_not_our_pantheon(self):
        self._run(self.target)
        with open(os.path.join(self.target, "records", "pre-founding", "casting-record.json")) as f:
            record = json.load(f)
        self.assertEqual(record["final"]["pantheon"], [])

    def test_bootstrapped_ledger_chains_from_its_own_genesis(self):
        """A fork's first entry commits to GENESIS, not to seq 413 of ours."""
        self._run(self.target)
        mod = _load_ledger_module()
        mod.LEDGER = os.path.join(self.target, "records", "ledger.jsonl")
        entry = mod.append("test-god", "genesis-check", "first act in the fork", "2026-07-12T23:00:00+00:00")
        self.assertEqual(entry["seq"], 0)
        self.assertEqual(entry["prev"], mod.GENESIS)
        self.assertTrue(mod.verify())

    def test_refuses_to_bootstrap_into_an_existing_path(self):
        self._run(self.target)
        r = self._run(self.target)
        self.assertNotEqual(r.returncode, 0)

    def test_this_repos_own_ledger_is_never_touched(self):
        our_ledger = os.path.join(ROOT, "records", "ledger.jsonl")
        with open(our_ledger) as f:
            before = f.read()
        self._run(self.target)
        with open(our_ledger) as f:
            after = f.read()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
