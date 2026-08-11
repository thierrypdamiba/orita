"""Tests for the serialization mechanics (ROADMAP.md #19) — turning daily
Reports into a series.

Two invariants, both load-bearing:

1. `episode_number`/`consecutive_days` are honest counts of what the Ledger
   actually sealed — a day with no tablet cannot be papered over, and a
   missed day really does reset the streak to zero the day after the gap.
   The "seven consecutive daily reports posted" promise (ROADMAP.md #19) is
   only ever true when the tablets themselves back it; these tests prove the
   arithmetic cannot be faked into `True` any other way.
2. `report.render_report`'s new episode line and `CONNECT_YOUR_OWN` ad are
   additive and never break the report's existing promises: the single
   "Your move" line stays singular, the ad never begs for a star, and the ad
   never claims Fencepost performed an action on the reader's behalf.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from seam_engine import ledger, report, streak

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
README_MD = FENCEPOST_ROOT / "README.md"
ROADMAP_MD = FENCEPOST_ROOT.parent / "ROADMAP.md"
SEAM_SCAN_YML = FENCEPOST_ROOT.parent / ".github" / "workflows" / "seam-scan.yml"


def _append_day(base: Path, day: date, *, primary: bool = True) -> None:
    p = None
    if primary:
        p = {
            "slug": "milestone-unannounced",
            "headline": "Milestone-level work shipped but never reached the sky",
            "detail": "1 milestone commit, none echoed in a post.",
            "confidence": 0.85,
            "evidence": ["https://github.com/x/orita/commit/0000001"],
        }
    ledger.append_scan(
        {
            "generated_at": f"{day.isoformat()}T12:00:00+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": p,
            "tail": [],
            "excluded": [],
        },
        now=datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc),
        base=base,
    )


# --- episode_number: counts installments, not gaps -----------------------------


def test_episode_number_zero_on_an_empty_ledger(tmp_path: Path):
    assert streak.episode_number(tmp_path) == 0


def test_episode_number_counts_quiet_days_too(tmp_path: Path):
    # A quiet day (no primary gap) still opens a tablet — report.py's own
    # honest-quiet-day branch proves a report still ships that day. The
    # episode count must agree: it counts days shipped, not gaps found.
    _append_day(tmp_path, date(2026, 7, 1), primary=True)
    _append_day(tmp_path, date(2026, 7, 2), primary=False)
    _append_day(tmp_path, date(2026, 7, 3), primary=False)
    assert streak.episode_number(tmp_path) == 3


def test_episode_number_matches_number_of_tablet_files(tmp_path: Path):
    for i in range(5):
        _append_day(tmp_path, date(2026, 7, 1) + timedelta(days=i))
    tablets = list(ledger.gaps_dir(tmp_path).glob("*.md"))
    assert streak.episode_number(tmp_path) == len(tablets) == 5


def test_episode_number_skips_a_digit_shaped_but_not_a_real_date_tablet(tmp_path: Path):
    # ledger._tablet_files' own filter is a digit-shape regex, not a real
    # calendar-date check -- "2026-02-30" and "2026-13-01" both match it.
    # A hand-edited/typo'd tablet name with that shape must not crash the
    # whole read; it is skipped like any other malformed entry.
    _append_day(tmp_path, date(2026, 7, 1))
    _append_day(tmp_path, date(2026, 7, 2))
    gaps = ledger.gaps_dir(tmp_path)
    (gaps / "2026-02-30.md").write_text("# not a real date\n")
    (gaps / "2026-13-01.md").write_text("# not a real date either\n")
    assert streak.episode_number(tmp_path) == 2


def test_consecutive_days_skips_a_digit_shaped_but_not_a_real_date_tablet(tmp_path: Path):
    _append_day(tmp_path, date(2026, 7, 1))
    _append_day(tmp_path, date(2026, 7, 2))
    (ledger.gaps_dir(tmp_path) / "2026-02-30.md").write_text("# not a real date\n")
    assert streak.consecutive_days(tmp_path) == 2


# --- consecutive_days: an unbroken run, reset by any real gap ------------------


def test_consecutive_days_zero_on_an_empty_ledger(tmp_path: Path):
    assert streak.consecutive_days(tmp_path) == 0


def test_consecutive_days_counts_an_unbroken_run(tmp_path: Path):
    for i in range(4):
        _append_day(tmp_path, date(2026, 7, 1) + timedelta(days=i))
    assert streak.consecutive_days(tmp_path) == 4


def test_consecutive_days_resets_after_a_missed_day(tmp_path: Path):
    _append_day(tmp_path, date(2026, 7, 1))
    _append_day(tmp_path, date(2026, 7, 2))
    # 2026-07-03 is skipped entirely.
    _append_day(tmp_path, date(2026, 7, 4))
    assert streak.consecutive_days(tmp_path, today=date(2026, 7, 4)) == 1
    # And the day before the gap is unreachable from today's anchor at all.
    assert streak.consecutive_days(tmp_path, today=date(2026, 7, 2)) == 2


def test_consecutive_days_anchors_on_the_latest_tablet_by_default(tmp_path: Path):
    _append_day(tmp_path, date(2026, 7, 1))
    _append_day(tmp_path, date(2026, 7, 2))
    _append_day(tmp_path, date(2026, 7, 3))
    assert streak.consecutive_days(tmp_path) == 3


def test_consecutive_days_a_quiet_day_still_counts_toward_the_streak(tmp_path: Path):
    # A day with no primary gap still shipped a report — it must still count
    # toward the cadence, or a perfectly honest quiet day would wrongly look
    # like a missed day and reset a real streak. The streak is about
    # *reports shipped*, never about *gaps found*.
    _append_day(tmp_path, date(2026, 7, 1), primary=True)
    _append_day(tmp_path, date(2026, 7, 2), primary=False)
    _append_day(tmp_path, date(2026, 7, 3), primary=True)
    assert streak.consecutive_days(tmp_path) == 3


# --- the literal done-when: seven consecutive daily reports --------------------


def test_is_seven_day_streak_false_below_seven(tmp_path: Path):
    for i in range(6):
        _append_day(tmp_path, date(2026, 7, 1) + timedelta(days=i))
    assert streak.consecutive_days(tmp_path) == 6
    assert streak.is_seven_day_streak(tmp_path) is False


def test_is_seven_day_streak_true_at_exactly_seven(tmp_path: Path):
    for i in range(7):
        _append_day(tmp_path, date(2026, 7, 1) + timedelta(days=i))
    assert streak.consecutive_days(tmp_path) == 7
    assert streak.is_seven_day_streak(tmp_path) is True


def test_is_seven_day_streak_cannot_be_faked_by_a_broken_run(tmp_path: Path):
    # Eight tablets exist, but one day in the middle was skipped — the
    # streak counted backward from the latest day is still short of seven.
    for i in range(4):
        _append_day(tmp_path, date(2026, 7, 1) + timedelta(days=i))
    # 2026-07-05 skipped.
    for i in range(4):
        _append_day(tmp_path, date(2026, 7, 6) + timedelta(days=i))
    assert streak.episode_number(tmp_path) == 8
    assert streak.consecutive_days(tmp_path) == 4
    assert streak.is_seven_day_streak(tmp_path) is False


def test_streak_status_shape(tmp_path: Path):
    for i in range(3):
        _append_day(tmp_path, date(2026, 7, 1) + timedelta(days=i))
    status = streak.streak_status(tmp_path)
    assert status == {
        "episode": 3,
        "streak_days": 3,
        "longest_streak": 3,
        "target": 7,
        "seven_day_streak": False,
        "days_remaining": 4,
    }


def test_longest_streak_survives_a_later_break(tmp_path: Path):
    for i in range(7):
        _append_day(tmp_path, date(2026, 7, 1) + timedelta(days=i))
    # break, then a shorter run
    _append_day(tmp_path, date(2026, 7, 10))
    assert streak.longest_streak(tmp_path) == 7
    assert streak.consecutive_days(tmp_path) == 1


# --- report.py wiring: additive, never breaks the report's existing law -------


def _sealed(*, primary: bool = True, recorded: int = 1) -> dict:
    p = None
    if primary:
        p = {
            "slug": "milestone-unannounced",
            "headline": "Milestone-level work shipped but never reached the sky",
            "detail": "3 milestone commit(s), none echoed in a post.",
            "confidence": 0.85,
            "evidence": ["https://github.com/x/orita/commit/0000001"],
        }
    return {
        "date": "2026-07-12",
        "generated_at": "2026-07-12T11:38:10+00:00",
        "repo": "x/orita",
        "primary_gap": p,
        "tail": [],
        "fenceposts_recorded_total": recorded,
    }


def test_render_report_without_episode_args_omits_the_episode_line():
    # Backward compatible: a hand-built sealed dict, no ledger behind it,
    # renders exactly as it did before this task.
    text = report.render_report(_sealed())
    assert "Episode" not in text
    assert "watch, unbroken" not in text


def test_render_report_with_episode_args_shows_the_line():
    text = report.render_report(_sealed(), episode_number=5, streak_days=3)
    assert "Episode 5" in text
    assert "Day 3 of the watch" in text


def test_render_report_always_carries_the_connect_your_own_ad():
    assert report.CONNECT_YOUR_OWN in report.render_report(_sealed(primary=True))
    assert report.CONNECT_YOUR_OWN in report.render_report(_sealed(primary=False))


def test_connect_your_own_links_the_real_connect_page():
    assert report.CONNECT_URL in report.CONNECT_YOUR_OWN
    assert report.CONNECT_URL == "https://thierrypdamiba.github.io/orita/fencepost/connect.html"


def test_connect_your_own_never_begs_for_a_star():
    # STRATEGY.md, "How stars are earned": the CTA is never "please star."
    lowered = report.CONNECT_YOUR_OWN.lower()
    for forbidden in ("please star", "star this", "star us", "give us a star", "star the repo"):
        assert forbidden not in lowered


def test_connect_your_own_never_claims_fencepost_acted_on_the_readers_behalf():
    # Same law suggest_move already holds: no first-person-plural claim of
    # having done something, and the ad's own verbs belong to the reader
    # ("point", "connect"), never to Fencepost.
    lowered = report.CONNECT_YOUR_OWN.lower()
    for forbidden in ("we posted", "we added", "we closed", "we'll connect", "fencepost connected"):
        assert forbidden not in lowered


def test_render_report_still_carries_exactly_one_your_move_line_with_the_ad_present():
    text = report.render_report(_sealed(), episode_number=1, streak_days=1)
    assert text.count("**Your move.**") == 1
    assert text.count("**Connect your own.**") == 1


def test_render_latest_carries_the_real_episode_and_streak(tmp_path: Path):
    _append_day(tmp_path, date(2026, 7, 1))
    _append_day(tmp_path, date(2026, 7, 2))
    _append_day(tmp_path, date(2026, 7, 3))
    text = report.render_latest(tmp_path)
    assert "Episode 3" in text
    assert "Day 3 of the watch" in text
    assert report.CONNECT_YOUR_OWN in text


def test_render_latest_streak_resets_after_a_missed_day(tmp_path: Path):
    _append_day(tmp_path, date(2026, 7, 1))
    _append_day(tmp_path, date(2026, 7, 2))
    # 2026-07-03 skipped
    _append_day(tmp_path, date(2026, 7, 4))
    text = report.render_latest(tmp_path)
    # episode 3 (three tablets total), but the streak anchored on the latest
    # tablet (07-04) is only 1 — the missed day really did break it.
    assert "Episode 3" in text
    assert "Day 1 of the watch" in text


# --- the doctrine: README and the daily Action actually say/do this -----------


def test_readme_names_the_serial_mechanic():
    text = README_MD.read_text(encoding="utf-8")
    assert "streak.py" in text
    assert "episode" in text.lower()


def test_readme_carries_the_connect_your_own_language():
    text = README_MD.read_text(encoding="utf-8")
    assert "Connect your own" in text


def test_readme_never_begs_for_a_star_in_the_serial_section():
    text = README_MD.read_text(encoding="utf-8")
    section = text.split("## The serial", 1)[1].split("## The self-audit", 1)[0]
    lowered = section.lower()
    for forbidden in ("please star", "star this", "star us", "give us a star"):
        assert forbidden not in lowered


def test_readme_names_seven_consecutive_days_as_the_proof():
    text = README_MD.read_text(encoding="utf-8")
    section = text.split("## The serial", 1)[1]
    assert "seven" in section.lower()
    assert "consecutive" in section.lower() or "no day skipped" in section.lower()


def test_roadmap_row_19_names_seven_consecutive_reports():
    # Task 170 (tools/roadmap_archive.py, run for real) moved tasks 1-169
    # out of ROADMAP.md byte-for-byte into a dated archive file, so row 19's
    # own text now lives in whichever ROADMAP-ARCHIVE-*.md covers it, not
    # necessarily the live file -- same fix shape task 170 already applied
    # to tests/test_wip_reclaim_check.py's continuity check.
    text = ROADMAP_MD.read_text(encoding="utf-8")
    repo_root = ROADMAP_MD.parent
    for path in repo_root.glob("ROADMAP-ARCHIVE-*.md"):
        text += path.read_text(encoding="utf-8")
    assert "Seven consecutive daily reports posted" in text


def test_seam_scan_workflow_runs_the_streak_status_step():
    text = SEAM_SCAN_YML.read_text(encoding="utf-8")
    assert "seam_engine.streak status" in text


# --- longest_streak: the empty-ledger floor ---------------------------------


def test_longest_streak_zero_on_an_empty_ledger(tmp_path: Path):
    assert streak.longest_streak(tmp_path) == 0


# --- CLI: main() ------------------------------------------------------------
#
# Never directly exercised before this task -- `uv run --with pytest-cov
# python -m pytest --cov` measured streak.py at 71%, missing exactly this
# function's four branches (default `status` command, the seven-day-held
# message, the days-remaining message, and the unknown-command exit code).
# Same untested-CLI-entrypoint shape tasks 647/657/658/659/661 already found
# and closed in sibling `main()`/argv-parsing blocks elsewhere in this repo,
# just never swept for this file.


def test_cli_status_defaults_to_status_command(tmp_path: Path, capsys):
    _append_day(tmp_path, date(2026, 7, 1))
    rc = streak.main(["--base", str(tmp_path)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["episode"] == 1
    assert out["streak_days"] == 1


def test_cli_status_reports_days_remaining_below_seven(tmp_path: Path, capsys):
    for day in (date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)):
        _append_day(tmp_path, day)
    rc = streak.main(["status", "--base", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["seven_day_streak"] is False
    assert out["days_remaining"] == 4
    assert "Day 3 of 7" in captured.err
    assert "4 to go" in captured.err


def test_cli_rejects_trailing_base_flag_with_no_value(capsys):
    rc = streak.main(["--base"])
    assert rc == 2
    assert "--base needs a path" in capsys.readouterr().out


def test_cli_status_reports_seven_day_streak_held(tmp_path: Path, capsys):
    for i in range(7):
        _append_day(tmp_path, date(2026, 7, 1) + timedelta(days=i))
    rc = streak.main(["status", "--base", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["seven_day_streak"] is True
    assert "Seven days, unbroken" in captured.err
    assert f"Episode {out['episode']}" in captured.err


def test_cli_rejects_an_unknown_command(tmp_path: Path, capsys):
    rc = streak.main(["bogus", "--base", str(tmp_path)])
    assert rc == 2
    assert "unknown command: bogus" in capsys.readouterr().err


def test_cli_status_on_an_empty_ledger_shows_day_zero(tmp_path: Path, capsys):
    rc = streak.main(["status", "--base", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["episode"] == 0
    assert out["streak_days"] == 0
    assert "Day 0 of 7" in captured.err
