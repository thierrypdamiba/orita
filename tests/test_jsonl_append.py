"""Task 510. Proves tools/jsonl_append.py's append_jsonl() behaves
correctly, and that the ten sibling checks it was extracted from
(arcade_app_watch, change_gate, ci_watch, gateway_toolset_check,
github_stars_check, scribe_growth_check, square_check, word_watch,
x_outage_tracker, x_post_queue) each now hold the identical function
object at their own `_append` name -- not just identical source text. An
Explore sweep this hour found all ten carrying a byte-identical
append-one-JSON-line helper, invisible to tools/duplicate_regex_check.py
(which only scans `re.compile()` call sites, never duplicated function
bodies) -- the same shape tasks 508 (tools/metrics_reader.py, six
duplicated readers) and 509 (tools/iso_time.py, three duplicated parsers)
already closed elsewhere in this directory. Identity, not equality, is
the guarantee that matters: two independently-maintained copies with the
same source today can still drift apart on the next edit to just one of
them; an `is` check on the same function object makes that class of
drift structurally impossible going forward.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ja = _load("jsonl_append", os.path.join(TOOLS, "jsonl_append.py"))

SIBLINGS = [
    "arcade_app_watch",
    "change_gate",
    "ci_watch",
    "gateway_toolset_check",
    "github_stars_check",
    "scribe_growth_check",
    "square_check",
    "word_watch",
    "x_outage_tracker",
    "x_post_queue",
]


class IdentityAcrossSiblingsCase(unittest.TestCase):
    """Every sibling's `_append` must BE jsonl_append's append_jsonl (same
    function object), not merely equal source -- the only guarantee that
    makes the ten-independent-copies drift this task closed structurally
    unable to recur one copy at a time."""

    def test_every_sibling_shares_the_one_append_object(self):
        for name in SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
                self.assertIs(
                    mod._append,
                    ja.append_jsonl,
                    f"{name}._append is a separate copy again, not the "
                    "shared tools/jsonl_append.py function",
                )


class AppendJsonlCase(unittest.TestCase):
    def test_appends_one_json_line(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.jsonl")
            ja.append_jsonl({"a": 1}, path)
            ja.append_jsonl({"a": 2}, path)
            with open(path) as f:
                lines = f.read().splitlines()
            self.assertEqual([json.loads(line) for line in lines], [{"a": 1}, {"a": 2}])

    def test_creates_missing_parent_directory(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "nested", "deeper", "log.jsonl")
            ja.append_jsonl({"a": 1}, path)
            self.assertTrue(os.path.exists(path))

    def test_non_ascii_content_not_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.jsonl")
            ja.append_jsonl({"name": "Kwaku Ananse — spider"}, path)
            with open(path, encoding="utf-8") as f:
                line = f.readline()
            self.assertIn("Kwaku Ananse — spider", line)


if __name__ == "__main__":
    unittest.main()
