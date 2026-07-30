"""Task 156. The Wall's own "Three real recipes stand today" line
(`docs/fencepost/index.html`) is a literal cardinal claim about
`discover_recipes()`'s real output -- true today (three real slugs under
RECIPES/), and, like `oracle/SCOPES.md`'s "34 tests" claim before task 153,
structurally unguarded: nothing anywhere cross-checks the site's own word
against the live count `discover_recipes()` actually returns.
`tests/test_fencepost_site_recipes.py::test_names_all_three_real_recipes`
only checks presence -- each of three known slugs appears somewhere in the
page's text -- never cardinality; a fourth merged recipe would still pass
it. `test_recipes.py::test_discover_recipes_finds_all_three_real_recipes`
and `test_recipes_doctrine.py::test_the_real_repo_tree_discovers_cleanly`
both assert `len(...) >= 3` / `>= 1` on purpose, a floor not an exact
count -- CONTRIBUTING.md's whole mechanism exists to invite a fourth
recipe, and the day one merges, the site's "Three real recipes stand
today" goes stale in public with every existing test still green.

This file closes that gap the same way task 153 closed oracle/SCOPES.md's
stale count claim: extract the claimed cardinal word from the live site
text (never a second hand-typed "3"), compute the real count from
`discover_recipes()` against the real repo tree, assert the two agree, and
prove with a real mutation fixture that a genuine fourth recipe would flip
the check red.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from seam_engine.recipes import discover_recipes

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = FENCEPOST_ROOT.parent
SITE_PATH = REPO_ROOT / "docs" / "fencepost" / "index.html"

_CARDINAL_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty-one": 21, "twenty-two": 22, "twenty-three": 23, "twenty-four": 24,
}

_CLAIM_RE = re.compile(r"([A-Za-z-]+) real recipes stand today")


def claimed_recipe_count(site_text: str) -> int:
    """Live-extract the site's own cardinal claim -- never a hand-typed 3.
    Raises if the claim sentence is missing, or its cardinal word is one
    this check doesn't recognize, rather than silently passing an
    unchecked claim through."""
    match = _CLAIM_RE.search(site_text)
    if not match:
        raise AssertionError(
            "docs/fencepost/index.html no longer contains a "
            "'<Cardinal> real recipes stand today' sentence -- this "
            "doctrine test has nothing left to cross-check against reality"
        )
    word = match.group(1).lower()
    if word not in _CARDINAL_WORDS:
        raise AssertionError(
            f"docs/fencepost/index.html's recipe-count claim uses an "
            f"unrecognized cardinal word {word!r} -- add it to "
            "_CARDINAL_WORDS before trusting this check"
        )
    return _CARDINAL_WORDS[word]


def real_recipe_count(fencepost_root: Path) -> int:
    return len(discover_recipes(fencepost_root))


def test_claim_extraction_is_structural_not_hardcoded():
    assert claimed_recipe_count("Five real recipes stand today:") == 5
    assert claimed_recipe_count("One real recipes stand today:") == 1


def test_missing_claim_sentence_raises_instead_of_silently_passing():
    with pytest.raises(AssertionError):
        claimed_recipe_count("<p>Nothing here about recipe counts.</p>")


def test_unrecognized_cardinal_word_raises():
    with pytest.raises(AssertionError):
        claimed_recipe_count("Several real recipes stand today:")


def test_real_recipe_count_is_currently_twenty_four():
    """Regression pin: today's real, live count under RECIPES/. Was 23 until
    RECIPES/issue-body-dangling-reference/ merged (the twenty-fourth real
    recipe) -- the exact drift this whole doctrine file exists to catch,
    now caught once for real instead of only rehearsed by the mutation
    test below."""
    assert real_recipe_count(FENCEPOST_ROOT) == 24


def test_site_claim_matches_the_real_live_count():
    site_text = SITE_PATH.read_text(encoding="utf-8")
    assert claimed_recipe_count(site_text) == real_recipe_count(FENCEPOST_ROOT)


def test_one_more_real_recipe_would_flip_this_check_red(tmp_path):
    """Mutation-based hand-verification: reconstruct the real repo's
    RECIPES/ tree plus one synthetic extra recipe, prove `real_recipe_count`
    sees one more than the live baseline, and prove that disagrees with the
    site's real, live claim -- the exact drift this file exists to catch,
    reproduced against real manifests, not asserted on faith.

    Computed against the LIVE baseline (`real_recipe_count(FENCEPOST_ROOT)`),
    never a second hand-typed cardinal -- this is exactly the fix task 156
    itself made to the site's own claim, applied here too, so this test
    does not go stale the next time a real recipe merges (it went stale
    once already: hand-typed as "4" when a real fourth recipe was still
    hypothetical, silently wrong the hour dangling-issue-reference actually
    merged and the live baseline became 4 -- caught before that could ship
    by making the assertion relative, not absolute)."""
    baseline = real_recipe_count(FENCEPOST_ROOT)

    fake_root = tmp_path / "fencepost"
    recipes_dir = fake_root / "RECIPES"
    recipes_dir.mkdir(parents=True)

    real_recipes_dir = FENCEPOST_ROOT / "RECIPES"
    for slug_dir in sorted(p for p in real_recipes_dir.iterdir() if p.is_dir()):
        manifest_src = slug_dir / "recipe.json"
        if not manifest_src.exists():
            continue
        dest = recipes_dir / slug_dir.name
        dest.mkdir()
        (dest / "recipe.json").write_text(
            manifest_src.read_text(encoding="utf-8"), encoding="utf-8"
        )

    extra = recipes_dir / "a-synthetic-extra-recipe"
    extra.mkdir()
    (extra / "recipe.json").write_text(
        json.dumps(
            {
                "slug": "a-synthetic-extra-recipe",
                "title": "A synthetic extra recipe",
                "author": "test",
                "description": "Exists only to prove this doctrine test catches real drift.",
                "toolkit": "github",
                "scopes": ["GetRepository"],
                "fixture": "fixtures/a_synthetic_extra_recipe",
                "detector_file": "detector.py",
                "entrypoint": "run_recipe_scan",
                "confidence_notes": "n/a -- synthetic mutation fixture",
            }
        ),
        encoding="utf-8",
    )

    real_count_with_extra = real_recipe_count(fake_root)
    assert real_count_with_extra == baseline + 1

    site_text = SITE_PATH.read_text(encoding="utf-8")
    assert claimed_recipe_count(site_text) != real_count_with_extra
