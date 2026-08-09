#!/usr/bin/env python3
"""Task 159. Off-By-One counts the target STRATEGY.md sets and nobody
had checked against it.

STRATEGY.md's metrics table (lines 52/56) is the one live source both
`report_cadence_check.TARGET_STREAK_DAYS` (task 116) and
`shared_reports_check.TARGET_SHARES` (task 120) claim, in a hand-typed
inline comment, to mirror:

    TARGET_STREAK_DAYS = 30  # STRATEGY.md: "1/day, 30 of 30 days"
    TARGET_SHARES = 50  # STRATEGY.md: "50 organic links/screenshots"

Task 158 closed the identical "never checked against the live thing it
claims to mirror" shape between two CODE files -- `metrics_cadence_check.
TARGET_STREAK_DAYS` against `report_cadence_check.TARGET_STREAK_DAYS` --
but never turned around to check either constant against the DOCUMENT both
comments actually cite. Grepped every test naming either constant:
`tests/test_report_cadence_check.py` and `tests/test_shared_reports_check.
py` only ever pass each module's own constant back into itself as
`target=`, and task 158's `test_cadence_target_mirror_doctrine.py` only
ever compared the two code constants to each other. If STRATEGY.md's row
ever moves its target (a plausible future decree -- this town has already
revised metrics rows before), or either constant drifts alone, nothing
anywhere would fail. The two numbers agree today; nothing yet proves it.

This module extracts each row's target number from STRATEGY.md's own live
table text via regex -- never a second hand-typed "30"/"50" -- and cross-
checks it against the two real modules' real constants, live-loaded.

Task 421: a third row joined the same doctrine. `github_stars_check.py`
(task 420) cross-checks the last live stargazer count against
`records/metrics.jsonl`'s claim, but nothing checked either of THOSE
against STRATEGY.md's own stated target ("1,000 (Star Covenant,
unbegged)"). `strategy_github_stars_target()` extracts it the same way,
and `github_stars_check.TARGET_STARS = 1000` is the code-side constant it
mirrors -- never a second hand-typed "1000" either.

Task 428: STRATEGY.md's metrics table has six rows total; three still had
no doc-vs-code target cross-check anywhere. The gap true-positive rate row
turned out to already be covered, separately, by
`fencepost/seam_engine/src/seam_engine/strategy_audit_target.py` (task
161/410) -- a live-Ledger cross-check, not this module's job. The other
two were genuinely uncovered: `connected_users_check.py` (task 412) and
`toolkits_in_use_check.py` (task 145) each cross-check their metric's
CLAIMED `records/metrics.jsonl` reading against real ground truth, but
neither module's own TARGET constant had ever been checked against
STRATEGY.md's live text -- the identical shape this module already closed
for the other three rows, still open on these two.
`strategy_connected_users_target()`/`strategy_toolkits_target()` extract
them the same way: live text in, never a hand-typed number.
`connected_users_check.TARGET_CONNECTED_USERS = 100` and
`toolkits_in_use_check.TARGET_TOOLKITS = 5` are the code-side constants
they mirror.

Usage:
    python3 tools/strategy_targets_check.py check
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
from types import ModuleType
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRATEGY_MD = os.path.join(ROOT, "STRATEGY.md")

REPORT_STREAK_ROW_LABEL = "Daily Fencepost Report shipped (town dogfood)"
SHARED_REPORTS_ROW_LABEL = "Shared Fencepost Reports in the wild"
GITHUB_STARS_ROW_LABEL = "GitHub stars"
CONNECTED_USERS_ROW_LABEL = "OAuth completions across users"
TOOLKITS_ROW_LABEL = "Distinct read-only toolkits connected"

_STREAK_PATTERN = re.compile(r"(\d+) of \d+ days")
_SHARES_PATTERN = re.compile(r"(\d+) organic links/screenshots")
_STARS_PATTERN = re.compile(r"([\d,]+)\s*\(Star Covenant")
_CONNECTED_USERS_PATTERN = re.compile(r"(\d+) connected users in \d+ days")
_TOOLKITS_PATTERN = re.compile(r">=(\d+) toolkits in real use")


class StrategyTargetError(ValueError):
    """Raised when a named metrics-table row is missing from STRATEGY.md,
    or its target cell doesn't carry the expected number-bearing phrase --
    never silently skipped, the same fail-loud discipline `check_words`/
    `check_change_gate` already hold elsewhere in this ritual."""


def _row_line(strategy_text: str, row_label: str) -> str:
    """The single markdown table row (a line starting with `|`) that names
    `row_label` in its metric column. Raises rather than returning None so
    a renamed or deleted row is loud, not a quiet empty match."""
    for line in strategy_text.splitlines():
        if line.startswith("|") and row_label in line:
            return line
    raise StrategyTargetError(f"STRATEGY.md: no metrics-table row found naming {row_label!r}")


def strategy_report_streak_target(strategy_text: str) -> int:
    """Extracts the live "N of N days" streak target from STRATEGY.md's
    "Daily Fencepost Report shipped (town dogfood)" row."""
    line = _row_line(strategy_text, REPORT_STREAK_ROW_LABEL)
    m = _STREAK_PATTERN.search(line)
    if not m:
        raise StrategyTargetError(
            f"STRATEGY.md row for {REPORT_STREAK_ROW_LABEL!r} has no 'N of N days' target: {line!r}"
        )
    return int(m.group(1))


def strategy_shared_reports_target(strategy_text: str) -> int:
    """Extracts the live organic-share target from STRATEGY.md's "Shared
    Fencepost Reports in the wild" row."""
    line = _row_line(strategy_text, SHARED_REPORTS_ROW_LABEL)
    m = _SHARES_PATTERN.search(line)
    if not m:
        raise StrategyTargetError(
            f"STRATEGY.md row for {SHARED_REPORTS_ROW_LABEL!r} has no 'N organic links/screenshots' target: {line!r}"
        )
    return int(m.group(1))


