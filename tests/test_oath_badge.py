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


class TestMainCliPolicyArgGuard(unittest.TestCase):
    """--policy used to hand a bare `json.loads(...)` result straight
    through to `compute_badge_state`, which crashed with a bare
    AttributeError (`ToolAudit.policy.items()`) on anything but a real
    dict -- the same valid-JSON-wrong-shape crash class task 364 fixed for
    ritual_check.py's own CLI. Must now raise the named OathBadgeArgError
    instead."""

    def setUp(self):
        import sys

        class _FakeApp:
            _catalog = [_MaterializedTool("ListIssues", True, False, ["read"])]

        class _FakeModule:
            app = _FakeApp()

        sys.modules["_oath_badge_fixture_module"] = _FakeModule

    def tearDown(self):
        import sys
        del sys.modules["_oath_badge_fixture_module"]

    def test_list_policy_raises_named_error(self):
        import json
        import tempfile
        fd, policy_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump([1, 2, 3], f)
        try:
            with self.assertRaises(oath_badge.OathBadgeArgError):
                oath_badge.main([
                    "--catalog", "_oath_badge_fixture_module:app",
                    "--policy", policy_path,
                ])
        finally:
            os.remove(policy_path)

    def test_well_formed_policy_still_works(self):
        import json
        import tempfile
        fd, policy_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({"read_only": True}, f)
        try:
            rc = oath_badge.main([
                "--catalog", "_oath_badge_fixture_module:app",
                "--policy", policy_path,
            ])
            self.assertEqual(rc, 0)
        finally:
            os.remove(policy_path)


class TestMainCliTrailingFlagWithNoValue(unittest.TestCase):
    """`_take()` used to index straight into `argv[i + 1]` with no bounds
    check -- any flag (`--catalog`, `--policy`, `--label`, `--out`) given as
    the last token with no following value crashed with a bare
    `IndexError: list index out of range` instead of naming the real
    problem. Reproduced live before the fix (mypy also flagged the
    downstream symptom: `load_catalog(catalog_spec)` at a `str | None`
    catalog_spec, since `_take` could return `None` for a genuinely present
    but valueless flag). Must now raise the named OathBadgeArgError for
    every one of the four flags, matching the discipline
    TestMainCliPolicyArgGuard already established for `--policy`'s
    wrong-JSON-shape case."""

    def setUp(self):
        import sys

        class _FakeApp:
            _catalog = [_MaterializedTool("ListIssues", True, False, ["read"])]

        class _FakeModule:
            app = _FakeApp()

        sys.modules["_oath_badge_fixture_module"] = _FakeModule

    def tearDown(self):
        import sys
        del sys.modules["_oath_badge_fixture_module"]

    def test_catalog_with_no_value_raises_named_error_not_indexerror(self):
        with self.assertRaises(oath_badge.OathBadgeArgError) as ctx:
            oath_badge.main(["--catalog"])
        self.assertIn("--catalog", str(ctx.exception))

    def test_policy_with_no_value_raises_named_error_not_indexerror(self):
        with self.assertRaises(oath_badge.OathBadgeArgError) as ctx:
            oath_badge.main([
                "--catalog", "_oath_badge_fixture_module:app",
                "--policy",
            ])
        self.assertIn("--policy", str(ctx.exception))

    def test_label_with_no_value_raises_named_error_not_indexerror(self):
        with self.assertRaises(oath_badge.OathBadgeArgError) as ctx:
            oath_badge.main([
                "--catalog", "_oath_badge_fixture_module:app",
                "--label",
            ])
        self.assertIn("--label", str(ctx.exception))

    def test_out_with_no_value_raises_named_error_not_indexerror(self):
        with self.assertRaises(oath_badge.OathBadgeArgError) as ctx:
            oath_badge.main([
                "--catalog", "_oath_badge_fixture_module:app",
                "--out",
            ])
        self.assertIn("--out", str(ctx.exception))


class TestUsageStringMatchesRealFlags(unittest.TestCase):
    """Task 437. The no-`--catalog` usage string advertised a `--write path`
    flag lifted from seam_engine/badge.py's own CLI -- oath_badge.py never
    parses `--write` at all, only `--out` actually persists the rendered
    badge to disk. An unrecognized flag is silently left in `argv` and
    never inspected again, so `--write somepath` used to exit 0, print the
    badge, and write nothing -- no error, matching the tool's own
    (wrong) usage text exactly."""

    def setUp(self):
        import sys

        class _FakeApp:
            _catalog = [_MaterializedTool("ListIssues", True, False, ["read"])]

        class _FakeModule:
            app = _FakeApp()

        sys.modules["_oath_badge_write_fixture_module"] = _FakeModule

    def tearDown(self):
        import sys
        del sys.modules["_oath_badge_write_fixture_module"]

    def test_usage_string_does_not_advertise_the_phantom_write_flag(self):
        import io
        import contextlib

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            rc = oath_badge.main([])
        self.assertEqual(rc, 2)
        self.assertNotIn("--write", stderr.getvalue())
        self.assertIn("--out path", stderr.getvalue())

    def test_write_flag_is_a_silent_no_op_out_is_the_real_flag(self):
        import tempfile

        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(path)
        try:
            rc = oath_badge.main([
                "--catalog", "_oath_badge_write_fixture_module:app",
                "--write", path,
            ])
            self.assertEqual(rc, 0)
            self.assertFalse(os.path.exists(path), "--write is not a real flag; it must not create a file")

            rc = oath_badge.main([
                "--catalog", "_oath_badge_write_fixture_module:app",
                "--out", path,
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(path), "--out is the real, tested persistence flag")
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestComputeBadgeStateHasNoDeadLabelParameter(unittest.TestCase):
    """Task 617. `compute_badge_state` used to accept a `label` keyword
    that did nothing at all -- `BadgeState` carries no label field and the
    badge's message text never referenced it, so `--label custom` reached
    `compute_badge_state(catalog, policy, label=label)` and was silently
    dropped; only the separate `render_badge_json(state, label=label)`
    call actually controlled the rendered label. `ruff --select ARG001`
    caught it as an unused function argument on ground `tools/` had never
    been linted against before. The parameter is now gone entirely rather
    than left unused, so a caller (this template is meant to be copied by
    forks, per its own module docstring) gets a real `TypeError` instead
    of a second, competing, no-op place to try to set the label -- the
    same "unrecognized flag is silently accepted" shape task 437's
    `--write` fix above already named in this same file, one layer
    deeper (a real parameter this time, not an unparsed CLI flag)."""

    def test_label_kwarg_no_longer_accepted(self):
        with self.assertRaises(TypeError):
            oath_badge.compute_badge_state(_clean_catalog(), label="custom")

    def test_cli_label_flag_still_controls_the_rendered_label_end_to_end(self):
        import io
        import contextlib

        class _FakeApp:
            _catalog = [_MaterializedTool("ListIssues", True, False, ["read"])]

        class _FakeModule:
            app = _FakeApp()

        sys.modules["_oath_badge_label_fixture_module"] = _FakeModule
        try:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = oath_badge.main([
                    "--catalog", "_oath_badge_label_fixture_module:app",
                    "--label", "my-fork-oath",
                ])
            self.assertEqual(rc, 0)
            self.assertIn('"label": "my-fork-oath"', stdout.getvalue())
        finally:
            del sys.modules["_oath_badge_label_fixture_module"]


if __name__ == "__main__":
    unittest.main()
