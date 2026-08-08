"""Tests for RECIPES/linear-comment-claims-unmerged-pr/detector.py's own
detection logic -- the seventy-first real recipe: a comment left on a
Linear issue claims a pull request shipped, but the named PR never
actually merged. The PR-claim twin of
test_linear_comment_claims_open_milestone_detector.py, and the Linear-side
twin of test_review_comment_claims_unmerged_pr_detector.py.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "linear-comment-claims-unmerged-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_linear_comment_claims_unmerged_pr_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


def _comment(cid: str, text: str, created_at: datetime, author: str = "some-mortal", issue_identifier: str = "ENG-310") -> "detector.Comment":
    return detector.Comment(
        id=cid, issue_identifier=issue_identifier, author=author, text=text, created_at=created_at,
        url=f"https://linear.app/orita-town/issue/{issue_identifier}#comment-{cid}",
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
        assert detector._claimed_pr_numbers("This also ships #501.") == [501]

    def test_includes_hash_n(self):
        assert detector._claimed_pr_numbers("Includes #502 as a side effect.") == [502]

    def test_merges_hash_n(self):
        assert detector._claimed_pr_numbers("I think this merges #503 too.") == [503]

    def test_via_hash_n(self):
        assert detector._claimed_pr_numbers("Fixed via #504 in the last commit.") == [504]

    def test_case_insensitive(self):
        assert detector._claimed_pr_numbers("SHIPS #505.") == [505]

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        assert detector._claimed_pr_numbers("Same root cause as #507, not touching here.") == []

    def test_multiple_claims_in_one_comment(self):
        assert detector._claimed_pr_numbers("Ships #501. Also merges #502.") == [501, 502]

    def test_duplicate_claim_in_one_comment_is_not_deduplicated_at_extraction(self):
        assert detector._claimed_pr_numbers("Ships #501 -- yes, really via #501.") == [501, 501]


class TestComputeGaps:
    def test_a_stale_unmerged_claim_is_surfaced_at_high_confidence(self):
        comment = _comment("L-1", "Ships #501 finally.", _NOW - timedelta(hours=50))
        pr = _pull(501, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "linear-comment-claims-unmerged-pr-L-1-501"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unmerged_claim_is_surfaced_at_low_confidence(self):
        comment = _comment("L-2", "Heard this merges #503, nice fix.", _NOW - timedelta(hours=4))
        pr = _pull(503, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_confidence_boundary_exactly_24_hours_is_stale_not_fresh(self):
        comment = _comment("L-3", "Includes #503.", _NOW - timedelta(hours=24))
        pr = _pull(503, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_confidence_boundary_just_under_24_hours_is_fresh(self):
        comment = _comment("L-4", "Includes #503.", _NOW - timedelta(hours=23, minutes=59))
        pr = _pull(503, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert surfaced[0].confidence == 0.5

    def test_a_merged_claimed_pr_is_excluded_not_surfaced(self):
        comment = _comment("L-5", "Includes #502 as a side effect.", _NOW - timedelta(hours=50))
        pr = _pull(502, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-L-5-502" in excluded_slugs

    def test_a_closed_but_unmerged_claimed_pr_is_still_surfaced(self):
        # Closed without merging is still a false "shipped" claim -- the
        # PR's own state disagrees with the Linear comment either way.
        comment = _comment("L-6", "Ships #504 today.", _NOW - timedelta(hours=50))
        pr = _pull(504, state="closed", merged=False)

        surfaced, excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.85

    def test_a_claim_naming_a_pr_that_does_not_exist_is_excluded_not_surfaced(self):
        comment = _comment("L-7", "Ships #999 today, guess it landed.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-L-7-999" in excluded_slugs

    def test_a_comment_with_no_claim_phrase_produces_no_candidate_at_all(self):
        comment = _comment("L-8", "Another quiet week, see #505 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-L-8"

    def test_a_duplicate_claim_in_one_comment_produces_one_candidate_not_two(self):
        comment = _comment("L-9", "Ships #501 -- yes, really via #501.", _NOW - timedelta(hours=50))
        pr = _pull(501, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "linear-comment-claims-unmerged-pr-L-9-501"

    def test_evidence_carries_both_the_comment_url_and_the_pr_url(self):
        comment = _comment("L-10", "Ships #501 finally.", _NOW - timedelta(hours=50))
        pr = _pull(501, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        assert surfaced[0].evidence == [comment.url, pr.url]

    def test_excluded_not_found_evidence_carries_only_the_comment_url(self):
        comment = _comment("L-11", "Ships #999 today.", _NOW - timedelta(hours=50))

        _surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert excluded[0].evidence == [comment.url]

    def test_no_surfaced_or_excluded_candidates_for_an_empty_comment_list(self):
        surfaced, excluded = detector.compute_gaps([], [_pull(501)], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        stale = _comment("L-12", "Ships #501 finally.", _NOW - timedelta(hours=50))
        fresh = _comment("L-13", "Ships #503 finally.", _NOW - timedelta(hours=4))
        pulls = [_pull(501, state="open", merged=False), _pull(503, state="open", merged=False)]

        surfaced, _excluded = detector.compute_gaps([fresh, stale], pulls, now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.5]

    def test_headline_and_detail_never_grade_or_blame_the_commenter(self):
        # CONTRIBUTING.md's "No grading, ever" law: the text may name the
        # gap, never the commenter's own error.
        comment = _comment("L-14", "Ships #501 finally.", _NOW - timedelta(hours=50), author="some-mortal")
        pr = _pull(501, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([comment], [pr], now=_NOW)

        combined = (surfaced[0].headline + surfaced[0].detail).lower()
        for word in ("mistake", "wrong", "blame", "dropped the ball", "error", "fault"):
            assert word not in combined


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "linear-comment-claims-unmerged-pr-LIN-C-4601-501"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "linear-comment-claims-unmerged-pr-LIN-C-4602-503" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_not_found_and_no_claim_comments(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-LIN-C-4603-502" in excluded_slugs
        assert "claimed-pr-not-found-LIN-C-4604-999" in excluded_slugs
        assert "no-claim-phrase-LIN-C-4605" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_501_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("linear-comment-claims-unmerged-pr-LIN-C-4601-501") == 1

    def test_source_is_marked_fixture_not_live(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"

    def test_run_recipe_scan_defaults_now_to_the_real_wall_clock_when_omitted(self):
        before = datetime.now(timezone.utc)
        result = detector.run_recipe_scan()
        after = datetime.now(timezone.utc)
        generated_at = datetime.fromisoformat(result["generated_at"])
        assert before <= generated_at <= after


class TestLoaders:
    """load_comments/load_pulls -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_comments_parses_the_real_fixture(self):
        comments = detector.load_comments()
        assert len(comments) > 0
        assert all(isinstance(c, detector.Comment) for c in comments)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_comments_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_comments(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)


class TestManifest:
    """The manifest itself: schema-valid, clears the oath, matches the
    fixture/detector this test file exercises."""

    def test_recipe_json_clears_validate_recipe(self):
        from seam_engine.recipes import load_recipe_manifest, validate_recipe

        manifest_path = FENCEPOST_ROOT / "RECIPES" / "linear-comment-claims-unmerged-pr" / "recipe.json"
        manifest = load_recipe_manifest(manifest_path)
        validated = validate_recipe(manifest)
        assert validated.slug == "linear-comment-claims-unmerged-pr"
        assert validated.toolkit == "linear+github"
        assert set(validated.scopes) == {"SearchIssueComments", "ListPullRequests"}
