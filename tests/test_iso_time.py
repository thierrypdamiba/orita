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
import time
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

    def test_naive_timestamp_assumed_utc_not_machine_local_time(self):
        """A timestamp with no `Z` and no explicit offset (a hand-typed
        value missing the `Z` this repo's own convention always appends)
        must parse to the identical instant regardless of the machine's
        own local timezone -- `datetime.astimezone()` called directly on a
        naive `datetime` presumes it already represents *local* system
        time, which would silently make the same input string parse to a
        different real instant purely depending on which machine ran it.
        Pinned against `oracle_engine.time_utils.parse_ts` (the sibling
        parser for the identical class of input), which already holds the
        naive-means-UTC line explicitly.
        """
        original_tz = os.environ.get("TZ")
        try:
            os.environ["TZ"] = "America/Los_Angeles"
            time.tzset()
            dt = it.parse_iso_utc("2026-07-14T01:15:00")
        finally:
            if original_tz is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = original_tz
            time.tzset()
        self.assertEqual(dt, datetime(2026, 7, 14, 1, 15, 0, tzinfo=timezone.utc))

    def test_schedule_status_verdict_independent_of_machine_timezone(self):
        """The same real inputs to `cron_health.schedule_status` must
        yield the same verdict no matter the machine's own local
        timezone -- before the fix, a naive `now` (no `Z`) shifted by the
        machine's local UTC offset, which could move `now` across the
        cron's own fire hour and flip `on_time` into `pending`/`overdue`
        purely as a function of which timezone happened to be set."""
        ch = _load("cron_health", os.path.join(TOOLS, "cron_health.py"))
        original_tz = os.environ.get("TZ")
        results = {}
        try:
            for tz in ("UTC", "America/Los_Angeles"):
                os.environ["TZ"] = tz
                time.tzset()
                results[tz] = ch.schedule_status(
                    "0 13 * * *", "2026-07-13T13:05:00Z", "2026-07-14T08:00:00"
                )
        finally:
            if original_tz is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = original_tz
            time.tzset()
        self.assertEqual(results["UTC"]["status"], "on_time")
        self.assertEqual(results["UTC"], results["America/Los_Angeles"])


if __name__ == "__main__":
    unittest.main()
