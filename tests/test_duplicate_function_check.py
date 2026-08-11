"""Task 671. Proves tools/duplicate_function_check.py actually bites on a
synthetic hand-typed duplicate function body, ignores trivial bodies below
its own size floor, correctly excludes thin single-statement delegators
to a shared function (the false-positive shape its own first live run
against the real tree caught, before shipping), stays name-blind (task
513's own real finding -- `_iter_scan_files` vs `_iter_public_files`,
same body, different name), and -- the real point -- confirms the live,
current `tools/*.py` tree holds zero real violations today.
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


dfc = _load("duplicate_function_check", os.path.join(ROOT, "tools", "duplicate_function_check.py"))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _rm(path):
    shutil.rmtree(path, ignore_errors=True)


# A genuinely duplicated multi-statement body (a small ISO-timestamp
# parser, deliberately shaped like the real historical `_parse(ts)` bug
# task 509 found) -- big enough to clear `_MIN_BODY_NODES`, and not a
# thin delegator (several statements, no shared import backing it).
_REAL_DUPLICATE_BODY = (
    "def {name}(ts):\n"
    "    if ts.endswith('Z'):\n"
    "        ts = ts[:-1] + '+00:00'\n"
    "    dt = datetime.fromisoformat(ts)\n"
    "    if dt.tzinfo is None:\n"
    "        dt = dt.replace(tzinfo=timezone.utc)\n"
    "    return dt.astimezone(timezone.utc)\n"
)


class FixtureViolationCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.orita, "tools"), exist_ok=True)
        self.addCleanup(_rm, self.orita)

    def test_two_files_with_hand_typed_duplicate_body_are_flagged(self):
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_a.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_b.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        files = {rel for rel, _name, _lineno in violations[0]["locations"]}
        self.assertEqual(
            files,
            {
                os.path.join("tools", "fixture_tool_a.py"),
                os.path.join("tools", "fixture_tool_b.py"),
            },
        )
        formatted = dfc.format_violations(violations)
        self.assertIn("DUPLICATE BODY/BODIES FOUND", formatted)

    def test_duplicate_body_under_different_names_is_still_flagged(self):
        # Task 513's own real finding: arcade_hero_check.py's
        # `_iter_scan_files` carried the identical body to five siblings'
        # `_iter_public_files`, invisible to a name-sensitive hash. This
        # checker hashes the body only, never the name.
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_a.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse_ts"),
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_b.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_iso_to_utc"),
        )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        names = {name for _rel, name, _lineno in violations[0]["locations"]}
        self.assertEqual(names, {"_parse_ts", "_iso_to_utc"})

    def test_import_instead_of_redefinition_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "tools", "fixture_shared.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="parse_ts"),
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_consumer_a.py"),
            "import os, sys\n"
            "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
            "import fixture_shared\n"
            "parse_ts = fixture_shared.parse_ts\n",
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_consumer_b.py"),
            "import os, sys\n"
            "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
            "import fixture_shared\n"
            "parse_ts = fixture_shared.parse_ts\n",
        )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_different_bodies_under_the_same_name_are_not_flagged(self):
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_a.py"),
            "def _helper(x):\n"
            "    total = 0\n"
            "    for i in range(x):\n"
            "        total += i\n"
            "        total *= 2\n"
            "    return total\n",
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_b.py"),
            "def _helper(x):\n"
            "    total = 0\n"
            "    for i in range(x):\n"
            "        total -= i\n"
            "        total //= 2\n"
            "    return total\n",
        )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_trivial_body_below_the_size_floor_is_not_flagged(self):
        _write(os.path.join(self.orita, "tools", "fixture_tool_a.py"), "def _noop():\n    return None\n")
        _write(os.path.join(self.orita, "tools", "fixture_tool_b.py"), "def _noop():\n    return None\n")
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_thin_delegator_duplicated_across_files_is_not_flagged(self):
        # The false positive this checker's own first live run against
        # the real tree caught, before shipping: arcade_hero_check.py and
        # no_grading_check.py both wrap `scan_files.find_pattern_
        # violations(...)` in a single `return` -- same textual shape,
        # genuinely different bound arguments per file. Reproduced here
        # with a shared module and two distinct argument sets.
        _write(
            os.path.join(self.orita, "tools", "fixture_shared.py"),
            "def find_pattern_violations(orita_dir, iter_files, patterns, is_negated):\n"
            "    return []\n",
        )
        for suffix, args in (("a", "PATTERNS_A"), ("b", "PATTERNS_B")):
            _write(
                os.path.join(self.orita, "tools", f"fixture_tool_{suffix}.py"),
                "import os, sys\n"
                "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
                "import fixture_shared\n"
                f"{args} = object()\n"
                "def _iter_scan_files(orita_dir):\n"
                "    return []\n"
                "def _is_negated_or_predictive(text, start):\n"
                "    return False\n"
                "def _find_violations_uncached(orita_dir):\n"
                f"    return fixture_shared.find_pattern_violations(\n"
                f"        orita_dir, _iter_scan_files, {args}, _is_negated_or_predictive\n"
                "    )\n",
            )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_multi_statement_body_is_never_excluded_as_a_delegator(self):
        # A thin delegator is EXACTLY one statement. A body that happens
        # to end in a `return module.func(...)` but does real work first
        # is a genuine duplicate if it recurs, not a delegator.
        body = (
            "def {name}(x):\n"
            "    y = x + 1\n"
            "    z = y * 2\n"
            "    return fixture_shared.finish(y, z)\n"
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_shared.py"),
            "def finish(y, z):\n    return y + z\n",
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_a.py"),
            "import os, sys\n"
            "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
            "import fixture_shared\n\n" + body.format(name="_a"),
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_b.py"),
            "import os, sys\n"
            "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
            "import fixture_shared\n\n" + body.format(name="_b"),
        )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)

    def test_init_files_are_skipped(self):
        _write(
            os.path.join(self.orita, "tools", "__init__.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_a.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_non_tools_directories_are_not_scanned(self):
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-a", "detector.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        _write(
            os.path.join(self.orita, "fencepost", "RECIPES", "recipe-b", "detector.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_syntax_error_file_is_skipped_not_crashed_on(self):
        _write(os.path.join(self.orita, "tools", "fixture_broken.py"), "def broken(:\n")
        _write(
            os.path.join(self.orita, "tools", "fixture_tool_a.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])


class LiveTreeCase(unittest.TestCase):
    def test_live_tools_tree_holds_zero_real_violations_today(self):
        dfc.clear_cache()
        violations = dfc.find_violations()
        self.assertEqual(
            violations, [],
            f"real duplicate function body/bodies found in the live tools/ tree: {violations!r}",
        )

    def test_format_violations_reports_clean_on_the_live_tree(self):
        dfc.clear_cache()
        formatted = dfc.format_violations(dfc.find_violations())
        self.assertIn("clean", formatted)


class CacheCase(unittest.TestCase):
    def test_result_is_memoized_per_orita_dir(self):
        orita = tempfile.mkdtemp()
        self.addCleanup(_rm, orita)
        dfc.clear_cache()
        first = dfc.find_violations(orita_dir=orita)
        _write(
            os.path.join(orita, "tools", "fixture_tool_a.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        _write(
            os.path.join(orita, "tools", "fixture_tool_b.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        second = dfc.find_violations(orita_dir=orita)
        self.assertEqual(first, second, "a new file after the first call should not appear without clear_cache()")
        dfc.clear_cache()
        third = dfc.find_violations(orita_dir=orita)
        self.assertEqual(len(third), 1)


if __name__ == "__main__":
    unittest.main()
