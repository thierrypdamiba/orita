"""Tests for RECIPES/issue-comment-claims-unfixed-issue/detector.py's own
detection logic -- the fifty-eighth real recipe: an issue or pull
request's own ordinary timeline comment invokes a real closing keyword
against an issue, but the issue never actually closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-comment-claims-unfixed-issue" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_comment_claims_unfixed_issue_test", DETECTOR_PATH)
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


def _issue(number: int, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClaimedIssueNumbers:
    def test_fixes_hash_n(self):
        assert detector._claimed_issue_numbers("This also fixes #2201.") == [2201]

    def test_closes_hash_n(self):
        assert detector._claimed_issue_numbers("Closes #2202 as a side effect.") == [2202]

    def test_resolves_hash_n(self):
        assert detector._claimed_issue_numbers("I think this resolves #2203 too.") == [2203]

    def test_past_tense_fixed_hash_n(self):
        assert detector._claimed_issue_numbers("Fixed #2204 in the last commit.") == [2204]

    def test_case_insensitive(self):
        assert detector._claimed_issue_numbers("FIXES #2205.") == [2205]

    def test_present_participle_closing_never_matches(self):
        # Iron Rule #8's own prescribed safe form must never trip this
        # recipe's claim grammar either.
        assert detector._claimed_issue_numbers("Closing #2206 today, in prose only.") == []

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        # This is issue-body-dangling-reference's/issue-comment-dangling-
        # reference's own broader regex; a bare "same root cause as #N"
        # aside is not a fixed-it claim.
        assert detector._claimed_issue_numbers("Same root cause as #2207, not touching here.") == []

    def test_multiple_claims_in_one_comment(self):
        assert detector._claimed_issue_numbers("Fixes #2201. Also closes #2202.") == [2201, 2202]

    def test_duplicate_claim_in_one_comment_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_issue_numbers("Fixes #2201 -- yes, really closes #2201.") == [2201, 2201]


class TestComputeGaps:
    def test_a_stale_unfixed_claim_is_surfaced_at_high_confidence(self):
        comment = _comment(1, "This also fixes #2201 while we're in here.", _NOW - timedelta(hours=50))
        issue = _issue(2201, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-comment-claims-unfixed-issue-1-2201"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unfixed_claim_is_surfaced_at_low_confidence(self):
        comment = _comment(2, "I think this resolves #2203 too.", _NOW - timedelta(hours=4))
        issue = _issue(2203, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_a_claim_at_exactly_the_edit_grace_window_boundary_is_high_confidence(self):
        comment = _comment(2, "Closes #2203.", _NOW - timedelta(hours=24))
        issue = _issue(2203, state="open")

        surfaced, _ = detector.compute_gaps([comment], [issue], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_a_closed_claimed_issue_is_excluded_not_surfaced(self):
        comment = _comment(3, "Closes #2202 as a side effect.", _NOW - timedelta(hours=50))
        issue = _issue(2202, state="closed")

        surfaced, excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-3-2202" in excluded_slugs

    def test_a_claim_naming_an_issue_that_does_not_exist_is_excluded_not_surfaced(self):
        comment = _comment(4, "Fix #2999 today, same root cause.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-issue-not-found-4-2999" in excluded_slugs

    def test_a_comment_with_no_claim_phrase_is_excluded_not_surfaced(self):
        comment = _comment(5, "Same root cause as #2205, not touching here.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-5"

    def test_a_comment_with_no_body_at_all_produces_no_candidate_at_all(self):
        comment = _comment(6, None, _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_claim_in_one_comment_produces_one_candidate_not_two(self):
        comment = _comment(7, "Fixes #2201 -- yes, really closes #2201.", _NOW - timedelta(hours=3))
        issue = _issue(2201, state="open")

        surfaced, excluded = detector.compute_gaps([comment], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-comment-claims-unfixed-issue-7-2201"

    def test_a_claim_naming_a_real_pull_request_number_is_treated_as_not_found(self):
        # This recipe deliberately checks only the issue list, never the PR
        # list -- the identical boundary every sibling *-claims-unfixed-
        # issue recipe already holds. A closing-keyword claim that happens
        # to land on a real PR number (issue list empty here) is excluded
        # as not-found, the same as a genuinely dangling number -- it is
        # simply out of this recipe's own remit either way.
        comment = _comment(8, "Fixes #500, a real PR number in this repo.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([comment], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-issue-not-found-8-500" in excluded_slugs


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-comment-claims-unfixed-issue-7101-2201"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_two_fresh_claims_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-comment-claims-unfixed-issue-7102-2203" in tail_slugs
        assert "issue-comment-claims-unfixed-issue-7107-2201" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_dangling_and_no_claim_comments(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-7103-2202" in excluded_slugs
        assert "claimed-issue-not-found-7104-2999" in excluded_slugs
        assert "no-claim-phrase-7105" in excluded_slugs

    def test_the_shipped_fixtures_null_body_comment_produces_no_candidate(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = set()
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        all_slugs |= {g["slug"] for g in result["tail"]}
        all_slugs |= {g["slug"] for g in result["excluded"]}
        assert not any("-7106-" in s or s.endswith("-7106") for s in all_slugs)

    def test_the_shipped_fixture_deduplicates_the_repeated_2201_claim_within_one_comment(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("issue-comment-claims-unfixed-issue-7107-2201") == 1


class TestLoaders:
    """load_issue_comments/load_issues -- mirrors every prior recipe's
    own _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_issue_comments_parses_the_real_fixture(self):
        comments = detector.load_issue_comments()
        assert len(comments) > 0
        assert all(isinstance(c, detector.IssueComment) for c in comments)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issue_comments_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issue_comments(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
