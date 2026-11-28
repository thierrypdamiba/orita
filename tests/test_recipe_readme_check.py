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
import re
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

[`RECIPES/alpha-gap/`](RECIPES/alpha-gap/) is the first (ROADMAP.md #1).
[`RECIPES/beta-gap/`](RECIPES/beta-gap/) is the second (ROADMAP.md #2).

## Run your own

Not this section's problem.
"""


def _write_recipe(fencepost_root, slug, with_readme=True):
    """A minimal, schema-valid recipe.json under <fencepost_root>/RECIPES/<slug>/ --
    enough for discover_recipes() to accept it without ever needing a real
    detector.py (discover_recipes only reads the manifest, never imports
    the detector). Writes a stub README.md alongside it by default -- the
    convention 37 of 38 real recipes hold, see MissingRecipeReadmeCase for
    the one exception this check exists to catch."""
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
    if with_readme:
        with open(os.path.join(recipe_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(f"# {slug}\n")


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
        self.assertEqual(result["missing_readme"], [])
        self.assertEqual(result["real_count"], 2)
        self.assertEqual(result["linked_count"], 2)
        self.assertEqual(result["missing_roadmap_citation"], [])

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


class MissingRecipeReadmeCase(unittest.TestCase):
    """The fourth cross-check (task 504): a real recipe directory with no
    own README.md -- exactly the silent gap an Explore agent found sitting
    in `merged-pr-pr-still-open/` (task #419, fully shipped, fully tested,
    just never given its own README.md the way 37 of its 38 siblings
    were). Every existing cross-check in this file is aimed at the PARENT
    README's own links; this is the first one that ever looks inside a
    recipe's own directory."""

    def _fixture(self, slugs_with_readme, slugs_without_readme):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, tmpdir, ignore_errors=True)
        lines = ["## Community recipes", ""]
        for slug in slugs_with_readme:
            _write_recipe(tmpdir, slug, with_readme=True)
            lines.append(f"[`RECIPES/{slug}/`](RECIPES/{slug}/) has one (ROADMAP.md #1).")
        for slug in slugs_without_readme:
            _write_recipe(tmpdir, slug, with_readme=False)
            lines.append(f"[`RECIPES/{slug}/`](RECIPES/{slug}/) does not (ROADMAP.md #2).")
        lines += ["", "## Run your own"]
        readme_path = os.path.join(tmpdir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return readme_path, tmpdir

    def test_recipe_with_no_own_readme_is_caught(self):
        readme_path, fencepost_root = self._fixture(["alpha-gap"], ["beta-gap"])
        result = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_readme"], ["beta-gap"])
        # the other three checks stay clean -- this is genuinely orthogonal
        self.assertEqual(result["missing_from_readme"], [])
        self.assertEqual(result["stale_in_readme"], [])
        self.assertEqual(result["mismatched_links"], [])

    def test_every_recipe_with_its_own_readme_is_clean(self):
        readme_path, fencepost_root = self._fixture(["alpha-gap", "beta-gap"], [])
        result = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_readme"], [])

    def test_writing_the_missing_readme_flips_it_back_to_clean(self):
        readme_path, fencepost_root = self._fixture(["alpha-gap"], ["beta-gap"])
        broken = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertFalse(broken["clean"])
        with open(os.path.join(fencepost_root, "RECIPES", "beta-gap", "README.md"), "w", encoding="utf-8") as f:
            f.write("# beta-gap\n")
        fixed = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertTrue(fixed["clean"])


class MissingRoadmapCitationCase(unittest.TestCase):
    """Task 526: the fifth cross-check. Every real, live recipe entry in
    the README carries `(ROADMAP.md #NNN)` right after its ordinal claim
    -- except the reference recipe, which claims no ordinal at all and is
    never expected to. Nothing checked this before: `merged-pr-branch-
    not-deleted`'s own paragraph (task #514) silently shipped without its
    citation, alone among the other 39 numbered entries, and stayed that
    way undetected until this task's live sweep of `fencepost/README.md`
    found it by hand."""

    def _fixture(self, section_lines):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, tmpdir, ignore_errors=True)
        lines = ["## Community recipes", ""]
        lines += section_lines
        lines += ["", "## Run your own"]
        readme_path = os.path.join(tmpdir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return readme_path, tmpdir

    def test_entry_with_no_citation_is_caught(self):
        readme_path, fencepost_root = self._fixture(
            [
                "[`RECIPES/alpha-gap/`](RECIPES/alpha-gap/) is the second (ROADMAP.md #10).",
                "[`RECIPES/beta-gap/`](RECIPES/beta-gap/) is the third: no citation at all.",
            ]
        )
        for slug in ("alpha-gap", "beta-gap"):
            _write_recipe(fencepost_root, slug)
        result = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_roadmap_citation"], ["beta-gap"])
        # the other cross-checks stay clean -- this is genuinely orthogonal
        self.assertEqual(result["missing_from_readme"], [])
        self.assertEqual(result["stale_in_readme"], [])
        self.assertEqual(result["mismatched_links"], [])

    def test_reference_recipe_is_exempt(self):
        readme_path, fencepost_root = self._fixture(
            [
                f"[`RECIPES/{rrc._REFERENCE_RECIPE_SLUG}/`](RECIPES/{rrc._REFERENCE_RECIPE_SLUG}/) "
                "is the reference: no citation, and none expected.",
            ]
        )
        _write_recipe(fencepost_root, rrc._REFERENCE_RECIPE_SLUG)
        result = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_roadmap_citation"], [])

    def test_every_entry_with_a_citation_is_clean(self):
        readme_path, fencepost_root = self._fixture(
            ["[`RECIPES/alpha-gap/`](RECIPES/alpha-gap/) is the second (ROADMAP.md #10)."]
        )
        _write_recipe(fencepost_root, "alpha-gap")
        result = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_roadmap_citation"], [])

    def test_adding_the_missing_citation_flips_it_back_to_clean(self):
        readme_path, fencepost_root = self._fixture(
            ["[`RECIPES/alpha-gap/`](RECIPES/alpha-gap/) is the second: no citation yet."]
        )
        _write_recipe(fencepost_root, "alpha-gap")
        broken = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertFalse(broken["clean"])
        self.assertEqual(broken["missing_roadmap_citation"], ["alpha-gap"])

        with open(readme_path, encoding="utf-8") as f:
            text = f.read()
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(text.replace("is the second: no citation yet.", "is the second (ROADMAP.md #10)."))
        fixed = rrc.check_recipe_readme(readme_path=readme_path, fencepost_root=fencepost_root)
        self.assertTrue(fixed["clean"])
        self.assertEqual(fixed["missing_roadmap_citation"], [])


class RealRepoRoadmapCitationCase(unittest.TestCase):
    """The real point: today's real fencepost/README.md carries a
    `(ROADMAP.md #NNN)` citation on every one of its forty numbered
    entries -- the reference recipe alone exempt. Regression pin for the
    real bug this task found and fixed: `merged-pr-branch-not-deleted`'s
    own paragraph shipped (task #514) without one."""

    def test_real_readme_has_no_missing_citations(self):
        result = rrc.check_recipe_readme()
        self.assertEqual(
            result["missing_roadmap_citation"], [],
            msg=f"recipe entrie(s) missing a (ROADMAP.md #NNN) citation: {result['missing_roadmap_citation']}",
        )


class FormatResultCase(unittest.TestCase):
    def test_clean_result_names_the_real_count(self):
        text = rrc.format_result({"clean": True, "real_count": 26, "linked_count": 26,
                                   "missing_from_readme": [], "stale_in_readme": [], "mismatched_links": [],
                                   "missing_readme": []})
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
            "missing_readme": ["delta-gap"],
            "missing_roadmap_citation": ["epsilon-gap"],
        })
        self.assertIn("BROKEN", text)
        self.assertIn("gamma-gap", text)
        self.assertIn("beta-gap", text)
        self.assertIn("alpha-gap", text)
        self.assertIn("delta-gap", text)
        self.assertIn("epsilon-gap", text)


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
                f"mismatched={result['mismatched_links']} missing_readme={result['missing_readme']}",
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


