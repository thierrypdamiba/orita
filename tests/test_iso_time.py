"""Task 509. Proves tools/iso_time.py's parse_iso_utc() behaves correctly,
and that the three sibling checks it was extracted from (cron_health,
voice_window_check, x_outage_tracker) each now hold the identical function
object at their own `_parse` name -- not just identical source text. An
Explore sweep this hour found all three carrying a byte-identical one-line
`Z`-suffixed ISO parser, invisible to tools/duplicate_regex_check.py (which
only scans `re.compile()` call sites, never duplicated function bodies) --
the exact same shape task 508 already closed one file over
(tools/metrics_reader.py, six duplicated readers). Identity, not equality,
is the guarantee that matters: two independently-maintained copies with the
same source today can still drift apart on the next edit to just one of
them; an `is` check on the same function object makes that class of drift
structurally impossible going forward.
"""
import importlib.util
import os
import sys
import unittest
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


it = _load("iso_time", os.path.join(TOOLS, "iso_time.py"))

SIBLINGS = [
    "cron_health",
    "voice_window_check",
    "x_outage_tracker",
]


class IdentityAcrossSiblingsCase(unittest.TestCase):
    """Every sibling's `_parse` must BE iso_time's parse_iso_utc (same
    function object), not merely equal source -- the only guarantee that
    makes the three-independent-copies drift this task closed structurally
    unable to recur one copy at a time."""

    def test_every_sibling_shares_the_one_parser_object(self):
        for name in SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
                self.assertIs(
                    mod._parse,
                    it.parse_iso_utc,
                    f"{name}._parse is a separate copy again, not the "
                    "shared tools/iso_time.py function",
                )


class ParseIsoUtcCase(unittest.TestCase):
    def test_z_suffixed_parses_as_utc(self):
        dt = it.parse_iso_utc("2026-08-03T16:00:00Z")
        self.assertEqual(dt, datetime(2026, 8, 3, 16, 0, 0, tzinfo=timezone.utc))

    def test_explicit_offset_normalized_to_utc(self):
        dt = it.parse_iso_utc("2026-08-03T12:00:00-04:00")
        self.assertEqual(dt, datetime(2026, 8, 3, 16, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(dt.utcoffset().total_seconds(), 0)

    def test_already_utc_offset_roundtrips(self):
        dt = it.parse_iso_utc("2026-08-03T16:00:00+00:00")
        self.assertEqual(dt, datetime(2026, 8, 3, 16, 0, 0, tzinfo=timezone.utc))

    def test_result_is_timezone_aware(self):
        dt = it.parse_iso_utc("2026-08-03T16:00:00Z")
        self.assertIsNotNone(dt.tzinfo)


if __name__ == "__main__":
    unittest.main()
