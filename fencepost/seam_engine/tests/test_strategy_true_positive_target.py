"""ROADMAP #161 (candidate). STRATEGY.md's metrics table sets Ogun's own
tally a bar to clear:

    | Gap true-positive rate (self-audited) | leading | >=90% | ogun |

`audit.py`'s own module docstring quotes STRATEGY.md's residual-risk
mitigation verbatim, but nothing in the suite ever read the ">=90%" cell
back off the live document and checked it against what `audit_ledger()`
actually computes from the real Ledger. Grepped every existing test naming
either "true-positive rate" or "90%": zero hits anywhere in tests/,
fencepost/seam_engine/tests/, or oracle/oracle_engine/tests/ before this
file. Tasks 116/120/158/159 built the identical
STRATEGY.md-row-vs-live-code shape for two sibling metrics rows; this is
the row those tasks never reached.

Same discipline as `tools/strategy_targets_check.py` (task 159): the
target is extracted structurally from STRATEGY.md's own text, never a
second hand-typed "90", and the live side is never a hand-typed "100" --
it is whatever `audit.audit_ledger()` computes from either a synthetic
fixture Ledger or the real one.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from seam_engine import audit, ledger, strategy_audit_target as sat


def _row(target_pct: str = ">=90%") -> str:
    return (
        "| metric | type | target | owner |\n"
        "|--|--|--|--|\n"
        "| Daily Fencepost Report shipped (town dogfood) | leading | 1/day, 30 of 30 days | off-by-one |\n"
        f"| Gap true-positive rate (self-audited) | leading | {target_pct} | ogun |\n"
        "| GitHub stars | lagging | 1,000 (Star Covenant, unbegged) | off-by-one |\n"
    )


def _scan(*, primary: bool = True, confidence: float = 0.85, bar: float = 0.70) -> dict:
    p = None
    if primary:
        p = {
            "slug": "milestone-unannounced",
            "headline": "h",
            "detail": "d",
            "confidence": confidence,
            "evidence": ["https://github.com/x/orita/commit/0000000"],
            "label": "primary",
        }
    return {
        "generated_at": "t",
        "repo": "x/orita",
        "window_hours": 24,
        "confidence_bar": bar,
        "separation_margin": 0.15,
        "primary_gap": p,
        "tail": [{"slug": "coincidence-a", "confidence": 0.1, "label": "coincidence"}],
        "excluded": [],
    }


def _at(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, 12, tzinfo=timezone.utc)


# --- structural extraction, proven on synthetic fixtures, not the real file ---


class TestExtractionIsStructural:
    def test_reads_the_stated_percentage(self):
        assert sat.strategy_true_positive_rate_target(_row(">=90%")) == 90

    def test_reads_a_different_percentage(self):
        assert sat.strategy_true_positive_rate_target(_row(">=75%")) == 75

    def test_tolerates_a_space_after_the_operator(self):
        assert sat.strategy_true_positive_rate_target(_row(">= 80%")) == 80

    def test_ignores_unrelated_rows_with_percent_signs(self):
        text = (
            "| metric | type | target | owner |\n"
            "|--|--|--|--|\n"
            "| Some other metric | leading | >=50% | somebody |\n"
            "| Gap true-positive rate (self-audited) | leading | >=65% | ogun |\n"
        )
        assert sat.strategy_true_positive_rate_target(text) == 65

    def test_missing_row_raises(self):
        text = (
            "| metric | type | target | owner |\n"
            "|--|--|--|--|\n"
            "| Daily Fencepost Report shipped (town dogfood) | leading | 1/day, 30 of 30 days | off-by-one |\n"
        )
        with pytest.raises(sat.StrategyTargetError):
            sat.strategy_true_positive_rate_target(text)

    def test_row_present_but_missing_the_number_bearing_phrase_raises(self):
        text = _row("some day, hopefully")
        with pytest.raises(sat.StrategyTargetError):
            sat.strategy_true_positive_rate_target(text)


# --- the real, live document, read today -----------------------------------


class TestRealStrategyDoc:
    def test_real_strategy_md_states_a_ninety_percent_bar_today(self):
        text = sat.STRATEGY_MD.read_text(encoding="utf-8")
        assert sat.strategy_true_positive_rate_target(text) == 90


# --- the live cross-check: today's real target against today's real tally ---


class TestLiveCrossCheck:
    def test_real_ledger_rate_meets_strategys_real_target_today(self):
        result = sat.check_strategy_true_positive_target()
        assert result["strategy_target_pct"] == 90
        assert result["live_total"] > 0
        assert result["live_rate_pct"] is not None
        assert result["meets_target"] is True

    def test_live_rate_matches_audit_ledger_directly(self):
        result = sat.check_strategy_true_positive_target()
        live = audit.audit_ledger()
        assert result["live_confirmed"] == live.confirmed
        assert result["live_total"] == live.total
        assert result["live_rate_pct"] == (None if live.rate is None else round(live.rate * 100, 4))

    def test_fixture_ledger_at_the_docs_own_target_meets_it(self, tmp_path: Path):
        strategy_path = tmp_path / "STRATEGY.md"
        strategy_path.write_text(_row(">=90%"), encoding="utf-8")
        ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 12), base=tmp_path)

        result = sat.check_strategy_true_positive_target(
            strategy_path=strategy_path, ledger_base=tmp_path
        )
        assert result["strategy_target_pct"] == 90
        assert result["live_rate_pct"] == 100.0
        assert result["meets_target"] is True


# --- mutation: a real drift on either side must flip the check red ---------


class TestMutationCatchesDrift:
    def test_a_thinner_real_tally_would_fail_the_docs_own_bar(self, tmp_path: Path):
        """Reconstructs the plausible future shape of a real regression: the
        Ledger picks up a false positive alongside the confirmed gaps,
        dropping the live rate below STRATEGY.md's unmoved 90% bar. Proves
        the check would have caught it, not merely that it agrees today."""
        strategy_path = tmp_path / "STRATEGY.md"
        strategy_path.write_text(_row(">=90%"), encoding="utf-8")

        ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 12), base=tmp_path)
        ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 13), base=tmp_path)
        ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 14), base=tmp_path)
        # a genuine false positive: claims to clear a 0.70 bar with 0.60 confidence
        ledger.append_scan(_scan(confidence=0.60, bar=0.70), now=_at(2026, 7, 15), base=tmp_path)

        result = sat.check_strategy_true_positive_target(
            strategy_path=strategy_path, ledger_base=tmp_path
        )
        assert result["live_rate_pct"] == 75.0
        assert result["strategy_target_pct"] == 90
        assert result["meets_target"] is False

    def test_a_drifted_future_strategy_decree_the_real_ledger_cannot_meet(self, tmp_path: Path):
        """Reconstructs a plausible future STRATEGY.md revision (this town
        has already revised metrics rows before, per task 159's own note)
        that raises the bar past what a still-perfect, all-confirmed real
        Ledger can ever satisfy -- 100% cannot clear >=101%."""
        strategy_path = tmp_path / "STRATEGY.md"
        strategy_path.write_text(_row(">=101%"), encoding="utf-8")
        ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 12), base=tmp_path)

        result = sat.check_strategy_true_positive_target(
            strategy_path=strategy_path, ledger_base=tmp_path
        )
        assert result["live_rate_pct"] == 100.0
        assert result["strategy_target_pct"] == 101
        assert result["meets_target"] is False

    def test_no_claims_yet_never_silently_passes_as_meeting_the_bar(self, tmp_path: Path):
        strategy_path = tmp_path / "STRATEGY.md"
        strategy_path.write_text(_row(">=90%"), encoding="utf-8")
        ledger.append_scan(_scan(primary=False), now=_at(2026, 7, 12), base=tmp_path)

        result = sat.check_strategy_true_positive_target(
            strategy_path=strategy_path, ledger_base=tmp_path
        )
        assert result["live_total"] == 0
        assert result["live_rate_pct"] is None
        assert result["meets_target"] is False
