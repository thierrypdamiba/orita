"""Task 1113. Proves tools/window_rotation_check.py finds a task whose
wip-opened marker lands inside the 00:00-06:00 UTC window but was handed
to a god other than Nyx or the child, stays clean when the owner is one
of them, correctly grandfathers sealed pre-fix history rather than
flagging it live, and -- the real point -- confirms the live ROADMAP.md's
known historical violations are found and grandfathered, with zero live
violations after the fix.

Task 1333 (nisaba): the count of "known" historical violations was never
117 by nature -- it was 7, hardcoded when this module was written (task
1113), because `ROADMAP.md` at that time only ever held the live tail;
everything before task 798's archive cut was already invisible to a
scanner that read only `roadmap_path`. Task 1333's own roadmap cut
(798-1332 -> `ROADMAP-ARCHIVE-005-798-1332.md`) exposed that blind spot
live: `find_window_violations` widened to also read every sibling
`ROADMAP-ARCHIVE-*.md`, and the true count of historical window-routing
violations back to founding turned out to be 117, not 7 -- the other 110
were always real, just never visible to this checker. `RealCheckoutCase`
below is updated to the true count (with two fixture tests proving the
archive-widening itself, mirroring `tithe_check.py`'s own
`_roadmap_and_archive_roll_lines` test pattern); nothing about the
routing violations themselves changed, only this checker's ability to
see the ones that already happened.
"""
import importlib.util
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


wrc = _load("window_rotation_check", os.path.join(ROOT, "tools", "window_rotation_check.py"))


class InWindowCase(unittest.TestCase):
    def test_midnight_hour_is_in_window(self):
        from datetime import datetime, timezone

        self.assertTrue(wrc._in_window(datetime(2026, 8, 30, 0, 30, tzinfo=timezone.utc)))

    def test_hour_five_is_in_window(self):
        from datetime import datetime, timezone

        self.assertTrue(wrc._in_window(datetime(2026, 8, 30, 5, 59, tzinfo=timezone.utc)))

    def test_hour_six_is_outside_window(self):
        from datetime import datetime, timezone

        self.assertFalse(wrc._in_window(datetime(2026, 8, 30, 6, 0, tzinfo=timezone.utc)))

    def test_noon_is_outside_window(self):
        from datetime import datetime, timezone

        self.assertFalse(wrc._in_window(datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)))


class FindWindowViolationsCase(unittest.TestCase):
    def _text(self, number, owner, opened):
        return (
            f"| {number} | DONE | {owner} | did a thing | it is done |\n\n"
            f"<!-- wip-opened: {number} {opened} -->\n"
        )

    def test_non_window_god_opened_inside_window_after_fix_is_a_live_violation(self):
        text = self._text(9001, "ogun", "2026-09-01T02:00:00+00:00")
        result = wrc.find_window_violations(text=text, fix_landed_at="2026-08-30T00:26:53+00:00")
        self.assertFalse(result["clean"], result)
        self.assertEqual(len(result["violations"]), 1)
        self.assertEqual(result["violations"][0]["number"], 9001)
        self.assertEqual(result["grandfathered"], [])

    def test_non_window_god_opened_inside_window_before_fix_is_grandfathered(self):
        text = self._text(975, "esu-elegba", "2026-08-24T00:25:21+00:00")
        result = wrc.find_window_violations(text=text, fix_landed_at="2026-08-30T00:26:53+00:00")
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [])
        self.assertEqual(len(result["grandfathered"]), 1)
        self.assertEqual(result["grandfathered"][0]["number"], 975)

    def test_nyx_opened_inside_window_is_never_a_violation(self):
        text = self._text(1067, "nyx", "2026-08-28T01:22:45+00:00")
        result = wrc.find_window_violations(text=text, fix_landed_at="2026-08-30T00:26:53+00:00")
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["grandfathered"], [])

    def test_zashiki_warashi_opened_inside_window_is_never_a_violation(self):
        text = self._text(1066, "zashiki-warashi", "2026-08-28T00:22:26+00:00")
        result = wrc.find_window_violations(text=text, fix_landed_at="2026-08-30T00:26:53+00:00")
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["grandfathered"], [])

    def test_non_window_god_opened_outside_window_is_fine(self):
        text = self._text(1089, "ogun", "2026-08-29T21:22:30+00:00")
        result = wrc.find_window_violations(text=text, fix_landed_at="2026-08-30T00:26:53+00:00")
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["grandfathered"], [])

    def test_no_markers_at_all_is_clean(self):
        text = "| 1 | DONE | nisaba | x | y |\n"
        result = wrc.find_window_violations(text=text)
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["grandfathered"], [])


