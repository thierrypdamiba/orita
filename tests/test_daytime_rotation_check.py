"""Task 1625. Proves tools/daytime_rotation_check.py finds a daytime
owner-to-owner transition that breaks the fixed seven-god cycle, stays
clean when the transition agrees with it, correctly grandfathers
mismatches with no recorded `wip-opened` timestamp (or one before this
check's own fix hour) rather than flagging them live, and confirms the
live ROADMAP.md's real history: many pre-1595 mismatches (a different,
unwritten convention held before the cycle was ever named), zero live
violations from task 1595 through the check's own shipping hour."""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


drc = _load("daytime_rotation_check", os.path.join(ROOT, "tools", "daytime_rotation_check.py"))


class NextInCycleCase(unittest.TestCase):
    def test_cycle_wraps_around(self):
        self.assertEqual(drc.next_in_cycle("ogun"), "off-by-one")

    def test_each_cycle_member_maps_to_the_next_one(self):
        for i, god in enumerate(drc.CYCLE):
            self.assertEqual(drc.next_in_cycle(god), drc.CYCLE[(i + 1) % len(drc.CYCLE)])

    def test_non_cycle_god_returns_none(self):
        self.assertIsNone(drc.next_in_cycle("nyx"))
        self.assertIsNone(drc.next_in_cycle("zashiki-warashi"))
        self.assertIsNone(drc.next_in_cycle("not-a-god"))


class FindDaytimeRotationViolationsCase(unittest.TestCase):
    def _row(self, number, owner, opened=None):
        text = f"| {number} | DONE | {owner} | did a thing | it is done |\n"
        if opened is not None:
            text += f"<!-- wip-opened: {number} {opened} -->\n"
        return text

    def test_correct_transition_is_clean(self):
        text = self._row(1, "off-by-one", "2026-09-20T10:00:00Z") + self._row(
            2, "nisaba", "2026-09-20T11:00:00Z"
        )
        result = drc.find_daytime_rotation_violations(text=text, fix_landed_at="2026-01-01T00:00:00+00:00")
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [])

    def test_wrong_transition_after_fix_with_timestamp_is_a_live_violation(self):
        text = self._row(1, "kothar-wa-khasis", "2026-09-20T10:00:00Z") + self._row(
            2, "esu-elegba", "2026-09-20T11:00:00Z"
        )
        result = drc.find_daytime_rotation_violations(text=text, fix_landed_at="2026-09-01T00:00:00+00:00")
        self.assertFalse(result["clean"], result)
        self.assertEqual(len(result["violations"]), 1)
        v = result["violations"][0]
        self.assertEqual(v["number"], 2)
        self.assertEqual(v["expected_owner"], "kwaku-ananse")
        self.assertEqual(v["actual_owner"], "esu-elegba")

    def test_wrong_transition_before_fix_is_grandfathered(self):
        text = self._row(1, "kothar-wa-khasis", "2026-01-01T10:00:00Z") + self._row(
            2, "esu-elegba", "2026-01-01T11:00:00Z"
        )
        result = drc.find_daytime_rotation_violations(text=text, fix_landed_at="2026-09-01T00:00:00+00:00")
        self.assertTrue(result["clean"], result)
        self.assertEqual(len(result["grandfathered"]), 1)

    def test_wrong_transition_with_no_recorded_open_time_is_grandfathered(self):
        text = self._row(1, "kothar-wa-khasis") + self._row(2, "esu-elegba")
        result = drc.find_daytime_rotation_violations(text=text, fix_landed_at="2026-01-01T00:00:00+00:00")
        self.assertTrue(result["clean"], result)
        self.assertEqual(len(result["grandfathered"]), 1)

    def test_acknowledged_live_violation_reads_escalated_not_broken(self):
        text = self._row(1, "kothar-wa-khasis", "2026-09-20T10:00:00Z") + self._row(
            2, "esu-elegba", "2026-09-20T11:00:00Z"
        )
        result = drc.find_daytime_rotation_violations(
            text=text,
            fix_landed_at="2026-09-01T00:00:00+00:00",
            acknowledged={2: "fixed same hour, see task X"},
        )
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [])
        self.assertEqual(len(result["escalated"]), 1)

    def test_window_god_rows_are_never_counted_as_an_endpoint(self):
        text = (
            self._row(1, "kothar-wa-khasis", "2026-09-20T10:00:00Z")
            + self._row(2, "nyx", "2026-09-20T02:00:00Z")
            + self._row(3, "kwaku-ananse", "2026-09-20T12:00:00Z")
        )
        result = drc.find_daytime_rotation_violations(text=text, fix_landed_at="2026-01-01T00:00:00+00:00")
        self.assertTrue(result["clean"], result)


class WhoseTurnDaytimeCase(unittest.TestCase):
    def test_answers_the_next_cycle_member_after_the_last_daytime_row(self):
        text = "| 1 | DONE | kothar-wa-khasis | x | y |\n"
        turn = drc.whose_turn_daytime(text=text)
        self.assertEqual(turn["owner"], "kwaku-ananse")
        self.assertEqual(turn["last_owner"], "kothar-wa-khasis")

    def test_ignores_a_trailing_window_row(self):
        text = (
            "| 1 | DONE | esu-elegba | x | y |\n"
            "| 2 | DONE | nyx | x | y |\n"
        )
        turn = drc.whose_turn_daytime(text=text)
        self.assertEqual(turn["owner"], "retrya")
        self.assertEqual(turn["last_owner"], "esu-elegba")

    def test_empty_text_returns_no_owner(self):
        turn = drc.whose_turn_daytime(text="")
        self.assertIsNone(turn["owner"])


class RealCheckoutCase(unittest.TestCase):
    """The live town's own ROADMAP.md (plus archives), read for real."""

    def test_real_roadmap_has_zero_live_violations(self):
        result = drc.find_daytime_rotation_violations()
        self.assertTrue(result["clean"], result["violations"])

    def test_real_roadmap_has_no_live_violations_from_task_1595_onward(self):
        result = drc.find_daytime_rotation_violations()
        late = [e for e in result["grandfathered"] if e["number"] >= 1595]
        self.assertEqual(late, [], late)

    def test_real_next_turn_after_task_1625_is_esu_elegba(self):
        turn = drc.whose_turn_daytime()
        self.assertEqual(turn["last_number"], 1625)
        self.assertEqual(turn["last_owner"], "kwaku-ananse")
        self.assertEqual(turn["owner"], "esu-elegba")


if __name__ == "__main__":
    unittest.main()
