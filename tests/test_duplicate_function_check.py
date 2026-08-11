"""Task 671. Proves tools/duplicate_function_check.py actually bites on a
synthetic hand-typed duplicate function body, ignores trivial bodies below
its own size floor, correctly excludes thin single-statement delegators
to a shared function (the false-positive shape its own first live run
against the real tree caught, before shipping), stays name-blind (task
513's own real finding -- `_iter_scan_files` vs `_iter_public_files`,
same body, different name), and -- the real point -- confirms the live,
current tree holds zero real (unseeded) violations today.

Task 674 widened the scan past `tools/*.py` to also cover
`fencepost/seam_engine/src/seam_engine/*.py` and
`oracle/oracle_engine/src/oracle_engine/*.py`, and seeded the checker's
first-ever `_ALLOWED_DUPLICATES` entry (`_dynamic_import_target`, real
and deliberate between `tools/network_boundary_check.py` and
`fencepost/seam_engine/src/seam_engine/recipes.py`). `FixtureViolationCase`
below still writes its synthetic fixtures under a fake `tools/` dir --
the checker's own logic (thin-delegator exclusion, size floor, name-
blindness, `_ALLOWED_DUPLICATES`) does not depend on which of the three
scanned globs a file lives under, so re-using `tools/` there keeps those
cases focused on the logic they exist to prove. `WidenedScopeCase` and
`AllowedDuplicateCase` below are the new, scope-specific coverage.
"""
import ast
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
    def test_live_tree_holds_zero_real_unseeded_violations_today(self):
        dfc.clear_cache()
        violations = dfc.find_violations()
        self.assertEqual(
            violations, [],
            f"real duplicate function body/bodies found in the live tree: {violations!r}",
        )

    def test_format_violations_reports_clean_on_the_live_tree(self):
        dfc.clear_cache()
        formatted = dfc.format_violations(dfc.find_violations())
        self.assertIn("clean", formatted)