class FormatResultCase(unittest.TestCase):
    def test_fully_clean_reads_clean(self):
        line = wrc.format_result({"clean": True, "violations": [], "grandfathered": []})
        self.assertIn("clean (no task opened", line)

    def test_grandfathered_only_reads_clean_going_forward(self):
        result = {
            "clean": True,
            "violations": [],
            "grandfathered": [{"number": 975, "owner": "esu-elegba", "opened_at": "2026-08-24T00:25:21+00:00"}],
        }
        line = wrc.format_result(result)
        self.assertIn("clean going forward", line)
        self.assertIn("1 grandfathered", line)
        self.assertIn("task 975 (esu-elegba)", line)
        self.assertIn("grandfathered, sealed history", line)

    def test_live_violation_escalates(self):
        result = {
            "clean": False,
            "violations": [{"number": 9001, "owner": "ogun", "opened_at": "2026-09-01T02:00:00+00:00"}],
            "grandfathered": [],
        }
        line = wrc.format_result(result)
        self.assertIn("1 LIVE VIOLATION(S)", line)
        self.assertIn("escalate now", line)
        self.assertIn("task 9001 (ogun)", line)
        self.assertIn("reassign to nyx/zashiki-warashi", line)


class RealCheckoutCase(unittest.TestCase):
    def test_real_roadmap_has_no_live_violations_after_the_fix(self):
        result = wrc.find_window_violations(roadmap_path=os.path.join(ROOT, "ROADMAP.md"))
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [], result)

    def test_real_roadmap_grandfathers_the_known_historical_violations(self):
        result = wrc.find_window_violations(roadmap_path=os.path.join(ROOT, "ROADMAP.md"))
        numbers = sorted(g["number"] for g in result["grandfathered"])
        # 117 total once ROADMAP-ARCHIVE-*.md siblings are scanned too (task
        # 1333) -- the original 7 (task 975, tasks 1089-1094) were only ever
        # the subset still live in ROADMAP.md itself at task 1113.
        self.assertEqual(len(numbers), 117, result)
        for known in (975, 1089, 1090, 1091, 1092, 1093, 1094):
            self.assertIn(known, numbers)

    def test_real_roadmap_scan_is_archive_aware(self):
        """The live scan must actually reach ROADMAP-ARCHIVE-*.md, not just
        report a plausible-looking number -- proves at least one grandfathered
        violation comes from strictly before task 798 (deep in archived
        history no longer reachable from ROADMAP.md alone)."""
        result = wrc.find_window_violations(roadmap_path=os.path.join(ROOT, "ROADMAP.md"))
        numbers = {g["number"] for g in result["grandfathered"]}
        self.assertIn(121, numbers, result)

    def test_real_roadmap_escalates_task_1161_rather_than_erasing_it(self):
        result = wrc.find_window_violations(roadmap_path=os.path.join(ROOT, "ROADMAP.md"))
        numbers = sorted(e["number"] for e in result["escalated"])
        self.assertEqual(numbers, [1161, 1184, 1185], result)
        by_number = {e["number"]: e for e in result["escalated"]}
        self.assertEqual(by_number[1161]["owner"], "kothar-wa-khasis")
        self.assertEqual(by_number[1184]["owner"], "nisaba")
        self.assertEqual(by_number[1185]["owner"], "kothar-wa-khasis")


