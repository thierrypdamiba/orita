"""Tests for the recurring-gap machinery in scan.py (ROADMAP.md #19) and the
live-X-read wiring (ROADMAP.md #94).

`_effective_since` is the one piece of arithmetic that decides how far back
`run_scan` looks for GitHub commits. Everything else in scan.py that depends
on network I/O (`fetch_github_activity`, `run_scan` itself) has no test here,
same as before this task — this file adds coverage only for the new, pure
logic, not a retroactive test of the network path. `load_x_posts_from_live`
is pure (no network, no filesystem) so it IS covered here, the same way
`_effective_since` already is.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from seam_engine.scan import (
    GithubEvent,
    XPost,
    _effective_since,
    load_github_events_from_live,
    load_x_posts_from_live,
)

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


# --- load_x_posts_from_live (ROADMAP.md #94) -----------------------------------


def test_load_x_posts_from_live_parses_normalized_entries():
    data = [
        {"id": "1", "text": "hello seam", "url": "https://x.com/oritatown/status/1", "ts": "2026-07-16T12:00:00Z"},
        {"id": "2", "text": "second post", "url": "https://x.com/oritatown/status/2", "ts": "2026-07-15T09:30:00+00:00"},
    ]
    posts = load_x_posts_from_live(data)
    assert posts == [
        XPost(id="1", text="hello seam", url="https://x.com/oritatown/status/1",
              ts=datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)),
        XPost(id="2", text="second post", url="https://x.com/oritatown/status/2",
              ts=datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)),
    ]


def test_load_x_posts_from_live_matches_xpost_shape_the_ledger_reader_already_produces():
    # Same dataclass, same four fields, regardless of which reader built it —
    # compute_candidates/coincidence_candidates must never be able to tell
    # a live-sourced XPost from a ledger-sourced one.
    live = load_x_posts_from_live([
        {"id": "9", "text": "t", "url": "https://x.com/oritatown/status/9", "ts": "2026-07-16T00:00:00Z"},
    ])[0]
    hand_built = XPost(id="9", text="t", url="https://x.com/oritatown/status/9",
                        ts=datetime(2026, 7, 16, tzinfo=timezone.utc))
    assert live == hand_built


def test_load_x_posts_from_live_rejects_empty_list():
    # An empty live result is refused, not silently accepted as "posted
    # nothing, ever" — @oritatown has posted before, so an empty read is far
    # more likely to mean the call failed or was blocked (this town's own
    # X_GetUserTweets outage returns exactly this shape). Ogun's law: a
    # false "never posted" would flag every past commit as newly unannounced.
    with pytest.raises(ValueError, match="empty list"):
        load_x_posts_from_live([])


def test_load_x_posts_from_live_rejects_an_entry_missing_a_required_key():
    with pytest.raises(ValueError, match=r"entry 1.*ts"):
        load_x_posts_from_live([
            {"id": "1", "text": "ok", "url": "https://x.com/oritatown/status/1", "ts": "2026-07-16T00:00:00Z"},
            {"id": "2", "text": "missing ts", "url": "https://x.com/oritatown/status/2"},
        ])


def test_load_x_posts_from_live_rejects_multiple_missing_keys_naming_all_of_them():
    with pytest.raises(ValueError, match=r"\['text', 'url'\]"):
        load_x_posts_from_live([{"id": "1", "ts": "2026-07-16T00:00:00Z"}])


# --- the CLI's --x-posts flag ---------------------------------------------------


def test_cli_main_rejects_missing_x_posts_path_argument():
    from seam_engine.scan import main
    assert main(["--x-posts"]) == 2


def test_cli_reads_x_posts_file_and_threads_it_into_run_scan(tmp_path, monkeypatch):
    # Prove the CLI wiring end to end without touching the real network: stub
    # fetch_github_activity so the only thing under test is "did --x-posts
    # actually reach run_scan's x_posts parameter," mirroring how run_scan
    # itself has no network test in this file (module docstring, above).
    import seam_engine.scan as scan_mod

    captured = {}
    original = scan_mod.run_scan

    def fake_run_scan(owner, repo, window_hours=24, x_posts=None, github_events=None):
        captured["x_posts"] = x_posts
        return original(owner, repo, window_hours=window_hours, x_posts=x_posts, github_events=github_events)

    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [])
    monkeypatch.setattr(scan_mod, "run_scan", fake_run_scan)

    live_posts = [
        {"id": "1", "text": "t", "url": "https://x.com/oritatown/status/1", "ts": "2026-07-16T00:00:00Z"},
    ]
    posts_path = tmp_path / "live-posts.json"
    posts_path.write_text(json.dumps(live_posts))
    out_path = tmp_path / "out.json"

    rc = scan_mod.main([str(out_path), "--x-posts", str(posts_path)])

    assert rc == 0
    assert captured["x_posts"] == live_posts
    result = json.loads(out_path.read_text())
    assert result["x_posts_source"] == "live"


def test_cli_without_x_posts_flag_uses_the_ledger_fallback(tmp_path, monkeypatch):
    import seam_engine.scan as scan_mod

    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [])
    out_path = tmp_path / "out.json"

    rc = scan_mod.main([str(out_path)])

    assert rc == 0
    result = json.loads(out_path.read_text())
    assert result["x_posts_source"] == "ledger"


def test_cli_module_entrypoint_is_wired_to_main():
    # `python -m seam_engine.scan` must exit through the new argparse-lite
    # main(), not the old bare-script body it replaced (ROADMAP.md #94).
    src = FENCEPOST_ROOT / "seam_engine" / "src" / "seam_engine" / "scan.py"
    text = src.read_text()
    assert 'raise SystemExit(main())' in text


# --- load_github_events_from_live (ROADMAP.md #128) -----------------------------


def test_load_github_events_from_live_parses_normalized_entries():
    data = [
        {"kind": "commit", "id": "abc1234", "title": "ship the thing", "url": "https://github.com/thierrypdamiba/orita/commit/abc1234", "ts": "2026-07-18T09:00:00Z", "author": "kothar-wa-khasis"},
        {"kind": "release", "id": "v1.0", "title": "v1.0", "url": "https://github.com/thierrypdamiba/orita/releases/tag/v1.0", "ts": "2026-07-17T00:00:00+00:00", "author": "nisaba"},
    ]
    events = load_github_events_from_live(data)
    assert events == [
        GithubEvent(kind="commit", id="abc1234", title="ship the thing",
                    url="https://github.com/thierrypdamiba/orita/commit/abc1234",
                    ts=datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc), author="kothar-wa-khasis"),
        GithubEvent(kind="release", id="v1.0", title="v1.0",
                    url="https://github.com/thierrypdamiba/orita/releases/tag/v1.0",
                    ts=datetime(2026, 7, 17, 0, 0, tzinfo=timezone.utc), author="nisaba"),
    ]


def test_load_github_events_from_live_matches_githubevent_shape_the_direct_fetcher_already_produces():
    live = load_github_events_from_live([
        {"kind": "commit", "id": "9", "title": "t", "url": "https://github.com/thierrypdamiba/orita/commit/9", "ts": "2026-07-16T00:00:00Z", "author": "a"},
    ])[0]
    hand_built = GithubEvent(kind="commit", id="9", title="t",
                              url="https://github.com/thierrypdamiba/orita/commit/9",
                              ts=datetime(2026, 7, 16, tzinfo=timezone.utc), author="a")
    assert live == hand_built


def test_load_github_events_from_live_rejects_empty_list():
    # This repo commits most hours of most days -- an empty live read is far
    # more likely to mean the call failed or was blocked (this sandbox's own
    # proxy layer returns exactly this shape of failure for direct GitHub
    # REST egress) than that nothing shipped since the window opened.
    with pytest.raises(ValueError, match="empty list"):
        load_github_events_from_live([])


def test_load_github_events_from_live_rejects_an_entry_missing_a_required_key():
    with pytest.raises(ValueError, match=r"entry 1.*author"):
        load_github_events_from_live([
            {"kind": "commit", "id": "1", "title": "ok", "url": "https://github.com/x/y/commit/1", "ts": "2026-07-16T00:00:00Z", "author": "a"},
            {"kind": "commit", "id": "2", "title": "missing author", "url": "https://github.com/x/y/commit/2", "ts": "2026-07-16T00:00:00Z"},
        ])


def test_load_github_events_from_live_rejects_multiple_missing_keys_naming_all_of_them():
    with pytest.raises(ValueError, match=r"\['title', 'url', 'author'\]"):
        load_github_events_from_live([{"kind": "commit", "id": "1", "ts": "2026-07-16T00:00:00Z"}])


# --- run_scan's github_events override --------------------------------------------


def test_run_scan_with_github_events_override_never_calls_fetch_github_activity(monkeypatch):
    import seam_engine.scan as scan_mod

    def boom(*a, **k):
        raise AssertionError("fetch_github_activity should not be called when github_events is supplied")

    monkeypatch.setattr(scan_mod, "fetch_github_activity", boom)
    live_events = [
        {"kind": "commit", "id": "1", "title": "t", "url": "https://github.com/thierrypdamiba/orita/commit/1", "ts": "2026-07-16T00:00:00Z", "author": "a"},
    ]
    result = scan_mod.run_scan("thierrypdamiba", "orita", x_posts=[
        {"id": "1", "text": "t", "url": "https://x.com/oritatown/status/1", "ts": "2026-07-16T00:00:00Z"},
    ], github_events=live_events)
    assert result["github_events_source"] == "override"


def test_run_scan_without_github_events_uses_direct_fetch(monkeypatch):
    import seam_engine.scan as scan_mod

    called = {}

    def fake_fetch(owner, repo, since):
        called["hit"] = True
        return []

    monkeypatch.setattr(scan_mod, "fetch_github_activity", fake_fetch)
    result = scan_mod.run_scan("thierrypdamiba", "orita", x_posts=[
        {"id": "1", "text": "t", "url": "https://x.com/oritatown/status/1", "ts": "2026-07-16T00:00:00Z"},
    ])
    assert called.get("hit") is True
    assert result["github_events_source"] == "direct"


# --- the CLI's --github-events flag -------------------------------------------


def test_cli_main_rejects_missing_github_events_path_argument():
    from seam_engine.scan import main
    assert main(["--github-events"]) == 2


def test_cli_reads_github_events_file_and_threads_it_into_run_scan(tmp_path, monkeypatch):
    import seam_engine.scan as scan_mod

    captured = {}
    original = scan_mod.run_scan

    def fake_run_scan(owner, repo, window_hours=24, x_posts=None, github_events=None):
        captured["github_events"] = github_events
        return original(owner, repo, window_hours=window_hours, x_posts=x_posts, github_events=github_events)

    monkeypatch.setattr(scan_mod, "run_scan", fake_run_scan)

    live_events = [
        {"kind": "commit", "id": "1", "title": "t", "url": "https://github.com/thierrypdamiba/orita/commit/1", "ts": "2026-07-16T00:00:00Z", "author": "a"},
    ]
    events_path = tmp_path / "live-events.json"
    events_path.write_text(json.dumps(live_events))
    out_path = tmp_path / "out.json"

    rc = scan_mod.main([str(out_path), "--github-events", str(events_path)])

    assert rc == 0
    assert captured["github_events"] == live_events
    result = json.loads(out_path.read_text())
    assert result["github_events_source"] == "override"


def test_cli_without_github_events_flag_uses_direct_fetch(monkeypatch, tmp_path):
    import seam_engine.scan as scan_mod

    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [])
    out_path = tmp_path / "out.json"

    rc = scan_mod.main([str(out_path)])

    assert rc == 0
    result = json.loads(out_path.read_text())
    assert result["github_events_source"] == "direct"

