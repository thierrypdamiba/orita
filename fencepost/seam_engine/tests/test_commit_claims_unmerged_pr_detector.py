"""Tests for RECIPES/commit-claims-unmerged-pr/detector.py's own
detection logic -- the seventy-third real recipe: a commit's own message
claims a pull request shipped, but the PR never actually merged.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "commit-claims-unmerged-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_commit_claims_unmerged_pr_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


def _commit(sha: str, message: str, ts: datetime, author: str = "esu-elegba") -> "detector.Commit":
    return detector.Commit(
        sha=sha, message=message, url=f"https://github.com/example/example-repo/commit/{sha}",
        ts=ts, author=author,
    )


def _pull(number: int, state: str = "open", merged: bool = False) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestClaimedPrNumbersReuse:
    """This recipe reuses seam_engine.pr_claims verbatim -- these tests
    prove the import actually happened, not a second retyped copy."""

    def test_ships_hash_n(self):
        assert detector._claimed_pr_numbers("Ships #8001.") == [8001]

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        assert detector._claimed_pr_numbers("See #8002 for background.") == []


class TestComputeGaps:
    def test_a_stale_open_claim_is_surfaced_at_high_confidence(self):
        commit = _commit("aaa1111", "Ships #8001.", _NOW - timedelta(hours=50))
        pull = _pull(8001, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([commit], [pull], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-claims-unmerged-pr-aaa1111-8001"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_open_claim_is_surfaced_at_low_confidence(self):
        commit = _commit("bbb2222", "Ships #8003.", _NOW - timedelta(hours=4))
        pull = _pull(8003, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([commit], [pull], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_merged_claimed_pr_is_excluded_not_surfaced(self):
        commit = _commit("ccc3333", "Ships #8004.", _NOW - timedelta(hours=50))
        pull = _pull(8004, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps([commit], [pull], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-ccc3333-8004" in excluded_slugs

    def test_a_claim_naming_a_pr_that_does_not_exist_is_excluded_not_surfaced(self):
        commit = _commit("ddd4444", "Ships #8999.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-ddd4444-8999" in excluded_slugs

    def test_a_commit_with_no_claim_phrase_produces_no_candidate_at_all(self):
        commit = _commit("eee5555", "Housekeeping only, see #8005 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([commit], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-eee5555"

    def test_a_duplicate_claim_in_one_message_produces_one_candidate_not_two(self):
        commit = _commit(
            "fff6666", "Ships #8001 and ships #8001 again.", _NOW - timedelta(hours=50)
        )
        pull = _pull(8001, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([commit], [pull], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-claims-unmerged-pr-fff6666-8001"

    def test_a_bare_hash_mention_alongside_a_real_claim_does_not_produce_a_second_candidate(self):
        commit = _commit(
            "aaa7777", "Ships #8001. See #8999 for background.", _NOW - timedelta(hours=50)
        )
        pull = _pull(8001, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([commit], [pull], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "commit-claims-unmerged-pr-aaa7777-8001"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "commit-claims-unmerged-pr-e1f22a3-941"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "commit-claims-unmerged-pr-f2a33b4-942" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_the_dangling_claim_and_the_no_claim_commit(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-a3b44c5-943" in excluded_slugs
        assert "claimed-pr-not-found-b4c55d6-999" in excluded_slugs
        assert "no-claim-phrase-c5d66e7" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_941_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("commit-claims-unmerged-pr-e1f22a3-941") == 1

    def test_source_is_honestly_marked_fixture(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"


class TestLoaders:
    """load_commits/load_pulls -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_commits_parses_the_real_fixture(self):
        commits = detector.load_commits()
        assert len(commits) > 0
        assert all(isinstance(c, detector.Commit) for c in commits)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_commits_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_commits(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
