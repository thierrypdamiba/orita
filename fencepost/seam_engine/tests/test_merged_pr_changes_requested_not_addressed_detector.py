"""Tests for RECIPES/merged-pr-changes-requested-not-addressed/detector.py's
own detection logic (ROADMAP.md #1613) -- the hundred-twelfth real recipe:
a pull request merged while its own live GitHub review_decision still read
CHANGES_REQUESTED.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "merged-pr-changes-requested-not-addressed" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_merged_pr_changes_requested_not_addressed_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 9, 20, 4, 0, 0, tzinfo=timezone.utc)


def _pr(
    number: int, title: str = "Example change", *, state: str = "closed",
    merged: bool = True, review_decision: str | None = "CHANGES_REQUESTED",
    merged_at: datetime | None = _NOW,
) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=title, state=state, merged=merged,
        review_decision=review_decision, merged_at=merged_at,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestComputeGaps:
    def test_a_merged_pr_with_changes_requested_is_surfaced(self):
        pr = _pr(214)

        surfaced, excluded = detector.compute_gaps([pr])

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-changes-requested-not-addressed-214"
        assert surfaced[0].confidence == 0.8

    def test_a_merged_pr_with_approved_is_excluded_not_surfaced(self):
        pr = _pr(221, review_decision="APPROVED")

        surfaced, excluded = detector.compute_gaps([pr])

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "merged-pr-changes-requested-no-objection-221"
        assert excluded[0].confidence == 0.0

    def test_an_unmerged_pr_with_changes_requested_is_excluded_not_surfaced(self):
        pr = _pr(229, state="open", merged=False, merged_at=None)

        surfaced, excluded = detector.compute_gaps([pr])

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "merged-pr-changes-requested-not-merged-229"

    def test_a_merged_pr_with_no_review_decision_at_all_is_excluded(self):
        pr = _pr(233, review_decision=None)

        surfaced, excluded = detector.compute_gaps([pr])

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "merged-pr-changes-requested-no-objection-233"

    @pytest.mark.parametrize("decision", ["REVIEW_REQUIRED", None, "APPROVED"])
    def test_only_changes_requested_ever_surfaces_on_a_merged_pr(self, decision):
        pr = _pr(300, review_decision=decision)

        surfaced, excluded = detector.compute_gaps([pr])

        assert surfaced == []
        assert len(excluded) == 1

    def test_multiple_pull_requests_are_each_evaluated_independently(self):
        gap_pr = _pr(214)
        approved_pr = _pr(221, review_decision="APPROVED")
        open_pr = _pr(229, state="open", merged=False, merged_at=None)

        surfaced, excluded = detector.compute_gaps([gap_pr, approved_pr, open_pr])

        assert {g.slug for g in surfaced} == {"merged-pr-changes-requested-not-addressed-214"}
        assert {g.slug for g in excluded} == {
            "merged-pr-changes-requested-no-objection-221",
            "merged-pr-changes-requested-not-merged-229",
        }

    def test_headline_and_detail_never_uppercase_lie_about_the_decision_field(self):
        """The headline names the field's real value (CHANGES_REQUESTED) so a
        reader can trust the report without re-opening the PR -- mirrors
        `approved-pr-still-unmerged`'s own precedent of naming the exact
        field value in its excluded-case detail text."""
        pr = _pr(214)

        surfaced, _ = detector.compute_gaps([pr])

        assert "CHANGES_REQUESTED" in surfaced[0].headline
        assert "CHANGES_REQUESTED" in surfaced[0].detail


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "merged-pr-changes-requested-not-addressed-214"
        assert result["primary_gap"]["confidence"] == 0.8

    def test_the_shipped_fixture_excludes_the_other_three(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert excluded_slugs == {
            "merged-pr-changes-requested-no-objection-221",
            "merged-pr-changes-requested-not-merged-229",
            "merged-pr-changes-requested-no-objection-233",
        }

    def test_output_shape_matches_every_other_recipes_run_recipe_scan(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert set(result.keys()) == {
            "generated_at", "source", "confidence_bar", "separation_margin",
            "primary_gap", "tail", "excluded",
        }
        assert result["source"] == "fixture"


class TestLoaders:
    """load_pull_requests -- mirrors every prior recipe's own _load_rows
    guard against syntactically valid but non-list JSON."""

    def test_load_pull_requests_parses_the_real_fixture(self):
        pull_requests = detector.load_pull_requests()
        assert len(pull_requests) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pull_requests)

    def test_load_pull_requests_reads_merged_at_as_a_datetime(self):
        pull_requests = detector.load_pull_requests()
        merged = [p for p in pull_requests if p.merged]
        assert merged
        assert all(isinstance(p.merged_at, datetime) for p in merged)

    def test_load_pull_requests_leaves_merged_at_none_when_never_merged(self):
        pull_requests = detector.load_pull_requests()
        unmerged = [p for p in pull_requests if not p.merged]
        assert unmerged
        assert all(p.merged_at is None for p in unmerged)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pull_requests_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pull_requests(bad_file)
