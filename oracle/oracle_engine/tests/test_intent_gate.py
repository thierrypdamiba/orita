"""Task 35. `oracle/INTENT.md` states the Oracle Desk's first cadence
publishes on the town's own accounts only — no per-user reads, no mortal's
financial data — until a future decree opens it further. This module is
the check that makes that a lock, not a claim: the live server's own
registered tool catalog must contain zero tools shaped like a per-user
account read, the same names Fencepost's own consent gate
(`fencepost/seam_engine/src/seam_engine/consent.py`, `REQUIRED_SCOPES`)
requires a human to explicitly grant before a *human* account is ever
touched. Oracle Desk requires none of them to exist at all, yet.
"""
from __future__ import annotations

import os
import re
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine
_ORACLE_ROOT = os.path.dirname(_ORACLE_ENGINE_ROOT)  # oracle/
_ORITA_ROOT = os.path.dirname(_ORACLE_ROOT)  # repo root

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))

# Mirrored verbatim from fencepost/seam_engine/src/seam_engine/consent.py's
# REQUIRED_SCOPES — the exact tool names a HUMAN would have to explicitly
# grant before any per-user toolkit is read. Oracle Desk's current cadence
# requires none of these to be reachable at all; if one of these names (or
# the "gmail"/"google_calendar"/"notion"/"slack" toolkits they belong to)
# ever appears in the live catalog, the town has quietly opened a door
# oracle/INTENT.md says stays shut until a numbered decree opens it.
PER_USER_ACCOUNT_TOOL_NAMES = frozenset({
    # Gmail
    "ListEmails", "GetEmail", "SearchThreads",
    # Google Calendar
    "ListEvents", "GetEvent",
    # Notion (never wired to either desk; named because INTENT.md names it)
    "ListPages", "GetPage", "SearchPages", "QueryDatabase",
    # Slack (same — named, never wired)
    "ListChannels", "GetChannelHistory", "SearchMessages",
})

PER_USER_TOOLKIT_NAMES = frozenset({"gmail", "google_calendar", "notion", "slack"})


def _live_catalog():
    from oracle_engine.server import app

    return list(app._catalog)


def _tool_name(declared) -> str:
    if isinstance(declared, dict):
        return str(declared.get("name", ""))
    return str(getattr(declared, "name", getattr(declared, "__name__", "")))


class TestNoPerUserAccountScopeIsReachable(unittest.TestCase):
    def test_live_catalog_holds_no_per_user_account_tool_name(self):
        catalog = _live_catalog()
        self.assertGreaterEqual(len(catalog), 1, "server.py must register at least one tool")
        names = {_tool_name(t) for t in catalog}
        forbidden_present = names & PER_USER_ACCOUNT_TOOL_NAMES
        self.assertEqual(
            forbidden_present,
            set(),
            f"per-user account tool(s) reachable with no decree to authorize them: {forbidden_present}",
        )

    def test_live_catalog_names_no_per_user_toolkit(self):
        catalog = _live_catalog()
        names = {_tool_name(t).lower() for t in catalog}
        for toolkit in PER_USER_TOOLKIT_NAMES:
            for name in names:
                self.assertNotIn(
                    toolkit,
                    name,
                    f"tool {name!r} names the per-user toolkit {toolkit!r}",
                )

    def test_a_spliced_per_user_tool_would_be_caught(self):
        """Regression guard: if a Gmail-shaped tool were spliced into the
        catalog without a decree, this test must fail the same run it
        lands — proving the check is a real gate, not a rubber stamp."""
        catalog = _live_catalog() + [{"name": "ListEmails", "read_only": True}]
        names = {_tool_name(t) for t in catalog}
        self.assertTrue(names & PER_USER_ACCOUNT_TOOL_NAMES)


class TestIntentDocStatesTheClosedDoor(unittest.TestCase):
    def setUp(self):
        intent_path = os.path.join(_ORACLE_ROOT, "INTENT.md")
        self.assertTrue(os.path.exists(intent_path), "oracle/INTENT.md must exist")
        with open(intent_path, encoding="utf-8") as f:
            raw = f.read()
        # Normalize line-wrapped prose so a phrase split across a markdown
        # line break (e.g. "...accounts\nonly") still matches a substring
        # check; doctrine is about content, not where the editor wrapped it.
        self.text = re.sub(r"\s+", " ", raw)

    def test_states_town_only_cadence(self):
        self.assertIn("town's own accounts only", self.text.lower())

    def test_states_no_per_user_reads_yet(self):
        self.assertIn("no per-user read", self.text.lower())

    def test_names_the_future_decree_gate(self):
        self.assertIn("decree", self.text.lower())
        self.assertRegex(
            self.text,
            re.compile(r"future decree", re.IGNORECASE),
            "INTENT.md must name that only a future decree opens this further",
        )

    def test_names_every_forbidden_per_user_toolkit(self):
        for toolkit in ("gmail", "google calendar", "notion", "slack"):
            self.assertIn(toolkit.lower(), self.text.lower())


if __name__ == "__main__":
    unittest.main()