# --- _community_recipes_section's own docstring claim, cross-checked ------
#
# ROADMAP.md #479: the same "claims a number about itself, nothing ever
# checked it against the live thing it describes" shape
# test_recipes.py's own `test_oath_scopes_for_toolkit_docstring_matches_
# the_real_live_counts` (task 475) already closed for
# `_oath_scopes_for_toolkit`'s docstring, found here one file over:
# `_community_recipes_section`'s docstring said "twenty-six community
# recipes" from the hour task 426 wrote it (26 real recipes then); three
# more have merged since (tweet-claims-unfixed-issue,
# tweet-claims-unmerged-pr, tweet-claims-open-milestone), so the real live
# count is 29 today, not 26. Nothing in this file's own test suite ever
# read that docstring back against `_linked_recipes`/`discover_recipes`'s
# live count -- fixed at the root (the docstring itself), pinned here so
# it cannot silently drift again.
# Task 2733: this file used to hold its OWN hand-typed `_CARDINAL_WORDS`
# map (zero through "one hundred sixteen", needing a new line added by
# hand every time the live count grew past its own ceiling) purely to
# parse and re-synthesize `_community_recipes_section`'s one-sentence
# count claim -- the identical "needs hand-extending every time the
# number grows, easy to forget" shape as the nine-time recurring bug this
# whole file exists to catch, and a straight duplicate of logic that now
# lives in production code (`cardinal_word`/`cardinal_value`/
# `claimed_section_count` in `tools/recipe_readme_check.py` itself,
# where `check_recipe_readme()` can also use it live). Delegating here
# removes the duplicate rather than maintaining two independent copies of
# the same ceiling-limited map.
_word_for = rrc.cardinal_word
claimed_section_count = rrc.claimed_section_count


