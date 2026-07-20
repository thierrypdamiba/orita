"""Tests for ROADMAP.md #174: `seam_scan`/`combined_scan_preview`'s missing
`github_events_json` escape hatch.

`scan.run_scan`/`combined_scan.run_combined_scan` both already accept a
`github_events=` override (task 128), mirroring the `x_posts=` override task
94 gave the X side, exactly so a caller whose direct GitHub egress is
blocked (this sandbox's own proxy wall, per `scan.py`'s module docstring)
can hand in an already-fetched, normalized event list instead of crashing.
The CLI got this via `--github-events`. The two live MCP tools on
`server.py` -- the actual surface a connecting agent session calls -- only
ever grew the X-side override (`x_posts_json`); this file proves the
GitHub-side one now exists too, mirrors it line for line, and that the
pre-fix crash was real.

`server.py` imports `fetch_github_activity` by name (`from seam_engine.scan
import fetch_github_activity, ...`), so `seam_scan` calls the binding in
`server`'s own namespace, not `scan_mod.fetch_github_activity` -- tests that
exercise `seam_scan`'s direct-fetch path patch `seam_engine.server`, not
`seam_engine.scan`. `combined_scan_preview` goes through `run_combined_scan`
-> `run_scan`, which calls the module-level name inside `scan.py` itself, so
those tests patch `scan_mod` instead. Every `@app.tool`-decorated function
also runs through Arcade's own error-translation wrapper (`arcade_tdk.tool`),
which re-raises framework-recognized exceptions (an HTTP 403 becomes
`UpstreamError`) but wraps anything else (a raw `ValueError`) in a generic
`FatalToolError` whose `developer_message` carries the original type and
text -- tests account for that wrapping rather than expecting the raw type.
"""
from __future__ import annotations

import json

import pytest
from arcade_core.errors import FatalToolError, UpstreamError

import seam_engine.scan as scan_mod
import seam_engine.server as server_mod
from seam_engine.server import combined_scan_preview, seam_scan

LIVE_EVENTS_JSON = json.dumps([
    {
        "kind": "commit",
        "id": "c1",
        "title": "milestone: real work",
        "url": "https://github.com/thierrypdamiba/orita/commit/c1",
        "ts": "2026-07-20T08:00:00Z",
        "author": "off-by-one",
    },
])


def _blocked_fetch(owner, repo, since):
    """Stands in for this sandbox's real proxy-wall behavior: any direct
    call to `fetch_github_activity` raises, exactly as task 174's live
    reproduction showed (`server.seam_scan()` -> `UpstreamError` 403)."""
    raise UpstreamError("Upstream HTTP request failed (Forbidden, client error).", status_code=403)


def test_seam_scan_crashes_without_the_override_when_direct_fetch_is_blocked(monkeypatch):
    """Pins the pre-fix symptom this task closes: a blocked direct fetch
    takes the whole tool down with an uncaught UpstreamError."""
    monkeypatch.setattr(server_mod, "fetch_github_activity", _blocked_fetch)
    with pytest.raises(UpstreamError):
        seam_scan()


def test_seam_scan_succeeds_with_github_events_json_even_when_direct_fetch_is_blocked(monkeypatch):
    monkeypatch.setattr(server_mod, "fetch_github_activity", _blocked_fetch)
    result = seam_scan(github_events_json=LIVE_EVENTS_JSON)
    assert result["github_events_source"] == "override"
    assert result["repo"] == "thierrypdamiba/orita"


def test_seam_scan_default_path_reports_direct_source(monkeypatch):
    monkeypatch.setattr(server_mod, "fetch_github_activity", lambda owner, repo, since: [])
    result = seam_scan()
    assert result["github_events_source"] == "direct"


def test_combined_scan_preview_crashes_without_the_override_when_direct_fetch_is_blocked(monkeypatch):
    monkeypatch.setattr(scan_mod, "fetch_github_activity", _blocked_fetch)
    with pytest.raises(UpstreamError):
        combined_scan_preview()


def test_combined_scan_preview_succeeds_with_github_events_json_even_when_direct_fetch_is_blocked(monkeypatch):
    monkeypatch.setattr(scan_mod, "fetch_github_activity", _blocked_fetch)
    result = combined_scan_preview(github_events_json=LIVE_EVENTS_JSON)
    assert result["repo"] == "thierrypdamiba/orita"
    assert "primary_gap" in result


def test_github_events_json_rejects_an_empty_array_same_as_the_x_side():
    """`load_github_events_from_live` refuses an empty list (task 128) --
    this override must not silently swallow that guarantee, even filtered
    through the tool wrapper's generic FatalToolError translation."""
    with pytest.raises(FatalToolError) as exc_info:
        seam_scan(github_events_json=json.dumps([]))
    assert "ValueError" in exc_info.value.developer_message
    assert "empty list" in exc_info.value.developer_message
