"""Tests for RECIPES/release-claims-dangling-milestone/detector.py's own
detection logic -- the eighty-ninth real recipe: a GitHub release's own
body claims a milestone number that doesn't exist at all.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "release-claims-dangling-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_release_claims_dangling_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 19, 16, 0, 0, tzinfo=timezone.utc)


def _release(id_: str, body: str, *, published_at: str = "2026-07-25T09:00:00Z") -> "detector.Release":
    return detector.Release(
        id=id_, title=f"Release {id_}", tag=id_, body=body,
        published_at=datetime.fromisoformat(published_at.replace("Z", "+00:00")),
        url=f"https://github.com/example/example-repo/releases/tag/{id_}",
    )


def _milestone(number: int, *, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbersReuse:
    """This recipe reuses seam_engine.milestone_claims verbatim -- these
    tests prove the import actually happened, not a ninth retyped copy."""

    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("milestone #9901 shipped.") == [9901]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("see #9902 for background.") == []

    def test_a_negated_claim_is_never_extracted(self):
        """The shared grammar's own negation check, inherited not retyped:
        a sentence denying a milestone was hit must not read as claiming
        it was."""
        assert detector._claimed_milestone_numbers("we have not hit milestone #9903.") == []


class TestComputeGaps:
    def test_a_claim_naming_a_milestone_that_does_not_exist_is_surfaced(self):
        surfaced, excluded = detector.compute_gaps(
            [_release("rel-a", "Milestone #9901 shipped.")], [_milestone(1)], now=_NOW,
        )

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "release-claims-dangling-milestone-rel-a-9901"
        assert surfaced[0].confidence == 0.8
        assert "#9901" in surfaced[0].headline

    def test_a_claim_naming_a_real_open_milestone_is_excluded_not_surfaced(self):
        """Whether a real milestone's claim is TRUE is
        release-claims-open-milestone's own seam -- this recipe's exact
        inverse on the same surface -- not this one's."""
        surfaced, excluded = detector.compute_gaps(
            [_release("rel-a", "Milestone #4 shipped.")], [_milestone(4, state="open")], now=_NOW,
        )

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "claimed-milestone-exists-rel-a-4"
        assert excluded[0].confidence == 0.0
        assert "release-claims-open-milestone" in excluded[0].detail

    def test_a_claim_naming_a_real_closed_milestone_is_excluded_too(self):
        """The exclusion does not depend on the target's state: the seam
        is resolution, not truth."""
        surfaced, excluded = detector.compute_gaps(
            [_release("rel-a", "Milestone #4 shipped.")], [_milestone(4, state="closed")], now=_NOW,
        )

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "claimed-milestone-exists-rel-a-4"
        assert "'closed'" in excluded[0].detail

    def test_the_real_milestones_url_is_in_the_excluded_candidates_evidence(self):
        surfaced, excluded = detector.compute_gaps(
            [_release("rel-a", "Milestone #4 shipped.")], [_milestone(4)], now=_NOW,
        )

        assert excluded[0].evidence == [
            "https://github.com/example/example-repo/releases/tag/rel-a",
            "https://github.com/example/example-repo/milestone/4",
        ]

    def test_a_release_with_no_claim_phrase_is_named_as_an_exclusion(self):
        """Named, not two silent empties -- the same shape every sibling
        detector's own compute_gaps already holds for this surface."""
        surfaced, excluded = detector.compute_gaps(
            [_release("rel-a", "Housekeeping. See #9902 for background.")],
            [_milestone(1)], now=_NOW,
        )

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "no-claim-phrase-rel-a"
        assert excluded[0].confidence == 0.0

    def test_an_empty_body_is_named_as_an_exclusion_too(self):
        surfaced, excluded = detector.compute_gaps(
            [_release("rel-a", "")], [_milestone(1)], now=_NOW,
        )

        assert surfaced == []
        assert [g.slug for g in excluded] == ["no-claim-phrase-rel-a"]

    def test_the_same_claim_written_twice_in_one_release_is_deduplicated(self):
        """Two identical GapCandidates would tie each other out of rank()'s
        SEPARATION_MARGIN -- the guard every dangling-milestone sibling
        already holds."""
        surfaced, excluded = detector.compute_gaps(
            [_release("rel-a", "Milestone #9901 shipped. And again: milestone #9901 shipped.")],
            [_milestone(1)], now=_NOW,
        )

        assert len(surfaced) == 1
        assert surfaced[0].slug == "release-claims-dangling-milestone-rel-a-9901"

    def test_a_negated_claim_never_becomes_a_candidate(self):
        surfaced, excluded = detector.compute_gaps(
            [_release("rel-a", "we have not hit milestone #9903 this cycle.")],
            [_milestone(1)], now=_NOW,
        )

        assert surfaced == []
        assert [g.slug for g in excluded] == ["no-claim-phrase-rel-a"]

    def test_a_bare_hash_n_is_never_read_as_a_milestone_claim(self):
        """release-note-dangling-reference's number space, not this one's:
        a milestone lives in a separate sequence, and conflating them is
        the false positive Ogun's law calls fatal."""
        surfaced, excluded = detector.compute_gaps(
            [_release("rel-a", "The gate's own count lives in #4, which is an issue.")],
            [_milestone(1)], now=_NOW,
        )

        assert surfaced == []
        assert [g.slug for g in excluded] == ["no-claim-phrase-rel-a"]

    def test_a_real_and_a_dangling_claim_across_two_releases_split_correctly(self):
        surfaced, excluded = detector.compute_gaps(
            [
                _release("rel-a", "Milestone #4 shipped."),
                _release("rel-b", "Milestone #9901 shipped too."),
            ],
            [_milestone(4)], now=_NOW,
        )

        assert [g.slug for g in surfaced] == ["release-claims-dangling-milestone-rel-b-9901"]
        assert [g.slug for g in excluded] == ["claimed-milestone-exists-rel-a-4"]

    def test_two_distinct_dangling_claims_in_two_releases_both_surface(self):
        surfaced, _ = detector.compute_gaps(
            [
                _release("rel-a", "Milestone #9901 shipped."),
                _release("rel-b", "Milestone #9904 shipped."),
            ],
            [_milestone(1)], now=_NOW,
        )

        assert {g.slug for g in surfaced} == {
            "release-claims-dangling-milestone-rel-a-9901",
            "release-claims-dangling-milestone-rel-b-9904",
        }

    def test_an_empty_milestone_list_makes_every_claim_dangling(self):
        surfaced, excluded = detector.compute_gaps(
            [_release("rel-a", "Milestone #4 shipped.")], [], now=_NOW,
        )

        assert excluded == []
        assert [g.slug for g in surfaced] == ["release-claims-dangling-milestone-rel-a-4"]

    def test_a_surfaced_candidate_carries_only_the_releases_own_evidence_url(self):
        """There is no milestone to point at -- that is the whole seam.
        Pointing at a URL that resolves to nothing would be worse than
        pointing at nothing."""
        surfaced, _ = detector.compute_gaps(
            [_release("rel-a", "Milestone #9901 shipped.")], [_milestone(1)], now=_NOW,
        )

        assert surfaced[0].evidence == ["https://github.com/example/example-repo/releases/tag/rel-a"]

    def test_releases_are_processed_in_a_deterministic_id_order(self):
        """Sorted by id, the same deterministic-ordering discipline
        commit-claims-dangling-milestone's own compute_gaps already holds
        (there, sorted by sha) -- output order must not depend on input
        order."""
        surfaced_1, _ = detector.compute_gaps(
            [_release("rel-b", "Milestone #9904 shipped."), _release("rel-a", "Milestone #9901 shipped.")],
            [_milestone(1)], now=_NOW,
        )
        surfaced_2, _ = detector.compute_gaps(
            [_release("rel-a", "Milestone #9901 shipped."), _release("rel-b", "Milestone #9904 shipped.")],
            [_milestone(1)], now=_NOW,
        )

        assert [g.slug for g in surfaced_1] == [g.slug for g in surfaced_2]