class DocstringCountDoctrineCase(unittest.TestCase):
    def test_claim_extraction_is_structural_not_hardcoded(self):
        self.assertEqual(
            claimed_section_count(
                "never mistaken for one of the five community recipes "
                "this section actually enumerates"
            ),
            5,
        )

    def test_claim_missing_sentence_raises(self):
        with self.assertRaises(AssertionError):
            claimed_section_count("Nothing here about a recipe count.")

    def test_real_live_section_count_is_currently_one_hundred_twelve(self):
        # Regression pin: today's real, live linked-recipe count. Was 109
        # until repo-description-claims-open-milestone merged (task 1407,
        # the hundred-ninth), then 110 until repo-description-claims-
        # unmerged-pr merged (task 1408, the hundred-tenth), then 111
        # until manifest-version-never-tagged merged (task 1607, the
        # hundred-eleventh), then 112 until merged-pr-changes-requested-
        # not-addressed merged (task 1613, the hundred-twelfth), then 113
        # until readme-star-count-stale merged (task 1647, the
        # hundred-thirteenth), then 114 until help-wanted-issue-never-
        # referenced merged (task 2683, the hundred-fourteenth), then 115
        # until notion-page-dangling-reference merged (task 2729, the
        # hundred-fifteenth), then 116 until notion-page-claims-unfixed-
        # issue merged (task 2731, the hundred-sixteenth).
        # Task 1380's own addendum named this exact repo-root pin
        # (distinct from the fencepost-side ones in
        # test_recipe_count_doctrine.py etc.) as the one dawn-run itself
        # has now caught missing five separate times (101->102 task 1259,
        # 102->103 task 1353, 103->104 task 1380's own addendum, 110->111
        # task 1608 (catching task 1607's own miss), 111->112 task 1613's
        # own addendum -- this fix); task 2684 was the seventh miss of the
        # identical pin, by task 2683's own close; task 2730 (hour 01 UTC,
        # 2026-11-28) was the eighth, by task 2729's own close; this fix
        # (hour 03 UTC, 2026-11-28) is the ninth, by task 2731's own close --
        # same shape every time, caught live by dawn-run's the-oath job
        # rather than proactively before that push, and this file
        # (test_recipe_readme_check.py) is the one file the "walked forward
        # every self-referential count/ordinal claim" lists in tasks 2729
        # AND 2731 both failed to name.
        with open(rrc.DEFAULT_README_PATH, encoding="utf-8") as f:
            text = f.read()
        section = rrc._community_recipes_section(text)
        self.assertEqual(len(rrc._linked_recipes(section)), 116)

    def test_docstring_matches_the_real_live_count(self):
        with open(rrc.DEFAULT_README_PATH, encoding="utf-8") as f:
            text = f.read()
        section = rrc._community_recipes_section(text)
        real_count = len(rrc._linked_recipes(section))
        claimed = claimed_section_count(rrc._community_recipes_section.__doc__)
        self.assertEqual(
            claimed, real_count,
            msg=f"_community_recipes_section's docstring claims {claimed} "
                f"community recipes, but the real live count is {real_count}",
        )

    def test_one_fewer_recipe_in_the_claim_would_flip_this_check_red(self):
        """Mutation-based hand-verification, same discipline
        test_recipes.py's own analogous doctrine test already holds itself
        to: prove the checker actually flags a real drift, not just that
        it happens to pass today."""
        with open(rrc.DEFAULT_README_PATH, encoding="utf-8") as f:
            text = f.read()
        section = rrc._community_recipes_section(text)
        real_count = len(rrc._linked_recipes(section))
        stale_doc = (
            f"never mistaken for one of the {_word_for(real_count - 1)} "
            "community recipes this section actually enumerates"
        )
        self.assertNotEqual(claimed_section_count(stale_doc), real_count)


