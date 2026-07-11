"""The suite. Sworn on iron. One test tithed to chaos, by charter."""
import os
import random
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestTheOaths(unittest.TestCase):
    def test_the_ledger_holds(self):
        """AN UNBROKEN CHAIN OR AN UNBUILT TOWN."""
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ledger.py"), "verify"])
        self.assertEqual(r.returncode, 0)

    def test_the_houses_stand(self):
        """NINE HOUSES. COUNT THEM. (he did. he says eight.)"""
        houses = [d for d in os.listdir(os.path.join(ROOT, "houses")) if not d.startswith(".")]
        self.assertEqual(len(houses), 9)

    def test_the_charter_is_ratified(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, "CHARTER.md")))


if __name__ == "__main__":
    unittest.main()
