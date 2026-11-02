"""Tests for `margin_law.clears_margin` — Ogun's own extracted law, on its
own, at its own module boundary.

Task 902 pulled this one function out of `ranking.py` into its own file so
`audit.py` could share the exact corrected law (10-place rounding, not the
pre-fix 4-place shape) without inheriting `ranking.py`'s `httpx` dependency
transitively. Both `test_ranking.py` (`test_election_ignores_the_rounded_
display_lead_at_the_margin_boundary`, `test_true_margin_lead_with_float_
underflow_still_elects`) and `test_audit.py`
(`test_a_hairline_sub_margin_lead_stays_false_not_rounded_into_confirmed`)
already exercise this exact function end-to-end, through `rank()` and
`audit_ledger()` — but neither calls `clears_margin` directly, and no test
file has ever named `margin_law` itself. A module that embodies "false
positives are fatal" (STRATEGY.md's non-negotiable #3, Ogun's standing law)
deserves its own direct boundary test, not just incidental coverage through
two different callers' integration tests. If a future edit to this module
ever breaks the float-rounding boundary it exists to get right, this file
is the one that should go red first, at the smallest possible radius.
"""
from __future__ import annotations

from seam_engine.margin_law import MARGIN_DECISION_PLACES, clears_margin


def test_margin_decision_places_is_ten():
    # The module docstring's whole derivation (fine enough to erase float
    # noise, coarse enough to never round across a real 2-dp boundary)
    # depends on this constant staying 10. Pin it directly so a change
    # here is deliberate, not accidental.
    assert MARGIN_DECISION_PLACES == 10


def test_exact_equality_clears():
    # A lead exactly equal to the margin clears it -- "at least," not
    # "strictly more than."
    assert clears_margin(0.15, 0.15) is True


def test_real_lead_above_margin_clears():
    assert clears_margin(0.20, 0.15) is True


def test_real_lead_below_margin_does_not_clear():
    # A genuine, non-noise shortfall -- not a floating-point artifact.
    # 10-place rounding must not paper over a real 0.01 gap.
    assert clears_margin(0.14, 0.15) is False


def test_ieee754_dust_above_margin_still_clears():
    # The exact scenario `test_ranking.py`'s
    # test_true_margin_lead_with_float_underflow_still_elects covers
    # end-to-end: 0.95 - 0.80 underflows to something fractionally below
    # 0.15 in raw IEEE-754 (e.g. 0.14999999999999991), not a real
    # shortfall. 10-place rounding must clean that dust away.
    exact_lead = 0.95 - 0.80
    assert exact_lead < 0.15  # confirm the raw float really does underflow
    assert clears_margin(exact_lead, 0.15) is True


def test_display_rounded_boundary_trap_stays_false():
    # The exact scenario task 895/902 both exist to fix, and
    # test_audit.py's test_a_hairline_sub_margin_lead_stays_false_not_
    # rounded_into_confirmed names directly: a true lead of 0.14996 is
    # genuinely below the 0.15 margin, but `round(lead, 4)` -- the pre-fix
    # shape -- rounds it UP to exactly 0.1500, which would wrongly clear
    # the margin. At 10 places, 0.14996 stays 0.14996 and correctly fails.
    exact_lead = 0.94996 - 0.8
    assert round(exact_lead, 4) == 0.15  # the display-rounded trap exists
    assert clears_margin(exact_lead, 0.15) is False  # but the real law refuses it


def test_negative_lead_never_clears():
    # The runner-up actually leads -- never a cleared margin, regardless
    # of how large |exact_lead| is.
    assert clears_margin(-0.10, 0.15) is False


def test_zero_margin_any_nonnegative_lead_clears():
    # A margin of zero is a degenerate but legal input -- any lead at or
    # above zero clears it.
    assert clears_margin(0.0, 0.0) is True
    assert clears_margin(0.0001, 0.0) is True


def test_zero_lead_against_positive_margin_does_not_clear():
    assert clears_margin(0.0, 0.15) is False
