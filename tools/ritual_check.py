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

Task 82 brings in the one live-API-input tool that never joined tasks
71/73/74's fold: `cron_health.py` (task 62). Its own docstring once claimed
it "stays a live-API-input tool, not folded into ritual_check.py's local-
only scope" -- but `check_ci` (task 73) is ALSO a live-API-input the
caller pre-fetches and hands in, and it folded in fine. `check_cron`
mirrors `check_ci` exactly: `cron_checks` is `None` unless the caller
already holds this hour's live `list_workflow_runs` read, folded through
`cron_health.schedule_status` with no network call of its own.

Task 83 folds the one number `check_x_recheck` (task 61) never covered:
`x_outage_tracker.should_escalate` (task 81), whether an ongoing X outage
has crossed its 48h threshold and already fired, or is due to. Same
read-only shape as `check_x_recheck` exactly -- this check never calls
`record_escalation` itself; that only happens when the god on duty
actually surfaces the escalation to Thierry.

Task 85 folds the one local-filesystem number that never joined `check_words`
(task 74) despite the identical shape: `x_post_queue.pending_entries` (task
55), the owed-report backlog count every hourly note had re-derived by hand
("N now pending") since the queue was built. `check_owed_posts` is
unconditional, not flag-gated -- reading one append-only jsonl is as cheap
as `check_town_ledger`'s own ledger read.

