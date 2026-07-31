"""Tests for RECIPES/duplicate-pr-still-open/detector.py's own detection
logic -- the twenty-second real recipe: a pull request that names itself a
duplicate of another PR whose original has since merged or closed, while
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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "duplicate-pr-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_duplicate_pr_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def _pull(
    number: int,
    body: str,
    state: str = "open",
    closed_at: datetime | None = None,
) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, body=body,
        closed_at=closed_at, url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestNamedDuplicateOf:
    def test_duplicate_of_hash_n(self):
        assert detector._named_duplicate_of("Duplicate of #800") == 800

    def test_dup_of_hash_n(self):
        assert detector._named_duplicate_of("dup of #803") == 803

    def test_duplicate_colon_hash_n(self):
        assert detector._named_duplicate_of("Duplicate: #805") == 805

    def test_bare_duplicate_hash_n(self):
        assert detector._named_duplicate_of("duplicate #805") == 805

    def test_no_marker_returns_none(self):
        assert detector._named_duplicate_of("A regular doc PR, no duplicate mention at all.") is None

    def test_dupe_does_not_false_positive(self):
        assert detector._named_duplicate_of("This is not a dupe situation, see #800 for a different reason") is None


class TestComputeGaps:
    def test_a_stale_merged_original_is_surfaced_at_high_confidence(self):
        dup = _pull(801, "Duplicate of #800")
        original = _pull(800, "Some fix", state="merged", closed_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "duplicate-pr-still-open-801-800"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_original_is_surfaced_at_low_confidence(self):
        dup = _pull(802, "dup of #803")
        original = _pull(803, "Some fix", state="closed", closed_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_still_open_named_original_is_excluded_not_surfaced(self):
        dup = _pull(804, "Duplicate of #805")
        original = _pull(805, "Some fix", state="open")

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "original-still-open-804-805" in excluded_slugs

    def test_a_pr_with_no_duplicate_marker_produces_no_candidate_at_all(self):
        pull = _pull(806, "A regular doc PR, no duplicate mention at all.")

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-duplicate-marker-806"

    def test_a_duplicate_that_is_itself_already_closed_is_never_considered(self):
        dup = _pull(807, "Duplicate of #808", state="closed", closed_at=datetime(2026, 7, 22, 11, 0, 0, tzinfo=timezone.utc))
        original = _pull(808, "Some fix", state="closed", closed_at=datetime(2026, 7, 22, 10, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_an_unrecognized_original_number_is_excluded_not_surfaced(self):
        dup = _pull(809, "duplicate of #999")

        surfaced, excluded = detector.compute_gaps([dup], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "nonexistent-original-809-999"

    def test_an_original_that_is_still_open_is_not_treated_as_resolved_even_if_it_has_a_closed_at(self):
        # A malformed/hypothetical row: state="open" but closed_at set.
        # state is the source of truth for "resolved", not closed_at alone.
        dup = _pull(810, "Duplicate of #811")
        original = _pull(811, "Some fix", state="open", closed_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "original-still-open-810-811" in excluded_slugs


class TestNonexistentOriginalIsNotMislabeledStillOpen:
    """ROADMAP.md #432: before this fix, `original is None or original.state
    not in _RESOLVED_STATES` folded a dangling reference (the named original
    was never real) into the same `original-still-open-...` slug and the
    same false detail line ("that PR has not resolved yet") as a
    genuinely-unresolved original -- the PR-side twin of the same conflation
    fixed in `duplicate-issue-still-open/detector.py`. A dangling reference
    gets its own `nonexistent-original-...` slug now."""

    def test_a_named_original_that_does_not_exist_is_excluded_as_nonexistent_not_still_open(self):
        dup = _pull(812, "duplicate of #999")  # #999 is never in the pull list at all

        surfaced, excluded = detector.compute_gaps([dup], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        candidate = excluded[0]
        assert candidate.slug == "nonexistent-original-812-999"
        assert "resolved" not in candidate.detail
        assert "open" not in candidate.detail
        assert candidate.evidence == [dup.url]  # no original.url to append -- it doesn't exist

    def test_a_named_original_that_exists_and_is_still_open_is_still_excluded_as_still_open(self):
        # The genuinely-unresolved path must survive the split unchanged.
        # `original` itself is also `open` here, but with no duplicate
        # marker of its own, so it produces its own separate excluded
        # candidate -- this test asserts on the #813 candidate specifically.
        dup = _pull(813, "Duplicate of #814")
        original = _pull(814, "Some fix", state="open")

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert surfaced == []
        by_slug = {g.slug: g for g in excluded}
        candidate = by_slug["original-still-open-813-814"]
        assert candidate.evidence == [dup.url, original.url]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "duplicate-pr-still-open-801-800"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_closed_original_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "duplicate-pr-still-open-802-803" in tail_slugs

    def test_the_shipped_fixture_excludes_the_still_open_named_original(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "original-still-open-804-805" in excluded_slugs
        assert "no-duplicate-marker-806" in excluded_slugs
        assert "nonexistent-original-809-999" in excluded_slugs

    def test_the_shipped_fixture_never_considers_the_already_closed_duplicate(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-807-" in s for s in all_slugs)


class TestLoaders:
    """load_pulls -- mirrors every prior recipe's own _load_rows guard
    against syntactically valid but non-list JSON."""

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
