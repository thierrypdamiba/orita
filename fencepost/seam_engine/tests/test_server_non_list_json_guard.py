"""Task 362: the non-list-JSON crash class tasks 358/359/361 closed on
RECIPES/*/detector.py, gmail_calendar.py, and scan.py's/combined_scan.py's
own CLI loaders was still open one call-site over -- server.py's two live
MCP tools (`seam_scan`, `combined_scan_preview`), the actual surface a
connecting agent session calls. Both parsed a caller-supplied JSON string
with a bare `json.loads()` and handed the result straight to
`load_x_posts_from_live`/`load_github_events_from_live` (or, for
`combined_scan_preview`, straight to `run_combined_scan`), unmarked. A
non-list payload (a JSON object, number, null, string, or bool) reached
`enumerate()`/`not data` inside those functions and produced a confusing
`TypeError` instead of the campaign's named `ValueError` -- reproduced live
before this fix (`load_github_events_from_live(42)` raised a bare
`'int' object is not iterable'`). Fixed by threading every one of the four
`json.loads()` call sites in `server.py` through `scan._parse_json_list`,
the same guard `scan.py`'s own `_load_json_list` (task 361) already uses,
refactored to share one text-parsing core.

Mirrors `test_server_combined_scan_tool.py`'s/`test_server_github_events_
override.py`'s pattern: every `@app.tool`-decorated function runs through
Arcade's own error-translation wrapper, which wraps a raw `ValueError` in a
`FatalToolError` whose `developer_message` carries the original type and
text -- these tests account for that wrapping rather than expecting the
raw type.
"""
from __future__ import annotations

import json

import pytest
from arcade_core.errors import FatalToolError

from seam_engine.server import combined_scan_preview, seam_scan

_BAD_VALUES = [{"a": 1}, 5, None, "x", True]


@pytest.mark.parametrize("bad_value", _BAD_VALUES)
def test_seam_scan_x_posts_json_rejects_non_list_json(monkeypatch, bad_value):
    with pytest.raises(FatalToolError) as exc_info:
        seam_scan(x_posts_json=json.dumps(bad_value))
    assert "ValueError" in exc_info.value.developer_message
    assert "expected a JSON list" in exc_info.value.developer_message


@pytest.mark.parametrize("bad_value", _BAD_VALUES)
def test_seam_scan_github_events_json_rejects_non_list_json(monkeypatch, bad_value):
    with pytest.raises(FatalToolError) as exc_info:
        seam_scan(github_events_json=json.dumps(bad_value))
    assert "ValueError" in exc_info.value.developer_message
    assert "expected a JSON list" in exc_info.value.developer_message


@pytest.mark.parametrize("bad_value", _BAD_VALUES)
def test_combined_scan_preview_x_posts_json_rejects_non_list_json(monkeypatch, bad_value):
    with pytest.raises(FatalToolError) as exc_info:
        combined_scan_preview(x_posts_json=json.dumps(bad_value))
    assert "ValueError" in exc_info.value.developer_message
    assert "expected a JSON list" in exc_info.value.developer_message


@pytest.mark.parametrize("bad_value", _BAD_VALUES)
def test_combined_scan_preview_github_events_json_rejects_non_list_json(monkeypatch, bad_value):
    with pytest.raises(FatalToolError) as exc_info:
        combined_scan_preview(github_events_json=json.dumps(bad_value))
    assert "ValueError" in exc_info.value.developer_message
    assert "expected a JSON list" in exc_info.value.developer_message
