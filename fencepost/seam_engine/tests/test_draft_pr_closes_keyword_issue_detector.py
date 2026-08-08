"""Tests for RECIPES/draft-pr-closes-keyword-issue/detector.py's own
detection logic -- the sixty-fifth real recipe: a pull request's own body
already claims a closing keyword, while the pull request itself is still
marked a draft.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "draft-pr-closes-keyword-issue" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_draft_pr_closes_keyword_issue_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


def _pr(
    number: int,
    *,
    state: str = "open",
    draft: bool = True,
    body: str | None = "Closes #501.",
    updated_at: datetime | None = None,
) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, draft=draft, body=body,
        updated_at=updated_at or _NOW,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestLoadPullRequests:
    def test_loads_the_real_fixture_without_error(self):
        prs = detector.load_pull_requests()
        assert len(prs) == 9
        numbers = {p.number for p in prs}
        assert numbers == {2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009}

    def test_parses_fields_correctly_for_one_row(self):
        prs = detector.load_pull_requests()
        by_number = {p.number: p for p in prs}
        pr = by_number[2001]
        assert pr.title == "Rework the retry backoff so it caps on the third attempt"
        assert pr.state == "open"
        assert pr.draft is True
        assert pr.body == "Closes #501 once the retry backoff test is green."
        assert pr.updated_at == datetime(2026, 7, 29, 9, 0, 0, tzinfo=timezone.utc)

    def test_a_null_body_parses_as_none(self):
        prs = detector.load_pull_requests()
        by_number = {p.number: p for p in prs}
        assert by_number[2005].body is None

    def test_rejects_a_non_list_payload(self, tmp_path):
        bad = tmp_path / "pull_requests.json"
        bad.write_text(json.dumps({"not": "a list"}))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pull_requests(bad)


class TestComputeGapsSurfaced:
    def test_a_stale_draft_with_closing_keyword_is_surfaced_at_high_confidence(self):
        pr = _pr(2001, updated_at=_NOW - timedelta(hours=243))

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "draft-pr-closes-keyword-issue-2001"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [pr.url]
        assert "#501" in surfaced[0].detail
        assert "draft=True" in surfaced[0].detail

    def test_a_recently_touched_draft_with_closing_keyword_is_surfaced_at_low_confidence(self):
        pr = _pr(2002, body="Fixes #502.", updated_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_exactly_at_the_24h_boundary_scores_high_confidence(self):
        pr = _pr(2101, updated_at=_NOW - timedelta(hours=24))

        surfaced, _ = detector.compute_gaps([pr], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_just_under_the_24h_boundary_scores_low_confidence(self):
        pr = _pr(2102, updated_at=_NOW - timedelta(hours=23, minutes=59))

        surfaced, _ = detector.compute_gaps([pr], now=_NOW)

        assert surfaced[0].confidence == 0.5

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        fresh = _pr(2201, updated_at=_NOW - timedelta(hours=1))
        stale = _pr(2202, updated_at=_NOW - timedelta(hours=300))

        surfaced, _ = detector.compute_gaps([fresh, stale], now=_NOW)

        assert [g.slug for g in surfaced] == [
            "draft-pr-closes-keyword-issue-2202",
            "draft-pr-closes-keyword-issue-2201",
        ]

    def test_multiple_qualifying_prs_each_get_their_own_candidate(self):
        a = _pr(2301, updated_at=_NOW - timedelta(hours=100))
        b = _pr(2302, updated_at=_NOW - timedelta(hours=100))

        surfaced, _ = detector.compute_gaps([a, b], now=_NOW)

        assert {g.slug for g in surfaced} == {
            "draft-pr-closes-keyword-issue-2301",
            "draft-pr-closes-keyword-issue-2302",
        }

    def test_past_tense_closing_keyword_is_recognized_too(self):
        pr = _pr(2303, body="closed #501", updated_at=_NOW - timedelta(hours=100))

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1


class TestComputeGapsExcluded:
    def test_non_draft_pr_is_excluded(self):
        pr = _pr(2501, draft=False)

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-draft-2501"
        assert excluded[0].confidence == 0.0

    def test_draft_with_no_closing_keyword_is_excluded(self):
        pr = _pr(2502, body="WIP -- nothing wired up yet.")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-2502"

    def test_draft_with_null_body_is_excluded(self):
        pr = _pr(2503, body=None)

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-2503"

    def test_draft_with_a_bare_mention_not_a_closing_keyword_is_excluded(self):
        pr = _pr(2504, body="Related to #506, still scoping the approach.")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-2504"

    def test_draft_closed_without_merging_is_excluded(self):
        pr = _pr(2505, state="closed")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "already-closed-2505"

    def test_malformed_draft_merged_combination_is_excluded_and_named_malformed(self):
        pr = _pr(2506, state="merged")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "malformed-merged-draft-2506"
        assert "malformed" in excluded[0].detail.lower()

    def test_not_draft_takes_priority_over_keyword_check_even_when_closed(self):
        pr = _pr(2507, draft=False, state="closed", body="No keyword here.")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "not-draft-2507"

    def test_no_keyword_check_runs_before_merged_state_check(self):
        # A draft PR with no closing keyword at all is excluded on its own
        # grounds regardless of state -- named precisely, not folded into
        # the malformed-merged-draft bucket just because state happens to
        # read "merged" too.
        pr = _pr(2508, state="merged", body="WIP, nothing to close.")

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-2508"


class TestComputeGapsMixedFixture:
    def test_the_real_fixture_elects_2001_as_primary(self):
        prs = detector.load_pull_requests()

        surfaced, excluded = detector.compute_gaps(prs, now=_NOW)

        assert [g.slug for g in surfaced] == [
            "draft-pr-closes-keyword-issue-2001",
            "draft-pr-closes-keyword-issue-2002",
        ]
        assert surfaced[0].confidence == 0.85
        assert surfaced[1].confidence == 0.5

    def test_the_real_fixture_excludes_every_non_qualifying_pr_named_not_hidden(self):
        prs = detector.load_pull_requests()

        _, excluded = detector.compute_gaps(prs, now=_NOW)

        excluded_slugs = {g.slug for g in excluded}
        assert excluded_slugs == {
            "not-draft-2003",
            "no-closing-keyword-2004",
            "no-closing-keyword-2005",
            "no-closing-keyword-2006",
            "already-closed-2007",
            "malformed-merged-draft-2008",
            "not-draft-2009",
        }
        assert all(g.confidence == 0.0 for g in excluded)

    def test_the_real_fixture_surfaces_no_more_and_no_fewer_than_two(self):
        prs = detector.load_pull_requests()
        surfaced, _ = detector.compute_gaps(prs, now=_NOW)
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

    def test_primary_gap_is_pr_2001(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"]["slug"] == "draft-pr-closes-keyword-issue-2001"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_tail_carries_pr_2002(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = [g["slug"] for g in result["tail"]]
        assert tail_slugs == ["draft-pr-closes-keyword-issue-2002"]

    def test_excluded_carries_all_seven_non_qualifying_prs(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert len(result["excluded"]) == 7

    def test_uses_the_real_wall_clock_by_default(self):
        # No `now` passed -- exercises the real datetime.now(timezone.utc)
        # branch, the same "manual demo drifts with real time" property
        # every sibling recipe's own bare-run mode carries.
        result = detector.run_recipe_scan()
        assert result["source"] == "fixture"
        assert "generated_at" in result

    def test_accepts_an_explicit_pull_requests_path_override(self, tmp_path):
        custom = tmp_path / "pull_requests.json"
        custom.write_text(json.dumps([
            {
                "number": 9001,
                "title": "Custom fixture PR",
                "state": "open",
                "draft": True,
                "body": "Closes #9002.",
                "updated_at": "2026-08-01T00:00:00Z",
                "url": "https://github.com/example/example-repo/pull/9001",
            }
        ]))

        result = detector.run_recipe_scan(pull_requests_path=custom, now=_NOW)

        assert result["primary_gap"]["slug"] == "draft-pr-closes-keyword-issue-9001"


class TestRecipeManifest:
    """The manifest itself, checked the same way every sibling recipe's own
    test file checks its own recipe.json -- schema-valid, read-only scopes,
    fixture pointed under fixtures/, and it actually discovers cleanly
    through the real validator every PR is held to."""

    def test_recipe_json_is_valid_and_discovered_cleanly(self):
        from seam_engine.recipes import discover_recipes

        manifests = discover_recipes(FENCEPOST_ROOT)
        slugs = {m.slug for m in manifests}
        assert "draft-pr-closes-keyword-issue" in slugs

    def test_recipe_json_declares_only_already_cleared_scopes(self):
        manifest_path = (
            FENCEPOST_ROOT / "RECIPES" / "draft-pr-closes-keyword-issue" / "recipe.json"
        )
        manifest = json.loads(manifest_path.read_text())
        assert manifest["scopes"] == ["ListPullRequests"]
        assert manifest["toolkit"] == "github"
        assert manifest["fixture"] == "fixtures/draft_pr_closes_keyword_issue"
        assert manifest["entrypoint"] == "run_recipe_scan"
        assert manifest["detector_file"] == "detector.py"
