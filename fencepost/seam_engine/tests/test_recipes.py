"""Tests for the seam-recipe schema/validator (ROADMAP.md #22).

Every rule `validate_recipe`/`load_recipe_manifest`/`discover_recipes` claims
has a test that goes red if the rule breaks — same discipline as
test_ranking.py and test_gmail_calendar.py. The reference recipe under
`RECIPES/example-release-vs-changelog/` is exercised end to end: this is the
proof that "a first external recipe PR is mergeable under the oath" is not
aspirational — one already lives in this repo and clears every check.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from seam_engine.recipes import (
    RECIPES_DIR_NAME,
    REQUIRED_FIELDS,
    RecipeManifest,
    RecipeValidationError,
    discover_recipes,
    load_detector,
    load_recipe_manifest,
    validate_recipe,
)

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_RECIPE = FENCEPOST_ROOT / RECIPES_DIR_NAME / "example-release-vs-changelog" / "recipe.json"
SECOND_RECIPE = FENCEPOST_ROOT / RECIPES_DIR_NAME / "merged-pr-issue-still-open" / "recipe.json"
THIRD_RECIPE = FENCEPOST_ROOT / RECIPES_DIR_NAME / "release-not-tweeted" / "recipe.json"


def _manifest(**overrides) -> RecipeManifest:
    base = dict(
        slug="test-recipe",
        title="A test recipe",
        author="test",
        description="A recipe for testing.",
        toolkit="github",
        scopes=("ListRepoCommits",),
        fixture="fixtures/test_recipe",
        detector_file="detector.py",
        entrypoint="run_recipe_scan",
        confidence_notes="Fixed 0.8, explained here.",
    )
    base.update(overrides)
    return RecipeManifest(**base)


def _write_recipe(d: Path, **overrides) -> None:
    """Write a minimal, otherwise-valid recipe.json + detector.py into `d`."""
    data = dict(
        slug=d.name, title="X", author="a", description="d",
        toolkit="github", scopes=["ListRepoCommits"],
        fixture="fixtures/x", detector_file="detector.py",
        entrypoint="run_recipe_scan", confidence_notes="n",
    )
    data.update(overrides)
    d.mkdir(parents=True, exist_ok=True)
    (d / "recipe.json").write_text(json.dumps(data))
    (d / "detector.py").write_text("def run_recipe_scan():\n    return {}\n")


# --- the reference recipe already in the repo -------------------------------


def test_reference_recipe_exists():
    assert REFERENCE_RECIPE.exists(), "RECIPES/example-release-vs-changelog/recipe.json must still exist"


def test_reference_recipe_loads_and_validates():
    manifest = load_recipe_manifest(REFERENCE_RECIPE)
    assert manifest.slug == "example-release-vs-changelog"


def test_reference_recipe_detector_actually_runs_and_finds_its_gap():
    """Not just schema-valid — a working detector that finds a real gap in
    its own fixture. This is what "an example recipe that passes" means."""
    manifest = load_recipe_manifest(REFERENCE_RECIPE)
    fn = load_detector(manifest)
    result = fn()
    assert result["source"] == "fixture"
    assert result["primary_gap"] is not None
    assert "release-vs-changelog" in result["primary_gap"]["slug"]
    assert result["primary_gap"]["confidence"] >= result["confidence_bar"]
    # The matched release (v0.2.0) is named, not hidden, same as scan.py's
    # excluded list.
    assert len(result["excluded"]) == 1


def test_discover_recipes_finds_the_reference_recipe():
    manifests = discover_recipes(FENCEPOST_ROOT)
    slugs = [m.slug for m in manifests]
    assert "example-release-vs-changelog" in slugs


# --- the second real recipe (ROADMAP.md #108) -------------------------------
#
# RECIPES/ held exactly one real recipe from task 22 through task 107.
# CONTRIBUTING.md's whole pitch — "a stranger's recipe merges beside a
# god's" — had never been proven against real multiplicity, only a
# synthetic tmp_path fixture below. This block, plus
# `test_discover_recipes_finds_both_real_recipes`, is that proof.


def test_second_recipe_exists():
    assert SECOND_RECIPE.exists(), "RECIPES/merged-pr-issue-still-open/recipe.json must still exist"


def test_second_recipe_loads_and_validates():
    manifest = load_recipe_manifest(SECOND_RECIPE)
    assert manifest.slug == "merged-pr-issue-still-open"
    # No new scope beyond SCOPES.md's already-cleared GitHub row.
    assert set(manifest.scopes) <= {"ListPullRequests", "ListIssues", "GetIssue"}


def test_second_recipe_detector_actually_runs_and_finds_its_gap():
    """Mirrors test_reference_recipe_detector_actually_runs_and_finds_its_gap:
    not just schema-valid — a working detector that finds a real gap in its
    own fixture. `now` is passed explicitly (unlike the reference recipe,
    this one's confidence is age-gated, so its result is only deterministic
    against a fixed clock, not the real wall-clock a bare `fn()` would use)."""
    manifest = load_recipe_manifest(SECOND_RECIPE)
    fn = load_detector(manifest)
    result = fn(now=datetime(2026, 7, 17, 12, 0, 0, tzinfo=timezone.utc))
    assert result["source"] == "fixture"
    assert result["primary_gap"] is not None
    assert "merged-pr-issue-still-open" in result["primary_gap"]["slug"]
    assert result["primary_gap"]["confidence"] >= result["confidence_bar"]
    # PR #104 (fresh, <24h) is weighed and shown in the tail, not hidden,
    # but does not out-rank the stale #101 gap or break its election.
    tail_slugs = [g["slug"] for g in result["tail"]]
    assert any("104" in s for s in tail_slugs)
    # PR #102 (issue already closed), PR #103 (no closing keyword), and
    # PR #105 (names #99, which does not exist at all -- ROADMAP.md #429)
    # are all named, not hidden, in excluded.
    excluded_slugs = [g["slug"] for g in result["excluded"]]
    assert len(excluded_slugs) == 3
    assert any("102" in s for s in excluded_slugs)
    assert any("103" in s for s in excluded_slugs)
    assert any(s.startswith("nonexistent-target-105-") for s in excluded_slugs)


def test_discover_recipes_finds_both_real_recipes():
    """The actual multiplicity proof ROADMAP.md #108 exists to give:
    discover_recipes() run against the real repo tree — the same call a
    stranger's PR is validated by — returns both real recipes together,
    not just one."""
    manifests = discover_recipes(FENCEPOST_ROOT)
    slugs = [m.slug for m in manifests]
    assert len(slugs) >= 2
    assert "example-release-vs-changelog" in slugs
    assert "merged-pr-issue-still-open" in slugs


# --- the third real recipe (ROADMAP.md #110) --------------------------------
#
# The first CROSS-TOOLKIT recipe: both recipes above watch a seam entirely
# inside GitHub. This one reads GitHub releases against X tweets — the exact
# worked example STRATEGY.md names by hand ("a release shipped but never
# tweeted"). This block, plus test_discover_recipes_finds_all_three_real_recipes,
# is the proof a cross-toolkit detector clears the same oath a single-toolkit
# one does, with no special-casing anywhere in recipes.py.


def test_third_recipe_exists():
    assert THIRD_RECIPE.exists(), "RECIPES/release-not-tweeted/recipe.json must still exist"


def test_third_recipe_loads_and_validates():
    manifest = load_recipe_manifest(THIRD_RECIPE)
    assert manifest.slug == "release-not-tweeted"
    assert manifest.toolkit == "github+x"
    # No new scope beyond SCOPES.md's already-cleared GitHub/X rows.
    assert set(manifest.scopes) <= {"GetRepository", "ListRepoCommits", "GetUserTweets"}


def test_third_recipe_detector_actually_runs_and_finds_its_gap():
    """Mirrors both prior detector-actually-runs tests: not just
    schema-valid — a working detector that reads across two fixture files
    shaped like two different toolkits and finds a real gap between them."""
    manifest = load_recipe_manifest(THIRD_RECIPE)
    fn = load_detector(manifest)
    result = fn(now=datetime(2026, 7, 17, 14, 0, 0, tzinfo=timezone.utc))
    assert result["source"] == "fixture"
    assert result["primary_gap"] is not None
    assert "release-not-tweeted-v0.3.0" == result["primary_gap"]["slug"]
    assert result["primary_gap"]["confidence"] >= result["confidence_bar"]
    # v0.4.0 (fresh, <24h) is weighed and shown in the tail, not hidden, but
    # does not out-rank the stale v0.3.0 gap or break its election.
    tail_slugs = [g["slug"] for g in result["tail"]]
    assert any("v0.4.0" in s for s in tail_slugs)
    # v0.2.1 (tweeted the same day) is named, not hidden, in excluded.
    excluded_slugs = [g["slug"] for g in result["excluded"]]
    assert len(excluded_slugs) == 1
    assert any("v0.2.1" in s for s in excluded_slugs)


def test_discover_recipes_finds_all_three_real_recipes():
    """The actual multiplicity proof ROADMAP.md #110 exists to give:
    discover_recipes() run against the real repo tree returns all three real
    recipes together, single-toolkit and cross-toolkit alike."""
    manifests = discover_recipes(FENCEPOST_ROOT)
    slugs = [m.slug for m in manifests]
    assert len(slugs) >= 3
    assert "example-release-vs-changelog" in slugs
    assert "merged-pr-issue-still-open" in slugs
    assert "release-not-tweeted" in slugs


# --- schema validation: required fields --------------------------------


def test_every_required_field_is_actually_required(tmp_path: Path):
    full = {
        "slug": "x", "title": "X", "author": "a", "description": "d",
        "toolkit": "github", "scopes": ["ListRepoCommits"],
        "fixture": "fixtures/x", "detector_file": "detector.py",
        "entrypoint": "run_recipe_scan", "confidence_notes": "n",
    }
    assert set(full.keys()) == set(REQUIRED_FIELDS)
    for field in REQUIRED_FIELDS:
        partial = dict(full)
        del partial[field]
        d = tmp_path / f"x-missing-{field}"
        d.mkdir()
        (d / "recipe.json").write_text(json.dumps(partial))
        with pytest.raises(RecipeValidationError, match=field):
            load_recipe_manifest(d / "recipe.json")


def test_not_json_is_rejected(tmp_path: Path):
    d = tmp_path / "not-json"
    d.mkdir()
    (d / "recipe.json").write_text("{not valid json")
    with pytest.raises(RecipeValidationError, match="not valid JSON"):
        load_recipe_manifest(d / "recipe.json")


def test_missing_manifest_file_is_rejected(tmp_path: Path):
    with pytest.raises(RecipeValidationError, match="no such file"):
        load_recipe_manifest(tmp_path / "nope" / "recipe.json")


def test_slug_directory_mismatch_is_rejected(tmp_path: Path):
    d = tmp_path / "actual-dir-name"
    _write_recipe(d, slug="different-slug")
    with pytest.raises(RecipeValidationError, match="directory name"):
        load_recipe_manifest(d / "recipe.json")


def test_bad_slug_shape_is_rejected():
    with pytest.raises(RecipeValidationError, match="slug"):
        validate_recipe(_manifest(slug="Not_Kebab_Case"))


def test_slug_with_trailing_newline_is_rejected():
    # _SLUG_RE is anchored with a bare `$`, which (without re.MULTILINE)
    # matches end-of-string OR immediately before one single trailing `\n`
    # -- not just true end-of-string. A slug carrying a stray trailing
    # newline is not "lowercase, starts with a letter, kebab-case" (the
    # done-condition's own words), so it must be refused exactly like
    # "Not_Kebab_Case" above, the same discipline consent.py's own
    # `_ISSUE_URL_RE` already holds with `\Z`.
    with pytest.raises(RecipeValidationError, match="slug"):
        validate_recipe(_manifest(slug="valid-slug\n"))


def test_empty_title_is_rejected():
    with pytest.raises(RecipeValidationError, match="title"):
        validate_recipe(_manifest(title="  "))


def test_empty_description_is_rejected():
    with pytest.raises(RecipeValidationError, match="description"):
        validate_recipe(_manifest(description=""))


def test_empty_confidence_notes_is_rejected():
    with pytest.raises(RecipeValidationError, match="confidence_notes"):
        validate_recipe(_manifest(confidence_notes=""))


# --- the read-only oath on declared scopes: the core of task 22 -------------


@pytest.mark.parametrize(
    "scope",
    ["CreateIssue", "SendEmail", "DeleteEvent", "MergePullRequest", "PostTweet",
     "ReplyToTweet", "ModifyLabels", "PublishPage", "ShareFile", "TrashEmail",
     "InviteMember", "RevokeConnectedUser"],
)
def test_a_flatly_write_shaped_scope_is_rejected(scope: str):
    """The done-condition's own example: a write/send/delete/post scope must
    be refused, whatever else the manifest says."""
    with pytest.raises(RecipeValidationError, match="not read-only"):
        validate_recipe(_manifest(scopes=(scope,)))


def test_a_write_scoped_recipe_is_rejected_end_to_end(tmp_path: Path):
    """The exact scenario the done-condition names: a recipe.json declaring
    a write scope must not be mergeable — proven the way a real PR would be
    checked, through load_recipe_manifest, not just validate_recipe in
    isolation."""
    d = tmp_path / "sends-email"
    _write_recipe(d, scopes=["SendEmail"])
    with pytest.raises(RecipeValidationError, match="not read-only"):
        load_recipe_manifest(d / "recipe.json")


def test_a_scope_that_starts_read_only_but_hides_a_write_word_is_rejected():
    # "ListAndDeleteIssues" clears the prefix allow-list (starts with List)
    # but must still be caught — the deny-list is what catches it. Proves
    # the deny-list has independent value, not just decoration.
    with pytest.raises(RecipeValidationError, match="write verb"):
        validate_recipe(_manifest(scopes=("ListAndDeleteIssues",)))


@pytest.mark.parametrize(
    "scope",
    [
        "GetdeleteIssues",
        "ListmodifyPRs",
        "ReadremoveComments",
        "SearchpostTweets",
        "Countsharefiles",
    ],
)
def test_a_write_verb_glued_lowercase_onto_the_allowed_prefix_is_rejected(scope):
    # No capital letter marks where the allowed prefix ends and the write
    # verb begins, so `_pascal_words` swallows both into one word that
    # equals neither -- the exact-word deny-list alone would wave this
    # through. Proves the glued-verb check has independent value, the same
    # way ListAndDeleteIssues proves the deny-list does above.
    with pytest.raises(RecipeValidationError, match="glues the write verb"):
        validate_recipe(_manifest(scopes=(scope,)))


@pytest.mark.parametrize(
    "scope",
    [
        "ListAnddeleteIssues",
        "ListIssuesremove",
        "GetRepoAndtrash",
        "ListMydeleteQueue",
    ],
)
def test_a_write_verb_glued_onto_a_non_prefix_word_is_rejected(scope):
    # task 175's fix only ever checks the leading allowed-prefix word for a
    # glued verb (_word_hides_glued_verb requires the word to start with
    # get/list/read/search/count). A verb glued in lowercase onto the END of
    # any OTHER word -- "Anddelete", "Issuesremove", "Andtrash", "Mydelete"
    # -- never starts with an allowed prefix, so that check never even looks
    # at it, and none of these words equal a forbidden verb exactly either.
    # Proves the end-anchored glue check has independent value beyond the
    # prefix-anchored one task 175 shipped.
    with pytest.raises(RecipeValidationError, match="glues the write verb"):
        validate_recipe(_manifest(scopes=(scope,)))


def test_scope_with_trailing_newline_is_rejected():
    # Same anchoring gap as test_slug_with_trailing_newline_is_rejected,
    # in _ALLOWED_SCOPE_RE this time: "GetIssues\n" clears the bare-`$`
    # regex undetected even though a trailing newline is not one of the
    # oath's allowed [A-Za-z0-9] characters and the error text itself
    # promises "Get*/List*/Read*/Search*/Count*, or exactly WhoAmI --
    # nothing else, ever."
    with pytest.raises(RecipeValidationError, match="not read-only"):
        validate_recipe(_manifest(scopes=("GetIssues\n",)))


def test_read_only_scopes_are_accepted():
    # Task 424: every scope here must actually sit on consent.REQUIRED_SCOPES
    # for the manifest's own toolkit ("github", `_manifest`'s default) --
    # "WhoAmI" used to appear here but is only ever granted for the "x"
    # toolkit (SCOPES.md's own table), so it would have failed the new
    # check 3/3 for the wrong reason (an unrelated toolkit's tool, not a
    # write-shaped one) and was never actually proving what this test's
    # name claims.
    manifest = validate_recipe(
        _manifest(scopes=("GetRepository", "ListRepoCommits", "GetIssue", "CountStargazers"))
    )
    assert manifest.scopes == ("GetRepository", "ListRepoCommits", "GetIssue", "CountStargazers")


def test_real_scopes_from_scopes_md_still_accepted_after_glued_verb_check():
    # SCOPES.md's real read-only rows, including plural nouns that happen to
    # share a prefix with a forbidden verb (Labels/Label) -- the glued-verb
    # check must not start refusing scopes that were always legitimate.
    manifest = validate_recipe(
        _manifest(
            scopes=(
                "ListRepositoryActivities",
                "GetLatestRelease",
                "CountStargazers",
                "ListRepoCommits",
            )
        )
    )
    assert "ListRepositoryActivities" in manifest.scopes


def test_no_scopes_at_all_is_rejected():
    with pytest.raises(RecipeValidationError, match="scopes"):
        validate_recipe(_manifest(scopes=()))


# --- Task 424: check 3/3 -- a read-only-SHAPED scope must also be a real,
# oath-covered one (consent.REQUIRED_SCOPES for the recipe's toolkit) --------


def test_a_read_only_shaped_scope_the_oath_never_swears_to_is_rejected():
    # "GetWidgets" clears checks 1 and 2 (Get*-shaped, no write verb) but
    # names a tool no toolkit's REQUIRED_SCOPES has ever heard of.
    with pytest.raises(RecipeValidationError, match="REQUIRED_SCOPES"):
        validate_recipe(_manifest(toolkit="github", scopes=("GetWidgets",)))


def test_the_real_historical_gap_is_caught_by_the_new_check():
    # Mutation-based hand-verification, in test form: reconstruct
    # consent.REQUIRED_SCOPES exactly as it stood before task 424 (no
    # "GetPullRequest") and prove the real, shipped
    # `duplicate-pr-still-open` recipe.json -- unchanged by this task --
    # would have failed this check the whole time it sat on the merged
    # RECIPES/ tree, the same discipline test_consent_doctrine.py's own
    # "would this catcher have caught the real historical string" test
    # already holds gateway.py's coverage check to.
    from seam_engine import recipes as recipes_mod

    pre_424_scopes = frozenset(
        s for s in recipes_mod.REQUIRED_SCOPES["github"] if s != "GetPullRequest"
    )
    assert "GetPullRequest" not in pre_424_scopes

    real_manifest = recipes_mod.load_recipe_manifest(
        FENCEPOST_ROOT / RECIPES_DIR_NAME / "duplicate-pr-still-open" / "recipe.json"
    )
    assert "GetPullRequest" in real_manifest.scopes

    allowed = pre_424_scopes  # simulates the pre-fix REQUIRED_SCOPES["github"]
    uncovered = [s for s in real_manifest.scopes if s not in allowed]
    assert uncovered == ["GetPullRequest"], (
        "the reconstructed pre-424 REQUIRED_SCOPES would not have flagged "
        "duplicate-pr-still-open's real, shipped GetPullRequest scope -- "
        "this test no longer proves what its name claims"
    )


def test_a_scope_covered_only_under_a_different_toolkit_is_still_rejected():
    # "WhoAmI" is real and oath-covered -- but only for "x", never "github".
    # A github-toolkit recipe declaring it must be refused the same as any
    # other uncovered scope; toolkits are not interchangeable just because
    # both grant SOME read-only tool by that shape.
    with pytest.raises(RecipeValidationError, match="REQUIRED_SCOPES"):
        validate_recipe(_manifest(toolkit="github", scopes=("WhoAmI",)))


def test_composite_toolkit_unions_both_sides_scopes():
    # Six of the twenty-six real recipes declare a "toolkit+toolkit" pair
    # (a GitHub-vs-X seam). A scope legitimately on either named toolkit's
    # REQUIRED_SCOPES must be accepted.
    manifest = validate_recipe(
        _manifest(toolkit="github+x", scopes=("ListIssues", "GetUserTweets"))
    )
    assert manifest.scopes == ("ListIssues", "GetUserTweets")

    manifest = validate_recipe(
        _manifest(toolkit="x+github", scopes=("GetMyMentions", "GetFileContents"))
    )
    assert manifest.scopes == ("GetMyMentions", "GetFileContents")


def test_composite_toolkit_still_rejects_a_scope_covered_by_neither_side():
    with pytest.raises(RecipeValidationError, match="REQUIRED_SCOPES"):
        validate_recipe(_manifest(toolkit="github+x", scopes=("ListEvents",)))


def test_unknown_toolkit_rejects_every_scope_named():
    # An unrecognized toolkit string (typo, a toolkit REQUIRED_SCOPES has
    # never been given a row for) must not silently pass every scope --
    # `_oath_scopes_for_toolkit` returns an empty set for a part it doesn't
    # know, so every declared scope is correctly reported as uncovered.
    with pytest.raises(RecipeValidationError, match="REQUIRED_SCOPES"):
        validate_recipe(_manifest(toolkit="notarealtoolkit", scopes=("GetRepository",)))


def test_all_real_shipped_recipes_pass_the_oath_coverage_check():
    # The generalization this task exists to prove: every real recipe under
    # RECIPES/ today (not just the one reference recipe
    # test_reference_recipes_scopes_are_already_on_scopes_md_table already
    # checked) actually clears check 3/3 -- discover_recipes() itself would
    # already raise if not, but a direct assertion here names what's being
    # proven rather than relying on an absence of exception elsewhere.
    manifests = discover_recipes(FENCEPOST_ROOT)
    assert len(manifests) >= 26
    for m in manifests:
        from seam_engine.recipes import _oath_scopes_for_toolkit

        allowed = _oath_scopes_for_toolkit(m.toolkit)
        uncovered = [s for s in m.scopes if s not in allowed]
        assert not uncovered, f"{m.slug}: scope(s) {uncovered} not covered by the Oath for toolkit {m.toolkit!r}"


# --- _oath_scopes_for_toolkit's own docstring claim, cross-checked ---------

# `_oath_scopes_for_toolkit`'s docstring names how many of today's real
# recipes declare a plus-joined ("github+x"/"x+github") toolkit -- a hand-
# typed cardinal-word count of both the plus-joined subset and the total
# recipe count, never rechecked against `discover_recipes()` since it was
# written at 26 real recipes (task 424). Three more recipes have merged
# since (tweet-claims-unfixed-issue, tweet-claims-unmerged-pr,
# tweet-claims-open-milestone -- all three "x+github", the exact shape this
# claim describes), so both halves of the sentence went stale: the real
# live count is 10 of 29 then, not the 6 of 26 the docstring still swore
# to (later still: `deleted-branch-pr-still-open` merged as the thirtieth
# real recipe, task 485, a single-toolkit "github" entry that leaves the
# plus-joined half at 10 while moving the total to 30). The same "claims a
# number about itself, nothing ever checked it against the live thing it
# describes" shape `test_recipe_count_doctrine.py` already closed for
# `docs/fencepost/index.html`'s own cardinal claim, found here for
# `_oath_scopes_for_toolkit`'s own docstring.
_CARDINAL_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty-one": 21, "twenty-two": 22, "twenty-three": 23, "twenty-four": 24,
    "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28,
    "twenty-nine": 29, "thirty": 30, "thirty-one": 31, "thirty-two": 32,
    "thirty-three": 33, "thirty-four": 34, "thirty-five": 35, "thirty-six": 36,
    "thirty-seven": 37, "thirty-eight": 38,
}

_PLUS_JOINED_CLAIM_RE = re.compile(
    r"but ([a-z-]+) of the ([a-z-]+) real recipes today name a plus-joined pair"
)


def claimed_plus_joined_counts(doc_text: str) -> tuple[int, int]:
    """Live-extracts `_oath_scopes_for_toolkit`'s own "N of the M real
    recipes today name a plus-joined pair" claim -- never a second
    hand-typed (6, 26). Raises if the sentence is missing or uses a
    cardinal word this check doesn't recognize, rather than silently
    passing an unchecked claim through."""
    match = _PLUS_JOINED_CLAIM_RE.search(doc_text)
    if not match:
        raise AssertionError(
            "_oath_scopes_for_toolkit's docstring no longer contains a "
            "'N of the M real recipes today name a plus-joined pair' "
            "sentence -- this doctrine test has nothing left to cross-check"
        )
    plus_word, total_word = match.group(1).lower(), match.group(2).lower()
    for word in (plus_word, total_word):
        if word not in _CARDINAL_WORDS:
            raise AssertionError(
                f"_oath_scopes_for_toolkit's docstring uses an unrecognized "
                f"cardinal word {word!r} -- add it to _CARDINAL_WORDS before "
                "trusting this check"
            )
    return _CARDINAL_WORDS[plus_word], _CARDINAL_WORDS[total_word]


def real_plus_joined_counts(fencepost_root: Path) -> tuple[int, int]:
    """The REAL, live (plus-joined count, total count) across every recipe
    `discover_recipes()` finds today -- structural, never a second
    hand-typed sum."""
    manifests = discover_recipes(fencepost_root)
    plus_joined = sum(1 for m in manifests if "+" in m.toolkit)
    return plus_joined, len(manifests)


def test_plus_joined_claim_extraction_is_structural_not_hardcoded():
    assert claimed_plus_joined_counts(
        "but two of the five real recipes today name a plus-joined pair"
    ) == (2, 5)


def test_plus_joined_claim_missing_sentence_raises():
    with pytest.raises(AssertionError):
        claimed_plus_joined_counts("Nothing here about plus-joined toolkits.")


def test_real_plus_joined_counts_are_currently_eleven_of_thirty_eight():
    # Regression pin: today's real, live counts under RECIPES/. Was (11, 37)
    # until good-first-issue-never-referenced merged (the thirty-eighth
    # real recipe, task 499, single-toolkit "github" -- the plus-joined
    # half stays 11).
    assert real_plus_joined_counts(FENCEPOST_ROOT) == (11, 38)


def test_oath_scopes_for_toolkit_docstring_matches_the_real_live_counts():
    from seam_engine import recipes as recipes_mod

    claimed = claimed_plus_joined_counts(recipes_mod._oath_scopes_for_toolkit.__doc__)
    assert claimed == real_plus_joined_counts(FENCEPOST_ROOT), (
        f"_oath_scopes_for_toolkit's docstring claims {claimed[0]} of "
        f"{claimed[1]} real recipes name a plus-joined toolkit, but the "
        f"real live counts are {real_plus_joined_counts(FENCEPOST_ROOT)}"
    )


def test_one_more_plus_joined_recipe_would_flip_this_check_red():
    """Mutation-based hand-verification, same discipline
    `test_recipe_count_doctrine.py` already holds itself to: prove the
    checker actually flags a real drift, not just that it happens to pass
    today. A synthetic doc claim one recipe short of the real live count
    must disagree with `real_plus_joined_counts`."""
    real_plus, real_total = real_plus_joined_counts(FENCEPOST_ROOT)
    stale_doc = (
        f"but {_word_for(real_plus - 1)} of the {_word_for(real_total)} "
        "real recipes today name a plus-joined pair"
    )
    claimed = claimed_plus_joined_counts(stale_doc)
    assert claimed != (real_plus, real_total)


def _word_for(n: int) -> str:
    for word, value in _CARDINAL_WORDS.items():
        if value == n:
            return word
    raise AssertionError(f"no cardinal word mapped for {n} -- extend _CARDINAL_WORDS")


# --- MOCK ONLY: fixture must live under fixtures/ ---------------------------


def test_fixture_outside_fixtures_dir_is_rejected():
    with pytest.raises(RecipeValidationError, match="fixtures/"):
        validate_recipe(_manifest(fixture="not_fixtures/x"))


def test_fixture_path_traversal_is_rejected():
    with pytest.raises(RecipeValidationError, match="escape"):
        validate_recipe(_manifest(fixture="fixtures/../secrets"))


# --- detector_file must be a bare filename, entrypoint a real identifier ----


@pytest.mark.parametrize("bad", ["../detector.py", "sub/detector.py", "detector.txt", ""])
def test_bad_detector_file_shapes_are_rejected(bad: str):
    with pytest.raises(RecipeValidationError, match="detector_file"):
        validate_recipe(_manifest(detector_file=bad))


def test_bad_entrypoint_identifier_is_rejected():
    with pytest.raises(RecipeValidationError, match="entrypoint"):
        validate_recipe(_manifest(entrypoint="not a valid identifier"))



# --- discover_recipes: the whole-directory sweep CI runs --------------------


def test_discover_recipes_raises_naming_every_bad_manifest_at_once(tmp_path: Path):
    recipes_dir = tmp_path / RECIPES_DIR_NAME
    _write_recipe(recipes_dir / "bad-one", scopes=["CreateIssue"])
    _write_recipe(recipes_dir / "bad-two", title="")

    with pytest.raises(RecipeValidationError) as excinfo:
        discover_recipes(tmp_path)
    msg = str(excinfo.value)
    assert "bad-one" in msg
    assert "bad-two" in msg


def test_discover_recipes_passes_when_every_manifest_is_clean(tmp_path: Path):
    recipes_dir = tmp_path / RECIPES_DIR_NAME
    _write_recipe(recipes_dir / "good-one")
    manifests = discover_recipes(tmp_path)
    assert [m.slug for m in manifests] == ["good-one"]


def test_discover_recipes_on_a_directory_with_no_recipes_returns_empty(tmp_path: Path):
    assert discover_recipes(tmp_path) == []


def test_discover_recipes_on_a_missing_RECIPES_dir_returns_empty(tmp_path: Path):
    assert discover_recipes(tmp_path / "nonexistent") == []


# --- load_detector: proves a recipe's entrypoint is real, not just named ---


def test_load_detector_needs_a_manifest_with_a_path():
    with pytest.raises(RecipeValidationError, match="manifest loaded from disk"):
        load_detector(_manifest())


def test_load_detector_on_a_missing_file_is_rejected(tmp_path: Path):
    d = tmp_path / "no-detector"
    d.mkdir()
    (d / "recipe.json").write_text(json.dumps({
        "slug": "no-detector", "title": "X", "author": "a", "description": "d",
        "toolkit": "github", "scopes": ["ListRepoCommits"], "fixture": "fixtures/x",
        "detector_file": "detector.py", "entrypoint": "run_recipe_scan", "confidence_notes": "n",
    }))
    manifest = RecipeManifest(
        slug="no-detector", title="X", author="a", description="d", toolkit="github",
        scopes=("ListRepoCommits",), fixture="fixtures/x", detector_file="detector.py",
        entrypoint="run_recipe_scan", confidence_notes="n", path=d / "recipe.json",
    )
    with pytest.raises(RecipeValidationError, match="does not exist"):
        load_detector(manifest)


def test_load_detector_on_a_missing_entrypoint_is_rejected(tmp_path: Path):
    d = tmp_path / "wrong-entrypoint"
    _write_recipe(d, entrypoint="does_not_exist")
    manifest = load_recipe_manifest(d / "recipe.json")
    with pytest.raises(RecipeValidationError, match="no callable"):
        load_detector(manifest)
