"""Tests for RECIPES/readme-star-count-stale/detector.py's own detection
logic (ROADMAP.md #1647) -- the hundred-thirteenth real recipe: the
README's own hardcoded prose star-count claim has fallen behind the live
count.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "readme-star-count-stale" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_readme_star_count_stale_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 9, 21, 15, 0, 0, tzinfo=timezone.utc)


def _readme(path: str, text: str) -> "detector.ReadmeFile":
    return detector.ReadmeFile(
        path=path, text=text,
        url=f"https://github.com/example/example-repo/blob/main/{path}",
    )


def _stars(count: int, checked_at: datetime = _NOW) -> "detector.StarCount":
    return detector.StarCount(
        count=count, checked_at=checked_at,
        url="https://github.com/example/example-repo/stargazers",
    )


class TestStalenessThreshold:
    def test_floor_of_25_below_500(self):
        assert detector._staleness_threshold(100) == 25

    def test_five_percent_above_500(self):
        assert detector._staleness_threshold(1000) == 50


class TestComputeGaps:
    def test_a_bare_claim_the_live_count_has_moved_well_past_is_surfaced(self):
        r = _readme("README.md", "We have 900 GitHub stars!")

        surfaced, excluded = detector.compute_gaps([r], _stars(1400))

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "readme-star-count-stale-README.md"
        assert surfaced[0].confidence == 0.7

    def test_a_claim_the_live_count_has_not_reached_is_excluded(self):
        r = _readme("README.md", "We have 900 stars!")

        surfaced, excluded = detector.compute_gaps([r], _stars(850))

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "readme-star-claim-current-README.md"

    def test_a_claim_equal_to_the_live_count_is_excluded(self):
        r = _readme("README.md", "We have 900 stars!")

        surfaced, excluded = detector.compute_gaps([r], _stars(900))

        assert surfaced == []
        assert excluded[0].slug == "readme-star-claim-current-README.md"

    def test_drift_under_the_noise_floor_is_excluded_not_surfaced(self):
        r = _readme("README.md", "We have 1380+ stars!")

        surfaced, excluded = detector.compute_gaps([r], _stars(1400))

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "readme-star-claim-within-tolerance-README.md"

    def test_a_plus_qualified_claim_can_still_go_stale_past_the_floor(self):
        r = _readme("README.md", "We have 500+ stars!")

        surfaced, excluded = detector.compute_gaps([r], _stars(1400))

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "readme-star-count-stale-README.md"

    def test_a_file_with_no_star_claim_is_excluded_named_not_hidden(self):
        r = _readme("NOTES.md", "Just some scratch notes.")

        surfaced, excluded = detector.compute_gaps([r], _stars(1400))

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "readme-no-star-claim-NOTES.md"

    def test_star_emoji_prefixed_claim_is_parsed(self):
        r = _readme("README.md", "⭐ 900 GitHub stars and counting")

        surfaced, _ = detector.compute_gaps([r], _stars(1400))

        assert len(surfaced) == 1

    def test_comma_thousands_separator_is_parsed(self):
        r = _readme("README.md", "We have 1,200 stars!")

        surfaced, excluded = detector.compute_gaps([r], _stars(1250))

        assert surfaced == []
        assert excluded[0].slug == "readme-star-claim-within-tolerance-README.md"

    def test_multiple_readmes_are_each_evaluated_independently(self):
        stale = _readme("README.md", "900 GitHub stars")
        current = _readme("docs/community.md", "1380+ stars")
        unclaimed = _readme("NOTES.md", "no claim here")

        surfaced, excluded = detector.compute_gaps([stale, current, unclaimed], _stars(1400))

        assert {g.slug for g in surfaced} == {"readme-star-count-stale-README.md"}
        assert {g.slug for g in excluded} == {
            "readme-star-claim-within-tolerance-docs/community.md",
            "readme-no-star-claim-NOTES.md",
        }


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "readme-star-count-stale-README.md"
        assert result["primary_gap"]["confidence"] == 0.7

    def test_the_shipped_fixture_excludes_the_within_tolerance_and_unclaimed_readmes(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "readme-star-claim-within-tolerance-docs/community.md" in excluded_slugs
        assert "readme-no-star-claim-NOTES.md" in excluded_slugs

    def test_output_shape_matches_every_other_recipes_run_recipe_scan(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert set(result.keys()) == {
            "generated_at", "source", "confidence_bar", "separation_margin",
            "primary_gap", "tail", "excluded",
        }
        assert result["source"] == "fixture"


class TestLoaders:
    """load_readme_files/load_star_count -- mirrors every prior recipe's
    own _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_readme_files_parses_the_real_fixture(self):
        readmes = detector.load_readme_files()
        assert len(readmes) > 0
        assert all(isinstance(r, detector.ReadmeFile) for r in readmes)

    def test_load_star_count_parses_the_real_fixture(self):
        stars = detector.load_star_count()
        assert isinstance(stars, detector.StarCount)
        assert stars.count > 0

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_readme_files_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_readme_files(bad_file)
