"""Tests for RECIPES/review-comment-claims-unmerged-pr/detector.py's own
detection logic -- the fifty-fifth real recipe: a pull request's own
inline code review comment invokes a real ships/includes/merges/via #N
claim against a PR, but the PR never actually merged.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "review-comment-claims-unmerged-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_review_comment_claims_unmerged_pr_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)


def _comment(cid: int, body: str | None, updated_at: datetime, pr_number: int = 1) -> "detector.ReviewComment":
    return detector.ReviewComment(
        id=cid, pull_request_number=pr_number, body=body or "",
        updated_at=updated_at,
        url=f"https://github.com/example/example-repo/pull/{pr_number}#discussion_r{cid}",
    )


def _pull(number: int, state: str = "open", merged: bool = False) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestClaimedPrNumbersReuse:
    """detector.py imports seam_engine.pr_claims.claimed_pr_numbers rather
    than retyping the grammar -- these tests exercise it through the
    detector's own bound name, proving the import actually landed and
    behaves as every sibling *-claims-unmerged-pr recipe expects."""

    def test_ships_hash_n(self):
        assert detector._claimed_pr_numbers("This also ships #901.") == [901]

    def test_includes_hash_n(self):
        assert detector._claimed_pr_numbers("Includes #902 as a side effect.") == [902]

    def test_merges_hash_n(self):
        assert detector._claimed_pr_numbers("I think this merges #903 too.") == [903]

    def test_via_hash_n(self):
        assert detector._claimed_pr_numbers("Fixed via #904 in the last commit.") == [904]

    def test_case_insensitive(self):
        assert detector._claimed_pr_numbers("SHIPS #905.") == [905]

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        assert detector._claimed_pr_numbers("Same root cause as #907, not touching here.") == []

    def test_multiple_claims_in_one_comment(self):
        assert detector._claimed_pr_numbers("Ships #901. Also merges #902.") == [901, 902]

    def test_duplicate_claim_in_one_comment_is_not_deduplicated_at_extraction(self):
        assert detector._claimed_pr_numbers("Ships #901 -- yes, really via #901.") == [901, 901]


class TestComputeGaps:
    def test_a_stale_unmerged_claim_is_surfaced_at_high_confidence(self):
        comment = _comment(1, "This also ships #901 while we're in here.", _NOW - timedelta(hours=50))
        pr = _pull(901, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "review-comment-claims-unmerged-pr-1-901"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unmerged_claim_is_surfaced_at_low_confidence(self):
        comment = _comment(2, "I think this merges #903 too.", _NOW - timedelta(hours=4))
        pr = _pull(903, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_a_claim_at_exactly_the_edit_grace_window_boundary_is_high_confidence(self):
        comment = _comment(2, "Includes #903.", _NOW - timedelta(hours=24))
        pr = _pull(903, state="open", merged=False)

        surfaced, _ = detector.compute_gaps([comment], [pr], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_a_merged_claimed_pr_is_excluded_not_surfaced(self):
        comment = _comment(3, "Includes #902 as a side effect.", _NOW - timedelta(hours=50))
        pr = _pull(902, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-3-902" in excluded_slugs

    def test_a_closed_but_unmerged_claimed_pr_is_still_surfaced(self):
        # Closed without merging is still a false "shipped" claim -- the
        # PR's own state disagrees with the review comment either way.
        comment = _comment(9, "Ships #904 today.", _NOW - timedelta(hours=50))
        pr = _pull(904, state="closed", merged=False)

        surfaced, excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.85

    def test_a_claim_naming_a_pr_that_does_not_exist_is_excluded_not_surfaced(self):
        comment = _comment(4, "Ships #999 today, same root cause.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-4-999" in excluded_slugs

    def test_a_comment_with_no_claim_phrase_is_excluded_not_surfaced(self):
        comment = _comment(5, "Same root cause as #905, not touching here.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-5"

    def test_a_comment_with_no_body_at_all_produces_no_candidate_at_all(self):
        comment = _comment(6, None, _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_claim_in_one_comment_produces_one_candidate_not_two(self):
        comment = _comment(7, "Ships #901 -- yes, really via #901.", _NOW - timedelta(hours=3))
        pr = _pull(901, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "review-comment-claims-unmerged-pr-7-901"

    def test_a_claim_naming_a_real_issue_number_is_treated_as_not_found(self):
        # This recipe deliberately checks only the PR list, never the
        # issue list -- the mirror boundary review-comment-claims-
        # unfixed-issue already holds for the issue side.
        comment = _comment(8, "Ships #500, a real issue number in this repo.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-8-500" in excluded_slugs


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "review-comment-claims-unmerged-pr-9201-901"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_two_fresh_claims_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "review-comment-claims-unmerged-pr-9202-903" in tail_slugs
        assert "review-comment-claims-unmerged-pr-9207-901" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_dangling_and_no_claim_comments(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-9203-902" in excluded_slugs
        assert "claimed-pr-not-found-9204-999" in excluded_slugs
        assert "no-claim-phrase-9205" in excluded_slugs

    def test_the_shipped_fixtures_null_body_comment_produces_no_candidate(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = set()
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        all_slugs |= {g["slug"] for g in result["tail"]}
        all_slugs |= {g["slug"] for g in result["excluded"]}
        assert not any("-9206-" in s or s.endswith("-9206") for s in all_slugs)

    def test_the_shipped_fixture_deduplicates_the_repeated_901_claim_within_one_comment(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("review-comment-claims-unmerged-pr-9207-901") == 1


class TestLoaders:
    """load_review_comments/load_pulls -- mirrors every prior recipe's
    own _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_review_comments_parses_the_real_fixture(self):
        comments = detector.load_review_comments()
        assert len(comments) > 0
        assert all(isinstance(c, detector.ReviewComment) for c in comments)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_review_comments_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_review_comments(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
