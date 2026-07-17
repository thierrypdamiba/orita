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
    # PR #102 (issue already closed) and PR #103 (no closing keyword) are
    # both named, not hidden, in excluded.
    excluded_slugs = [g["slug"] for g in result["excluded"]]
    assert len(excluded_slugs) == 2
    assert any("102" in s for s in excluded_slugs)
    assert any("103" in s for s in excluded_slugs)


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


def test_read_only_scopes_are_accepted():
    manifest = validate_recipe(
        _manifest(scopes=("GetRepository", "ListRepoCommits", "WhoAmI", "CountStargazers"))
    )
    assert manifest.scopes == ("GetRepository", "ListRepoCommits", "WhoAmI", "CountStargazers")


def test_no_scopes_at_all_is_rejected():
    with pytest.raises(RecipeValidationError, match="scopes"):
        validate_recipe(_manifest(scopes=()))


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
