"""Tests for the recurring-gap machinery in scan.py (ROADMAP.md #19) and the
live-X-read wiring (ROADMAP.md #94).

`_effective_since` is the one piece of arithmetic that decides how far back
`run_scan` looks for GitHub commits. `fetch_github_activity` itself (the one
piece that makes a real network call) has no test HERE — that stays true —
but as of ROADMAP.md #154 it does have tests, in
`test_fetch_github_activity.py`, using `httpx.MockTransport` instead of a
real network call: the pagination bug that claim's own complacency helped
hide (a single unpaginated page silently dropped every commit past the
newest 100) is closed there, not in this file.
`run_scan` now DOES get exercised below (the "prior-milestone-evidence
cross-check" section, added 2026-07-19), but only with `github_events`/
`x_posts` supplied directly and `fetch_github_activity` never reached — the
network path itself is still untested here, on purpose, same as before.
`load_x_posts_from_live` is pure (no network, no filesystem) so it IS covered
here, the same way `_effective_since` already is.
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
    _unresolved_prior_milestone_evidence,
    compute_candidates,
    load_github_events_from_live,
    load_x_posts_from_live,
    run_scan,
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

    def fake_run_scan(owner, repo, window_hours=24, x_posts=None, github_events=None, **kwargs):
        # **kwargs absorbs check_prior_milestones/ledger_base (added after this
        # test was written, ROADMAP.md's 2026-07-19 fix) without forwarding
        # them to `original` — this test is only about `--x-posts` wiring, not
        # the ledger cross-check, so it deliberately keeps that check off.
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


@pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
def test_load_json_list_raises_named_error_not_typeerror_when_json_is_not_a_list(
    tmp_path: Path, bad_value: object
) -> None:
    """task 361: the same non-list guard the RECIPES/*/detector.py campaign
    (task 358) and gmail_calendar.py (task 359) closed, on scan.py's own
    --x-posts/--github-events CLI loaders that scan didn't reach."""
    from seam_engine.scan import _load_json_list

    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps(bad_value))
    with pytest.raises(ValueError, match="expected a JSON list"):
        _load_json_list(bad_file)


@pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
def test_parse_json_list_raises_named_error_not_typeerror_when_json_is_not_a_list(
    bad_value: object,
) -> None:
    """task 362: `_load_json_list` (task 361) is now a thin path-reading
    wrapper around this text-parsing core -- `server.py`'s live MCP tools
    (`seam_scan`/`combined_scan_preview`) parse a caller-supplied JSON
    *string*, not a file path, so they call this directly."""
    from seam_engine.scan import _parse_json_list

    with pytest.raises(ValueError, match="expected a JSON list"):
        _parse_json_list(json.dumps(bad_value), "some_param")


@pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
def test_cli_x_posts_with_non_list_json_raises_named_error(tmp_path, bad_value):
    """Pre-fix, a dict/int/None/string/bool payload reached
    `load_x_posts_from_live`'s `not data` / `enumerate(data)` unmarked,
    producing a confusing crash or silently wrong behavior instead of a
    clear message. Proves the CLI path itself now raises the named error."""
    from seam_engine.scan import main

    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps(bad_value))
    out_path = tmp_path / "out.json"
    with pytest.raises(ValueError, match="expected a JSON list"):
        main([str(out_path), "--x-posts", str(bad_file)])


@pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
def test_cli_github_events_with_non_list_json_raises_named_error(tmp_path, bad_value):
    """Mirrors test_cli_x_posts_with_non_list_json_raises_named_error for
    --github-events."""
    from seam_engine.scan import main

    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps(bad_value))
    out_path = tmp_path / "out.json"
    with pytest.raises(ValueError, match="expected a JSON list"):
        main([str(out_path), "--github-events", str(bad_file)])


def test_cli_without_x_posts_flag_uses_the_ledger_fallback(tmp_path, monkeypatch):
    import seam_engine.scan as scan_mod

    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [])
    # main()'s check_prior_milestones=True (2026-07-19 fix, see below) reads
    # the REAL fencepost/GAPS ledger by default; this test stubs an empty
    # events list purely to test flag routing, not the ledger cross-check —
    # isolate it from real ledger contents the same way fetch_github_activity
    # is already stubbed away from the real network.
    monkeypatch.setattr(scan_mod, "_unresolved_prior_milestone_evidence", lambda *a, **k: {})
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

    def fake_run_scan(owner, repo, window_hours=24, x_posts=None, github_events=None, **kwargs):
        # See the sibling x-posts test above for why **kwargs is here and why
        # it is not forwarded to `original`.
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
    # main()'s check_prior_milestones=True (2026-07-19 fix, see below) reads
    # the REAL fencepost/GAPS ledger by default; this test stubs an empty
    # events list purely to test flag routing, not the ledger cross-check —
    # isolate it from real ledger contents the same way fetch_github_activity
    # is already stubbed away from the real network.
    monkeypatch.setattr(scan_mod, "_unresolved_prior_milestone_evidence", lambda *a, **k: {})
    out_path = tmp_path / "out.json"

    rc = scan_mod.main([str(out_path)])

    assert rc == 0
    result = json.loads(out_path.read_text())
    assert result["github_events_source"] == "direct"


# --- prior-milestone-evidence cross-check (found + closed 2026-07-19) ----------
#
# scan.py's own module docstring promised (ROADMAP.md #19) that "a milestone
# commit stays a live candidate for as long as it remains genuinely
# unannounced" — but that promise was only ever kept for the direct-fetch
# path (`_effective_since`'s `since` reaches `fetch_github_activity`); the
# live-override path (`load_github_events_from_live`) never received `since`
# at all, so a caller supplying a too-short window could make an
# already-sealed, still-open milestone gap silently vanish. This is not a
# hypothetical: `fencepost/GAPS/2026-07-18.md` sealed 4 real, still-
# unannounced milestone commits as this town's own primary gap; the very
# next day's override-sourced scan (`fencepost/candidates/2026-07-19.json`)
# saw only 1, unrelated commit, with no real X post ever landing in between
# (X posting has been forbidden since 2026-07-14 — `tools/x_outage_tracker.py`).
# These tests prove `_unresolved_prior_milestone_evidence`/`run_scan`'s new
# `check_prior_milestones` catch exactly that, against the real ledger data,
# not a synthetic stand-in for it.

from seam_engine import ledger as _ledger_mod  # noqa: E402 -- grouped with this section on purpose

_REAL_0718_EVIDENCE = [
    "https://github.com/thierrypdamiba/orita/commit/5110507911296f182115359fafc6dfcffcd23796",
    "https://github.com/thierrypdamiba/orita/commit/fab95533935e34db435529ffb8028d4bdee6d385",
    "https://github.com/thierrypdamiba/orita/commit/d8d98321640fa055827928fb6b099e0ef5c217f7",
    "https://github.com/thierrypdamiba/orita/commit/a53262bfcc4412eb9fd12a26f9992591fda596f6",
]
_REAL_0718_SEALED_AT = "2026-07-18T13:10:49.350606+00:00"
_REAL_0719_ONLY_EVENT_URL = "https://github.com/thierrypdamiba/orita/commit/a4d02f092efb7fe919ad95494d68873f76f78599"


def _seal_milestone_gap(base: Path, *, evidence: list[str], generated_at: str, confidence: float = 0.75) -> None:
    """Seal one scan result carrying a `milestone-unannounced` primary gap
    into a fixture ledger at `base` — the same shape `ledger.append_scan`
    always takes, built by hand here only so the test controls `generated_at`
    and `evidence` exactly.
    """
    _ledger_mod.append_scan(
        {
            "generated_at": generated_at,
            "repo": "thierrypdamiba/orita",
            "window_hours": 24,
            "confidence_bar": 0.7,
            "separation_margin": 0.15,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "Milestone-level work shipped but never reached @oritatown",
                "detail": f"{len(evidence)} milestone commit(s), none echoed in a post.",
                "confidence": confidence,
                "evidence": evidence,
            },
            "tail": [],
            "excluded": [],
        },
        base=base,
    )


def test_unresolved_prior_milestone_evidence_finds_open_evidence_with_no_resolving_post(tmp_path):
    _seal_milestone_gap(tmp_path, evidence=_REAL_0718_EVIDENCE, generated_at=_REAL_0718_SEALED_AT)
    x_posts = [XPost(id="1", text="unrelated", url="https://x.com/oritatown/status/1",
                      ts=datetime(2026, 7, 13, tzinfo=timezone.utc))]  # before the gap was sealed

    unresolved = _unresolved_prior_milestone_evidence(x_posts, tmp_path)

    assert set(unresolved) == set(_REAL_0718_EVIDENCE)
    assert all(at == _REAL_0718_SEALED_AT for at in unresolved.values())


def test_unresolved_prior_milestone_evidence_drops_urls_once_a_post_lands_after_sealing(tmp_path):
    _seal_milestone_gap(tmp_path, evidence=_REAL_0718_EVIDENCE, generated_at=_REAL_0718_SEALED_AT)
    x_posts = [XPost(id="1", text="fencepost, finally", url="https://x.com/oritatown/status/2",
                      ts=datetime(2026, 7, 18, 14, tzinfo=timezone.utc))]  # after the gap was sealed

    unresolved = _unresolved_prior_milestone_evidence(x_posts, tmp_path)

    assert unresolved == {}


def test_unresolved_prior_milestone_evidence_ignores_non_milestone_primary_gaps(tmp_path):
    _ledger_mod.append_scan(
        {
            "generated_at": _REAL_0718_SEALED_AT, "repo": "thierrypdamiba/orita",
            "window_hours": 24, "confidence_bar": 0.7, "separation_margin": 0.15,
            "primary_gap": {
                "slug": "release-v1", "headline": "Release shipped but never reached @oritatown",
                "detail": "d", "confidence": 0.9, "evidence": ["https://github.com/thierrypdamiba/orita/releases/tag/v1"],
            },
            "tail": [], "excluded": [],
        },
        base=tmp_path,
    )
    x_posts = [XPost(id="1", text="t", url="https://x.com/oritatown/status/1", ts=datetime(2026, 7, 13, tzinfo=timezone.utc))]

    assert _unresolved_prior_milestone_evidence(x_posts, tmp_path) == {}


def test_unresolved_prior_milestone_evidence_cannot_recover_a_tail_only_milestone_gap(tmp_path):
    # A documented, narrower-than-ideal scope: ledger.append_scan seals a tail
    # entry's slug/confidence/label only, never its evidence — so a
    # milestone-unannounced candidate that only ever sat below the bar (like
    # the real 2026-07-19 entry itself) leaves nothing this function can
    # recover. This test pins that limitation rather than hiding it.
    _ledger_mod.append_scan(
        {
            "generated_at": "2026-07-19T01:14:35.907870+00:00", "repo": "thierrypdamiba/orita",
            "window_hours": 24, "confidence_bar": 0.7, "separation_margin": 0.15,
            "primary_gap": None,
            "tail": [{"slug": "milestone-unannounced", "confidence": 0.45, "label": "coincidence"}],
            "excluded": [],
        },
        base=tmp_path,
    )
    x_posts = [XPost(id="1", text="t", url="https://x.com/oritatown/status/1", ts=datetime(2026, 7, 13, tzinfo=timezone.utc))]

    assert _unresolved_prior_milestone_evidence(x_posts, tmp_path) == {}


def _live_x_posts_no_new_activity() -> list[dict]:
    """A normalized x_posts override with real posts, none after the real
    2026-07-18 gap was sealed — standing in for "the outage means no new
    post could possibly have resolved it," without touching the real
    HAND/mortal-sky-log.md file."""
    return [{"id": "1", "text": "old news", "url": "https://x.com/oritatown/status/1",
             "ts": "2026-07-12T00:00:00Z"}]


def test_run_scan_raises_reproducing_the_real_2026_07_18_to_07_19_regression(tmp_path):
    # This is the real incident, replayed: seed the fixture ledger with
    # exactly what fencepost/GAPS/2026-07-18.md really sealed (4 evidence
    # commits), then hand run_scan exactly what the real
    # fencepost/candidates/2026-07-19.json override actually supplied (1
    # unrelated commit, missing all 4). Before this fix, run_scan accepted
    # this silently -- that IS what actually happened on 2026-07-19. Now it
    # must raise.
    _seal_milestone_gap(tmp_path, evidence=_REAL_0718_EVIDENCE, generated_at=_REAL_0718_SEALED_AT)
    truncated_events = [
        {"kind": "commit", "id": "a4d02f0", "title": "unrelated work",
         "url": _REAL_0719_ONLY_EVENT_URL, "ts": "2026-07-19T00:30:00Z", "author": "someone"},
    ]

    with pytest.raises(ValueError, match=r"missing 4 previously-sealed"):
        run_scan(
            "thierrypdamiba", "orita",
            x_posts=_live_x_posts_no_new_activity(),
            github_events=truncated_events,
            check_prior_milestones=True,
            ledger_base=tmp_path,
        )


def test_run_scan_does_not_raise_when_the_override_still_carries_all_open_evidence(tmp_path):
    _seal_milestone_gap(tmp_path, evidence=_REAL_0718_EVIDENCE, generated_at=_REAL_0718_SEALED_AT)
    complete_events = [
        {"kind": "commit", "id": url.rsplit("/", 1)[-1][:7], "title": "fencepost milestone work",
         "url": url, "ts": "2026-07-18T12:00:00Z", "author": "someone"}
        for url in _REAL_0718_EVIDENCE
    ] + [
        {"kind": "commit", "id": "a4d02f0", "title": "unrelated work",
         "url": _REAL_0719_ONLY_EVENT_URL, "ts": "2026-07-19T00:30:00Z", "author": "someone"},
    ]

    result = run_scan(
        "thierrypdamiba", "orita",
        x_posts=_live_x_posts_no_new_activity(),
        github_events=complete_events,
        check_prior_milestones=True,
        ledger_base=tmp_path,
    )

    assert result["github_events_source"] == "override"


def test_check_prior_milestones_guards_evidence_urls_not_the_reported_count(tmp_path):
    # Live, real finding (2026-08-11, task 677): the same production entrypoint
    # (`seam_engine.scan --github-events <cache>`) run twice a few hours apart
    # against the town's own real cache reported 116 milestone commits at
    # 12:59 UTC (the day's live-fetch seam-scan.yml cron run, sealed into
    # today's Ledger tip) and 111 at 15:10 UTC (this hour's cache-override
    # rerun, after ingesting only 6 new, non-milestone-matching commits) --
    # same slug, same confidence, the identical 5 evidence URLs in the same
    # order, just a smaller `detail` count. `check_prior_milestones=True`
    # raised nothing, correctly: every previously-sealed EVIDENCE url was
    # still present in the smaller run. That is `_unresolved_prior_milestone_
    # evidence`'s real, honest scope (its own docstring already says so --
    # "narrowed to the ones still genuinely open", read via the Ledger's
    # `evidence` list, capped at 5 by `run_scan`'s own `[:5]` slice) -- it
    # was never a promise to reconcile the full `len(milestones)` denominator
    # a `detail` string reports, only the handful of URLs a reader might
    # click. This test pins that boundary on purpose, with a fixture shaped
    # like the real 2026-08-11 case (all sealed evidence present, one real
    # additional milestone commit missing from the override), so a future
    # reader finds a tested boundary here instead of re-discovering the same
    # live surprise this docstring is quoting from.
    _seal_milestone_gap(tmp_path, evidence=_REAL_0718_EVIDENCE, generated_at=_REAL_0718_SEALED_AT)
    # All 4 sealed evidence URLs present (nothing missing -- check_prior_
    # milestones has no complaint), PLUS one extra real milestone commit
    # that a fuller live-fetch would have found but this override omits.
    # The omitted commit is never named in the ledger's own evidence (only
    # the first 5 milestone commits ever become `evidence`), so nothing
    # anywhere records that it went missing -- the exact silent-denominator-
    # shrink shape this test documents.
    events_missing_one_unsealed_milestone_commit = [
        {"kind": "commit", "id": url.rsplit("/", 1)[-1][:7], "title": "fencepost milestone work",
         "url": url, "ts": "2026-07-18T12:00:00Z", "author": "someone"}
        for url in _REAL_0718_EVIDENCE
    ]

    result = run_scan(
        "thierrypdamiba", "orita",
        x_posts=_live_x_posts_no_new_activity(),
        github_events=events_missing_one_unsealed_milestone_commit,
        check_prior_milestones=True,
        ledger_base=tmp_path,
    )

    # No raise (asserted implicitly by reaching here) -- and the surfaced
    # gap's own reported count reflects only what THIS run's events held,
    # 4 milestone commits, never the 5th the real town's own history had
    # that hour. A smaller, true-to-this-run count, not a fabricated one --
    # but nothing compares it against the Ledger's own last-sealed count
    # either. That asymmetry (URLs checked, counts not) is the real boundary.
    assert result["primary_gap"]["slug"] == "milestone-unannounced"
    assert result["primary_gap"]["detail"].startswith("4 milestone commit(s)")


def test_run_scan_check_prior_milestones_defaults_off_preserving_old_behavior(tmp_path):
    # Backward compatibility: a fixture ledger with real missing evidence is
    # present, but check_prior_milestones is left at its default (False) --
    # exactly how every other test in this file already calls run_scan, and
    # exactly how run_combined_scan.py still calls it today. Must not raise.
    _seal_milestone_gap(tmp_path, evidence=_REAL_0718_EVIDENCE, generated_at=_REAL_0718_SEALED_AT)
    truncated_events = [
        {"kind": "commit", "id": "a4d02f0", "title": "unrelated work",
         "url": _REAL_0719_ONLY_EVENT_URL, "ts": "2026-07-19T00:30:00Z", "author": "someone"},
    ]

    result = run_scan(
        "thierrypdamiba", "orita",
        x_posts=_live_x_posts_no_new_activity(),
        github_events=truncated_events,
        ledger_base=tmp_path,  # supplied but unused -- check_prior_milestones stays False
    )

    assert result["github_events_source"] == "override"


def test_cli_main_activates_the_prior_milestone_check_by_default(monkeypatch):
    # main() is the real entrypoint seam-scan.yml's cron and every manual
    # override run actually call — prove it turns the new safety net on
    # without anyone needing to remember a flag.
    import seam_engine.scan as scan_mod

    captured = {}

    def fake_run_scan(owner, repo, window_hours=24, x_posts=None, github_events=None, **kwargs):
        captured.update(kwargs)
        return {
            "generated_at": "2026-07-19T00:00:00+00:00", "repo": f"{owner}/{repo}",
            "window_hours": window_hours, "account_live_since": "2026-07-12T00:00:00+00:00",
            "x_posts_source": "ledger", "github_events_source": "direct",
            "confidence_bar": 0.7, "separation_margin": 0.15,
            "primary_gap": None, "tail": [], "excluded": [],
        }

    monkeypatch.setattr(scan_mod, "run_scan", fake_run_scan)

    rc = scan_mod.main([])

    assert rc == 0
    assert captured.get("check_prior_milestones") is True


# --- live proof against the real, already-sealed ledger -----------------------


def test_real_ledger_has_unresolved_milestone_evidence_right_now():
    # Not a fixture: reads the REAL fencepost/GAPS/*.md tablets this town has
    # actually sealed. As of this writing, no real X post has landed since
    # 2026-07-18T13:10:49Z (the outage tracked in tools/x_outage_tracker.py
    # is still open), so the 4 commits fencepost/GAPS/2026-07-18.md sealed as
    # this town's own primary milestone gap are still, genuinely, unresolved
    # today -- this is the live proof the bug this task fixes is real, not
    # hypothetical. (This assertion is a live snapshot: once a real X post
    # finally lands mentioning one of MILESTONE_KEYWORDS, or once this
    # specific evidence is superseded by a later real primary_gap entry,
    # it will need updating -- same as every other "live" test in this repo.)
    from seam_engine.scan import load_x_posts_from_ledger

    real_x_posts = load_x_posts_from_ledger()
    unresolved = _unresolved_prior_milestone_evidence(real_x_posts, None)

    for url in _REAL_0718_EVIDENCE:
        assert url in unresolved, f"{url} should still read as unresolved (no real post has landed since it was sealed)"


def test_real_ledger_chain_still_verifies_intact_after_this_task():
    # Confirms this task's changes never touched the real, sealed
    # fencepost/GAPS/*.md tablets themselves (only scan.py's code and this
    # test file) -- a tampered tablet would fail this, immediately.
    problems = _ledger_mod.verify(None)
    assert problems == []



# --- release-title keyword-extraction boundary (ROADMAP.md #209) --------------
#
# `compute_candidates` decides a release was announced by the keyword overlap
# between its title and the town's X posts. A bare version-string title
# ("v1.0", "v0.2.0") yields NO extractable keywords -- `_keywords` needs a
# letter followed by 2+ word chars, which a version number never has -- so the
# overlap is empty for a reason that has nothing to do with whether the release
# was actually announced. Off-By-One's boundary: the release branch must not
# read "empty title keywords" as "nobody tweeted it."

_LIVE = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _release(title: str, rid: str = "v1.0") -> GithubEvent:
    return GithubEvent(
        kind="release",
        id=rid,
        title=title,
        url=f"https://github.com/thierrypdamiba/orita/releases/tag/{rid}",
        ts=datetime(2026, 7, 10, tzinfo=timezone.utc),
        author="nisaba",
    )


def _post(text: str, pid: str = "1") -> XPost:
    return XPost(
        id=pid,
        text=text,
        url=f"https://x.com/oritatown/status/{pid}",
        ts=datetime(2026, 7, 10, 1, 0, tzinfo=timezone.utc),
    )


def test_bare_version_release_named_verbatim_in_a_post_is_not_a_gap():
    # The bug: "v1.0" has no extractable keywords, so keyword overlap can
    # never match, so this release was ALWAYS surfaced at 0.9 even though the
    # post literally announces it. Pre-fix this asserted the opposite; a
    # stash-and-rerun of the pre-fix scan.py fails here with a stray
    # `release-v1.0` in `surfaced`.
    release = _release("v1.0")
    posts = [_post("Fencepost v1.0 is live today -- connect your own accounts!")]
    surfaced, _excluded = compute_candidates([release], posts, _LIVE)
    assert not any(g.slug == "release-v1.0" for g in surfaced), (
        "a release announced verbatim in a post must not be a gap -- a "
        "0.9-confidence false positive is the crying-wolf failure Ogun's law forbids"
    )


def test_bare_version_release_named_in_no_post_is_still_surfaced():
    # The fallback must not swing the other way into a false NEGATIVE: a
    # bare-version release that no post mentions is still a real gap.
    release = _release("v1.0")
    posts = [_post("good morning from the town, a quiet day at the crossroads")]
    surfaced, _excluded = compute_candidates([release], posts, _LIVE)
    gaps = [g for g in surfaced if g.slug == "release-v1.0"]
    assert len(gaps) == 1 and gaps[0].confidence == 0.9, (
        "an unannounced release is still the gap it always was"
    )


def test_keyword_bearing_release_title_keeps_the_exact_pre_fix_overlap_behavior():
    # The fallback fires ONLY when the title yields no keywords. A descriptive
    # title keeps the original overlap match, unchanged in both directions.
    release = _release("The Counter Awakens", rid="ep-3")
    announced = compute_candidates(
        [release], [_post("the counter awakens at last, tonight")], _LIVE
    )[0]
    silent = compute_candidates(
        [release], [_post("unrelated chatter about lunch")], _LIVE
    )[0]
    assert not any(g.slug == "release-ep-3" for g in announced)
    assert any(g.slug == "release-ep-3" for g in silent)


def _milestone_commit(cid: str, ts: datetime) -> GithubEvent:
    return GithubEvent(
        kind="commit", id=cid, title=f"fencepost: milestone commit {cid}",
        url=f"https://github.com/thierrypdamiba/orita/commit/{cid}",
        ts=ts, author="test",
    )


def test_milestone_evidence_is_oldest_first_regardless_of_input_commit_order():
    # Task 577: caught live comparing a fresh scan (via the `--github-events`
    # override, whose cache is always saved oldest-first) against today's
    # already-sealed tablet entry (generated via the direct-fetch path,
    # which returns GitHub's own `/commits` page order -- newest-first): same
    # slug, same count, same 0.85 confidence, ZERO evidence-URL overlap.
    # Pre-fix, `evidence=[m.url for m in milestones][:5]` silently inherited
    # whichever order `commits` happened to arrive in. Two commit lists
    # below carry the exact same five milestone commits, one oldest-first
    # (the override/cache convention) and one newest-first (the direct-fetch
    # convention) -- both must produce identical, oldest-first evidence.
    oldest_first = [
        _milestone_commit("aaa0001", datetime(2026, 7, 12, 8, 0, tzinfo=timezone.utc)),
        _milestone_commit("aaa0002", datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)),
        _milestone_commit("aaa0003", datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)),
        _milestone_commit("aaa0004", datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)),
        _milestone_commit("aaa0005", datetime(2026, 8, 6, 8, 0, tzinfo=timezone.utc)),
    ]
    newest_first = list(reversed(oldest_first))
    posts = [_post("unrelated chatter, no milestone keyword here")]

    gap_from_oldest_first_input = next(
        g for g in compute_candidates(oldest_first, posts, _LIVE)[0]
        if g.slug == "milestone-unannounced"
    )
    gap_from_newest_first_input = next(
        g for g in compute_candidates(newest_first, posts, _LIVE)[0]
        if g.slug == "milestone-unannounced"
    )

    expected_evidence = [c.url for c in oldest_first]
    assert gap_from_oldest_first_input.evidence == expected_evidence
    assert gap_from_newest_first_input.evidence == expected_evidence, (
        "evidence must be deterministic (oldest-first) regardless of "
        "which order the caller's github_events happened to arrive in"
    )
