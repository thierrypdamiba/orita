"""Tests for RECIPES/commit-closes-keyword-pr-still-open/detector.py's own
detection logic (ROADMAP.md #403) -- the twenty-fifth real recipe: a commit
already on the default branch names a real GitHub closing keyword for a
PULL REQUEST that is still open, the PR-side twin of
`commit-closes-keyword-issue-still-open` (task 388), which explicitly only
ever checked issue numbers.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "commit-closes-keyword-pr-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_commit_closes_keyword_pr_still_open_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 30, 12, 0, 0, tzinfo=timezone.utc)


def _commit(sha: str, message: str, ts: datetime, author: str = "some-god") -> "detector.Commit":
    return detector.Commit(
        sha=sha, message=message, ts=ts, author=author,
        url=f"https://github.com/example/example-repo/commit/{sha}",
    )


def _pr(
    number: int, state: str = "open", merged: bool = False, merged_at: datetime | None = None
) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged, merged_at=merged_at,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestClosingRefs:
    @pytest.mark.parametrize(
        "message,expected",
        [
            ("Fixes #901", [901]),
            ("closes #902: draft-back retry now caps its own backoff", [902]),
            ("Resolved #903", [903]),
            ("fixed #12", [12]),
            ("closed #13", [13]),
            ("resolves #14", [14]),
        ],
    )
    def test_recognized_keyword_forms(self, message, expected):
        assert detector._closing_refs(message) == expected

    def test_present_participle_never_matches(self):
        # Iron Rule #8's own prescribed safe phrasing -- proven safe here,
        # on the PR side exactly as it already was on the issue side.
        assert detector._closing_refs("closing #901 as a worked example, not a live command") == []

    def test_bare_mention_never_matches(self):
        assert detector._closing_refs("Touches #904 while investigating, no promise made") == []

    def test_multiple_refs_in_one_message_are_all_returned_deduplicated(self):
        assert detector._closing_refs("fixes #1 and closes #2, also fixes #1 again") == [1, 2]


class TestComputeGaps:
    def test_a_stale_promise_on_a_still_open_pr_is_surfaced_at_high_confidence(self):
        commit = _commit("a1", "Fixes #901", ts=_NOW - timedelta(hours=31))
        pr = _pr(901)

        surfaced, excluded = detector.compute_gaps([commit], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-closes-keyword-pr-still-open-a1-901"
        assert surfaced[0].confidence == 0.85

    def test_a_promise_exactly_at_the_24h_line_is_surfaced_at_high_confidence(self):
        commit = _commit("a2", "Fixes #901", ts=_NOW - timedelta(hours=24))
        pr = _pr(901)

        surfaced, excluded = detector.compute_gaps([commit], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_promise_on_a_still_open_pr_is_surfaced_at_low_confidence(self):
        commit = _commit("b2", "closes #902", ts=_NOW - timedelta(hours=6))
        pr = _pr(902)

        surfaced, excluded = detector.compute_gaps([commit], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_promise_on_an_already_merged_pr_is_excluded_not_surfaced(self):
        commit = _commit("c3", "Resolved #903", ts=_NOW - timedelta(hours=48))
        pr = _pr(903, state="closed", merged=True, merged_at=_NOW - timedelta(hours=40))

        surfaced, excluded = detector.compute_gaps([commit], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "already-resolved-c3-903"
        assert "already merged" in excluded[0].detail

    def test_a_promise_on_a_pr_closed_without_merging_is_excluded_not_surfaced(self):
        commit = _commit("c4", "closed #905", ts=_NOW - timedelta(hours=48))
        pr = _pr(905, state="closed", merged=False, merged_at=None)

        surfaced, excluded = detector.compute_gaps([commit], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "already-resolved-c4-905"
        assert "closed without merging" in excluded[0].detail

    def test_a_commit_with_no_closing_keyword_produces_no_candidate_at_all(self):
        commit = _commit("d4", "Touches #904 while investigating, no promise made", ts=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([commit], [_pr(904)], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-d4"

    def test_a_promise_naming_a_nonexistent_pr_is_excluded_not_surfaced(self):
        # A broken link, not this recipe's own seam.
        commit = _commit("e5", "fixes #999", ts=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "nonexistent-target-e5-999"

    def test_present_participle_phrasing_is_excluded_as_no_keyword_at_all(self):
        commit = _commit("f6", "closing #901 the way the guard's docstring describes it", ts=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([commit], [_pr(901)], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-f6"

    def test_one_commit_naming_two_prs_produces_two_independent_candidates(self):
        commit = _commit("g7", "fixes #1 and closes #2", ts=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([commit], [_pr(1), _pr(2)], now=_NOW)

        assert excluded == []
        slugs = {g.slug for g in surfaced}
        assert slugs == {
            "commit-closes-keyword-pr-still-open-g7-1",
            "commit-closes-keyword-pr-still-open-g7-2",
        }

    def test_one_commit_naming_two_prs_where_only_one_resolves_splits_surfaced_and_excluded(self):
        commit = _commit("h8", "fixes #1 and closes #2", ts=_NOW - timedelta(hours=48))
        pr1 = _pr(1)  # still open -- surfaced
        pr2 = _pr(2, state="closed", merged=True, merged_at=_NOW - timedelta(hours=30))  # resolved -- excluded

        surfaced, excluded = detector.compute_gaps([commit], [pr1, pr2], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-closes-keyword-pr-still-open-h8-1"
        assert len(excluded) == 1
        assert excluded[0].slug == "already-resolved-h8-2"

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        fresh = _commit("i9", "fixes #1", ts=_NOW - timedelta(hours=2))
        stale = _commit("j0", "fixes #2", ts=_NOW - timedelta(hours=50))

        surfaced, _ = detector.compute_gaps([fresh, stale], [_pr(1), _pr(2)], now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.5]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "commit-closes-keyword-pr-still-open-p1q2r3s-901"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_promise_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "commit-closes-keyword-pr-still-open-q2r3s4t-902" in tail_slugs

    def test_the_shipped_fixture_excludes_the_resolved_and_keywordless_and_dangling_commits(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "already-resolved-r3s4t5u-903" in excluded_slugs
        assert "already-resolved-s4t5u6v-905" in excluded_slugs
        assert "no-closing-keyword-t5u6v7w" in excluded_slugs
        assert "nonexistent-target-u6v7w8x-999" in excluded_slugs
        assert "no-closing-keyword-v7w8x9y" in excluded_slugs

    def test_the_shipped_fixture_produces_exactly_five_excluded_candidates(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert len(result["excluded"]) == 5

    def test_generated_at_reflects_the_passed_in_clock(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["generated_at"] == _NOW.isoformat()

    def test_source_is_honestly_marked_fixture(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"


class TestLoaders:
    """load_commits/load_prs -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_commits_parses_the_real_fixture(self):
        commits = detector.load_commits()
        assert len(commits) > 0
        assert all(isinstance(c, detector.Commit) for c in commits)

    def test_load_prs_parses_the_real_fixture(self):
        prs = detector.load_prs()
        assert len(prs) > 0
        assert all(isinstance(p, detector.PullRequest) for p in prs)

    def test_load_prs_parses_merged_and_merged_at_fields(self):
        prs = detector.load_prs()
        merged_pr = next(p for p in prs if p.number == 903)
        assert merged_pr.merged is True
        assert merged_pr.merged_at is not None

    def test_load_prs_leaves_merged_at_none_for_an_open_pr(self):
        prs = detector.load_prs()
        open_pr = next(p for p in prs if p.number == 901)
        assert open_pr.merged is False
        assert open_pr.merged_at is None

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_commits_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_commits(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_prs_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_prs(bad_file)


class TestSharedRegexImport:
    """Proves this recipe actually imports `CLOSING_KEYWORD_RE` from the
    shared module rather than retyping a sixth copy -- the exact drift
    `tools/duplicate_regex_check.py` exists to catch. Object identity, not
    just textual similarity, per task 394's own lesson."""

    def test_closing_keyword_re_is_the_same_object_as_the_shared_module(self):
        from seam_engine.closing_keywords import CLOSING_KEYWORD_RE

        assert detector.CLOSING_KEYWORD_RE is CLOSING_KEYWORD_RE
