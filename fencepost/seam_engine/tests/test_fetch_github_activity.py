"""Tests for `fetch_github_activity`'s pagination (ROADMAP.md #154).

`test_scan.py`'s own module docstring has said since 2026-07-12 that
`fetch_github_activity` itself "has no test here — that stays true", on the
grounds that it's the one piece that makes a real network call. That claim
was honest but let a real bug hide behind it: the function fetched exactly
one `per_page=100` page of `/commits` and stopped, so once the real commit
count between `since` and now passed 100 it silently kept only the 100 MOST
RECENT ones — a live `seam-scan` CI failure on 2026-07-19 (task 150's own
new `check_prior_milestones` gate caught it: 14 previously-sealed
still-unannounced milestone commits back to 2026-07-12 had fallen off page
1). This file closes the untested gap `test_scan.py` named plainly, using
`httpx.MockTransport` (already in `scan.py`'s own dependency, no new one
added) instead of a real network call, so the network boundary stays real
but observable.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from seam_engine.scan import _MAX_COMMIT_PAGES, fetch_github_activity

SINCE = datetime(2026, 7, 12, 0, 0, tzinfo=timezone.utc)


def _commit(n: int) -> dict:
    return {
        "sha": f"{n:040x}",
        "commit": {
            "message": f"task {n}: a real commit message\n\nbody",
            "author": {"name": "Some God", "date": "2026-07-12T11:38:10+00:00"},
        },
        "html_url": f"https://github.com/thierrypdamiba/orita/commit/{n:040x}",
    }


def _no_release_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(404, json={"message": "Not Found"})


def _paged_transport(pages: list[list[dict]]):
    """A MockTransport serving `pages[i]` for `?page=i+1`, and 404 for releases."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/releases/latest"):
            return _no_release_response(request)
        assert request.url.path.endswith("/commits")
        page = int(request.url.params.get("page", "1"))
        if page > len(pages):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=pages[page - 1])

    return httpx.MockTransport(handler)


def test_fetch_github_activity_follows_pagination_past_the_first_page(monkeypatch):
    # The real bug: 114 real commits since `since`, but a single unpaginated
    # per_page=100 call only ever saw the newest 100. Two pages here (100 +
    # 14) must both be collected.
    page_1 = [_commit(n) for n in range(100, 0, -1)]  # 100 commits
    page_2 = [_commit(n) for n in range(114, 100, -1)]  # 14 more commits
    transport = _paged_transport([page_1, page_2])

    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)

    events = fetch_github_activity("thierrypdamiba", "orita", SINCE)

    assert len(events) == 114
    ids = {e.id for e in events}
    assert f"{1:040x}"[:7] in ids  # the oldest commit, the one page 1 alone would drop
    assert f"{114:040x}"[:7] in ids  # the newest commit, from page 2


def test_fetch_github_activity_stops_at_the_first_short_page(monkeypatch):
    # A short (< per_page) page is the real "last page" signal — pagination
    # must not keep requesting page 3 once page 2 comes back with 14 items.
    page_1 = [_commit(n) for n in range(100, 0, -1)]
    page_2 = [_commit(n) for n in range(105, 100, -1)]  # 5 commits, short
    requested_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/releases/latest"):
            return _no_release_response(request)
        page = int(request.url.params.get("page", "1"))
        requested_pages.append(page)
        if page == 1:
            return httpx.Response(200, json=page_1)
        if page == 2:
            return httpx.Response(200, json=page_2)
        raise AssertionError(f"fetch_github_activity requested page {page} past the short page")

    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)

    events = fetch_github_activity("thierrypdamiba", "orita", SINCE)

    assert requested_pages == [1, 2]
    assert len(events) == 105


def test_fetch_github_activity_single_short_page_unchanged_behavior(monkeypatch):
    # The common case (a young repo / narrow window): one short page, no
    # pagination needed — proves the fix doesn't regress the original,
    # already-correct single-page shape.
    page_1 = [_commit(n) for n in range(3, 0, -1)]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/releases/latest"):
            return _no_release_response(request)
        assert request.url.params.get("page", "1") == "1"
        return httpx.Response(200, json=page_1)

    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)

    events = fetch_github_activity("thierrypdamiba", "orita", SINCE)
    assert len(events) == 3


def test_fetch_github_activity_raises_rather_than_looping_forever(monkeypatch):
    # The safety valve: if GitHub ever serves _MAX_COMMIT_PAGES consecutive
    # full pages, refuse to keep paginating silently rather than guessing
    # when to stop.
    full_page = [_commit(n) for n in range(100)]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/releases/latest"):
            return _no_release_response(request)
        return httpx.Response(200, json=full_page)

    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)

    with pytest.raises(RuntimeError, match=f"{_MAX_COMMIT_PAGES}"):
        fetch_github_activity("thierrypdamiba", "orita", SINCE)


def test_fetch_github_activity_still_fetches_the_release(monkeypatch):
    # Pagination must not disturb the existing release-fetch behavior.
    page_1 = [_commit(1)]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/releases/latest"):
            return httpx.Response(
                200,
                json={
                    "tag_name": "episode-001",
                    "name": "Episode One",
                    "html_url": "https://github.com/thierrypdamiba/orita/releases/tag/episode-001",
                    "published_at": "2026-07-13T00:00:00Z",
                    "author": {"login": "kwaku-ananse"},
                },
            )
        return httpx.Response(200, json=page_1)

    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)

    events = fetch_github_activity("thierrypdamiba", "orita", SINCE)
    kinds = {e.kind for e in events}
    assert kinds == {"commit", "release"}


def test_mutation_the_real_pre_fix_single_page_shape_would_have_dropped_old_commits(monkeypatch):
    """Hand-verification: reconstruct the real pre-task-154 shape (one
    unpaginated per_page=100 call) against the SAME 114-commit fixture the
    fix-proving test above uses, and prove it really would have silently
    kept only the newest 100 — the live bug, not a synthetic one."""
    from seam_engine import github_auth

    page_1 = [_commit(n) for n in range(100, 0, -1)]
    page_2 = [_commit(n) for n in range(114, 100, -1)]
    transport = _paged_transport([page_1, page_2])

    def pre_fix_fetch(owner: str, repo: str, since) -> list:
        headers = github_auth.github_headers()
        with httpx.Client(timeout=15.0, headers=headers, transport=transport) as client:
            commits = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits",
                params={"since": since.isoformat(), "per_page": 100},
            )
            commits.raise_for_status()
            return commits.json()

    dropped = pre_fix_fetch("thierrypdamiba", "orita", SINCE)
    assert len(dropped) == 100  # the real bug: 14 real commits silently missing

    # The real, fixed function, same fixture, same instant in history:
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client",
        lambda *a, **k: real_client(*a, **{**k, "transport": transport}),
    )
    fixed = fetch_github_activity("thierrypdamiba", "orita", SINCE)
    assert len(fixed) == 114
