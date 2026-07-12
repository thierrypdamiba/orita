"""Tests for the Fencepost Report — the daily dispatch, not the tablet.

A report names one gap (or none) and never the coincidence tail. These tests
go red if the report starts padding itself with the ranking noise the tablet
is for, or drops the line the whole arc turns on.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from seam_engine import ledger, report


def _sealed(*, primary: bool, recorded: int, tail_n: int = 2) -> dict:
    p = None
    if primary:
        p = {
            "slug": "milestone-unannounced",
            "headline": "Milestone-level work shipped but never reached the sky",
            "detail": "3 milestone commit(s), none echoed in a post.",
            "confidence": 0.85,
            "evidence": [f"https://github.com/x/orita/commit/{i:07d}" for i in range(3)],
        }
    tail = [{"slug": f"coincidence-{i}", "confidence": 0.5, "label": "coincidence"} for i in range(tail_n)]
    return {
        "date": "2026-07-12",
        "generated_at": "2026-07-12T11:38:10+00:00",
        "repo": "x/orita",
        "primary_gap": p,
        "tail": tail,
        "fenceposts_recorded_total": recorded,
    }


def _at(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, tzinfo=timezone.utc)


# --- one gap, never the tail --------------------------------------------------


def test_report_names_the_one_gap():
    text = report.render_report(_sealed(primary=True, recorded=1))
    assert "Milestone-level work" in text
    assert "confidence 0.85" in text


def test_report_never_shows_the_coincidence_tail():
    text = report.render_report(_sealed(primary=True, recorded=1, tail_n=3))
    assert "coincidence-0" not in text
    assert "coincidence-1" not in text


def test_report_caps_evidence_at_three_links():
    text = report.render_report(_sealed(primary=True, recorded=1))
    assert text.count("github.com/x/orita/commit") <= 3


# --- the line and the count are load-bearing ----------------------------------


def test_report_always_carries_the_line():
    assert report.THE_LINE in report.render_report(_sealed(primary=True, recorded=1))
    assert report.THE_LINE in report.render_report(_sealed(primary=False, recorded=0))


def test_wall_reads_one_behind_recorded():
    text = report.render_report(_sealed(primary=True, recorded=3))
    assert "The wall reads 2" in text
    assert "3 fenceposts named" in text


def test_wall_never_goes_negative_at_zero_recorded():
    text = report.render_report(_sealed(primary=False, recorded=0))
    assert "The wall reads 0" in text


# --- an honest quiet day -------------------------------------------------------


def test_no_primary_says_nothing_cleared_the_bar():
    text = report.render_report(_sealed(primary=False, recorded=0))
    assert "Nothing cleared the bar" in text
    assert "milestone-unannounced" not in text


# --- rendered from a live ledger, not a hand-built dict -----------------------


def test_render_latest_reads_the_real_ledger(tmp_path: Path):
    ledger.append_scan(
        {
            "generated_at": "2026-07-12T11:38:10+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "Milestone-level work shipped but never reached the sky",
                "detail": "3 milestone commit(s), none echoed in a post.",
                "confidence": 0.85,
                "evidence": ["https://github.com/x/orita/commit/0000001"],
            },
            "tail": [],
            "excluded": [],
        },
        now=_at(2026, 7, 12),
        base=tmp_path,
    )

    text = report.render_latest(tmp_path)
    assert "# Fencepost Report — 2026-07-12" in text
    assert "Milestone-level work" in text
    assert "1 fencepost named" in text
    assert "The wall reads 0" in text
    assert report.THE_LINE in text


def test_render_latest_on_empty_ledger_raises(tmp_path: Path):
    try:
        report.render_latest(tmp_path)
        assert False, "expected ValueError on an empty ledger"
    except ValueError:
        pass
