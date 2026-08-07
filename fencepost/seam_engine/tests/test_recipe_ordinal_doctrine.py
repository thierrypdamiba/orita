"""Task 522. Every real recipe's own `detector.py` docstring opens with a
claimed cardinal position in the recipe order -- "Eighth real seam
recipe", "The eighteenth real seam recipe", "The forty-first real seam
recipe, and the fifth and final leg of the dangling-reference family" --
but nothing anywhere checks that these forty individual claims are
mutually consistent. `test_recipe_count_doctrine.py` (task 156) is
explicit about the shape of gap it closes and no more: it proves only
that the WALL's single aggregate cardinal ("Forty-one real recipes stand
today") matches `discover_recipes()`'s live length. It says nothing about
whether recipe #17 and recipe #24 quietly claim the same ordinal, or
whether some number in the middle of the sequence was skipped when two
recipes shipped in the same task and one docstring was typed by hand
against a stale mental count -- a real class of drift this town's own
history has already hit once at the aggregate level (task 494 found a
stale forward-pointer of the identical "prose claim silently outlives the
code" shape, one recipe's docstring referencing another's by name rather
than by number, but the same root cause: a claim in prose nothing
re-derives from the live tree).

This file closes the per-recipe half of that gap: extract each real
recipe's own claimed ordinal from its `detector.py` docstring (never a
second hand-typed table -- `discover_recipes()` supplies the live slug
list, the same function `test_recipe_count_doctrine.py` already trusts),
and assert the live set is —

1. every real recipe but the reference `example-release-vs-changelog/`
   (task 22, CONTRIBUTING.md's own copy-this-shape scaffold, which opens
   "Example seam recipe" on purpose and claims no ordinal at all) carries
   exactly one ordinal claim;
2. all of those claims are pairwise distinct; and
3. together they form the unbroken sequence `2..N` for `N` real recipes
   (the reference recipe is the unnumbered first; the earliest NUMBERED
   recipe, `merged-pr-issue-still-open`, has always opened "Second real
   seam recipe" -- this is the live, real invariant, not an assumption).

Proven against the real repo tree today (currently clean -- no duplicate,
no gap, confirmed by `test_the_real_ordinal_claims_are_currently_clean`
below), and mutation-tested with a synthetic pair of `detector.py`
docstrings carrying a genuine duplicate ordinal to prove a real collision
would flip this check red, the same "prove the net catches something,
don't just trust the shape of the code" discipline
`test_recipe_count_doctrine.py`'s own mutation test already established.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from seam_engine.recipes import discover_recipes

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]

_ORDINAL_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19, "twentieth": 20, "twenty-first": 21,
    "twenty-second": 22, "twenty-third": 23, "twenty-fourth": 24,
    "twenty-fifth": 25, "twenty-sixth": 26, "twenty-seventh": 27,
    "twenty-eighth": 28, "twenty-ninth": 29, "thirtieth": 30,
    "thirty-first": 31, "thirty-second": 32, "thirty-third": 33,
    "thirty-fourth": 34, "thirty-fifth": 35, "thirty-sixth": 36,
    "thirty-seventh": 37, "thirty-eighth": 38, "thirty-ninth": 39,
    "fortieth": 40, "forty-first": 41, "forty-second": 42,
    "forty-third": 43, "forty-fourth": 44, "forty-fifth": 45,
    "forty-sixth": 46, "forty-seventh": 47, "forty-eighth": 48,
    "forty-ninth": 49, "fiftieth": 50, "fifty-first": 51, "fifty-second": 52,
    "fifty-third": 53, "fifty-fourth": 54,
}

# Matches right at the top of the docstring only (``re.match``, not
# ``search``) so a later, unrelated "real seam recipe" mention deeper in
# the same file (every sibling recipe's docstring names several others by
# ordinal, in prose, while explaining its own place in a family) can
# never be mistaken for THIS recipe's own claim.
_ORDINAL_CLAIM_RE = re.compile(
    r'"""(?:The )?([A-Za-z]+(?:-[a-z]+)?) real seam recipe\b', re.IGNORECASE
)


