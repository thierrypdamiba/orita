"""Tests for the Gap Ledger — the append-only, hash-chained tablet.

Every property the ledger promises has a test that goes red if the promise
breaks: it seals, it chains, it only ever appends, and it catches a tampered
tablet. A test that cannot fail is a broken oath.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from seam_engine import ledger


def _scan(*, primary: bool, generated_at: str, tail_n: int = 2) -> dict:
    p = None
    if primary:
        p = {
            "slug": "milestone-unannounced",
            "headline": "Milestone-level work shipped but never reached the sky",
            "detail": "3 milestone commit(s), none echoed in a post.",
            "confidence": 0.85,
            "evidence": [f"https://github.com/x/orita/commit/{i:07d}" for i in range(3)],
            "label": "primary",
        }
    tail = [
        {"slug": f"coincidence-{i}", "confidence": 0.5 - 0.01 * i, "label": "coincidence"}
        for i in range(tail_n)
    ]
    return {
        "generated_at": generated_at,
        "repo": "x/orita",
        "window_hours": 24,
        "confidence_bar": 0.7,
        "separation_margin": 0.15,
        "primary_gap": p,
        "tail": tail,
        "excluded": [{"slug": "release-old"}],
    }


def _at(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, tzinfo=timezone.utc)


# --- it writes a readable, dated tablet --------------------------------------


def test_first_append_creates_dated_tablet(tmp_path: Path):
    scan = _scan(primary=True, generated_at="2026-07-12T11:38:10+00:00")
    tablet = ledger.append_scan(scan, now=_at(2026, 7, 12), base=tmp_path)

    assert tablet == ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    assert tablet.exists()
    text = tablet.read_text()
    assert "# Gap Ledger — 2026-07-12" in text
    assert "## Entry 0" in text
    assert "Milestone-level work" in text
    assert "Tablet sealed." in text
    # the typed record is embedded and parseable
    assert "<!-- typed-record -->" in text


def test_readable_evidence_links_are_rendered(tmp_path: Path):
    scan = _scan(primary=True, generated_at="2026-07-12T11:38:10+00:00")
    tablet = ledger.append_scan(scan, now=_at(2026, 7, 12), base=tmp_path)
    text = tablet.read_text()
    assert "https://github.com/x/orita/commit/0000000" in text
    assert "Evidence:" in text


# --- the chain ---------------------------------------------------------------


def test_first_entry_chains_from_genesis(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="t"), now=_at(2026, 7, 12), base=tmp_path)
    recs = ledger.read_records(tmp_path)
    assert len(recs) == 1
    assert recs[0]["prev"] == ledger.GENESIS
    assert recs[0]["seq"] == 0
    assert ledger.verify(tmp_path) == []


def test_second_entry_same_day_appends_and_chains(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="t1"), now=_at(2026, 7, 12, 9), base=tmp_path)
    before = (ledger.gaps_dir(tmp_path) / "2026-07-12.md").read_text()

    ledger.append_scan(_scan(primary=False, generated_at="t2"), now=_at(2026, 7, 12, 18), base=tmp_path)
    after = (ledger.gaps_dir(tmp_path) / "2026-07-12.md").read_text()

    # append-only: the earlier bytes are untouched, the file only grew
    assert after.startswith(before)
    assert len(after) > len(before)

    recs = ledger.read_records(tmp_path)
    assert [r["seq"] for r in recs] == [0, 1]
    assert recs[1]["prev"] == recs[0]["seal"]  # entry 1 chains from entry 0
    assert ledger.verify(tmp_path) == []


def test_new_day_opens_new_tablet_chained_to_prior(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="d1"), now=_at(2026, 7, 12), base=tmp_path)
    ledger.append_scan(_scan(primary=True, generated_at="d2"), now=_at(2026, 7, 13), base=tmp_path)

    files = {p.name for p in ledger.gaps_dir(tmp_path).glob("*.md")}
    assert files == {"2026-07-12.md", "2026-07-13.md"}

    recs = ledger.read_records(tmp_path)
    assert len(recs) == 2
    # the second tablet's first entry chains from the first tablet's last seal
    assert recs[1]["prev"] == recs[0]["seal"]
    # the new tablet header records where it chains from
    day2 = (ledger.gaps_dir(tmp_path) / "2026-07-13.md").read_text()
    assert recs[0]["seal"][:12] in day2
    assert ledger.verify(tmp_path) == []


# --- tamper-evidence: the reason a ledger exists ------------------------------


def test_editing_a_sealed_record_is_caught(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="honest"), now=_at(2026, 7, 12), base=tmp_path)
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    # forge the confidence inside the sealed record without re-sealing
    tablet.write_text(tablet.read_text().replace('"confidence": 0.85', '"confidence": 0.99'))

    problems = ledger.verify(tmp_path)
    assert problems, "a forged record must be caught"
    assert any("seal does not match" in p for p in problems)


def test_deleting_an_entry_breaks_the_chain(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="e0"), now=_at(2026, 7, 12, 9), base=tmp_path)
    ledger.append_scan(_scan(primary=True, generated_at="e1"), now=_at(2026, 7, 12, 18), base=tmp_path)
    assert ledger.verify(tmp_path) == []

    # amputate the second entry's typed record's prev-link
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    recs = ledger.read_records(tmp_path)
    good_prev = recs[1]["prev"]
    tablet.write_text(tablet.read_text().replace(f'"prev": "{good_prev}"', f'"prev": "{ledger.GENESIS}"', 1))

    problems = ledger.verify(tmp_path)
    assert any("prev-link broken" in p or "seal does not match" in p for p in problems)


# --- the count is honest -----------------------------------------------------


def test_count_only_advances_on_a_real_fencepost(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="g1"), now=_at(2026, 7, 12), base=tmp_path)
    ledger.append_scan(_scan(primary=False, generated_at="held"), now=_at(2026, 7, 13), base=tmp_path)
    ledger.append_scan(_scan(primary=True, generated_at="g2"), now=_at(2026, 7, 14), base=tmp_path)

    recs = ledger.read_records(tmp_path)
    totals = [r["sealed"]["fenceposts_recorded_total"] for r in recs]
    assert totals == [1, 1, 2]  # the empty day does not inflate the count


def test_no_primary_records_the_seam_held(tmp_path: Path):
    tablet = ledger.append_scan(_scan(primary=False, generated_at="q"), now=_at(2026, 7, 12), base=tmp_path)
    text = tablet.read_text()
    assert "None cleared the bar" in text
    assert "Recorded." in text
    recs = ledger.read_records(tmp_path)
    assert recs[0]["sealed"]["primary_gap"] is None
    assert recs[0]["sealed"]["fenceposts_recorded_total"] == 0


# --- last_seal --------------------------------------------------------------


def test_last_seal_is_genesis_on_empty_ledger(tmp_path: Path):
    assert ledger.last_seal(tmp_path) == ledger.GENESIS
