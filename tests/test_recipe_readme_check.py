"""Task 426. Proves tools/recipe_readme_check.py cross-checks
fencepost/README.md's Community recipes section against the live
seam_engine.recipes.discover_recipes() tree in BOTH directions:
every real recipe is linked, every link points at a real recipe, and a
link's own bracket text agrees with its own href -- the reverse
direction tests/test_fencepost_site_recipes.py's loose substring match
never covered.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest

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


rrc = _load("recipe_readme_check", os.path.join(ROOT, "tools", "recipe_readme_check.py"))

_SAMPLE_SECTION = """## Community recipes

Some intro prose.

[`RECIPES/alpha-gap/`](RECIPES/alpha-gap/) is the first.
[`RECIPES/beta-gap/`](RECIPES/beta-gap/) is the second.

## Run your own

Not this section's problem.
"""


def _write_recipe(fencepost_root, slug):
    """A minimal, schema-valid recipe.json under <fencepost_root>/RECIPES/<slug>/ --
    enough for discover_recipes() to accept it without ever needing a real
    detector.py (discover_recipes only reads the manifest, never imports
    the detector)."""
    recipe_dir = os.path.join(fencepost_root, "RECIPES", slug)
    os.makedirs(recipe_dir, exist_ok=True)
    manifest = {
        "slug": slug,
        "title": f"{slug} title",
        "author": "nisaba",
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


class SectionParsingCase(unittest.TestCase):
    def test_extracts_bounded_section_only(self):
        section = rrc._community_recipes_section(_SAMPLE_SECTION)
        self.assertIn("alpha-gap", section)
        self.assertIn("beta-gap", section)
        self.assertNotIn("Not this section's problem", section)

    def test_missing_header_returns_empty_string_not_error(self):
        section = rrc._community_recipes_section("# some doc with no matching section\n")
        self.assertEqual(section, "")

    def test_linked_recipes_extracts_text_and_href_pairs(self):
        section = rrc._community_recipes_section(_SAMPLE_SECTION)
        links = rrc._linked_recipes(section)
        self.assertEqual(links, [("alpha-gap", "alpha-gap"), ("beta-gap", "beta-gap")])

    def test_a_link_outside_the_section_is_never_counted(self):
        text = _SAMPLE_SECTION + "\n[`RECIPES/gamma-gap/`](RECIPES/gamma-gap/) in another section entirely.\n"
        section = rrc._community_recipes_section(text)
        links = rrc._linked_recipes(section)
        slugs = {h for _t, h in links}
        self.assertNotIn("gamma-gap", slugs)


class CrossCheckCase(unittest.TestCase):
    def _fixture(self, readme_text, slugs):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, tmpdir, ignore_errors=True)
        for slug in slugs:
            _write_recipe(tmpdir, slug)
        readme_path = os.path.join(tmpdir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_text)
        return readme_path, tmpdir

    def test_matching_readme_and_disk_is_clean(self):
        readme_path, fencepost_root = self._fixture(_SAMPLE_SECTION, ["alpha-gap", "beta-gap"])
        result = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_from_readme"], [])
        self.assertEqual(result["stale_in_readme"], [])
        self.assertEqual(result["mismatched_links"], [])
        self.assertEqual(result["real_count"], 2)
        self.assertEqual(result["linked_count"], 2)

    def test_real_recipe_never_linked_is_caught(self):
        """The direction test_fencepost_site_recipes.py's own
        test_names_all_real_recipes already covers -- kept here so the
        HOURLY RITUAL sees it too, not only the test suite."""
        readme_path, fencepost_root = self._fixture(_SAMPLE_SECTION, ["alpha-gap", "beta-gap", "gamma-gap"])
        result = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_readme"], ["gamma-gap"])
        self.assertEqual(result["stale_in_readme"], [])

    def test_dead_link_to_a_removed_recipe_is_caught(self):
        """The direction NOTHING checked before this task: a recipe
        directory no longer on disk, but its link still sits in the
        README's prose -- exactly what a bad merge or an overbroad
        cleanup pass would produce, and exactly the shape
        test_names_all_real_recipes' own forward-only substring match
        could never notice."""
        readme_path, fencepost_root = self._fixture(_SAMPLE_SECTION, ["alpha-gap"])  # beta-gap removed
        result = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_readme"], [])
        self.assertEqual(result["stale_in_readme"], ["beta-gap"])

    def test_mismatched_link_text_and_href_is_caught(self):
        section = """## Community recipes

