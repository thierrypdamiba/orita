#!/usr/bin/env python3
"""Task 61. Kothar-wa-Khasis's fix for the ritual note's own toil.

Tasks 55-59 turned five real hand-narrated judgment calls into durable,
tested tools -- the owed-post backlog (x_post_queue.py), the outage streak
and its recheck cooldown (x_outage_tracker.py), the checkout recovery
(sync_checkout.sh). But the hourly ritual note that REPORTS on all of them
was still assembled the old way: run `python3 tools/ledger.py verify`, run
`python3 -m seam_engine.ledger verify --base fencepost` (or the fencepost
tablet path), eyeball whether today's `fencepost/REPORTS/<date>.md` exists,
run `python3 tools/x_outage_tracker.py should-recheck ...` twice -- four or
five separate commands, copied into prose, in the same order, every hour.

This module runs the LOCAL half of that ritual in one pass and returns one
structured result. It does NOT touch the square (GitHub issues/PRs) --
that's a live API read with no local fixture shape, out of scope for a
script that fixture-tests cleanly offline, same boundary `sync_checkout.sh`
drew around git state versus GitHub state.

Same discipline as sync_checkout.sh: refuse (report broken=True) rather
than paper over a real problem. A ledger that fails to verify is reported
broken, never silently skipped.

Usage:
    python3 tools/ritual_check.py [--now ISO_TS] [--fencepost-base DIR]
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FENCEPOST_BASE = os.path.join(ROOT, "fencepost")
DEFAULT_REPORTS_DIR = os.path.join(ROOT, "fencepost", "REPORTS")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _town_ledger():
    return _load("_ritual_town_ledger", os.path.join(ROOT, "tools", "ledger.py"))


def _outage_tracker():
    return _load("_ritual_outage_tracker", os.path.join(ROOT, "tools", "x_outage_tracker.py"))


def _seam_ledger():
    src = os.path.join(ROOT, "fencepost", "seam_engine", "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    import seam_engine.ledger as seam_ledger  # noqa: PLC0415
    return seam_ledger


def check_town_ledger() -> dict:
    """Verify records/ledger.jsonl by importing tools/ledger.py's own
    entries()/verify logic rather than re-implementing the chain walk or
    shelling out to a subprocess."""
    mod = _town_ledger()
    entries = mod._entries()
    prev = mod.GENESIS
    for i, e in enumerate(entries):
        e = dict(e)
        h = e.pop("hash")
        if e["prev"] != prev or mod._hash(e, prev) != h:
            return {"ok": False, "count": len(entries), "broken_at_seq": i}
        prev = h
    return {"ok": True, "count": len(entries), "broken_at_seq": None}


def check_fencepost_ledger(base: str = DEFAULT_FENCEPOST_BASE) -> dict:
    """Verify the fencepost Gap Ledger tablet chain via seam_engine.ledger's
    own verify(), which returns a problems list rather than printing."""
    from pathlib import Path

    seam_ledger = _seam_ledger()
    problems = seam_ledger.verify(Path(base))
    records = seam_ledger.read_records(Path(base))
    return {"ok": not problems, "count": len(records), "problems": list(problems)}


def check_report_freshness(now: datetime, reports_dir: str = DEFAULT_REPORTS_DIR) -> dict:
    """Whether today's (UTC) Fencepost Report exists. Missing-today-but-
    present-yesterday is the EXPECTED state before seam-scan.yml's daily
    cron fires -- reported as `pending`, not `stale`. Missing both today
    AND yesterday is a real gap worth flagging as `stale`."""
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    today_path = os.path.join(reports_dir, f"{today}.md")
    yesterday_path = os.path.join(reports_dir, f"{yesterday}.md")
    if os.path.exists(today_path):
        return {"status": "current", "date": today, "path": today_path}
    if os.path.exists(yesterday_path):
        return {"status": "pending", "date": today, "fallback_path": yesterday_path}
    return {"status": "stale", "date": today, "fallback_path": None}


def check_x_recheck(now_iso: str, cooldown_hours: float = 2.0) -> dict:
    """should_recheck() for both tracked X tools, via the real log."""
    mod = _outage_tracker()
    entries = mod._entries()
    result = {}
    for tool in mod.TRACKED_TOOLS:
        result[tool] = {
            "due": mod.should_recheck(entries, tool, now_iso, cooldown_hours),
            "status_line": mod.format_status_line(entries, tool),
        }
    return result


def run_ritual_check(now: datetime | None = None, fencepost_base: str = DEFAULT_FENCEPOST_BASE) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)
    now_iso = now.isoformat(timespec="seconds")
    town = check_town_ledger()
    fencepost = check_fencepost_ledger(fencepost_base)
    report = check_report_freshness(now)
    recheck = check_x_recheck(now_iso)
    broken = (not town["ok"]) or (not fencepost["ok"])
    return {
        "now": now_iso,
        "town_ledger": town,
        "fencepost_ledger": fencepost,
        "report": report,
        "x_recheck": recheck,
        "broken": broken,
    }


def format_ritual_check(result: dict) -> str:
    lines = [f"ritual check @ {result['now']}"]
    t = result["town_ledger"]
    lines.append(
        f"  town ledger: {'intact' if t['ok'] else 'BROKEN at seq ' + str(t['broken_at_seq'])}, {t['count']} entries"
    )
    f = result["fencepost_ledger"]
    lines.append(
        f"  fencepost ledger: {'intact' if f['ok'] else 'BROKEN'}, {f['count']} entries"
        + ("" if f["ok"] else f" -- {f['problems']}")
    )
    r = result["report"]
    if r["status"] == "current":
        lines.append(f"  report: current ({r['path']})")
    elif r["status"] == "pending":
        lines.append(f"  report: pending for {r['date']} (falls back to {r['fallback_path']})")
    else:
        lines.append(f"  report: STALE -- no report for {r['date']} or the day before")
    for tool, info in result["x_recheck"].items():
        lines.append(f"  {tool}: {'due' if info['due'] else 'not due'} -- {info['status_line']}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    now = None
    base = DEFAULT_FENCEPOST_BASE
    i = 0
    while i < len(argv):
        if argv[i] == "--now" and i + 1 < len(argv):
            now = datetime.fromisoformat(argv[i + 1].replace("Z", "+00:00")).astimezone(timezone.utc)
            i += 2
        elif argv[i] == "--fencepost-base" and i + 1 < len(argv):
            base = argv[i + 1]
            i += 2
        elif argv[i] == "--json":
            base = base
            i += 1
        else:
            i += 1
    result = run_ritual_check(now=now, fencepost_base=base)
    if "--json" in argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_ritual_check(result))
    sys.exit(1 if result["broken"] else 0)
