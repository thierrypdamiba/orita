"""Tests for `scan.commit_event_fields`/`scan.release_event_fields` (task 553).

These two pure functions were pulled out of `fetch_github_activity`'s own
commit-mapping loop and `_release_event_from_json` respectively, string
`ts` kept as-is (never parsed to a `datetime` inside them) so
`github_events_cache.normalize_raw_commits`/`normalize_raw_release` can use
their output directly as a cache entry. No behavior change was intended —
this file proves that identity two ways: unit-level field mapping, and
byte-identical output against `fetch_github_activity`'s/
`_release_event_from_json`'s own pre-refactor construction for a fixed
fixture.
"""
from __future__ import annotations

from datetime import UTC, datetime

from seam_engine.scan import (
    GithubEvent,
    _release_event_from_json,
    commit_event_fields,
    release_event_fields,
)

RAW_COMMIT = {
    "sha": "abcdef1234567890abcdef1234567890abcdef1",
    "commit": {
        "message": "Task 553: first line only\n\nbody text, dropped",
        "author": {"name": "Nisaba", "date": "2026-08-05T12:00:00Z"},
    },
    "html_url": "https://github.com/thierrypdamiba/orita/commit/abcdef1234567890abcdef1234567890abcdef1",
}

RAW_RELEASE = {
    "tag_name": "episode-001",
    "name": "Episode 1 — The Founding",
    "html_url": "https://github.com/thierrypdamiba/orita/releases/tag/episode-001",
    "published_at": "2026-07-11T10:58:26Z",
    "author": {"login": "thierrypdamiba"},
}


def test_commit_event_fields_maps_all_six_keys():
    fields = commit_event_fields(RAW_COMMIT)
    assert fields == {
        "kind": "commit",
        "id": "abcdef1",
        "title": "Task 553: first line only",
        "url": "https://github.com/thierrypdamiba/orita/commit/abcdef1234567890abcdef1234567890abcdef1",
        "ts": "2026-08-05T12:00:00Z",
        "author": "Nisaba",
    }


def test_commit_event_fields_ts_is_the_original_string_not_a_datetime():
    fields = commit_event_fields(RAW_COMMIT)
    assert fields["ts"] == "2026-08-05T12:00:00Z"
    assert isinstance(fields["ts"], str)


def test_commit_event_fields_truncates_sha_to_seven_and_takes_first_line():
    fields = commit_event_fields(RAW_COMMIT)
    assert fields["id"] == RAW_COMMIT["sha"][:7]
    assert "\n" not in fields["title"]
    assert fields["title"] == "Task 553: first line only"


def test_release_event_fields_maps_all_six_keys():
    fields = release_event_fields(RAW_RELEASE)
    assert fields == {
        "kind": "release",
        "id": "episode-001",
        "title": "Episode 1 — The Founding",
        "url": "https://github.com/thierrypdamiba/orita/releases/tag/episode-001",
        "ts": "2026-07-11T10:58:26Z",
        "author": "thierrypdamiba",
    }


def test_release_event_fields_falls_back_to_tag_name_when_name_is_blank():
    raw = dict(RAW_RELEASE, name="")
    fields = release_event_fields(raw)
    assert fields["title"] == "episode-001"


def test_release_event_fields_falls_back_to_unknown_author():
    raw = dict(RAW_RELEASE, author={})
    fields = release_event_fields(raw)
    assert fields["author"] == "unknown"


def test_release_event_from_json_still_returns_a_githubevent_with_parsed_ts():
    # Byte-identical-behavior proof: _release_event_from_json now builds on
    # release_event_fields internally, but its own public contract (a
    # GithubEvent with a real datetime ts) must be unchanged.
    event = _release_event_from_json(RAW_RELEASE)
    assert event == GithubEvent(
        kind="release",
        id="episode-001",
        title="Episode 1 — The Founding",
        url="https://github.com/thierrypdamiba/orita/releases/tag/episode-001",
        ts=datetime(2026, 7, 11, 10, 58, 26, tzinfo=UTC),
        author="thierrypdamiba",
    )
