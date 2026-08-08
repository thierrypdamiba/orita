"""Tests for RECIPES/linear-comment-claims-unfixed-issue/detector.py's own
detection logic -- the sixty-eighth real recipe: a Linear issue comment
invokes a real closing keyword against an issue, but the issue never
actually closed. The Linear-side twin of
test_mention_claims_unfixed_issue_detector.py and
test_slack_message_claims_unfixed_issue_detector.py.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "linear-comment-claims-unfixed-issue" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_linear_comment_claims_unfixed_issue_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)


def _comment(cid: str, text: str, created_at: datetime, author: str = "some-mortal", issue_identifier: str = "ENG-142") -> "detector.Comment":
    return detector.Comment(
        id=cid, issue_identifier=issue_identifier, author=author, text=text, created_at=created_at,
        url=f"https://linear.app/orita-town/issue/{issue_identifier}#comment-{cid}",
    )


def _issue(number: int, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClaimedIssueNumbers:
    def test_fixes_hash_n(self):
        assert detector._claimed_issue_numbers("Fixes #4201.") == [4201]

    def test_closes_hash_n(self):
        assert detector._claimed_issue_numbers("Closes #4202 this time.") == [4202]

    def test_resolves_hash_n(self):
        assert detector._claimed_issue_numbers("Resolves #4203.") == [4203]

    def test_past_tense_fixed_hash_n(self):
        assert detector._claimed_issue_numbers("Fixed #4204.") == [4204]

    def test_case_insensitive(self):
        assert detector._claimed_issue_numbers("FIXES #4205.") == [4205]

    def test_present_participle_closing_never_matches(self):
        # Iron Rule #8's own prescribed safe form must never trip this
        # recipe's claim grammar either.
        assert detector._claimed_issue_numbers("Closing #4206 today, in prose only.") == []

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        # This is a future Linear-side dangling-reference recipe's own
        # broader regex; a bare "see #N" mention in prose is not a
        # fixed-it claim.
        assert detector._claimed_issue_numbers("See #4207 for background.") == []

    def test_multiple_claims_in_one_comment(self):
        assert detector._claimed_issue_numbers("Fixes #4201. Closes #4202.") == [4201, 4202]

    def test_duplicate_claim_in_one_comment_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_issue_numbers("Fixes #4201 and closes #4201 again.") == [4201, 4201]


class TestComputeGaps:
    def test_a_stale_unfixed_claim_is_surfaced_at_high_confidence(self):
        comment = _comment("L-1", "Fixes #4201.", _NOW - timedelta(hours=50))
        issue = _issue(4201, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "linear-comment-claims-unfixed-issue-L-1-4201"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unfixed_claim_is_surfaced_at_low_confidence(self):
        comment = _comment("L-2", "Resolves #4203.", _NOW - timedelta(hours=4))
        issue = _issue(4203, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_closed_claimed_issue_is_excluded_not_surfaced(self):
        comment = _comment("L-3", "Closes #4202.", _NOW - timedelta(hours=50))
        issue = _issue(4202, state="closed")

        surfaced, excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-L-3-4202" in excluded_slugs

    def test_a_claim_naming_an_issue_that_does_not_exist_is_excluded_not_surfaced(self):
        comment = _comment("L-4", "Fix #4999 today.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-issue-not-found-L-4-4999" in excluded_slugs

    def test_a_comment_with_no_claim_phrase_produces_no_candidate_at_all(self):
        comment = _comment("L-5", "Housekeeping only, see #4205 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-L-5"

    def test_a_duplicate_claim_in_one_comment_produces_one_candidate_not_two(self):
        comment = _comment("L-6", "Fixes #4201 and closes #4201 again.", _NOW - timedelta(hours=50))
        issue = _issue(4201, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "linear-comment-claims-unfixed-issue-L-6-4201"

    def test_confidence_boundary_exactly_24_hours_is_stale_not_fresh(self):
        comment = _comment("L-7", "Fixes #4201.", _NOW - timedelta(hours=24))
        issue = _issue(4201, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_confidence_boundary_just_under_24_hours_is_fresh(self):
        comment = _comment("L-8", "Fixes #4201.", _NOW - timedelta(hours=23, minutes=59))
        issue = _issue(4201, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert surfaced[0].confidence == 0.5

    def test_evidence_carries_both_the_comment_url_and_the_issue_url(self):
        comment = _comment("L-9", "Fixes #4201.", _NOW - timedelta(hours=50))
        issue = _issue(4201, state="open")

        surfaced, _excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert surfaced[0].evidence == [comment.url, issue.url]

    def test_excluded_not_found_evidence_carries_only_the_comment_url(self):
        comment = _comment("L-10", "Fix #4999 today.", _NOW - timedelta(hours=50))

        _surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert excluded[0].evidence == [comment.url]

    def test_no_surfaced_or_excluded_candidates_for_an_empty_comment_list(self):
        surfaced, excluded = detector.compute_gaps([], [_issue(4201)], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        stale = _comment("L-11", "Fixes #4201.", _NOW - timedelta(hours=50))
        fresh = _comment("L-12", "Fixes #4203.", _NOW - timedelta(hours=4))
        issues = [_issue(4201, state="open"), _issue(4203, state="open")]

        surfaced, _excluded = detector.compute_gaps([fresh, stale], issues, now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.5]

    def test_headline_and_detail_never_grade_or_blame_the_commenter(self):
        # CONTRIBUTING.md's "No grading, ever" law: the text may name the
        # gap, never the commenter's own error.
        comment = _comment("L-13", "Fixes #4201.", _NOW - timedelta(hours=50), author="some-mortal")
        issue = _issue(4201, state="open")

        surfaced, _excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        combined = (surfaced[0].headline + surfaced[0].detail).lower()
        for word in ("mistake", "wrong", "blame", "dropped the ball", "error", "fault"):
            assert word not in combined


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "linear-comment-claims-unfixed-issue-LIN-C-4201-4201"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "linear-comment-claims-unfixed-issue-LIN-C-4202-4203" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_not_found_and_no_claim_comments(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-LIN-C-4203-4202" in excluded_slugs
        assert "claimed-issue-not-found-LIN-C-4204-4999" in excluded_slugs
        assert "no-claim-phrase-LIN-C-4205" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_4201_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("linear-comment-claims-unfixed-issue-LIN-C-4201-4201") == 1

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
    """load_comments/load_issues -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_comments_parses_the_real_fixture(self):
        comments = detector.load_comments()
        assert len(comments) > 0
        assert all(isinstance(c, detector.Comment) for c in comments)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_comments_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_comments(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)


class TestManifest:
    """The manifest itself: schema-valid, clears the oath, matches the
    fixture/detector this test file exercises."""

    def test_recipe_json_clears_validate_recipe(self):
        from seam_engine.recipes import load_recipe_manifest, validate_recipe

        manifest_path = FENCEPOST_ROOT / "RECIPES" / "linear-comment-claims-unfixed-issue" / "recipe.json"
        manifest = load_recipe_manifest(manifest_path)
        validated = validate_recipe(manifest)
        assert validated.slug == "linear-comment-claims-unfixed-issue"
        assert validated.toolkit == "linear+github"
        assert set(validated.scopes) == {"SearchIssueComments", "ListIssues"}
