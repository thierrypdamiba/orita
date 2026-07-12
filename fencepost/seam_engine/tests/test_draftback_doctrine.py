"""Doctrine tests for draftback.py (ROADMAP.md #17) — same shape of law as

test_connect_doctrine.py and test_onboarding_doctrine.py, aimed at the one
module in this engine that is allowed to write anywhere outside the repo.
Where test_draftback.py proves the *behavior* (forbidden action_names raise,
create_fn is never called when they do), this file proves the *source code
itself* carries no path to a send, independent of any runtime check ever
firing — the strongest form of "a test proves no send path exists in the
code" the done-condition for task 17 asks for.

It also holds the docs to the exact live Arcade tool this module is built to
map onto: `OutlookMail_CreateDraftEmail` (draft-only, the-hand gateway) and
never `OutlookMail_SendEmail` — documented, per ROADMAP.md #17's done
condition, not wired. See draftback.py's module docstring and
DRAFTS/README.md for the mapping itself; these tests just make sure the two
never drift apart, and that SendEmail never sneaks into an actual call site.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from seam_engine import draftback

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DRAFTBACK_SRC = Path(draftback.__file__).read_text(encoding="utf-8")
DRAFTS_README = FENCEPOST_ROOT / "DRAFTS" / "README.md"
SCOPES_MD = FENCEPOST_ROOT / "SCOPES.md"

# The real Arcade action names this module is built to map onto, once the
# Hand connects a live mailbox — see draftback.py's module docstring and
# DRAFTS/README.md. Named here, verbatim, so a drift between doc and code
# fails red instead of silently.
LIVE_DRAFT_ACTION = "OutlookMail_CreateDraftEmail"
LIVE_SEND_ACTION = "OutlookMail_SendEmail"

NEGATION_CUES = ("never", "cannot", "may not", "won't", "not ", "forbidden", "pending")


# --- the source itself contains no call to a forbidden action ---------------


@pytest.mark.parametrize("forbidden", draftback.FORBIDDEN_DELIVERY_ACTIONS)
def test_forbidden_action_is_never_invoked_as_a_call_in_the_source(forbidden: str):
    """A stronger, static version of test_draftback.py's runtime proof: even
    if `_assert_draft_only` were deleted tomorrow, there is still no line in
    this file shaped like `SendEmail(...)` — no call site to find."""
    assert f"{forbidden}(" not in DRAFTBACK_SRC


def test_outlook_send_email_is_never_invoked_as_a_call_in_the_source():
    """The one live tool this module is explicitly documented (not wired) to
    map onto for sending would be OutlookMail_SendEmail. It must never
    appear as a call, full toolkit-qualified name included."""
    assert f"{LIVE_SEND_ACTION}(" not in DRAFTBACK_SRC


def test_create_fn_is_invoked_nowhere_except_the_two_deliver_functions():
    """The injected adapter is called exactly twice in the whole module —
    once per deliver_* function. No other function, including the CLI or
    the preview renderers, ever touches it."""
    assert DRAFTBACK_SRC.count("create_fn(") == 2


@pytest.mark.parametrize(
    "fn", [draftback.deliver_email_draft, draftback.deliver_notion_page]
)
def test_assert_draft_only_runs_strictly_before_create_fn_is_called(fn):
    """Ordering, not just presence: `_assert_draft_only` must appear before
    `create_fn(` in each function's own source, so the gate runs before the
    one call it is guarding, never after."""
    src = inspect.getsource(fn)
    assert "_assert_draft_only(" in src
    assert "create_fn(" in src
    assert src.index("_assert_draft_only(") < src.index("create_fn(")


def test_module_defines_no_function_named_send_or_similar():
    """No `def send`, `def publish`, `def share`, `def post` anywhere in this
    module — the send path isn't just unused, it was never written."""
    banned_defs = ("def send", "def publish", "def share", "def post_")
    lowered = DRAFTBACK_SRC.lower()
    for banned in banned_defs:
        assert banned not in lowered


# --- the OutlookMail mapping is documented, not executed ---------------------


def test_module_docstring_names_the_live_outlook_action_it_maps_onto():
    assert LIVE_DRAFT_ACTION in DRAFTBACK_SRC, (
        f"draftback.py's module docstring must name {LIVE_DRAFT_ACTION!r} as "
        f"the live Arcade action this module is built to map onto (documented, "
        f"not wired) — ROADMAP.md #17"
    )


def test_drafts_readme_documents_the_mapping_and_negates_send():
    assert DRAFTS_README.exists(), "DRAFTS/README.md must exist and document the mapping"
    text = DRAFTS_README.read_text(encoding="utf-8")
    assert LIVE_DRAFT_ACTION in text
    assert LIVE_SEND_ACTION in text
    # Every line naming the send action must negate it — same shape of law
    # test_connect_doctrine.py holds CONNECT.md to for other forbidden tools.
    for line in text.splitlines():
        if LIVE_SEND_ACTION in line:
            lowered = line.lower()
            assert any(cue in lowered for cue in NEGATION_CUES), (
                f"DRAFTS/README.md names {LIVE_SEND_ACTION!r} on a line that "
                f"does not negate it: {line!r}"
            )


def test_scopes_md_addendum_names_the_live_outlook_action():
    text = SCOPES_MD.read_text(encoding="utf-8")
    assert LIVE_DRAFT_ACTION in text, (
        "SCOPES.md's draft-back addendum must name the exact live Arcade "
        f"action ({LIVE_DRAFT_ACTION!r}) draft-back is documented to map onto"
    )


def test_live_draft_action_is_not_itself_a_forbidden_or_send_shaped_name():
    lowered = LIVE_DRAFT_ACTION.lower()
    assert "send" not in lowered
    assert "publish" not in lowered
    assert "share" not in lowered
