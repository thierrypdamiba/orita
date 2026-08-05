"""Task 554. Proves tools/site_recipe_check.py cross-checks
docs/fencepost/index.html's Community recipes section against the live
seam_engine.recipes.discover_recipes() tree in BOTH directions:
every real recipe is linked, every link points at a real recipe, and a
link's own href slug agrees with its own anchor text -- the reverse
direction tests/test_fencepost_site_recipes.py's loose substring match
never covered for the Wall, the same gap recipe_readme_check.py (task 426)
already closed for fencepost/README.md.
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


src = _load("site_recipe_check", os.path.join(ROOT, "tools", "site_recipe_check.py"))

_SAMPLE_SITE = """<html><body>
<section class="prose">
<h2>Community recipes</h2>
<p>Some intro prose.</p>
<p><b><a href="https://github.com/thierrypdamiba/orita/tree/main/fencepost/RECIPES/alpha-gap">alpha-gap</a></b>
is the first.<br>
<b><a href="https://github.com/thierrypdamiba/orita/tree/main/fencepost/RECIPES/beta-gap">beta-gap</a></b>
is the second.</p>
</section>
<section class="prose">
<h2>Run your own</h2>
<p><a href="https://github.com/thierrypdamiba/orita/tree/main/fencepost/RECIPES/gamma-gap">gamma-gap</a> not this section's problem.</p>
</section>
</body></html>
"""


def _write_recipe(fencepost_root, slug):
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
        section = src._community_recipes_section(_SAMPLE_SITE)
        self.assertIn("alpha-gap", section)
        self.assertIn("beta-gap", section)
        self.assertNotIn("gamma-gap", section)

    def test_missing_header_returns_empty_string_not_error(self):
        section = src._community_recipes_section("<html><body>no matching section</body></html>")
        self.assertEqual(section, "")

    def test_linked_recipes_extracts_href_and_text_pairs(self):
        section = src._community_recipes_section(_SAMPLE_SITE)
        links = src._linked_recipes(section)
        self.assertEqual(links, [("alpha-gap", "alpha-gap"), ("beta-gap", "beta-gap")])

    def test_a_link_outside_the_section_is_never_counted(self):
        section = src._community_recipes_section(_SAMPLE_SITE)
        links = src._linked_recipes(section)
        slugs = {h for h, _t in links}
        self.assertNotIn("gamma-gap", slugs)


class CrossCheckCase(unittest.TestCase):
    def _fixture(self, site_text, slugs):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, tmpdir, ignore_errors=True)
        for slug in slugs:
            _write_recipe(tmpdir, slug)
        site_path = os.path.join(tmpdir, "index.html")
        with open(site_path, "w", encoding="utf-8") as f:
            f.write(site_text)
        return site_path, tmpdir

    def test_matching_site_and_disk_is_clean(self):
        site_path, fencepost_root = self._fixture(_SAMPLE_SITE, ["alpha-gap", "beta-gap"])
        result = src.check_site_recipe_readme(site_path=site_path, fencepost_root=fencepost_root)
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_from_site"], [])
        self.assertEqual(result["stale_in_site"], [])
        self.assertEqual(result["mismatched_links"], [])
        self.assertEqual(result["real_count"], 2)
        self.assertEqual(result["linked_count"], 2)

    def test_real_recipe_never_linked_is_caught(self):
        """The direction test_fencepost_site_recipes.py's own
        test_names_all_real_recipes already covers -- kept here so the
        HOURLY RITUAL sees it too, not only the test suite."""
        site_path, fencepost_root = self._fixture(_SAMPLE_SITE, ["alpha-gap", "beta-gap", "delta-gap"])
        result = src.check_site_recipe_readme(site_path=site_path, fencepost_root=fencepost_root)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_site"], ["delta-gap"])
        self.assertEqual(result["stale_in_site"], [])

    def test_dead_link_to_a_removed_recipe_is_caught(self):
        """The direction NOTHING checked before this task: a recipe
        directory no longer on disk, but its link still sits in the site's
        own published prose -- exactly what a bad merge or an overbroad
        cleanup pass would produce, and exactly the shape
        test_names_all_real_recipes' own forward-only substring match
        could never notice. Reproduces the real live bug found this hour
        against fencepost/RECIPES/stale-branch-no-pr/ (confirmed via a
        temporary mv/restore against the real repo before this fix
        existed: recipe_readme_check.py caught it for fencepost/README.md,
        site_link_check.py and test_fencepost_site_recipes.py both stayed
        clean for the Wall)."""
        site_path, fencepost_root = self._fixture(_SAMPLE_SITE, ["alpha-gap"])  # beta-gap removed
        result = src.check_site_recipe_readme(site_path=site_path, fencepost_root=fencepost_root)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_site"], [])
        self.assertEqual(result["stale_in_site"], ["beta-gap"])

    def test_mismatched_link_href_and_text_is_caught(self):
        site_text = """<html><body><section class="prose">
