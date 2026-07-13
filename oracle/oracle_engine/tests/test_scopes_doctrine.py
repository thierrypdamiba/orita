"""Task 30. oracle/SCOPES.md's oath, proven the same way Fencepost proves
its own: the live server's real, registered tool catalog is checked against
`tools/oath_badge.py`'s reusable template (task 25) — no write-capable,
trade-capable, or wallet-capable tool anywhere in this config, and a
regression that reintroduces the scaffold's original `star_repo` shape
would flip this red the same run it lands.
"""
from __future__ import annotations

import importlib.util
import logging
import os
import sys
import unittest

logging.disable(logging.CRITICAL)

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine
_ORACLE_ROOT = os.path.dirname(_ORACLE_ENGINE_ROOT)  # oracle/
_ORITA_ROOT = os.path.dirname(_ORACLE_ROOT)  # repo root

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))


def _load_oath_badge():
    spec = importlib.util.spec_from_file_location(
        "oath_badge", os.path.join(_ORITA_ROOT, "tools", "oath_badge.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


oath_badge = _load_oath_badge()


def _live_catalog():
    from oracle_engine.server import app

    return list(app._catalog)


class TestLiveServerHonorsTheOath(unittest.TestCase):
    def test_every_registered_tool_is_clean_under_the_default_read_only_policy(self):
        catalog = _live_catalog()
        self.assertGreaterEqual(len(catalog), 1, "server.py must register at least one tool")
        state = oath_badge.compute_badge_state(catalog)
        self.assertTrue(state.ok, state.violations)
        self.assertEqual(state.color, oath_badge.GREEN)
        self.assertEqual(state.violations, [])

    def test_the_scaffold_default_write_tool_does_not_survive(self):
        """`arcade new` ships a `star_repo` example tool by default — a real
        write against a mortal's GitHub account (Operation.UPDATE,
        read_only=False). It must not be registered on the live server."""
        names = {oath_badge._extract_declared(t)[0] for t in _live_catalog()}
        self.assertNotIn("star_repo", names)
        self.assertNotIn("whisper_secret", names)


class TestOathViolationWouldBeCaught(unittest.TestCase):
    """Regression guard: if `star_repo`'s exact declared shape were spliced
    back into the catalog, the badge must go red, naming it — proving the
    check is a real gate, not a rubber stamp."""

    def test_a_spliced_write_shaped_tool_flips_the_badge_red(self):
        catalog = _live_catalog() + [
            {
                "name": "star_repo",
                "read_only": False,
                "destructive": False,
                "operations": ("write",),
            }
        ]
        state = oath_badge.compute_badge_state(catalog)
        self.assertFalse(state.ok)
        self.assertEqual(state.color, oath_badge.RED)
        self.assertEqual(len(state.violations), 1)
        self.assertIn("star_repo", state.violations[0])


class TestScopesDocNamesTheForbiddenClasses(unittest.TestCase):
    def test_scopes_md_states_zero_trade_and_wallet_scopes(self):
        scopes_path = os.path.join(_ORACLE_ROOT, "SCOPES.md")
        with open(scopes_path, encoding="utf-8") as f:
            text = f.read()
        for forbidden_class in ("trade", "wallet", "brokerage"):
            self.assertIn(forbidden_class, text.lower())


if __name__ == "__main__":
    unittest.main()
