"""Tests for RECIPES/release-claims-open-milestone/detector.py's own
detection logic (ROADMAP.md #385) -- the sixteenth real recipe: a GitHub
release's own body text claims a milestone shipped, but the milestone never
actually closed.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "release-claims-open-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_release_claims_open_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _release(tag: str, body: str, published_at: datetime) -> "detector.Release":
    return detector.Release(
        id=f"REL-{tag}", title=f"Release {tag}", tag=tag, body=body,
        published_at=published_at, url=f"https://github.com/example/example-repo/releases/tag/{tag}",
    )


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbers:
    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("Milestone #4001 shipped.") == [4001]

    def test_case_insensitive(self):
        assert detector._claimed_milestone_numbers("MILESTONE #4002 is done.") == [4002]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("See #4003 for background.") == []

    def test_multiple_claims_in_one_body(self):
        assert detector._claimed_milestone_numbers("Milestone #4001. Milestone #4002.") == [4001, 4002]

    def test_duplicate_claim_in_one_body_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_milestone_numbers("Milestone #4001 and milestone #4001 again.") == [4001, 4001]


class TestComputeGaps:
    def test_a_stale_open_claim_is_surfaced_at_high_confidence(self):
        release = _release("v1.0", "Milestone #4001 shipped.", _NOW - timedelta(hours=50))
        milestone = _milestone(4001, state="open")

        surfaced, excluded = detector.compute_gaps([release], [milestone], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "release-claims-open-milestone-v1.0-4001"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_open_claim_is_surfaced_at_low_confidence(self):
        release = _release("v1.1", "Milestone #4003 shipped.", _NOW - timedelta(hours=4))
        milestone = _milestone(4003, state="open")

        surfaced, excluded = detector.compute_gaps([release], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_closed_claimed_milestone_is_excluded_not_surfaced(self):
        release = _release("v1.2", "Milestone #4004 shipped.", _NOW - timedelta(hours=50))
        milestone = _milestone(4004, state="closed")

        surfaced, excluded = detector.compute_gaps([release], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-v1.2-4004" in excluded_slugs

    def test_a_claim_naming_a_milestone_that_does_not_exist_is_excluded_not_surfaced(self):
        release = _release("v1.3", "Milestone #4999 shipped.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([release], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-not-found-v1.3-4999" in excluded_slugs

    def test_a_release_with_no_claim_phrase_produces_no_candidate_at_all(self):
        release = _release("v1.4", "Housekeeping only, see #4005 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([release], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-v1.4"

    def test_a_duplicate_claim_in_one_body_produces_one_candidate_not_two(self):
        release = _release("v1.5", "Milestone #4001 and milestone #4001 again.", _NOW - timedelta(hours=50))
        milestone = _milestone(4001, state="open")

        surfaced, excluded = detector.compute_gaps([release], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "release-claims-open-milestone-v1.5-4001"

    def test_a_bare_hash_mention_with_no_milestone_word_does_not_clear_a_real_gap(self):
        release = _release("v1.6", "Milestone #4001 shipped. See #4999 for background.", _NOW - timedelta(hours=50))
        milestone = _milestone(4001, state="open")

        surfaced, excluded = detector.compute_gaps([release], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "release-claims-open-milestone-v1.6-4001"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "release-claims-open-milestone-v1.6.0-4001"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "release-claims-open-milestone-v1.6.1-4003" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_and_no_claim_releases(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-v1.6.4-4004" in excluded_slugs
        assert "claimed-milestone-not-found-v1.6.2-4999" in excluded_slugs
        assert "no-claim-phrase-v1.6.3" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_4001_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("release-claims-open-milestone-v1.6.0-4001") == 1


class TestLoaders:
    """load_releases/load_milestones -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_releases_parses_the_real_fixture(self):
        releases = detector.load_releases()
        assert len(releases) > 0
        assert all(isinstance(r, detector.Release) for r in releases)

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_releases_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_releases(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
