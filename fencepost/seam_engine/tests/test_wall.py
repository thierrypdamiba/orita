"""Tests for the wall's law enforcement (ROADMAP.md #21).

Two things are proven here that `test_arc_doctrine.py` (task 18) did not:

1. `wall_for` is a *guard*, not just a formula — it actively refuses to
   return a number that would let the counter reach `recorded` instead of
   sitting strictly one behind it, for every input, not merely the ones
   task 18 happened to parametrize.
2. `ledger.py` and `report.py` no longer each carry their own copy of the
   arithmetic — they both import and call `wall_for`. This is checked
   structurally (source-grep), on iron: the day either file goes back to
   inlining `max(recorded - 1, 0)` instead of calling the shared,
   guarded function, this test goes red before a report can ship computed
   two different ways in two different places again.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from seam_engine import draftback, report
from seam_engine.wall import TEASER_LINE, WallInvariantViolation, wall_for

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
LEDGER_SRC = FENCEPOST_ROOT / "seam_engine" / "src" / "seam_engine" / "ledger.py"
REPORT_SRC = FENCEPOST_ROOT / "seam_engine" / "src" / "seam_engine" / "report.py"
DRAFTBACK_SRC = FENCEPOST_ROOT / "seam_engine" / "src" / "seam_engine" / "draftback.py"


# --- the guard: wall_for never lets the wall reach parity -----------------


@pytest.mark.parametrize("recorded", [0, 1, 2, 3, 5, 10, 100, 1000, 999999])
def test_wall_for_never_reaches_recorded(recorded: int):
    wall = wall_for(recorded)
    if recorded == 0:
        assert wall == 0
    else:
        assert wall == recorded - 1
        assert wall < recorded


def test_wall_for_matches_max_formula_exactly():
    for recorded in range(0, 50):
        assert wall_for(recorded) == max(recorded - 1, 0)


def test_wall_for_rejects_a_negative_recorded():
    # The Ledger's own count can only grow or hold, never go negative
    # (ARC.md) — a negative input can only mean an upstream bug, and
    # wall_for refuses to guess at an answer for it.
    with pytest.raises(WallInvariantViolation):
        wall_for(-1)


def test_wall_invariant_violation_is_a_runtime_error():
    # So a violation is a loud, uncaught crash by default (CI-visible),
    # never something a broad `except Exception` upstream could swallow
    # into a silently wrong number reaching a report.
    assert issubclass(WallInvariantViolation, RuntimeError)


# --- structural proof: ledger.py and report.py call the one function ------


def test_ledger_does_not_inline_the_wall_formula():
    src = LEDGER_SRC.read_text(encoding="utf-8")
    assert "max(recorded - 1, 0)" not in src
    assert "wall_for(recorded)" in src
    assert "from seam_engine.wall import wall_for" in src


def test_report_does_not_inline_the_wall_formula():
    src = REPORT_SRC.read_text(encoding="utf-8")
    assert "max(recorded - 1, 0)" not in src
    assert "wall_for(recorded)" in src
    assert "from seam_engine.wall import" in src


def test_draftback_does_not_inline_the_wall_formula():
    # The third caller wall.py's own docstring warned about (ROADMAP.md #95):
    # render_notion_page (task 17) predates wall_for (task 21) and kept its
    # own inlined copy of the formula until now.
    src = DRAFTBACK_SRC.read_text(encoding="utf-8")
    assert "max(recorded - 1, 0)" not in src
    assert "wall_for(recorded)" in src
    assert "from seam_engine.wall import wall_for" in src


def test_notion_page_wall_matches_wall_for_for_the_same_recorded():
    # Same regression test_ledger_and_report_produce_the_same_wall_for_the_
    # same_recorded already runs for ledger/report, now covering the third
    # caller: the rendered Notion draft must never disagree with wall_for.
    for recorded in [0, 1, 2, 7, 40]:
        sealed = {
            "date": "2026-07-12",
            "generated_at": "2026-07-12T00:00:00+00:00",
            "repo": "x/orita",
            "primary_gap": None,
            "fenceposts_recorded_total": recorded,
        }
        page = draftback.render_notion_page(sealed)
        combined = "\n".join(b.text for b in page.blocks)
        expected = wall_for(recorded)
        assert f"The wall reads {expected}" in combined


def test_ledger_and_report_produce_the_same_wall_for_the_same_recorded():
    # The exact regression ARC.md warned about: "two places that must never
    # disagree." Proven here by calling both real code paths, not by
    # re-deriving the formula a third time.
    for recorded in [0, 1, 2, 7, 40]:
        sealed = {
            "date": "2026-07-12",
            "generated_at": "2026-07-12T00:00:00+00:00",
            "repo": "x/orita",
            "primary_gap": None,
            "tail": [],
            "fenceposts_recorded_total": recorded,
        }
        report_text = report.render_report(sealed)
        report_wall = int(
            [line for line in report_text.splitlines() if "The wall reads" in line][0]
            .rsplit("The wall reads", 1)[1]
            .strip()
            .rstrip(".")
        )
        assert report_wall == wall_for(recorded)


# --- the teaser: rendered, honest, never a date ----------------------------


def test_teaser_line_names_no_date():
    # A handful of cheap lexical smoke checks against the exact overclaim
    # ARC.md forbids (test_arc_doctrine.py's OVERCLAIM_CUES) plus a check
    # that nothing that looks like a calendar date sneaks in.
    lowered = TEASER_LINE.lower()
    for cue in ("counting down", "almost at zero", "reaching zero soon", "will eventually hit zero"):
        assert cue not in lowered
    import re

    assert not re.search(r"\b\d{4}-\d{2}-\d{2}\b", TEASER_LINE)


def test_teaser_line_names_a_witnessed_declaration():
    lowered = TEASER_LINE.lower()
    assert "declaration" in lowered or "witnessed" in lowered


def test_render_report_carries_the_teaser_line():
    sealed = {
        "date": "2026-07-12",
        "generated_at": "2026-07-12T00:00:00+00:00",
        "repo": "x/orita",
        "primary_gap": None,
        "tail": [],
        "fenceposts_recorded_total": 3,
    }
    text = report.render_report(sealed)
    assert TEASER_LINE in text


# --- the site: the teaser actually renders ---------------------------------


def test_index_html_carries_the_teaser_widget():
    index = (FENCEPOST_ROOT.parent / "docs" / "fencepost" / "index.html").read_text(
        encoding="utf-8"
    )
    assert 'id="teaser"' in index
    assert "the day it closes" in index.lower()
    assert "not declared" in index.lower()


def test_teaser_extraction_regex_matches_teaser_line_exactly():
    # ARC.md's task-21 paragraph (corrected by task 126) claims the site's
    # #teaser div is fetched live off the same report that carries
    # TEASER_LINE verbatim, not a hand-typed copy that could drift from it.
    # Prove the extraction regex actually captures TEASER_LINE -- not a
    # substring, not a paraphrase -- out of a REAL render_report() output,
    # the same generator the live site fetches from. A regex that merely
    # looked plausible would not be proof; this locks it to the real thing.
    import re

    sealed = {
        "date": "2026-07-12",
        "generated_at": "2026-07-12T00:00:00+00:00",
        "repo": "x/orita",
        "primary_gap": None,
        "tail": [],
        "fenceposts_recorded_total": 3,
    }
    text = report.render_report(sealed)
    match = re.search(r"The day it closes:[^\n]*", text)
    assert match is not None
    assert match.group(0) == TEASER_LINE


def test_index_html_extracts_teaser_from_the_same_fetch_that_updates_wall():
    # Task 126: the teaser must not be a second, disconnected fetch/handler
    # that could itself drift out of step with the wall counter -- it has
    # to live inside the SAME .then() block that already regexes "wall
    # reads N" out of the fetched report, so both are always read off the
    # one live document, in the same pass, or neither is.
    index = (FENCEPOST_ROOT.parent / "docs" / "fencepost" / "index.html").read_text(
        encoding="utf-8"
    )
    wall_idx = index.index("getElementById('wall')")
    teaser_write_idx = index.index("getElementById('teaser')", wall_idx)
    # Nothing that starts a new fetch handler sits between the two.
    between = index[wall_idx:teaser_write_idx]
    assert ".then(function" not in between
    assert "The day it closes:" in index
    assert "esc(tm[0])" in index


def test_style_css_styles_the_teaser():
    css = (FENCEPOST_ROOT.parent / "docs" / "style.css").read_text(encoding="utf-8")
    assert ".counter .teaser" in css
