"""Task 1854. Proves tools/roadmap_row_order_check.py catches a row
inserted out of ascending task-number order in the live table -- exactly
the shape task 1853's own row took (inserted right under the header
instead of appended at the bottom) -- and stays clean on a well-ordered
table, including the live ROADMAP.md after this hour's fix."""
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


rroc = _load("roadmap_row_order_check", os.path.join(ROOT, "tools", "roadmap_row_order_check.py"))


class FindOrderViolationsCase(unittest.TestCase):
    def _row(self, number, owner="off-by-one"):
        return f"| {number} | DONE | {owner} | did a thing | it is done |\n"

    def test_ascending_rows_are_clean(self):
        text = self._row(1) + self._row(2) + self._row(3)
        result = rroc.find_order_violations(text=text)
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["row_count"], 3)

    def test_row_inserted_under_the_header_is_a_violation(self):
        # The exact task-1853 shape: the newest row (3) lands first,
        # ahead of the older run (1, 2) instead of after it.
        text = self._row(3) + self._row(1) + self._row(2)
        result = rroc.find_order_violations(text=text)
        self.assertFalse(result["clean"], result)
        self.assertEqual(len(result["violations"]), 1)
        v = result["violations"][0]
        self.assertEqual(v["number"], 1)
        self.assertEqual(v["after"], 3)

    def test_duplicate_number_is_a_violation(self):
        text = self._row(1) + self._row(1)
        result = rroc.find_order_violations(text=text)
        self.assertFalse(result["clean"], result)

    def test_empty_table_is_clean(self):
        result = rroc.find_order_violations(text="")
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["row_count"], 0)

    def test_single_row_is_clean(self):
        result = rroc.find_order_violations(text=self._row(1))
        self.assertTrue(result["clean"], result)


class RealCheckoutCase(unittest.TestCase):
    """The live town's own ROADMAP.md, read for real -- proves this
    hour's own reordering fix (task 1853 moved back after task 1852)
    actually holds against the checked-in file, not just a synthetic
    string."""

    def test_real_roadmap_has_zero_live_violations(self):
        result = rroc.find_order_violations()
        self.assertTrue(result["clean"], result["violations"])


if __name__ == "__main__":
    unittest.main()
