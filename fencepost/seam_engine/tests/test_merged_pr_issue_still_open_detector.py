"""Tests for RECIPES/merged-pr-issue-still-open/detector.py's own detection
logic (ROADMAP.md #183) -- no test file exercised `compute_gaps`/
`_closed_issue_numbers` directly before this one; test_recipes.py only
validates the recipe manifest schema, never the business logic beneath it.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "merged-pr-issue-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_merged_pr_issue_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)


def _pull(body: str, merged_at: datetime = datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc)) -> "detector.MergedPull":
    return detector.MergedPull(
        id="PR-1", title="Some fix", number=100, body=body, merged_at=merged_at,
        url="https://github.com/example/example-repo/pull/100",
    )


def _issue(number: int, state: str) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClosedIssueNumbers:
    def test_a_single_closing_keyword_returns_one_number(self):
        assert detector._closed_issue_numbers("Closes #55") == [55]

    def test_two_closing_keywords_return_both_numbers(self):
        assert detector._closed_issue_numbers("This closes #1 and fixes #2") == [1, 2]

    def test_no_closing_keyword_returns_an_empty_list(self):
        assert detector._closed_issue_numbers("No linked issue, docs only.") == []

    def test_the_bare_word_fix_is_matched_not_just_fixes(self):
        # Regression: `fixes?` (the pre-427 pattern) only ever matched
        # `fixe`/`fixes`, never the bare word `fix` -- an asymmetry with
        # `closes?`/`resolves?`, which both correctly span their bare and
        # `s`-suffixed forms. "Fix #N" is one of GitHub's own documented
        # closing-keyword forms and a common way to write it.
        assert detector._closed_issue_numbers("Fix #56.") == [56]

    def test_the_same_number_named_twice_is_deduplicated(self):
        # ROADMAP.md #444: a body naming the same issue via two different
        # closing-keyword forms ("Closes #5 and also fixes #5") used to
        # return [5, 5] -- reproduced live against the pre-fix code before
        # writing this test. `commit-closes-keyword-issue-still-open`'s
        # `_closing_refs` already dedupes this exact shape; this recipe's
        # own hand-rolled extractor did not.
        assert detector._closed_issue_numbers("Closes #5 and also fixes #5") == [5]

    def test_past_tense_closed_is_matched(self):
        # ROADMAP.md #543: this recipe's own `_CLOSES_RE` used to be a
        # private, present-tense-only copy of GitHub's closing-keyword
        # grammar (`closes?|fix(?:es)?|resolves?`) -- "closed #42" (a real,
        # common way to phrase a merged PR's own promise) never matched at
        # all. Reproduced live against the pre-fix code before writing this
        # test: the old `_CLOSES_RE` returned `[]` on this exact string.
        # Now imports `seam_engine.closing_keywords.CLOSING_KEYWORD_RE`,
        # which task 184's own live incident already proved matches past
        # tense.
        assert detector._closed_issue_numbers("This PR closed #42.") == [42]

    def test_past_tense_fixed_and_resolved_are_matched(self):
        assert detector._closed_issue_numbers("Fixed #1, resolved #2.") == [1, 2]


class TestComputeGapsMultiIssuePr:
    def test_a_pr_naming_two_closing_keywords_still_flags_the_one_left_open(self):
        # Issue #1 is already closed; issue #2 is still open and stale
        # (well past _STALE_HOURS). Before the fix, `_closed_issue_number`'s
        # `.search()` only ever saw #1, so the PR was excluded as
        # "already closed" and #2's real, still-open gap was never surfaced
        # at all -- reproduced live against the pre-fix code before writing
        # this test.
        pr = _pull("This closes #1 and fixes #2", merged_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc))
        issues = [_issue(1, "closed"), _issue(2, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        surfaced_slugs = {g.slug for g in surfaced}
        excluded_slugs = {g.slug for g in excluded}
        assert "merged-pr-issue-still-open-100-2" in surfaced_slugs
        assert "issue-already-closed-100-1" in excluded_slugs
        assert not any("2" in s and "closed" in s for s in excluded_slugs)

    def test_both_issues_open_and_stale_surfaces_both_as_distinct_candidates(self):
        pr = _pull("Closes #1 and fixes #2", merged_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc))
        issues = [_issue(1, "open"), _issue(2, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert excluded == []
        surfaced_slugs = sorted(g.slug for g in surfaced)
        assert surfaced_slugs == ["merged-pr-issue-still-open-100-1", "merged-pr-issue-still-open-100-2"]

    def test_single_issue_pr_behavior_is_unchanged(self):
        pr = _pull("Closes #55", merged_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc))
        issues = [_issue(55, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-issue-still-open-100-55"

    def test_a_number_named_twice_no_longer_ties_rank_out_of_a_primary(self):
        # ROADMAP.md #444: before the dedup fix, "Closes #5 and also fixes
        # #5" produced two identically-slugged, identically-scored
        # GapCandidates; rank()'s SEPARATION_MARGIN saw a 0.0 lead and
        # refused to elect a primary on a real, single gap. Reproduced live
        # (primary came back None) before writing this test.
        from seam_engine.ranking import rank

        pr = _pull("Closes #5 and also fixes #5", merged_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc))
        issues = [_issue(5, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)
        assert len(surfaced) == 1

        ranking = rank(surfaced)
        assert ranking.primary is not None
        assert ranking.primary.slug == "merged-pr-issue-still-open-100-5"

    def test_a_past_tense_only_promise_is_still_surfaced_as_a_gap(self):
        # ROADMAP.md #543: the real end-to-end case the past-tense fix
        # protects -- a PR whose body ONLY ever phrases its promise in past
        # tense ("This closed #42") used to fall all the way through to
        # `no-closing-keyword-100` (excluded, "no seam here") because the
        # old `_CLOSES_RE` never matched it at all. Reproduced live against
        # the pre-fix code before writing this test.
        pr = _pull("This closed #42, once the retry logic landed.", merged_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc))
        issues = [_issue(42, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-issue-still-open-100-42"


class TestNonexistentIssueIsNotMislabeledClosed:
    """ROADMAP.md #429: before this fix, `issue is None or issue.state ==
    "closed"` folded a dangling reference (the named issue was never real)
    into the same `issue-already-closed-...` slug and the same false detail
    line ("it already reads closed") as a genuinely resolved promise --
    reproduced live against the pre-fix code before writing this test. A
    dangling reference gets its own `nonexistent-target-...` slug now,
    matching the split every newer sibling in this recipe family already
    made (`merged-pr-pr-still-open/detector.py`'s own `nonexistent-target-`
    vs `already-resolved-`)."""

    def test_a_promised_issue_that_does_not_exist_is_excluded_as_nonexistent_not_closed(self):
        pr = _pull("Closes #999", merged_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc))
        issues = [_issue(1, "open")]  # #999 is never in the issue list at all

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        candidate = excluded[0]
        assert candidate.slug == "nonexistent-target-100-999"
        assert "already" not in candidate.detail
        assert "closed" not in candidate.detail
        assert candidate.evidence == [pr.url]  # no issue.url to append -- it doesn't exist

    def test_a_promised_issue_that_exists_and_is_closed_is_still_excluded_as_already_closed(self):
        # The genuinely-resolved path must survive the split unchanged.
        pr = _pull("Closes #1", merged_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc))
        issues = [_issue(1, "closed")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "issue-already-closed-100-1"
        assert excluded[0].evidence == [pr.url, issues[0].url]


class TestLoadPullsAndIssues:
    """load_pulls/load_issues (task 358) -- no test in this file called either
    loader directly before this class; test_recipes.py only proves
    discover_recipes()/load_detector() can import the module. Both crashed
    with a bare TypeError on syntactically valid but non-list JSON, reproduced
    live before the fix ({"a": 1} -> "string indices must be integers"; a
    scalar/None -> "'<type>' object is not iterable")."""

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.MergedPull) for p in pulls)

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
