"""Tests for RECIPES/issue-comment-claims-open-milestone/detector.py's own
detection logic (ROADMAP.md #591) -- the fifty-ninth real recipe: an
issue or pull request's own ordinary timeline comment claims a milestone
shipped that's still open.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this
test exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-comment-claims-open-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_comment_claims_open_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)


def _comment(cid: int, body: str | None, updated_at: datetime, issue_number: int = 1) -> "detector.IssueComment":
    return detector.IssueComment(
        id=cid, issue_number=issue_number, body=body or "",
        updated_at=updated_at,
        url=f"https://github.com/example/example-repo/issues/{issue_number}#issuecomment-{cid}",
    )


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbers:
    """Exercises the shared seam_engine.milestone_claims grammar through
    this detector's own local alias -- the grammar itself is already
    covered exhaustively by test_milestone_claims.py; this class only
    proves the alias is wired correctly."""

    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("Milestone #6101 shipped.") == [6101]

    def test_case_insensitive(self):
        assert detector._claimed_milestone_numbers("MILESTONE #6102 is done.") == [6102]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("See #6103 for background.") == []

    def test_multiple_claims_in_one_body(self):
        assert detector._claimed_milestone_numbers("Milestone #6101. Milestone #6102.") == [6101, 6102]

    def test_duplicate_claim_in_one_body_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_milestone_numbers("Milestone #6101 and milestone #6101 again.") == [6101, 6101]


class TestComputeGaps:
    def test_a_stale_open_claim_is_surfaced_at_high_confidence(self):
        comment = _comment(1, "This also ships milestone #6101 while we're in here.", _NOW - timedelta(hours=50))
        milestone = _milestone(6101, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [milestone], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-comment-claims-open-milestone-1-6101"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_open_claim_is_surfaced_at_low_confidence(self):
        comment = _comment(2, "I think this closes milestone #6103 too.", _NOW - timedelta(hours=4))
        milestone = _milestone(6103, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_a_claim_at_exactly_the_edit_grace_window_boundary_is_high_confidence(self):
        comment = _comment(2, "Milestone #6103 shipped.", _NOW - timedelta(hours=24))
        milestone = _milestone(6103, state="open")

        surfaced, _ = detector.compute_gaps([comment], [milestone], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_a_closed_claimed_milestone_is_excluded_not_surfaced(self):
        comment = _comment(3, "Milestone #6102 shipped as a side effect.", _NOW - timedelta(hours=50))
        milestone = _milestone(6102, state="closed")

        surfaced, excluded = detector.compute_gaps([comment], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-3-6102" in excluded_slugs

    def test_a_claim_naming_a_milestone_that_does_not_exist_is_excluded_not_surfaced(self):
        comment = _comment(4, "Milestone #6999 today, same root cause.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-not-found-4-6999" in excluded_slugs

    def test_a_comment_with_no_claim_phrase_is_excluded_not_surfaced(self):
        comment = _comment(5, "Same root cause as #6105, not touching here.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-5"

    def test_a_comment_with_no_body_at_all_produces_no_candidate_at_all(self):
        comment = _comment(6, None, _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_claim_in_one_comment_produces_one_candidate_not_two(self):
        comment = _comment(7, "Milestone #6101 shipped today and milestone #6101 confirmed again.", _NOW - timedelta(hours=3))
        milestone = _milestone(6101, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-comment-claims-open-milestone-7-6101"

    def test_a_claim_naming_a_real_pull_request_number_is_treated_as_not_found(self):
        # A "milestone #N" claim phrase names a milestone number, never a
        # PR number -- this test only confirms an out-of-range number
        # (milestone list empty here) is excluded as not-found, the same
        # as a genuinely dangling number.
        comment = _comment(8, "Milestone #500, a number that isn't a real milestone here.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-not-found-8-500" in excluded_slugs


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-comment-claims-open-milestone-8101-6101"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_two_fresh_claims_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-comment-claims-open-milestone-8102-6103" in tail_slugs
        assert "issue-comment-claims-open-milestone-8107-6101" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_dangling_and_no_claim_comments(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-8103-6102" in excluded_slugs
        assert "claimed-milestone-not-found-8104-6999" in excluded_slugs
        assert "no-claim-phrase-8105" in excluded_slugs

    def test_the_shipped_fixtures_null_body_comment_produces_no_candidate(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = set()
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        all_slugs |= {g["slug"] for g in result["tail"]}
        all_slugs |= {g["slug"] for g in result["excluded"]}
        assert not any("-8106-" in s or s.endswith("-8106") for s in all_slugs)

    def test_the_shipped_fixture_deduplicates_the_repeated_6101_claim_within_one_comment(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("issue-comment-claims-open-milestone-8107-6101") == 1


class TestLoaders:
    """load_issue_comments/load_milestones -- mirrors every prior recipe's
    own _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_issue_comments_parses_the_real_fixture(self):
        comments = detector.load_issue_comments()
        assert len(comments) > 0
        assert all(isinstance(c, detector.IssueComment) for c in comments)

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issue_comments_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issue_comments(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
