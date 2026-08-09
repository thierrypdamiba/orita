"""ROADMAP #161 (candidate). STRATEGY.md's metrics table sets a target for
Ogun's own true-positive tally:

    | Gap true-positive rate (self-audited) | leading | >=90% | ogun |

`audit.py`'s own module docstring already quotes STRATEGY.md's residual-risk
mitigation verbatim ("publish an honest daily true-positive tally... label
confidence on every surfaced gap") but nothing built from that docstring, or
anywhere else in the suite, ever turned around to read the ">=90%" cell and
compare it against what `audit_ledger()` actually computes from the real,
live Ledger. Tasks 116/120/158/159 built this identical
STRATEGY.md-row-vs-live-code cross-check for two sibling metrics rows
(report streak, shared reports); this is the row those tasks never reached
-- the one this module's own sibling (`audit.py`) already cites by name.

Structural extraction only, never a hand-typed second "90": the target is
read live off STRATEGY.md's own table text, and the live rate is read off
whatever `audit_ledger()` computes from the real Ledger this run, so a
future STRATEGY.md decree or a real drop in the tally is caught the same
run it happens, not claimed from memory.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from seam_engine import audit

_ROW_LABEL = "Gap true-positive rate (self-audited)"
_TARGET_PATTERN = re.compile(r">=\s*(\d+)%")

# fencepost/seam_engine/src/seam_engine/strategy_audit_target.py -> repo root
# (…/strategy_audit_target.py -> seam_engine -> src -> seam_engine -> fencepost -> repo root)
_REPO_ROOT = Path(__file__).resolve().parents[4]
STRATEGY_MD = _REPO_ROOT / "STRATEGY.md"


class StrategyTargetError(ValueError):
    """Raised when STRATEGY.md's metrics table doesn't carry a row this
    module can check -- never silently skipped."""


def strategy_true_positive_rate_target(strategy_text: str) -> int:
    """The live ">=N%" target off STRATEGY.md's own
    'Gap true-positive rate (self-audited)' row, as an int percentage."""
    for line in strategy_text.splitlines():
        if line.startswith("|") and _ROW_LABEL in line:
            m = _TARGET_PATTERN.search(line)
            if not m:
                raise StrategyTargetError(
                    f"STRATEGY.md row for {_ROW_LABEL!r} has no '>=N%' target: {line!r}"
                )
            return int(m.group(1))
    raise StrategyTargetError(f"STRATEGY.md: no metrics-table row found naming {_ROW_LABEL!r}")


def check_strategy_true_positive_target(
    strategy_path: Path | None = None, ledger_base: Path | None = None
) -> dict[str, Any]:
    """Cross-checks STRATEGY.md's live target against the real, live
    true-positive rate `audit.audit_ledger()` computes from the real
    Ledger -- never a hand-typed copy of either number."""
    path = strategy_path if strategy_path is not None else STRATEGY_MD
    text = path.read_text(encoding="utf-8")
    target_pct = strategy_true_positive_rate_target(text)

    tally = audit.audit_ledger(ledger_base)
    live_rate = tally.rate

    return {
        "strategy_target_pct": target_pct,
        "live_confirmed": tally.confirmed,
        "live_total": tally.total,
        "live_rate_pct": None if live_rate is None else round(live_rate * 100, 4),
        "meets_target": live_rate is not None and (live_rate * 100) >= target_pct,
    }
