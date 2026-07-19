"""Tests for `fetch_latest_release` and `server.get_latest_release`
(ROADMAP.md #157).

`server.get_latest_release` used to answer "what's the latest release?" by
calling `fetch_github_activity(owner, repo, datetime(1970, 1, 1, ...))` and
filtering the result for `kind == "release"` — harmless before task 154
(one unpaginated 100-commit page, thrown away), but task 154 correctly
turned commit fetching into a real paginating loop. An epoch `since` now
forces that loop to paginate the repo's ENTIRE commit history before ever
reaching the release call: wasteful at best, and (past
`_MAX_COMMIT_PAGES * 100` commits) a live `RuntimeError` that never returns
a release again, for a question that only ever needed one HTTP request.
`fetch_latest_release` asks it directly; this file proves it does, and
proves the real pre-fix crash it replaces.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from seam_engine.scan import GithubEvent, _MAX_COMMIT_PAGES, fetch_github_activity, fetch_latest_release

RELEASE_JSON = {
    "tag_name": "episode-001",
    "name": "Episode One",
    "html_url": "https://github.com/thierrypdamiba/orita/releases/tag/episode-001",
    "published_at": "2026-07-13T00:00:00Z",
    "author": {"login": "kwaku-ananse"},
}


def _install_transport(monkeypatch, handler) -> None:
    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)


# --- fetch_latest_release: the fixed path -----------------------------------


def test_fetch_latest_release_makes_exactly_one_request_never_touching_commits(monkeypatch):
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        assert request.url.path.endswith("/releases/latest")
        return httpx.Response(200, json=RELEASE_JSON)

    _install_transport(monkeypatch, handler)

    event = fetch_latest_release("thierrypdamiba", "orita")

    assert requested_paths == ["/repos/thierrypdamiba/orita/releases/latest"]
    assert event == GithubEvent(
        kind="release",
        id="episode-001",
        title="Episode One",
        url="https://github.com/thierrypdamiba/orita/releases/tag/episode-001",
        ts=datetime(2026, 7, 13, 0, 0, tzinfo=timezone.utc),
        author="kwaku-ananse",
    )


def test_fetch_latest_release_returns_none_on_404(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    _install_transport(monkeypatch, handler)

    assert fetch_latest_release("thierrypdamiba", "orita") is None


def test_fetch_latest_release_falls_back_to_tag_name_when_name_is_blank(monkeypatch):
    body = dict(RELEASE_JSON, name="")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    _install_transport(monkeypatch, handler)

    event = fetch_latest_release("thierrypdamiba", "orita")
    assert event.title == "episode-001"


# --- the real pre-fix crash this closes -------------------------------------


def test_mutation_the_real_pre_fix_epoch_since_shape_would_have_raised(monkeypatch):
    """Hand-verification: reconstruct `get_latest_release`'s real pre-task-157
    shape (`fetch_github_activity(owner, repo, EPOCH)`, filtered for
    `kind == "release"`) against a repo that keeps answering full 100-commit
    pages -- exactly what a real repo committing most hours of most days
    looks like once its total history passes `_MAX_COMMIT_PAGES * 100`
    commits -- and prove it really does raise `RuntimeError` and never reach
    the release at all. The fixed `fetch_latest_release`, against the exact
    same transport, makes zero `/commits` requests and returns the release
    cleanly."""
    commit = {
        "sha": "a" * 40,
        "commit": {
            "message": "a commit",
            "author": {"name": "Some God", "date": "2026-07-12T11:38:10+00:00"},
        },
        "html_url": "https://github.com/thierrypdamiba/orita/commit/aaaa",
    }
    full_page = [commit] * 100
    commit_requests: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/releases/latest"):
            return httpx.Response(200, json=RELEASE_JSON)
        commit_requests.append(1)
        return httpx.Response(200, json=full_page)

    _install_transport(monkeypatch, handler)

    # The real pre-fix shape: server.get_latest_release's old body, inline.
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(RuntimeError, match=f"{_MAX_COMMIT_PAGES}"):
        fetch_github_activity("thierrypdamiba", "orita", epoch)
    assert len(commit_requests) == _MAX_COMMIT_PAGES  # paginated the entire way before giving up

    # The real, fixed function, same transport, same instant in history:
    commit_requests.clear()
    event = fetch_latest_release("thierrypdamiba", "orita")
    assert commit_requests == []  # never touched /commits at all
    assert event.id == "episode-001"


# --- server.get_latest_release: the live tool is wired to the fixed path ---


def test_server_get_latest_release_calls_fetch_latest_release_not_fetch_github_activity(monkeypatch):
    import seam_engine.server as server_mod

    calls = {"fetch_latest_release": 0, "fetch_github_activity": 0}

    def fake_fetch_latest_release(owner, repo):
        calls["fetch_latest_release"] += 1
        return GithubEvent(
            kind="release", id="episode-001", title="Episode One",
            url="https://x/y", ts=datetime(2026, 7, 13, tzinfo=timezone.utc),
            author="kwaku-ananse",
        )

    def fake_fetch_github_activity(owner, repo, since):
        calls["fetch_github_activity"] += 1
        raise AssertionError("get_latest_release must not call fetch_github_activity")

    monkeypatch.setattr(server_mod, "fetch_latest_release", fake_fetch_latest_release)
    monkeypatch.setattr(server_mod, "fetch_github_activity", fake_fetch_github_activity)

    result = server_mod.get_latest_release(owner="thierrypdamiba", repo="orita")

    assert calls == {"fetch_latest_release": 1, "fetch_github_activity": 0}
    assert result["id"] == "episode-001"


def test_server_get_latest_release_returns_none_when_fetch_latest_release_returns_none(monkeypatch):
    import seam_engine.server as server_mod

    monkeypatch.setattr(server_mod, "fetch_latest_release", lambda owner, repo: None)

    assert server_mod.get_latest_release(owner="thierrypdamiba", repo="orita") is None
