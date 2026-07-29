"""Tests for RECIPES/milestone-closed-never-released/detector.py's own
detection logic (ROADMAP.md #383) -- the fourteenth real recipe: a
milestone closed long ago, but no release has ever claimed it. The
milestone-side twin of merged-pr-never-released (task 381): that recipe
watches a merged PR's own SILENCE across every release read so far; this
one watches the identical silence one level up, against a milestone.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "milestone-closed-never-released" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_milestone_closed_never_released_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _milestone(
    number: int,
    state: str = "closed",
    closed_at: datetime | None = None,
) -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        closed_at=closed_at,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


def _release(tag: str, body: str, published_at: datetime | None = None) -> "detector.Release":
    return detector.Release(
        id=f"rel-{tag}", title=tag, tag=tag, body=body,
        published_at=published_at or _NOW,
        url=f"https://github.com/example/example-repo/releases/tag/{tag}",
    )


class TestComputeGaps:
    def test_a_stale_uncredited_close_is_surfaced_at_high_confidence(self):
        milestone = _milestone(3001, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([milestone], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-closed-never-released-3001"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_milestone_is_surfaced_at_low_confidence(self):
        milestone = _milestone(3002, closed_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([milestone], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_close_exactly_at_the_stale_bar_is_high_confidence(self):
        milestone = _milestone(3003, closed_at=_NOW - timedelta(hours=96))

        surfaced, _ = detector.compute_gaps([milestone], [], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_a_milestone_claimed_by_a_release_is_excluded_not_surfaced(self):
        milestone = _milestone(3004, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v1.0.0", "This release ships milestone #3004 and nothing else.")

        surfaced, excluded = detector.compute_gaps([milestone], [release], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "milestone-claimed-3004"

    def test_a_milestone_claimed_by_an_older_release_not_just_the_newest_is_excluded(self):
        # A milestone credited by a PAST release, not the most recent one
        # read -- proves the check scans every release read so far, not
        # only the latest `GetLatestRelease` snapshot.
        milestone = _milestone(3005, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        old_release = _release("v0.9.0", "Milestone #3005 shipped.", published_at=datetime(2026, 7, 21, 0, 0, 0, tzinfo=timezone.utc))
        newest_release = _release("v1.1.0", "A quiet patch release, no claims.", published_at=_NOW)

        surfaced, excluded = detector.compute_gaps([milestone], [old_release, newest_release], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "milestone-claimed-3005"

    def test_a_still_open_milestone_is_excluded_not_surfaced(self):
        milestone = _milestone(3006, state="open", closed_at=None)

        surfaced, excluded = detector.compute_gaps([milestone], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "milestone-not-closed-3006"

    def test_a_release_claiming_an_unrelated_milestone_number_does_not_clear_the_real_one(self):
        milestone = _milestone(3007, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v2.0.0", "Milestone #9999 shipped, unrelated to this fixture.")

        surfaced, excluded = detector.compute_gaps([milestone], [release], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-closed-never-released-3007"

    def test_a_bare_hash_mention_with_no_milestone_word_does_not_clear_it(self):
        # "see #N for background" is not a shipped-it claim -- the claim
        # phrase requires the literal word "milestone" before the number.
        milestone = _milestone(3008, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v2.0.1", "See #3008 for background context.")

        surfaced, excluded = detector.compute_gaps([milestone], [release], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-closed-never-released-3008"

    def test_the_claim_phrase_is_case_insensitive(self):
        milestone = _milestone(3009, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v2.0.2", "MILESTONE #3009 is done.")

        surfaced, excluded = detector.compute_gaps([milestone], [release], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "milestone-claimed-3009"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "milestone-closed-never-released-2002"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recent_close_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "milestone-closed-never-released-2003" in tail_slugs

    def test_the_shipped_fixture_excludes_the_claimed_and_open_milestones(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "milestone-claimed-2001" in excluded_slugs
        assert "milestone-not-closed-2004" in excluded_slugs

    def test_the_shipped_fixture_never_considers_2001_2004_as_candidates(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-2001" in s or "-2004" in s for s in all_slugs)


class TestLoaders:
    """load_milestones/load_releases -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    def test_load_releases_parses_the_real_fixture(self):
        releases = detector.load_releases()
        assert len(releases) > 0
        assert all(isinstance(r, detector.Release) for r in releases)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_releases_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_releases(bad_file)
