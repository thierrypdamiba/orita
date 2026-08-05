"""Task 540. Proves tools/jsonl_read.py's read_jsonl_entries() behaves
correctly, and that the fourteen sibling checks it was extracted from
(arcade_app_watch, change_gate, child_work_check, ci_watch,
consent_grant_log, gateway_toolset_check, github_stars_check, ledger,
scribe_growth_check, square_check, voice_window_check, word_watch,
x_outage_tracker, x_post_queue) each now delegate their own `_entries` to
it -- not a reinlined copy of the read-and-mark-malformed logic.
`tools/jsonl_append.py` (task 510) already got this same treatment for
the WRITE half of these same fourteen logs; the READ half carried the
identical duplicate-function disease, invisible to
`tools/duplicate_regex_check.py` (which only ever inspects
`re.compile(...)` call sites) until an AST-hash sweep with string/number
constants normalized before hashing (the malformed-non-object branch
carried three cosmetically different message phrasings across the
fourteen copies) caught it live this hour.

A bare `assertIs` on the function object (the `_append` pattern) doesn't
fit here: twelve of the fourteen wrappers carry their own default
`path=<module's own LOG/QUEUE constant>`, so each is a distinct function
object by necessity -- the same "wrapper-with-its-own-default" shape
task 523's `LoadSnapshotsDelegatesCase` proved for
`time_utils.load_snapshots`. Patch-and-observe is the identity guarantee's
equivalent for that shape.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


jr = _load("jsonl_read", os.path.join(TOOLS, "jsonl_read.py"))

# Every sibling whose own _entries(path=<its own default>) needs no other
# setup beyond loading the file directly.
SIMPLE_SIBLINGS = [
    "arcade_app_watch",
    "change_gate",
    "child_work_check",
    "ci_watch",
    "gateway_toolset_check",
    "github_stars_check",
    "scribe_growth_check",
    "square_check",
    "voice_window_check",
    "word_watch",
    "x_outage_tracker",
    "x_post_queue",
]


class DelegatesToSharedReaderCase(unittest.TestCase):
    """Every sibling's `_entries` must genuinely call through to
    jsonl_read.read_jsonl_entries, not carry a reinlined copy."""

    def test_every_simple_sibling_delegates(self):
        self.assertEqual(
            len(SIMPLE_SIBLINGS), 12, "sibling list drifted from the live sweep"
        )
        for name in SIMPLE_SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(f"_test_jr_{name}", os.path.join(TOOLS, f"{name}.py"))
                self.assertIs(
                    mod.jsonl_read,
                    jr,
                    f"{name} did not resolve the shared tools/jsonl_read.py module",
                )
                sentinel = [{"marker": name}]
                with mock.patch.object(
                    mod.jsonl_read, "read_jsonl_entries", return_value=sentinel
                ) as patched:
                    # child_work_check._entries requires a path argument
                    # (no default); every other sibling has its own.
                    result = (
                        mod._entries(getattr(mod, "LOG", None))
                        if name == "child_work_check"
                        else mod._entries()
                    )
                patched.assert_called_once()
                self.assertEqual(result, sentinel)

    def test_consent_grant_log_delegates(self):
        mod = _load(
            "_test_jr_consent_grant_log",
            os.path.join(TOOLS, "consent_grant_log.py"),
        )
        self.assertIs(mod.jsonl_read, jr)
        sentinel = [{"marker": "consent"}]
        with mock.patch.object(
            mod.jsonl_read, "read_jsonl_entries", return_value=sentinel
        ) as patched:
            result = mod._entries()
        patched.assert_called_once()
        self.assertEqual(result, sentinel)

    def test_ledger_delegates_with_its_own_ledger_path(self):
        mod = _load("_test_jr_ledger", os.path.join(TOOLS, "ledger.py"))
        self.assertIs(mod.jsonl_read, jr)
        sentinel = [{"marker": "ledger"}]
        with mock.patch.object(
            mod.jsonl_read, "read_jsonl_entries", return_value=sentinel
        ) as patched:
            result = mod._entries()
        patched.assert_called_once_with(mod.LEDGER)
        self.assertEqual(result, sentinel)


class ReadJsonlEntriesCase(unittest.TestCase):
    def test_missing_file_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(jr.read_jsonl_entries(os.path.join(d, "nope.jsonl")), [])

    def test_reads_real_entries_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.jsonl")
            with open(path, "w") as f:
                f.write(json.dumps({"a": 1}) + "\n")
                f.write(json.dumps({"a": 2}) + "\n")
            self.assertEqual(jr.read_jsonl_entries(path), [{"a": 1}, {"a": 2}])

    def test_skips_blank_lines(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.jsonl")
            with open(path, "w") as f:
                f.write(json.dumps({"a": 1}) + "\n\n")
            self.assertEqual(jr.read_jsonl_entries(path), [{"a": 1}])

    def test_malformed_json_marked_not_raised(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.jsonl")
            with open(path, "w") as f:
                f.write("not json at all\n")
            entries = jr.read_jsonl_entries(path)
            self.assertEqual(len(entries), 1)
            self.assertTrue(entries[0]["_malformed"])
            self.assertIn("_error", entries[0])

    def test_non_object_json_marked_not_raised(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.jsonl")
            with open(path, "w") as f:
                f.write(json.dumps([1, 2, 3]) + "\n")
            entries = jr.read_jsonl_entries(path)
            self.assertEqual(len(entries), 1)
            self.assertTrue(entries[0]["_malformed"])
            self.assertIn("not a JSON object", entries[0]["_error"])

    def test_non_ascii_content_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    json.dumps({"name": "Kwaku Ananse — spider"}, ensure_ascii=False)
                    + "\n"
                )
            entries = jr.read_jsonl_entries(path)
            self.assertEqual(entries, [{"name": "Kwaku Ananse — spider"}])


if __name__ == "__main__":
    unittest.main()