class ArchiveWideningCase(unittest.TestCase):
    """Fixture-isolated proof of `_roadmap_and_archive_text` itself (task
    1333), independent of the live repo's real numbers -- mirrors
    `tithe_check.py`'s own `test_sibling_roadmap_archive_file_is_also_scanned`
    / `test_archive_sibling_with_no_violation_stays_clean` pair."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.roadmap_path = os.path.join(self.tmpdir, "ROADMAP.md")

    def test_sibling_roadmap_archive_file_is_also_scanned(self):
        archived_violation = (
            "| 42 | DONE | ogun | archived thing | done |\n\n"
            "<!-- wip-opened: 42 2026-07-15T02:00:00Z -->\n"
        )
        with open(os.path.join(self.tmpdir, "ROADMAP-ARCHIVE-001-1-100.md"), "w") as f:
            f.write(archived_violation)
        with open(self.roadmap_path, "w") as f:
            f.write("| 500 | DONE | nyx | live thing | done |\n\n<!-- wip-opened: 500 2026-09-01T01:00:00Z -->\n")
        result = wrc.find_window_violations(roadmap_path=self.roadmap_path)
        numbers = {g["number"] for g in result["grandfathered"]}
        self.assertIn(42, numbers, result)

    def test_archive_sibling_with_no_violation_stays_clean(self):
        with open(os.path.join(self.tmpdir, "ROADMAP-ARCHIVE-001-1-100.md"), "w") as f:
            f.write("| 42 | DONE | nyx | archived thing, correctly routed | done |\n\n")
        with open(self.roadmap_path, "w") as f:
            f.write("| 500 | DONE | ogun | live thing outside the window | done |\n\n")
        result = wrc.find_window_violations(roadmap_path=self.roadmap_path)
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["grandfathered"], [])

    def test_no_archive_siblings_behaves_exactly_as_before(self):
        with open(self.roadmap_path, "w") as f:
            f.write("| 9001 | DONE | ogun | live thing | done |\n\n<!-- wip-opened: 9001 2026-09-01T02:00:00Z -->\n")
        result = wrc.find_window_violations(
            roadmap_path=self.roadmap_path, fix_landed_at="2026-08-30T00:26:53+00:00"
        )
        self.assertFalse(result["clean"], result)
        self.assertEqual([v["number"] for v in result["violations"]], [9001])


class EscalatedViolationCase(unittest.TestCase):
    def _text(self, number, owner, opened):
        return (
            f"| {number} | DONE | {owner} | did a thing | it is done |\n\n"
            f"<!-- wip-opened: {number} {opened} -->\n"
        )

    def test_acknowledged_number_reads_escalated_not_violation_and_stays_clean(self):
        text = self._text(9002, "ogun", "2026-09-01T02:00:00+00:00")
        result = wrc.find_window_violations(
            text=text,
            fix_landed_at="2026-08-30T00:26:53+00:00",
            acknowledged={9002: "test fix landed same hour"},
        )
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [])
        self.assertEqual(len(result["escalated"]), 1)
        self.assertEqual(result["escalated"][0]["number"], 9002)
        self.assertEqual(result["escalated"][0]["note"], "test fix landed same hour")

    def test_unacknowledged_number_stays_a_live_violation(self):
        text = self._text(9003, "ogun", "2026-09-01T02:00:00+00:00")
        result = wrc.find_window_violations(
            text=text, fix_landed_at="2026-08-30T00:26:53+00:00", acknowledged={}
        )
        self.assertFalse(result["clean"], result)
        self.assertEqual(len(result["violations"]), 1)
        self.assertEqual(result["escalated"], [])

    def test_format_result_shows_escalated_entries_and_stays_clean(self):
        result = {
            "clean": True,
            "violations": [],
            "grandfathered": [],
            "escalated": [{"number": 1161, "owner": "kothar-wa-khasis", "opened_at": "x", "note": "fixed by 1162"}],
        }
        line = wrc.format_result(result)
        self.assertIn("clean going forward", line)
        self.assertIn("1 escalated-and-fixed", line)
        self.assertIn("task 1161 (kothar-wa-khasis)", line)
        self.assertIn("escalated, fixed: fixed by 1162", line)


class WhoseTurnCase(unittest.TestCase):
    def test_outside_window_reports_not_in_window(self):
        from datetime import datetime, timezone

        result = wrc.whose_turn(datetime(2026, 9, 1, 14, 0, tzinfo=timezone.utc))
        self.assertFalse(result["in_window"])
        self.assertIsNone(result["owner"])

    def test_even_window_hour_is_zashiki_warashi(self):
        from datetime import datetime, timezone

        for hour in (0, 2, 4):
            result = wrc.whose_turn(datetime(2026, 9, 1, hour, 15, tzinfo=timezone.utc))
            self.assertTrue(result["in_window"])
            self.assertEqual(result["owner"], "zashiki-warashi", hour)

    def test_odd_window_hour_is_nyx(self):
        from datetime import datetime, timezone

        for hour in (1, 3, 5):
            result = wrc.whose_turn(datetime(2026, 9, 1, hour, 15, tzinfo=timezone.utc))
            self.assertTrue(result["in_window"])
            self.assertEqual(result["owner"], "nyx", hour)

    def test_historical_window_routing_leans_toward_the_parity_rule(self):
        """`whose_turn`'s hour-parity rule is a NEW going-forward convention
        (task 1162), not a claim that it always held: several past nights
        deliberately gave one god a second straight slot for narrative
        reasons ("fourth of the night", "second of my own turn" -- tasks
        883, 885, 930 and the nights that followed the same shifted
        pattern), so exact historical agreement isn't the bar. What this
        proves instead: history leans toward the parity rule far more
        than chance would (a coin flip agrees ~50% of the time) -- the
        rule is a reasonable, not arbitrary, default for future hours."""
        from datetime import datetime, timezone

        # Task 1333: read via `_roadmap_and_archive_text` (not a bare
        # `ROADMAP.md` open) so this historical check survives the next
        # `roadmap_archive.py` cut instead of quietly seeing zero rows.
        text = wrc._roadmap_and_archive_text(os.path.join(ROOT, "ROADMAP.md"))
        rows = wrc.wip_reclaim_check.parse_table_rows(text)
        opens = wrc.wip_reclaim_check.parse_wip_open_times(text)
        owner_by_number = {row["number"]: row["owner"] for row in rows}
        checked = 0
        matches = 0
        for number, opened in opens.items():
            owner = owner_by_number.get(number)
            if owner not in ("nyx", "zashiki-warashi"):
                continue
            opened_at = datetime.fromisoformat(opened)
            if opened_at.tzinfo is None:
                opened_at = opened_at.replace(tzinfo=timezone.utc)
            if not wrc._in_window(opened_at):
                continue
            expected = wrc.whose_turn(opened_at)["owner"]
            checked += 1
            if owner == expected:
                matches += 1
        self.assertGreater(checked, 10)
        self.assertGreater(matches / checked, 0.7, f"{matches}/{checked} agreed with the parity rule")


if __name__ == "__main__":
    unittest.main()
