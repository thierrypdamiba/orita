"""Task 66. Direct test coverage for tools/ledger.py -- the town's
append-only hash chain, previously exercised only indirectly through
tests/test_ritual_check.py and tests/test_fork_record.py despite being
the single most safety-critical file in the repo (121 real entries
sealed against it with zero direct unit test of its own).

Also proves the new CLI guard (parse_append_args) rejects the exact
malformed-invocation shape that sealed records/ledger.jsonl seq 118-119:
flag syntax (`--actor nisaba --kind roadmap ...`) run against a CLI that
only ever reads bare positionals. append() itself never validated, so
it wrote the garbage permanently; the guard is the fix.
"""
import importlib.util
import json
import os
import shutil
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


class LedgerCoreCase(unittest.TestCase):
    """append/verify/hash-chaining/tamper-detection, exercised directly."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.mod = _load(f"_test_ledger_{id(self)}", os.path.join(ROOT, "tools", "ledger.py"))
        self.mod.LEDGER = os.path.join(self.tmpdir, "ledger.jsonl")

    def test_empty_ledger_has_no_entries(self):
        self.assertEqual(self.mod._entries(), [])

    def test_first_append_chains_from_genesis(self):
        e = self.mod.append("nisaba", "test", "first", "2026-07-14T00:00:00+00:00")
        self.assertEqual(e["seq"], 0)
        self.assertEqual(e["prev"], self.mod.GENESIS)
        self.assertIn("hash", e)

    def test_second_append_chains_from_first_hash(self):
        first = self.mod.append("nisaba", "test", "one", "2026-07-14T00:00:00+00:00")
        second = self.mod.append("nisaba", "test", "two", "2026-07-14T00:01:00+00:00")
        self.assertEqual(second["seq"], 1)
        self.assertEqual(second["prev"], first["hash"])
        self.assertNotEqual(first["hash"], second["hash"])

    def test_append_is_durable_across_module_instances(self):
        self.mod.append("nisaba", "test", "one", "2026-07-14T00:00:00+00:00")
        reloaded = _load(f"_test_ledger_reload_{id(self)}", os.path.join(ROOT, "tools", "ledger.py"))
        reloaded.LEDGER = self.mod.LEDGER
        self.assertEqual(len(reloaded._entries()), 1)

    def test_verify_true_on_intact_chain(self):
        self.mod.append("nisaba", "test", "one", "2026-07-14T00:00:00+00:00")
        self.mod.append("nisaba", "test", "two", "2026-07-14T00:01:00+00:00")
        self.assertTrue(self.mod.verify())

    def test_verify_true_on_empty_chain(self):
        self.assertTrue(self.mod.verify())

    def test_verify_false_on_tampered_detail(self):
        self.mod.append("nisaba", "test", "one", "2026-07-14T00:00:00+00:00")
        self.mod.append("nisaba", "test", "two", "2026-07-14T00:01:00+00:00")
        with open(self.mod.LEDGER) as f:
            lines = f.readlines()
        tampered = json.loads(lines[0])
        tampered["detail"] = "tampered, not what was sealed"
        lines[0] = json.dumps(tampered, ensure_ascii=False) + "\n"
        with open(self.mod.LEDGER, "w") as f:
            f.writelines(lines)
        self.assertFalse(self.mod.verify())

    def test_verify_false_on_broken_prev_link(self):
        self.mod.append("nisaba", "test", "one", "2026-07-14T00:00:00+00:00")
        self.mod.append("nisaba", "test", "two", "2026-07-14T00:01:00+00:00")
        with open(self.mod.LEDGER) as f:
            lines = f.readlines()
        tampered = json.loads(lines[1])
        tampered["prev"] = "0" * 64
        lines[1] = json.dumps(tampered, ensure_ascii=False) + "\n"
        with open(self.mod.LEDGER, "w") as f:
            f.writelines(lines)
        self.assertFalse(self.mod.verify())


class ParseAppendArgsCase(unittest.TestCase):
    """The CLI guard: rejects flag-shaped actor/act, mirroring the real
    seq 118-119 incident, without overcorrecting into rejecting real
    hyphenated content (actor names, detail text)."""

    def setUp(self):
        self.mod = _load(f"_test_ledger_cli_{id(self)}", os.path.join(ROOT, "tools", "ledger.py"))

    def test_normal_call_parses_cleanly(self):
        actor, act, detail = self.mod.parse_append_args(
            ["ogun", "fix", "cleared", "the", "path"]
        )
        self.assertEqual((actor, act, detail), ("ogun", "fix", "cleared the path"))

    def test_hyphenated_actor_name_is_not_a_flag(self):
        # off-by-one is a real actor name; a leading hyphen is the trigger,
        # not any hyphen anywhere in the string.
        actor, act, detail = self.mod.parse_append_args(
            ["off-by-one", "seal", "workflow-cadence sealed"]
        )
        self.assertEqual(actor, "off-by-one")
        self.assertEqual(act, "seal")

    def test_detail_containing_hyphens_is_untouched(self):
        actor, act, detail = self.mod.parse_append_args(
            ["nisaba", "note", "a well-formed, hyphen-heavy sentence - like this one"]
        )
        self.assertIn("well-formed", detail)

    def test_too_few_args_raises(self):
        with self.assertRaises(self.mod.LedgerCLIError):
            self.mod.parse_append_args(["nisaba"])

    def test_no_args_raises(self):
        with self.assertRaises(self.mod.LedgerCLIError):
            self.mod.parse_append_args([])

    def test_flag_shaped_actor_raises_the_real_incident_shape(self):
        # The exact shape that sealed seq 118 malformed.
        with self.assertRaises(self.mod.LedgerCLIError) as ctx:
            self.mod.parse_append_args(
                ["--actor", "nisaba", "--kind", "roadmap", "--detail", "task 65 -> WIP"]
            )
        self.assertIn("looks like a flag", str(ctx.exception))
        self.assertIn("seq 118-119", str(ctx.exception))

    def test_flag_shaped_act_raises(self):
        with self.assertRaises(self.mod.LedgerCLIError):
            self.mod.parse_append_args(["ogun", "--kind", "fix", "cleared it"])

    def test_equals_style_flag_raises(self):
        with self.assertRaises(self.mod.LedgerCLIError):
            self.mod.parse_append_args(["--actor=foo", "--act=bar", "--detail=baz"])


class LedgerCLIDispatchCase(unittest.TestCase):
    """End-to-end through the real main() dispatch (the same function
    `python3 tools/ledger.py ...` invokes), proving a rejected call
    writes nothing and returns non-zero, and the ledger file is
    byte-identical before and after."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.mod = _load(f"_test_ledger_cli_dispatch_{id(self)}", os.path.join(ROOT, "tools", "ledger.py"))
        self.mod.LEDGER = os.path.join(self.tmpdir, "ledger.jsonl")

    def test_valid_append_writes_one_line(self):
        rc = self.mod.main(["append", "nisaba", "test", "a", "real", "entry"])
        self.assertEqual(rc, 0)
        with open(self.mod.LEDGER) as f:
            self.assertEqual(len(f.readlines()), 1)

    def test_malformed_flag_call_exits_nonzero_and_writes_nothing(self):
        # Real incident shape (seq 118): append --actor nisaba --kind roadmap --detail "..."
        before_exists = os.path.exists(self.mod.LEDGER)
        rc = self.mod.main(
            ["append", "--actor", "nisaba", "--kind", "roadmap", "--detail", "task 65 -> WIP"]
        )
        self.assertNotEqual(rc, 0)
        # Nothing was ever created -- not an empty file, not a partial write.
        self.assertEqual(os.path.exists(self.mod.LEDGER), before_exists)

    def test_malformed_call_after_a_valid_entry_leaves_it_byte_identical(self):
        self.mod.main(["append", "ogun", "fix", "cleared the path"])
        with open(self.mod.LEDGER) as f:
            before = f.read()
        rc = self.mod.main(["append", "--actor", "nisaba", "--kind", "roadmap", "bad call"])
        self.assertNotEqual(rc, 0)
        with open(self.mod.LEDGER) as f:
            after = f.read()
        self.assertEqual(before, after)

    def test_verify_dispatch_returns_zero_on_intact_chain(self):
        self.mod.main(["append", "nisaba", "test", "one"])
        self.assertEqual(self.mod.main(["verify"]), 0)

    def test_unknown_command_returns_nonzero(self):
        self.assertEqual(self.mod.main(["not-a-real-command"]), 1)


if __name__ == "__main__":
    unittest.main()
