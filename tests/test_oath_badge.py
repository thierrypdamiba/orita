"""Task 25. The oath-badge template, proven the same way Ogun proved the
original: green while every declared tool honors the oath, red the instant
one doesn't — and the badge names the offender, it does not just fail
quietly.
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "oath_badge", os.path.join(ROOT, "tools", "oath_badge.py")
    )
    mod = importlib.util.module_from_spec(spec)
    # dataclasses' own type resolution looks the module up in sys.modules by
    # name — register it before exec_module or the frozen dataclasses above
    # blow up on a module that "doesn't exist" from dataclasses' point of view.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


oath_badge = _load()


def _clean_catalog():
    return [
        {"name": "ListIssues", "read_only": True, "destructive": False, "operations": ("read",)},
        {"name": "GetRepository", "read_only": True, "destructive": False, "operations": ("read",)},
        {"name": "CountStargazers", "read_only": True, "destructive": False, "operations": ("read",)},
    ]


def _catalog_with_write_tool():
    dirty = _clean_catalog()
    dirty.append(
        {"name": "DeleteIssue", "read_only": False, "destructive": True, "operations": ("write",)}
    )
    return dirty


class TestOathBadgeCleanCatalog(unittest.TestCase):
    def test_all_read_only_tools_pass_the_default_oath(self):
        state = oath_badge.compute_badge_state(_clean_catalog())
        self.assertTrue(state.ok)
        self.assertEqual(state.color, oath_badge.GREEN)
        self.assertEqual(state.violations, [])
        self.assertEqual(state.tools_checked, 3)
        self.assertEqual(state.tools_clean, 3)

    def test_rendered_json_is_green_and_not_an_error(self):
        state = oath_badge.compute_badge_state(_clean_catalog())
        rendered = oath_badge.render_badge_json(state)
        import json
        payload = json.loads(rendered)
        self.assertEqual(payload["color"], "brightgreen")
        self.assertFalse(payload["isError"])


class TestOathBadgeSplicedWriteTool(unittest.TestCase):
    def test_a_single_write_shaped_tool_flips_the_badge_red(self):
        state = oath_badge.compute_badge_state(_catalog_with_write_tool())
        self.assertFalse(state.ok)
        self.assertEqual(state.color, oath_badge.RED)
        self.assertEqual(len(state.violations), 1)
        self.assertIn("DeleteIssue", state.violations[0])

    def test_the_violation_names_the_mismatched_fields(self):
        state = oath_badge.compute_badge_state(_catalog_with_write_tool())
        violation = state.violations[0]
        self.assertIn("read_only", violation)
        self.assertIn("destructive", violation)

    def test_clean_tools_still_counted_clean_even_when_one_is_dirty(self):
        state = oath_badge.compute_badge_state(_catalog_with_write_tool())
        self.assertEqual(state.tools_checked, 4)
        self.assertEqual(state.tools_clean, 3)


class TestOathBadgeCustomPolicy(unittest.TestCase):
    """A fork's non-negotiable need not be Ogun's read-only oath."""

    def test_a_no_delete_only_policy_ignores_writes_that_are_not_deletes(self):
        policy = {"destructive": False}
        catalog = [
            {"name": "CreateComment", "read_only": False, "destructive": False, "operations": ("write",)},
        ]
        state = oath_badge.compute_badge_state(catalog, policy=policy)
        self.assertTrue(state.ok, state.violations)

    def test_a_no_delete_only_policy_still_catches_a_destructive_tool(self):
        policy = {"destructive": False}
        catalog = [
            {"name": "DeleteRepo", "read_only": False, "destructive": True, "operations": ("write",)},
        ]
        state = oath_badge.compute_badge_state(catalog, policy=policy)
        self.assertFalse(state.ok)
        self.assertIn("DeleteRepo", state.violations[0])


class TestOathBadgeIntegrityChecks(unittest.TestCase):
    def test_a_failing_integrity_check_reddens_an_otherwise_clean_catalog(self):
        def broken_ledger():
            return ["ledger chain broken at seq 3"]

        state = oath_badge.compute_badge_state(_clean_catalog(), integrity_checks=[broken_ledger])
        self.assertFalse(state.ok)
        self.assertEqual(state.color, oath_badge.RED)
        self.assertIn("ledger chain broken at seq 3", state.integrity_problems)

    def test_a_passing_integrity_check_stays_green(self):
        state = oath_badge.compute_badge_state(_clean_catalog(), integrity_checks=[lambda: []])
        self.assertTrue(state.ok)


class _Behavior:
    def __init__(self, read_only, destructive, operations):
        self.read_only = read_only
        self.destructive = destructive
        self.operations = operations


class _Metadata:
    def __init__(self, behavior):
        self.behavior = behavior


class _Definition:
    def __init__(self, name, behavior):
        self.name = name
        self.metadata = _Metadata(behavior)


class _MaterializedTool:
    """Mirrors the real arcade-mcp shape: `.definition.metadata.behavior`."""

    def __init__(self, name, read_only, destructive, operations):
        behavior = _Behavior(read_only, destructive, operations)
        self.definition = _Definition(name, behavior)


class TestOathBadgeArcadeShapedCatalog(unittest.TestCase):
    """The real arcade-mcp `_catalog` shape (MaterializedTool-like), not just
    the plain-dict fixture shape — the whole point is this module works for
    the real server AND a fixture without caring which."""

    def test_arcade_shaped_clean_tool_passes(self):
        tool = _MaterializedTool("ListIssues", True, False, ["read"])
        state = oath_badge.compute_badge_state([tool])
        self.assertTrue(state.ok)

    def test_arcade_shaped_write_tool_fails(self):
        tool = _MaterializedTool("DeleteIssue", False, True, ["write"])
        state = oath_badge.compute_badge_state([tool])
        self.assertFalse(state.ok)
        self.assertIn("DeleteIssue", state.violations[0])

    def test_load_catalog_extracts_the_underscore_catalog_attribute(self):
        class _FakeApp:
            _catalog = [_MaterializedTool("ListIssues", True, False, ["read"])]

        class _FakeModule:
            app = _FakeApp()

        import sys
        sys.modules["_oath_badge_fixture_module"] = _FakeModule
        try:
            catalog = oath_badge.load_catalog("_oath_badge_fixture_module:app")
            state = oath_badge.compute_badge_state(catalog)
            self.assertTrue(state.ok)
            self.assertEqual(state.tools_checked, 1)
        finally:
            del sys.modules["_oath_badge_fixture_module"]


if __name__ == "__main__":
    unittest.main()
