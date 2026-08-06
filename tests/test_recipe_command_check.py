"""Task 571. Proves tools/recipe_command_check.py actually executes every
recipe README's own "Run it yourself" block and catches the three shapes
a static text/link check could never catch: no block at all, a block that
doesn't start where the README claims, and a block that runs but fails or
returns something other than the shape its own run_recipe_scan promises.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

_SEAM_ENGINE_SRC = os.path.join(ROOT, "fencepost", "seam_engine", "src")
if _SEAM_ENGINE_SRC not in sys.path:
    sys.path.insert(0, _SEAM_ENGINE_SRC)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


rcc = _load("recipe_command_check", os.path.join(ROOT, "tools", "recipe_command_check.py"))

_GOOD_JSON = {
    "generated_at": "2026-08-06T00:00:00+00:00",
    "source": "fixture",
    "confidence_bar": 0.7,
    "separation_margin": 0.15,
    "primary_gap": None,
    "tail": [],
    "excluded": [],
}


def _write_recipe(fencepost_root, slug, detector_body, *, with_run_block=True, block_cd_line="cd fencepost/seam_engine"):
    """A minimal, schema-valid recipe.json + README.md + detector.py under
    <fencepost_root>/RECIPES/<slug>/, real enough for discover_recipes()
    to accept it and for check_recipe_commands() to actually try to run
    its own documented command."""
    recipe_dir = os.path.join(fencepost_root, "RECIPES", slug)
    os.makedirs(recipe_dir, exist_ok=True)
    manifest = {
        "slug": slug,
        "title": f"{slug} title",
        "author": "ogun",
        "description": f"{slug} description",
        "toolkit": "github",
        "scopes": ["GetRepository"],
        "fixture": "fixtures/dummy",
        "detector_file": "detector.py",
        "entrypoint": "run_recipe_scan",
        "confidence_notes": "fixed 0.80",
    }
    with open(os.path.join(recipe_dir, "recipe.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    with open(os.path.join(recipe_dir, "detector.py"), "w", encoding="utf-8") as f:
        f.write(detector_body)

    if with_run_block:
        readme = (
            f"# {slug}\n\nRun it yourself:\n\n```\n{block_cd_line}\n"
            f"python3 ../RECIPES/{slug}/detector.py\n```\n"
        )
    else:
        readme = f"# {slug}\n\nno run section here.\n"
    with open(os.path.join(recipe_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)


class RunItYourselfBlockParsingCase(unittest.TestCase):
    def test_extracts_the_fenced_block(self):
        text = "Run it yourself:\n\n```\ncd fencepost/seam_engine\nPYTHONPATH=src uv run python x.py\n```\n"
        block = rcc._run_it_yourself_block(text)
        self.assertEqual(block, "cd fencepost/seam_engine\nPYTHONPATH=src uv run python x.py")

    def test_missing_block_returns_none(self):
        self.assertIsNone(rcc._run_it_yourself_block("# no run section here\n"))


class CheckRecipeCommandsCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fencepost_root = self._tmp.name
        self.seam_engine_dir = os.path.join(self.fencepost_root, "seam_engine")
        os.makedirs(self.seam_engine_dir, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _check(self):
        return rcc.check_recipe_commands(
            fencepost_root=self.fencepost_root,
            seam_engine_dir=self.seam_engine_dir,
            timeout=15,
        )

    def test_a_real_working_command_is_clean(self):
        _write_recipe(
            self.fencepost_root, "good-one",
            f"import json\nprint(json.dumps({_GOOD_JSON!r}))\n",
        )
        result = self._check()
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["checked_count"], 1)
        self.assertEqual(result["real_count"], 1)

    def test_no_run_it_yourself_block_is_named(self):
        _write_recipe(self.fencepost_root, "no-block", "print('unused')\n", with_run_block=False)
        result = self._check()
        self.assertFalse(result["clean"])
        self.assertIn("no-block", result["no_block"])

    def test_block_not_starting_with_the_documented_cd_is_named(self):
        _write_recipe(
            self.fencepost_root, "wrong-shape",
            "print('unused')\n",
            block_cd_line="cd somewhere/else",
        )
        result = self._check()
        self.assertFalse(result["clean"])
        self.assertIn("wrong-shape", result["unexpected_shape"])

    def test_a_command_that_exits_nonzero_is_named_with_its_stderr(self):
        _write_recipe(
            self.fencepost_root, "broken-cmd",
            "import sys\nsys.stderr.write('boom: ModuleNotFoundError\\n')\nsys.exit(1)\n",
        )
        result = self._check()
        self.assertFalse(result["clean"])
        slugs = [p["slug"] for p in result["command_failed"]]
        self.assertIn("broken-cmd", slugs)
        reason = next(p["reason"] for p in result["command_failed"] if p["slug"] == "broken-cmd")
        self.assertIn("boom", reason)

    def test_non_json_stdout_is_named_malformed(self):
        _write_recipe(self.fencepost_root, "not-json", "print('not json at all')\n")
        result = self._check()
        self.assertFalse(result["clean"])
        slugs = [p["slug"] for p in result["malformed_output"]]
        self.assertIn("not-json", slugs)

    def test_json_missing_expected_keys_is_named_malformed(self):
        _write_recipe(
            self.fencepost_root, "thin-json",
            "import json\nprint(json.dumps({'primary_gap': None}))\n",
        )
        result = self._check()
        self.assertFalse(result["clean"])
        slugs = [p["slug"] for p in result["malformed_output"]]
        self.assertIn("thin-json", slugs)

    def test_a_recipe_with_no_readme_at_all_is_silently_skipped(self):
        # recipe_readme_check.py's own missing_readme already names this
        # gap; this check's job starts only once a block exists to run.
        recipe_dir = os.path.join(self.fencepost_root, "RECIPES", "no-readme")
        os.makedirs(recipe_dir, exist_ok=True)
        manifest = {
            "slug": "no-readme", "title": "t", "author": "a", "description": "d",
            "toolkit": "github", "scopes": ["GetRepository"], "fixture": "fixtures/x",
            "detector_file": "detector.py", "entrypoint": "run_recipe_scan",
            "confidence_notes": "fixed 0.8",
        }
        with open(os.path.join(recipe_dir, "recipe.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        with open(os.path.join(recipe_dir, "detector.py"), "w", encoding="utf-8") as f:
            f.write("print('unused')\n")
        result = self._check()
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["checked_count"], 0)
        self.assertEqual(result["real_count"], 1)


def _write_recipe_with_command(fencepost_root, slug, command_lines):
    """Like `_write_recipe`, but the caller controls every line of the
    documented block after the `cd` line verbatim -- needed to write a
    recipe whose command actually invokes `uv` (real recipes' shape),
    unlike `_write_recipe`'s own fixtures, which always document a plain
    `python3` command on purpose."""
    recipe_dir = os.path.join(fencepost_root, "RECIPES", slug)
    os.makedirs(recipe_dir, exist_ok=True)
    manifest = {
        "slug": slug, "title": f"{slug} title", "author": "ogun",
        "description": f"{slug} description", "toolkit": "github",
        "scopes": ["GetRepository"], "fixture": "fixtures/dummy",
        "detector_file": "detector.py", "entrypoint": "run_recipe_scan",
        "confidence_notes": "fixed 0.80",
    }
    with open(os.path.join(recipe_dir, "recipe.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    with open(os.path.join(recipe_dir, "detector.py"), "w", encoding="utf-8") as f:
        f.write("print('unused -- this fixture is never meant to actually run')\n")
    block = "\n".join(["cd fencepost/seam_engine", *command_lines])
    with open(os.path.join(recipe_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(f"# {slug}\n\nRun it yourself:\n\n```\n{block}\n```\n")


class UvUnavailableCase(unittest.TestCase):
    """Task 588. `dawn-run.yml`'s `the-oath` job installs only PyYAML
    (task 404's own lean-root-job boundary) -- no `uv`. A recipe whose
    documented command actually invokes `uv` must not read as BROKEN
    just because that one external tool isn't on PATH there; same class
    of fix `badge_freshness_check.py` (task 425) already made for a
    missing `arcade-mcp-server`, but scoped per command rather than a
    blanket skip -- a fixture recipe that never mentions `uv` at all
    (like every other fixture in this file) still gets checked for real
    even when `uv` is absent from the machine running the test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fencepost_root = self._tmp.name
        self.seam_engine_dir = os.path.join(self.fencepost_root, "seam_engine")
        os.makedirs(self.seam_engine_dir, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _check(self):
        return rcc.check_recipe_commands(
            fencepost_root=self.fencepost_root,
            seam_engine_dir=self.seam_engine_dir,
            timeout=15,
        )

    def test_uv_command_skipped_clean_when_uv_missing(self):
        _write_recipe_with_command(
            self.fencepost_root, "needs-uv",
            ["PYTHONPATH=src uv run python detector.py"],
        )
        with mock.patch.object(rcc.shutil, "which", return_value=None):
            result = self._check()
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["checked_count"], 0)
        self.assertEqual(result["real_count"], 1)
        self.assertIn("needs-uv", result["skipped_no_uv"])

    def test_uv_command_still_runs_for_real_when_uv_present(self):
        _write_recipe_with_command(
            self.fencepost_root, "needs-uv",
            ["PYTHONPATH=src uv run python detector.py"],
        )
        with mock.patch.object(rcc.shutil, "which", return_value="/usr/bin/uv"):
            # `uv` "present" per the mock, but not actually runnable in
            # this sandbox -- the point of this test is only that the
            # command is attempted (not silently skipped), so a real
            # subprocess failure is the expected, correct outcome here.
            result = self._check()
        self.assertEqual(result["status"], "checked")
        self.assertEqual(result["checked_count"], 1)
        self.assertEqual(result["skipped_no_uv"], [])

    def test_non_uv_command_still_checked_for_real_even_when_uv_missing(self):
        _write_recipe(
            self.fencepost_root, "plain-python",
            f"import json\nprint(json.dumps({_GOOD_JSON!r}))\n",
        )
        with mock.patch.object(rcc.shutil, "which", return_value=None):
            result = self._check()
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["status"], "checked")
        self.assertEqual(result["checked_count"], 1)
        self.assertEqual(result["skipped_no_uv"], [])


class FormatResultCase(unittest.TestCase):
    def test_clean_line_names_the_counts(self):
        line = rcc.format_result({"clean": True, "status": "checked", "checked_count": 51, "real_count": 51})
        self.assertIn("51/51", line)

    def test_unavailable_line_names_it_explicitly(self):
        line = rcc.format_result({
            "clean": True, "status": "unavailable",
            "real_count": 0, "checked_count": 0,
        })
        self.assertIn("unavailable", line)
        self.assertIn("uv", line)

    def test_broken_line_names_every_problem_kind(self):
        line = rcc.format_result({
            "clean": False,
            "no_block": ["a"],
            "unexpected_shape": ["b"],
            "command_failed": [{"slug": "c", "reason": "exit 1: boom"}],
            "malformed_output": [{"slug": "d", "reason": "not valid JSON"}],
        })
        self.assertIn("a", line)
        self.assertIn("b", line)
        self.assertIn("c (exit 1: boom)", line)
        self.assertIn("d (not valid JSON)", line)


class LiveRealRepoCase(unittest.TestCase):
    """The same live, unmocked full-sweep discipline test_recipes.py's own
    test_all_real_shipped_recipes_pass_the_oath_coverage_check already
    holds -- every real recipe's own documented command, actually run.

    Task 588: `uv` genuinely isn't installed in `dawn-run.yml`'s
    `the-oath` job (this test's own root `tests/` suite runs there), so
    a bare unmocked call against the real 51 recipes -- every one
    documenting a `uv run` command -- gets every one skipped there, not
    checked. Either every real recipe's command actually ran clean, or
    every one was honestly skipped for the one documented environment
    reason; both are `clean`, the same either/or
    `test_badge_freshness_check.py`'s own
    `test_the_real_committed_badge_is_not_currently_stale` already holds
    for a missing `arcade-mcp-server`. A real `checked_count` short of
    `real_count` with nothing in `skipped_no_uv` accounting for the gap
    would still mean something genuinely didn't run and wasn't named --
    that stays a real failure here, not silently waved through."""

    def test_every_real_shipped_recipe_command_runs_clean(self):
        result = rcc.check_recipe_commands()
        self.assertTrue(result["clean"], result)
        self.assertGreater(result["real_count"], 0)
        self.assertEqual(
            result["checked_count"] + len(result["skipped_no_uv"]),
            result["real_count"],
        )
        if result["status"] == "checked":
            self.assertEqual(result["checked_count"], result["real_count"])
        else:
            self.assertIn(result["status"], ("unavailable", "partially_unavailable"))


if __name__ == "__main__":
    unittest.main()
