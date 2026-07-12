"""Doctrine tests for CONTRIBUTING.md + recipes.py (ROADMAP.md #22) — same
shape of law as test_connect_doctrine.py and test_draftback_doctrine.py:
CONTRIBUTING.md's schema table must not silently drift from
`seam_engine.recipes`'s actual constants, and the oath it promises must be
provably enforced in code, not merely asked for in prose.

The done-condition for task 22 is "a first external recipe PR is mergeable
under the oath." This file is where that claim is made literal: it runs
`discover_recipes()` — the exact function CI runs over a PR — against the
real repo tree, proves the shipped reference recipe clears it cleanly, and
proves a write-scoped recipe does not.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from seam_engine import recipes
from seam_engine.recipes import (
    MANIFEST_FILENAME,
    RECIPES_DIR_NAME,
    REQUIRED_FIELDS,
    RecipeValidationError,
    discover_recipes,
)

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
CONTRIBUTING_MD = FENCEPOST_ROOT / "CONTRIBUTING.md"
RECIPES_README = FENCEPOST_ROOT / RECIPES_DIR_NAME / "README.md"
REFERENCE_DIR = FENCEPOST_ROOT / RECIPES_DIR_NAME / "example-release-vs-changelog"

FORBIDDEN_SCOPE_EXAMPLES = (
    "SendEmail", "CreateEvent", "DeleteIssue", "PostTweet", "ModifyLabels",
)
NEGATION_CUES = ("never", "cannot", "may not", "won't", "not ", "refused", "no more forgiving")


def _contributing() -> str:
    assert CONTRIBUTING_MD.exists(), "CONTRIBUTING.md must exist — task 22 isn't done until it does"
    return CONTRIBUTING_MD.read_text(encoding="utf-8")


# --- CONTRIBUTING.md exists and is not a stub --------------------------------


def test_contributing_md_exists_and_is_not_a_stub():
    assert len(_contributing()) > 2000, "CONTRIBUTING.md reads like a stub, not a schema doc"


def test_recipes_readme_exists_and_points_at_contributing():
    assert RECIPES_README.exists()
    assert "CONTRIBUTING.md" in RECIPES_README.read_text(encoding="utf-8")


def test_fencepost_readme_links_to_contributing_and_the_reference_recipe():
    text = (FENCEPOST_ROOT / "README.md").read_text(encoding="utf-8")
    assert "CONTRIBUTING.md" in text
    assert "example-release-vs-changelog" in text


# --- the schema table cannot silently drift from the code --------------------


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_contributing_md_documents_every_required_field(field: str):
    assert f"`{field}`" in _contributing(), (
        f"recipes.REQUIRED_FIELDS names {field!r}, but CONTRIBUTING.md's "
        "schema table doesn't mention it — the doc and the validator have drifted"
    )


def test_contributing_md_names_the_manifest_filename_and_directory():
    text = _contributing()
    assert MANIFEST_FILENAME in text
    assert RECIPES_DIR_NAME in text


def test_contributing_md_quotes_the_scopes_md_oath_line():
    text = _contributing()
    for prefix in ("Get*", "List*", "Read*", "Search*", "Count*", "WhoAmI"):
        assert prefix in text, f"CONTRIBUTING.md must quote SCOPES.md's oath line ({prefix!r} missing)"


@pytest.mark.parametrize("verb", sorted(recipes._FORBIDDEN_VERBS))
def test_contributing_md_names_every_forbidden_verb(verb: str):
    text = _contributing()
    assert verb in text, (
        f"recipes._FORBIDDEN_VERBS contains {verb!r}, but CONTRIBUTING.md's "
        "deny-list prose doesn't name it"
    )


def test_contributing_md_documents_the_local_preflight_command():
    assert "python -m seam_engine.recipes discover" in _contributing()


def test_contributing_md_documents_mock_only():
    text = _contributing().lower()
    assert "mock only" in text
    assert "fixtures/" in _contributing()


def test_contributing_md_carries_the_no_grading_law():
    text = _contributing().lower()
    assert "grad" in text  # "grading" / "grades"
    assert "rank" in text


# --- the oath is enforced in code, not just described in prose --------------


@pytest.mark.parametrize("scope", FORBIDDEN_SCOPE_EXAMPLES)
def test_write_scoped_recipe_is_rejected_by_the_real_validator(tmp_path: Path, scope: str):
    """The literal done-condition check: a recipe declaring a write/send/
    delete/post scope must be rejected — through the same discover_recipes
    a real PR would be checked with, not just validate_recipe in isolation."""
    recipes_dir = tmp_path / RECIPES_DIR_NAME
    d = recipes_dir / "write-scoped-recipe"
    d.mkdir(parents=True)
    (d / "recipe.json").write_text(json.dumps({
        "slug": "write-scoped-recipe", "title": "A recipe that shouldn't merge",
        "author": "attacker", "description": "Tries to sneak a write scope in.",
        "toolkit": "github", "scopes": [scope],
        "fixture": "fixtures/write-scoped-recipe",
        "detector_file": "detector.py", "entrypoint": "run_recipe_scan",
        "confidence_notes": "n/a",
    }))
    (d / "detector.py").write_text("def run_recipe_scan():\n    return {}\n")

    with pytest.raises(RecipeValidationError, match="not read-only"):
        discover_recipes(tmp_path)


# --- the shipped reference recipe is the proof the done-condition holds -----


def test_reference_recipe_directory_exists():
    assert REFERENCE_DIR.is_dir(), "RECIPES/example-release-vs-changelog/ must exist"
    assert (REFERENCE_DIR / MANIFEST_FILENAME).exists()
    assert (REFERENCE_DIR / "detector.py").exists()


def test_the_real_repo_tree_discovers_cleanly():
    """The done-condition, run for real: `discover_recipes()` against the
    actual fencepost/ tree — not a synthetic tmp_path — must return without
    raising, and the reference recipe must be in the result. This is what
    'a first external recipe PR is mergeable under the oath' means: the
    exact check a PR would be held to already passes against what's here."""
    manifests = discover_recipes(FENCEPOST_ROOT)
    assert len(manifests) >= 1
    slugs = {m.slug for m in manifests}
    assert "example-release-vs-changelog" in slugs


def test_reference_recipes_fixture_lives_under_fixtures_dir():
    manifest = next(
        m for m in discover_recipes(FENCEPOST_ROOT) if m.slug == "example-release-vs-changelog"
    )
    assert manifest.fixture.startswith("fixtures/")
    assert (FENCEPOST_ROOT / manifest.fixture).is_dir()


def test_reference_recipes_scopes_are_already_on_scopes_md_table():
    """The example recipe asks for nothing SCOPES.md doesn't already grant
    the GitHub toolkit — it needs no new gateway scope to graduate."""
    scopes_md = (FENCEPOST_ROOT / "SCOPES.md").read_text(encoding="utf-8")
    manifest = next(
        m for m in discover_recipes(FENCEPOST_ROOT) if m.slug == "example-release-vs-changelog"
    )
    for scope in manifest.scopes:
        assert scope in scopes_md, f"{scope!r} isn't on SCOPES.md's table"
