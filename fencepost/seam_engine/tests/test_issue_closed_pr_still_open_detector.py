"""Tests for RECIPES/issue-closed-pr-still-open/detector.py's own detection
logic (ROADMAP.md #373) -- the sixth real recipe, the mirror image of
merged-pr-issue-still-open (task 108/183): a still-OPEN PR names a closing
keyword for an issue that closed anyway, through some other route.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-closed-pr-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_closed_pr_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)


def _pull(
    body: str,
    state: str = "open",
    opened_at: datetime = datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc),
) -> "detector.OpenPull":
    return detector.OpenPull(
        id="PR-1", title="Some fix", number=100, body=body, state=state,
        opened_at=opened_at, url="https://github.com/example/example-repo/pull/100",
    )


def _issue(number: int, state: str, closed_at: datetime | None = None) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state, closed_at=closed_at,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestNamedIssueNumbers:
    def test_a_single_closing_keyword_returns_one_number(self):
        assert detector._named_issue_numbers("Closes #55") == [55]

    def test_two_closing_keywords_return_both_numbers(self):
        assert detector._named_issue_numbers("This closes #1 and fixes #2") == [1, 2]

    def test_no_closing_keyword_returns_an_empty_list(self):
        assert detector._named_issue_numbers("No linked issue, docs only.") == []

    def test_the_bare_word_fix_is_matched_not_just_fixes(self):
        # Regression: `fixes?` (the pre-427 pattern) only ever matched
        # `fixe`/`fixes`, never the bare word `fix` -- an asymmetry with
        # `closes?`/`resolves?`, which both correctly span their bare and
        # `s`-suffixed forms. "Fix #N" is one of GitHub's own documented
        # closing-keyword forms and a common way to write it.
        assert detector._named_issue_numbers("Fix #56.") == [56]

    def test_the_same_number_named_twice_is_deduplicated(self):
        # ROADMAP.md #444: a body naming the same issue via two different
        # closing-keyword forms ("Closes #5 and also fixes #5") used to
        # return [5, 5] -- reproduced live against the pre-fix code before
        # writing this test. `merged-pr-issue-still-open`'s sibling
        # extractor carried the identical gap, fixed in the same task.
        assert detector._named_issue_numbers("Closes #5 and also fixes #5") == [5]


class TestComputeGaps:
    def test_a_stale_closed_issue_is_surfaced_at_high_confidence(self):
        pr = _pull("Closes #1")
        issues = [_issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-closed-pr-still-open-100-1"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_issue_is_surfaced_at_low_confidence(self):
        pr = _pull("Fixes #1")
        issues = [_issue(1, "closed", closed_at=_NOW - timedelta(hours=4))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_still_open_named_issue_is_excluded_not_surfaced(self):
        pr = _pull("Resolves #1")
        issues = [_issue(1, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "issue-still-open-100-1"

    def test_a_pr_with_no_closing_keyword_produces_no_candidate_at_all(self):
        pr = _pull("Cosmetic only, no linked issue.")
        issues = [_issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-100"

    def test_a_merged_pr_is_never_considered_at_all(self):
        # This recipe's seam is specifically a PR that never merged (so
        # GitHub's auto-close never had a trigger). A merged PR is
        # merged-pr-issue-still-open's seam, not this one's.
        pr = _pull("Closes #1", state="merged")
        issues = [_issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_pr_naming_two_closing_keywords_judges_each_issue_independently(self):
        pr = _pull("This closes #1 and fixes #2")
        issues = [
            _issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc)),
            _issue(2, "open"),
        ]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        surfaced_slugs = {g.slug for g in surfaced}
        excluded_slugs = {g.slug for g in excluded}
        assert "issue-closed-pr-still-open-100-1" in surfaced_slugs
        assert "issue-still-open-100-2" in excluded_slugs

    def test_a_number_named_twice_no_longer_ties_rank_out_of_a_primary(self):
        # ROADMAP.md #444: before the dedup fix, "Closes #5 and also fixes
        # #5" produced two identically-slugged, identically-scored
        # GapCandidates; rank()'s SEPARATION_MARGIN saw a 0.0 lead and
        # refused to elect a primary on a real, single gap. Reproduced live
        # (primary came back None) before writing this test.
        from seam_engine.ranking import rank

        pr = _pull("Closes #5 and also fixes #5")
        issues = [_issue(5, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)
        assert len(surfaced) == 1

        ranking = rank(surfaced)
        assert ranking.primary is not None
        assert ranking.primary.slug == "issue-closed-pr-still-open-100-5"

    def test_an_unrecognized_issue_number_is_excluded_not_surfaced(self):
        pr = _pull("Closes #999")
        issues = [_issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "nonexistent-target-100-999"


class TestNonexistentIssueIsNotMislabeledStillOpen:
    """ROADMAP.md #430: a PR naming an issue number that doesn't exist at
    all used to fall into the same `issue-still-open-...` slug and "has not
    closed yet" detail as a PR naming a genuinely still-open issue -- a
    false claim, since no such issue was ever found to be open or closed."""

    def test_a_nonexistent_issue_excludes_with_its_own_slug_and_an_honest_detail(self):
        pr = _pull("Closes #100")
        issues = [_issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "nonexistent-target-100-100"
        assert "still open" not in excluded[0].detail
        assert "has not closed" not in excluded[0].detail
        assert "no such issue exists" in excluded[0].detail

    def test_a_genuinely_still_open_issue_keeps_its_own_distinct_slug(self):
        pr = _pull("Resolves #1")
        issues = [_issue(1, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "issue-still-open-100-1"
        assert "has not closed yet" in excluded[0].detail


class TestClosedIssueWithNoTimestampIsNotMislabeledStillOpen:
    """ROADMAP.md #433: `issue.state != "closed" or issue.closed_at is
    None` folded a genuinely still-open named issue and a named issue that
    reads closed but carries no closed_at (a malformed record) into the
    same `issue-still-open-...` slug and its false "has not closed yet"
    detail. Split so the malformed case gets its own honest slug."""

    def test_a_closed_named_issue_with_no_timestamp_is_excluded_as_malformed_not_still_open(self):
        pr = _pull("Closes #740")
        issue = _issue(740, "closed", closed_at=None)

        surfaced, excluded = detector.compute_gaps([pr], [issue], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        candidate = excluded[0]
        assert candidate.slug == "issue-closed-no-timestamp-100-740"
        assert "has not closed yet" not in candidate.detail
        assert "malformed" in candidate.detail
        assert candidate.evidence == [pr.url, issue.url]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-closed-pr-still-open-601-501"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_closed_issue_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-closed-pr-still-open-602-502" in tail_slugs

    def test_the_shipped_fixture_excludes_the_still_open_named_issue(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "issue-still-open-603-503" in excluded_slugs
        assert "no-closing-keyword-604" in excluded_slugs

    def test_the_shipped_fixture_excludes_the_nonexistent_named_issue(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "nonexistent-target-605-599" in excluded_slugs


class TestLoaders:
    """load_pulls/load_issues -- mirrors merged-pr-issue-still-open's own
    _load_rows guard against syntactically valid but non-list JSON (task
    358's closed campaign), applied here fresh since this is a new loader,
    not a shared one."""

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.OpenPull) for p in pulls)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
