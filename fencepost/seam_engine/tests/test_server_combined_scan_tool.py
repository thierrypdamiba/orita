"""Tests for `combined_scan_preview` (ROADMAP.md #113): making the real,
tested `combined_scan.py` machinery (task 111) reachable from the live MCP
tool surface, not just `python -m seam_engine.combined_scan`.

Mirrors `test_badge.py`'s introspection pattern: read the ACTUAL registered
`seam_engine.server.app` catalog rather than trusting a docstring, and prove
the new tool's declared behavior is exactly as read-only as every other tool
in this file.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import seam_engine.scan as scan_mod
from seam_engine import badge
from seam_engine.scan import GithubEvent
from seam_engine.server import app, combined_scan_preview

NOW = datetime(2026, 7, 17, 15, 0, tzinfo=timezone.utc)


def _catalog_names() -> list[str]:
    return [mat_tool.definition.name for mat_tool in app._catalog]  # noqa: SLF001


# --- registration: the tool is actually reachable ---------------------------


def test_combined_scan_preview_is_registered_on_the_live_server():
    names = _catalog_names()
    assert "CombinedScanPreview" in names, names


def test_combined_scan_preview_declares_itself_read_only():
    """Same check `badge.audit_server_tools` runs for every tool -- this one
    must pass it too, not just exist."""
    audits = {a.name: a for a in badge.audit_server_tools()}
    assert "CombinedScanPreview" in audits
    audit = audits["CombinedScanPreview"]
    assert audit.ok, audit.violation
    assert audit.read_only is True
    assert audit.destructive is False
    assert audit.operations == ("read",)


def test_badge_stays_green_with_the_new_tool_counted():
    state = badge.compute_badge_state()
    assert state.color == badge.GREEN, state.violations
    names = _catalog_names()
    assert state.tools_checked == len(names)
    assert state.tools_clean == state.tools_checked


# --- behavior: it actually returns combined_scan's real shape ---------------


def test_combined_scan_preview_returns_run_combined_scan_shape(monkeypatch, tmp_path):
    # No live network: same discipline as test_scan.py / test_combined_scan.py.
    events = [
        GithubEvent(
            kind="commit", id="c1", title="milestone: real work",
            url="https://github.com/x/orita/commit/c1", ts=NOW - timedelta(hours=2),
            author="off-by-one",
        ),
    ]
    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda owner, repo, since: events)
    # ROADMAP.md #180's own new prior-milestone check reads the real,
    # ever-growing ledger by default -- isolate this test (about the tool's
    # output shape, not about that check) from live ledger state, same
    # pattern used in test_server_github_events_override.py.
    monkeypatch.setattr(scan_mod, "_unresolved_prior_milestone_evidence", lambda *a, **k: {})

    result = combined_scan_preview(
        owner="thierrypdamiba",
        repo="orita",
        window_hours=24,
        x_posts_json=None,
    )

    # Same top-level shape run_combined_scan/run_scan already return, proven
    # by test_combined_scan.py -- this tool must not reshape or hide it.
    for key in ("generated_at", "repo", "primary_gap", "tail", "excluded",
                "recipe_sources", "recipe_errors"):
        assert key in result, result.keys()
    assert result["repo"] == "thierrypdamiba/orita"


def test_seam_scan_yml_is_untouched_by_this_task():
    """Task 111's boundary is unchanged: `combined_scan.py`/`combined_scan_
    preview` are reachable, but the real daily Action still calls `scan.py`
    alone -- every recipe is fixture-only (MOCK ONLY oath), so folding one
    into the live report would fabricate a gap, not just risk one."""
    from pathlib import Path

    workflow = (Path(__file__).resolve().parents[3] / ".github" / "workflows" / "seam-scan.yml").read_text()
    assert "combined_scan" not in workflow
