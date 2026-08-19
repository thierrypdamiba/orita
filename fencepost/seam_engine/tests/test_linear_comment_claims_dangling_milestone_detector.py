"""Tests for RECIPES/linear-comment-claims-dangling-milestone/detector.py's
own detection logic -- the eighty-fourth real recipe: a Linear issue
comment claims a milestone number that doesn't exist at all.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "linear-comment-claims-dangling-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_linear_comment_claims_dangling_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)


def _comment(id_: str, text: str | None, created_at: datetime, issue_identifier: str = "ENG-900") -> "detector.Comment":
    return detector.Comment(
        id=id_, issue_identifier=issue_identifier, author="example-commenter", text=text or "",
        created_at=created_at,
        url=f"https://linear.app/example-town/issue/{issue_identifier}#comment-{id_}",
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
        assert detector._claimed_milestone_numbers("milestone #9701 shipped.") == [9701]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("see #9702 for background.") == []


class TestComputeGaps:
    def test_a_claim_naming_a_milestone_that_does_not_exist_is_surfaced(self):
        comment = _comment("LIN-2001", "milestone #9701 shipped.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "linear-comment-claims-dangling-milestone-LIN-2001-9701"
        assert surfaced[0].confidence == 0.8

    def test_confidence_is_flat_regardless_of_comment_age(self):
        fresh = _comment("LIN-2002", "milestone #9703 shipped.", _NOW - timedelta(minutes=5))
        stale = _comment("LIN-2003", "milestone #9704 shipped.", _NOW - timedelta(days=365))

        surfaced, _ = detector.compute_gaps([fresh, stale], [], now=_NOW)

        assert {g.confidence for g in surfaced} == {0.8}

    def test_a_claim_naming_a_real_open_milestone_is_excluded_not_surfaced(self):
        comment = _comment("LIN-2004", "milestone #9705 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(9705, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-LIN-2004-9705" in excluded_slugs

    def test_a_claim_naming_a_real_closed_milestone_is_also_excluded(self):
        comment = _comment("LIN-2005", "milestone #9706 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(9706, state="closed")

        surfaced, excluded = detector.compute_gaps([comment], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-LIN-2005-9706" in excluded_slugs

    def test_a_comment_with_no_claim_phrase_produces_no_candidate_at_all(self):
        comment = _comment("LIN-2006", "housekeeping only, see #9707 for background.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-LIN-2006"

    def test_a_comment_with_no_text_at_all_produces_no_candidate_at_all(self):
        comment = _comment("LIN-2007", None, _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_claim_in_one_comment_produces_one_candidate_not_two(self):
        comment = _comment("LIN-2008", "milestone #9701 and milestone #9701 again.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "linear-comment-claims-dangling-milestone-LIN-2008-9701"

    def test_a_bare_hash_mention_alongside_a_real_claim_does_not_produce_a_second_candidate(self):
        comment = _comment("LIN-2009", "milestone #9701 shipped. see #9999 for background.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "linear-comment-claims-dangling-milestone-LIN-2009-9701"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "linear-comment-claims-dangling-milestone-LIN-C-9501-9601"
        assert result["primary_gap"]["confidence"] == 0.8

    def test_the_shipped_fixture_excludes_the_real_claims_and_the_no_claim_comment(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claimed-milestone-exists-LIN-C-9502-9602" in excluded_slugs
        assert "no-claim-phrase-LIN-C-9503" in excluded_slugs
        assert "claimed-milestone-exists-LIN-C-9504-9603" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_9601_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("linear-comment-claims-dangling-milestone-LIN-C-9501-9601") == 1

    def test_the_shipped_fixture_never_examines_the_null_text_comment(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("9505" in s for s in all_slugs)

    def test_source_is_honestly_marked_fixture(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"


class TestLoaders:
    """load_comments/load_milestones -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_comments_parses_the_real_fixture(self):
        comments = detector.load_comments()
        assert len(comments) > 0
        assert all(isinstance(c, detector.Comment) for c in comments)

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_comments_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_comments(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
