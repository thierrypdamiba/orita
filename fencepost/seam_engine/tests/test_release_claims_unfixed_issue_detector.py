"""Tests for RECIPES/release-claims-unfixed-issue/detector.py's own
detection logic (ROADMAP.md #382) -- the thirteenth real recipe: a GitHub
release's own body text invokes a real closing keyword against an issue,
but the issue never actually closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "release-claims-unfixed-issue" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_release_claims_unfixed_issue_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _release(tag: str, body: str, published_at: datetime) -> "detector.Release":
    return detector.Release(
        id=f"REL-{tag}", title=f"Release {tag}", tag=tag, body=body,
        published_at=published_at, url=f"https://github.com/example/example-repo/releases/tag/{tag}",
    )


def _issue(number: int, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClaimedIssueNumbers:
    def test_fixes_hash_n(self):
        assert detector._claimed_issue_numbers("Fixes #1101.") == [1101]

    def test_closes_hash_n(self):
        assert detector._claimed_issue_numbers("Closes #1102 this time.") == [1102]

    def test_resolves_hash_n(self):
        assert detector._claimed_issue_numbers("Resolves #1103.") == [1103]

    def test_past_tense_fixed(self):
        assert detector._claimed_issue_numbers("Fixed #1104.") == [1104]

    def test_past_tense_closed(self):
        assert detector._claimed_issue_numbers("Closed #1105.") == [1105]

    def test_past_tense_resolved(self):
        assert detector._claimed_issue_numbers("Resolved #1106.") == [1106]

    def test_case_insensitive(self):
        assert detector._claimed_issue_numbers("FIXES #1107.") == [1107]

    def test_optional_colon(self):
        assert detector._claimed_issue_numbers("Fixes: #1108.") == [1108]

    def test_present_participle_never_matches(self):
        # Iron Rule #8's own prescribed safe phrasing for discussing the
        # grammar in prose without invoking it.
        assert detector._claimed_issue_numbers("Closing #1109 in the notes.") == []

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        # This is dangling-issue-reference's own broader regex; a bare "see
        # #N" mention in prose is not a fix claim.
        assert detector._claimed_issue_numbers("See #1110 for background.") == []

    def test_multiple_claims_in_one_body(self):
        assert detector._claimed_issue_numbers("Fixes #1101. Resolves #1102.") == [1101, 1102]

    def test_duplicate_claim_in_one_body_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_issue_numbers("Fixes #1101 and fixes #1101 again.") == [1101, 1101]


class TestComputeGaps:
    def test_a_stale_unfixed_claim_is_surfaced_at_high_confidence(self):
        release = _release("v1.0", "Fixes #1101.", _NOW - timedelta(hours=50))
        issue = _issue(1101, state="open")

        surfaced, excluded = detector.compute_gaps([release], [issue], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "release-claims-unfixed-issue-v1.0-1101"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unfixed_claim_is_surfaced_at_low_confidence(self):
        release = _release("v1.1", "Resolves #1103.", _NOW - timedelta(hours=4))
        issue = _issue(1103, state="open")

        surfaced, excluded = detector.compute_gaps([release], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_closed_claimed_issue_is_excluded_not_surfaced(self):
        release = _release("v1.2", "Resolves #1102.", _NOW - timedelta(hours=50))
        issue = _issue(1102, state="closed")

        surfaced, excluded = detector.compute_gaps([release], [issue], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-v1.2-1102" in excluded_slugs

    def test_a_claim_naming_an_issue_that_does_not_exist_is_excluded_not_surfaced(self):
        release = _release("v1.3", "Fix #1999.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([release], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-issue-not-found-v1.3-1999" in excluded_slugs

    def test_a_release_with_no_claim_phrase_produces_no_candidate_at_all(self):
        release = _release("v1.4", "Housekeeping only, see #1105 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([release], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-v1.4"

    def test_a_duplicate_claim_in_one_body_produces_one_candidate_not_two(self):
        release = _release("v1.5", "Fixes #1101 and fixes #1101 again.", _NOW - timedelta(hours=50))
        issue = _issue(1101, state="open")

        surfaced, excluded = detector.compute_gaps([release], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "release-claims-unfixed-issue-v1.5-1101"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "release-claims-unfixed-issue-v1.1.0-1101"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "release-claims-unfixed-issue-v1.1.1-1103" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_and_no_claim_releases(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-v1.1.0-1102" in excluded_slugs
        assert "claimed-issue-not-found-v1.1.2-1999" in excluded_slugs
        assert "no-claim-phrase-v1.1.3" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_1101_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("release-claims-unfixed-issue-v1.1.0-1101") == 1


class TestLoaders:
    """load_releases/load_issues -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_releases_parses_the_real_fixture(self):
        releases = detector.load_releases()
        assert len(releases) > 0
        assert all(isinstance(r, detector.Release) for r in releases)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_releases_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_releases(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
