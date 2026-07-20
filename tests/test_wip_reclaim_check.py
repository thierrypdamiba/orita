"""Task 123. Proves tools/wip_reclaim_check.py finds a stale WIP row, stays
clean on a fresh one, flags a WIP row with no matching open-timestamp as
`unknown` rather than silently passing it, and -- the real point -- confirms
the live, current ROADMAP.md holds zero currently-open WIP rows today.
"""
import importlib.util
import os
import sys
import unittest
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


wrc = _load("wip_reclaim_check", os.path.join(ROOT, "tools", "wip_reclaim_check.py"))


def _now(iso):
    return datetime.fromisoformat(iso).astimezone(timezone.utc)


class TableParsingCase(unittest.TestCase):
    def test_parses_number_status_owner(self):
        text = "| 1 | DONE | nisaba | do a thing | it is done |\n"
        rows = wrc.parse_table_rows(text)
        self.assertEqual(rows, [{"number": 1, "status": "DONE", "owner": "nisaba"}])

    def test_non_standard_status_text_still_parses(self):
        text = "| 19 | DONE-MACHINERY · long prose | kwaku-ananse | x | y |\n"
        rows = wrc.parse_table_rows(text)
        self.assertEqual(rows[0]["number"], 19)
        self.assertTrue(rows[0]["status"].startswith("DONE-MACHINERY"))

    def test_wip_row_parses_exactly(self):
        text = "| 5 | WIP | off-by-one | count something | a count exists |\n"
        rows = wrc.parse_table_rows(text)
        self.assertEqual(rows[0]["status"], "WIP")


class OpenTimeParsingCase(unittest.TestCase):
    def test_finds_open_timestamp_for_marked_task(self):
        text = "*2026-07-18 02:0x UTC, off-by-one: doing stuff. Task 121 → WIP.*\n"
        opens = wrc.parse_wip_open_times(text)
        self.assertEqual(opens[121], "2026-07-18T02:00:00+00:00")

    def test_ascii_arrow_also_matches(self):
        text = "*2026-07-18 03:1x UTC, nisaba: stuff. Task 55 -> WIP.*\n"
        opens = wrc.parse_wip_open_times(text)
        self.assertEqual(opens[55], "2026-07-18T03:10:00+00:00")

    def test_later_mention_wins_over_earlier_one(self):
        text = (
            "*2026-07-18 01:0x UTC, nyx: Task 9 → WIP.*\n"
            "*2026-07-18 05:0x UTC, nyx: reopened it. Task 9 → WIP.*\n"
        )
        opens = wrc.parse_wip_open_times(text)
        self.assertEqual(opens[9], "2026-07-18T05:00:00+00:00")

    def test_task_never_mentioned_is_absent(self):
        text = "*2026-07-18 02:0x UTC, off-by-one: unrelated prose.*\n"
        opens = wrc.parse_wip_open_times(text)
        self.assertNotIn(121, opens)

    def test_explicit_marker_convention_is_found_with_no_interlude_present(self):
        # The post-task-170 live ROADMAP.md format never writes the legacy
        # interlude preamble at all -- this is the convention task 182 added
        # so a WIP row's open time is still recoverable in that format.
        text = (
            "| 182 | WIP | nisaba | fix the thing | it is fixed |\n\n"
            "<!-- wip-opened: 182 2026-07-20T18:30:00+00:00 -->\n"
        )
        opens = wrc.parse_wip_open_times(text)
        self.assertEqual(opens[182], "2026-07-20T18:30:00+00:00")

    def test_explicit_marker_z_suffix_normalizes_to_utc_offset(self):
        text = "<!-- wip-opened: 55 2026-07-20T18:30:00Z -->\n"
        opens = wrc.parse_wip_open_times(text)
        self.assertEqual(opens[55], "2026-07-20T18:30:00+00:00")

    def test_explicit_marker_overrides_a_legacy_interlude_for_the_same_task(self):
        text = (
            "*2026-07-18 01:0x UTC, nyx: Task 9 → WIP.*\n"
            "<!-- wip-opened: 9 2026-07-18T04:45:00+00:00 -->\n"
        )
        opens = wrc.parse_wip_open_times(text)
        self.assertEqual(opens[9], "2026-07-18T04:45:00+00:00")


