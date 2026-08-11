"""Tests for the read-only badge (SCOPES.md oath, clause 4).

The badge exists to catch a real violation, not to decorate a green light.
Every test here either proves the badge stays green while the real server
and the real ledger are clean, or proves it goes red the moment either one
is not — a badge that cannot fail is not a proof, it is a sticker.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from seam_engine import badge, ledger


def _at(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, tzinfo=timezone.utc)


def _scan(*, confidence: float = 0.85, bar: float = 0.70, margin: float = 0.15) -> dict:
    return {
        "generated_at": "t",
        "repo": "x/orita",
        "window_hours": 24,
        "confidence_bar": bar,
        "separation_margin": margin,
        "primary_gap": {
            "slug": "milestone-unannounced",
            "headline": "Milestone shipped, never announced",
            "detail": "3 commits, none echoed.",
            "confidence": confidence,
            "evidence": ["https://github.com/x/orita/commit/0000000"],
            "label": "primary",
        },
        "tail": [{"slug": "coincidence-a", "confidence": 0.55, "label": "coincidence"}],
        "excluded": [],
    }


# --- the live server's own catalog is actually read-only --------------------


def test_every_registered_tool_declares_itself_read_only():
    """The real server.py, introspected as-is. If a future tool lands with a
    write-shaped Behavior, this test (not just the badge) goes red."""
    audits = badge.audit_server_tools()
    assert len(audits) >= 1, "server.py must register at least one tool for this to mean anything"
    for a in audits:
        assert a.ok, a.violation


def test_tool_audit_flags_a_write_shaped_tool_as_a_violation():
    """A tool that is NOT read_only, or IS destructive, or performs a
    non-read operation must be caught — proves the check is not a rubber
    stamp that always says ok."""
    write_tool = badge.ToolAudit(
        name="SendEmail", read_only=False, destructive=True, operations=("write",)
    )
    assert not write_tool.ok
    assert write_tool.violation is not None
    assert "SendEmail" in write_tool.violation


def test_tool_audit_ok_requires_all_three_conditions():
    # read_only True but destructive True still fails
    assert not badge.ToolAudit(
        name="X", read_only=True, destructive=True, operations=("read",)
    ).ok
    # read_only True, destructive False, but a non-read operation still fails
    assert not badge.ToolAudit(
        name="X", read_only=True, destructive=False, operations=("read", "write")
    ).ok
    # all three clean: ok
    assert badge.ToolAudit(
        name="X", read_only=True, destructive=False, operations=("read",)
    ).ok


# --- compute_badge_state: green only when everything real checks out --------


def test_badge_is_green_against_the_real_server_and_an_empty_ledger(tmp_path: Path):
    state = badge.compute_badge_state(ledger_base=tmp_path, now=_at(2026, 7, 12))
    assert state.color == badge.GREEN
    assert state.ok
    assert state.violations == []
    assert state.runs_sealed == 0
    assert "0 writes fired" in state.message


def test_badge_counts_real_sealed_runs_from_the_ledger(tmp_path: Path):
    ledger.append_scan(_scan(), now=_at(2026, 7, 12), base=tmp_path)
    ledger.append_scan(_scan(), now=_at(2026, 7, 13), base=tmp_path)

    state = badge.compute_badge_state(ledger_base=tmp_path, now=_at(2026, 7, 13))
    assert state.color == badge.GREEN
    assert state.runs_sealed == 2
    assert "2 sealed runs" in state.message


def test_badge_singular_run_word(tmp_path: Path):
    ledger.append_scan(_scan(), now=_at(2026, 7, 12), base=tmp_path)
    state = badge.compute_badge_state(ledger_base=tmp_path, now=_at(2026, 7, 12))
    assert "1 sealed run" in state.message
    assert "1 sealed runs" not in state.message


def test_badge_goes_red_when_the_ledger_chain_was_tampered_with(tmp_path: Path):
    ledger.append_scan(_scan(), now=_at(2026, 7, 12), base=tmp_path)
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    tampered = tablet.read_text().replace("milestone-unannounced", "tampered-slug")
    tablet.write_text(tampered)

    state = badge.compute_badge_state(ledger_base=tmp_path, now=_at(2026, 7, 12))
    assert state.color == badge.RED
    assert not state.ok
    assert not state.chain_intact
    assert len(state.violations) > 0
    assert "violation" in state.message


def test_badge_names_every_violation_it_finds(tmp_path: Path):
    ledger.append_scan(_scan(), now=_at(2026, 7, 12), base=tmp_path)
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    tablet.write_text(tablet.read_text().replace("milestone-unannounced", "x"))

    state = badge.compute_badge_state(ledger_base=tmp_path, now=_at(2026, 7, 12))
    assert len(state.violations) == 1
    assert "was edited after it was sealed" in state.violations[0] or "seal does not match" in state.violations[0]


# --- rendering: shields.io endpoint-badge schema -----------------------------


def test_render_badge_json_shape_is_valid_shields_endpoint_schema(tmp_path: Path):
    import json

    state = badge.compute_badge_state(ledger_base=tmp_path, now=_at(2026, 7, 12))
    rendered = badge.render_badge_json(state)
    payload = json.loads(rendered)

    assert payload["schemaVersion"] == 1
    assert payload["label"] == "read-only"
    assert payload["color"] == "brightgreen"
    assert payload["isError"] is False
    assert "0 writes fired" in payload["message"]


def test_render_badge_json_is_red_and_is_error_true_on_violation():
    import json

    state = replace(
        badge.compute_badge_state(),
        color=badge.RED,
        message="1 violation found — see BADGE.json",
        violations=["fake: not read-only-clean"],
    )
    payload = json.loads(badge.render_badge_json(state))
    assert payload["color"] == "red"
    assert payload["isError"] is True


def test_render_never_names_or_ranks_a_person():
    # Ogun's own oath: grade/name/rank NO ONE. The badge proves a property of
    # the system, not a verdict on a god — no author/owner field ever enters it.
    state = badge.compute_badge_state()
    rendered = badge.render_badge_json(state)
    for banned in ("author", "owner", "blame", "grade:"):
        assert banned not in rendered.lower()


# --- CLI: writes the rendering, exits nonzero on a real violation ------------


def test_main_writes_the_badge_file(tmp_path: Path, capsys):
    rc = badge.main(["--base", str(tmp_path), "--write", "--out-base", str(tmp_path)])
    assert rc == 0
    out = badge.badge_path(tmp_path)
    assert out.exists()
    assert '"color": "brightgreen"' in out.read_text()


def test_main_exits_nonzero_when_the_ledger_chain_is_broken(tmp_path: Path):
    ledger.append_scan(_scan(), now=_at(2026, 7, 12), base=tmp_path)
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    tablet.write_text(tablet.read_text().replace("milestone-unannounced", "x"))

    rc = badge.main(["--base", str(tmp_path)])
    assert rc == 1


def test_main_rejects_trailing_base_flag_with_no_value(capsys):
    rc = badge.main(["--base"])
    assert rc == 2
    assert "--base needs a path" in capsys.readouterr().out


def test_main_rejects_trailing_out_base_flag_with_no_value(capsys):
    rc = badge.main(["--out-base"])
    assert rc == 2
    assert "--out-base needs a path" in capsys.readouterr().out


def test_badge_path_defaults_to_fencepost_root():
    p = badge.badge_path()
    assert p.name == "BADGE.json"
    assert p.parent.name == "fencepost"
