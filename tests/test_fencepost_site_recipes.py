"""Task 112. The Wall (`docs/fencepost/index.html`) is the one surface a real
stranger actually lands on -- `fencepost/README.md`'s Community recipes
section (task 110) is repo-internal. This proves the site file on disk
actually names all three real recipes, links CONTRIBUTING.md, and states the
same fixture-only/not-yet-wired-live boundary the code's own docstrings hold
-- mechanical proof, not a claim, the same "prove it, don't just claim it"
discipline the rest of this engine holds itself to.
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_PATH = os.path.join(ROOT, "docs", "fencepost", "index.html")


class TestFencepostSiteRecipes(unittest.TestCase):
    def setUp(self):
        with open(SITE_PATH, encoding="utf-8") as f:
            self.text = f.read()

    def test_names_all_real_recipes(self):
        for slug in (
            "example-release-vs-changelog",
            "merged-pr-issue-still-open",
            "release-not-tweeted",
            "dangling-issue-reference",
            "contributor-thanked-not-credited",
            "issue-closed-pr-still-open",
            "duplicate-issue-still-open",
            "commit-closes-keyword-issue-still-open",
            "release-claims-unmerged-pr",
            "milestone-closed-issue-still-open",
            "milestone-closed-pr-still-open",
            "merged-pr-never-released",
            "release-claims-unfixed-issue",
            "milestone-closed-never-released",
            "readme-credited-not-thanked",
            "release-claims-open-milestone",
            "issue-closed-never-released",
            "mention-dangling-reference",
            "milestone-closed-not-tweeted",
            "merged-pr-not-tweeted",
        ):
            self.assertIn(slug, self.text, f"site never names recipe {slug!r}")

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


if __name__ == "__main__":
    unittest.main()
