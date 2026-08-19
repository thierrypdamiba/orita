"""Tests for RECIPES/mention-claims-dangling-milestone/detector.py's own
detection logic -- the eighty-sixth real recipe: a mortal's own X mention
claims a milestone number that doesn't exist at all.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "mention-claims-dangling-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_mention_claims_dangling_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)


def _mention(id_: str, text: str | None, created_at: datetime) -> "detector.Mention":
    return detector.Mention(
        id=id_, author="example-mortal", text=text or "",
        created_at=created_at,
        url=f"https://x.com/example-mortal/status/{id_}",
    )


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbersReuse:
    """This recipe reuses seam_engine.milestone_claims verbatim -- these
    tests prove the import actually happened, not a second retyped copy."""

    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("milestone #7401 shipped.") == [7401]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("see #7402 for background.") == []


class TestComputeGaps:
    def test_a_claim_naming_a_milestone_that_does_not_exist_is_surfaced(self):
        mention = _mention("M-1001", "milestone #7401 shipped.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "mention-claims-dangling-milestone-M-1001-7401"
        assert surfaced[0].confidence == 0.8

    def test_confidence_is_flat_regardless_of_mention_age(self):
        fresh = _mention("M-1002", "milestone #7403 shipped.", _NOW - timedelta(minutes=5))
        stale = _mention("M-1003", "milestone #7404 shipped.", _NOW - timedelta(days=365))

        surfaced, _ = detector.compute_gaps([fresh, stale], [], now=_NOW)

        assert {g.confidence for g in surfaced} == {0.8}

    def test_a_claim_naming_a_real_open_milestone_is_excluded_not_surfaced(self):
        mention = _mention("M-1004", "milestone #7405 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(7405, state="open")

        surfaced, excluded = detector.compute_gaps([mention], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-M-1004-7405" in excluded_slugs

    def test_a_claim_naming_a_real_closed_milestone_is_also_excluded(self):
        mention = _mention("M-1005", "milestone #7406 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(7406, state="closed")

        surfaced, excluded = detector.compute_gaps([mention], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-M-1005-7406" in excluded_slugs

    def test_a_mention_with_no_claim_phrase_produces_no_candidate_at_all(self):
        mention = _mention("M-1006", "housekeeping only, see #7407 for background.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-M-1006"

    def test_a_mention_with_no_text_at_all_produces_no_candidate_at_all(self):
        mention = _mention("M-1007", None, _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_claim_in_one_mention_produces_one_candidate_not_two(self):
        mention = _mention("M-1008", "milestone #7401 and milestone #7401 again.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "mention-claims-dangling-milestone-M-1008-7401"

    def test_a_bare_hash_mention_alongside_a_real_claim_does_not_produce_a_second_candidate(self):
        mention = _mention("M-1009", "milestone #7401 shipped. see #7999 for background.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "mention-claims-dangling-milestone-M-1009-7401"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "mention-claims-dangling-milestone-M-6301-6301"
        assert result["primary_gap"]["confidence"] == 0.8

    def test_the_shipped_fixture_excludes_the_real_claims_and_the_no_claim_mention(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claimed-milestone-exists-M-6302-6302" in excluded_slugs
        assert "no-claim-phrase-M-6303" in excluded_slugs
        assert "claimed-milestone-exists-M-6304-6303" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_6301_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("mention-claims-dangling-milestone-M-6301-6301") == 1

    def test_the_shipped_fixture_never_examines_the_null_text_mention(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("6305" in s for s in all_slugs)

    def test_source_is_honestly_marked_fixture(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"


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