Task 86 closes the one door left standing from that whole run: `change_gate.py`
(task 69) -- the FIRST of these hand-narrated-number tools ever built, a full
sixteen tasks before `square_check.py` (70) started the fold-into-`ritual_check`
habit -- never itself joined it. Every hourly note since has still hand-read
"no gap surfaced this hour differs from the last one posted... so staying
silent on X" instead of calling `should_post_gap()`, the exact function built
to answer it. `check_change_gate` takes no new argument: it reads whichever
report text `check_report_freshness` already resolved this call (today's file
if `current`, yesterday's fallback if `pending`) and folds `should_post_gap`
through it -- no second file read, no network call, `None` only when there is
truly no report to compare (`stale`). Hit the same trap task 83's and 85's
own notes already named: `should_post_gap`'s `path=LOG` default binds at
module-*definition* time, so `check_change_gate` passes `path=mod.LOG`
explicitly rather than trusting the bare default -- a monkeypatched test
log would otherwise be silently ignored, the same class of bug those two
tasks' live proofs caught before commit.

Task 87 closes the one door task 85 itself proved didn't need a key:
`check_words` (task 74) stayed gated behind `check_words_flag`/
`--check-words` even after `check_owed_posts` (task 85) used the identical
local-filesystem-only, no-network shape to argue it needed no flag at all.
A forgotten flag meant `words` silently came back `None` and "no new words
from Thierry" quietly stopped being checked, with no error and no line in
the printed block. `check_words()` now takes no flag and always runs,
mirroring `check_owed_posts` exactly.

Task 88 fixes a real bug `SquareFoldCase.test_unchanged_after_recording`
exposed in its own setup step: `check_square`/`check_words` compared this
hour's fresh read against the last DURABLY RECORDED entry, same as
`check_ci`, but unlike `check_ci` -- which calls `record_check` before
reading the streak back -- neither ever called `record_square_check`/
`record_word_check` to persist what they just observed. Calling
`ritual_check.py` alone (the "one call" tasks 71/74 built) therefore never
advanced `HAND/square-check-log.jsonl`/`HAND/word-check-log.jsonl` at all;
every entry those logs actually gained came from a SEPARATE, easy-to-forget
`square_check.py record ...`/`word_watch.py record ...` call the god on duty
had to remember to also run by hand. Worse than a stale audit trail: if a
real change ever landed and only `ritual_check.py` was run afterward, every
following hour would keep comparing against the SAME pre-change baseline
forever and report "changed" every single hour, never settling into a new
"unchanged since <the real new value>" baseline -- the exact false-signal
shape Ogun's law exists to catch, just inside the town's own ritual instead
of a Fencepost gap. Both folds now record (after computing the delta, so
the comparison itself is unaffected) the same `now_iso` `run_ritual_check`
already threads through `check_x_recheck`/`check_x_escalation`/`check_cron`.

Same discipline as sync_checkout.sh: refuse (report broken=True) rather
than paper over a real problem. A ledger that fails to verify is reported
broken, never silently skipped.

Task 90 closes the one ritual step that never joined this fold at all:
`tools/sync_checkout.sh` (task 58) recovers a detached-HEAD checkout, but
`TOWN-OPERATIONS.md`'s own documented order still runs it as a wholly
separate command before this script even starts, and every hourly note
since has typed "both checkouts recovered via tools/sync_checkout.sh...
no recovery needed" from that command's own stdout rather than this
block. `check_checkout` does NOT call `sync_checkout.sh`'s actual
`checkout -B` recovery -- it only reads whether each tracked repo is
CURRENTLY on a detached HEAD (`git symbolic-ref -q HEAD`, the identical
probe `sync_checkout.sh` itself uses for its own case-1 check), the same
"read the state, let the god act on it" boundary `check_x_escalation`
already holds versus `record_escalation`. Actually recovering a real
divergence still belongs to `sync_checkout.sh`, run first, same as always
-- this only makes the CURRENT state visible in the one block instead of
a separate command's printed line.

Usage:
    python3 tools/ritual_check.py [--now ISO_TS] [--fencepost-base DIR] [--square-state PATH] [--cron-checks PATH]
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FENCEPOST_BASE = os.path.join(ROOT, "fencepost")
DEFAULT_REPORTS_DIR = os.path.join(ROOT, "fencepost", "REPORTS")
DEFAULT_CHECKOUT_DIRS = (ROOT, os.path.join(os.path.dirname(ROOT), "orita-vault"))


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


def _x_post_queue():
    return _load("_ritual_x_post_queue", os.path.join(ROOT, "tools", "x_post_queue.py"))


def _cron_health():
    return _load("_ritual_cron_health", os.path.join(ROOT, "tools", "cron_health.py"))


def _change_gate():
    return _load("_ritual_change_gate", os.path.join(ROOT, "tools", "change_gate.py"))


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


def check_x_escalation(now_iso: str) -> dict:
    """should_escalate() for every tool in x_outage_tracker.TRACKED_TOOLS,
    via the real outage log and the real HAND/escalations.jsonl. Mirrors
    `check_x_recheck`'s exact shape (task 61) -- read-only, makes no write
    of its own. A real escalation is only ever recorded (`record_escalation`)
    when the god on duty actually surfaces it to Thierry, not by this check;
    this fold exists purely so the verdict lands in the same printed block
    instead of a sixth hand-run command every hour."""
    mod = _outage_tracker()
    entries = mod._entries(mod.LOG)
    escalation_entries = mod._escalation_entries(mod.ESCALATION_LOG)
    result = {}
    for tool in mod.TRACKED_TOOLS:
        due, reason = mod.should_escalate(entries, tool, now_iso, escalation_entries=escalation_entries)
        result[tool] = {"due": due, "reason": reason}
    return result


def check_square(square_state: dict | None, now_iso: str) -> dict | None:
    """Fold a caller-supplied, already-computed square state (task 70's
    `square_check.compute_square_state` output) through `square_delta`.
    Makes no network call -- `square_state` is None unless the caller
    already holds this hour's live `list_issues`/`list_pull_requests` read.
    Task 88: records this hour's state via `record_square_check` AFTER
    computing the delta (recording first would make every call compare a
    state against itself) so the log's baseline actually advances -- calling
    `ritual_check.py` alone is now enough, no separate `square_check.py
    record` call required to keep a real change from reporting "changed"
    forever afterward."""
    if square_state is None:
        return None
    mod = _square_check()
    changed, reason = mod.square_delta(square_state, path=mod.LOG)
    mod.record_square_check(square_state, now_iso, path=mod.LOG)
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


def check_cron(cron_checks: list | None, now_iso: str) -> dict | None:
    """Fold this hour's already-fetched `{workflow, cron_expr, last_run_at}`
    dicts through `cron_health.schedule_status`, mirroring `check_ci`'s
    exact live-API-input-but-no-network-call shape (task 73) rather than
    `check_words`'s local-filesystem shape (task 74) -- `cron_checks` is
    `None` unless the caller already holds this hour's live
    `list_workflow_runs` read for the tracked scheduled workflows. An
    unparseable cron (`cron_health.parse_daily_cron`'s own rejection)
    surfaces as `{"status": "error", "error": ...}` for that workflow
    rather than crashing the whole ritual check -- the same refuse-not-
    crash discipline `sync_checkout.sh` already holds, scoped to one
    workflow instead of the whole run."""
    if cron_checks is None:
        return None
    mod = _cron_health()
    result = {}
    for c in cron_checks:
        try:
            result[c["workflow"]] = mod.schedule_status(c["cron_expr"], c.get("last_run_at"), now_iso)
        except ValueError as e:
            result[c["workflow"]] = {"status": "error", "error": str(e)}
    return result


def check_words(now_iso: str) -> dict:
    """Read the four places Thierry's words land (task 74's
    `word_watch.compute_word_state`) and fold through `word_delta`.
    Local filesystem only -- no network call, unlike `check_square`/
    `check_ci` which take a caller-supplied live API read. Unconditional
    since task 87, mirroring `check_owed_posts` (task 85)'s own reasoning:
    reading four small local paths is the identical cheap, no-network,
    local-filesystem-only class, so there's no flag to skip it -- a
    forgotten flag used to mean `words` silently came back `None` with no
    error and no line in the printed block. Task 88: records this hour's
    state via `record_word_check` AFTER computing the delta, the identical
    fix `check_square` gets in the same task -- without it a real word
    landing would report "changed" every hour forever after, never settling
    into a new baseline, since nothing else ever advanced the log either."""
    mod = _word_watch()
    state = mod.compute_word_state(root=mod.ROOT)
    changed, reason = mod.word_delta(state, path=mod.LOG)
    mod.record_word_check(state, now_iso, path=mod.LOG)
    return {"changed": changed, "reason": reason}


def check_owed_posts() -> dict:
    """Task 55's `x_post_queue.pending_entries` -- the owed-report backlog
    count every hourly note has re-derived by hand ("N now pending") since
    task 55 shipped -- folded in the same local-filesystem-only, no-network
    shape `check_words` already holds (task 74). Unconditional, like
    `check_town_ledger`/`check_x_recheck`: reading one append-only jsonl is
    cheap enough that there's no flag to skip it."""
    mod = _x_post_queue()
    entries = mod.pending_entries(path=mod.QUEUE)
    return {"count": len(entries), "tasks": [e["task"] for e in entries]}


def _checkout_state(repo_dir: str) -> dict | None:
    """Read-only detached-HEAD probe for one repo dir, mirroring
    sync_checkout.sh's own case-1 detection exactly, never its recovery.
    Returns None if repo_dir isn't a git checkout at all -- a missing
    sibling repo in some environment shouldn't crash the whole ritual
    check, the same missing-input tolerance check_change_gate holds for a
    stale report."""
    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        return None
    sym = subprocess.run(
        ["git", "symbolic-ref", "-q", "HEAD"],
        cwd=repo_dir, capture_output=True, text=True,
    )
    detached = sym.returncode != 0
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir, capture_output=True, text=True,
    ).stdout.strip()
    branch = None if detached else sym.stdout.strip().replace("refs/heads/", "")
    return {"repo": repo_dir, "detached": detached, "head_sha": head_sha, "branch": branch}


