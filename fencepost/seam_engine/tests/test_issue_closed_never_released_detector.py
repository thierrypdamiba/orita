"""Tests for RECIPES/issue-closed-never-released/detector.py's own
detection logic (ROADMAP.md #386) -- the seventeenth real recipe: an issue
closed long ago, but no release has ever claimed it. The issue-side twin
of merged-pr-never-released (task 381) and milestone-closed-never-released
(task 383): those recipes watch a merged PR's / a closed milestone's own
SILENCE across every release read so far; this one watches the identical
silence against a closed issue, reusing release-claims-unfixed-issue's
(task 382) own real closing-keyword grammar rather than inventing a fourth
claim phrase.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-closed-never-released" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_closed_never_released_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _issue(
    number: int,
    state: str = "closed",
    closed_at: datetime | None = None,
) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        closed_at=closed_at,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


def _release(tag: str, body: str, published_at: datetime | None = None) -> "detector.Release":
    return detector.Release(
        id=f"rel-{tag}", title=tag, tag=tag, body=body,
        published_at=published_at or _NOW,
        url=f"https://github.com/example/example-repo/releases/tag/{tag}",
    )


class TestComputeGaps:
    def test_a_stale_uncredited_close_is_surfaced_at_high_confidence(self):
        issue = _issue(4001, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-closed-never-released-4001"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_issue_is_surfaced_at_low_confidence(self):
        issue = _issue(4002, closed_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_close_exactly_at_the_stale_bar_is_high_confidence(self):
        issue = _issue(4003, closed_at=_NOW - timedelta(hours=96))

        surfaced, _ = detector.compute_gaps([issue], [], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_an_issue_claimed_by_a_release_is_excluded_not_surfaced(self):
        issue = _issue(4004, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v1.0.0", "Fixes #4004 and nothing else.")

        surfaced, excluded = detector.compute_gaps([issue], [release], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "issue-claimed-4004"

    def test_an_issue_claimed_by_an_older_release_not_just_the_newest_is_excluded(self):
        # An issue credited by a PAST release, not the most recent one
        # read -- proves the check scans every release read so far, not
        # only the latest `GetLatestRelease` snapshot.
        issue = _issue(4005, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        old_release = _release("v0.9.0", "Closes #4005.", published_at=datetime(2026, 7, 21, 0, 0, 0, tzinfo=timezone.utc))
        newest_release = _release("v1.1.0", "A quiet patch release, no claims.", published_at=_NOW)

        surfaced, excluded = detector.compute_gaps([issue], [old_release, newest_release], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "issue-claimed-4005"

    def test_a_still_open_issue_is_excluded_not_surfaced(self):
        issue = _issue(4006, state="open", closed_at=None)

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "issue-not-closed-4006"

    def test_a_release_claiming_an_unrelated_issue_number_does_not_clear_the_real_one(self):
        issue = _issue(4007, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v2.0.0", "Fixes #9999, unrelated to this fixture.")

        surfaced, excluded = detector.compute_gaps([issue], [release], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-closed-never-released-4007"

    def test_a_bare_hash_mention_with_no_closing_keyword_does_not_clear_it(self):
        # "see #N for background" is not a credit claim -- the real
        # GitHub closing-keyword grammar requires fixes/closes/resolves.
        issue = _issue(4008, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v2.0.1", "See #4008 for background context.")

        surfaced, excluded = detector.compute_gaps([issue], [release], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-closed-never-released-4008"

    def test_the_claim_phrase_is_case_insensitive(self):
        issue = _issue(4009, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v2.0.2", "RESOLVES #4009 for good.")

        surfaced, excluded = detector.compute_gaps([issue], [release], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "issue-claimed-4009"

    def test_present_participle_closing_does_not_match(self):
        # Iron Rule #8's prescribed safe phrasing -- "closing #N" must
        # never itself be read as a credit claim by this recipe either.
        issue = _issue(4010, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        release = _release("v2.0.3", "Discusses closing #4010 as a worked example, not a real claim.")

        surfaced, excluded = detector.compute_gaps([issue], [release], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-closed-never-released-4010"


class TestClosedIssueWithNoTimestampIsNotMislabeledStillOpen:
    """ROADMAP.md #433: `issue.state != "closed" or issue.closed_at is
    None` folded two different facts into one `issue-not-closed-...` slug:
    a genuinely still-open issue, and an issue that reads state=closed but
    carries no closed_at (a malformed record) -- whose own detail line
    ("reads state={state}") would print "reads state=closed" underneath a
    headline claiming "is still open," a direct self-contradiction. Split
    so the malformed case gets its own honest slug."""

    def test_a_closed_issue_with_no_timestamp_is_excluded_as_malformed_not_still_open(self):
        issue = _issue(730, state="closed", closed_at=None)

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        candidate = excluded[0]
        assert candidate.slug == "issue-closed-no-timestamp-730"
        assert "is still open" not in candidate.headline
        assert "malformed" in candidate.detail
        assert candidate.evidence == [issue.url]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-closed-never-released-5002"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recent_close_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-closed-never-released-5003" in tail_slugs

    def test_the_shipped_fixture_excludes_the_claimed_and_open_issues(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "issue-claimed-5001" in excluded_slugs
        assert "issue-not-closed-5004" in excluded_slugs

    def test_the_shipped_fixture_never_considers_5001_5004_as_candidates(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-5001" in s or "-5004" in s for s in all_slugs)


class TestLoaders:
    """load_issues/load_releases -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    def test_load_releases_parses_the_real_fixture(self):
        releases = detector.load_releases()
        assert len(releases) > 0
        assert all(isinstance(r, detector.Release) for r in releases)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_releases_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_releases(bad_file)
