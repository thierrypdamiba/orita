"""Tests for RECIPES/pr-checklist-complete-still-open/detector.py's own
detection logic (ROADMAP.md #579) -- the fifty-second real recipe: a pull
request's own checklist is all checked off, but the PR itself never merged.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "pr-checklist-complete-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_pr_checklist_complete_still_open_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 6, 22, 0, 0, tzinfo=timezone.utc)


def _pr(
    number: int,
    state: str = "open",
    merged: bool = False,
    updated_at: datetime | None = None,
    body: str = "",
    title: str | None = None,
) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=title or f"PR {number}", state=state, merged=merged,
        body=body, updated_at=updated_at or _NOW,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestChecklistMarks:
    def test_extracts_a_single_checked_and_unchecked_mark(self):
        assert detector._checklist_marks("- [ ] one\n- [x] two\n") == [" ", "x"]

    def test_ignores_a_line_with_no_checkbox(self):
        assert detector._checklist_marks("Just prose, no checklist here.") == []

    def test_tolerates_leading_whitespace_and_mixed_case_mark(self):
        assert detector._checklist_marks("  - [X] done\n") == ["x"]

    def test_empty_body_yields_no_marks(self):
        assert detector._checklist_marks("") == []

    def test_a_bare_number_reference_checkbox_still_counts_generic_text(self):
        # This grammar cares only that SOME text follows the mark -- unlike
        # seam_engine.checklist.CHECKLIST_RE, a "#N" is not required.
        assert detector._checklist_marks("- [x] #904") == ["x"]

    def test_a_checkbox_with_nothing_after_it_does_not_match(self):
        assert detector._checklist_marks("- [x]\n- [ ]   \n") == []

    def test_multiple_items_preserve_order(self):
        assert detector._checklist_marks("- [x] a\n- [ ] b\n- [x] c\n") == ["x", " ", "x"]


class TestComputeGaps:
    def test_a_stale_open_pr_with_all_boxes_checked_is_surfaced_at_high_confidence(self):
        pr = _pr(301, updated_at=_NOW - timedelta(hours=48), body="- [x] one\n- [x] two")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "pr-checklist-complete-still-open-301"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [pr.url]

    def test_a_recently_touched_pr_is_surfaced_at_low_confidence(self):
        pr = _pr(302, updated_at=_NOW - timedelta(hours=3), body="- [x] one")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_exactly_twenty_four_hours_counts_as_stale(self):
        pr = _pr(303, updated_at=_NOW - timedelta(hours=24), body="- [x] one")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_an_unchecked_box_excludes_the_pr_as_not_complete(self):
        pr = _pr(304, updated_at=_NOW - timedelta(hours=48), body="- [x] one\n- [ ] two")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "pr-checklist-incomplete-304"

    def test_a_pr_with_no_checklist_produces_no_candidate_at_all(self):
        pr = _pr(305, body="Just a description, no checklist.")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_merged_pr_is_excluded_even_with_a_complete_checklist(self):
        pr = _pr(306, state="closed", merged=True, updated_at=_NOW - timedelta(hours=48), body="- [x] one")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "pr-resolved-306"

    def test_a_closed_unmerged_pr_is_excluded_even_with_a_complete_checklist(self):
        pr = _pr(307, state="closed", merged=False, updated_at=_NOW - timedelta(hours=48), body="- [x] one")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "pr-resolved-307"

    def test_a_merged_pr_with_an_incomplete_checklist_is_still_excluded_as_resolved_not_incomplete(self):
        pr = _pr(308, state="closed", merged=True, body="- [ ] one")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "pr-resolved-308"

    def test_multiple_open_prs_each_get_their_own_candidate(self):
        prs = [
            _pr(309, updated_at=_NOW - timedelta(hours=48), body="- [x] a"),
            _pr(310, updated_at=_NOW - timedelta(hours=72), body="- [x] b"),
        ]

        surfaced, excluded = detector.compute_gaps(prs, now=_NOW)

        assert {g.slug for g in surfaced} == {
            "pr-checklist-complete-still-open-309",
            "pr-checklist-complete-still-open-310",
        }

    def test_surfaced_candidates_sort_by_confidence_descending(self):
        prs = [
            _pr(311, updated_at=_NOW - timedelta(hours=2), body="- [x] a"),
            _pr(312, updated_at=_NOW - timedelta(hours=100), body="- [x] b"),
        ]

        surfaced, _ = detector.compute_gaps(prs, now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.5]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "pr-checklist-complete-still-open-201"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_touched_pr_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "pr-checklist-complete-still-open-203" in tail_slugs

    def test_the_shipped_fixture_excludes_the_incomplete_and_merged_prs(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "pr-checklist-incomplete-202" in excluded_slugs
        assert "pr-resolved-204" in excluded_slugs

    def test_the_shipped_fixture_never_considers_the_checklist_free_pr(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-205" in s for s in all_slugs)


class TestLoaders:
    """load_pull_requests -- mirrors every prior recipe's own _load_rows
    guard against syntactically valid but non-list JSON."""

    def test_load_pull_requests_parses_the_real_fixture(self):
        prs = detector.load_pull_requests()
        assert len(prs) > 0
        assert all(isinstance(p, detector.PullRequest) for p in prs)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pull_requests_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pull_requests(bad_file)

    def test_load_pull_requests_defaults_a_missing_body_to_empty_string(self, tmp_path: Path):
        f = tmp_path / "prs.json"
        f.write_text(json.dumps([{
            "number": 1, "title": "t", "state": "open", "merged": False,
            "updated_at": "2026-08-06T00:00:00Z", "url": "https://example.com/1",
        }]))
        prs = detector.load_pull_requests(f)
        assert prs[0].body == ""
