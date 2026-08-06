"""Tests for RECIPES/mention-claims-unmerged-pr/detector.py's own
detection logic -- the forty-ninth real recipe: a mortal's own X mention
of the connected account claims a PR shipped, but the named PR never
actually merged.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "mention-claims-unmerged-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_mention_claims_unmerged_pr_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)


def _mention(mid: str, text: str, created_at: datetime, author: str = "some-mortal") -> "detector.Mention":
    return detector.Mention(
        id=mid, author=author, text=text, created_at=created_at,
        url=f"https://x.com/{author}/status/{mid}",
    )


def _pull(number: int, state: str = "open", merged: bool = False) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestClaimedPrNumbers:
    def test_ships_hash_n(self):
        assert detector._claimed_pr_numbers("Ships #901 today.") == [901]

    def test_case_insensitive(self):
        assert detector._claimed_pr_numbers("MERGES #903 now.") == [903]

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        assert detector._claimed_pr_numbers("See #905 for background.") == []

    def test_multiple_claims_in_one_mention(self):
        assert detector._claimed_pr_numbers("Ships #901. Includes #902.") == [901, 902]

    def test_duplicate_claim_in_one_mention_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_pr_numbers("Ships #901 and via #901 again.") == [901, 901]


class TestComputeGaps:
    def test_a_stale_unmerged_claim_is_surfaced_at_high_confidence(self):
        mention = _mention("P-1", "Ships #901 today.", _NOW - timedelta(hours=50))
        pr = _pull(901, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([mention], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "mention-claims-unmerged-pr-P-1-901"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unmerged_claim_is_surfaced_at_low_confidence(self):
        mention = _mention("P-2", "Merges #903 now.", _NOW - timedelta(hours=4))
        pr = _pull(903, state="closed", merged=False)

        surfaced, excluded = detector.compute_gaps([mention], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_merged_claimed_pr_is_excluded_not_surfaced(self):
        mention = _mention("P-3", "Includes #902 finally.", _NOW - timedelta(hours=50))
        pr = _pull(902, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps([mention], [pr], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-P-3-902" in excluded_slugs

    def test_a_claim_naming_a_pr_that_does_not_exist_is_excluded_not_surfaced(self):
        mention = _mention("P-4", "Ships #999 today.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-P-4-999" in excluded_slugs

    def test_a_mention_with_no_claim_phrase_produces_no_candidate_at_all(self):
        mention = _mention("P-5", "Housekeeping only, see #905 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-P-5"

    def test_a_duplicate_claim_in_one_mention_produces_one_candidate_not_two(self):
        mention = _mention("P-6", "Ships #901 today and via #901 again.", _NOW - timedelta(hours=50))
        pr = _pull(901, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([mention], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "mention-claims-unmerged-pr-P-6-901"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "mention-claims-unmerged-pr-P-901-901"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "mention-claims-unmerged-pr-P-902-903" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_and_no_claim_mentions(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-P-903-902" in excluded_slugs
        assert "claimed-pr-not-found-P-904-999" in excluded_slugs
        assert "no-claim-phrase-P-905" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_901_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("mention-claims-unmerged-pr-P-901-901") == 1


class TestLoaders:
    """load_mentions/load_pulls -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_mentions_parses_the_real_fixture(self):
        mentions = detector.load_mentions()
        assert len(mentions) > 0
        assert all(isinstance(m, detector.Mention) for m in mentions)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_mentions_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_mentions(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
