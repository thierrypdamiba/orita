"""Confidence ranking for the seam-scan.

One law, cast as numbers: a gap ships only when it clears the bar AND stands
clearly above the pile. Everything else is a coincidence — shown, never claimed.

This is Ogun's law made executable. False positives are fatal, so the engine
would rather name nothing than guess between two look-alikes. Volume is not a
gap. A commit topic that recurs twenty-six times and never reaches X is loud,
not important. Salience is a gap: milestone-class work that stays silent.

Pure and deterministic. No I/O. Ranking is a function of the candidates and the
two constants below — nothing else. Tie confidences break by slug so the same
input always yields the same order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from seam_engine.scan import GapCandidate

# --- The law, as numbers -----------------------------------------------------

# Below the bar, nothing is a gap. A candidate under this is a coincidence.
CONFIDENCE_BAR = 0.70

# The one gap must lead the next candidate by at least this. Two look-alikes at
# the top means the engine cannot honestly name THE gap, so it names none.
SEPARATION_MARGIN = 0.15


class Label(str, Enum):
    """What the ranker asserts about a candidate.

    PRIMARY     — the one fencepost: cleared the bar and stands clear of the pack.
    CONTENDER   — cleared the bar but was not elected (not top, or top-but-tied).
    COINCIDENCE — below the bar: surfaced only to show it was weighed and dropped.
    """

    PRIMARY = "primary"
    CONTENDER = "contender"
    COINCIDENCE = "coincidence"


@dataclass
class RankedGap:
    slug: str
    headline: str
    detail: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    label: str = Label.COINCIDENCE.value
    rank: int = 0  # 1 = strongest
    lead: float = 0.0  # confidence minus the next candidate's (0 for the last)


@dataclass
class Ranking:
    """The full ranked field, plus the two constants that produced it."""

    ranked: list[RankedGap]
    confidence_bar: float
    separation_margin: float

    @property
    def primary(self) -> RankedGap | None:
        """The single elected gap, or None when nothing cleared the law."""
        for g in self.ranked:
            if g.label == Label.PRIMARY.value:
                return g
        return None

    @property
    def tail(self) -> list[RankedGap]:
        """Every candidate that is not the primary — the confidence-scored tail."""
        return [g for g in self.ranked if g.label != Label.PRIMARY.value]


def rank(
    candidates: list[GapCandidate],
    *,
    bar: float = CONFIDENCE_BAR,
    margin: float = SEPARATION_MARGIN,
) -> Ranking:
    """Order candidates by confidence, label exactly-one-or-none PRIMARY.

    Rules, in order:
    1. Sort by confidence descending; break ties by slug (deterministic).
    2. Anything at or above `bar` is a CONTENDER; anything below is COINCIDENCE.
    3. Elect the top candidate to PRIMARY only if it clears `bar` AND leads the
       runner-up by at least `margin`. Otherwise no PRIMARY is elected — the
       field is ambiguous or weak, and Ogun's law forbids crying wolf.
    """
    ordered = sorted(candidates, key=lambda g: (-g.confidence, g.slug))

    ranked: list[RankedGap] = []
    for i, g in enumerate(ordered):
        nxt = ordered[i + 1].confidence if i + 1 < len(ordered) else 0.0
        label = Label.CONTENDER if g.confidence >= bar else Label.COINCIDENCE
        ranked.append(
            RankedGap(
                slug=g.slug,
                headline=g.headline,
                detail=g.detail,
                confidence=g.confidence,
                evidence=list(g.evidence),
                label=label.value,
                rank=i + 1,
                lead=round(g.confidence - nxt, 4),
            )
        )

    if ranked and ranked[0].confidence >= bar and ranked[0].lead >= margin:
        ranked[0].label = Label.PRIMARY.value

    return Ranking(ranked=ranked, confidence_bar=bar, separation_margin=margin)
