"""Tests for RECIPES/mention-claims-open-milestone/detector.py's own
detection logic -- the forty-eighth real recipe: a mortal's own X mention
of the connected account claims a milestone shipped, but the named
milestone never actually closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "mention-claims-open-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_mention_claims_open_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)


def _mention(mid: str, text: str, created_at: datetime, author: str = "some-mortal") -> "detector.Mention":
    return detector.Mention(
        id=mid, author=author, text=text, created_at=created_at,
        url=f"https://x.com/{author}/status/{mid}",
    )


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbers:
    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("Milestone #5301 shipped.") == [5301]

    def test_case_insensitive(self):
        assert detector._claimed_milestone_numbers("MILESTONE #5302 done.") == [5302]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("See #5303 for background.") == []

    def test_multiple_claims_in_one_mention(self):
        assert detector._claimed_milestone_numbers("Milestone #5301. Milestone #5302.") == [5301, 5302]

    def test_duplicate_claim_in_one_mention_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_milestone_numbers("Milestone #5301 and milestone #5301 again.") == [5301, 5301]


class TestComputeGaps:
    def test_a_stale_open_claim_is_surfaced_at_high_confidence(self):
        mention = _mention("M-1", "Milestone #5301 shipped.", _NOW - timedelta(hours=50))
        milestone = _milestone(5301, state="open")

        surfaced, excluded = detector.compute_gaps([mention], [milestone], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "mention-claims-open-milestone-M-1-5301"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_open_claim_is_surfaced_at_low_confidence(self):
        mention = _mention("M-2", "Milestone #5303 done.", _NOW - timedelta(hours=4))
        milestone = _milestone(5303, state="open")

        surfaced, excluded = detector.compute_gaps([mention], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_closed_claimed_milestone_is_excluded_not_surfaced(self):
        mention = _mention("M-3", "Milestone #5302 wrapped up.", _NOW - timedelta(hours=50))
        milestone = _milestone(5302, state="closed")

        surfaced, excluded = detector.compute_gaps([mention], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-M-3-5302" in excluded_slugs

    def test_a_claim_naming_a_milestone_that_does_not_exist_is_excluded_not_surfaced(self):
        mention = _mention("M-4", "Milestone #5999 shipped today.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-not-found-M-4-5999" in excluded_slugs

    def test_a_mention_with_no_claim_phrase_produces_no_candidate_at_all(self):
        mention = _mention("M-5", "Housekeeping only, see #5305 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-M-5"

    def test_a_duplicate_claim_in_one_mention_produces_one_candidate_not_two(self):
        mention = _mention("M-6", "Milestone #5301 shipped and milestone #5301 confirmed again.", _NOW - timedelta(hours=50))
        milestone = _milestone(5301, state="open")

        surfaced, excluded = detector.compute_gaps([mention], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "mention-claims-open-milestone-M-6-5301"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "mention-claims-open-milestone-M-5301-5301"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "mention-claims-open-milestone-M-5302-5303" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_and_no_claim_mentions(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-M-5303-5302" in excluded_slugs
        assert "claimed-milestone-not-found-M-5304-5999" in excluded_slugs
        assert "no-claim-phrase-M-5305" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_5301_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("mention-claims-open-milestone-M-5301-5301") == 1


class TestLoaders:
    """load_mentions/load_milestones -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_mentions_parses_the_real_fixture(self):
        mentions = detector.load_mentions()
        assert len(mentions) > 0
        assert all(isinstance(m, detector.Mention) for m in mentions)

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_mentions_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_mentions(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
