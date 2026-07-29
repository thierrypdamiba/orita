"""Tests for RECIPES/commit-closes-keyword-issue-still-open/detector.py's
own detection logic (ROADMAP.md #377) -- the eighth real recipe: a commit
already on the default branch names a real GitHub closing keyword for an
issue that is still open.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "commit-closes-keyword-issue-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_commit_closes_keyword_issue_still_open_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)


def _commit(sha: str, message: str, ts: datetime, author: str = "some-god") -> "detector.Commit":
    return detector.Commit(
        sha=sha, message=message, ts=ts, author=author,
        url=f"https://github.com/example/example-repo/commit/{sha}",
    )


def _issue(number: int, state: str = "open", closed_at: datetime | None = None) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state, closed_at=closed_at,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClosingRefs:
    @pytest.mark.parametrize(
        "message,expected",
        [
            ("Fixes #801", [801]),
            ("closes #802: draft-back now handles an empty inbox", [802]),
            ("Resolved #803", [803]),
            ("fixed #12", [12]),
            ("closed #13", [13]),
            ("resolves #14", [14]),
        ],
    )
    def test_recognized_keyword_forms(self, message, expected):
        assert detector._closing_refs(message) == expected

    def test_present_participle_never_matches(self):
        # Iron Rule #8's own prescribed safe phrasing -- proven safe here,
        # not just recommended.
        assert detector._closing_refs("closing #801 as a worked example, not a live command") == []

    def test_bare_mention_never_matches(self):
        assert detector._closing_refs("Touches #804 while investigating, no promise made") == []

    def test_multiple_refs_in_one_message_are_all_returned_deduplicated(self):
        assert detector._closing_refs("fixes #1 and closes #2, also fixes #1 again") == [1, 2]


class TestComputeGaps:
    def test_a_stale_promise_on_a_still_open_issue_is_surfaced_at_high_confidence(self):
        commit = _commit("a1", "Fixes #801", ts=_NOW - timedelta(hours=31))
        issue = _issue(801)

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-closes-keyword-issue-still-open-a1-801"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_promise_on_a_still_open_issue_is_surfaced_at_low_confidence(self):
        commit = _commit("b2", "closes #802", ts=_NOW - timedelta(hours=6))
        issue = _issue(802)

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_promise_on_an_already_closed_issue_is_excluded_not_surfaced(self):
        commit = _commit("c3", "Resolved #803", ts=_NOW - timedelta(hours=48))
        issue = _issue(803, state="closed", closed_at=_NOW - timedelta(hours=40))

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "already-closed-c3-803"

    def test_a_commit_with_no_closing_keyword_produces_no_candidate_at_all(self):
        commit = _commit("d4", "Touches #804 while investigating, no promise made", ts=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([commit], [_issue(804)], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-d4"

    def test_a_promise_naming_a_nonexistent_issue_is_excluded_not_surfaced(self):
        # This is dangling-issue-reference's seam, not this recipe's own.
        commit = _commit("e5", "fixes #999", ts=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "nonexistent-target-e5-999"

    def test_present_participle_phrasing_is_excluded_as_no_keyword_at_all(self):
        commit = _commit("f6", "closing #801 the way the guard's docstring describes it", ts=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([commit], [_issue(801)], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-f6"

    def test_one_commit_naming_two_issues_produces_two_independent_candidates(self):
        commit = _commit("g7", "fixes #1 and closes #2", ts=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([commit], [_issue(1), _issue(2)], now=_NOW)

        assert excluded == []
        slugs = {g.slug for g in surfaced}
        assert slugs == {
            "commit-closes-keyword-issue-still-open-g7-1",
            "commit-closes-keyword-issue-still-open-g7-2",
        }


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "commit-closes-keyword-issue-still-open-a1b2c3d-801"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_promise_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "commit-closes-keyword-issue-still-open-b2c3d4e-802" in tail_slugs

    def test_the_shipped_fixture_excludes_the_already_closed_and_keywordless_and_dangling_commits(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "already-closed-c3d4e5f-803" in excluded_slugs
        assert "no-closing-keyword-d4e5f6a" in excluded_slugs
        assert "nonexistent-target-e5f6a7b-999" in excluded_slugs
        assert "no-closing-keyword-f6a7b8c" in excluded_slugs


class TestLoaders:
    """load_commits/load_issues -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_commits_parses_the_real_fixture(self):
        commits = detector.load_commits()
        assert len(commits) > 0
        assert all(isinstance(c, detector.Commit) for c in commits)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_commits_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_commits(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
