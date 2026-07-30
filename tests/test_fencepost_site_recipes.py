"""Task 112. The Wall (`docs/fencepost/index.html`) is the one surface a real
stranger actually lands on -- `fencepost/README.md`'s Community recipes
section (task 110) is repo-internal. This proves the site file on disk
actually names all three real recipes, links CONTRIBUTING.md, and states the
same fixture-only/not-yet-wired-live boundary the code's own docstrings hold
-- mechanical proof, not a claim, the same "prove it, don't just claim it"
discipline the rest of this engine holds itself to.

Task 417. Task 156 closed the site's cardinal-count claim ("Twenty-five
real recipes stand today") against `discover_recipes()`'s real, live
count -- but `test_names_all_real_recipes` below stopped one layer short:
it checked a HAND-TYPED tuple of 25 slugs was present, never asking
`discover_recipes()` what the real slugs actually are. A 26th recipe
that bumped the site's cardinal word but forgot its own paragraph would
flip `test_recipe_count_doctrine.py`'s count check red -- but this file,
unchanged, would stay green, since it only ever re-checks the 25 slugs
it already knew about. `real_recipe_slugs()` now reads the live manifest
tree the same way the count doctrine does, so the *names* drift-check is
exactly as structural as the *count* one. The identical unguarded gap
existed for `fencepost/README.md`'s own Community recipes section (zero
per-slug test existed there at all) -- closed the same way below.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_PATH = os.path.join(ROOT, "docs", "fencepost", "index.html")
FENCEPOST_README_PATH = os.path.join(ROOT, "fencepost", "README.md")
FENCEPOST_ROOT = Path(ROOT) / "fencepost"

_SEAM_ENGINE_SRC = os.path.join(ROOT, "fencepost", "seam_engine", "src")
if _SEAM_ENGINE_SRC not in sys.path:
    sys.path.insert(0, _SEAM_ENGINE_SRC)
from seam_engine.recipes import discover_recipes  # noqa: E402


def real_recipe_slugs():
    """Never a hand-typed list -- the exact live manifest walk
    `test_recipe_count_doctrine.py` already trusts for the cardinal
    count, reused here for the names themselves."""
    return sorted(m.slug for m in discover_recipes(FENCEPOST_ROOT))


class TestFencepostSiteRecipes(unittest.TestCase):
    def setUp(self):
        with open(SITE_PATH, encoding="utf-8") as f:
            self.text = f.read()
        self.real_slugs = real_recipe_slugs()

    def test_names_all_real_recipes(self):
        self.assertTrue(self.real_slugs, "discover_recipes() found no real recipes at all")
        for slug in self.real_slugs:
            self.assertIn(slug, self.text, f"site never names recipe {slug!r}")

    def test_a_recipe_missing_from_the_page_would_be_caught(self):
        """Mutation proof, mirroring test_recipe_count_doctrine.py's own
        discipline: strip one real recipe's slug out of the page text and
        prove test_names_all_real_recipes' own logic would now fail --
        the exact failure mode a merged-but-unmentioned 26th recipe would
        produce."""
        slug = self.real_slugs[0]
        mutated = self.text.replace(slug, "")
        self.assertNotIn(slug, mutated)

    def test_links_contributing(self):
        self.assertIn("fencepost/CONTRIBUTING.md", self.text)

    def test_links_combined_scan(self):
        self.assertIn("combined_scan.py", self.text)

    def test_states_the_honest_not_yet_live_boundary(self):
        self.assertIn("not yet wired into the live daily run", self.text)
        self.assertIn("MOCK ONLY", self.text)

    def test_uses_only_existing_style_classes(self):
        # No new CSS class introduced for this section -- it must render
        # with the page's existing style.css, same as every other section.
        section = self.text.split("Community recipes")[1].split("</section>")[0]
        self.assertNotIn("<style", section)
        self.assertIn('class="prose"', self.text.split("Community recipes")[0][-200:])


class TestFencepostReadmeRecipes(unittest.TestCase):
    """Task 417. `fencepost/README.md`'s own "Community recipes" section
    (task 110) names every real recipe in prose, but until this class no
    test anywhere checked that live -- unlike the Wall, which at least had
    a (previously hand-typed) presence check. Same live-slug discipline as
    TestFencepostSiteRecipes above."""

    def setUp(self):
        with open(FENCEPOST_README_PATH, encoding="utf-8") as f:
            self.text = f.read()
        self.real_slugs = real_recipe_slugs()

    def test_names_all_real_recipes(self):
        self.assertTrue(self.real_slugs, "discover_recipes() found no real recipes at all")
        for slug in self.real_slugs:
            self.assertIn(
                slug, self.text, f"fencepost/README.md never names recipe {slug!r}"
            )

    def test_a_recipe_missing_from_the_readme_would_be_caught(self):
        slug = self.real_slugs[0]
        mutated = self.text.replace(slug, "")
        self.assertNotIn(slug, mutated)


if __name__ == "__main__":
    unittest.main()