class WidenedScopeCase(unittest.TestCase):
    """Task 674: `fencepost/seam_engine/src/seam_engine/*.py` and
    `oracle/oracle_engine/src/oracle_engine/*.py` joined `tools/*.py` as
    scanned globs. These prove the widened globs are actually walked --
    not just present as unused constants -- by planting a duplicate that
    ONLY a cross-directory scan can see."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        for rel in (
            os.path.join("tools"),
            os.path.join("fencepost", "seam_engine", "src", "seam_engine"),
            os.path.join("oracle", "oracle_engine", "src", "oracle_engine"),
        ):
            os.makedirs(os.path.join(self.orita, rel), exist_ok=True)
        self.addCleanup(_rm, self.orita)

    def test_duplicate_between_tools_and_seam_engine_is_flagged(self):
        _write(
            os.path.join(self.orita, "tools", "fixture_tool.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        _write(
            os.path.join(self.orita, "fencepost", "seam_engine", "src", "seam_engine", "fixture_seam.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        files = {rel for rel, _name, _lineno in violations[0]["locations"]}
        self.assertEqual(
            files,
            {
                os.path.join("tools", "fixture_tool.py"),
                os.path.join("fencepost", "seam_engine", "src", "seam_engine", "fixture_seam.py"),
            },
        )

    def test_duplicate_between_tools_and_oracle_engine_is_flagged(self):
        _write(
            os.path.join(self.orita, "tools", "fixture_tool.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        _write(
            os.path.join(self.orita, "oracle", "oracle_engine", "src", "oracle_engine", "fixture_oracle.py"),
            "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
        )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)

    def test_duplicate_confined_to_seam_engine_alone_is_still_flagged(self):
        for name in ("fixture_seam_a.py", "fixture_seam_b.py"):
            _write(
                os.path.join(self.orita, "fencepost", "seam_engine", "src", "seam_engine", name),
                "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
            )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)

    def test_recipes_detector_py_still_out_of_scope(self):
        # fencepost/RECIPES/*/detector.py stayed deliberately out of
        # scope in task 671 (legitimately parallel functions by design)
        # and task 674's widening did not touch that call -- confirmed
        # here so a future widening of the RECIPES glob is a conscious
        # choice, not an accidental side effect of this task's own edit.
        for slug in ("recipe-a", "recipe-b"):
            _write(
                os.path.join(self.orita, "fencepost", "RECIPES", slug, "detector.py"),
                "from datetime import datetime, timezone\n\n" + _REAL_DUPLICATE_BODY.format(name="_parse"),
            )
        violations = dfc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])


class AllowedDuplicateCase(unittest.TestCase):
    """Task 674: proves `_ALLOWED_DUPLICATES` actually suppresses its one
    seeded, real, deliberate two-copy pair on the live tree -- and that
    the exclusion is scoped to exactly those two files, not to the hash
    everywhere it might appear."""

    def test_live_seeded_pair_is_real_and_shares_the_body_hash(self):
        real_root = dfc.ROOT
        bodies_a = dict(
            (name, h) for name, h, _ in dfc._function_bodies(
                os.path.join(real_root, "tools", "network_boundary_check.py")
            )
        )
        bodies_b = dict(
            (name, h) for name, h, _ in dfc._function_bodies(
                os.path.join(
                    real_root, "fencepost", "seam_engine", "src", "seam_engine", "recipes.py"
                )
            )
        )
        self.assertIn("_dynamic_import_target", bodies_a)
        self.assertIn("_dynamic_import_target", bodies_b)
        shared_hash = bodies_a["_dynamic_import_target"]
        self.assertEqual(shared_hash, bodies_b["_dynamic_import_target"])
        self.assertIn(shared_hash, dfc._ALLOWED_DUPLICATES)

    def test_seeded_hash_is_a_real_sha256_hex_digest(self):
        for h in dfc._ALLOWED_DUPLICATES:
            self.assertEqual(len(h), 64, f"{h!r} is not a 64-char hex digest")
            int(h, 16)  # raises ValueError if not valid hex

    def test_allowed_pair_widened_to_a_third_file_is_still_flagged(self):
        # The allow-list is a closed SET of files, not a blanket pass for
        # the hash. A third file sharing the exact same seeded body is a
        # real, new duplicate the seeded exception must not silently
        # swallow. Extracts the real function's exact source segment
        # (via ast.get_source_segment) from the two real, live seeded
        # files, so the fixture body is provably identical AST, not a
        # hand-retyped approximation that might drift from the real one.
        real_root = dfc.ROOT
        nb_path = os.path.join(real_root, "tools", "network_boundary_check.py")
        recipes_path = os.path.join(
            real_root, "fencepost", "seam_engine", "src", "seam_engine", "recipes.py"
        )
        with open(nb_path, encoding="utf-8") as f:
            nb_source = f.read()
        with open(recipes_path, encoding="utf-8") as f:
            recipes_source = f.read()
        nb_tree = ast.parse(nb_source)
        func_src = None
        for node in ast.walk(nb_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_dynamic_import_target":
                func_src = ast.get_source_segment(nb_source, node)
                break
        self.assertIsNotNone(func_src)

        orita = tempfile.mkdtemp()
        self.addCleanup(_rm, orita)
        os.makedirs(os.path.join(orita, "tools"), exist_ok=True)
        os.makedirs(
            os.path.join(orita, "fencepost", "seam_engine", "src", "seam_engine"), exist_ok=True
        )
        _write(os.path.join(orita, "tools", "network_boundary_check.py"), nb_source)
        _write(
            os.path.join(orita, "fencepost", "seam_engine", "src", "seam_engine", "recipes.py"),
            recipes_source,
        )
        # A third, unseeded file, same body under a distinct name (task
        # 513's own name-blind proof still holds here).
        _write(
            os.path.join(orita, "tools", "fixture_third_copy.py"),
            "import ast\n\n" + func_src.replace("_dynamic_import_target", "_third_copy", 1) + "\n",
        )
        violations = dfc.find_violations(orita_dir=orita)
        self.assertEqual(len(violations), 1)
        files = {rel for rel, _name, _lineno in violations[0]["locations"]}
        self.assertEqual(
            files,
            {
                os.path.join("tools", "network_boundary_check.py"),
                os.path.join("fencepost", "seam_engine", "src", "seam_engine", "recipes.py"),
                os.path.join("tools", "fixture_third_copy.py"),
            },
        )


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
