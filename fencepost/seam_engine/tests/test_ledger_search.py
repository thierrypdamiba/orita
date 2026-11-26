"""Tests for ledger_search — the Ledger's own "searched a year later" promise.

Built on a synthetic tablet (`tmp_path`, never the real `GAPS/`), the same
isolation `test_streak.py`/`test_audit.py` already use so a test run never
touches the live ledger it would otherwise have to clean up after.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from seam_engine import ledger, ledger_search


def _seal(base: Path, day: str, *, slug: str | None, tail_slugs: list[str]) -> None:
    primary = None
    if slug is not None:
        primary = {
            "slug": slug,
            "headline": f"headline for {slug}",
            "detail": "detail",
            "confidence": 0.85,
            "evidence": ["https://github.com/x/orita/commit/0000001"],
        }
    ledger.append_scan(
        {
            "generated_at": f"{day}T12:00:00+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": primary,
            "tail": [{"slug": t, "confidence": 0.5, "label": "coincidence"} for t in tail_slugs],
            "excluded": [],
        },
        now=datetime.fromisoformat(f"{day}T12:00:00+00:00").replace(tzinfo=timezone.utc),
        base=base,
    )


@pytest.fixture
def seeded_base(tmp_path: Path) -> Path:
    _seal(tmp_path, "2026-01-01", slug="milestone-unannounced", tail_slugs=["coincidence-x"])
    _seal(tmp_path, "2026-01-02", slug=None, tail_slugs=["coincidence-x", "coincidence-y"])
    _seal(tmp_path, "2026-01-05", slug="renewal-unreminded", tail_slugs=["coincidence-y"])
    return tmp_path


# -- matches() -----------------------------------------------------------


def test_matches_date_exact() -> None:
    sealed: dict[str, Any] = {"date": "2026-01-02", "primary_gap": None, "tail": []}
    assert ledger_search.matches(sealed, date="2026-01-02")
    assert not ledger_search.matches(sealed, date="2026-01-01")


def test_matches_since_until_inclusive() -> None:
    sealed: dict[str, Any] = {"date": "2026-01-02", "primary_gap": None, "tail": []}
    assert ledger_search.matches(sealed, since="2026-01-02", until="2026-01-02")
    assert ledger_search.matches(sealed, since="2026-01-01", until="2026-01-05")
    assert not ledger_search.matches(sealed, since="2026-01-03")
    assert not ledger_search.matches(sealed, until="2026-01-01")


def test_matches_slug_checks_primary_and_tail() -> None:
    sealed: dict[str, Any] = {
        "date": "2026-01-01",
        "primary_gap": {"slug": "milestone-unannounced", "headline": "h", "confidence": 0.85},
        "tail": [{"slug": "coincidence-x", "confidence": 0.5, "label": "coincidence"}],
    }
    assert ledger_search.matches(sealed, slug="milestone-unannounced")
    assert ledger_search.matches(sealed, slug="coincidence-x")
    assert not ledger_search.matches(sealed, slug="nothing-here")


def test_matches_no_filters_matches_everything() -> None:
    sealed: dict[str, Any] = {"date": "2026-01-01", "primary_gap": None, "tail": []}
    assert ledger_search.matches(sealed)


def test_matches_filters_combine_with_and() -> None:
    sealed = {
        "date": "2026-01-01",
        "primary_gap": {"slug": "milestone-unannounced", "headline": "h", "confidence": 0.85},
        "tail": [],
    }
    assert not ledger_search.matches(sealed, date="2026-01-01", slug="nothing-here")
    assert ledger_search.matches(sealed, date="2026-01-01", slug="milestone-unannounced")


# -- search() --------------------------------------------------------------


def test_search_filters_against_real_read_records(seeded_base: Path) -> None:
    records = ledger.read_records(seeded_base)
    hits, skipped = ledger_search.search(records, slug="milestone-unannounced")
    assert skipped == 0
    assert len(hits) == 1
    assert hits[0]["sealed"]["date"] == "2026-01-01"


def test_search_tail_only_slug_still_found(seeded_base: Path) -> None:
    records = ledger.read_records(seeded_base)
    hits, _ = ledger_search.search(records, slug="coincidence-y")
    dates = sorted(h["sealed"]["date"] for h in hits)
    assert dates == ["2026-01-02", "2026-01-05"]


def test_search_date_range(seeded_base: Path) -> None:
    records = ledger.read_records(seeded_base)
    hits, _ = ledger_search.search(records, since="2026-01-02", until="2026-01-02")
    assert len(hits) == 1
    assert hits[0]["sealed"]["date"] == "2026-01-02"


def test_search_no_filters_returns_every_record_chain_order(seeded_base: Path) -> None:
    records = ledger.read_records(seeded_base)
    hits, skipped = ledger_search.search(records)
    assert skipped == 0
    assert [h["sealed"]["date"] for h in hits] == ["2026-01-01", "2026-01-02", "2026-01-05"]
    assert [h["seq"] for h in hits] == [0, 1, 2]


def test_search_malformed_record_skipped_not_raised() -> None:
    records = [
        {"_tablet": "x.md", "_malformed": True, "_error": "boom"},
        {
            "seq": 0,
            "prev": "0" * 64,
            "seal": "a" * 64,
            "sealed": {"date": "2026-01-01", "primary_gap": None, "tail": []},
        },
    ]
    hits, skipped = ledger_search.search(records)
    assert skipped == 1
    assert len(hits) == 1


# -- format_hit() ------------------------------------------------------------


def test_format_hit_primary_gap_line(seeded_base: Path) -> None:
    records = ledger.read_records(seeded_base)
    line = ledger_search.format_hit(records[0])
    assert "milestone-unannounced" in line
    assert "2026-01-01" in line
    assert "0.85" in line


def test_format_hit_no_primary_gap_line(seeded_base: Path) -> None:
    records = ledger.read_records(seeded_base)
    line = ledger_search.format_hit(records[1])
    assert "no primary gap cleared the bar" in line
    assert "tail: coincidence-x, coincidence-y" in line


# -- main() CLI ---------------------------------------------------------------


def test_main_prints_matches_and_returns_zero(seeded_base: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = ledger_search.main(["--slug", "renewal-unreminded", "--base", str(seeded_base)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "renewal-unreminded" in out


def test_main_no_matches_says_so(seeded_base: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = ledger_search.main(["--slug", "nothing-ever-matches-this", "--base", str(seeded_base)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "no matching entries sealed" in out


def test_main_rejects_unknown_flag(seeded_base: Path) -> None:
    rc = ledger_search.main(["--bogus", "--base", str(seeded_base)])
    assert rc == 2


def test_main_missing_flag_value_exits() -> None:
    with pytest.raises(SystemExit):
        ledger_search.main(["--slug"])
