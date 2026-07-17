"""ROADMAP.md #115. STRATEGY.md's own line 36 said, since before the seam

engine existed: "Day one it dogfoods on the-hand gateway (Github + X +
Outlook already live = three accounts = a real seam)." Three accounts are
genuinely connected on the-hand gateway, but `scan.py` -- the module that
actually computes the seam -- reads exactly two of them: GitHub and X.
Outlook appears nowhere in `scan.py`; its only real role, per `draftback.py`,
is the write-back destination for the Gap Ledger (`OutlookMail_CreateDraftEmail`,
draft-only). A read side of the seam and a write-back destination are not the
same thing, and counting Outlook toward "three accounts = a real seam" is
exactly the overclaim Ogun's law (STRATEGY.md's own standing law from the
dissents) forbids: "refuse to promise confidence we can't show."

STRATEGY.md's line was fixed to say what the code actually does: the real
seam today is GitHub-vs-X (two accounts); Outlook is connected and live, but
only as the Ledger's write-back destination, not a second read side. These
tests prove the corrected doc claim against the real code, not against
itself -- a future PR that quietly re-widens Outlook into scan.py without
updating this file, or that puts a send action back on draftback.py's
allow-list, fails one of these loudly.
"""
from __future__ import annotations

from pathlib import Path

from seam_engine import draftback, scan

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
ORITA_ROOT = FENCEPOST_ROOT.parent
STRATEGY_MD = ORITA_ROOT / "STRATEGY.md"

SCAN_SRC = Path(scan.__file__).read_text(encoding="utf-8")
DRAFTBACK_SRC = Path(draftback.__file__).read_text(encoding="utf-8")


def test_strategy_no_longer_counts_outlook_as_a_seam_account():
    text = STRATEGY_MD.read_text(encoding="utf-8")
    assert "Outlook already live = three accounts = a real seam" not in text, (
        "STRATEGY.md re-introduced the overclaim: Outlook is a write-back "
        "destination, not a read side of the seam -- see scan.py/draftback.py"
    )


def test_strategy_names_the_real_two_account_seam():
    text = STRATEGY_MD.read_text(encoding="utf-8")
    assert "the real seam today reads only two of them" in text
    assert "GitHub-vs-X reconciliation" in text
    assert "write-back destination" in text


def test_scan_module_never_reads_outlook():
    # scan.py computes the seam. If it ever gains an Outlook read, STRATEGY.md's
    # corrected "two accounts" claim goes stale silently unless this fails.
    assert "outlook" not in SCAN_SRC.lower()


def test_draftback_outlook_role_is_draft_only_never_send():
    # The structural proof that Outlook's only real role is write-back, and
    # that write-back is bounded to drafts -- mirrors test_draftback_doctrine.py's
    # own source-level checks, scoped to just the Outlook action names.
    assert "OutlookMail_CreateDraftEmail" in DRAFTBACK_SRC
    assert "CreateDraftEmail" in draftback.ALLOWED_DELIVERY_ACTIONS
    assert "SendEmail" in draftback.FORBIDDEN_DELIVERY_ACTIONS
