"""Tests for RECIPES/locked-resolved-pr-still-open/detector.py's own
detection logic -- the ninety-first real recipe: a pull request is locked
as resolved, but never actually closed or merged.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "locked-resolved-pr-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_locked_resolved_pr_still_open_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)


def _pull(
    number: int,
    *,
    state: str = "open",
    locked: bool = True,
    active_lock_reason: str | None = "resolved",
    updated_at: datetime | None = None,
) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, locked=locked,
        active_lock_reason=active_lock_reason,
        updated_at=updated_at or _NOW,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestLoadPulls:
    def test_loads_the_real_fixture_without_error(self):
        pulls = detector.load_pulls()
        assert len(pulls) == 11
        numbers = {p.number for p in pulls}
        assert numbers == {1301, 1302, 1303, 1304, 1305, 1306, 1307, 1308, 1309, 1310, 1311}

    def test_parses_fields_correctly_for_one_row(self):
        pulls = detector.load_pulls()
        by_number = {p.number: p for p in pulls}
        pull = by_number[1301]
        assert pull.title == "Swap the ranking margin's tie-break to prefer the older candidate"
        assert pull.state == "open"
        assert pull.locked is True
        assert pull.active_lock_reason == "resolved"
        assert pull.updated_at == datetime(2026, 8, 8, 5, 0, 0, tzinfo=timezone.utc)

    def test_a_null_active_lock_reason_parses_as_none(self):
        pulls = detector.load_pulls()
        by_number = {p.number: p for p in pulls}
        assert by_number[1308].active_lock_reason is None
        assert by_number[1309].active_lock_reason is None

    def test_rejects_a_non_list_payload(self, tmp_path):
        bad = tmp_path / "pulls.json"
        bad.write_text(json.dumps({"not": "a list"}))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad)


class TestComputeGapsSurfaced:
    def test_a_stale_locked_resolved_open_pr_is_surfaced_at_high_confidence(self):
        pull = _pull(1301, updated_at=_NOW - timedelta(hours=175))

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "locked-resolved-pr-still-open-1301"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [pull.url]
        assert "resolved" in surfaced[0].detail
        assert "state='open'" in surfaced[0].detail

    def test_a_recently_locked_resolved_open_pr_is_surfaced_at_low_confidence(self):
        pull = _pull(1302, updated_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_exactly_at_the_24h_boundary_scores_high_confidence(self):
        pull = _pull(1401, updated_at=_NOW - timedelta(hours=24))

        surfaced, _ = detector.compute_gaps([pull], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_just_under_the_24h_boundary_scores_low_confidence(self):
        pull = _pull(1402, updated_at=_NOW - timedelta(hours=23, minutes=59))

        surfaced, _ = detector.compute_gaps([pull], now=_NOW)

        assert surfaced[0].confidence == 0.5

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        fresh = _pull(1501, updated_at=_NOW - timedelta(hours=1))
        stale = _pull(1502, updated_at=_NOW - timedelta(hours=200))

        surfaced, _ = detector.compute_gaps([fresh, stale], now=_NOW)

        assert [g.slug for g in surfaced] == [
            "locked-resolved-pr-still-open-1502",
            "locked-resolved-pr-still-open-1501",
        ]

    def test_multiple_qualifying_pulls_each_get_their_own_candidate(self):
        a = _pull(1601, updated_at=_NOW - timedelta(hours=100))
        b = _pull(1602, updated_at=_NOW - timedelta(hours=100))

        surfaced, _ = detector.compute_gaps([a, b], now=_NOW)

        assert {g.slug for g in surfaced} == {
            "locked-resolved-pr-still-open-1601",
            "locked-resolved-pr-still-open-1602",
        }


class TestComputeGapsExcluded:
    def test_not_locked_pr_is_excluded(self):
        pull = _pull(1701, locked=False, active_lock_reason=None)

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-locked-1701"
        assert excluded[0].confidence == 0.0

    def test_locked_with_off_topic_reason_is_excluded(self):
        pull = _pull(1702, active_lock_reason="off-topic")

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "non-resolution-lock-reason-1702"

    def test_locked_with_spam_reason_is_excluded(self):
        pull = _pull(1703, active_lock_reason="spam")

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "non-resolution-lock-reason-1703"

    def test_locked_with_too_heated_reason_is_excluded(self):
        pull = _pull(1704, active_lock_reason="too heated")

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "non-resolution-lock-reason-1704"

    def test_locked_with_no_reason_recorded_is_excluded_distinctly_from_non_resolution_reason(self):
        pull = _pull(1705, active_lock_reason=None)

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-lock-reason-1705"

    def test_locked_resolved_but_already_merged_is_excluded(self):
        pull = _pull(1706, state="merged", active_lock_reason="resolved")

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "already-resolved-1706"
        assert "merged" in excluded[0].headline

    def test_locked_resolved_but_already_closed_without_merging_is_excluded(self):
        pull = _pull(1707, state="closed", active_lock_reason="resolved")

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "already-resolved-1707"
        assert "closed" in excluded[0].headline

    def test_malformed_unlocked_with_reason_is_excluded_and_named_malformed(self):
        pull = _pull(1708, locked=False, active_lock_reason="resolved")

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "malformed-lock-1708"
        assert "malformed" in excluded[0].detail.lower()

    def test_not_locked_takes_priority_over_reason_check_even_when_closed(self):
        pull = _pull(1709, locked=False, active_lock_reason=None, state="closed")

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "not-locked-1709"

    def test_off_topic_locked_but_closed_is_still_excluded_by_reason_not_state(self):
        # The reason check runs before the state check, so a non-"resolved"
        # reason is excluded on its own grounds regardless of state --
        # named precisely, not folded into the "already resolved" bucket.
        pull = _pull(1710, active_lock_reason="spam", state="closed")

        surfaced, excluded = detector.compute_gaps([pull], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "non-resolution-lock-reason-1710"


class TestComputeGapsMixedFixture:
    def test_the_real_fixture_elects_1301_as_primary(self):
        pulls = detector.load_pulls()

        surfaced, excluded = detector.compute_gaps(pulls, now=_NOW)

        assert [g.slug for g in surfaced] == [
            "locked-resolved-pr-still-open-1301",
            "locked-resolved-pr-still-open-1302",
        ]
        assert surfaced[0].confidence == 0.85
        assert surfaced[1].confidence == 0.5

    def test_the_real_fixture_excludes_every_non_qualifying_pull_named_not_hidden(self):
        pulls = detector.load_pulls()

        _, excluded = detector.compute_gaps(pulls, now=_NOW)

        excluded_slugs = {g.slug for g in excluded}
        assert excluded_slugs == {
            "already-resolved-1303",
            "already-resolved-1304",
            "non-resolution-lock-reason-1305",
            "non-resolution-lock-reason-1306",
            "non-resolution-lock-reason-1307",
            "no-lock-reason-1308",
            "not-locked-1309",
            "malformed-lock-1310",
            "not-locked-1311",
        }
        assert all(g.confidence == 0.0 for g in excluded)

    def test_the_real_fixture_surfaces_no_more_and_no_fewer_than_two(self):
        pulls = detector.load_pulls()
        surfaced, _ = detector.compute_gaps(pulls, now=_NOW)
        assert len(surfaced) == 2

    def test_empty_input_surfaces_and_excludes_nothing(self):
        surfaced, excluded = detector.compute_gaps([], now=_NOW)
        assert surfaced == []
        assert excluded == []


class TestRunRecipeScan:
    def test_output_shape_matches_every_sibling_recipe(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["generated_at"] == _NOW.isoformat()
        assert set(result.keys()) == {
            "generated_at", "source", "confidence_bar", "separation_margin",
            "primary_gap", "tail", "excluded",
        }

    def test_primary_gap_is_pr_1301(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"]["slug"] == "locked-resolved-pr-still-open-1301"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_tail_carries_pr_1302(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = [g["slug"] for g in result["tail"]]
        assert tail_slugs == ["locked-resolved-pr-still-open-1302"]

    def test_excluded_carries_all_nine_non_qualifying_pulls(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert len(result["excluded"]) == 9

    def test_uses_the_real_wall_clock_by_default(self):
        # No `now` passed -- exercises the real datetime.now(timezone.utc)
        # branch, the same "manual demo drifts with real time" property
        # every sibling recipe's own bare-run mode carries.
        result = detector.run_recipe_scan()
        assert result["source"] == "fixture"
        assert "generated_at" in result

    def test_accepts_an_explicit_pulls_path_override(self, tmp_path):
        custom = tmp_path / "pulls.json"
        custom.write_text(json.dumps([
            {
                "number": 9001,
                "title": "Custom fixture PR",
                "state": "open",
                "locked": True,
                "active_lock_reason": "resolved",
                "updated_at": "2026-08-01T00:00:00Z",
                "url": "https://github.com/example/example-repo/pull/9001",
            }
        ]))

        result = detector.run_recipe_scan(pulls_path=custom, now=_NOW)

        assert result["primary_gap"]["slug"] == "locked-resolved-pr-still-open-9001"


class TestRecipeManifest:
    """The manifest itself, checked the same way every sibling recipe's own
    test file checks its own recipe.json -- schema-valid, read-only scopes,
    fixture pointed under fixtures/, and it actually discovers cleanly
    through the real validator every PR is held to."""

    def test_recipe_json_is_valid_and_discovered_cleanly(self):
        from seam_engine.recipes import discover_recipes

        manifests = discover_recipes(FENCEPOST_ROOT)
        slugs = {m.slug for m in manifests}
        assert "locked-resolved-pr-still-open" in slugs

    def test_recipe_json_declares_only_already_cleared_scopes(self):
        manifest_path = (
            FENCEPOST_ROOT / "RECIPES" / "locked-resolved-pr-still-open" / "recipe.json"
        )
        manifest = json.loads(manifest_path.read_text())
        assert manifest["scopes"] == ["ListPullRequests", "GetPullRequest"]
        assert manifest["toolkit"] == "github"
        assert manifest["fixture"] == "fixtures/locked_resolved_pr_still_open"
        assert manifest["entrypoint"] == "run_recipe_scan"
        assert manifest["detector_file"] == "detector.py"
