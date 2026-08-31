"""Tests for RECIPES/issue-body-claims-unfixed-issue/detector.py's own
detection logic -- the ninety-sixth real recipe: an issue or pull
request's own OPENING BODY invokes a real closing keyword against an
issue, but the issue never actually closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-body-claims-unfixed-issue" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_body_claims_unfixed_issue_test", DETECTOR_PATH)
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


def _pull_src(number: int, body: str | None, updated_at: datetime, state: str = "open") -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, body=body or "",
        updated_at=updated_at,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


def _target_issue(number: int, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Target {number}", state=state, body="",
        updated_at=_NOW,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestComputeGaps:
    def test_a_stale_unfixed_claim_from_an_issue_body_is_surfaced_at_high_confidence(self):
        source = _issue_src(10, "This also fixes #2201 while we're in here.", _NOW - timedelta(hours=50))
        target = _target_issue(2201)

        surfaced, excluded = detector.compute_gaps([source, target], [], now=_NOW)
        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-body-claims-unfixed-issue-issue-10-2201"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unfixed_claim_from_a_pr_body_is_surfaced_at_low_confidence(self):
        source = _pull_src(20, "I think this resolves #2203 too.", _NOW - timedelta(hours=4))
        target = _target_issue(2203)

        surfaced, _ = detector.compute_gaps([target], [source], now=_NOW)
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-body-claims-unfixed-issue-pr-20-2203"
        assert surfaced[0].confidence == 0.55

    def test_a_claim_at_exactly_the_edit_grace_window_boundary_is_high_confidence(self):
        source = _issue_src(11, "Closes #2203.", _NOW - timedelta(hours=24))
        target = _target_issue(2203)

        surfaced, _ = detector.compute_gaps([source, target], [], now=_NOW)
        assert surfaced[0].confidence == 0.85

    def test_a_closed_claimed_issue_is_excluded_not_surfaced(self):
        source = _issue_src(12, "Closes #2202 as a side effect.", _NOW - timedelta(hours=50))
        target = _target_issue(2202, state="closed")

        surfaced, excluded = detector.compute_gaps([source, target], [], now=_NOW)
        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-issue-12-2202" in excluded_slugs

    def test_a_claim_naming_an_issue_that_does_not_exist_is_excluded_not_surfaced(self):
        source = _issue_src(13, "Fix #2999 today, same root cause.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([source], [], now=_NOW)
        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-issue-not-found-issue-13-2999" in excluded_slugs

    def test_a_body_with_no_claim_phrase_produces_no_candidate_at_all(self):
        source = _issue_src(14, "Same root cause as #2205, not touching here.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([source], [], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_a_body_with_no_content_at_all_produces_no_candidate_at_all(self):
        source = _issue_src(15, None, _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([source], [], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_claim_in_one_body_produces_one_candidate_not_two(self):
        source = _pull_src(21, "Fixes #2201 -- yes, really closes #2201.", _NOW - timedelta(hours=3))
        target = _target_issue(2201)

        surfaced, excluded = detector.compute_gaps([target], [source], now=_NOW)
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-body-claims-unfixed-issue-pr-21-2201"

    def test_a_claim_naming_a_real_pull_request_number_is_treated_as_not_found(self):
        # This recipe deliberately checks only the issue list, never the PR
        # list -- the identical boundary every sibling *-claims-unfixed-
        # issue recipe already holds. A closing-keyword claim that happens
        # to land on a real PR number is excluded as not-found, the same
        # as a genuinely dangling number -- out of this recipe's own
        # remit either way.
        source = _issue_src(16, "Fixes #500, a real PR number in this repo.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([source], [], now=_NOW)
        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-issue-not-found-issue-16-500" in excluded_slugs

    def test_both_an_issue_and_a_pr_body_can_carry_the_same_claim_independently(self):
        i_source = _issue_src(17, "Fixes #2201.", _NOW - timedelta(hours=50))
        p_source = _pull_src(22, "Fixes #2201.", _NOW - timedelta(hours=50))
        target = _target_issue(2201)

        surfaced, _ = detector.compute_gaps([i_source, target], [p_source], now=_NOW)
        slugs = {g.slug for g in surfaced}
        assert "issue-body-claims-unfixed-issue-issue-17-2201" in slugs
        assert "issue-body-claims-unfixed-issue-pr-22-2201" in slugs


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-body-claims-unfixed-issue-issue-2203-2201"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_three_fresh_claims_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-body-claims-unfixed-issue-issue-2207-2201" in tail_slugs
        assert "issue-body-claims-unfixed-issue-pr-52-2201" in tail_slugs
        assert "issue-body-claims-unfixed-issue-pr-53-2205" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-issue-2204-2202" in excluded_slugs
        assert "claimed-issue-not-found-issue-2205-2999" in excluded_slugs

    def test_the_shipped_fixtures_blank_body_and_no_claim_pr_produce_no_candidate(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = set()
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        all_slugs |= {g["slug"] for g in result["tail"]}
        all_slugs |= {g["slug"] for g in result["excluded"]}
        assert not any("-2206-" in s or s.endswith("-2206") for s in all_slugs)
        assert not any("-55-" in s or s.endswith("-55") for s in all_slugs)

    def test_the_shipped_fixture_deduplicates_the_repeated_2201_claim_in_pr_52(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("issue-body-claims-unfixed-issue-pr-52-2201") == 1


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
