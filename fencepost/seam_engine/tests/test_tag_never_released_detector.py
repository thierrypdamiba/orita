"""Tests for RECIPES/tag-never-released/detector.py's own detection logic
(ROADMAP.md #653) -- the seventy-eighth real recipe: a git tag was pushed,
but no GitHub Release was ever published for it.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "tag-never-released" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_tag_never_released_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 2, 12, 0, 0, tzinfo=timezone.utc)


def _tag(name: str, pushed_at: datetime, sha: str = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4") -> "detector.Tag":
    return detector.Tag(
        name=name, sha=sha, pushed_at=pushed_at,
        url=f"https://github.com/example/example-repo/tree/{name}",
    )


def _release(tag_name: str, published_at: datetime, rel_id: str = "rel_1") -> "detector.Release":
    return detector.Release(
        tag_name=tag_name, name=f"{tag_name} release", id=rel_id, published_at=published_at,
        url=f"https://github.com/example/example-repo/releases/tag/{tag_name}",
    )


class TestComputeGaps:
    def test_a_tag_with_a_matching_release_is_excluded_not_surfaced(self):
        tag = _tag("v2.0.0", datetime(2026, 7, 1, tzinfo=timezone.utc))
        release = _release("v2.0.0", datetime(2026, 7, 1, 1, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([tag], [release], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "tag-released-v2.0.0"
        assert excluded[0].confidence == 0.0

    def test_an_unreleased_tag_past_the_bar_is_surfaced_at_high_confidence(self):
        tag = _tag("v2.1.0", datetime(2026, 7, 1, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([tag], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "tag-never-released-v2.1.0"
        assert surfaced[0].confidence == 0.85

    def test_a_freshly_pushed_unreleased_tag_is_surfaced_at_low_confidence(self):
        tag = _tag("v2.2.0-rc1", datetime(2026, 8, 2, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([tag], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_release_with_a_different_tag_name_leaves_the_tag_unreleased(self):
        tag = _tag("v3.0.0", datetime(2026, 6, 1, tzinfo=timezone.utc))
        unrelated_release = _release("v3.0.0-different", datetime(2026, 6, 2, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([tag], [unrelated_release], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "tag-never-released-v3.0.0"

    def test_multiple_tags_are_each_evaluated_independently(self):
        released = _tag("v4.0.0", datetime(2026, 5, 1, tzinfo=timezone.utc))
        stale_unreleased = _tag("v4.1.0", datetime(2026, 6, 1, tzinfo=timezone.utc))
        release = _release("v4.0.0", datetime(2026, 5, 1, 1, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([released, stale_unreleased], [release], now=_NOW)

        assert {g.slug for g in excluded} == {"tag-released-v4.0.0"}
        assert {g.slug for g in surfaced} == {"tag-never-released-v4.1.0"}


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "tag-never-released-v1.1.0"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_tag_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "tag-never-released-v1.2.0-rc1" in tail_slugs

    def test_the_shipped_fixture_excludes_the_already_released_tags(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "tag-released-v0.9.0" in excluded_slugs
        assert "tag-released-v1.0.0" in excluded_slugs


class TestLoaders:
    """load_tags/load_releases -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_tags_parses_the_real_fixture(self):
        tags = detector.load_tags()
        assert len(tags) > 0
        assert all(isinstance(t, detector.Tag) for t in tags)

    def test_load_releases_parses_the_real_fixture(self):
        releases = detector.load_releases()
        assert len(releases) > 0
        assert all(isinstance(r, detector.Release) for r in releases)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_tags_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_tags(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_releases_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_releases(bad_file)
