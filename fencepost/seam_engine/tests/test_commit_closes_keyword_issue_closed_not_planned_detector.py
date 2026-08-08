"""Tests for RECIPES/commit-closes-keyword-issue-closed-not-planned/detector.py's
own detection logic (ROADMAP.md #594) -- the sixty-second real recipe: a
commit's own closing keyword credited itself with fixing an issue whose
own record shows it closed for an unrelated reason (state_reason=not_planned,
not completed).

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
DETECTOR_PATH = (
    FENCEPOST_ROOT
    / "RECIPES"
    / "commit-closes-keyword-issue-closed-not-planned"
    / "detector.py"
)

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_commit_closes_keyword_issue_closed_not_planned_test",
    DETECTOR_PATH,
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


def _commit(sha: str, message: str, ts: datetime = _NOW) -> "detector.Commit":
    return detector.Commit(
        sha=sha, message=message, url=f"https://github.com/example/example-repo/commit/{sha}",
        ts=ts, author="off-by-one",
    )


def _issue(
    number: int,
    state: str = "closed",
    state_reason: str | None = "not_planned",
    closed_at: datetime | None = None,
) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state, state_reason=state_reason,
        closed_at=closed_at, url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClosingRefs:
    def test_fixes_hash_n(self):
        assert detector._closing_refs("Fixes #701 -- normalization bug") == [701]

    def test_closes_hash_n_lowercase(self):
        assert detector._closing_refs("closes #702: flaky login redirect") == [702]

    def test_resolved_past_tense(self):
        assert detector._closing_refs("Resolved #703 -- pagination cursor drift") == [703]

    def test_no_keyword_returns_empty(self):
        assert detector._closing_refs("Touches #705 while investigating, no promise made") == []

    def test_present_participle_does_not_match(self):
        # "closing #N" is Iron Rule #8's own prescribed safe form, outside
        # the grammar on purpose -- the same boundary the sibling
        # still-open recipe's own test proves.
        assert detector._closing_refs("closing #701 during triage") == []

    def test_multiple_targets_in_one_message_both_extracted(self):
        assert detector._closing_refs("Fixes #710, closes #703 in the same sweep") == [710, 703]

    def test_duplicate_reference_deduplicated_first_seen_order(self):
        assert detector._closing_refs("fixes #701, and also fixes #701 again") == [701]


class TestComputeGaps:
    def test_a_stale_not_planned_closure_is_surfaced_at_high_confidence(self):
        commit = _commit("a1c701d", "Fixes #701 -- normalization bug in the retry queue")
        issue = _issue(701, closed_at=_NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-closes-keyword-issue-closed-not-planned-a1c701d-701"
        assert surfaced[0].confidence == 0.85

    def test_a_recent_not_planned_closure_is_surfaced_at_low_confidence(self):
        commit = _commit("b2c702d", "closes #702: flaky login redirect")
        issue = _issue(702, closed_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_completed_closure_is_excluded_as_working_as_intended(self):
        commit = _commit("c3c703d", "Resolved #703 -- pagination cursor drift")
        issue = _issue(703, state_reason="completed", closed_at=_NOW - timedelta(days=7))

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "closed-as-completed-c3c703d-703" in excluded_slugs

    def test_a_still_open_target_is_excluded_not_surfaced(self):
        commit = _commit("d4c704d", "fixes #704 per triage")
        issue = _issue(704, state="open", state_reason=None, closed_at=None)

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "still-open-d4c704d-704" in excluded_slugs

    def test_still_open_exclusion_names_the_sibling_recipe_not_itself(self):
        commit = _commit("d4c704d", "fixes #704 per triage")
        issue = _issue(704, state="open", state_reason=None, closed_at=None)

        _, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        candidate = next(g for g in excluded if g.slug == "still-open-d4c704d-704")
        assert "commit-closes-keyword-issue-still-open" in candidate.detail

    def test_a_commit_naming_no_closing_keyword_produces_no_candidate_at_all(self):
        commit = _commit("f6c705d", "Touches #705 while investigating, no promise made here")

        surfaced, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-f6c705d"

    def test_an_unrecognized_target_is_excluded_not_surfaced(self):
        commit = _commit("e5c999d", "fixes #999 per the triage note")

        surfaced, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "nonexistent-target-e5c999d-999"

    def test_nonexistent_target_names_dangling_issue_reference_not_itself(self):
        commit = _commit("e5c999d", "fixes #999 per the triage note")

        _, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert "dangling-issue-reference" in excluded[0].detail

    def test_a_closed_issue_with_no_state_reason_is_excluded_as_unproven(self):
        commit = _commit("g7c706d", "fixes #706 -- duplicate cleanup")
        issue = _issue(706, state_reason=None, closed_at=_NOW - timedelta(days=4))

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "state-reason-missing-g7c706d-706" in excluded_slugs

    def test_a_not_planned_closure_with_no_timestamp_is_excluded_as_malformed(self):
        commit = _commit("h8c707d", "closes #707 -- retry logic")
        issue = _issue(707, state_reason="not_planned", closed_at=None)

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert surfaced == []
        by_slug = {g.slug: g for g in excluded}
        candidate = by_slug["no-closed-timestamp-h8c707d-707"]
        assert "malformed" in candidate.detail

    def test_an_unrecognized_state_reason_is_excluded_not_guessed(self):
        commit = _commit("k2c709d", "fixes #709 -- retry the release pipeline")
        issue = _issue(709, state_reason="duplicate", closed_at=_NOW - timedelta(days=3))

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "state-reason-unrecognized-k2c709d-709" in excluded_slugs

    def test_unrecognized_state_reason_detail_names_the_value(self):
        commit = _commit("k2c709d", "fixes #709 -- retry the release pipeline")
        issue = _issue(709, state_reason="duplicate", closed_at=_NOW - timedelta(days=3))

        _, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        candidate = next(g for g in excluded if g.slug == "state-reason-unrecognized-k2c709d-709")
        assert "duplicate" in candidate.detail

    def test_a_commit_naming_two_targets_produces_two_independent_candidates(self):
        commit = _commit("j1c708d", "Fixes #710, closes #703 in the same sweep")
        target_710 = _issue(710, state_reason="not_planned", closed_at=_NOW - timedelta(hours=3))
        target_703 = _issue(703, state_reason="completed", closed_at=_NOW - timedelta(days=7))

        surfaced, excluded = detector.compute_gaps([commit], [target_710, target_703], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-closes-keyword-issue-closed-not-planned-j1c708d-710"
        assert surfaced[0].confidence == 0.5
        excluded_slugs = {g.slug for g in excluded}
        assert "closed-as-completed-j1c708d-703" in excluded_slugs

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        commits = [
            _commit("b2c702d", "closes #702: flaky login redirect"),
            _commit("a1c701d", "Fixes #701 -- normalization bug in the retry queue"),
        ]
        issues = [
            _issue(702, closed_at=_NOW - timedelta(hours=6)),
            _issue(701, closed_at=_NOW - timedelta(hours=50)),
        ]

        surfaced, _ = detector.compute_gaps(commits, issues, now=_NOW)

        assert [g.confidence for g in surfaced] == sorted(
            (g.confidence for g in surfaced), reverse=True
        )
        assert surfaced[0].slug == "commit-closes-keyword-issue-closed-not-planned-a1c701d-701"

    def test_exactly_24_hours_clears_the_stale_bar(self):
        commit = _commit("a1c701d", "Fixes #701 -- normalization bug in the retry queue")
        issue = _issue(701, closed_at=_NOW - timedelta(hours=24))

        surfaced, _ = detector.compute_gaps([commit], [issue], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_evidence_includes_both_commit_and_issue_urls(self):
        commit = _commit("a1c701d", "Fixes #701 -- normalization bug in the retry queue")
        issue = _issue(701, closed_at=_NOW - timedelta(hours=50))

        surfaced, _ = detector.compute_gaps([commit], [issue], now=_NOW)

        assert surfaced[0].evidence == [commit.url, issue.url]

    def test_nonexistent_target_evidence_has_only_the_commit_url(self):
        commit = _commit("e5c999d", "fixes #999 per the triage note")

        _, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert excluded[0].evidence == [commit.url]


class TestNoOverlapWithStillOpenSibling:
    """The docstring's own load-bearing claim: this recipe's surfaced set
    and commit-closes-keyword-issue-still-open's surfaced set are provably
    disjoint, since one requires state=="open" and the other requires
    state=="closed" with state_reason=="not_planned"."""

    def test_an_open_issue_never_surfaces_here_regardless_of_state_reason(self):
        commit = _commit("d4c704d", "fixes #704 per triage")
        # An open issue with a state_reason at all would be a malformed
        # GitHub record (state_reason only applies once closed), but even
        # so this recipe must never surface it -- state alone gates entry.
        issue = _issue(704, state="open", state_reason="not_planned", closed_at=None)

        surfaced, excluded = detector.compute_gaps([commit], [issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "still-open-d4c704d-704"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "commit-closes-keyword-issue-closed-not-planned-a1c701d-701"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recent_closures_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "commit-closes-keyword-issue-closed-not-planned-b2c702d-702" in tail_slugs
        assert "commit-closes-keyword-issue-closed-not-planned-j1c708d-710" in tail_slugs

    def test_the_shipped_fixture_excludes_every_named_branch(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "closed-as-completed-c3c703d-703" in excluded_slugs
        assert "still-open-d4c704d-704" in excluded_slugs
        assert "nonexistent-target-e5c999d-999" in excluded_slugs
        assert "no-closing-keyword-f6c705d" in excluded_slugs
        assert "no-closing-keyword-i9c701d" in excluded_slugs
        assert "state-reason-missing-g7c706d-706" in excluded_slugs
        assert "no-closed-timestamp-h8c707d-707" in excluded_slugs
        assert "state-reason-unrecognized-k2c709d-709" in excluded_slugs
        assert "closed-as-completed-j1c708d-703" in excluded_slugs

    def test_the_shipped_fixture_produces_the_expected_excluded_count(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert len(result["excluded"]) == 9

    def test_source_is_marked_fixture(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"


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

    def test_load_issues_reads_the_real_state_reason_field(self):
        issues = detector.load_issues()
        by_number = {i.number: i for i in issues}
        assert by_number[701].state_reason == "not_planned"
        assert by_number[703].state_reason == "completed"
        assert by_number[706].state_reason is None

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