class TestLoaders:
    def test_load_releases_reads_the_shipped_fixture(self):
        releases = detector.load_releases()

        assert {r.id for r in releases} == {
            "rel-9101", "rel-9102", "rel-9103", "rel-9104", "rel-9105",
        }

    def test_load_milestones_reads_the_shipped_fixture(self):
        milestones = detector.load_milestones()

        assert {m.number for m in milestones} == {7, 12}

    def test_load_releases_refuses_a_non_list_payload(self, tmp_path):
        p = tmp_path / "releases.json"
        p.write_text(json.dumps({"id": "rel-a"}))

        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_releases(p)

    def test_load_milestones_refuses_a_non_list_payload(self, tmp_path):
        p = tmp_path / "milestones.json"
        p.write_text(json.dumps({"number": 1}))

        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(p)


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"]["slug"] == "release-claims-dangling-milestone-rel-9105-9401"
        assert result["primary_gap"]["confidence"] == 0.8
        assert result["tail"] == []

    def test_the_shipped_fixture_excludes_both_real_milestones(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert {g["slug"] for g in result["excluded"]} == {
            "claimed-milestone-exists-rel-9101-7",
            "claimed-milestone-exists-rel-9102-12",
            "no-claim-phrase-rel-9103",
            "no-claim-phrase-rel-9104",
        }

    def test_the_shipped_fixtures_repeated_claim_is_deduplicated(self):
        """rel-9105 names milestone #9401 twice on purpose -- one candidate
        must come back, not two tied ones."""
        result = detector.run_recipe_scan(now=_NOW)

        assert result["tail"] == []
        assert result["primary_gap"] is not None

    def test_the_shipped_fixtures_negated_claim_never_surfaces(self):
        result = detector.run_recipe_scan(now=_NOW)
        slugs = {g["slug"] for g in result["excluded"]}
        slugs.add(result["primary_gap"]["slug"])

        assert not any("9406" in s for s in slugs)

    def test_the_shipped_fixtures_bare_issue_reference_never_surfaces(self):
        result = detector.run_recipe_scan(now=_NOW)
        slugs = {g["slug"] for g in result["excluded"]}
        slugs.add(result["primary_gap"]["slug"])

        assert not any("9405" in s for s in slugs)

    def test_generated_at_is_the_now_it_was_handed(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["generated_at"] == _NOW.isoformat()

    def test_it_defaults_now_to_the_real_clock(self):
        result = detector.run_recipe_scan()

        assert result["generated_at"] is not None
