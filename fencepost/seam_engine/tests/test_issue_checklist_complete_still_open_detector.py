"""Tests for RECIPES/issue-checklist-complete-still-open/detector.py's own
detection logic (ROADMAP.md #558) -- the forty-sixth real recipe: an issue's
own checklist is all checked off, but the issue itself never closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-checklist-complete-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_issue_checklist_complete_still_open_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 5, 21, 10, 0, tzinfo=timezone.utc)


def _issue(
    number: int,
    state: str = "open",
    updated_at: datetime | None = None,
    body: str = "",
    title: str | None = None,
) -> "detector.Issue":
    return detector.Issue(
        number=number, title=title or f"Issue {number}", state=state,
        body=body, updated_at=updated_at or _NOW,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestChecklistTargets:
    """`detector._checklist_targets` is `seam_engine.checklist.checklist_targets`
    imported verbatim (task 558's own shared-module extraction) -- it keeps
    duplicates by design; this recipe's own dedup happens inside
    `compute_gaps`, exercised separately below."""

    def test_extracts_a_single_checked_and_unchecked_reference(self):
        assert detector._checklist_targets("- [ ] #1\n- [x] #2\n") == [1, 2]

    def test_ignores_a_bare_mention_with_no_checkbox(self):
        assert detector._checklist_targets("See #5 for related context.") == []

    def test_tolerates_leading_whitespace_and_mixed_case_mark(self):
        assert detector._checklist_targets("  - [X] #7\n") == [7]

    def test_empty_body_yields_no_targets(self):
        assert detector._checklist_targets("") == []

    def test_a_duplicate_reference_is_kept_raw_not_deduplicated_here(self):
        assert detector._checklist_targets("- [x] #9\n- [x] #9\n- [x] #3\n") == [9, 9, 3]


class TestComputeGaps:
    def test_a_stale_open_parent_with_all_targets_closed_is_surfaced_at_high_confidence(self):
        target = _issue(904, state="closed")
        parent = _issue(901, state="open", updated_at=_NOW - timedelta(hours=48), body="- [x] #904")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-checklist-complete-still-open-901"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [parent.url, target.url]

    def test_a_recently_touched_open_parent_is_surfaced_at_low_confidence(self):
        target = _issue(905, state="closed")
        parent = _issue(902, state="open", updated_at=_NOW - timedelta(hours=3), body="- [x] #905")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_still_open_target_excludes_the_parent_as_not_complete(self):
        target = _issue(906, state="open")
        parent = _issue(903, state="open", updated_at=_NOW - timedelta(hours=48), body="- [ ] #906")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "not-complete-903"

    def test_a_nonexistent_target_is_excluded_as_unverifiable_not_surfaced(self):
        parent = _issue(907, state="open", updated_at=_NOW - timedelta(hours=48), body="- [x] #999")

        surfaced, excluded = detector.compute_gaps([parent], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "checklist-target-not-found-907"

    def test_one_still_open_target_among_several_still_excludes_the_whole_parent(self):
        closed_target = _issue(910, state="closed")
        open_target = _issue(911, state="open")
        parent = _issue(
            908, state="open", updated_at=_NOW - timedelta(hours=48),
            body="- [x] #910\n- [ ] #911\n",
        )

        surfaced, excluded = detector.compute_gaps([parent, closed_target, open_target], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "not-complete-908"

    def test_a_parent_with_no_checklist_produces_no_candidate_at_all(self):
        parent = _issue(909, state="open", body="just prose, no checklist")

        surfaced, excluded = detector.compute_gaps([parent], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_bare_mention_with_no_checkbox_is_never_extracted(self):
        target = _issue(913, state="closed")
        parent = _issue(912, state="open", body="See #913 for context.")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_closed_parent_is_never_considered_at_all(self):
        target = _issue(915, state="closed")
        parent = _issue(914, state="closed", updated_at=_NOW - timedelta(hours=48), body="- [x] #915")

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_checklist_reference_is_deduplicated_to_one_evidence_entry(self):
        target = _issue(917, state="closed")
        parent = _issue(
            916, state="open", updated_at=_NOW - timedelta(hours=48),
            body="- [x] #917\n- [x] #917\n",
        )

        surfaced, excluded = detector.compute_gaps([parent, target], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].evidence == [parent.url, target.url]
        assert excluded == []


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-checklist-complete-still-open-1001"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_touched_parents_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-checklist-complete-still-open-1002" in tail_slugs
        assert "issue-checklist-complete-still-open-1007" in tail_slugs

    def test_the_shipped_fixture_deduplicates_1007s_repeated_reference(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_by_slug = {g["slug"]: g for g in result["tail"]}
        assert len(tail_by_slug["issue-checklist-complete-still-open-1007"]["evidence"]) == 2

    def test_the_shipped_fixture_excludes_the_incomplete_and_broken_parents(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "not-complete-1003" in excluded_slugs
        assert "checklist-target-not-found-1004" in excluded_slugs

    def test_the_shipped_fixture_never_considers_the_closed_parent_or_bare_mention(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-1005" in s for s in all_slugs)
        assert not any("-1006" in s for s in all_slugs)


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
