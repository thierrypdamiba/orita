"""Tests for the recurring-gap machinery in scan.py (ROADMAP.md #19).

`_effective_since` is the one piece of arithmetic that decides how far back
`run_scan` looks for GitHub commits. Everything else in scan.py that depends
on network I/O (`fetch_github_activity`, `run_scan` itself) has no test here,
same as before this task — this file adds coverage only for the new, pure
logic, not a retroactive test of the network path.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from seam_engine.scan import _effective_since

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
README_MD = FENCEPOST_ROOT / "README.md"

NOW = datetime(2026, 7, 12, 21, 0, tzinfo=timezone.utc)


def test_effective_since_reaches_back_past_a_stale_window():
    # The account went live 40 hours ago; a 24h window would silently drop
    # the first 16 hours of it. `_effective_since` must not let that happen —
    # this is the exact bug that made "recurring" an accident of a young repo
    # rather than something the scan actually guarantees.
    account_live_since = NOW - timedelta(hours=40)
    since = _effective_since(NOW, window_hours=24, account_live_since=account_live_since)
    assert since == account_live_since


def test_effective_since_reaches_at_least_the_rolling_window_for_a_young_account():
    # The account went live only 2 hours ago — the rolling 24h window
    # reaches back further than the account's whole lifetime, so it wins
    # (harmlessly: compute_candidates still filters everything against
    # account_live_since for relevance; fetching a little extra history is
    # not a false positive).
    account_live_since = NOW - timedelta(hours=2)
    since = _effective_since(NOW, window_hours=24, account_live_since=account_live_since)
    assert since == NOW - timedelta(hours=24)
    assert since < account_live_since


def test_effective_since_reaches_back_to_an_old_account_even_with_a_wide_window():
    # An old account (400 days live) with a deliberately wide window (e.g. a
    # fork's own `window_hours=24*30`, per ONBOARDING.md/CONNECT.md) — the
    # account's own lifetime is still the older, and therefore winning, bound.
    account_live_since = NOW - timedelta(days=400)
    since = _effective_since(NOW, window_hours=24 * 30, account_live_since=account_live_since)
    assert since == account_live_since
    assert since < NOW - timedelta(hours=24 * 30)


def test_effective_since_is_a_pure_min_never_exceeds_either_bound():
    account_live_since = NOW - timedelta(hours=10)
    since = _effective_since(NOW, window_hours=24, account_live_since=account_live_since)
    assert since <= NOW - timedelta(hours=24)
    assert since <= account_live_since


def test_effective_since_at_the_boundary_is_inclusive_of_the_earlier_bound():
    account_live_since = NOW - timedelta(hours=24)
    since = _effective_since(NOW, window_hours=24, account_live_since=account_live_since)
    assert since == account_live_since == NOW - timedelta(hours=24)


# --- no drift between the two entrypoints --------------------------------------


def test_the_live_mcp_tool_reuses_the_same_recurring_gap_arithmetic():
    # server.py's `seam_scan` tool and scan.py's `run_scan` (the one the
    # daily Action runs) must never quietly disagree about how far back a
    # still-unannounced gap can recur — both call the one function.
    from seam_engine import server

    assert server._effective_since is _effective_since


def test_readme_names_the_recurring_gap_machinery():
    text = README_MD.read_text(encoding="utf-8")
    assert "_effective_since" in text