<h2>Community recipes</h2>
<p><a href="https://github.com/thierrypdamiba/orita/tree/main/fencepost/RECIPES/alpha-gap">beta-gap</a> typo'd.</p>
</section></body></html>
"""
        site_path, fencepost_root = self._fixture(site_text, ["alpha-gap", "beta-gap"])
        result = src.check_site_recipe_readme(site_path=site_path, fencepost_root=fencepost_root)
        self.assertFalse(result["clean"])
        self.assertEqual(result["mismatched_links"], [("alpha-gap", "beta-gap")])

    def test_no_real_recipes_and_empty_section_is_clean(self):
        site_text = '<html><body><section class="prose"><h2>Community recipes</h2><p>none yet</p></section></body></html>'
        site_path, fencepost_root = self._fixture(site_text, [])
        result = src.check_site_recipe_readme(site_path=site_path, fencepost_root=fencepost_root)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real_count"], 0)


class FormatResultCase(unittest.TestCase):
    def test_clean_result_names_the_real_count(self):
        text = src.format_result({
            "clean": True, "real_count": 45, "linked_count": 45,
            "missing_from_site": [], "stale_in_site": [], "mismatched_links": [],
        })
        self.assertIn("45 real recipe(s)", text)
        self.assertIn("clean", text)

    def test_broken_result_names_every_problem_kind(self):
        text = src.format_result({
            "clean": False,
            "real_count": 2,
            "linked_count": 2,
            "missing_from_site": ["gamma-gap"],
            "stale_in_site": ["beta-gap"],
            "mismatched_links": [("alpha-gap", "beta-gap")],
        })
        self.assertIn("BROKEN", text)
        self.assertIn("gamma-gap", text)
        self.assertIn("beta-gap", text)
        self.assertIn("alpha-gap", text)


class RealRepoCase(unittest.TestCase):
    """The real point: today's real docs/fencepost/index.html names every
    real recipe discover_recipes() finds, and every link it carries still
    resolves -- and a temp copy with one recipe's link removed flips the
    check from clean to broken and back, proving the reverse direction
    actually works against the real live tree, not only a synthetic
    fixture."""

    def test_real_site_and_real_recipes_agree(self):
        result = src.check_site_recipe_readme()
        self.assertTrue(
            result["clean"],
            msg=f"missing={result['missing_from_site']} stale={result['stale_in_site']} "
                f"mismatched={result['mismatched_links']}",
        )
        self.assertGreater(result["real_count"], 0)

    def test_removing_one_real_recipe_link_from_a_temp_copy_flips_clean_to_broken_and_back(self):
        with open(src.DEFAULT_SITE_PATH, encoding="utf-8") as f:
            real_text = f.read()
        from seam_engine.recipes import discover_recipes  # noqa: PLC0415
        from pathlib import Path  # noqa: PLC0415
        victim_slug = sorted(m.slug for m in discover_recipes(Path(src.DEFAULT_FENCEPOST_ROOT)))[0]
        with tempfile.TemporaryDirectory() as tmpdir:
            broken_path = os.path.join(tmpdir, "index.html")
            with open(broken_path, "w", encoding="utf-8") as f:
                f.write(real_text.replace(
                    f'<a href="https://github.com/thierrypdamiba/orita/tree/main/fencepost/RECIPES/{victim_slug}">'
                    f'{victim_slug}</a>',
                    "",
                ))
            broken_result = src.check_site_recipe_readme(
                site_path=broken_path, fencepost_root=src.DEFAULT_FENCEPOST_ROOT
            )
            self.assertFalse(broken_result["clean"])
            self.assertIn(victim_slug, broken_result["missing_from_site"])

            restored_path = os.path.join(tmpdir, "index-restored.html")
            with open(restored_path, "w", encoding="utf-8") as f:
                f.write(real_text)
            restored_result = src.check_site_recipe_readme(
                site_path=restored_path, fencepost_root=src.DEFAULT_FENCEPOST_ROOT
            )
            self.assertTrue(restored_result["clean"])


if __name__ == "__main__":
    unittest.main()