class FindStaleCase(unittest.TestCase):
    def _text(self, opened_hour="02:0x"):
        return (
            f"*2026-07-18 {opened_hour} UTC, off-by-one: doing the thing. Task 5 → WIP.*\n"
            "| 5 | WIP | off-by-one | do the thing | it is done |\n"
        )

    def test_wip_opened_over_two_hours_ago_is_stale(self):
        result = wrc.find_stale(text=self._text("02:0x"), now=_now("2026-07-18T05:00:00+00:00"))
        self.assertFalse(result["clean"])
        self.assertEqual(len(result["stale"]), 1)
        self.assertEqual(result["stale"][0]["number"], 5)
        self.assertGreaterEqual(result["stale"][0]["elapsed_hours"], 2.0)

    def test_wip_opened_under_two_hours_ago_is_fresh(self):
        result = wrc.find_stale(text=self._text("04:0x"), now=_now("2026-07-18T05:00:00+00:00"))
        self.assertTrue(result["clean"])
        self.assertEqual(len(result["fresh"]), 1)
        self.assertEqual(result["stale"], [])

    def test_wip_row_with_no_matching_interlude_is_unknown_not_silently_clean(self):
        text = "| 5 | WIP | off-by-one | do the thing | it is done |\n"
        result = wrc.find_stale(text=text, now=_now("2026-07-18T05:00:00+00:00"))
        self.assertFalse(result["clean"])
        self.assertEqual(len(result["unknown"]), 1)
        self.assertEqual(result["stale"], [])

    def test_no_wip_rows_at_all_is_clean_with_zero_open_count(self):
        text = "| 5 | DONE | off-by-one | do the thing | it is done |\n"
        result = wrc.find_stale(text=text, now=_now("2026-07-18T05:00:00+00:00"))
        self.assertTrue(result["clean"])
        self.assertEqual(result["open_count"], 0)

    def test_threshold_is_exactly_two_hours_by_default(self):
        self.assertEqual(wrc.RECLAIM_THRESHOLD_HOURS, 2.0)

    def test_exact_threshold_boundary_counts_as_stale(self):
        result = wrc.find_stale(text=self._text("03:0x"), now=_now("2026-07-18T05:00:00+00:00"))
        self.assertEqual(result["stale"][0]["elapsed_hours"], 2.0)
        self.assertFalse(result["clean"])

    def _post_170_text(self, opened="2026-07-20T18:30:00+00:00"):
        # Shaped like the LIVE ROADMAP.md format since task 170: a single
        # per-task table with no legacy interlude preamble line at all.
        return (
            "## Extending the queue past 181 (this hour)\n\n"
            "| # | status | owner | task | done when |\n"
            "|--:|:--|:--|:--|:--|\n"
            "| 182 | WIP | nisaba | fix the thing | it is fixed |\n\n"
            f"<!-- wip-opened: 182 {opened} -->\n"
        )

    def test_post_170_format_wip_row_under_two_hours_is_fresh_not_unknown(self):
        # Task 182's own regression pin: before the fix, a WIP row in the
        # CURRENT (post-170) file shape always fell through to `unknown`
        # ("escalate now"), no matter how fresh it actually was, because
        # parse_wip_open_times found no legacy interlude to key off of.
        result = wrc.find_stale(text=self._post_170_text(), now=_now("2026-07-20T18:31:00+00:00"))
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["unknown"], [], result)
        self.assertEqual(len(result["fresh"]), 1)

    def test_post_170_format_wip_row_over_two_hours_is_stale_not_unknown(self):
        result = wrc.find_stale(text=self._post_170_text(), now=_now("2026-07-20T20:31:00+00:00"))
        self.assertFalse(result["clean"])
        self.assertEqual(result["unknown"], [], result)
        self.assertEqual(len(result["stale"]), 1)
        self.assertEqual(result["stale"][0]["number"], 182)

    def test_post_170_format_wip_row_with_no_marker_at_all_is_still_unknown(self):
        # No regression on the existing safety net: a WIP row that names
        # NEITHER convention must still escalate as unknown, not silently
        # pass.
        text = (
            "| 182 | WIP | nisaba | fix the thing | it is fixed |\n\n"
        )
        result = wrc.find_stale(text=text, now=_now("2026-07-20T18:31:00+00:00"))
        self.assertFalse(result["clean"])
        self.assertEqual(len(result["unknown"]), 1)


class FormatResultCase(unittest.TestCase):
    def test_zero_open_reads_clean_no_task(self):
        line = wrc.format_result({"open_count": 0, "clean": True, "stale": [], "unknown": [], "fresh": [], "threshold_hours": 2.0})
        self.assertIn("no task currently WIP", line)

    def test_all_fresh_reads_clean_with_count(self):
        line = wrc.format_result(
            {"open_count": 2, "clean": True, "stale": [], "unknown": [], "fresh": [1, 2], "threshold_hours": 2.0}
        )
        self.assertIn("clean (2 WIP task(s)", line)

    def test_stale_entry_is_named_with_hours(self):
        result = {
            "open_count": 1,
            "clean": False,
            "stale": [{"number": 5, "owner": "off-by-one", "opened_at": "2026-07-18T02:00:00+00:00", "elapsed_hours": 3.0}],
            "unknown": [],
            "fresh": [],
            "threshold_hours": 2.0,
        }
        line = wrc.format_result(result)
        self.assertIn("task 5 (off-by-one)", line)
        self.assertIn("3.0h ago", line)
        self.assertIn("RECLAIMABLE", line)

    def test_unknown_entry_is_named_and_escalated(self):
        result = {
            "open_count": 1,
            "clean": False,
            "stale": [],
            "unknown": [{"number": 9, "owner": "nyx", "status": "WIP"}],
            "fresh": [],
            "threshold_hours": 2.0,
        }
        line = wrc.format_result(result)
        self.assertIn("task 9 (nyx)", line)
        self.assertIn("escalate now", line)


class RealCheckoutCase(unittest.TestCase):
    def test_real_roadmap_holds_zero_open_wip_today(self):
        result = wrc.find_stale(roadmap_path=os.path.join(ROOT, "ROADMAP.md"))
        self.assertEqual(result["open_count"], 0, result)
        self.assertTrue(result["clean"], result)

    def test_real_roadmap_has_no_row_number_gaps_up_to_its_own_highest_task(self):
        # Task 170 (tools/roadmap_archive.py, run for real) moved tasks
        # 1-169 out of ROADMAP.md byte-for-byte into a dated archive file,
        # leaving only current/recent rows live -- so continuity now has
        # to be checked across the live file PLUS every archive it points
        # at, not the live file alone.
        with open(os.path.join(ROOT, "ROADMAP.md"), encoding="utf-8") as f:
            text = f.read()
        rows = wrc.parse_table_rows(text)
        for name in os.listdir(ROOT):
            if name.startswith("ROADMAP-ARCHIVE-") and name.endswith(".md"):
                with open(os.path.join(ROOT, name), encoding="utf-8") as f:
                    rows.extend(wrc.parse_table_rows(f.read()))
        nums = sorted(r["number"] for r in rows)
        self.assertEqual(nums, list(range(1, nums[-1] + 1)), nums)


if __name__ == "__main__":
    unittest.main()
