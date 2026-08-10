"""Tests for RECIPES/commit-claims-dangling-milestone/detector.py's own
detection logic -- the seventy-sixth real recipe: a commit's own message
claims a milestone number that doesn't exist at all.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "commit-claims-dangling-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_commit_claims_dangling_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


def _commit(sha: str, message: str, ts: datetime, author: str = "esu-elegba") -> "detector.Commit":
    return detector.Commit(
        sha=sha, message=message, url=f"https://github.com/example/example-repo/commit/{sha}",
        ts=ts, author=author,
    )


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbersReuse:
    """This recipe reuses seam_engine.milestone_claims verbatim -- these
    tests prove the import actually happened, not a second retyped copy."""

    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("Milestone #9001 shipped.") == [9001]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("See #9002 for background.") == []


class TestComputeGaps:
    def test_a_claim_naming_a_milestone_that_does_not_exist_is_surfaced(self):
        commit = _commit("aaa1111", "Milestone #9001 shipped.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-claims-dangling-milestone-aaa1111-9001"
        assert surfaced[0].confidence == 0.8

    def test_confidence_is_flat_regardless_of_commit_age(self):
        fresh = _commit("bbb2222", "Milestone #9003 shipped.", _NOW - timedelta(minutes=5))
        stale = _commit("ccc3333", "Milestone #9004 shipped.", _NOW - timedelta(days=365))

        surfaced, _ = detector.compute_gaps([fresh, stale], [], now=_NOW)

        assert {g.confidence for g in surfaced} == {0.8}

    def test_a_claim_naming_a_real_open_milestone_is_excluded_not_surfaced(self):
        commit = _commit("ddd4444", "Milestone #9005 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(9005, state="open")

        surfaced, excluded = detector.compute_gaps([commit], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-ddd4444-9005" in excluded_slugs

    def test_a_claim_naming_a_real_closed_milestone_is_also_excluded(self):
        commit = _commit("eee5555", "Milestone #9006 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(9006, state="closed")

        surfaced, excluded = detector.compute_gaps([commit], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-eee5555-9006" in excluded_slugs

    def test_a_commit_with_no_claim_phrase_produces_no_candidate_at_all(self):
        commit = _commit("fff6666", "Housekeeping only, see #9007 for background.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-fff6666"

    def test_a_duplicate_claim_in_one_message_produces_one_candidate_not_two(self):
        commit = _commit(
            "aaa7777", "Milestone #9001 and milestone #9001 again.", _NOW - timedelta(hours=1)
        )

        surfaced, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-claims-dangling-milestone-aaa7777-9001"

    def test_a_bare_hash_mention_alongside_a_real_claim_does_not_produce_a_second_candidate(self):
        commit = _commit(
            "bbb8888", "Milestone #9001 shipped. See #9999 for background.", _NOW - timedelta(hours=1)
        )

        surfaced, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-claims-dangling-milestone-bbb8888-9001"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "commit-claims-dangling-milestone-e1f22a3-8302"
        assert result["primary_gap"]["confidence"] == 0.8

    def test_the_shipped_fixture_excludes_the_real_claims_and_the_no_claim_commit(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claimed-milestone-exists-f2a33b4-8301" in excluded_slugs
        assert "no-claim-phrase-a3b44c5" in excluded_slugs
        assert "claimed-milestone-exists-b4c55d6-8301" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_8302_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("commit-claims-dangling-milestone-e1f22a3-8302") == 1

    def test_source_is_honestly_marked_fixture(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"


class TestLoaders:
    """load_commits/load_milestones -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_commits_parses_the_real_fixture(self):
        commits = detector.load_commits()
        assert len(commits) > 0
        assert all(isinstance(c, detector.Commit) for c in commits)

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_commits_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_commits(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