[`RECIPES/alpha-gap/`](RECIPES/beta-gap/) is a typo'd link.

## Run your own
"""
        readme_path, fencepost_root = self._fixture(section, ["alpha-gap", "beta-gap"])
        result = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertFalse(result["clean"])
        self.assertEqual(result["mismatched_links"], [("alpha-gap", "beta-gap")])

    def test_no_real_recipes_and_empty_section_is_clean(self):
        readme_path, fencepost_root = self._fixture("## Community recipes\n\nnone yet\n\n## Run your own\n", [])
        result = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real_count"], 0)


class FormatResultCase(unittest.TestCase):
    def test_clean_result_names_the_real_count(self):
        text = rrc.format_result({"clean": True, "real_count": 26, "linked_count": 26,
                                   "missing_from_readme": [], "stale_in_readme": [], "mismatched_links": []})
        self.assertIn("26 real recipe(s)", text)
        self.assertIn("clean", text)

    def test_broken_result_names_every_problem_kind(self):
        text = rrc.format_result({
            "clean": False,
            "real_count": 2,
            "linked_count": 2,
            "missing_from_readme": ["gamma-gap"],
            "stale_in_readme": ["beta-gap"],
            "mismatched_links": [("alpha-gap", "beta-gap")],
        })
        self.assertIn("BROKEN", text)
        self.assertIn("gamma-gap", text)
        self.assertIn("beta-gap", text)
        self.assertIn("alpha-gap", text)


class RealRepoCase(unittest.TestCase):
    """The real point: today's real fencepost/README.md names every real
    recipe discover_recipes() finds, and every link it carries still
    resolves -- and a temp copy with one recipe's directory removed flips
    the check from clean to broken and back, proving the reverse
    direction actually works against the real live tree, not only a
    synthetic fixture."""

    def test_real_readme_and_real_recipes_agree(self):
        result = rrc.check_recipe_readme()
        self.assertTrue(
            result["clean"],
            msg=f"missing={result['missing_from_readme']} stale={result['stale_in_readme']} "
                f"mismatched={result['mismatched_links']}",
        )
        self.assertGreater(result["real_count"], 0)

    def test_removing_one_real_recipe_link_from_a_temp_copy_flips_clean_to_broken_and_back(self):
        with open(rrc.DEFAULT_README_PATH, encoding="utf-8") as f:
            real_text = f.read()
        # Pick any real, currently-linked slug to strip out of a temp copy.
        from seam_engine.recipes import discover_recipes  # noqa: PLC0415
        from pathlib import Path  # noqa: PLC0415
        victim_slug = sorted(m.slug for m in discover_recipes(Path(rrc.DEFAULT_FENCEPOST_ROOT)))[0]
        with tempfile.TemporaryDirectory() as tmpdir:
            broken_path = os.path.join(tmpdir, "README.md")
            with open(broken_path, "w", encoding="utf-8") as f:
                f.write(real_text.replace(
                    f"[`RECIPES/{victim_slug}/`](RECIPES/{victim_slug}/)",
                    "",
                ))
            broken_result = rrc.check_recipe_readme(
                readme_path=broken_path, fencepost_root=rrc.DEFAULT_FENCEPOST_ROOT
            )
            self.assertFalse(broken_result["clean"])
            self.assertIn(victim_slug, broken_result["missing_from_readme"])

            restored_path = os.path.join(tmpdir, "README-restored.md")
            with open(restored_path, "w", encoding="utf-8") as f:
                f.write(real_text)
            restored_result = rrc.check_recipe_readme(
                readme_path=restored_path, fencepost_root=rrc.DEFAULT_FENCEPOST_ROOT
            )
            self.assertTrue(restored_result["clean"])


if __name__ == "__main__":
    unittest.main()
