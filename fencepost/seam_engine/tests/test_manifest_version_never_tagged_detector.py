"""Tests for RECIPES/manifest-version-never-tagged/detector.py's own
detection logic (ROADMAP.md #1607) -- the hundred-eleventh real recipe: a
version manifest (pyproject.toml/package.json/Cargo.toml/...) was bumped,
but no git tag was ever pushed for it.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "manifest-version-never-tagged" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_manifest_version_never_tagged_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)


def _manifest(path: str, version: str) -> "detector.ManifestVersion":
    return detector.ManifestVersion(
        path=path, version=version,
        url=f"https://github.com/example/example-repo/blob/main/{path}",
    )


def _tag(name: str, sha: str = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4",
         pushed_at: datetime = _NOW) -> "detector.Tag":
    return detector.Tag(
        name=name, sha=sha, pushed_at=pushed_at,
        url=f"https://github.com/example/example-repo/releases/tag/{name}",
    )


class TestNormalizeVersion:
    def test_strips_a_single_leading_v(self):
        assert detector._normalize_version("v1.4.0") == "1.4.0"
        assert detector._normalize_version("V1.4.0") == "1.4.0"

    def test_leaves_a_bare_version_untouched(self):
        assert detector._normalize_version("1.4.0") == "1.4.0"

    def test_does_not_touch_anything_past_the_leading_letter(self):
        assert detector._normalize_version("v1.4.0-rc.1") == "1.4.0-rc.1"


class TestComputeGaps:
    def test_a_version_with_no_matching_tag_is_surfaced(self):
        m = _manifest("pyproject.toml", "1.4.0")

        surfaced, excluded = detector.compute_gaps([m], [_tag("v1.3.0")])

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "manifest-version-never-tagged-pyproject.toml-1.4.0"
        assert surfaced[0].confidence == 0.75

    def test_a_version_matching_a_v_prefixed_tag_is_excluded_not_surfaced(self):
        m = _manifest("pyproject.toml", "1.3.0")

        surfaced, excluded = detector.compute_gaps([m], [_tag("v1.3.0")])

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "manifest-tagged-pyproject.toml-1.3.0"
        assert excluded[0].confidence == 0.0

    def test_a_version_matching_a_bare_tag_is_excluded_too(self):
        """Not every real tag carries a leading 'v' -- the normalization
        must hold in both directions, not just manifest-has-no-v."""
        m = _manifest("package.json", "2.0.0")

        surfaced, excluded = detector.compute_gaps([m], [_tag("2.0.0")])

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "manifest-tagged-package.json-2.0.0"

    @pytest.mark.parametrize("version", [
        "2.0.0-rc.1", "2.0.0-alpha", "2.0.0-beta.2", "2.0.0-dev",
        "2.0.0-SNAPSHOT", "2.0.0+build.5", "2.0.0-nightly",
    ])
    def test_a_prerelease_or_build_suffixed_version_is_excluded_outright(self, version: str):
        m = _manifest("package.json", version)

        surfaced, excluded = detector.compute_gaps([m], [])

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].confidence == 0.0
        assert "pre-release" in excluded[0].headline

    def test_multiple_manifests_are_each_evaluated_independently(self):
        tagged = _manifest("Cargo.toml", "1.3.0")
        untagged = _manifest("pyproject.toml", "1.4.0")
        prerelease = _manifest("package.json", "2.0.0-rc.1")

        surfaced, excluded = detector.compute_gaps(
            [tagged, untagged, prerelease], [_tag("v1.3.0")]
        )

        assert {g.slug for g in surfaced} == {"manifest-version-never-tagged-pyproject.toml-1.4.0"}
        assert {g.slug for g in excluded} == {
            "manifest-tagged-Cargo.toml-1.3.0",
            "manifest-prerelease-package.json-2.0.0-rc.1",
        }


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "manifest-version-never-tagged-pyproject.toml-1.4.0"
        assert result["primary_gap"]["confidence"] == 0.75

    def test_the_shipped_fixture_excludes_the_prerelease_and_the_matched_tag(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "manifest-prerelease-package.json-2.0.0-rc.1" in excluded_slugs
        assert "manifest-tagged-Cargo.toml-1.3.0" in excluded_slugs

    def test_output_shape_matches_every_other_recipes_run_recipe_scan(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert set(result.keys()) == {
            "generated_at", "source", "confidence_bar", "separation_margin",
            "primary_gap", "tail", "excluded",
        }
        assert result["source"] == "fixture"


class TestLoaders:
    """load_manifest_versions/load_tags -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_manifest_versions_parses_the_real_fixture(self):
        manifests = detector.load_manifest_versions()
        assert len(manifests) > 0
        assert all(isinstance(m, detector.ManifestVersion) for m in manifests)

    def test_load_tags_parses_the_real_fixture(self):
        tags = detector.load_tags()
        assert len(tags) > 0
        assert all(isinstance(t, detector.Tag) for t in tags)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_manifest_versions_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_manifest_versions(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_tags_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_tags(bad_file)
