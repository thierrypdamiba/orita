#!/usr/bin/env python3
"""Task 61 (extended task 71). Kothar-wa-Khasis's fix for the ritual note's
own toil.

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
structured result. It makes no network call of its own -- that's a live API
read with no local fixture shape, out of scope for a script that
fixture-tests cleanly offline, same boundary `sync_checkout.sh` drew around
git state versus GitHub state.

Task 70 gave the square (GitHub issues/PRs) the identical durable-compare
shape as a SEPARATE tool, `square_check.py`, because it too takes an
already-fetched state rather than calling the network -- the same boundary
this module already holds. Task 71 closes the seam between the two: the god
on duty was still running `ritual_check.py` for the local four, then
`square_check.py check` for the square, then hand-stitching both outputs
into one paragraph. `run_ritual_check(square_state=...)` now takes the
already-computed square state (via `square_check.compute_square_state`,
built from this hour's own `list_issues`/`list_pull_requests` read) as an
optional argument and folds `square_check.square_delta`'s verdict into the
same structured result and the same printed block -- one call, one block,
when the god on duty has that hour's square read in hand. Passing nothing
for `square_state` leaves the result's `square` key `None`, unchanged from
before -- fully backward compatible for a local-only run.

Same discipline as sync_checkout.sh: refuse (report broken=True) rather
than paper over a real problem. A ledger that fails to verify is reported
broken, never silently skipped.

Usage:
    python3 tools/ritual_check.py [--now ISO_TS] [--fencepost-base DIR] [--square-state PATH]
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


def _square_check():
    return _load("_ritual_square_check", os.path.join(ROOT, "tools", "square_check.py"))


def _ci_watch():
    return _load("_ritual_ci_watch", os.path.join(ROOT, "tools", "ci_watch.py"))


def _word_watch():
    return _load("_ritual_word_watch", os.path.join(ROOT, "tools", "word_watch.py"))


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


def check_square(square_state: dict | None) -> dict | None:
    """Fold a caller-supplied, already-computed square state (task 70's
    `square_check.compute_square_state` output) through `square_delta`.
    Makes no network call -- `square_state` is None unless the caller
    already holds this hour's live `list_issues`/`list_pull_requests` read."""
    if square_state is None:
        return None
    mod = _square_check()
    changed, reason = mod.square_delta(square_state, path=mod.LOG)
    return {"changed": changed, "reason": reason}


def check_ci(ci_checks: list | None) -> dict | None:
    """Fold this hour's already-observed CI conclusions (task 73's
    `ci_watch.record_check` shape: `{workflow, conclusion, run_id,
    checked_at}` dicts) through the durable log. Makes no network call --
    `ci_checks` is None unless the caller already holds this hour's live
    `list_workflow_runs` read for the tracked workflows. Each supplied
    check is recorded (append-only) before the status lines are read back,
    same order `x_outage_tracker`'s own recheck-then-record flow already
    holds."""
    if ci_checks is None:
        return None
    mod = _ci_watch()
    for c in ci_checks:
        mod.record_check(c["workflow"], c["conclusion"], c["run_id"], c["checked_at"], path=mod.LOG)
    entries = mod._entries(mod.LOG)
    return {w: mod.format_status_line(entries, w) for w in mod.TRACKED_WORKFLOWS}


def check_words(check_words_flag: bool) -> dict | None:
    """Read the four places Thierry's words land (task 74's
    `word_watch.compute_word_state`) and fold through `word_delta`.
    Local filesystem only -- no network call, unlike `check_square`/
    `check_ci` which take a caller-supplied live API read. Off by
    default (`check_words_flag=False`) so a caller who doesn't want the
    filesystem walk this hour gets `None`, unchanged from before this
    task."""
    if not check_words_flag:
        return None
    mod = _word_watch()
    state = mod.compute_word_state(root=mod.ROOT)
    changed, reason = mod.word_delta(state, path=mod.LOG)
    return {"changed": changed, "reason": reason}


def run_ritual_check(
    now: datetime | None = None,
    fencepost_base: str = DEFAULT_FENCEPOST_BASE,
    square_state: dict | None = None,
    ci_checks: list | None = None,
    check_words_flag: bool = False,
) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)
    now_iso = now.isoformat(timespec="seconds")
    town = check_town_ledger()
    fencepost = check_fencepost_ledger(fencepost_base)
    report = check_report_freshness(now)
    recheck = check_x_recheck(now_iso)
    square = check_square(square_state)
    ci = check_ci(ci_checks)
    words = check_words(check_words_flag)
    broken = (not town["ok"]) or (not fencepost["ok"])
    return {
        "now": now_iso,
        "town_ledger": town,
        "fencepost_ledger": fencepost,
        "report": report,
        "x_recheck": recheck,
        "square": square,
        "ci": ci,
        "words": words,
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
    if result["square"] is not None:
        s = result["square"]
        lines.append(f"  square: {'changed' if s['changed'] else 'unchanged'} -- {s['reason']}")
    if result["ci"] is not None:
        for workflow, line in result["ci"].items():
            lines.append(f"  ci/{workflow}: {line}")
    if result["words"] is not None:
        w = result["words"]
        lines.append(f"  words: {'changed' if w['changed'] else 'unchanged'} -- {w['reason']}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    now = None
    base = DEFAULT_FENCEPOST_BASE
    square_state = None
    ci_checks = None
    check_words_flag = False
    i = 0
    while i < len(argv):
        if argv[i] == "--now" and i + 1 < len(argv):
            now = datetime.fromisoformat(argv[i + 1].replace("Z", "+00:00")).astimezone(timezone.utc)
            i += 2
        elif argv[i] == "--fencepost-base" and i + 1 < len(argv):
            base = argv[i + 1]
            i += 2
        elif argv[i] == "--square-state" and i + 1 < len(argv):
            with open(argv[i + 1]) as f:
                raw = json.load(f)
            sq = _square_check()
            square_state = sq.compute_square_state(raw.get("issues", []), raw.get("prs", []))
            i += 2
        elif argv[i] == "--ci-checks" and i + 1 < len(argv):
            with open(argv[i + 1]) as f:
                ci_checks = json.load(f)
            i += 2
        elif argv[i] == "--json":
            base = base
            i += 1
        elif argv[i] == "--check-words":
            check_words_flag = True
            i += 1
        else:
            i += 1
    result = run_ritual_check(
        now=now,
        fencepost_base=base,
        square_state=square_state,
        ci_checks=ci_checks,
        check_words_flag=check_words_flag,
    )
    if "--json" in argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_ritual_check(result))
    sys.exit(1 if result["broken"] else 0)
