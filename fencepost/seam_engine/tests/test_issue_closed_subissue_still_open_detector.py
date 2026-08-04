"""Tests for RECIPES/issue-closed-subissue-still-open/detector.py's own
detection logic (ROADMAP.md #530) -- the forty-third real recipe: an issue
reads closed, but its own checklist still points at an open sub-issue.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-closed-subissue-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_closed_subissue_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


def _issue(
    number: int,
    state: str = "open",
    closed_at: datetime | None = None,
    body: str = "",
    title: str | None = None,
) -> "detector.Issue":
    return detector.Issue(
        number=number, title=title or f"Issue {number}", state=state,
        closed_at=closed_at, body=body,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestChecklistTargets:
    def test_extracts_a_single_checked_and_unchecked_reference(self):
        assert detector._checklist_targets("- [ ] #1\n- [x] #2\n") == [1, 2]

    def test_ignores_a_bare_mention_with_no_checkbox(self):
        assert detector._checklist_targets("See #5 for related context.") == []

    def test_tolerates_leading_whitespace_and_mixed_case_mark(self):
        assert detector._checklist_targets("  - [X] #7\n") == [7]

    def test_empty_body_yields_no_targets(self):
        assert detector._checklist_targets("") == []


class TestComputeGaps:
    def test_a_stale_closed_parent_is_surfaced_at_high_confidence(self):
        parent = _issue(801, state="closed", closed_at=_NOW - timedelta(hours=48), body="- [ ] #804")
        target = _issue(804, state="open")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-closed-subissue-still-open-801-804"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_parent_is_surfaced_at_low_confidence(self):
        parent = _issue(802, state="closed", closed_at=_NOW - timedelta(hours=3), body="- [ ] #805")
        target = _issue(805, state="open")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_target_already_closed_is_excluded_as_claim_holds(self):
        parent = _issue(803, state="closed", closed_at=_NOW - timedelta(hours=48), body="- [x] #806")
        target = _issue(806, state="closed")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "claim-true-803-806"

    def test_a_nonexistent_target_is_excluded_as_dangling_not_surfaced(self):
        parent = _issue(807, state="closed", closed_at=_NOW - timedelta(hours=48), body="- [ ] #999")

        surfaced, excluded = detector.compute_gaps([parent], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "checklist-target-not-found-807-999"

    def test_a_parent_with_no_checklist_produces_no_candidate_at_all(self):
        parent = _issue(808, state="closed", closed_at=_NOW - timedelta(hours=48), body="just prose, no checklist")

        surfaced, excluded = detector.compute_gaps([parent], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_bare_mention_with_no_checkbox_is_never_extracted(self):
        parent = _issue(809, state="closed", closed_at=_NOW - timedelta(hours=48), body="See #810 for context.")
        target = _issue(810, state="open")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_still_open_parent_is_never_considered_at_all(self):
        parent = _issue(811, state="open", body="- [ ] #812")
        target = _issue(812, state="open")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_checklist_reference_is_deduplicated_to_one_candidate(self):
        parent = _issue(813, state="closed", closed_at=_NOW - timedelta(hours=48), body="- [ ] #814\n- [ ] #814\n")
        target = _issue(814, state="open")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert len(surfaced) == 1
        assert excluded == []

    def test_a_closed_parent_with_no_timestamp_is_excluded_as_malformed(self):
        parent = _issue(815, state="closed", closed_at=None, body="- [ ] #816")
        target = _issue(816, state="open")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert surfaced == []
        candidate = excluded[0]
        assert candidate.slug == "issue-closed-no-timestamp-815-816"
        assert "malformed" in candidate.detail


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-closed-subissue-still-open-901-904"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_closed_parent_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-closed-subissue-still-open-902-905" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_target(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-901-906" in excluded_slugs
        assert "checklist-target-not-found-901-999" in excluded_slugs

    def test_the_shipped_fixture_never_considers_the_open_parent_or_bare_mention(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-907-" in s for s in all_slugs)
        assert not any("-903-" in s for s in all_slugs)


class TestLoaders:
    """load_issues -- mirrors every prior recipe's own _load_rows guard
    against syntactically valid but non-list JSON."""

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
