"""Tests for consent.py — the double-checked consent gate (ROADMAP #20).

DONE WHEN: "the consent gate blocks all reads until the human confirms
scopes." Every test in the first section proves the block by construction —
patching the fixture loaders to explode if called, then showing the gate
raises `ConsentRequiredError` *before* either loader runs. The remaining
sections exercise the two checks individually (public issue, scope confirm)
and the pure-decision doctrine (no I/O in this module, same shape as
`gateway.py`'s doctrine tests).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from seam_engine.consent import (
    REQUIRED_SCOPES,
    ConsentRecord,
    ConsentRequiredError,
    check_public_issue,
    check_scope_confirm,
    enforce_consent_for_toolkits,
    enforce_consent_gate,
)

GOOD_ISSUE = "https://github.com/thierrypdamiba/orita/issues/42"


def _record(
    toolkit: str = "gmail",
    *,
    issue_url: str = GOOD_ISSUE,
    scopes: frozenset[str] | None = None,
    human: str = "a-real-human",
) -> ConsentRecord:
    return ConsentRecord(
        human=human,
        issue_url=issue_url,
        toolkit=toolkit,
        confirmed_scopes=scopes if scopes is not None else REQUIRED_SCOPES[toolkit],
    )


# --- DONE WHEN: the gate blocks ALL reads until both checks pass -----------


def test_no_consent_record_blocks_the_read_before_it_starts(monkeypatch):
    from seam_engine import gmail_calendar as mod

    def _explode(*_args, **_kwargs):
        raise AssertionError("a loader ran — the gate did not block the read")

    monkeypatch.setattr(mod, "load_gmail_fixture", _explode)
    monkeypatch.setattr(mod, "load_calendar_fixture", _explode)

    with pytest.raises(ConsentRequiredError):
        mod.run_consented_gmail_calendar_scan({})


def test_consent_for_only_one_of_two_toolkits_still_blocks_the_read(monkeypatch):
    # Gmail confirmed, Calendar never confirmed — the whole read stays shut,
    # since a half-consented Gmail-vs-Calendar scan cannot honestly read
    # either side (a Gmail-only read with no Calendar consent would still be
    # reading toward a comparison the human never confirmed).
    from seam_engine import gmail_calendar as mod

    def _explode(*_args, **_kwargs):
        raise AssertionError("a loader ran — the gate did not block the read")

    monkeypatch.setattr(mod, "load_gmail_fixture", _explode)
    monkeypatch.setattr(mod, "load_calendar_fixture", _explode)

    consent = {"gmail": _record("gmail")}
    with pytest.raises(ConsentRequiredError):
        mod.run_consented_gmail_calendar_scan(consent)


def test_both_toolkits_consented_lets_the_gated_scan_run():
    from seam_engine.gmail_calendar import run_consented_gmail_calendar_scan

    consent = {
        "gmail": _record("gmail"),
        "google_calendar": _record("google_calendar"),
    }
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    result = run_consented_gmail_calendar_scan(consent, now=now)
    assert result["source"] == "fixture"
    assert result["primary_gap"] is not None


def test_a_bad_issue_url_blocks_even_with_perfect_scopes(monkeypatch):
    from seam_engine import gmail_calendar as mod

    def _explode(*_args, **_kwargs):
        raise AssertionError("a loader ran — the gate did not block the read")

    monkeypatch.setattr(mod, "load_gmail_fixture", _explode)
    monkeypatch.setattr(mod, "load_calendar_fixture", _explode)

    consent = {
        "gmail": _record("gmail", issue_url="I promise I opened one, trust me"),
        "google_calendar": _record("google_calendar"),
    }
    with pytest.raises(ConsentRequiredError, match="public issue"):
        mod.run_consented_gmail_calendar_scan(consent)


def test_a_short_scope_confirm_blocks_even_with_a_good_issue(monkeypatch):
    from seam_engine import gmail_calendar as mod

    def _explode(*_args, **_kwargs):
        raise AssertionError("a loader ran — the gate did not block the read")

    monkeypatch.setattr(mod, "load_gmail_fixture", _explode)
    monkeypatch.setattr(mod, "load_calendar_fixture", _explode)

    consent = {
        "gmail": _record("gmail", scopes=frozenset({"ListEmails"})),  # missing GetEmail, SearchThreads
        "google_calendar": _record("google_calendar"),
    }
    with pytest.raises(ConsentRequiredError, match="scope confirm"):
        mod.run_consented_gmail_calendar_scan(consent)


# --- enforce_consent_gate: the single-toolkit gate --------------------------


def test_none_raises_consent_required():
    with pytest.raises(ConsentRequiredError):
        enforce_consent_gate(None, toolkit="gmail")


def test_a_valid_record_passes_and_is_returned():
    record = _record("gmail")
    assert enforce_consent_gate(record, toolkit="gmail") is record


def test_a_record_for_a_different_toolkit_does_not_open_this_door():
    record = _record("gmail")
    with pytest.raises(ConsentRequiredError):
        enforce_consent_gate(record, toolkit="google_calendar")


def test_an_unknown_toolkit_can_never_pass():
    record = ConsentRecord(
        human="a-real-human",
        issue_url=GOOD_ISSUE,
        toolkit="slack",
        confirmed_scopes=frozenset({"ListChannels"}),
    )
    with pytest.raises(ConsentRequiredError):
        enforce_consent_gate(record, toolkit="slack")


def test_enforce_consent_for_toolkits_gates_every_named_toolkit():
    consent = {
        "gmail": _record("gmail"),
        "google_calendar": _record("google_calendar"),
    }
    cleared = enforce_consent_for_toolkits(consent, toolkits=("gmail", "google_calendar"))
    assert set(cleared) == {"gmail", "google_calendar"}


def test_enforce_consent_for_toolkits_stops_at_the_first_missing_one():
    with pytest.raises(ConsentRequiredError):
        enforce_consent_for_toolkits({}, toolkits=("gmail", "google_calendar"))


# --- check_public_issue: check 1 of 2 ----------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        GOOD_ISSUE,
        "https://github.com/some-fork/fencepost/issues/1",
        "https://github.com/a/b/issues/999999",
    ],
)
def test_real_issue_urls_pass_check_one(url: str):
    ok, _ = check_public_issue(_record(issue_url=url))
    assert ok


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url at all",
        "https://github.com/owner/repo/pull/1",  # a PR is not an issue
        "https://example.com/issues/1",  # not github.com
        "github.com/owner/repo/issues/1",  # missing scheme
        "https://github.com/owner/repo/issues/",  # no number
    ],
)
def test_fake_or_private_issue_urls_fail_check_one(url: str):
    ok, why = check_public_issue(_record(issue_url=url))
    assert not ok
    assert why


# --- check_scope_confirm: check 2 of 2 ---------------------------------------


def test_exact_scope_match_passes_check_two():
    ok, _ = check_scope_confirm(_record("gmail"))
    assert ok


def test_missing_a_scope_fails_check_two():
    record = _record("gmail", scopes=frozenset({"ListEmails", "GetEmail"}))  # missing SearchThreads
    ok, why = check_scope_confirm(record)
    assert not ok
    assert "SearchThreads" in why


def test_an_extra_unlisted_scope_fails_check_two_even_if_read_only():
    extra = REQUIRED_SCOPES["gmail"] | {"ListDrafts"}  # not asked for; still rejected verbatim
    record = _record("gmail", scopes=extra)
    ok, why = check_scope_confirm(record)
    assert not ok
    assert "ListDrafts" in why


def test_empty_scope_confirm_fails_check_two():
    ok, _ = check_scope_confirm(_record("gmail", scopes=frozenset()))
    assert not ok


@pytest.mark.parametrize("toolkit", sorted(REQUIRED_SCOPES))
def test_every_documented_toolkit_has_a_passable_exact_confirm(toolkit: str):
    ok, _ = check_scope_confirm(_record(toolkit))
    assert ok


# --- doctrine: this module is pure judgment, no I/O of its own --------------


def test_module_performs_no_io_of_its_own():
    from seam_engine import consent as mod

    text = Path(mod.__file__).read_text(encoding="utf-8")
    for banned in ("import httpx", "import requests", "open(", "Path(", ".read_text(", "json.load"):
        assert banned not in text, (
            f"{banned!r} appears in consent.py — the gate must stay pure "
            "judgment, never a read of its own"
        )


def test_module_never_names_a_write_capable_tool():
    from seam_engine import consent as mod

    text = Path(mod.__file__).read_text(encoding="utf-8")
    for bad in ("SendEmail", "CreateDraft", "DeleteEvent", "UpdateEvent", "PostTweet"):
        assert bad not in text, f"{bad} appears in consent.py — a write-capable tool name in a gate module"


def test_required_scopes_never_contains_a_write_verb_prefix():
    write_prefixes = ("Create", "Update", "Delete", "Send", "Post", "Reply", "Merge", "Modify", "Trash")
    for toolkit, scopes in REQUIRED_SCOPES.items():
        for scope in scopes:
            assert not scope.startswith(write_prefixes), (
                f"{toolkit}/{scope} looks write-capable — REQUIRED_SCOPES must stay read-only"
            )
