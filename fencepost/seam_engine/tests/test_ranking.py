"""Tests for the confidence ranking — Ogun's law, checked on iron.

Every rule the law makes has a test that fails if the rule breaks. A test that
cannot fail is a broken oath; each of these has a way to go red.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from seam_engine.ranking import (
    CONFIDENCE_BAR,
    SEPARATION_MARGIN,
    Label,
    rank,
)
from seam_engine.scan import (
    GapCandidate,
    GithubEvent,
    XPost,
    coincidence_candidates,
    compute_candidates,
)


def cand(slug: str, conf: float) -> GapCandidate:
    return GapCandidate(slug=slug, headline=f"h-{slug}", detail=f"d-{slug}", confidence=conf)


# --- election: exactly one, or none ------------------------------------------


def test_lone_high_candidate_is_primary():
    r = rank([cand("only", 0.85)])
    assert r.primary is not None
    assert r.primary.slug == "only"
    assert r.primary.label == Label.PRIMARY.value
    assert r.tail == []


def test_one_primary_over_a_pile_of_coincidences():
    r = rank([cand("gap", 0.85), cand("noise-a", 0.5), cand("noise-b", 0.45), cand("noise-c", 0.3)])
    assert r.primary.slug == "gap"
    # exactly one primary
    assert sum(1 for g in r.ranked if g.label == Label.PRIMARY.value) == 1
    # everything else is a coincidence, confidence-scored and ordered
    tail = r.tail
    assert [g.slug for g in tail] == ["noise-a", "noise-b", "noise-c"]
    assert all(g.label == Label.COINCIDENCE.value for g in tail)
    assert [g.confidence for g in tail] == sorted((g.confidence for g in tail), reverse=True)


def test_no_primary_when_top_is_below_the_bar():
    r = rank([cand("weak-a", 0.55), cand("weak-b", 0.4)])
    assert r.primary is None
    assert all(g.label == Label.COINCIDENCE.value for g in r.ranked)


def test_ambiguous_top_elects_no_primary():
    # Two look-alikes within the margin: the law refuses to guess.
    r = rank([cand("twin-a", 0.85), cand("twin-b", 0.80)])
    assert r.primary is None
    assert {g.label for g in r.ranked} == {Label.CONTENDER.value}


def test_clear_lead_over_a_bar_clearing_runner_up_still_elects():
    # #1 clears the bar and leads #2 by >= margin even though #2 also clears it.
    r = rank([cand("lead", 0.95), cand("second", 0.72)])
    assert r.primary.slug == "lead"
    assert r.ranked[1].label == Label.CONTENDER.value  # cleared bar, not elected


def test_boundary_exactly_at_bar_and_margin_elects():
    top = round(CONFIDENCE_BAR + SEPARATION_MARGIN, 4)  # lead over 2nd == margin
    r = rank([cand("edge", top), cand("below", CONFIDENCE_BAR)])
    # top == bar+margin clears the bar; lead over 2nd (== bar) is exactly margin
    assert r.primary.slug == "edge"


# --- shape and determinism ---------------------------------------------------


def test_ranks_and_leads_are_computed():
    r = rank([cand("a", 0.9), cand("b", 0.5), cand("c", 0.2)])
    assert [g.rank for g in r.ranked] == [1, 2, 3]
    assert r.ranked[0].lead == pytest.approx(0.4)  # 0.9 - 0.5
    assert r.ranked[1].lead == pytest.approx(0.3)  # 0.5 - 0.2
    assert r.ranked[2].lead == pytest.approx(0.2)  # 0.2 - 0.0 (last)


def test_ties_break_by_slug_deterministically():
    r1 = rank([cand("zeta", 0.5), cand("alpha", 0.5)])
    r2 = rank([cand("alpha", 0.5), cand("zeta", 0.5)])
    assert [g.slug for g in r1.ranked] == ["alpha", "zeta"]
    assert [g.slug for g in r2.ranked] == ["alpha", "zeta"]


def test_empty_field_has_no_primary():
    r = rank([])
    assert r.primary is None
    assert r.ranked == []


def test_ranking_carries_the_constants():
    r = rank([cand("x", 0.9)])
    assert r.confidence_bar == CONFIDENCE_BAR
    assert r.separation_margin == SEPARATION_MARGIN


# --- coincidence detector: the tail must stay under the bar -------------------


def _live() -> datetime:
    return datetime(2026, 7, 12, tzinfo=timezone.utc)


def _commit(title: str, author: str = "ogun") -> GithubEvent:
    return GithubEvent(
        kind="commit", id="deadbee", title=title, url=f"https://x/{title}",
        ts=datetime(2026, 7, 12, 6, tzinfo=timezone.utc), author=author,
    )


def test_coincidence_confidence_never_reaches_the_bar():
    # A wildly recurring topic must still score below the bar — volume is not a gap.
    events = [_commit(f"ledger recorded entry {i}") for i in range(200)]
    tail = coincidence_candidates(events, x_posts=[], account_live_since=_live())
    assert tail, "expected loud recurring topics to surface as coincidences"
    assert all(c.confidence < CONFIDENCE_BAR for c in tail)


def test_topic_on_x_is_not_a_coincidence():
    events = [_commit("lantern lantern lantern") for _ in range(10)]
    post = XPost(id="1", text="the attic lantern", url="https://x.com/p/1", ts=_live())
    tail = coincidence_candidates(events, x_posts=[post], account_live_since=_live())
    assert all("lantern" not in c.slug for c in tail)  # it reached X — no seam


def test_milestone_topic_does_not_leak_into_the_tail():
    events = [_commit("fencepost strategy work") for _ in range(10)]
    tail = coincidence_candidates(events, x_posts=[], account_live_since=_live())
    # milestone words feed the primary gap, never the coincidence tail
    assert all("fencepost" not in c.slug and "strategy" not in c.slug for c in tail)


def test_full_pipeline_emits_one_primary_over_a_scored_tail():
    # A milestone commit cluster (the gap) plus loud routine topics (the tail).
    events = [_commit(f"fencepost flagship step {i}") for i in range(4)]
    events += [_commit(f"ledger recorded sealed {i}") for i in range(20)]
    surfaced, _ = compute_candidates(events, x_posts=[], account_live_since=_live())
    coincidences = coincidence_candidates(events, x_posts=[], account_live_since=_live())
    r = rank(surfaced + coincidences)

    assert r.primary is not None
    assert r.primary.slug == "milestone-unannounced"
    assert r.primary.confidence >= CONFIDENCE_BAR
    assert r.tail, "the scan must emit a confidence-scored tail"
    assert all(g.confidence < r.primary.confidence for g in r.tail)
    assert all(g.label == Label.COINCIDENCE.value for g in r.tail)