class CardinalWordRoundTripCase(unittest.TestCase):
    """`cardinal_word`/`cardinal_value` replace the old hand-typed,
    ceiling-limited `_CARDINAL_WORDS` map -- proves the round trip holds
    across the full 0-999 range the docstring claim could ever need, not
    just the handful of values this repo has hit so far."""

    def test_round_trip_every_value_zero_to_nine_hundred_ninety_nine(self):
        for n in range(0, 1000):
            self.assertEqual(rrc.cardinal_value(rrc.cardinal_word(n)), n)

    def test_matches_every_value_the_old_hand_typed_map_once_held(self):
        # The exact spot-checks the retired _CARDINAL_WORDS map's entries
        # covered, so the replacement is proven byte-for-byte equivalent
        # on real history, not just internally consistent with itself.
        known = {
            0: "zero", 16: "sixteen", 20: "twenty", 26: "twenty-six",
            29: "twenty-nine", 99: "ninety-nine", 100: "one hundred",
            101: "one hundred one", 110: "one hundred ten",
            112: "one hundred twelve", 116: "one hundred sixteen",
        }
        for value, word in known.items():
            self.assertEqual(rrc.cardinal_word(value), word)
            self.assertEqual(rrc.cardinal_value(word), value)

    def test_out_of_range_raises_instead_of_truncating(self):
        with self.assertRaises(ValueError):
            rrc.cardinal_word(1000)
        with self.assertRaises(ValueError):
            rrc.cardinal_word(-1)

    def test_unrecognized_word_raises_instead_of_guessing(self):
        with self.assertRaises(ValueError):
            rrc.cardinal_value("eleventy-one")


class CheckRecipeReadmeDocstringMismatchCase(unittest.TestCase):
    """`check_recipe_readme()` itself -- the live command the hourly
    ritual already runs -- now folds in the docstring-count claim rather
    than staying blind to the exact drift that broke `dawn-run` nine
    times, caught only by this file's own separate doctrine test."""

    def test_live_check_is_clean_against_todays_real_docstring(self):
        result = rrc.check_recipe_readme()
        self.assertTrue(result["clean"])
        self.assertIsNone(result["docstring_count_mismatch"])

    def test_live_check_flags_a_staled_docstring(self):
        original_doc = rrc._community_recipes_section.__doc__
        try:
            rrc._community_recipes_section.__doc__ = (
                "never mistaken for one of the twelve community\n"
                "    recipes this section actually enumerates today."
            )
            result = rrc.check_recipe_readme()
            self.assertFalse(result["clean"])
            self.assertEqual(result["real_count"], result["docstring_count_mismatch"]["real"])
            self.assertEqual(result["docstring_count_mismatch"]["claimed"], 12)
            self.assertIn("docstring claims", rrc.format_result(result))
        finally:
            rrc._community_recipes_section.__doc__ = original_doc


class FixDocstringCountCase(unittest.TestCase):
    """`fix` -- the one-command self-correction every future recipe-
    adding task should run instead of hand-editing this prose from
    memory and missing it a tenth time."""

    def _temp_copy(self, tmp_dir: str) -> str:
        tmp_path = os.path.join(tmp_dir, "recipe_readme_check.py")
        with open(os.path.join(ROOT, "tools", "recipe_readme_check.py"), encoding="utf-8") as f:
            source_text = f.read()
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(source_text)
        return tmp_path

    def test_fix_rewrites_a_staled_count_to_match_reality(self):
        real_count = rrc.check_recipe_readme()["real_count"]
        stale_word = _word_for(real_count - 1)
        current_word = _word_for(real_count)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = self._temp_copy(tmp_dir)
            with open(tmp_path, encoding="utf-8") as f:
                src = f.read()
            self.assertIn(f"one of the {current_word} community", src)
            src = src.replace(f"one of the {current_word} community", f"one of the {stale_word} community")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(src)

            changed = rrc.fix_docstring_count(module_path=tmp_path)
            self.assertTrue(changed)
            with open(tmp_path, encoding="utf-8") as f:
                fixed_src = f.read()
            self.assertIn(f"one of the {current_word} community", fixed_src)
            self.assertNotIn(f"one of the {stale_word} community", fixed_src)

    def test_fix_is_idempotent_on_an_already_correct_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = self._temp_copy(tmp_dir)
            with open(tmp_path, encoding="utf-8") as f:
                before = f.read()
            changed = rrc.fix_docstring_count(module_path=tmp_path)
            self.assertFalse(changed)
            with open(tmp_path, encoding="utf-8") as f:
                after = f.read()
            self.assertEqual(before, after)

    def test_fix_touches_nothing_outside_the_one_claim_sentence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = self._temp_copy(tmp_dir)
            real_count = rrc.check_recipe_readme()["real_count"]
            current_word = _word_for(real_count)
            stale_word = _word_for(real_count - 1)
            with open(tmp_path, encoding="utf-8") as f:
                src = f.read()
            src = src.replace(f"one of the {current_word} community", f"one of the {stale_word} community")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(src)
            rrc.fix_docstring_count(module_path=tmp_path)
            with open(tmp_path, encoding="utf-8") as f:
                fixed_src = f.read()
            with open(os.path.join(ROOT, "tools", "recipe_readme_check.py"), encoding="utf-8") as f:
                real_src = f.read()
            self.assertEqual(fixed_src, real_src)


if __name__ == "__main__":
    unittest.main()
