"""Tests for RECIPES/duplicate-issue-still-open/detector.py's own detection
logic (ROADMAP.md #376) -- the seventh real recipe: an issue that names
itself a duplicate of another issue whose original has since closed, while
the duplicate itself was never closed alongside it.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "duplicate-issue-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_duplicate_issue_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def _issue(
    number: int,
    body: str,
    state: str = "open",
    closed_at: datetime | None = None,
) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state, body=body,
        closed_at=closed_at, url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestNamedDuplicateOf:
    def test_duplicate_of_hash_n(self):
        assert detector._named_duplicate_of("Duplicate of #700") == 700

    def test_dup_of_hash_n(self):
        assert detector._named_duplicate_of("dup of #703") == 703

    def test_duplicate_colon_hash_n(self):
        assert detector._named_duplicate_of("Duplicate: #705") == 705

    def test_bare_duplicate_hash_n(self):
        assert detector._named_duplicate_of("duplicate #705") == 705

    def test_no_marker_returns_none(self):
        assert detector._named_duplicate_of("A regular bug report, no duplicate mention at all.") is None

    def test_dupe_does_not_false_positive(self):
        # "dupe" is not "dup"/"duplicate" -- the \b boundary after the
        # optional "licate" group must not let this slip through.
        assert detector._named_duplicate_of("This is not a dupe situation, see #700 for a different reason") is None


class TestComputeGaps:
    def test_a_stale_closed_original_is_surfaced_at_high_confidence(self):
        dup = _issue(701, "Duplicate of #700")
        original = _issue(700, "Some bug", state="closed", closed_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "duplicate-issue-still-open-701-700"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_original_is_surfaced_at_low_confidence(self):
        dup = _issue(702, "dup of #703")
        original = _issue(703, "Some bug", state="closed", closed_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_still_open_named_original_is_excluded_not_surfaced(self):
        dup = _issue(704, "Duplicate of #705")
        original = _issue(705, "Some bug", state="open")

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "original-still-open-704-705" in excluded_slugs

    def test_an_issue_with_no_duplicate_marker_produces_no_candidate_at_all(self):
        issue = _issue(706, "A regular bug report, no duplicate mention at all.")

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-duplicate-marker-706"

    def test_a_duplicate_that_is_itself_already_closed_is_never_considered(self):
        # This recipe's seam is specifically a duplicate that is STILL
        # open. One that already closed itself (whether via the duplicate
        # marking or any other route) has no gap left to surface.
        dup = _issue(707, "Duplicate of #708", state="closed", closed_at=datetime(2026, 7, 22, 11, 0, 0, tzinfo=timezone.utc))
        original = _issue(708, "Some bug", state="closed", closed_at=datetime(2026, 7, 22, 10, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_an_unrecognized_original_number_is_excluded_not_surfaced(self):
        dup = _issue(709, "duplicate of #999")

        surfaced, excluded = detector.compute_gaps([dup], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "nonexistent-original-709-999"


class TestNonexistentOriginalIsNotMislabeledStillOpen:
    """ROADMAP.md #432: before this fix, `original is None or original.state
    != "closed"` folded a dangling reference (the named original was never
    real) into the same `original-still-open-...` slug and the same false
    detail line ("that issue has not closed yet") as a genuinely-unresolved
    original -- reproduced live against the pre-fix code before writing this
    test. A dangling reference gets its own `nonexistent-original-...` slug
    now, matching the split `merged-pr-issue-still-open/detector.py` (task
    429) and `issue-closed-pr-still-open/detector.py` (task 430) already
    made for their own referencing-record/target-record pairs."""

    def test_a_named_original_that_does_not_exist_is_excluded_as_nonexistent_not_still_open(self):
        dup = _issue(710, "duplicate of #999")  # #999 is never in the issue list at all

        surfaced, excluded = detector.compute_gaps([dup], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        candidate = excluded[0]
        assert candidate.slug == "nonexistent-original-710-999"
        assert "closed" not in candidate.detail
        assert "open" not in candidate.detail
        assert candidate.evidence == [dup.url]  # no original.url to append -- it doesn't exist

    def test_a_named_original_that_exists_and_is_still_open_is_still_excluded_as_still_open(self):
        # The genuinely-unresolved path must survive the split unchanged.
        # `original` itself is also `open` here, but with no duplicate
        # marker of its own, so it produces its own separate excluded
        # candidate -- this test asserts on the #711 candidate specifically.
        dup = _issue(711, "Duplicate of #712")
        original = _issue(712, "Some bug", state="open")

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert surfaced == []
        by_slug = {g.slug: g for g in excluded}
        candidate = by_slug["original-still-open-711-712"]
        assert candidate.evidence == [dup.url, original.url]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "duplicate-issue-still-open-701-700"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_closed_original_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "duplicate-issue-still-open-702-703" in tail_slugs

    def test_the_shipped_fixture_excludes_the_still_open_named_original(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "original-still-open-704-705" in excluded_slugs
        assert "no-duplicate-marker-706" in excluded_slugs
        assert "nonexistent-original-709-999" in excluded_slugs

    def test_the_shipped_fixture_never_considers_the_already_closed_duplicate(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-707-" in s for s in all_slugs)


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
