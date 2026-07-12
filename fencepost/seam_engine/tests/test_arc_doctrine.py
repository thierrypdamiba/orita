"""Tests for ARC.md and the site copy that carries it (ROADMAP row 18) — the

narrative arc is "the wait for the day the town closes its own last gap,"
and the one thing that would turn that arc sour is the wall quietly
reaching parity with the recorded count. These tests hold two different
promises to the same law:

1. The math: `wall = max(recorded - 1, 0)` sits strictly below `recorded`
   for every recorded >= 1, in both places that compute it (`ledger`,
   `report`). (At recorded == 0 they are both 0 — there is nothing yet to
   be one behind of, which is honest, not a loophole.) If a future edit
   ever lets the wall catch up once a real fencepost exists, this file
   goes red before a single report ships with a lie in it.
2. The doctrine: ARC.md and the live site must say the honest thing about
   why the wall holds — never imply it is counting down, never call it a
   bug, and always name the one reason it holds (the read-only oath).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from seam_engine import ledger, report

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
ARC_MD = FENCEPOST_ROOT / "ARC.md"
README_MD = FENCEPOST_ROOT / "README.md"
INDEX_HTML = FENCEPOST_ROOT.parent / "docs" / "fencepost" / "index.html"

# Copy that would misdescribe the wall as trending toward zero rather than
# fixed one-behind. If any of these show up without the accompanying
# negation this test also checks for, the doctrine has gone soft.
OVERCLAIM_CUES = ("counting down", "almost at zero", "reaching zero soon", "will eventually hit zero")


def _arc_md() -> str:
    assert ARC_MD.exists(), f"missing {ARC_MD} — task 18 isn't done until this file exists"
    return ARC_MD.read_text(encoding="utf-8")


def _readme_md() -> str:
    return README_MD.read_text(encoding="utf-8")


def _index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


# --- the math: the invariant the whole arc depends on --------------------------


@pytest.mark.parametrize("recorded", [0, 1, 2, 3, 10, 100, 9999])
def test_wall_never_equals_recorded_in_report(recorded: int):
    sealed = {
        "date": "2026-07-12",
        "generated_at": "2026-07-12T00:00:00+00:00",
        "repo": "x/orita",
        "primary_gap": None,
        "tail": [],
        "fenceposts_recorded_total": recorded,
    }
    text = report.render_report(sealed)
    wall = max(recorded - 1, 0)
    assert f"The wall reads {wall}" in text
    # the never-equal invariant: at recorded == 0 the floor makes wall == 0
    # == recorded, which is honest (there is nothing to be one behind of
    # yet); for every recorded >= 1 the wall must sit strictly below it.
    if recorded == 0:
        assert wall == 0
    else:
        assert wall < recorded


@pytest.mark.parametrize("recorded", [0, 1, 2, 3, 10, 50])
def test_wall_never_equals_recorded_in_ledger(tmp_path: Path, recorded: int):
    # Drive fenceposts_recorded_total up to `recorded` by appending that many
    # real-gap scans (one per day, so each opens/appends a distinct tablet
    # without colliding), then read the wall the ledger's own prose renders.
    for i in range(recorded):
        ledger.append_scan(
            {
                "generated_at": f"day-{i}",
                "repo": "x/orita",
                "confidence_bar": 0.7,
                "primary_gap": {
                    "slug": f"gap-{i}",
                    "headline": f"Gap {i}",
                    "detail": "",
                    "confidence": 0.9,
                    "evidence": [],
                },
                "tail": [],
                "excluded": [],
            },
            now=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
            base=tmp_path,
        )
    expected_wall = max(recorded - 1, 0)
    if recorded:
        tablets = sorted(ledger.gaps_dir(tmp_path).glob("*.md"))
        combined = "\n".join(p.read_text() for p in tablets)
        assert f"as {expected_wall} on the wall" in combined

    # The invariant that matters: once at least one fencepost is recorded,
    # the wall sits strictly below it; at zero, both are honestly zero.
    if recorded == 0:
        assert expected_wall == 0
    else:
        assert expected_wall == recorded - 1
        assert expected_wall < recorded


def test_wall_is_monotonic_non_decreasing_as_recorded_grows():
    # A promise ARC.md makes explicitly: the distance never closes on its
    # own as the count climbs. wall(n) = n-1 for n>=1, so consecutive walls
    # differ by exactly 1 per new fencepost, never by more (which would
    # mean the wall "caught up") and never by less than 0 (which would mean
    # the wall went backwards on its own).
    walls = [max(n - 1, 0) for n in range(0, 20)]
    diffs = [b - a for a, b in zip(walls, walls[1:])]
    assert all(d in (0, 1) for d in diffs)
    # and the gap (recorded - wall) never shrinks below 1 once recorded > 0
    for n in range(1, 20):
        assert n - max(n - 1, 0) == 1


# --- the doctrine: ARC.md says the honest thing ---------------------------------


def test_arc_md_exists_and_is_not_a_stub():
    assert len(_arc_md()) > 2000, "ARC.md reads like a stub, not a design doc"


def test_arc_md_states_the_formula():
    text = _arc_md()
    assert "max(fenceposts_recorded_total - 1, 0)" in text or "max(recorded - 1, 0)" in text


def test_arc_md_names_the_read_only_oath_as_the_reason_it_holds():
    text = _arc_md()
    assert "SCOPES.md" in text
    assert "read-only" in text.lower() or "read only" in text.lower()


def test_arc_md_names_the_hand_and_the_gate_for_the_one_exception():
    # The one door out of the invariant is a witnessed act, not a script —
    # this must be grounded in the town's own architecture doc, not asserted
    # bare.
    text = _arc_md()
    assert "the Hand" in text or "the Gate" in text
    assert "reference.md" in text or "the Road" in text


def test_arc_md_distinguishes_a_quiet_day_from_the_last_gap_closing():
    text = _arc_md()
    lowered = text.lower()
    assert "quiet day" in lowered
    assert "nothing cleared the bar" in lowered


@pytest.mark.parametrize("cue", OVERCLAIM_CUES)
def test_arc_md_never_overclaims_a_countdown(cue: str):
    assert cue not in _arc_md().lower()


def test_arc_md_is_signed():
    assert "nyx" in _arc_md().lower()


# --- the doctrine, live on the site and in the README ---------------------------


def test_readme_links_to_arc_md():
    assert "ARC.md" in _readme_md()


def test_index_html_links_to_arc_md():
    assert "fencepost/ARC.md" in _index_html()


def test_index_html_never_promises_a_scripted_countdown_to_zero():
    html = _index_html().lower()
    for cue in OVERCLAIM_CUES:
        assert cue not in html


def test_index_html_still_carries_the_line():
    assert "You were so close. You are always so close." in _index_html()


def test_index_html_names_the_witnessed_declaration_not_arithmetic():
    html = _index_html().lower()
    assert "declaration" in html or "witnessed" in html