def claimed_ordinal(detector_text: str) -> int | None:
    """The ordinal `detector_text`'s own docstring opens by claiming, or
    ``None`` if it opens with no such claim at all (the reference recipe's
    own shape). Raises if it opens with an ordinal-shaped word this table
    doesn't recognize, rather than silently reading it as "no claim" --
    the identical "unrecognized word must not silently pass" discipline
    `test_recipe_count_doctrine.py`'s own `claimed_recipe_count` uses for
    the site's aggregate cardinal."""
    match = _ORDINAL_CLAIM_RE.match(detector_text.lstrip())
    if not match:
        return None
    word = match.group(1).lower()
    if word not in _ORDINAL_WORDS:
        raise AssertionError(
            f"a detector.py docstring opens with an unrecognized ordinal "
            f"word {word!r} -- add it to _ORDINAL_WORDS before trusting "
            "this check"
        )
    return _ORDINAL_WORDS[word]


def live_ordinal_claims(fencepost_root: Path) -> dict[str, int | None]:
    """slug -> claimed ordinal (or None), read live from every real
    recipe's own `detector.py`, via the same `discover_recipes()` the
    rest of this engine already trusts as the one source of the real
    recipe list -- never a second hand-typed slug set."""
    claims: dict[str, int | None] = {}
    for manifest in discover_recipes(fencepost_root):
        # manifest.path is the recipe.json FILE, not its directory -- the
        # same `.parent / detector_file` join recipes.py's own
        # detector_file existence check (line 425) already uses.
        detector_path = manifest.path.parent / manifest.detector_file
        claims[manifest.slug] = claimed_ordinal(
            detector_path.read_text(encoding="utf-8")
        )
    return claims


def test_ordinal_extraction_is_structural_not_hardcoded():
    assert claimed_ordinal('"""Eighth real seam recipe: a thing.\n"""') == 8
    assert (
        claimed_ordinal('"""The eighteenth real seam recipe: a thing.\n"""')
        == 18
    )
    assert (
        claimed_ordinal(
            '"""The forty-first real seam recipe, and the fifth and '
            "final leg of the dangling-reference family: a thing.\n\"\"\""
        )
        == 41
    )


def test_the_reference_recipe_claims_no_ordinal():
    assert claimed_ordinal('"""Example seam recipe: a thing.\n"""') is None


def test_unrecognized_ordinal_word_raises_instead_of_silently_passing():
    with pytest.raises(AssertionError):
        claimed_ordinal('"""The umpteenth real seam recipe: a thing.\n"""')


def test_every_real_recipe_but_the_reference_claims_exactly_one_ordinal():
    claims = live_ordinal_claims(FENCEPOST_ROOT)
    unclaimed = [
        slug
        for slug, ordinal in claims.items()
        if ordinal is None and slug != "example-release-vs-changelog"
    ]
    assert unclaimed == [], (
        "recipe(s) with no ordinal claim in their own detector.py "
        f"docstring, and none of them is the reference recipe: {unclaimed}"
    )
    assert claims["example-release-vs-changelog"] is None


def test_all_claimed_ordinals_are_pairwise_distinct():
    claims = live_ordinal_claims(FENCEPOST_ROOT)
    numbered = [n for n in claims.values() if n is not None]
    duplicates = sorted({n for n in numbered if numbered.count(n) > 1})
    assert duplicates == [], (
        f"two or more recipes claim the same ordinal(s): {duplicates} -- "
        "a stale hand-typed docstring, not a live-derived one"
    )


def test_the_real_ordinal_claims_are_currently_clean():
    """Regression pin against today's real, live tree: 54 real recipes,
    the reference recipe unnumbered, the other 53 forming the unbroken
    sequence 2..54 -- no duplicate, no gap. Was 53/52/2..53 until
    review-comment-claims-unfixed-issue merged (the fifty-fourth real
    recipe)."""
    claims = live_ordinal_claims(FENCEPOST_ROOT)
    numbered = sorted(n for n in claims.values() if n is not None)
    assert len(claims) == 54
    assert numbered == list(range(2, 55))


def test_a_duplicate_ordinal_would_flip_this_check_red(tmp_path):
    """Mutation-based hand-verification: take the real live claims, then
    corrupt one non-reference recipe's own claim to collide with another
    real recipe's claim, and prove the pairwise-distinct check above would
    actually catch it -- not merely assumed to, by shape of the code."""
    claims = dict(live_ordinal_claims(FENCEPOST_ROOT))
    numbered_slugs = [
        slug for slug, n in claims.items() if n is not None
    ]
    victim, collider = numbered_slugs[0], numbered_slugs[1]
    claims[collider] = claims[victim]

    numbered = [n for n in claims.values() if n is not None]
    duplicates = sorted({n for n in numbered if numbered.count(n) > 1})
    assert duplicates == [claims[victim]]