def strategy_github_stars_target(strategy_text: str) -> int:
    """Extracts the live star-count target from STRATEGY.md's "GitHub
    stars" row, e.g. "1,000 (Star Covenant, unbegged)" -> 1000. Commas are
    stripped before parsing; the row is otherwise read exactly like its
    two siblings above -- live text in, never a hand-typed number."""
    line = _row_line(strategy_text, GITHUB_STARS_ROW_LABEL)
    m = _STARS_PATTERN.search(line)
    if not m:
        raise StrategyTargetError(
            f"STRATEGY.md row for {GITHUB_STARS_ROW_LABEL!r} has no 'N (Star Covenant' target: {line!r}"
        )
    return int(m.group(1).replace(",", ""))


def strategy_connected_users_target(strategy_text: str) -> int:
    """Extracts the live OAuth-completions target from STRATEGY.md's
    "'Connect your own' OAuth completions across users" row, e.g. "100
    connected users in 60 days" -> 100. The 60-day window is not extracted
    -- `connected_users_check.py` cross-checks a point-in-time count
    against ground truth, not a rolling 60-day rate, so only the user-count
    number has a code-side constant to mirror."""
    line = _row_line(strategy_text, CONNECTED_USERS_ROW_LABEL)
    m = _CONNECTED_USERS_PATTERN.search(line)
    if not m:
        raise StrategyTargetError(
            f"STRATEGY.md row for {CONNECTED_USERS_ROW_LABEL!r} has no "
            f"'N connected users in N days' target: {line!r}"
        )
    return int(m.group(1))


def strategy_toolkits_target(strategy_text: str) -> int:
    """Extracts the live toolkit-breadth target from STRATEGY.md's
    "Distinct read-only toolkits connected across users (Arcade breadth)"
    row, e.g. ">=5 toolkits in real use" -> 5."""
    line = _row_line(strategy_text, TOOLKITS_ROW_LABEL)
    m = _TOOLKITS_PATTERN.search(line)
    if not m:
        raise StrategyTargetError(
            f"STRATEGY.md row for {TOOLKITS_ROW_LABEL!r} has no "
            f"'>=N toolkits in real use' target: {line!r}"
        )
    return int(m.group(1))


def _load(name: str, relpath: str) -> ModuleType:
    path = os.path.join(ROOT, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load module {name!r} from {path!r}: no loader for this file type")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_strategy_targets(strategy_path: str = STRATEGY_MD) -> dict[str, Any]:
    """Cross-checks both live STRATEGY.md targets against the two real
    modules' real constants, live-loaded fresh each call -- never a hand-
    typed copy of either the doc number or the code constant."""
    with open(strategy_path, encoding="utf-8") as f:
        text = f.read()

    rcc = _load("_stc_report_cadence_check", "tools/report_cadence_check.py")
    src = _load("_stc_shared_reports_check", "tools/shared_reports_check.py")
    ghs = _load("_stc_github_stars_check", "tools/github_stars_check.py")
    cuc = _load("_stc_connected_users_check", "tools/connected_users_check.py")
    tiu = _load("_stc_toolkits_in_use_check", "tools/toolkits_in_use_check.py")

    strategy_streak = strategy_report_streak_target(text)
    strategy_shares = strategy_shared_reports_target(text)
    strategy_stars = strategy_github_stars_target(text)
    strategy_connected_users = strategy_connected_users_target(text)
    strategy_toolkits = strategy_toolkits_target(text)

    return {
        "report_streak": {
            "strategy_target": strategy_streak,
            "code_target": rcc.TARGET_STREAK_DAYS,
            "agree": strategy_streak == rcc.TARGET_STREAK_DAYS,
        },
        "shared_reports": {
            "strategy_target": strategy_shares,
            "code_target": src.TARGET_SHARES,
            "agree": strategy_shares == src.TARGET_SHARES,
        },
        "github_stars": {
            "strategy_target": strategy_stars,
            "code_target": ghs.TARGET_STARS,
            "agree": strategy_stars == ghs.TARGET_STARS,
        },
        "connected_users": {
            "strategy_target": strategy_connected_users,
            "code_target": cuc.TARGET_CONNECTED_USERS,
            "agree": strategy_connected_users == cuc.TARGET_CONNECTED_USERS,
        },
        "toolkits": {
            "strategy_target": strategy_toolkits,
            "code_target": tiu.TARGET_TOOLKITS,
            "agree": strategy_toolkits == tiu.TARGET_TOOLKITS,
        },
    }


def format_strategy_targets(result: dict[str, Any]) -> str:
    lines = []
    for key, label in (
        ("report_streak", "report cadence"),
        ("shared_reports", "shared reports"),
        ("github_stars", "github stars"),
        ("connected_users", "connected users"),
        ("toolkits", "toolkits"),
    ):
        row = result[key]
        status = "agree" if row["agree"] else "DRIFT"
        lines.append(
            f"strategy target ({label}): STRATEGY.md={row['strategy_target']} "
            f"code={row['code_target']} -- {status}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = check_strategy_targets()
    print(format_strategy_targets(out))
    sys.exit(0 if all(row["agree"] for row in out.values()) else 1)
