"""Tests for RECIPES/locked-resolved-issue-still-open/detector.py's own
detection logic -- the sixty-fourth real recipe: an issue is locked as
resolved, but never actually closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "locked-resolved-issue-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_locked_resolved_issue_still_open_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


def _issue(
    number: int,
    *,
    state: str = "open",
    locked: bool = True,
    active_lock_reason: str | None = "resolved",
    updated_at: datetime | None = None,
) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state, locked=locked,
        active_lock_reason=active_lock_reason,
        updated_at=updated_at or _NOW,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestLoadIssues:
    def test_loads_the_real_fixture_without_error(self):
        issues = detector.load_issues()
        assert len(issues) == 10
        numbers = {i.number for i in issues}
        assert numbers == {1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1209, 1210}

    def test_parses_fields_correctly_for_one_row(self):
        issues = detector.load_issues()
        by_number = {i.number: i for i in issues}
        issue = by_number[1201]
        assert issue.title == "Report generator double-counts a candidate on a tied confidence score"
        assert issue.state == "open"
        assert issue.locked is True
        assert issue.active_lock_reason == "resolved"
        assert issue.updated_at == datetime(2026, 8, 1, 9, 0, 0, tzinfo=timezone.utc)

    def test_a_null_active_lock_reason_parses_as_none(self):
        issues = detector.load_issues()
        by_number = {i.number: i for i in issues}
        assert by_number[1207].active_lock_reason is None
        assert by_number[1208].active_lock_reason is None

    def test_rejects_a_non_list_payload(self, tmp_path):
        bad = tmp_path / "issues.json"
        bad.write_text(json.dumps({"not": "a list"}))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad)


class TestComputeGapsSurfaced:
    def test_a_stale_locked_resolved_open_issue_is_surfaced_at_high_confidence(self):
        issue = _issue(1201, updated_at=_NOW - timedelta(hours=171))

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "locked-resolved-issue-still-open-1201"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [issue.url]
        assert "resolved" in surfaced[0].detail
        assert "state='open'" in surfaced[0].detail

    def test_a_recently_locked_resolved_open_issue_is_surfaced_at_low_confidence(self):
        issue = _issue(1202, updated_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_exactly_at_the_24h_boundary_scores_high_confidence(self):
        issue = _issue(1211, updated_at=_NOW - timedelta(hours=24))

        surfaced, _ = detector.compute_gaps([issue], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_just_under_the_24h_boundary_scores_low_confidence(self):
        issue = _issue(1212, updated_at=_NOW - timedelta(hours=23, minutes=59))

        surfaced, _ = detector.compute_gaps([issue], now=_NOW)

        assert surfaced[0].confidence == 0.5

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        fresh = _issue(1301, updated_at=_NOW - timedelta(hours=1))
        stale = _issue(1302, updated_at=_NOW - timedelta(hours=200))

        surfaced, _ = detector.compute_gaps([fresh, stale], now=_NOW)

        assert [g.slug for g in surfaced] == [
            "locked-resolved-issue-still-open-1302",
            "locked-resolved-issue-still-open-1301",
        ]

    def test_multiple_qualifying_issues_each_get_their_own_candidate(self):
        a = _issue(1401, updated_at=_NOW - timedelta(hours=100))
        b = _issue(1402, updated_at=_NOW - timedelta(hours=100))

        surfaced, _ = detector.compute_gaps([a, b], now=_NOW)

        assert {g.slug for g in surfaced} == {
            "locked-resolved-issue-still-open-1401",
            "locked-resolved-issue-still-open-1402",
        }


class TestComputeGapsExcluded:
    def test_not_locked_issue_is_excluded(self):
        issue = _issue(1501, locked=False, active_lock_reason=None)

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-locked-1501"
        assert excluded[0].confidence == 0.0

    def test_locked_with_off_topic_reason_is_excluded(self):
        issue = _issue(1502, active_lock_reason="off-topic")

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "non-resolution-lock-reason-1502"

    def test_locked_with_spam_reason_is_excluded(self):
        issue = _issue(1503, active_lock_reason="spam")

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "non-resolution-lock-reason-1503"

    def test_locked_with_too_heated_reason_is_excluded(self):
        issue = _issue(1504, active_lock_reason="too heated")

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "non-resolution-lock-reason-1504"

    def test_locked_with_no_reason_recorded_is_excluded_distinctly_from_non_resolution_reason(self):
        issue = _issue(1505, active_lock_reason=None)

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-lock-reason-1505"

    def test_locked_resolved_but_already_closed_is_excluded(self):
        issue = _issue(1506, state="closed", active_lock_reason="resolved")

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "already-closed-1506"

    def test_malformed_unlocked_with_reason_is_excluded_and_named_malformed(self):
        issue = _issue(1507, locked=False, active_lock_reason="resolved")

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "malformed-lock-1507"
        assert "malformed" in excluded[0].detail.lower()

    def test_not_locked_takes_priority_over_reason_check_even_when_closed(self):
        issue = _issue(1508, locked=False, active_lock_reason=None, state="closed")

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "not-locked-1508"

    def test_off_topic_locked_but_closed_is_still_excluded_by_reason_not_state(self):
        # The reason check runs before the state check, so a non-"resolved"
        # reason is excluded on its own grounds regardless of state --
        # named precisely, not folded into the "already closed" bucket.
        issue = _issue(1509, active_lock_reason="spam", state="closed")

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "non-resolution-lock-reason-1509"


class TestComputeGapsMixedFixture:
    def test_the_real_fixture_elects_1201_as_primary(self):
        issues = detector.load_issues()

        surfaced, excluded = detector.compute_gaps(issues, now=_NOW)

        assert [g.slug for g in surfaced] == [
            "locked-resolved-issue-still-open-1201",
            "locked-resolved-issue-still-open-1202",
        ]
        assert surfaced[0].confidence == 0.85
        assert surfaced[1].confidence == 0.5

    def test_the_real_fixture_excludes_every_non_qualifying_issue_named_not_hidden(self):
        issues = detector.load_issues()

        _, excluded = detector.compute_gaps(issues, now=_NOW)

        excluded_slugs = {g.slug for g in excluded}
        assert excluded_slugs == {
            "already-closed-1203",
            "non-resolution-lock-reason-1204",
            "non-resolution-lock-reason-1205",
            "non-resolution-lock-reason-1206",
            "no-lock-reason-1207",
            "not-locked-1208",
            "malformed-lock-1209",
            "not-locked-1210",
        }
        assert all(g.confidence == 0.0 for g in excluded)

    def test_the_real_fixture_surfaces_no_more_and_no_fewer_than_two(self):
        issues = detector.load_issues()
        surfaced, _ = detector.compute_gaps(issues, now=_NOW)
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

    def test_primary_gap_is_issue_1201(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"]["slug"] == "locked-resolved-issue-still-open-1201"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_tail_carries_issue_1202(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = [g["slug"] for g in result["tail"]]
        assert tail_slugs == ["locked-resolved-issue-still-open-1202"]

    def test_excluded_carries_all_eight_non_qualifying_issues(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert len(result["excluded"]) == 8

    def test_uses_the_real_wall_clock_by_default(self):
        # No `now` passed -- exercises the real datetime.now(timezone.utc)
        # branch, the same "manual demo drifts with real time" property
        # every sibling recipe's own bare-run mode carries.
        result = detector.run_recipe_scan()
        assert result["source"] == "fixture"
        assert "generated_at" in result

    def test_accepts_an_explicit_issues_path_override(self, tmp_path):
        custom = tmp_path / "issues.json"
        custom.write_text(json.dumps([
            {
                "number": 9001,
                "title": "Custom fixture issue",
                "state": "open",
                "locked": True,
                "active_lock_reason": "resolved",
                "updated_at": "2026-08-01T00:00:00Z",
                "url": "https://github.com/example/example-repo/issues/9001",
            }
        ]))

        result = detector.run_recipe_scan(issues_path=custom, now=_NOW)

        assert result["primary_gap"]["slug"] == "locked-resolved-issue-still-open-9001"


class TestRecipeManifest:
    """The manifest itself, checked the same way every sibling recipe's own
    test file checks its own recipe.json -- schema-valid, read-only scopes,
    fixture pointed under fixtures/, and it actually discovers cleanly
    through the real validator every PR is held to."""

    def test_recipe_json_is_valid_and_discovered_cleanly(self):
        from seam_engine.recipes import discover_recipes

        manifests = discover_recipes(FENCEPOST_ROOT)
        slugs = {m.slug for m in manifests}
        assert "locked-resolved-issue-still-open" in slugs

    def test_recipe_json_declares_only_already_cleared_scopes(self):
        manifest_path = (
            FENCEPOST_ROOT / "RECIPES" / "locked-resolved-issue-still-open" / "recipe.json"
        )
        manifest = json.loads(manifest_path.read_text())
        assert manifest["scopes"] == ["ListIssues"]
        assert manifest["toolkit"] == "github"
        assert manifest["fixture"] == "fixtures/locked_resolved_issue_still_open"
        assert manifest["entrypoint"] == "run_recipe_scan"
        assert manifest["detector_file"] == "detector.py"
