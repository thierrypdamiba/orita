"""Tests for RECIPES/merged-pr-never-released/detector.py's own detection
logic (ROADMAP.md #381) -- the twelfth real recipe: a pull request merged
long ago, but no release has ever claimed it. The inverse of
release-claims-unmerged-pr (task 378): that recipe watches a release's own
FALSE claim about a PR that never merged; this one watches a merged PR's
own SILENCE across every release read so far.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "merged-pr-never-released" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_merged_pr_never_released_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def _pr(
    number: int,
    state: str = "closed",
    merged: bool = True,
    merged_at: datetime | None = None,
) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged,
        merged_at=merged_at,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


def _release(tag: str, body: str, published_at: datetime | None = None) -> "detector.Release":
    return detector.Release(
        id=f"rel-{tag}", title=tag, tag=tag, body=body,
        published_at=published_at or _NOW,
        url=f"https://github.com/example/example-repo/releases/tag/{tag}",
    )


class TestComputeGaps:
    def test_a_stale_uncredited_merge_is_surfaced_at_high_confidence(self):
        pr = _pr(2001, merged_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-never-released-2001"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_merged_pr_is_surfaced_at_low_confidence(self):
        pr = _pr(2002, merged_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_merge_exactly_at_the_stale_bar_is_high_confidence(self):
        pr = _pr(2003, merged_at=_NOW - timedelta(hours=96))

        surfaced, _ = detector.compute_gaps([pr], [], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_a_pr_claimed_by_a_release_is_excluded_not_surfaced(self):
        pr = _pr(2004, merged_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v1.0.0", "This release ships #2004 and nothing else.")

        surfaced, excluded = detector.compute_gaps([pr], [release], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "pr-claimed-2004"

    def test_a_pr_claimed_by_an_older_release_not_just_the_newest_is_excluded(self):
        # A PR credited by a PAST release, not the most recent one read --
        # proves the check scans every release read so far, not only the
        # latest `GetLatestRelease` snapshot.
        pr = _pr(2005, merged_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        old_release = _release("v0.9.0", "Includes #2005.", published_at=datetime(2026, 7, 21, 0, 0, 0, tzinfo=timezone.utc))
        newest_release = _release("v1.1.0", "A quiet patch release, no claims.", published_at=_NOW)

        surfaced, excluded = detector.compute_gaps([pr], [old_release, newest_release], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "pr-claimed-2005"

    def test_a_still_open_pr_is_excluded_not_surfaced(self):
        pr = _pr(2006, state="open", merged=False, merged_at=None)

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "pr-not-merged-2006"

    def test_a_closed_unmerged_pr_is_excluded_not_surfaced(self):
        pr = _pr(2007, state="closed", merged=False, merged_at=None)

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "pr-not-merged-2007"

    def test_a_release_claiming_an_unrelated_pr_number_does_not_clear_the_real_one(self):
        pr = _pr(2008, merged_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v2.0.0", "Includes #9999, unrelated to this fixture.")

        surfaced, excluded = detector.compute_gaps([pr], [release], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-never-released-2008"

    def test_a_bare_hash_mention_with_no_claim_verb_does_not_clear_it(self):
        # "see #N for background" is not a shipped-it claim -- the same
        # claim-verb anchor release-claims-unmerged-pr's own regex holds.
        pr = _pr(2009, merged_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v2.0.1", "See #2009 for background context.")

        surfaced, excluded = detector.compute_gaps([pr], [release], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-never-released-2009"


class TestMergedPrWithNoTimestampIsNotMislabeledUnmerged:
    """ROADMAP.md #433: `not pr.merged or pr.merged_at is None` folded a
    genuinely-unmerged PR and a PR that reads merged=True but carries no
    merged_at (a malformed record) into the same `pr-not-merged-...` slug
    and its detail line, which itself would print "merged=True" underneath
    a headline claiming "never merged" -- a direct self-contradiction.
    Split so the malformed case gets its own honest slug."""

    def test_a_merged_pr_with_no_timestamp_is_excluded_as_malformed_not_unmerged(self):
        pr = _pr(750, merged=True, merged_at=None)

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        candidate = excluded[0]
        assert candidate.slug == "pr-merged-no-timestamp-750"
        assert "never merged" not in candidate.headline
        assert "malformed" in candidate.detail
        assert candidate.evidence == [pr.url]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "merged-pr-never-released-1001"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recent_merge_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "merged-pr-never-released-1002" in tail_slugs

    def test_the_shipped_fixture_excludes_the_claimed_and_unmerged_prs(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "pr-claimed-1003" in excluded_slugs
        assert "pr-not-merged-1004" in excluded_slugs
        assert "pr-not-merged-1005" in excluded_slugs

    def test_the_shipped_fixture_never_considers_1003_1004_1005_as_candidates(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-1003" in s or "-1004" in s or "-1005" in s for s in all_slugs)


class TestLoaders:
    """load_pull_requests/load_releases -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_pull_requests_parses_the_real_fixture(self):
        pull_requests = detector.load_pull_requests()
        assert len(pull_requests) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pull_requests)

    def test_load_releases_parses_the_real_fixture(self):
        releases = detector.load_releases()
        assert len(releases) > 0
        assert all(isinstance(r, detector.Release) for r in releases)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pull_requests_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pull_requests(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_releases_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_releases(bad_file)
