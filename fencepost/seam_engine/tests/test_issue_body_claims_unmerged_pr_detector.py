"""Tests for RECIPES/issue-body-claims-unmerged-pr/detector.py's own
detection logic -- the ninety-seventh real recipe: an issue or pull
request's own OPENING BODY invokes a real closing keyword against a
pull request, but the pull request never actually merged.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-body-claims-unmerged-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_body_claims_unmerged_pr_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


def _issue_src(number: int, body: str | None, updated_at: datetime, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state, body=body or "",
        updated_at=updated_at,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


def _pull_src(number: int, body: str | None, updated_at: datetime, state: str = "open", merged: bool = False) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged, body=body or "",
        updated_at=updated_at,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


def _target_pr(number: int, state: str = "open", merged: bool = False) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"Target {number}", state=state, merged=merged, body="",
        updated_at=_NOW,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestComputeGaps:
    def test_a_stale_unmerged_claim_from_an_issue_body_is_surfaced_at_high_confidence(self):
        source = _issue_src(10, "This also fixes #501 while we're in here.", _NOW - timedelta(hours=50))
        target = _target_pr(501)

        surfaced, excluded = detector.compute_gaps([source], [target], now=_NOW)
        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-body-claims-unmerged-pr-issue-10-501"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unmerged_claim_from_a_pr_body_is_surfaced_at_low_confidence(self):
        source = _pull_src(20, "I think this resolves #503 too.", _NOW - timedelta(hours=4))
        target = _target_pr(503)

        surfaced, _ = detector.compute_gaps([], [target, source], now=_NOW)
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-body-claims-unmerged-pr-pr-20-503"
        assert surfaced[0].confidence == 0.55

    def test_a_claim_at_exactly_the_edit_grace_window_boundary_is_high_confidence(self):
        source = _issue_src(11, "Closes #503.", _NOW - timedelta(hours=24))
        target = _target_pr(503)

        surfaced, _ = detector.compute_gaps([source], [target], now=_NOW)
        assert surfaced[0].confidence == 0.85

    def test_a_merged_claimed_pr_is_excluded_not_surfaced(self):
        source = _issue_src(12, "Closes #502 as a side effect.", _NOW - timedelta(hours=50))
        target = _target_pr(502, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps([source], [target], now=_NOW)
        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-issue-12-502" in excluded_slugs

    def test_a_closed_without_merging_claimed_pr_is_excluded_not_surfaced(self):
        source = _issue_src(13, "Fixes #503 for good.", _NOW - timedelta(hours=50))
        target = _target_pr(503, state="closed", merged=False)

        surfaced, excluded = detector.compute_gaps([source], [target], now=_NOW)
        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-issue-13-503" in excluded_slugs

    def test_a_claim_naming_a_pr_that_does_not_exist_is_excluded_not_surfaced(self):
        source = _issue_src(14, "Fix #999 today, same root cause.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([source], [], now=_NOW)
        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-issue-14-999" in excluded_slugs

    def test_a_body_with_no_claim_phrase_produces_no_candidate_at_all(self):
        source = _issue_src(15, "Same root cause as #501, not touching here.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([source], [], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_a_body_with_no_content_at_all_produces_no_candidate_at_all(self):
        source = _issue_src(16, None, _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([source], [], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_claim_in_one_body_produces_one_candidate_not_two(self):
        source = _pull_src(21, "Fixes #501 -- yes, really closes #501.", _NOW - timedelta(hours=3))
        target = _target_pr(501)

        surfaced, excluded = detector.compute_gaps([], [target, source], now=_NOW)
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-body-claims-unmerged-pr-pr-21-501"

    def test_a_claim_naming_a_real_issue_number_is_treated_as_not_found(self):
        # This recipe deliberately checks only the pull-request list,
        # never the issue list -- the mirror image of the boundary
        # issue-body-claims-unfixed-issue holds itself to (that sibling
        # excludes a claim naming a real PR number the same way).
        source = _issue_src(17, "Fixes #10, a real issue number in this repo.", _NOW - timedelta(hours=50))
        other_issue = _issue_src(10, "", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([source, other_issue], [], now=_NOW)
        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-issue-17-10" in excluded_slugs

    def test_both_an_issue_and_a_pr_body_can_carry_the_same_claim_independently(self):
        i_source = _issue_src(18, "Fixes #501.", _NOW - timedelta(hours=50))
        p_source = _pull_src(22, "Fixes #501.", _NOW - timedelta(hours=50))
        target = _target_pr(501)

        surfaced, _ = detector.compute_gaps([i_source], [target, p_source], now=_NOW)
        slugs = {g.slug for g in surfaced}
        assert "issue-body-claims-unmerged-pr-issue-18-501" in slugs
        assert "issue-body-claims-unmerged-pr-pr-22-501" in slugs


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-body-claims-unmerged-pr-issue-40-501"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_two_fresh_claims_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-body-claims-unmerged-pr-issue-45-501" in tail_slugs
        assert "issue-body-claims-unmerged-pr-pr-60-501" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claims_and_the_dangling_claims(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-issue-41-502" in excluded_slugs
        assert "claim-true-pr-61-503" in excluded_slugs
        assert "claimed-pr-not-found-issue-42-999" in excluded_slugs
        assert "claimed-pr-not-found-issue-46-40" in excluded_slugs

    def test_the_shipped_fixtures_blank_body_and_no_claim_pr_produce_no_candidate(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = set()
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        all_slugs |= {g["slug"] for g in result["tail"]}
        all_slugs |= {g["slug"] for g in result["excluded"]}
        assert not any("-43-" in s or s.endswith("-43") for s in all_slugs)
        assert not any("-62-" in s or s.endswith("-62") for s in all_slugs)

    def test_the_shipped_fixture_deduplicates_the_repeated_501_claim_in_pr_60(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("issue-body-claims-unmerged-pr-pr-60-501") == 1


class TestLoaders:
    """load_issues/load_pulls -- mirrors every sibling detector's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
