"""Tests for draftback.py (ROADMAP.md #17) — the ledger written back to a

place YOU own, as an email-to-self draft or a Notion page, never auto-sent.

Three things must hold, and every test below exists to fail red the moment
one of them slips:
  1. Rendering is pure and deterministic (same sealed record -> same draft).
  2. A draft is never addressed anywhere but the caller's own account (no
     `to` parameter exists anywhere in the public API).
  3. Delivery refuses to run through anything but a draft-only action name,
     and never sends, publishes, shares, or posts — checked BEFORE the
     injected create_fn is ever called, not after.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from seam_engine import draftback

FIXTURE_SEALED_WITH_GAP: dict = {
    "date": "2026-07-12",
    "generated_at": "2026-07-12T09:00:00+00:00",
    "repo": "thierrypdamiba/orita",
    "confidence_bar": 0.70,
    "primary_gap": {
        "slug": "release-never-announced",
        "headline": "Release v0.3 shipped, never announced on X",
        "detail": "GitHub release v0.3 published 2026-07-11T22:00:00Z; no matching post found on @oritatown within 24h.",
        "confidence": 0.91,
        "evidence": ["https://github.com/thierrypdamiba/orita/releases/tag/v0.3"],
    },
    "tail": [
        {"slug": "commit-burst", "confidence": 0.42, "label": "coincidence"},
    ],
    "fenceposts_recorded_total": 4,
}

FIXTURE_SEALED_NO_GAP: dict = {
    "date": "2026-07-13",
    "generated_at": "2026-07-13T09:00:00+00:00",
    "repo": "thierrypdamiba/orita",
    "confidence_bar": 0.70,
    "primary_gap": None,
    "tail": [],
    "fenceposts_recorded_total": 4,
}


# --- rendering is pure and deterministic ------------------------------------


def test_render_email_draft_is_deterministic():
    a = draftback.render_email_draft(FIXTURE_SEALED_WITH_GAP)
    b = draftback.render_email_draft(FIXTURE_SEALED_WITH_GAP)
    assert a == b


def test_render_notion_page_is_deterministic():
    a = draftback.render_notion_page(FIXTURE_SEALED_WITH_GAP)
    b = draftback.render_notion_page(FIXTURE_SEALED_WITH_GAP)
    assert a == b


def test_render_email_draft_carries_the_gap_headline_and_the_line():
    draft = draftback.render_email_draft(FIXTURE_SEALED_WITH_GAP)
    assert "Release v0.3 shipped, never announced on X" in draft.subject
    assert "Release v0.3 shipped, never announced on X" in draft.body
    assert "You were so close. You are always so close." in draft.body


def test_render_email_draft_handles_no_gap_day_honestly():
    draft = draftback.render_email_draft(FIXTURE_SEALED_NO_GAP)
    assert "nothing cleared the bar" in draft.subject.lower()
    assert "Nothing cleared the bar today" in draft.body


def test_render_notion_page_carries_the_gap_and_the_count():
    page = draftback.render_notion_page(FIXTURE_SEALED_WITH_GAP)
    text = "\n".join(b.text for b in page.blocks)
    assert "Release v0.3 shipped, never announced on X" in text
    assert "0.91" in text
    assert "3" in text  # wall reads recorded-1 = 3


def test_render_notion_page_never_shows_the_coincidence_tail():
    # Same doctrine report.py holds: a dispatch is not a ledger. The tail
    # slug must not leak into the delivered artifact.
    page = draftback.render_notion_page(FIXTURE_SEALED_WITH_GAP)
    text = "\n".join(b.text for b in page.blocks)
    assert "commit-burst" not in text


# --- a draft is never addressed anywhere but the caller's own account ------


def test_email_draft_to_is_always_self():
    draft = draftback.render_email_draft(FIXTURE_SEALED_WITH_GAP)
    assert draft.to == draftback.SELF == "self"


def test_render_email_draft_accepts_no_destination_parameter():
    """Structural guarantee, not just behavioral: there is no `to`, `email`,
    `address`, or `recipient` parameter anywhere on the render function, so a
    future caller cannot even attempt to point a draft at someone else."""
    sig = inspect.signature(draftback.render_email_draft)
    forbidden_param_names = {"to", "email", "address", "recipient", "target"}
    assert forbidden_param_names.isdisjoint(sig.parameters.keys())


def test_notion_page_draft_names_no_workspace_or_parent_page():
    """NotionPageDraft carries no workspace/database/parent-page id — only
    title + blocks. A caller's own adapter, authenticated as the caller,
    decides where in their own account it lands."""
    page = draftback.render_notion_page(FIXTURE_SEALED_WITH_GAP)
    field_names = set(page.__dataclass_fields__.keys())
    assert field_names == {"title", "blocks"}


# --- delivery refuses anything but a draft-only action, before calling -----


@pytest.mark.parametrize("forbidden", draftback.FORBIDDEN_DELIVERY_ACTIONS)
def test_deliver_email_draft_refuses_every_forbidden_action(forbidden: str):
    calls = []
    with pytest.raises(draftback.DraftBackViolation):
        draftback.deliver_email_draft(
            FIXTURE_SEALED_WITH_GAP, calls.append, action_name=forbidden
        )
    assert calls == [], f"create_fn must never be called when action_name={forbidden!r} is refused"


@pytest.mark.parametrize("forbidden", draftback.FORBIDDEN_DELIVERY_ACTIONS)
def test_deliver_notion_page_refuses_every_forbidden_action(forbidden: str):
    calls = []
    with pytest.raises(draftback.DraftBackViolation):
        draftback.deliver_notion_page(
            FIXTURE_SEALED_WITH_GAP, calls.append, action_name=forbidden
        )
    assert calls == []


def test_deliver_email_draft_refuses_an_unrecognized_action_name_too():
    """Fails closed: an action name that is neither allowed nor on the named
    deny-list is still refused. Safety must not depend on the deny-list
    being exhaustive."""
    calls = []
    with pytest.raises(draftback.DraftBackViolation):
        draftback.deliver_email_draft(
            FIXTURE_SEALED_WITH_GAP, calls.append, action_name="SomeNewAction"
        )
    assert calls == []


def test_deliver_email_draft_calls_create_fn_exactly_once_for_an_allowed_action():
    calls = []

    def create_fn(draft: draftback.EmailDraft) -> dict:
        calls.append(draft)
        return {"id": "draft-123"}

    result = draftback.deliver_email_draft(FIXTURE_SEALED_WITH_GAP, create_fn)
    assert len(calls) == 1
    assert calls[0].to == "self"
    assert result["channel"] == "email"
    assert result["action"] == "CreateDraftEmail"
    assert result["result"] == {"id": "draft-123"}


def test_deliver_notion_page_calls_create_fn_exactly_once_for_an_allowed_action():
    calls = []

    def create_fn(page: draftback.NotionPageDraft) -> dict:
        calls.append(page)
        return {"id": "page-abc"}

    result = draftback.deliver_notion_page(FIXTURE_SEALED_WITH_GAP, create_fn)
    assert len(calls) == 1
    assert result["channel"] == "notion"
    assert result["action"] == "CreatePage"
    assert result["result"] == {"id": "page-abc"}


def test_allow_list_and_deny_list_never_overlap():
    allowed = set(draftback.ALLOWED_DELIVERY_ACTIONS)
    forbidden = set(draftback.FORBIDDEN_DELIVERY_ACTIONS)
    assert allowed.isdisjoint(forbidden)


def test_allow_list_contains_no_send_publish_share_post_verb():
    banned_substrings = ("send", "publish", "share", "post", "delete", "trash", "modify")
    for action in draftback.ALLOWED_DELIVERY_ACTIONS:
        lowered = action.lower()
        for bad in banned_substrings:
            assert bad not in lowered, f"{action!r} contains banned verb {bad!r}"


# --- the module cannot reach a live account on its own ----------------------


_FORBIDDEN_IMPORTS = ("requests", "httpx", "urllib.request", "socket", "smtplib")


def test_module_imports_no_network_library():
    src = Path(draftback.__file__).read_text(encoding="utf-8")
    for lib in _FORBIDDEN_IMPORTS:
        assert f"import {lib}" not in src, (
            f"draftback.py must never import {lib!r} — it has no credential and "
            f"must not be able to reach a live account without an injected adapter"
        )


def test_deliver_functions_require_an_injected_create_fn():
    """No default create_fn exists — you cannot call deliver_* without
    supplying the live adapter yourself. There is nothing this module can
    do on its own."""
    sig_email = inspect.signature(draftback.deliver_email_draft)
    sig_notion = inspect.signature(draftback.deliver_notion_page)
    assert sig_email.parameters["create_fn"].default is inspect.Parameter.empty
    assert sig_notion.parameters["create_fn"].default is inspect.Parameter.empty


# --- local preview + CLI: dry-run by default, never a live account ---------


def test_render_preview_email_is_marked_as_a_local_preview_only():
    text = draftback.render_preview(FIXTURE_SEALED_WITH_GAP, "email")
    assert "LOCAL PREVIEW ONLY" in text
    assert "No account was written to" in text
    assert "To: self" in text


def test_render_preview_notion_is_marked_as_a_local_preview_only():
    text = draftback.render_preview(FIXTURE_SEALED_WITH_GAP, "notion")
    assert "LOCAL PREVIEW ONLY" in text
    assert "No workspace was written to" in text


def test_render_preview_rejects_unknown_channel():
    with pytest.raises(ValueError):
        draftback.render_preview(FIXTURE_SEALED_WITH_GAP, "slack")


def test_cli_without_write_does_not_touch_disk(tmp_path, capsys):
    scan_path = tmp_path / "sealed.json"
    scan_path.write_text(json.dumps(FIXTURE_SEALED_WITH_GAP))
    rc = draftback.main(["email", str(scan_path), "--base", str(tmp_path)])
    assert rc == 0
    assert not (tmp_path / "DRAFTS").exists()
    out = capsys.readouterr().out
    assert "LOCAL PREVIEW ONLY" in out


def test_cli_with_write_writes_exactly_the_render_preview_output(tmp_path, capsys):
    scan_path = tmp_path / "sealed.json"
    scan_path.write_text(json.dumps(FIXTURE_SEALED_WITH_GAP))
    rc = draftback.main(["email", str(scan_path), "--write", "--base", str(tmp_path)])
    assert rc == 0

    written = tmp_path / "DRAFTS" / "2026-07-12-email.md"
    assert written.exists()
    assert written.read_text(encoding="utf-8") == draftback.render_preview(FIXTURE_SEALED_WITH_GAP, "email")


def test_cli_notion_write_writes_a_notion_preview(tmp_path):
    scan_path = tmp_path / "sealed.json"
    scan_path.write_text(json.dumps(FIXTURE_SEALED_WITH_GAP))
    rc = draftback.main(["notion", str(scan_path), "--write", "--base", str(tmp_path)])
    assert rc == 0
    written = tmp_path / "DRAFTS" / "2026-07-12-notion.md"
    assert written.exists()
    assert "LOCAL PREVIEW ONLY" in written.read_text(encoding="utf-8")


def test_cli_rejects_unknown_channel_argument():
    rc = draftback.main(["slack"])
    assert rc == 2


def test_cli_reads_from_stdin_sentinel_without_crashing(tmp_path, monkeypatch, capsys):
    import io
    import sys

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(FIXTURE_SEALED_NO_GAP)))
    rc = draftback.main(["email", "-"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "nothing cleared the bar" in out.lower()