def check_checkout(repo_dirs: tuple | None = None) -> list:
    """Task 90: fold sync_checkout.sh's own detached-HEAD signal into the
    one block. Unconditional, local-filesystem-only (a `git` subprocess
    call against a local working tree, no network) -- the same cheap class
    `check_words`/`check_owed_posts` already argued needs no flag."""
    if repo_dirs is None:
        repo_dirs = DEFAULT_CHECKOUT_DIRS
    return [s for s in (_checkout_state(d) for d in repo_dirs) if s is not None]


def check_change_gate(report_info: dict) -> dict | None:
    """Fold `change_gate.should_post_gap()` -- task 69's own change-gate
    rule -- using whichever report text `check_report_freshness` already
    resolved (its `path` if `current`, its `fallback_path` if `pending`).
    No second file read of its own, no network call. A `stale` report (no
    file exists at all, `report_info["path"]` and `["fallback_path"]` both
    absent/None) has nothing to compare against, so this returns None, the
    same "nothing to check" shape `check_square`/`check_ci`/`check_cron`
    already hold when their caller-supplied input is None."""
    path = report_info.get("path") or report_info.get("fallback_path")
    if path is None:
        return None
    mod = _change_gate()
    with open(path) as f:
        text = f.read()
    due, reason = mod.should_post_gap(text, path=mod.LOG)
    return {"due": due, "reason": reason}


