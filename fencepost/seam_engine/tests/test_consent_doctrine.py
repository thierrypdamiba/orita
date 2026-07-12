"""Doctrine tests: the public-facing consent artifact must never drift from

the code that actually gates on it. `.github/ISSUE_TEMPLATE/point-fencepost.md`
is where a real human types their scope confirm; `consent.REQUIRED_SCOPES` is
what `enforce_consent_gate` actually checks it against. If the table on the
issue template ever falls out of sync with the code, a human could type a
"correct" confirm straight off the template and still get blocked — the
worst possible failure for a consent flow, since it makes the gate look
broken rather than working as sworn. This file fails red the day that
happens, the same discipline `test_connect_doctrine.py` holds
`READ_ONLY_CAPABILITIES` to.
"""
from __future__ import annotations

from pathlib import Path

from seam_engine.consent import REQUIRED_SCOPES

REPO_ROOT = Path(__file__).resolve().parents[3]  # .../orita
TEMPLATE = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "point-fencepost.md"


def _template_text() -> str:
    assert TEMPLATE.exists(), f"missing {TEMPLATE} — task 9's intent-forcing template must still exist"
    return TEMPLATE.read_text(encoding="utf-8")


def test_template_file_exists():
    _template_text()


def test_template_names_a_public_issue_and_an_explicit_scope_confirm():
    text = _template_text().lower()
    assert "second lock" in text or "scope confirm" in text
    assert "verbatim" in text


def test_template_points_at_the_real_consent_module():
    text = _template_text()
    assert "seam_engine/src/seam_engine/consent.py" in text
    assert "enforce_consent_gate" in text


def test_every_required_scope_name_appears_verbatim_on_the_template():
    text = _template_text()
    for toolkit, scopes in REQUIRED_SCOPES.items():
        for scope in scopes:
            assert scope in text, (
                f"{toolkit}/{scope} is in consent.REQUIRED_SCOPES but does not appear "
                "verbatim on point-fencepost.md — the template has drifted from the gate"
            )


def test_template_never_asks_the_human_to_confirm_a_write_scope():
    text = _template_text()
    write_prefixes = ("Create", "Update", "Delete", "Send", "Post", "Reply", "Merge", "Modify", "Trash")
    # Only check inside the scope-confirm table rows (backtick-quoted lists),
    # so prose sentences that legitimately name a forbidden verb ("cannot
    # write, send, delete") to warn about it don't false-positive here.
    for line in text.splitlines():
        if not (line.strip().startswith("|") and "`" in line):
            continue
        for cell in line.split("`")[1::2]:
            for name in cell.split(","):
                name = name.strip()
                if not name:
                    continue
                assert not name.startswith(write_prefixes), (
                    f"{name!r} on the scope-confirm table looks write-capable"
                )
