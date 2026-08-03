"""Task 508. Proves tools/metrics_reader.py's last_metrics_entry() behaves
correctly, and that the six sibling checks it was extracted from
(connected_users_check, gap_true_positive_check, github_stars_check,
report_shipped_check, tasks_shipped_check, toolkits_in_use_check) each
now hold the identical function object at their own `_last_metrics_entry`
name -- not just identical source text. An Explore sweep this hour found
all six carrying a byte-identical copy of this reader, invisible to
tools/duplicate_regex_check.py (which only scans `re.compile()` call
sites, never duplicated function bodies). Identity, not equality, is the
guarantee that matters: two independently-maintained copies with the
same source today can still drift apart on the next edit to just one of
them (as already happened once, tasks 306/328 fixing one copy without
touching the other five); an `is` check on the same function object
makes that class of drift structurally impossible going forward.
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


mr = _load("metrics_reader", os.path.join(TOOLS, "metrics_reader.py"))

SIBLINGS = [
    "connected_users_check",
    "gap_true_positive_check",
    "github_stars_check",
    "report_shipped_check",
    "tasks_shipped_check",
    "toolkits_in_use_check",
]


class IdentityAcrossSiblingsCase(unittest.TestCase):
    """Every sibling's `_last_metrics_entry` must BE metrics_reader's
    last_metrics_entry (same function object), not merely equal source --
    the only guarantee that makes the six-independent-copies drift this
    task closed structurally unable to recur one copy at a time."""

    def test_every_sibling_shares_the_one_reader_object(self):
        for name in SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
                self.assertIs(
                    mod._last_metrics_entry,
                    mr.last_metrics_entry,
                    f"{name}._last_metrics_entry is a separate copy again, "
                    "not the shared tools/metrics_reader.py function",
                )


class LastMetricsEntryCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def _write(self, lines):
        with open(self.path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

    def test_missing_file_returns_none(self):
        self.assertIsNone(mr.last_metrics_entry(self.path))

    def test_returns_the_last_well_formed_object(self):
        self._write([
            json.dumps({"date": "2026-07-01", "n": 1}),
            json.dumps({"date": "2026-07-02", "n": 2}),
        ])
        self.assertEqual(mr.last_metrics_entry(self.path), {"date": "2026-07-02", "n": 2})

    def test_skips_malformed_trailing_line(self):
        self._write([
            json.dumps({"date": "2026-07-01", "n": 1}),
            "{not valid json",
        ])
        self.assertEqual(mr.last_metrics_entry(self.path), {"date": "2026-07-01", "n": 1})

    def test_skips_non_dict_trailing_line(self):
        self._write([
            json.dumps({"date": "2026-07-01", "n": 1}),
            json.dumps(42),
        ])
        self.assertEqual(mr.last_metrics_entry(self.path), {"date": "2026-07-01", "n": 1})

    def test_all_malformed_or_non_dict_returns_none(self):
        self._write(["{bad", json.dumps(None), json.dumps([1, 2])])
        self.assertIsNone(mr.last_metrics_entry(self.path))


if __name__ == "__main__":
    unittest.main()