def run_ritual_check(
    now: datetime | None = None,
    fencepost_base: str = DEFAULT_FENCEPOST_BASE,
    square_state: dict | None = None,
    ci_checks: list | None = None,
    cron_checks: list | None = None,
    checkout_dirs: tuple | None = None,
) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)
    now_iso = now.isoformat(timespec="seconds")
    checkout = check_checkout(checkout_dirs)
    town = check_town_ledger()
    fencepost = check_fencepost_ledger(fencepost_base)
    report = check_report_freshness(now)
    recheck = check_x_recheck(now_iso)
    escalation = check_x_escalation(now_iso)
    square = check_square(square_state, now_iso)
    ci = check_ci(ci_checks)
    words = check_words(now_iso)
    cron = check_cron(cron_checks, now_iso)
    owed_posts = check_owed_posts()
    change_gate = check_change_gate(report)
    broken = (not town["ok"]) or (not fencepost["ok"])
    return {
        "now": now_iso,
        "checkout": checkout,
        "town_ledger": town,
        "fencepost_ledger": fencepost,
        "report": report,
        "x_recheck": recheck,
        "x_escalation": escalation,
        "square": square,
        "ci": ci,
        "words": words,
        "cron": cron,
        "owed_posts": owed_posts,
        "change_gate": change_gate,
        "broken": broken,
    }


def format_ritual_check(result: dict) -> str:
    lines = [f"ritual check @ {result['now']}"]
    for c in result["checkout"]:
        if c["detached"]:
            lines.append(f"  checkout {c['repo']}: DETACHED HEAD @ {c['head_sha'][:12]} -- run tools/sync_checkout.sh")
        else:
            lines.append(f"  checkout {c['repo']}: {c['branch']} @ {c['head_sha'][:12]}")
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
    for tool, info in result["x_escalation"].items():
        lines.append(f"  {tool} escalation: {'due' if info['due'] else 'not due'} -- {info['reason']}")
    if result["square"] is not None:
        s = result["square"]
        lines.append(f"  square: {'changed' if s['changed'] else 'unchanged'} -- {s['reason']}")
    if result["ci"] is not None:
        for workflow, line in result["ci"].items():
            lines.append(f"  ci/{workflow}: {line}")
    w = result["words"]
    lines.append(f"  words: {'changed' if w['changed'] else 'unchanged'} -- {w['reason']}")
    if result["cron"] is not None:
        for workflow, info in result["cron"].items():
            if info["status"] == "error":
                lines.append(f"  cron/{workflow}: error -- {info['error']}")
            else:
                lines.append(
                    f"  cron/{workflow}: {info['status']}"
                    + (f" ({info['hours_late']}h late)" if info["hours_late"] is not None else "")
                    + f" -- due {info['due_at']}, last run {info['last_run_at']}"
                )
    op = result["owed_posts"]
    tasks_str = ",".join(str(t) for t in op["tasks"])
    lines.append(f"  owed posts: {op['count']} pending" + (f" (tasks: {tasks_str})" if op["count"] else ""))
    if result["change_gate"] is not None:
        cg = result["change_gate"]
        lines.append(f"  change gate: {'due' if cg['due'] else 'not due'} -- {cg['reason']}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    now = None
    base = DEFAULT_FENCEPOST_BASE
    square_state = None
    ci_checks = None
    cron_checks = None
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
        elif argv[i] == "--cron-checks" and i + 1 < len(argv):
            with open(argv[i + 1]) as f:
                cron_checks = json.load(f)
            i += 2
        elif argv[i] == "--json":
            base = base
            i += 1
        else:
            i += 1
    result = run_ritual_check(
        now=now,
        fencepost_base=base,
        square_state=square_state,
        ci_checks=ci_checks,
        cron_checks=cron_checks,
    )
    if "--json" in argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_ritual_check(result))
    sys.exit(1 if result["broken"] else 0)
