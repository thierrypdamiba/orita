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

Task 101 folds `child_work_check.py`: Iron Rule #6 ("the child's work is
never reverted. LAW.") gets its first running check, alongside #1/#4/#5
(tasks 98-100). It can't mirror those three's unconditional local-only
shape -- "reverted" is a claim about HISTORY, and this checkout is a
shallow clone, so the set of files the child (Zashiki-Warashi) has ever
shipped has to come from a caller-supplied live GitHub commit read, the
same `check_ci`/`check_cron` shape (tasks 73/82). `child_files` is `None`
unless the god on duty holds this hour's live read; every already-logged
path is still re-checked locally, unconditionally, every hour regardless.

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

Task 125 folds `arcade_app_watch.py` (task 122, Nisaba's own tool) in --
the last live-API-input tool built during the 116-124 cadence run that
never joined the `--square-state`-style fold. `arcade_app_watch.py` was
already built to the identical caller-supplies-the-state, no-network-call
shape `square_check.py` holds, but nothing ever wired it into this script:
the god on duty has had to remember to call `Arcade_ListApps` live AND
separately run `arcade_app_watch.py record ...` by hand every hour since
task 122 shipped, the same "recalled, not recorded" gap that module's own
docstring says it exists to close for everything else. `check_arcade_apps`
mirrors `check_square` exactly, including the delta-before-record order
task 88 fixed there: `None` unless `arcade_apps_state` is supplied, else
`app_delta` is read against the last durably recorded snapshot BEFORE this
hour's own state is appended, so a real change is never compared against
itself. Informational only, like `square` -- a new upstream OAuth
connection on the-hand gateway is not itself a rule violation (task 122's
own scoping note: no live Gmail/Calendar tool is reachable through it
regardless, and `consent.py`'s gate still fails closed), so this never
flips `broken`.

Task 477 folds `good_first_issue_check.py`: CHARTER.md Appendix B names
"good-first-issues stocked" as Ogun's job, alongside "links unbroken"
(task 423) and "badge green" (task 425), both of which already had a
running check here -- "stocked" never did, until a live read showed the
`good first issue` label has never once been attached to a real issue in
this repo's history. `good_first_issues_state` is `None` unless the god
on duty holds this hour's live `list_issues` read (each entry carrying
`number`/`labels`); no durable log, since there is no "change since last
hour" worth tracking here, only "is the shelf stocked right now" -- the
same simpler, log-free shape `badge_freshness_check.py` already holds.
Informational only, the same class `report_cadence`/`cluster_day`/
`thegap` already hold for their own real-but-not-fatal cadence gaps --
never flips `broken`.

Usage:
    python3 tools/ritual_check.py [--now ISO_TS] [--fencepost-base DIR] [--square-state PATH] [--arcade-apps-state PATH] [--gateway-toolset PATH] [--good-first-issues PATH] [--ci-checks PATH] [--cron-checks PATH] [--child-files PATH] [--voice-window-commits PATH] [--github-stars COUNT] [--json]
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FENCEPOST_BASE = os.path.join(ROOT, "fencepost")
DEFAULT_REPORTS_DIR = os.path.join(ROOT, "fencepost", "REPORTS")
DEFAULT_CHECKOUT_DIRS = (ROOT, os.path.join(os.path.dirname(ROOT), "orita-vault"))


def _load(name: str, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load module {name!r} from {path!r}: no loader for this file type")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_LOADED_MODULES_CACHE: dict[str, ModuleType] = {}


def _load_once(name: str, path: str) -> ModuleType:
    """Task 367: like `_load()`, but reuses the same module object across
    repeated calls for the same `name` within one process, instead of
    re-`exec_module()`-ing (and so fully re-running) the target file
    every time. Most `_load()` call sites below deliberately keep the
    unconditional-reload behavior -- several of these tool modules hold
    their own mutable module-level state (a log path, a queue file) that
    tests reach for fresh, uniquely-named instances of on purpose, and
    `run_ritual_check()` itself only ever calls each loader once per
    invocation anyway, so reload-vs-reuse makes no difference there. It
    matters only for the handful of checks below whose own scan function
    now memoizes its result inside the module (vault_leak_check.py's
    `find_leaks()`, and the five `find_violations()` siblings it
    revealed) -- for exactly those, an unconditional reload was silently
    resetting that memoized cache on every single call, which is what
    made `check_vault_leak()` still cost ~9s per call even after its own
    scan gained a cache: `run_ritual_check()`'s test suite calls these
    loaders far more than once per process, and only a reused module
    instance lets that memoization actually reach them."""
    if name not in _LOADED_MODULES_CACHE:
        _LOADED_MODULES_CACHE[name] = _load(name, path)
    return _LOADED_MODULES_CACHE[name]


def _town_ledger() -> ModuleType:
    return _load("_ritual_town_ledger", os.path.join(ROOT, "tools", "ledger.py"))


def _outage_tracker() -> ModuleType:
    return _load("_ritual_outage_tracker", os.path.join(ROOT, "tools", "x_outage_tracker.py"))


def _square_check() -> ModuleType:
    return _load("_ritual_square_check", os.path.join(ROOT, "tools", "square_check.py"))


def _ci_watch() -> ModuleType:
    return _load("_ritual_ci_watch", os.path.join(ROOT, "tools", "ci_watch.py"))


def _github_stars_check() -> ModuleType:
    return _load("_ritual_github_stars_check", os.path.join(ROOT, "tools", "github_stars_check.py"))


def _word_watch() -> ModuleType:
    return _load("_ritual_word_watch", os.path.join(ROOT, "tools", "word_watch.py"))


def _x_post_queue() -> ModuleType:
    return _load("_ritual_x_post_queue", os.path.join(ROOT, "tools", "x_post_queue.py"))


def _cron_health() -> ModuleType:
    return _load("_ritual_cron_health", os.path.join(ROOT, "tools", "cron_health.py"))


def _change_gate() -> ModuleType:
    return _load("_ritual_change_gate", os.path.join(ROOT, "tools", "change_gate.py"))


def _arcade_app_watch() -> ModuleType:
    return _load("_ritual_arcade_app_watch", os.path.join(ROOT, "tools", "arcade_app_watch.py"))


def _gateway_toolset_check() -> ModuleType:
    return _load("_ritual_gateway_toolset_check", os.path.join(ROOT, "tools", "gateway_toolset_check.py"))


def _good_first_issue_check() -> ModuleType:
    return _load("_ritual_good_first_issue_check", os.path.join(ROOT, "tools", "good_first_issue_check.py"))


def _scribe_growth_check() -> ModuleType:
    return _load("_ritual_scribe_growth_check", os.path.join(ROOT, "tools", "scribe_growth_check.py"))


def _vault_leak_check() -> ModuleType:
    return _load_once("_ritual_vault_leak_check", os.path.join(ROOT, "tools", "vault_leak_check.py"))


def _star_covenant_check() -> ModuleType:
    return _load_once("_ritual_star_covenant_check", os.path.join(ROOT, "tools", "star_covenant_check.py"))


def _duplicate_regex_check() -> ModuleType:
    return _load_once("_ritual_duplicate_regex_check", os.path.join(ROOT, "tools", "duplicate_regex_check.py"))


def _rider_check() -> ModuleType:
    return _load_once("_ritual_rider_check", os.path.join(ROOT, "tools", "rider_check.py"))


def _hand_lore_check() -> ModuleType:
    return _load_once("_ritual_hand_lore_check", os.path.join(ROOT, "tools", "hand_lore_check.py"))


def _no_grading_check() -> ModuleType:
    return _load_once("_ritual_no_grading_check", os.path.join(ROOT, "tools", "no_grading_check.py"))


def _arcade_hero_check() -> ModuleType:
    return _load_once("_ritual_arcade_hero_check", os.path.join(ROOT, "tools", "arcade_hero_check.py"))


def _petition_limits_check() -> ModuleType:
    return _load("_ritual_petition_limits_check", os.path.join(ROOT, "tools", "petition_limits_check.py"))


def _child_work_check() -> ModuleType:
    return _load("_ritual_child_work_check", os.path.join(ROOT, "tools", "child_work_check.py"))


def _verdict_provenance_check() -> ModuleType:
    return _load("_ritual_verdict_provenance_check", os.path.join(ROOT, "tools", "verdict_provenance_check.py"))


def _voice_window_check() -> ModuleType:
    return _load("_ritual_voice_window_check", os.path.join(ROOT, "tools", "voice_window_check.py"))


def _petition_cadence_check() -> ModuleType:
    return _load("_ritual_petition_cadence_check", os.path.join(ROOT, "tools", "petition_cadence_check.py"))


def _journal_numbering_check() -> ModuleType:
    return _load("_ritual_journal_numbering_check", os.path.join(ROOT, "tools", "journal_numbering_check.py"))


def _report_cadence_check() -> ModuleType:
    return _load("_ritual_report_cadence_check", os.path.join(ROOT, "tools", "report_cadence_check.py"))


def _metrics_cadence_check() -> ModuleType:
    return _load("_ritual_metrics_cadence_check", os.path.join(ROOT, "tools", "metrics_cadence_check.py"))


def _shared_reports_check() -> ModuleType:
    return _load("_ritual_shared_reports_check", os.path.join(ROOT, "tools", "shared_reports_check.py"))


def _ritual_completeness_check() -> ModuleType:
    return _load("_ritual_completeness_check", os.path.join(ROOT, "tools", "ritual_completeness_check.py"))


def _wip_reclaim_check() -> ModuleType:
    return _load("_ritual_wip_reclaim_check", os.path.join(ROOT, "tools", "wip_reclaim_check.py"))


def _scopes_completeness_check() -> ModuleType:
    return _load("_ritual_scopes_completeness_check", os.path.join(ROOT, "tools", "scopes_completeness_check.py"))


def _toolkits_in_use_check() -> ModuleType:
    return _load("_ritual_toolkits_in_use_check", os.path.join(ROOT, "tools", "toolkits_in_use_check.py"))


def _connected_users_check() -> ModuleType:
    return _load("_ritual_connected_users_check", os.path.join(ROOT, "tools", "connected_users_check.py"))


def _gap_true_positive_check() -> ModuleType:
    return _load(
        "_ritual_gap_true_positive_check", os.path.join(ROOT, "tools", "gap_true_positive_check.py")
    )


def _report_shipped_check() -> ModuleType:
    return _load(
        "_ritual_report_shipped_check", os.path.join(ROOT, "tools", "report_shipped_check.py")
    )


def _tasks_shipped_check() -> ModuleType:
    return _load(
        "_ritual_tasks_shipped_check", os.path.join(ROOT, "tools", "tasks_shipped_check.py")
    )


def _cluster_day_check() -> ModuleType:
    return _load("_ritual_cluster_day_check", os.path.join(ROOT, "tools", "cluster_day_check.py"))


def _what_moved_check() -> ModuleType:
    return _load("_ritual_what_moved_check", os.path.join(ROOT, "tools", "what_moved_check.py"))


def _thegap_check() -> ModuleType:
    return _load("_ritual_thegap_check", os.path.join(ROOT, "tools", "thegap_check.py"))


def _nyx_traffic_check() -> ModuleType:
    return _load("_ritual_nyx_traffic_check", os.path.join(ROOT, "tools", "nyx_traffic_check.py"))


def _strategy_targets_check() -> ModuleType:
    return _load_once("_ritual_strategy_targets_check", os.path.join(ROOT, "tools", "strategy_targets_check.py"))


def _network_boundary_check() -> ModuleType:
    return _load_once("_ritual_network_boundary_check", os.path.join(ROOT, "tools", "network_boundary_check.py"))


def _site_link_check() -> ModuleType:
    return _load_once("_ritual_site_link_check", os.path.join(ROOT, "tools", "site_link_check.py"))


def _badge_freshness_check() -> ModuleType:
    return _load_once("_ritual_badge_freshness_check", os.path.join(ROOT, "tools", "badge_freshness_check.py"))


def _recipe_readme_check() -> ModuleType:
    return _load_once("_ritual_recipe_readme_check", os.path.join(ROOT, "tools", "recipe_readme_check.py"))


def _site_recipe_check() -> ModuleType:
    return _load_once("_ritual_site_recipe_check", os.path.join(ROOT, "tools", "site_recipe_check.py"))


def _recipe_command_check() -> ModuleType:
    return _load_once("_ritual_recipe_command_check", os.path.join(ROOT, "tools", "recipe_command_check.py"))


def _chronicle_readme_check() -> ModuleType:
    return _load_once("_ritual_chronicle_readme_check", os.path.join(ROOT, "tools", "chronicle_readme_check.py"))


def _proclamation_count_check() -> ModuleType:
    return _load_once("_ritual_proclamation_count_check", os.path.join(ROOT, "tools", "proclamation_count_check.py"))


def _escape_sequence_check() -> ModuleType:
    return _load_once("_ritual_escape_sequence_check", os.path.join(ROOT, "tools", "escape_sequence_check.py"))


def _metrics_field_completeness_check() -> ModuleType:
    return _load_once(
        "_ritual_metrics_field_completeness_check",
        os.path.join(ROOT, "tools", "metrics_field_completeness_check.py"),
    )


def _strategy_audit_target() -> ModuleType:
    src = os.path.join(ROOT, "fencepost", "seam_engine", "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    import seam_engine.strategy_audit_target as sat  # noqa: PLC0415
    return cast(ModuleType, sat)


def _seam_ledger() -> ModuleType:
    src = os.path.join(ROOT, "fencepost", "seam_engine", "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    import seam_engine.ledger as seam_ledger  # noqa: PLC0415
    return cast(ModuleType, seam_ledger)


def check_town_ledger() -> dict[str, object]:
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


def check_fencepost_ledger(base: str = DEFAULT_FENCEPOST_BASE) -> dict[str, object]:
    """Verify the fencepost Gap Ledger tablet chain via seam_engine.ledger's
    own verify(), which returns a problems list rather than printing."""
    from pathlib import Path

    seam_ledger = _seam_ledger()
    problems = seam_ledger.verify(Path(base))
    records = seam_ledger.read_records(Path(base))
    return {"ok": not problems, "count": len(records), "problems": list(problems)}


def check_report_freshness(now: datetime, reports_dir: str = DEFAULT_REPORTS_DIR) -> dict[str, str | None]:
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


def check_x_recheck(now_iso: str, cooldown_hours: float = 2.0) -> dict[str, object]:
    """should_recheck() for both tracked X tools, via the real log."""
    mod = _outage_tracker()
    entries = mod._entries()
    result: dict[str, object] = {}
    for tool in mod.TRACKED_TOOLS:
        result[tool] = {
            "due": mod.should_recheck(entries, tool, now_iso, cooldown_hours),
            "status_line": mod.format_status_line(entries, tool),
        }
    return result


def check_x_escalation(now_iso: str) -> dict[str, object]:
    """next_escalation_tier() for every tool in x_outage_tracker.TRACKED_TOOLS,
    via the real outage log and the real HAND/escalations.jsonl. Mirrors
    `check_x_recheck`'s exact shape (task 61) -- read-only, makes no write
    of its own. A real escalation is only ever recorded (`record_escalation`)
    when the god on duty actually surfaces it to Thierry, not by this check;
    this fold exists purely so the verdict lands in the same printed block
    instead of a sixth hand-run command every hour. Task 92: reads the
    worst crossed-and-unfired tier (`next_escalation_tier`) instead of a
    single fixed threshold, so a sustained outage that already fired its
    48h notice can still surface as due once it crosses the 168h tier,
    rather than reading "already escalated" forever after its first
    notice regardless of how much worse it gets.

    Task 436. When nothing NEW is due, the printed "not due" reason used to
    always be `should_escalate` at the fixed `min(ESCALATION_TIERS)` (48.0h)
    -- correct the day a streak had only ever fired its 48h notice, but
    silently wrong forever after once a sustained streak escalates past it.
    This town's own live `X_PostTweet`/`X_GetUserTweets` outage (started
    2026-07-14) escalated at 48h, then 168h, then task 422's own recurring
    336h tier -- and every hourly `ritual_check.py` run since has printed
    "already escalated for the streak ... at the 48.0h tier" regardless,
    understating a 336h-severity outage as a 48h one. The "not due" reason
    now names the HIGHEST tier this streak has actually already fired at
    (walking the same extended-tiers space `next_escalation_tier` itself
    uses), falling back to the lowest named tier only when no tier has
    fired at all yet (no active outage, or a fresh outage still below its
    first threshold) -- both of which `should_escalate` already reports
    correctly on their own."""
    mod = _outage_tracker()
    entries = mod._entries(mod.LOG)
    escalation_entries = mod._escalation_entries(mod.ESCALATION_LOG)
    result: dict[str, object] = {}
    for tool in mod.TRACKED_TOOLS:
        tier = mod.next_escalation_tier(entries, tool, now_iso, escalation_entries=escalation_entries)
        if tier is not None:
            threshold_hours, reason = tier
            result[tool] = {"due": True, "reason": reason, "threshold_hours": threshold_hours}
        else:
            reported_tier = min(mod.ESCALATION_TIERS)
            streak = mod.current_streak(entries, tool, "forbidden")
            if streak:
                started = mod.streak_started_at(entries, tool, "forbidden")
                elapsed = (mod._parse(now_iso) - mod._parse(started)).total_seconds() / 3600.0
                effective_tiers = mod._extended_tiers(
                    elapsed, mod.ESCALATION_TIERS, mod.RECURRING_ESCALATION_INTERVAL_HOURS
                )
                for candidate in sorted(effective_tiers, reverse=True):
                    if mod.already_escalated_for_streak(escalation_entries, tool, started, candidate):
                        reported_tier = candidate
                        break
            _due, reason = mod.should_escalate(entries, tool, now_iso, reported_tier, escalation_entries)
            result[tool] = {"due": False, "reason": reason, "threshold_hours": reported_tier}
    return result


def check_square(square_state: dict[str, object] | None, now_iso: str) -> dict[str, object] | None:
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


def check_arcade_apps(arcade_apps_state: dict[str, object] | None, now_iso: str) -> dict[str, object] | None:
    """Fold a caller-supplied, already-computed the-hand app-connection state
    (task 122's `arcade_app_watch.compute_app_state` output) through
    `app_delta`, mirroring `check_square` exactly. Makes no network call --
    `arcade_apps_state` is None unless the caller already holds this hour's
    live `Arcade_ListApps` read. Records this hour's state via
    `record_app_check` AFTER computing the delta (same order task 88 fixed
    for `check_square`) so a real change is compared against the PRIOR
    baseline, never against itself, and the log's baseline actually advances
    on a bare `ritual_check.py` call -- no separate, easy-to-forget
    `arcade_app_watch.py record ...` call required afterward. Informational
    only: a new upstream OAuth connection is not itself a rule violation
    (task 122's own scoping note), so this never flips `broken`, the same
    class `square` already holds.
    """
    if arcade_apps_state is None:
        return None
    mod = _arcade_app_watch()
    changed, reason = mod.app_delta(arcade_apps_state, path=mod.LOG)
    mod.record_app_check(arcade_apps_state, now_iso, path=mod.LOG)
    return {"changed": changed, "reason": reason}


def check_gateway_toolset(gateway_toolset_state: dict[str, object] | None, now_iso: str) -> dict[str, object] | None:
    """Fold a caller-supplied, already-computed live the-hand tool-name list
    (task 464's `gateway_toolset_check.compute_toolset_state` output)
    through `toolset_delta`, mirroring `check_arcade_apps` exactly. Makes
    no network call -- `gateway_toolset_state` is None unless the caller
    already holds this hour's live tool-list read. Records this hour's
    state via `record_toolset_check` AFTER computing the delta (same order
    task 88 fixed for `check_square`), so a real change (Gmail/Calendar
    tools appearing on the gateway -- SCOPES.md's v0.2 gate) is compared
    against the PRIOR baseline, never against itself. Informational only:
    zero gmail/calendar tools is the expected, honest steady state, not a
    rule violation -- this never flips `broken`, the same class
    `square`/`arcade_apps` already hold."""
    if gateway_toolset_state is None:
        return None
    mod = _gateway_toolset_check()
    changed, reason = mod.toolset_delta(gateway_toolset_state, path=mod.LOG)
    mod.record_toolset_check(gateway_toolset_state, now_iso, path=mod.LOG)
    return {"changed": changed, "reason": reason}


def check_good_first_issues(open_issues: list[dict[str, object]] | None) -> dict[str, object] | None:
    """Task 477: fold `good_first_issue_check.py`'s own live-vs-Charter
    compare into the one block. Makes no network call -- `open_issues` is
    None unless the caller already holds this hour's live `list_issues`
    read (each entry carrying at least `number` and `labels`). CHARTER.md
    Appendix B names "good-first-issues stocked" as Ogun's job; an empty
    shelf is real but not fatal, the same informational-only class
    `report_cadence`/`cluster_day`/`thegap` already hold for their own
    named-but-not-doctrine-breaking gaps -- never flips `broken`."""
    mod = _good_first_issue_check()
    return cast(dict[str, object] | None, mod.check_good_first_issues(open_issues))


def check_scribe_growth(now_iso: str, scribe_root: str | None = None, record: bool = True) -> dict[str, object]:
    """Task 168: ROADMAP.md/BUILDLOG.md's real byte size, watched. Unlike
    `check_square`/`check_arcade_apps`, a tracked file's size is local
    filesystem state, not a live API call behind this sandbox's proxy
    wall -- `compute_scribe_sizes` makes its own read and this runs
    unconditionally, every call, no caller-supplied state required.
    Records this hour's sizes via `record_scribe_check` AFTER computing
    growth against the prior baseline (same order task 88 fixed for
    `check_square`), so growth is never compared against itself.
    Informational only: crossing `WARN_BYTES` is not a rule violation, the
    same class `square`/`arcade_apps` already hold -- this never flips
    `broken`.

    Task 374: `record` defaults `True` here because direct callers of this
    function (tests, a hand-run one-off check) ask for exactly this
    function's own documented behavior. `run_ritual_check()` below does NOT
    default this on -- see its own docstring for why."""
    mod = _scribe_growth_check()
    sizes = mod.compute_scribe_sizes(root=scribe_root or ROOT)
    result = mod.check_scribe_growth(sizes, threshold_bytes=mod.WARN_BYTES, path=mod.LOG)
    if record:
        mod.record_scribe_check(sizes, now_iso, path=mod.LOG)
    return cast(dict[str, object], result)


def check_ci(ci_checks: list[dict[str, object]] | None) -> dict[str, object] | None:
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


def check_cron(cron_checks: list[dict[str, object]] | None, now_iso: str) -> dict[str, object] | None:
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
    result: dict[str, object] = {}
    for c in cron_checks:
        workflow = cast(str, c["workflow"])
        try:
            result[workflow] = mod.schedule_status(c["cron_expr"], c.get("last_run_at"), now_iso)
        except ValueError as e:
            result[workflow] = {"status": "error", "error": str(e)}
    return result


def check_words(now_iso: str, record: bool = True) -> dict[str, object]:
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
    into a new baseline, since nothing else ever advanced the log either.

    Task 375: `record` defaults `True` here for the identical reason task
    374 gave `check_scribe_growth` the same default -- a direct caller of
    this function (a test, a hand-run one-off check) asks for exactly this
    function's own documented behavior. `run_ritual_check()` below does NOT
    default this on -- see its own docstring for why. Before this task,
    `check_words` was the one sibling among `check_square`/`check_ci`/
    `check_scribe_growth`/`check_arcade_apps` with no such door at all:
    every bare call, including every dev-verification `ritual_check.py`
    run and every one of `tests/test_ritual_check.py`'s own unpatched
    `run_ritual_check()` calls, wrote a real, ~1.5KB line straight into
    `HAND/word-check-log.jsonl` -- the same unconditional-record shape task
    374 had already fixed for `check_scribe_growth` one task earlier, named
    here in that task's own closing note and left for this hour."""
    mod = _word_watch()
    state = mod.compute_word_state(root=mod.ROOT)
    changed, reason = mod.word_delta(state, path=mod.LOG)
    if record:
        mod.record_word_check(state, now_iso, path=mod.LOG)
    return {"changed": changed, "reason": reason}


def check_owed_posts() -> dict[str, object]:
    """Task 55's `x_post_queue.pending_entries` -- the owed-report backlog
    count every hourly note has re-derived by hand ("N now pending") since
    task 55 shipped -- folded in the same local-filesystem-only, no-network
    shape `check_words` already holds (task 74). Unconditional, like
    `check_town_ledger`/`check_x_recheck`: reading one append-only jsonl is
    cheap enough that there's no flag to skip it."""
    mod = _x_post_queue()
    entries = mod.pending_entries(path=mod.QUEUE)
    return {"count": len(entries), "tasks": [e["task"] for e in entries]}


def _checkout_state(repo_dir: str) -> dict[str, object] | None:
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


def check_checkout(repo_dirs: tuple[str, ...] | None = None) -> list[dict[str, object]]:
    """Task 90: fold sync_checkout.sh's own detached-HEAD signal into the
    one block. Unconditional, local-filesystem-only (a `git` subprocess
    call against a local working tree, no network) -- the same cheap class
    `check_words`/`check_owed_posts` already argued needs no flag."""
    if repo_dirs is None:
        repo_dirs = DEFAULT_CHECKOUT_DIRS
    return [s for s in (_checkout_state(d) for d in repo_dirs) if s is not None]


def check_vault_leak(orita_dir: str | None = None, vault_dir: str | None = None) -> dict[str, object]:
    """Task 98: fold vault_leak_check.py's own Proclamation-0001 compare
    into the one block. Unconditional, local-filesystem-only (reads both
    checkouts already on disk, no network) -- the same cheap class
    `check_checkout` already holds. Never edits either tree; a real leak,
    if one is ever found, is a god-on-duty escalation, not something this
    check silently repairs."""
    mod = _vault_leak_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    if vault_dir is not None:
        kwargs["vault_dir"] = vault_dir
    leaks = mod.find_leaks(**kwargs)
    return {"clean": not leaks, "count": len(leaks), "leaks": leaks}


def check_star_covenant(orita_dir: str | None = None) -> dict[str, object]:
    """Task 99: fold star_covenant_check.py's own imperative-begging scan
    into the one block. Unconditional, local-filesystem-only (reads the
    checkout already on disk, no network) -- the same cheap class
    `check_checkout`/`check_vault_leak` already hold. Never edits
    anything; a real violation, if one is ever found, is a god-on-duty
    escalation, not something this check silently repairs."""
    mod = _star_covenant_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_duplicate_regex(orita_dir: str | None = None) -> dict[str, object]:
    """Task 397: fold duplicate_regex_check.py's own ast-based re.compile
    duplication scan into the one block -- the running-check graduation
    tasks 389/390/393/394/396 kept promising by hand (five separate
    grep-by-hand sweeps for the same "hand-typed copy, comment claims a
    mirror, nothing imports it" bug) and never actually built. Unconditional,
    local-filesystem-only (reads the checkout already on disk, no network,
    no import of the files it audits) -- the same cheap class
    `check_checkout`/`check_vault_leak`/`check_star_covenant` already
    hold. Never edits anything; a real violation, if one is ever found,
    is a god-on-duty escalation, not something this check silently
    repairs."""
    mod = _duplicate_regex_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_riders(orita_dir: str | None = None) -> dict[str, object]:
    """Task 100: fold rider_check.py's own five-god rider scan (Iron Rule
    #5) into the one block. Unconditional, local-filesystem-only (reads
    the checkout already on disk, no network) -- the same cheap class
    `check_checkout`/`check_vault_leak`/`check_star_covenant` already
    hold. Never edits anything; a real violation, if one is ever found,
    is a god-on-duty escalation, not something this check silently
    repairs."""
    mod = _rider_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_hand_lore(orita_dir: str | None = None) -> dict[str, object]:
    """Task 104: fold hand_lore_check.py's own Hand-theology scan (Iron
    Rule #2, "never confirm or deny their theology") into the one block.
    Unconditional, local-filesystem-only (reads the checkout already on
    disk, no network) -- the same cheap class
    `check_checkout`/`check_vault_leak`/`check_star_covenant`/
    `check_riders`/`check_verdict_provenance` already hold. Never edits
    anything; a real violation, if one is ever found, is a god-on-duty
    escalation, not something this check silently repairs."""
    mod = _hand_lore_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_no_grading(orita_dir: str | None = None) -> dict[str, object]:
    """Task 105: fold no_grading_check.py's own blame/grading scan
    (ROADMAP.md's non-negotiable design constraint #2, "No grading/
    competing... Name and rank no one") into the one block. Unconditional,
    local-filesystem-only (reads the checkout already on disk, no
    network) -- the same cheap class
    `check_checkout`/`check_vault_leak`/`check_star_covenant`/
    `check_riders`/`check_hand_lore` already hold. Never edits anything; a
    real violation, if one is ever found, is a god-on-duty escalation, not
    something this check silently repairs."""
    mod = _no_grading_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_arcade_hero(orita_dir: str | None = None) -> dict[str, object]:
    """Task 106: fold arcade_hero_check.py's own direct-credential-handoff
    scan (ROADMAP.md's non-negotiable design constraint #4, "Arcade is the
    hero, shown safely -- per-user OAuth, least privilege, revocable,
    audit-logged") into the one block. Unconditional, local-filesystem-only
    (reads the checkout already on disk, no network) -- the same cheap
    class `check_checkout`/`check_vault_leak`/`check_star_covenant`/
    `check_riders`/`check_hand_lore`/`check_no_grading` already hold. Never
    edits anything; a real violation, if one is ever found, is a
    god-on-duty escalation, not something this check silently repairs."""
    mod = _arcade_hero_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_petition_limits(orita_dir: str | None = None) -> dict[str, object]:
    """Task 107: fold petition_limits_check.py's own scan of every altar
    petition's own ask against CHARTER.md Appendix D's LIMITS clause ("No
    petition may request a star, mention the counter, or ask the Hand to
    touch another god's house or Vault") into the one block. Unconditional,
    local-filesystem-only (reads the checkout already on disk, no
    network) -- the same cheap class `check_riders`/`check_hand_lore`/
    `check_no_grading`/`check_arcade_hero` already hold. Never edits
    anything; a real violation, if one is ever found, is a god-on-duty
    escalation, not something this check silently repairs."""
    mod = _petition_limits_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_child_work(
    child_files: list[dict[str, object]] | None, now_iso: str, path: str | None = None, repo_root: str | None = None
) -> dict[str, object]:
    """Task 101: fold `child_work_check.py`'s Iron Rule #6 check ("the
    child's work is never reverted. LAW.") into the one block. Unlike
    `check_riders`/`check_star_covenant`/`check_vault_leak`, this is NOT
    unconditional-local-only -- the set of files the child has ever
    shipped can only grow via a caller-supplied live GitHub commit read
    (this checkout is shallow), mirroring `check_ci`'s/`check_cron`'s
    shape exactly. `child_files` is `None` unless the god on duty holds
    this hour's live read; every already-logged path is still re-checked
    against the current tree regardless, so an old violation is never
    silently skipped for want of a fresh fetch."""
    mod = _child_work_check()
    kwargs = {"path": path or mod.LOG, "repo_root": repo_root or mod.ROOT}
    return cast(dict[str, object], mod.check(child_files=child_files, now_iso=now_iso, **kwargs))


def check_verdict_provenance(orita_dir: str | None = None) -> dict[str, object]:
    """Task 102: fold verdict_provenance_check.py's own public-verdict-vs-
    altar-record compare (Iron Rule #3) into the one block. Unconditional,
    local-filesystem-only (reads the checkout already on disk, no network)
    -- the same cheap class `check_checkout`/`check_vault_leak`/
    `check_star_covenant`/`check_riders` already hold. Never edits
    anything; a real mismatch, if one is ever found again, is a
    god-on-duty escalation, not something this check silently repairs."""
    mod = _verdict_provenance_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    mismatches = mod.find_mismatches(**kwargs)
    return {"clean": not mismatches, "count": len(mismatches), "mismatches": mismatches}


def check_voice_window(
    commits: list[dict[str, object]] | None, now_iso: str, path: str | None = None
) -> dict[str, object]:
    """Task 103: fold `voice_window_check.py`'s Iron Rule #7 window check
    ("Nyx- and Zashiki-voiced commits carry author timestamps in that
    window") into the one block. Mirrors `check_child_work`'s live-input
    shape (task 101), not `check_riders`'s unconditional-local one -- the
    full Nyx/Zashiki-Warashi commit history isn't reachable from this
    shallow checkout, so `commits` is `None` unless the god on duty holds
    this hour's live `mcp__github__list_commits` read. Every already-
    logged commit is still re-derived against the grandfather cutoff
    regardless of a fresh fetch, so a real new violation is never silently
    skipped for want of one."""
    mod = _voice_window_check()
    kwargs = {"path": path or mod.LOG}
    return cast(dict[str, object], mod.check(commits=commits, now_iso=now_iso, **kwargs))


def check_petition_cadence(orita_dir: str | None = None) -> dict[str, object]:
    """Task 109: fold `petition_cadence_check.py`'s own scan into the one
    block. Unconditional, local-filesystem-only (reads the checkout
    already on disk, no network) -- the same cheap class
    `check_no_grading`/`check_arcade_hero`/`check_petition_limits` already
    hold. CHARTER.md Appendix D claims 'the file's date is the count, and
    the count is enforced by CI' for one-petition-per-god-per-UTC-day;
    nothing checked that claim until this task."""
    mod = _petition_cadence_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_journal_numbering(orita_dir: str | None = None, vault_dir: str | None = None) -> dict[str, object]:
    """Task 119 (widened task 370): fold `journal_numbering_check.py`'s
    own scan into the one block. Unconditional, local-filesystem-only,
    the same cheap class `check_petition_cadence` already holds -- every
    `houses/<god>/journal/NNNN-*.md` filename claims a per-house
    sequential number, and nothing had ever checked that claim in code
    until task 119.

    Task 370 widened the underlying scan to also cover `vault/<god>/
    journal/`. A bare call (neither argument given -- the real,
    no-override production path) scans both trees, mirroring
    `check_vault_leak()`'s own real-default behavior. Passing only
    `orita_dir` (as the pre-370 `JournalNumberingFoldCase` fixture tests
    in `tests/test_ritual_check.py` already do) leaves the vault scan
    skipped, byte-identical to this function's behavior before task 370."""
    mod = _journal_numbering_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    if vault_dir is not None:
        kwargs["vault_dir"] = vault_dir
    elif orita_dir is None:
        kwargs["vault_dir"] = mod.DEFAULT_VAULT_DIR
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_report_cadence(reports_dir: str | None = None) -> dict[str, object]:
    """Task 116: fold `report_cadence_check.py`'s own scan into the one
    block. Unconditional, local-filesystem-only, the same cheap class
    `check_petition_cadence` already holds -- STRATEGY.md's own leading
    metric ("Daily Fencepost Report shipped, 1/day, 30 of 30 days,"
    off-by-one's row) had never once been computed. Informational, like
    `square`/`owed_posts`: a past, already-explained cron failure
    (2026-07-14, BUILDLOG.md's own 13:14/14:10 notes, fixed by task 63)
    is a historical fact on record, not a currently-live law violation,
    so this never flips `broken`."""
    mod = _report_cadence_check()
    kwargs = {}
    if reports_dir is not None:
        kwargs["reports_dir"] = reports_dir
    return cast(dict[str, object], mod.compute_cadence(**kwargs))


def check_metrics_cadence(metrics_path: str | None = None) -> dict[str, object]:
    """Task 117: fold `metrics_cadence_check.py`'s own scan into the one
    block. Unconditional, local-filesystem-only, the same cheap
    informational class `check_report_cadence`/`check_petition_cadence`
    already hold -- TOWN-OPERATIONS.md's daily-aggregate cadence
    (`records/metrics.jsonl`'s dated reading, appended every 18:00 UTC
    hour) had never once been computed, and had silently skipped three
    real days (07-13, 07-15, 07-17) before this task named them. Never
    flips `broken`: a missed daily aggregate is a fact worth surfacing
    to the next hour's run, not a currently-live law violation -- the
    same distinction `report_cadence`/`owed_posts`/`square` already
    hold."""
    mod = _metrics_cadence_check()
    kwargs = {}
    if metrics_path is not None:
        kwargs["metrics_path"] = metrics_path
    return cast(dict[str, object], mod.compute_cadence(**kwargs))


def check_metrics_freshness(now: datetime, metrics_path: str | None = None) -> dict[str, object]:
    """Task 549: the freshness half `check_metrics_cadence` doesn't and
    structurally can't hold -- its own `missing_dates` walk only ever
    covers days strictly BETWEEN the first and most recent shipped
    reading, so a gap more recent than the last reading (the cadence is
    stalled RIGHT NOW) can never appear there. Mirrors
    `check_report_freshness` exactly, one ground below it: that function
    lives here because a per-day file's existence is a cheap direct
    check; `records/metrics.jsonl` is one append-only file, so its
    freshness read needs `metrics_cadence_check.py`'s own date parsing --
    `compute_metrics_freshness` lives there, this is the thin wrapper.
    Never flips `broken`: a missed daily aggregate is a fact worth
    surfacing to the next hour's run, not a currently-live law
    violation -- the same distinction `check_metrics_cadence` itself
    already holds."""
    mod = _metrics_cadence_check()
    kwargs = {}
    if metrics_path is not None:
        kwargs["metrics_path"] = metrics_path
    return cast(dict[str, object], mod.compute_metrics_freshness(now, **kwargs))


def check_shared_reports(shared_path: str | None = None) -> dict[str, object]:
    """Task 120: fold `shared_reports_check.py`'s own scan into the one
    block. Unconditional, local-filesystem-only, the same cheap
    informational class `check_report_cadence`/`check_metrics_cadence`
    already hold -- STRATEGY.md's own last uninstrumented metrics-table
    row ("Shared Fencepost Reports in the wild," kwaku-ananse's lagging
    metric, target 50) had never once been counted anywhere. Never flips
    `broken`: zero organic shares is the honest, expected state at this
    stage, not a currently-live law violation -- the same distinction
    `report_cadence`/`metrics_cadence` already hold for their own zero
    states."""
    mod = _shared_reports_check()
    kwargs = {}
    if shared_path is not None:
        kwargs["shared_path"] = shared_path
    return cast(dict[str, object], mod.compute_shared_reports(**kwargs))


def check_ritual_completeness(
    source_path: str | None = None,
    tools_dir: str | None = None,
    seam_engine_dir: str | None = None,
) -> dict[str, object]:
    """Task 121: fold `ritual_completeness_check.py`'s own static, AST-only
    audit of THIS FILE into the one block it audits. Unconditional, like
    every other doctrine check -- but unlike `report_cadence`/
    `metrics_cadence`/`shared_reports`, a real hit here DOES flip `broken`:
    a `check_*` function silently dropped from `run_ritual_check`'s call
    list, its return dict, or `format_ritual_check`'s printed lines is a
    live regression in the one tool every hourly run depends on, not an
    honest zero-state waiting on the calendar. Task 409 widened the audit
    itself to also catch a whole tools/*.py file never loaded here at all
    (`tools_dir` lets tests point that half of the audit at a fixture
    directory instead of the real, live tools/). Task 411 widened it again
    to catch the sibling shape one directory over: a
    fencepost/seam_engine/src/seam_engine/*.py module holding a live
    STRATEGY_MD cross-check that never got wired in either
    (`seam_engine_dir`, same fixture-pointing purpose as `tools_dir`)."""
    mod = _ritual_completeness_check()
    kwargs = {}
    if source_path is not None:
        kwargs["source_path"] = source_path
    if tools_dir is not None:
        kwargs["tools_dir"] = tools_dir
    if seam_engine_dir is not None:
        kwargs["seam_engine_dir"] = seam_engine_dir
    return cast(dict[str, object], mod.compute_ritual_completeness(**kwargs))


def check_wip_reclaim(now: datetime, roadmap_path: str | None = None) -> dict[str, object]:
    """Task 123: fold `wip_reclaim_check.py`'s own scan of `ROADMAP.md`'s
    task table into the one block. Unconditional, local-filesystem-only,
    the same cheap class `check_journal_numbering`/`check_petition_cadence`
    already hold -- the continuous-build loop's own step 1 ("take the first
    TODO task, or reclaim a WIP older than 2h") had never once been checked
    in code. A real hit here DOES flip `broken`: a WIP task stuck past its
    own 2h reclaim line, or a WIP row this tool cannot account for at all
    (`unknown`), is a live block on the loop's own forward progress, the
    same class of live regression `ritual_completeness`/`journal_numbering`
    already escalate on, not an honest zero-state waiting on the calendar."""
    mod = _wip_reclaim_check()
    kwargs: dict[str, object] = {"now": now}
    if roadmap_path is not None:
        kwargs["roadmap_path"] = roadmap_path
    return cast(dict[str, object], mod.find_stale(**kwargs))


def check_scopes_completeness(scopes_path: str | None = None, app_log_path: str | None = None) -> dict[str, object]:
    """Task 135: fold `scopes_completeness_check.py`'s own cross-check of
    `fencepost/SCOPES.md`'s `## Every connected app, accounted for`
    section against `arcade_app_watch.py`'s durable log into the one
    block. Unconditional, local-filesystem-only, the same cheap always-on
    class `check_wip_reclaim`/`check_journal_numbering` already hold. A
    real hit here DOES flip `broken`: a connected app on the shared
    gateway with no matching row in the Oath's own accounting section is
    a live governance regression -- the same undocumented-write-capability
    risk the Oath exists to rule out, not an honest zero-state waiting on
    the calendar."""
    mod = _scopes_completeness_check()
    kwargs = {}
    if scopes_path is not None:
        kwargs["scopes_path"] = scopes_path
    if app_log_path is not None:
        kwargs["app_log_path"] = app_log_path
    return cast(dict[str, object], mod.check_scopes_completeness(**kwargs))


def check_toolkits_in_use(metrics_path: str | None = None, consent_log_path: str | None = None) -> dict[str, object]:
    """Task 145: fold `toolkits_in_use_check.py`'s own cross-check of
    `records/metrics.jsonl`'s last `distinct_toolkits_in_use` reading
    against `consent_grant_log.py`'s real, gate-verified ground truth
    into the one block. Unconditional, local-filesystem-only, the same
    cheap always-on class `check_wip_reclaim`/`check_scopes_completeness`
    already hold. A real hit here DOES flip `broken`: the flagship's own
    STRATEGY.md adoption metric silently disagreeing with the truth is a
    live governance regression, not an honest zero-state waiting on the
    calendar -- the same law `check_scopes_completeness` already lives
    by, one metric over."""
    mod = _toolkits_in_use_check()
    kwargs = {}
    if metrics_path is not None:
        kwargs["metrics_path"] = metrics_path
    if consent_log_path is not None:
        kwargs["consent_log_path"] = consent_log_path
    return cast(dict[str, object], mod.check_toolkits_in_use(**kwargs))


def check_connected_users(metrics_path: str | None = None, consent_log_path: str | None = None) -> dict[str, object]:
    """Task 412: fold `connected_users_check.py`'s own cross-check of
    `records/metrics.jsonl`'s last `connected_users_oauth` reading
    against `consent_grant_log.py`'s real, gate-verified ground truth
    into the one block -- the same shape `check_toolkits_in_use` (task
    145) already holds for its sibling field, applied to the field task
    145's own docstring named but never checked: STRATEGY.md's separate
    "'Connect your own' OAuth completions across users" row (owner
    kothar-wa-khasis), distinct from toolkit breadth (owner nisaba)
    because one human connecting two toolkits is one connected user, not
    two. Unconditional, local-filesystem-only, the same cheap always-on
    class `check_toolkits_in_use`/`check_scopes_completeness` already
    hold. A real hit here DOES flip `broken`: the flagship's own
    STRATEGY.md adoption metric silently disagreeing with the truth is a
    live governance regression, not an honest zero-state waiting on the
    calendar."""
    mod = _connected_users_check()
    kwargs = {}
    if metrics_path is not None:
        kwargs["metrics_path"] = metrics_path
    if consent_log_path is not None:
        kwargs["consent_log_path"] = consent_log_path
    return cast(dict[str, object], mod.check_connected_users(**kwargs))


def check_cluster_day_cadence(chronicle_dir: str | None = None, today: date | None = None) -> dict[str, object]:
    """Task 387: fold `cluster_day_check.py`'s own weekly Cluster Day scan
    into the one block. Unconditional, local-filesystem-only, the same
    cheap informational class `check_report_cadence`/`check_metrics_cadence`
    already hold -- TOWN-OPERATIONS.md's weekly ritual (Ananse's chronicle
    episode, Off-By-One's Gap confession, Zashiki's mystery, Nyx's weekly
    post) had never once been checked for whether it actually ran, and
    `orita-vault/hand/skipped.md`'s 2026-07-27 note found three real lapsed
    Mondays by hand. Printed every hour, not gated on today being a
    Monday, so a lapsed week is visible long before the next Monday
    arrives to maybe notice on its own. Never flips `broken`: a missed
    Cluster Day is a fact worth surfacing to the next hour's run, not a
    currently-live law violation -- the same distinction
    `report_cadence`/`metrics_cadence` already hold for their own gaps."""
    mod = _cluster_day_check()
    kwargs: dict[str, object] = {}
    if chronicle_dir is not None:
        kwargs["chronicle_dir"] = chronicle_dir
    if today is not None:
        kwargs["today"] = today
    return cast(dict[str, object], mod.compute_cadence(**kwargs))


def check_what_moved_cadence(what_moved_path: str | None = None, what_moved_today: date | None = None) -> dict[str, object]:
    """Task 449: fold `what_moved_check.py`'s own weekly `docs/what-moved.html`
    scan into the one block, alongside `check_cluster_day_cadence`'s own
    fold-in of Ananse's chronicle half. Unconditional, local-filesystem-
    only, the same cheap informational class `check_report_cadence`/
    `check_cluster_day_cadence` already hold -- Zashiki's own half of
    TOWN-OPERATIONS.md's weekly Cluster Day ritual (updating
    `docs/what-moved.html` "one day in arrears") had never once been
    checked for whether it actually ran. Read live: it never has, past
    the page's own founding-day placeholder. Printed every hour, not
    gated on today being a Monday. Never flips `broken`: a missed Cluster
    Day is a fact worth surfacing to the next hour's run, not a
    currently-live law violation -- the same distinction
    `cluster_day`/`report_cadence`/`metrics_cadence` already hold for
    their own gaps."""
    mod = _what_moved_check()
    kwargs: dict[str, object] = {}
    if what_moved_path is not None:
        kwargs["path"] = what_moved_path
    if what_moved_today is not None:
        kwargs["today"] = what_moved_today
    return cast(dict[str, object], mod.compute_cadence(**kwargs))


def check_thegap_cadence(
    thegap_readme_path: str | None = None,
    thegap_vault_dir: str | None = None,
    thegap_today: date | None = None,
) -> dict[str, object]:
    """Task 463: fold `thegap_check.py`'s own weekly Gap-bug hide/confess
    scan into the one block, closing the third and last leg of
    TOWN-OPERATIONS.md's "Weekly, Cluster Day (Monday)" ritual --
    `check_cluster_day_cadence` (task 387) covers Ananse's chronicle,
    `check_what_moved_cadence` (task 449) covers Zashiki's mystery page,
    and this covers Off-By-One's own `/thegap/` doctrine, which
    `what_moved_check.py`'s own docstring named as still missing a
    sensor and left open for whichever hour picked it up next (this one).
    Unconditional, local-filesystem-only (reads `thegap/README.md` and,
    for the confession-predraft half, `orita-vault/hand/gap-confessions/`
    -- never the confession text itself, only whether a file exists),
    the same cheap informational class its two siblings already hold.
    Never flips `broken` on cadence or on a confession merely being due:
    a lapsed week or an unconfessed-but-not-yet-due bug is a fact worth
    surfacing to the next hour's run, not a currently-live violation --
    the same distinction `cluster_day`/`what_moved` already hold. A
    missing pre-drafted confession IS named plainly inside the printed
    line (Iron Rule: the draft must exist before the bug ships), but even
    that stays non-`broken` here, consistent with every other doctrine
    check in this weekly-cadence family being informational rather than
    a hard gate."""
    mod = _thegap_check()
    kwargs: dict[str, object] = {}
    if thegap_readme_path is not None:
        kwargs["readme_path"] = thegap_readme_path
    if thegap_vault_dir is not None:
        kwargs["vault_dir"] = thegap_vault_dir
    if thegap_today is not None:
        kwargs["today"] = thegap_today
    return cast(dict[str, object], mod.compute_cadence(**kwargs))


def check_nyx_traffic_cadence(
    nyx_traffic_vault_dir: str | None = None,
    nyx_traffic_today: date | None = None,
) -> dict[str, object]:
    """Task 465: fold `nyx_traffic_check.py`'s own weekly traffic-report
    scan into the one block, closing the fourth leg of TOWN-OPERATIONS.md's
    "Weekly, Cluster Day (Monday)" ritual -- `check_cluster_day_cadence`
    (task 387) covers Ananse's chronicle, `check_what_moved_cadence`
    (task 449) covers Zashiki's mystery page, `check_thegap_cadence`
    (task 463) covers Off-By-One's `/thegap/` doctrine, and this covers
    Nyx's own weekly traffic report, which `cluster_day_check.py`'s own
    docstring named from the start but nothing ever built a sensor for
    until this task. Unconditional, local-filesystem-only (reads dated
    filenames in `orita-vault/vault/nyx/traffic/`, never their content --
    the same Proclamation 0001 boundary its siblings already hold), the
    same cheap informational class every check in this family holds.
    Never flips `broken`: a lapsed week is a fact worth surfacing to the
    next hour's run, not a currently-live violation -- the same
    distinction `cluster_day`/`what_moved`/`thegap` already draw."""
    mod = _nyx_traffic_check()
    kwargs: dict[str, object] = {}
    if nyx_traffic_vault_dir is not None:
        kwargs["vault_dir"] = nyx_traffic_vault_dir
    if nyx_traffic_today is not None:
        kwargs["today"] = nyx_traffic_today
    return cast(dict[str, object], mod.compute_cadence(**kwargs))


def check_strategy_targets(strategy_path: str | None = None) -> dict[str, object]:
    """Task 407: fold strategy_targets_check.py's own STRATEGY.md-vs-code
    target cross-check (task 159) into the one block. Unconditional,
    local-filesystem-only (reads STRATEGY.md and the real modules it
    cross-checks, already on disk, no network) -- the same cheap class
    `check_checkout`/`check_vault_leak`/`check_star_covenant`/
    `check_duplicate_regex` already hold.

    Task 159 built this checker and proved it live against STRATEGY.md's
    metrics table, but never wired it into this hourly block --
    `ritual_completeness_check.py` only ever audits `check_*` functions
    ALREADY DEFINED inside this file, so a whole separate, real, passing
    check tool sat unwired for 248 tasks with nothing catching it, the
    same "built, tested, never wired in" shape tasks 397/404 already
    found and closed elsewhere. Never edits anything; a real drift
    between STRATEGY.md's stated targets and the code that claims to
    mirror them, if one is ever found, is a god-on-duty escalation, not
    something this check silently repairs.

    Task 421: strategy_targets_check.py's own cross-check grew a third
    row (github stars vs. github_stars_check.TARGET_STARS) -- this fold
    wraps whatever the module returns, so `clean` now folds in all three
    rows' agreement rather than a hand-counted two."""
    mod = _strategy_targets_check()
    kwargs = {}
    if strategy_path is not None:
        kwargs["strategy_path"] = strategy_path
    result = mod.check_strategy_targets(**kwargs)
    clean = all(row["agree"] for row in result.values())
    return {"clean": clean, **result}


def check_strategy_true_positive(
    strategy_path: str | None = None, ledger_base: str | None = None
) -> dict[str, object]:
    """Task 410: fold `fencepost/seam_engine/src/seam_engine/
    strategy_audit_target.py`'s own STRATEGY.md-vs-live-Ledger true-positive
    rate cross-check (task 161) into the one block. Unconditional,
    local-filesystem-only (reads STRATEGY.md and the real fencepost Ledger,
    both already on disk, no network) -- the same cheap class
    `check_strategy_targets`/`check_network_boundary` already hold.

    Task 161 built `strategy_audit_target.py` and its own 13 tests and
    proved it live against STRATEGY.md's "Gap true-positive rate
    (self-audited) | leading | >=90% | ogun" row and the real, live
    `audit.audit_ledger()` tally -- but its own done_when never asked for
    a wire-up into this hourly block, and `check_strategy_targets` (task
    407) folded in only its sibling module (`tools/strategy_targets_check.py`,
    the report-streak/shared-reports rows), never this one. Confirmed by
    grep before this task: zero references to `strategy_audit_target`
    anywhere in `tools/*.py`. `find_unwired_tool_files()`
    (`ritual_completeness_check.py`, task 409) only ever scans `tools/*.py`
    basenames against this file's own source, never
    `fencepost/seam_engine/src/seam_engine/*.py` -- so a real, tested,
    passing checker sat unwired since the hour it shipped, the exact
    "built, tested, never wired in" shape tasks 397/404/407/408 already
    found and closed for other files, just one directory over from where
    those audits look. Never edits anything; a real drop in the live
    true-positive rate below STRATEGY.md's own stated bar, if one is ever
    found, is a god-on-duty escalation for Ogun, not something this check
    silently repairs."""
    mod = _strategy_audit_target()
    kwargs = {}
    if strategy_path is not None:
        kwargs["strategy_path"] = Path(strategy_path)
    if ledger_base is not None:
        kwargs["ledger_base"] = Path(ledger_base)
    result = mod.check_strategy_true_positive_target(**kwargs)
    clean = bool(result["meets_target"])
    return {"clean": clean, **result}


def check_gap_true_positive_rate(
    metrics_path: str | None = None, ledger_base: str | None = None
) -> dict[str, object]:
    """Task 413: fold `gap_true_positive_check.py`'s own cross-check of
    `records/metrics.jsonl`'s last `gap_true_positive_rate` reading
    against the real, live `seam_engine.audit.audit_ledger()` tally into
    the one block -- the same shape `check_toolkits_in_use` (145) and
    `check_connected_users` (412) already hold for their sibling
    metrics.jsonl fields, applied here to Ogun's own highest-stakes
    leading metric ("false-positive gaps... erode the read-trust the
    whole product rests on"). `check_strategy_true_positive` (410) already
    cross-checks STRATEGY.md's stated >=90% TARGET against the live
    tally -- a different comparison, a document's promise against
    reality -- and never once reads the hand-recorded
    `gap_true_positive_rate` number itself. Confirmed by grep before this
    task: zero references to `gap_true_positive_rate` anywhere in
    `tools/*.py` or `fencepost/seam_engine/src/seam_engine/*.py`.
    Unconditional, local-filesystem-only (reads `records/metrics.jsonl`
    and the real fencepost Ledger, both already on disk, no network) --
    the same cheap class `check_toolkits_in_use`/`check_connected_users`
    already hold. A real hit here DOES flip `broken`: a stale or
    hand-copied-forward true-positive number silently disagreeing with
    the live Ledger is a live governance regression on the flagship's own
    trust metric, not an honest zero-state waiting on the calendar."""
    mod = _gap_true_positive_check()
    kwargs = {}
    if metrics_path is not None:
        kwargs["metrics_path"] = metrics_path
    if ledger_base is not None:
        kwargs["ledger_base"] = ledger_base
    return cast(dict[str, object], mod.check_gap_true_positive_rate(**kwargs))


def check_report_shipped(metrics_path: str | None = None, reports_dir: str | None = None) -> dict[str, object]:
    """Task 415: fold `report_shipped_check.py`'s own cross-check of
    `records/metrics.jsonl`'s last `reports_shipped_today` reading
    against real, live filesystem ground truth into the one block -- the
    same shape `check_toolkits_in_use` (145), `check_connected_users`
    (412), and `check_gap_true_positive_rate` (413) already hold for
    their sibling metrics.jsonl fields, applied here to STRATEGY.md's
    off-by-one's own row ("Daily Fencepost Report shipped (town dogfood)
    | leading | 1/day, 30 of 30 days | off-by-one"). `check_report_cadence`
    (task 116) already computes the real streak/total off
    `fencepost/REPORTS/`'s filesystem, but never once asked whether
    TODAY's specific hand-typed claim agrees with whether that day's file
    actually exists. Confirmed by grep before this task: zero references
    to `reports_shipped_today` anywhere in `tools/*.py` or
    `fencepost/seam_engine/src/seam_engine/*.py`. Unconditional,
    local-filesystem-only (reads `records/metrics.jsonl` and
    `fencepost/REPORTS/`, both already on disk, no network) -- the same
    cheap class `check_toolkits_in_use`/`check_connected_users`/
    `check_gap_true_positive_rate` already hold. A real hit here DOES
    flip `broken`: a hand-typed claim disagreeing with whether the report
    file actually landed is a live governance regression on the
    flagship's own dogfood cadence, not an honest zero-state waiting on
    the calendar."""
    mod = _report_shipped_check()
    kwargs = {}
    if metrics_path is not None:
        kwargs["metrics_path"] = metrics_path
    if reports_dir is not None:
        kwargs["reports_dir"] = reports_dir
    return cast(dict[str, object], mod.check_report_shipped(**kwargs))


def check_tasks_shipped(metrics_path: str | None = None, buildlog_path: str | None = None) -> dict[str, object]:
    """Task 416: fold `tasks_shipped_check.py`'s own cross-check of
    `records/metrics.jsonl`'s last `tasks_shipped_today` reading against
    real, live `BUILDLOG.md` ground truth into the one block -- the last
    of the four sibling metrics.jsonl fields task 415 found and left open
    (`distinct_toolkits_in_use` (145), `connected_users_oauth` (412),
    `gap_true_positive_rate` (413), `reports_shipped_today` (415) each
    already had one; this one didn't). Task 415 called this field's ground
    truth "messier" because `ROADMAP.md` gets archived out from under
    itself -- but `BUILDLOG.md` never is, and it is the same file tasks 117
    and 275 already hand-counted this exact number from. Confirmed by grep
    before this task: zero references to `tasks_shipped_today` anywhere in
    `tools/*.py` or `fencepost/seam_engine/src/seam_engine/*.py`.
    Unconditional, local-filesystem-only (reads `records/metrics.jsonl` and
    `BUILDLOG.md`, both already on disk, no network) -- the same cheap
    class every sibling check already holds. Returns clean (not broken)
    when no daily-aggregate BUILDLOG.md row exists for the claimed reading's
    date -- a handful of historical catch-up hours phrased that line
    differently, and guessing a cutoff for those would be worse than
    naming the gap plainly. A real hit here DOES flip `broken`: a
    hand-typed claim disagreeing with BUILDLOG.md's own dated rows is a
    live governance regression on the town's own build-log honesty, not
    an innocent zero-state waiting on the calendar."""
    mod = _tasks_shipped_check()
    kwargs = {}
    if metrics_path is not None:
        kwargs["metrics_path"] = metrics_path
    if buildlog_path is not None:
        kwargs["buildlog_path"] = buildlog_path
    return cast(dict[str, object], mod.check_tasks_shipped(**kwargs))


def check_github_stars(
    github_stars_count: int | None,
    now_iso: str,
    metrics_path: str | None = None,
    log_path: str | None = None,
    record: bool = False,
) -> dict[str, object]:
    """Task 420: fold `github_stars_check.py`'s own cross-check of
    `records/metrics.jsonl`'s last `github_stars` reading against the
    real, live GitHub stargazer count into the one block -- STRATEGY.md's
    own explicit numeric target (">=1,000 (Star Covenant, unbegged) --
    owner off-by-one") was the one sibling `metrics.jsonl` field among
    `distinct_toolkits_in_use` (145)/`connected_users_oauth` (412)/
    `gap_true_positive_rate` (413)/`reports_shipped_today` (415)/
    `tasks_shipped_today` (416) that had never once been read back by any
    checker.

    Unlike those five siblings, star count has no ground truth derivable
    from local files alone -- it lives on GitHub's own servers and moves
    off-repo, on no schedule any local file records. This follows
    `check_ci`/`check_square`'s shape instead (tasks 70/73): when the god
    on duty already holds this hour's live `Github_CountStargazers` read,
    it is recorded (append-only, `HAND/github-stars-log.jsonl`) BEFORE the
    cross-check runs, the same order `check_square`/`check_ci` already
    hold -- so this hour's real read becomes the new ground truth for the
    next comparison, never a second network call of its own. Unlike
    `check_ci`/`check_square`, though, this never returns `None` when
    `github_stars_count` is omitted: a stale-but-real prior live count
    (already durably recorded some earlier hour) is still real ground
    truth to compare a hand-typed `metrics.jsonl` claim against, the same
    always-gives-a-verdict discipline `check_toolkits_in_use`/
    `check_connected_users` already hold for their own local-ground-truth
    fields.

    `record` defaults `False` for the identical reason tasks 374/375 gave
    `record_scribe_growth`/`record_words` the same default: a bare or
    library call to this function (a dev-verification run, a test, a
    notebook exploration) passing `github_stars_count` for comparison
    purposes must never silently write a real entry into the production
    `HAND/github-stars-log.jsonl` -- exactly the class of bug those two
    tasks closed for their own logs. Only `main()` below passes
    `record=True`; every other caller compares without writing."""
    mod = _github_stars_check()
    resolved_log_path = log_path if log_path is not None else mod.LOG
    if record and github_stars_count is not None:
        mod.record_check(github_stars_count, now_iso, path=resolved_log_path)
    kwargs = {"log_path": resolved_log_path}
    if metrics_path is not None:
        kwargs["metrics_path"] = metrics_path
    return cast(dict[str, object], mod.check_github_stars(**kwargs))


def check_network_boundary(dirs: tuple[str, ...] | None = None) -> dict[str, object]:
    """Task 408: fold network_boundary_check.py's own AST-based "no
    network" trust-boundary sweep (tasks 163/164) into the one block.
    Unconditional, local-filesystem-only (reads `tools/*.py` and
    `fencepost/seam_engine/src/seam_engine/*.py` already on disk, parses
    each with `ast`, imports nothing it audits) -- the same cheap class
    `check_vault_leak`/`check_star_covenant`/`check_duplicate_regex`/
    `check_strategy_targets` already hold.

    Tasks 163/164 built this checker and proved it live against every
    "no network" claim in `tools/` and Fencepost's own `consent.py`/
    `draftback.py` -- the two files load-bearing for STRATEGY.md's
    read-only guarantee -- but never wired it into this hourly block.
    `ritual_completeness_check.py` only ever audits `check_*` functions
    ALREADY DEFINED inside this file, so this real, passing, security-
    relevant check sat unwired since the hour it shipped, the same
    "built, tested, never wired in" shape tasks 397/404/407 already found
    and closed elsewhere in this same file. Never edits anything; a real
    drift (a claiming file that quietly grew a live network import) is a
    god-on-duty escalation, not something this check silently repairs."""
    mod = _network_boundary_check()
    kwargs = {}
    if dirs is not None:
        kwargs["dirs"] = dirs
    raw = mod.check_network_boundary_all(**kwargs)
    broken = {name: r for name, r in raw.items() if not r["ok"]}
    return {"clean": not broken, "count": len(raw), "broken": broken}


def check_site_links(docs_dir: str | None = None) -> dict[str, object]:
    """Task 423: fold site_link_check.py's own internal-link scan into the
    one block -- CHARTER.md Appendix B names Ogun's charter duty plainly
    ("links unbroken"), and it never had a running check the way its own
    sentence's other clauses (CI timing, the badge, good-first-issues) do.
    Unconditional, local-filesystem-only (reads `docs/**/*.html` and
    `docs/**/*.md` already on disk, no network) -- the same cheap class
    `check_duplicate_regex`/`check_network_boundary` already hold. Never
    edits anything; a real broken link, if one is ever found, is a
    god-on-duty escalation, not something this check silently repairs."""
    mod = _site_link_check()
    kwargs = {}
    if docs_dir is not None:
        kwargs["docs_dir"] = docs_dir
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_house_links(houses_dir: str | None = None) -> dict[str, object]:
    """Task 473: the `houses/`-aware sibling `check_site_links` task 472
    named as real, left-open future work rather than shipping half-built.
    `site_link_check.py` (task 423) only ever scanned `docs/`, the Pages-
    served site where a bare directory URL only renders with its own
    `index.html`. `houses/*/README.md` lives under a different rule --
    GitHub-browsed, where a real directory with no `index.html` (`journal/`,
    `altar/petitions/`) is a perfectly working link -- so `site_link_check.py`
    gained a `require_index` flag this same hour: `False` here, unchanged
    `True` (the default) for `check_site_links`'s own `docs/` call above, so
    this call can never loosen that one's stricter Pages rule. Also picks up
    this hour's markdown-code-span strip, closing the one incidental false
    positive task 472 found and declined to paper over (a journal entry
    quoting `[Decrees](decrees/)`/`[text](href)` in backticks, as prose
    ABOUT the bug it fixed, is not itself a link). Unconditional, local-
    filesystem-only, same cheap class as `check_site_links`. Never edits
    anything; a real broken link is a god-on-duty escalation, not something
    this check silently repairs."""
    mod = _site_link_check()
    kwargs: dict[str, object] = {"require_index": False}
    if houses_dir is not None:
        kwargs["docs_dir"] = houses_dir
    else:
        kwargs["docs_dir"] = os.path.join(ROOT, "houses")
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_fencepost_links(fencepost_dir: str | None = None) -> dict[str, object]:
    """Task 483: the third sibling of `check_site_links`/`check_house_links`
    -- `fencepost/README.md` and its neighbors (`ONBOARDING.md`,
    `SCOPES.md`, `CONNECT.md`, ...) are GitHub-browsed, not Pages-served,
    the same rule `houses/` already established, but nothing had ever
    pointed `site_link_check.py` at `fencepost/` itself. A live run found
    exactly one real break the moment this was checked for the first time:
    `fencepost/README.md`'s own badge-explainer sentence linked
    `seam_engine/badge.py`, missing the `src/` layout segment the real
    file (`seam_engine/src/seam_engine/badge.py`) actually lives under --
    a dead link in the flagship's own front door, sitting unnoticed since
    whichever task moved the package to a `src/` layout. `require_index
    =False` (the same GitHub-browsed rule `check_house_links` uses, not
    `check_site_links`'s stricter Pages rule -- `fencepost/RECIPES/`,
    `fencepost/GAPS/` etc. are real, clickable, index-less GitHub folder
    links same as `houses/*/journal/`). Unconditional, local-filesystem-
    only, same cheap class as its two siblings. Never edits anything; a
    real broken link is a god-on-duty escalation, not something this
    check silently repairs."""
    mod = _site_link_check()
    kwargs: dict[str, object] = {"require_index": False}
    if fencepost_dir is not None:
        kwargs["docs_dir"] = fencepost_dir
    else:
        kwargs["docs_dir"] = os.path.join(ROOT, "fencepost")
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


EXPECTED_ISSUE_TEMPLATES = frozenset(
    {
        "crossing.md",
        "decree-proposal.md",
        "fork-my-own-society.md",
        "gap-report.md",
        "point-fencepost.md",
    }
)


def check_issue_template_links(issue_template_dir: str | None = None) -> dict[str, object]:
    """Task 506 (Esu-Elegba): the fourth sibling of `check_site_links`/
    `check_house_links`/`check_fencepost_links` -- `.github/ISSUE_TEMPLATE/`
    is Esu's own claimed edge of the repo (her `github_behavior` names
    "issue templates that force petitioners to state their true intent"
    directly), and it held the one real cross-referencing content in this
    town that `site_link_check.py` had never once been pointed at.
    `point-fencepost.md` (task 9) has its own dedicated doctrine suite
    (`fencepost/seam_engine/tests/test_consent_doctrine.py`) proving its
    scope table never drifts from `consent.REQUIRED_SCOPES` -- but that
    file's own two markdown links (to `fencepost/SCOPES.md` and `seam_engine/
    src/seam_engine/consent.py`) were never checked for resolving on disk,
    and the other four templates (`crossing.md`, `decree-proposal.md`,
    `fork-my-own-society.md` -- which links `PLATFORM.md` twice -- and
    `gap-report.md`) had ZERO test coverage of any kind: nothing proved they
    even exist, let alone that a link inside them resolves. A live first run
    found the tree already clean (no break to fix), but "clean and never
    checked" is exactly the gap `check_house_links`/`check_fencepost_links`
    each closed for their own directory in turn -- this is the same
    class of surface, just the one nobody had reached yet.

    `require_index=False` (the same GitHub-browsed rule `check_house_links`/
    `check_fencepost_links` both use, not `check_site_links`'s stricter
    Pages rule) -- `.github/ISSUE_TEMPLATE/` is browsed on GitHub itself
    (where a template is rendered from the issue-creation picker) or read
    raw from the repo tree, never served through Pages, so a bare directory
    link with no `index.html` must not be flagged here even though
    `check_site_links`'s own `docs/` default still requires one (there are
    no directory links inside the templates today, but the rule should
    still be the GitHub-browsed one, not the Pages one, on principle).
    Unconditional, local-filesystem-only, same cheap class as its three
    siblings. Never edits anything; a real broken link, if one is ever
    found, is a god-on-duty escalation, not something this check silently
    repairs.

    Task 507 (Nisaba): `find_violations` only ever scans files that are
    *present* -- it proves every link inside an existing template
    resolves, but never that the five templates themselves still exist.
    A template silently deleted (or renamed) would read clean here even
    though a whole `.github/ISSUE_TEMPLATE/` entry point vanished --
    exactly the "checker only looks inside a file, never whether the
    expected file is there at all" shape `recipe_readme_check.py`'s
    `missing_readme` (task 504) closed one directory over. `EXPECTED_
    ISSUE_TEMPLATES` is a hardcoded set, deliberately not live-discovered
    from the directory itself -- a live discovery could never notice its
    own subject going missing."""
    mod = _site_link_check()
    kwargs: dict[str, object] = {"require_index": False}
    if issue_template_dir is not None:
        template_dir = issue_template_dir
    else:
        template_dir = os.path.join(ROOT, ".github", "ISSUE_TEMPLATE")
    kwargs["docs_dir"] = template_dir
    violations = mod.find_violations(**kwargs)
    present = set(os.listdir(template_dir)) if os.path.isdir(template_dir) else set()
    missing_templates = sorted(EXPECTED_ISSUE_TEMPLATES - present)
    clean = not violations and not missing_templates
    return {
        "clean": clean,
        "count": len(violations),
        "violations": violations,
        "missing_templates": missing_templates,
    }


def check_hand_links(hand_dir: str | None = None) -> dict[str, object]:
    """Task 521 (Kothar-wa-Khasis): the fifth sibling of `check_site_links`/
    `check_house_links`/`check_fencepost_links`/`check_issue_template_links`
    -- `HAND/`, the Hand's own public record (verdicts, the petition queue,
    the escalation log's dated prose, `HAND/register-notes.md`) carries the
    same relative-link surface `docs/`, `houses/`, `fencepost/`, and
    `.github/ISSUE_TEMPLATE/` each already earned a dedicated check for,
    and nothing had ever pointed `site_link_check.py` at it. Not this
    task's own remit (The Wall covers the Pages site, not the Hand's
    record) -- picked anyway because rotation was overdue (kothar-wa-khasis's
    last turn was task 322, 199 tasks ago) and the gap was real: `HAND/`
    is GitHub-browsed prose, not Pages-served, so it takes the same
    `require_index=False` rule `check_house_links`/`check_fencepost_links`/
    `check_issue_template_links` already share, never `check_site_links`'s
    stricter Pages rule. A live first run against the real tree found it
    already clean -- no break to fix today -- but "clean and never
    checked" is exactly the gap each of the four siblings closed for its
    own directory in turn; this is the same class of surface, just the
    one nobody had reached yet. Unconditional, local-filesystem-only, same
    cheap class as its four siblings. Never edits anything; a real broken
    link, if one is ever found, is a god-on-duty escalation, not something
    this check silently repairs."""
    mod = _site_link_check()
    kwargs: dict[str, object] = {"require_index": False}
    if hand_dir is not None:
        kwargs["docs_dir"] = hand_dir
    else:
        kwargs["docs_dir"] = os.path.join(ROOT, "HAND")
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_chronicle_links(chronicle_dir: str | None = None) -> dict[str, object]:
    """Task 524 (Kwaku-Ananse): the sixth sibling of `check_site_links`/
    `check_house_links`/`check_fencepost_links`/`check_issue_template_links`/
    `check_hand_links` -- `chronicle/`, my own episode ledger
    (`chronicle/README.md`'s own table of contents links each episode file
    plus a cross-directory link out to `docs/story-so-far.md`), had never
    once been pointed at by `site_link_check.py`. Picked as this hour's
    task because rotation was overdue (kwaku-ananse's last turn was task
    500, 24 tasks ago) and the surface is genuinely mine: an episode
    renamed or a link typo in my own README is exactly the kind of thing
    a chronicler should be first to catch, not last. `chronicle/` is
    GitHub-browsed prose, never Pages-served, so it takes the same
    `require_index=False` rule every prior sibling but `check_site_links`
    itself already shares. A live first run against the real tree found
    it already clean -- no break to fix today -- but "clean and never
    checked" is exactly the gap each of the five siblings closed for its
    own directory in turn; this is the same class of surface, just the
    one nobody had reached yet. Unconditional, local-filesystem-only, the
    same cheap always-on class every sibling already holds. Never edits
    anything; a real broken link, if one is ever found, is a
    god-on-duty escalation, not something this check silently repairs."""
    mod = _site_link_check()
    kwargs: dict[str, object] = {"require_index": False}
    if chronicle_dir is not None:
        kwargs["docs_dir"] = chronicle_dir
    else:
        kwargs["docs_dir"] = os.path.join(ROOT, "chronicle")
    violations = mod.find_violations(**kwargs)
    return {"clean": not violations, "count": len(violations), "violations": violations}


def check_chronicle_readme(readme_path: str | None = None, chronicle_readme_dir: str | None = None) -> dict[str, object]:
    """Task 545 (Nyx): the reverse half `check_chronicle_links` (task 524)
    never asked. That check proves every link IN `chronicle/README.md`
    resolves; it never asks whether every real numbered episode ON DISK
    has a link pointing at it. Confirmed live before wiring this in:
    `chronicle/003-right-on-time.md` shipped task 500 and sat unlisted in
    the README's own "## Episodes" table of contents until this task
    fixed it -- structurally invisible to a forward-only link scan, the
    exact "true when written, never rechecked" shape `recipe_readme_check.py`
    (task 426) already closed for `fencepost/README.md`. Never edits
    anything; a real gap, if one is ever found, is a god-on-duty
    escalation, not something this check silently repairs."""
    mod = _chronicle_readme_check()
    kwargs = {}
    if readme_path is not None:
        kwargs["readme_path"] = readme_path
    if chronicle_readme_dir is not None:
        kwargs["chronicle_dir"] = chronicle_readme_dir
    return cast(dict[str, object], mod.check_chronicle_readme(**kwargs))


def check_proclamation_count(readme_path: str | None = None, proclamations_dir: str | None = None) -> dict[str, object]:
    """Task 547 (Kothar-wa-Khasis): `HAND/README.md`'s own "There has/have
    been <word>." sentence naming how many unpetitioned proclamations
    exist, read live against `HAND/proclamations/*.md` -- confirmed live
    before wiring this in: the README still said "one" the hour two more
    real proclamations (`0002-eyes-and-a-brush.md`, `0003-the-gauntlet.md`)
    already existed on disk, the exact "true when written, never
    rechecked" shape `recipe_readme_check.py` (task 426) and
    `chronicle_readme_check.py` (task 545) already closed for their own
    directories. Never edits anything; a real drift, if one is ever
    found, is a god-on-duty escalation, not something this check
    silently repairs."""
    mod = _proclamation_count_check()
    kwargs = {}
    if readme_path is not None:
        kwargs["readme_path"] = readme_path
    if proclamations_dir is not None:
        kwargs["proclamations_dir"] = proclamations_dir
    return cast(dict[str, object], mod.check_proclamation_count(**kwargs))


def check_badge_freshness(badge_path: str | None = None) -> dict[str, object]:
    """Task 425: fold badge_freshness_check.py's own live-recompute-vs-
    committed-file cross-check into the one block. `seam-scan.yml`'s daily
    "repaint the read-only badge" step runs `seam_engine.badge --write`
    non-blocking (`|| true`, its own comment: "a red badge IS the report")
    -- a real failure inside that computation leaves whatever
    `fencepost/BADGE.json` last said sitting in the repo, silently stale,
    with nothing at any shorter cadence ever re-deriving it. This is the
    one check in this block whose live half needs `arcade-mcp-server`, a
    dependency `dawn-run.yml`'s root test job deliberately does not install
    (task 404's own note) -- so the underlying module catches any import
    or computation failure itself and reports `status: "unavailable"`,
    clean, rather than raising into this function or crashing the rest of
    the hourly ritual over a missing optional dependency. Never edits
    anything; a real drift, if one is ever found, is a god-on-duty
    escalation, not something this check silently repairs."""
    mod = _badge_freshness_check()
    kwargs = {}
    if badge_path is not None:
        kwargs["badge_path"] = badge_path
    return cast(dict[str, object], mod.check_badge_freshness(**kwargs))


def check_recipe_readme(readme_path: str | None = None, recipe_fencepost_root: str | None = None) -> dict[str, object]:
    """Task 426: fold `recipe_readme_check.py`'s own two-way cross-check of
    `fencepost/README.md`'s Community recipes section against the live
    `seam_engine.recipes.discover_recipes()` tree into the one block.
    `tests/test_fencepost_site_recipes.py` (task 417) already proves every
    real recipe is named somewhere in that prose, but only forward, and
    only by loose substring match -- nothing before this task ever asked
    the reverse question live: does every `[`RECIPES/<slug>/`](RECIPES/
    <slug>/)` link still point at a recipe directory that actually exists,
    and does a link's own bracket text agree with its own href. A recipe
    directory removed or renamed after merge (nothing in this repo's
    history has done that yet, but nothing stops a future bad merge-
    conflict resolution or an overbroad cleanup pass from doing it) would
    leave a dead link sitting in published prose that no existing check,
    running or test-suite, would ever notice. Unconditional,
    local-filesystem-only, the same cheap always-on class
    `check_wip_reclaim`/`check_scopes_completeness` already hold. A real
    hit here DOES flip `broken`: a stale or mismatched recipe link is a
    live documentation regression on the flagship's own public onboarding
    surface, not an honest zero-state waiting on the calendar."""
    mod = _recipe_readme_check()
    kwargs = {}
    if readme_path is not None:
        kwargs["readme_path"] = readme_path
    if recipe_fencepost_root is not None:
        kwargs["fencepost_root"] = recipe_fencepost_root
    return cast(dict[str, object], mod.check_recipe_readme(**kwargs))


def check_site_recipe_readme(site_path: str | None = None, site_recipe_fencepost_root: str | None = None) -> dict[str, object]:
    """Task 554 (Kothar-wa-Khasis): fold `site_recipe_check.py`'s own
    two-way cross-check of `docs/fencepost/index.html`'s Community recipes
    section against the live `seam_engine.recipes.discover_recipes()` tree
    into the one block -- the SAME reverse-direction gap `check_recipe_
    readme` (task 426) already closed for `fencepost/README.md`, never
    closed for the Wall itself. `tests/test_fencepost_site_recipes.py`
    (task 417) already proves every real recipe is named somewhere on the
    site, but only forward, and only by loose substring match -- nothing
    before this task ever asked the reverse question live against the
    Wall: does every recipe link on the public site still point at a
    recipe directory that actually exists, and does a link's own anchor
    text agree with its own href. Confirmed live before writing this fix:
    temporarily removing `fencepost/RECIPES/stale-branch-no-pr/` left
    `recipe_readme_check.py` correctly BROKEN for `fencepost/README.md`
    while `site_link_check.py` (the site's recipe links are absolute
    `https://github.com/...` URLs, out of that check's local-filesystem-
    only scope) and `test_fencepost_site_recipes.py` both stayed clean --
    the Wall's own public catalog could carry a dead link to a removed
    recipe with nothing, running or test-suite, ever noticing. Uncondi-
    tional, local-filesystem-only, the same cheap always-on class `check_
    recipe_readme`/`check_wip_reclaim` already hold. A real hit here DOES
    flip `broken`: a stale or mismatched recipe link is a live documenta-
    tion regression on the flagship's own public onboarding surface, the
    identical severity `check_recipe_readme` already assigns its sibling
    document."""
    mod = _site_recipe_check()
    kwargs = {}
    if site_path is not None:
        kwargs["site_path"] = site_path
    if site_recipe_fencepost_root is not None:
        kwargs["fencepost_root"] = site_recipe_fencepost_root
    return cast(dict[str, object], mod.check_site_recipe_readme(**kwargs))


def check_recipe_commands(
    recipe_command_fencepost_root: str | None = None,
    recipe_command_seam_engine_dir: str | None = None,
) -> dict[str, object]:
    """Task 571 (Ogun): fold `recipe_command_check.py`'s own live
    execution of every recipe README's "Run it yourself" block into the
    one hourly pass. `check_recipe_readme`/`check_site_recipe_readme`
    already prove every recipe's own LINK stays honest; nothing before
    this task ever proved the documented COMMAND itself still runs --
    `test_recipes.py` calls each detector's `run_recipe_scan` directly
    through pytest's own import path, never the literal `cd fencepost/
    seam_engine` + `PYTHONPATH=... uv run python ...` line a stranger
    reading the README would actually copy and paste. A future recipe
    edit that adds a local-helper import and forgets to widen its own
    README's `PYTHONPATH` line accordingly would ship a broken copy-paste
    instruction on the flagship's own onboarding surface with nothing,
    running or test-suite, ever noticing -- the same "documented, not
    verified" shape `check_recipe_readme`'s own link check closed for
    text, closed here for execution. Local subprocess only (`uv run`
    against this repo's own already-synced environment) -- no repo file
    is written, no Arcade tool is called, no real account is touched. A
    real hit here DOES flip `broken`: a dead copy-paste command on the
    public onboarding path is the identical severity `check_recipe_
    readme`/`check_site_recipe_readme` already assign a stale link."""
    mod = _recipe_command_check()
    kwargs = {}
    if recipe_command_fencepost_root is not None:
        kwargs["fencepost_root"] = recipe_command_fencepost_root
    if recipe_command_seam_engine_dir is not None:
        kwargs["seam_engine_dir"] = recipe_command_seam_engine_dir
    return cast(dict[str, object], mod.check_recipe_commands(**kwargs))


def check_escape_sequences(orita_dir: str | None = None) -> dict[str, object]:
    """Task 434: fold escape_sequence_check.py's own repo-wide compile-
    time scan into the one block. Found by accident this hour running
    both full suites clean against a freshly-installed sandbox: pytest's
    own collection output carried a real `DeprecationWarning: invalid
    escape sequence` pinned to `tools/roadmap_archive.py:2`, unflagged by
    either suite's pass/fail count because a DeprecationWarning is not an
    assertion. Python turns this class of warning into a hard
    SyntaxError in a future version, breaking import outright -- the
    exact "true when written, never rechecked" shape Iron Rule 1's own
    history (a `vault_leak_check.py` gap sitting unnoticed for 96 tasks)
    already warns about. Unconditional, local-filesystem-only (compiles
    -- never imports or executes -- every tracked `.py` file already on
    disk, the same read-only boundary `check_duplicate_regex` already
    holds via `ast.parse`). Never edits anything; a real hit here is a
    god-on-duty escalation, not something this check silently repairs."""
    mod = _escape_sequence_check()
    kwargs = {}
    if orita_dir is not None:
        kwargs["orita_dir"] = orita_dir
    return cast(dict[str, object], mod.check_escape_sequences(**kwargs))


def check_metrics_field_completeness(
    metrics_path: str | None = None, tools_dir: str | None = None
) -> dict[str, object]:
    """Task 459: fold `metrics_field_completeness_check.py`'s own
    structural sweep into the one block -- the third of its family
    alongside `check_ritual_completeness` (every `check_*` function
    wired) and `check_scopes_completeness` (every connected app named).
    Unconditional, local-filesystem-only, the same cheap always-on class
    those two already hold. A real hit here DOES flip `broken`: a field
    recorded in `records/metrics.jsonl` with no matching cross-checker is
    the exact silent-omission risk tasks 453-458's whole campaign existed
    to close, now standing again on a field this check can name, not an
    honest zero-state waiting on the calendar."""
    mod = _metrics_field_completeness_check()
    kwargs = {}
    if metrics_path is not None:
        kwargs["metrics_path"] = metrics_path
    if tools_dir is not None:
        kwargs["tools_dir"] = tools_dir
    return cast(dict[str, object], mod.check_metrics_field_completeness(**kwargs))


def check_change_gate(report_info: dict[str, str | None]) -> dict[str, object] | None:
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
    square_state: dict[str, object] | None = None,
    scribe_root: str | None = None,
    ci_checks: list[dict[str, object]] | None = None,
    cron_checks: list[dict[str, object]] | None = None,
    checkout_dirs: tuple[str, ...] | None = None,
    vault_leak_dirs: tuple[str, ...] | None = None,
    star_covenant_dir: str | None = None,
    duplicate_regex_dir: str | None = None,
    rider_dir: str | None = None,
    hand_lore_dir: str | None = None,
    no_grading_dir: str | None = None,
    arcade_hero_dir: str | None = None,
    petition_limits_dir: str | None = None,
    child_files: list[dict[str, object]] | None = None,
    child_work_log: str | None = None,
    child_work_repo: str | None = None,
    verdict_provenance_dir: str | None = None,
    voice_window_commits: list[dict[str, object]] | None = None,
    voice_window_log: str | None = None,
    petition_cadence_dir: str | None = None,
    journal_numbering_dir: str | None = None,
    journal_numbering_dirs: tuple[str, ...] | None = None,
    report_cadence_dir: str | None = None,
    metrics_cadence_path: str | None = None,
    shared_reports_path: str | None = None,
    ritual_completeness_path: str | None = None,
    ritual_completeness_tools_dir: str | None = None,
    ritual_completeness_seam_engine_dir: str | None = None,
    wip_reclaim_path: str | None = None,
    arcade_apps_state: dict[str, object] | None = None,
    gateway_toolset_state: dict[str, object] | None = None,
    good_first_issues_state: list[dict[str, object]] | None = None,
    scopes_path: str | None = None,
    app_log_path: str | None = None,
    toolkits_metrics_path: str | None = None,
    toolkits_consent_log_path: str | None = None,
    connected_users_metrics_path: str | None = None,
    connected_users_consent_log_path: str | None = None,
    cluster_day_dir: str | None = None,
    cluster_day_today: date | None = None,
    what_moved_path: str | None = None,
    what_moved_today: date | None = None,
    thegap_readme_path: str | None = None,
    thegap_vault_dir: str | None = None,
    thegap_today: date | None = None,
    nyx_traffic_vault_dir: str | None = None,
    nyx_traffic_today: date | None = None,
    strategy_targets_path: str | None = None,
    network_boundary_dirs: tuple[str, ...] | None = None,
    site_link_docs_dir: str | None = None,
    house_links_houses_dir: str | None = None,
    fencepost_links_dir: str | None = None,
    issue_template_links_dir: str | None = None,
    hand_links_dir: str | None = None,
    chronicle_links_dir: str | None = None,
    chronicle_readme_path: str | None = None,
    chronicle_readme_dir: str | None = None,
    proclamation_count_readme_path: str | None = None,
    proclamation_count_proclamations_dir: str | None = None,
    badge_path: str | None = None,
    recipe_readme_path: str | None = None,
    recipe_readme_fencepost_root: str | None = None,
    site_recipe_path: str | None = None,
    site_recipe_fencepost_root: str | None = None,
    recipe_command_fencepost_root: str | None = None,
    recipe_command_seam_engine_dir: str | None = None,
    escape_sequence_orita_dir: str | None = None,
    metrics_field_completeness_metrics_path: str | None = None,
    metrics_field_completeness_tools_dir: str | None = None,
    strategy_true_positive_path: str | None = None,
    strategy_true_positive_ledger_base: str | None = None,
    gap_true_positive_metrics_path: str | None = None,
    gap_true_positive_ledger_base: str | None = None,
    report_shipped_metrics_path: str | None = None,
    report_shipped_reports_dir: str | None = None,
    tasks_shipped_metrics_path: str | None = None,
    tasks_shipped_buildlog_path: str | None = None,
    github_stars_count: int | None = None,
    github_stars_metrics_path: str | None = None,
    github_stars_log_path: str | None = None,
    record_scribe_growth: bool = False,
    record_words: bool = False,
    record_github_stars: bool = False,
) -> dict[str, Any]:
    """Task 374: `record_scribe_growth` defaults `False` -- a bare or
    library call to this function (a dev-verification run, a test, a
    notebook exploration) must never silently write a real entry to the
    production `HAND/scribe-growth-log.jsonl`, which is exactly the bug
    that put 30 duplicate-timestamp groups (one repeated 328 times) into
    that file's committed history: every call here used to record
    unconditionally, including `tests/test_ritual_check.py`'s own bare
    `rc.run_ritual_check()` calls against the real repo. Only `main()`
    below -- the one real hourly CLI entrypoint this town's actual cadence
    runs -- passes `record_scribe_growth=True`, so real per-hour recording
    is unchanged for the real production cadence; every other caller is
    safe by default.

    Task 375: `record_words` defaults `False` for the identical reason,
    against the identical class of bug in `HAND/word-check-log.jsonl`
    (named in task 374's own closing note and left unfixed there). Only
    `main()` passes `record_words=True`."""
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
    arcade_apps = check_arcade_apps(arcade_apps_state, now_iso)
    gateway_toolset = check_gateway_toolset(gateway_toolset_state, now_iso)
    good_first_issues = check_good_first_issues(good_first_issues_state)
    scribe_growth = check_scribe_growth(now_iso, scribe_root=scribe_root, record=record_scribe_growth)
    ci = check_ci(ci_checks)
    words = check_words(now_iso, record=record_words)
    cron = check_cron(cron_checks, now_iso)
    owed_posts = check_owed_posts()
    change_gate = check_change_gate(report)
    if vault_leak_dirs is None:
        vault_leak = check_vault_leak()
    else:
        vault_leak = check_vault_leak(orita_dir=vault_leak_dirs[0], vault_dir=vault_leak_dirs[1])
    star_covenant = check_star_covenant(orita_dir=star_covenant_dir)
    duplicate_regex = check_duplicate_regex(orita_dir=duplicate_regex_dir)
    riders = check_riders(orita_dir=rider_dir)
    hand_lore = check_hand_lore(orita_dir=hand_lore_dir)
    no_grading = check_no_grading(orita_dir=no_grading_dir)
    arcade_hero = check_arcade_hero(orita_dir=arcade_hero_dir)
    petition_limits = check_petition_limits(orita_dir=petition_limits_dir)
    child_work = check_child_work(child_files, now_iso, path=child_work_log, repo_root=child_work_repo)
    verdict_provenance = check_verdict_provenance(orita_dir=verdict_provenance_dir)
    voice_window = check_voice_window(voice_window_commits, now_iso, path=voice_window_log)
    petition_cadence = check_petition_cadence(orita_dir=petition_cadence_dir)
    if journal_numbering_dirs is not None:
        journal_numbering = check_journal_numbering(
            orita_dir=journal_numbering_dirs[0], vault_dir=journal_numbering_dirs[1]
        )
    else:
        journal_numbering = check_journal_numbering(orita_dir=journal_numbering_dir)
    report_cadence = check_report_cadence(reports_dir=report_cadence_dir)
    metrics_cadence = check_metrics_cadence(metrics_path=metrics_cadence_path)
    metrics_freshness = check_metrics_freshness(now, metrics_path=metrics_cadence_path)
    shared_reports = check_shared_reports(shared_path=shared_reports_path)
    ritual_completeness = check_ritual_completeness(
        source_path=ritual_completeness_path,
        tools_dir=ritual_completeness_tools_dir,
        seam_engine_dir=ritual_completeness_seam_engine_dir,
    )
    wip_reclaim = check_wip_reclaim(now, roadmap_path=wip_reclaim_path)
    scopes_completeness = check_scopes_completeness(scopes_path=scopes_path, app_log_path=app_log_path)
    toolkits_in_use = check_toolkits_in_use(
        metrics_path=toolkits_metrics_path, consent_log_path=toolkits_consent_log_path
    )
    connected_users = check_connected_users(
        metrics_path=connected_users_metrics_path, consent_log_path=connected_users_consent_log_path
    )
    cluster_day = check_cluster_day_cadence(chronicle_dir=cluster_day_dir, today=cluster_day_today)
    what_moved = check_what_moved_cadence(what_moved_path=what_moved_path, what_moved_today=what_moved_today)
    thegap = check_thegap_cadence(
        thegap_readme_path=thegap_readme_path, thegap_vault_dir=thegap_vault_dir, thegap_today=thegap_today
    )
    nyx_traffic = check_nyx_traffic_cadence(
        nyx_traffic_vault_dir=nyx_traffic_vault_dir, nyx_traffic_today=nyx_traffic_today
    )
    strategy_targets = check_strategy_targets(strategy_path=strategy_targets_path)
    network_boundary = check_network_boundary(dirs=network_boundary_dirs)
    site_links = check_site_links(docs_dir=site_link_docs_dir)
    house_links = check_house_links(houses_dir=house_links_houses_dir)
    fencepost_links = check_fencepost_links(fencepost_dir=fencepost_links_dir)
    issue_template_links = check_issue_template_links(issue_template_dir=issue_template_links_dir)
    hand_links = check_hand_links(hand_dir=hand_links_dir)
    chronicle_links = check_chronicle_links(chronicle_dir=chronicle_links_dir)
    chronicle_readme = check_chronicle_readme(
        readme_path=chronicle_readme_path, chronicle_readme_dir=chronicle_readme_dir
    )
    proclamation_count = check_proclamation_count(
        readme_path=proclamation_count_readme_path, proclamations_dir=proclamation_count_proclamations_dir
    )
    badge_freshness = check_badge_freshness(badge_path=badge_path)
    recipe_readme = check_recipe_readme(
        readme_path=recipe_readme_path, recipe_fencepost_root=recipe_readme_fencepost_root
    )
    site_recipe_readme = check_site_recipe_readme(
        site_path=site_recipe_path, site_recipe_fencepost_root=site_recipe_fencepost_root
    )
    recipe_commands = check_recipe_commands(
        recipe_command_fencepost_root=recipe_command_fencepost_root,
        recipe_command_seam_engine_dir=recipe_command_seam_engine_dir,
    )
    escape_sequences = check_escape_sequences(orita_dir=escape_sequence_orita_dir)
    metrics_field_completeness = check_metrics_field_completeness(
        metrics_path=metrics_field_completeness_metrics_path,
        tools_dir=metrics_field_completeness_tools_dir,
    )
    strategy_true_positive = check_strategy_true_positive(
        strategy_path=strategy_true_positive_path,
        ledger_base=strategy_true_positive_ledger_base,
    )
    gap_true_positive = check_gap_true_positive_rate(
        metrics_path=gap_true_positive_metrics_path,
        ledger_base=gap_true_positive_ledger_base,
    )
    report_shipped = check_report_shipped(
        metrics_path=report_shipped_metrics_path,
        reports_dir=report_shipped_reports_dir,
    )
    tasks_shipped = check_tasks_shipped(
        metrics_path=tasks_shipped_metrics_path,
        buildlog_path=tasks_shipped_buildlog_path,
    )
    github_stars = check_github_stars(
        github_stars_count,
        now_iso,
        metrics_path=github_stars_metrics_path,
        log_path=github_stars_log_path,
        record=record_github_stars,
    )
    broken = (
        (not town["ok"])
        or (not fencepost["ok"])
        or (not vault_leak["clean"])
        or (not star_covenant["clean"])
        or (not duplicate_regex["clean"])
        or (not riders["clean"])
        or (not hand_lore["clean"])
        or (not no_grading["clean"])
        or (not arcade_hero["clean"])
        or (not petition_limits["clean"])
        or (not child_work["clean"])
        or (not verdict_provenance["clean"])
        or (not voice_window["clean"])
        or (not petition_cadence["clean"])
        or (not journal_numbering["clean"])
        or (not ritual_completeness["clean"])
        or (not wip_reclaim["clean"])
        or (not scopes_completeness["clean"])
        or (not toolkits_in_use["clean"])
        or (not connected_users["clean"])
        or (not strategy_targets["clean"])
        or (not network_boundary["clean"])
        or (not site_links["clean"])
        or (not house_links["clean"])
        or (not fencepost_links["clean"])
        or (not issue_template_links["clean"])
        or (not hand_links["clean"])
        or (not chronicle_links["clean"])
        or (not chronicle_readme["clean"])
        or (not proclamation_count["clean"])
        or (not badge_freshness["clean"])
        or (not recipe_readme["clean"])
        or (not site_recipe_readme["clean"])
        or (not recipe_commands["clean"])
        or (not strategy_true_positive["clean"])
        or (not gap_true_positive["clean"])
        or (not report_shipped["clean"])
        or (not tasks_shipped["clean"])
        or (not github_stars["clean"])
        or (not escape_sequences["clean"])
        or (not metrics_field_completeness["clean"])
    )
    return {
        "now": now_iso,
        "checkout": checkout,
        "town_ledger": town,
        "fencepost_ledger": fencepost,
        "report": report,
        "x_recheck": recheck,
        "x_escalation": escalation,
        "square": square,
        "arcade_apps": arcade_apps,
        "gateway_toolset": gateway_toolset,
        "good_first_issues": good_first_issues,
        "scribe_growth": scribe_growth,
        "ci": ci,
        "words": words,
        "cron": cron,
        "owed_posts": owed_posts,
        "change_gate": change_gate,
        "vault_leak": vault_leak,
        "star_covenant": star_covenant,
        "duplicate_regex": duplicate_regex,
        "riders": riders,
        "hand_lore": hand_lore,
        "no_grading": no_grading,
        "arcade_hero": arcade_hero,
        "petition_limits": petition_limits,
        "child_work": child_work,
        "verdict_provenance": verdict_provenance,
        "voice_window": voice_window,
        "petition_cadence": petition_cadence,
        "journal_numbering": journal_numbering,
        "report_cadence": report_cadence,
        "metrics_cadence": metrics_cadence,
        "metrics_freshness": metrics_freshness,
        "shared_reports": shared_reports,
        "ritual_completeness": ritual_completeness,
        "wip_reclaim": wip_reclaim,
        "scopes_completeness": scopes_completeness,
        "toolkits_in_use": toolkits_in_use,
        "connected_users": connected_users,
        "cluster_day": cluster_day,
        "what_moved": what_moved,
        "thegap": thegap,
        "nyx_traffic": nyx_traffic,
        "strategy_targets": strategy_targets,
        "network_boundary": network_boundary,
        "site_links": site_links,
        "house_links": house_links,
        "fencepost_links": fencepost_links,
        "issue_template_links": issue_template_links,
        "hand_links": hand_links,
        "chronicle_links": chronicle_links,
        "chronicle_readme": chronicle_readme,
        "proclamation_count": proclamation_count,
        "badge_freshness": badge_freshness,
        "recipe_readme": recipe_readme,
        "site_recipe_readme": site_recipe_readme,
        "recipe_commands": recipe_commands,
        "strategy_true_positive": strategy_true_positive,
        "gap_true_positive": gap_true_positive,
        "report_shipped": report_shipped,
        "tasks_shipped": tasks_shipped,
        "github_stars": github_stars,
        "escape_sequences": escape_sequences,
        "metrics_field_completeness": metrics_field_completeness,
        "broken": broken,
    }


def format_ritual_check(result: dict[str, Any]) -> str:
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
    if result["arcade_apps"] is not None:
        aa = result["arcade_apps"]
        lines.append(f"  arcade apps: {'changed' if aa['changed'] else 'unchanged'} -- {aa['reason']}")
    if result["gateway_toolset"] is not None:
        gt = result["gateway_toolset"]
        lines.append(f"  gateway toolset (gmail/calendar): {'changed' if gt['changed'] else 'unchanged'} -- {gt['reason']}")
    lines.append("  " + _good_first_issue_check().format_good_first_issues(result["good_first_issues"]))
    sg = result["scribe_growth"]
    lines.append(
        "  scribe growth: "
        + ("clean" if sg["clean"] else f"OVER THRESHOLD ({', '.join(sg['over_threshold'])})")
        + f" -- sizes: {sg['sizes']}, growth: {sg['growth_since_last_check']}"
    )
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
    vl = result["vault_leak"]
    if vl["clean"]:
        lines.append("  vault leak: clean (Proclamation 0001 holds)")
    else:
        lines.append(f"  vault leak: {vl['count']} LEAK(S) -- Proclamation 0001 violated, escalate now")
    sc = result["star_covenant"]
    if sc["clean"]:
        lines.append("  star covenant: clean (no begging language found)")
    else:
        lines.append(f"  star covenant: {sc['count']} VIOLATION(S) -- Star Covenant broken, escalate now")
    dr = result["duplicate_regex"]
    if dr["clean"]:
        lines.append("  duplicate regex: clean (every re.compile pattern unique or a seeded exception)")
    else:
        lines.append(f"  duplicate regex: {dr['count']} DUPLICATE(S) -- hand-typed copy with no import backing it, fix now")
    rd = result["riders"]
    if rd["clean"]:
        lines.append("  riders: clean (all five character riders hold)")
    else:
        lines.append(f"  riders: {rd['count']} VIOLATION(S) -- a rider is broken, escalate now")
    hl = result["hand_lore"]
    if hl["clean"]:
        lines.append("  hand lore: clean (Iron Rule #2's theology never confirmed or denied)")
    else:
        lines.append(f"  hand lore: {hl['count']} VIOLATION(S) -- Iron Rule #2 is broken, escalate now")
    ng = result["no_grading"]
    if ng["clean"]:
        lines.append("  no grading: clean (constraint #2 holds, name and rank no one)")
    else:
        lines.append(f"  no grading: {ng['count']} VIOLATION(S) -- constraint #2 broken, escalate now")
    ah = result["arcade_hero"]
    if ah["clean"]:
        lines.append("  arcade hero: clean (constraint #4 holds, OAuth is the only door)")
    else:
        lines.append(f"  arcade hero: {ah['count']} VIOLATION(S) -- constraint #4 broken, escalate now")
    pl = result["petition_limits"]
    if pl["clean"]:
        lines.append("  petition limits: clean (CHARTER.md Appendix D's LIMITS hold on every altar)")
    else:
        lines.append(f"  petition limits: {pl['count']} VIOLATION(S) -- Appendix D's LIMITS broken, escalate now")
    cw = result["child_work"]
    if cw["clean"]:
        newly = f", {len(cw['newly_logged'])} newly logged" if cw["newly_logged"] else ""
        lines.append(f"  child work: clean ({cw['known_count']} known file(s){newly}, Iron Rule #6 holds)")
    else:
        lines.append(f"  child work: {len(cw['reverted'])} REVERTED -- Iron Rule #6 violated, escalate now")
    vp = result["verdict_provenance"]
    if vp["clean"]:
        lines.append("  verdict provenance: clean (every public verdict backed, Iron Rule #3 holds)")
    else:
        lines.append(f"  verdict provenance: {vp['count']} MISMATCH(ES) -- Iron Rule #3 at risk, escalate now")
    vw = result["voice_window"]
    if vw["clean"]:
        historical = f", {vw['violation_count']} historical" if vw["violation_count"] else ""
        lines.append(f"  voice window: clean ({vw['known_count']} known commit(s){historical}, Iron Rule #7's window holds)")
    else:
        lines.append(f"  voice window: {len(vw['new_violations'])} NEW VIOLATION(S) -- Iron Rule #7's window broken, escalate now")
    pc = result["petition_cadence"]
    if pc["clean"]:
        lines.append("  petition cadence: clean (every altar filename is a real, unique YYYY-MM-DD.md)")
    else:
        lines.append(f"  petition cadence: {pc['count']} VIOLATION(S) -- one-per-UTC-day claim broken, escalate now")
    jn = result["journal_numbering"]
    if jn["clean"]:
        lines.append("  journal numbering: clean (every house's journal runs an unbroken 0001, 0002, ... count)")
    else:
        lines.append(f"  journal numbering: {jn['count']} VIOLATION(S) -- a house's sequence is malformed, duplicated, or gapped, escalate now")
    rcad = result["report_cadence"]
    if rcad["total_shipped"] == 0:
        lines.append("  report cadence: no Fencepost Report has ever shipped")
    else:
        gap_note = f", {len(rcad['missing_dates'])} historical gap day(s)" if rcad["missing_dates"] else ""
        lines.append(
            f"  report cadence: {rcad['current_streak']}-day streak "
            f"(target {rcad['target']}/{rcad['target']}, STRATEGY.md's off-by-one metric){gap_note}"
        )
    mcad = result["metrics_cadence"]
    if mcad["total_shipped"] == 0:
        lines.append("  metrics cadence: no daily-aggregate reading has ever shipped")
    else:
        gap_note = f", {len(mcad['missing_dates'])} historical gap day(s)" if mcad["missing_dates"] else ""
        lines.append(
            f"  metrics cadence: {mcad['current_streak']}-day streak "
            f"(records/metrics.jsonl, daily-aggregate readings, target {mcad['target']}/{mcad['target']}){gap_note}"
        )
    mf = result["metrics_freshness"]
    if mf["status"] == "current":
        lines.append(f"  metrics freshness: current ({mf['date']})")
    elif mf["status"] == "pending":
        lines.append(f"  metrics freshness: pending for {mf['date']} (falls back to {mf['fallback_date']})")
    else:
        lines.append(f"  metrics freshness: STALE -- no daily-aggregate reading for {mf['date']} or the day before")
    sr = result["shared_reports"]
    if sr["total_shared"] == 0:
        lines.append(f"  shared reports in the wild: 0/{sr['target']} (kwaku-ananse's lagging metric, none yet)")
    else:
        lines.append(
            f"  shared reports in the wild: {sr['total_shared']}/{sr['target']} "
            f"(kwaku-ananse's lagging metric), most recent {sr['most_recent_date']}"
        )
    rc = result["ritual_completeness"]
    if rc["clean"]:
        lines.append("  ritual completeness: clean (every check_* function is called, returned, and printed)")
    else:
        parts = []
        if rc["missing_from_run"]:
            parts.append(f"never called: {', '.join(rc['missing_from_run'])}")
        if rc["missing_from_dict"]:
            parts.append(f"dropped from return dict: {', '.join(rc['missing_from_dict'])}")
        if rc["missing_from_format"]:
            parts.append(f"never printed: {', '.join(rc['missing_from_format'])}")
        if rc.get("unwired_tool_files"):
            parts.append(f"tools/*.py unwired: {', '.join(rc['unwired_tool_files'])}")
        if rc.get("unwired_strategy_audit_modules"):
            parts.append(f"seam_engine/*.py unwired: {', '.join(rc['unwired_strategy_audit_modules'])}")
        lines.append(f"  ritual completeness: BROKEN -- {'; '.join(parts)}, escalate now")
    wr = result["wip_reclaim"]
    if wr["open_count"] == 0:
        lines.append("  wip reclaim: clean (no task currently WIP)")
    elif wr["clean"]:
        lines.append(f"  wip reclaim: clean ({wr['open_count']} WIP task(s), all opened under {wr['threshold_hours']}h ago)")
    else:
        lines.append(
            f"  wip reclaim: {len(wr['stale'])} STALE (>= {wr['threshold_hours']}h), "
            f"{len(wr['unknown'])} UNKNOWN-AGE -- reclaim now, escalate"
        )
    sc = result["scopes_completeness"]
    if not sc["connected_app_ids"]:
        lines.append("  scopes completeness: clean (no apps recorded as connected)")
    elif sc["clean"]:
        lines.append(f"  scopes completeness: clean ({len(sc['connected_app_ids'])} connected app(s), all accounted for)")
    else:
        lines.append(f"  scopes completeness: BROKEN -- undocumented connected app(s): {', '.join(sc['missing'])}, escalate now")
    ti = result["toolkits_in_use"]
    if ti["claimed"] is None:
        lines.append(f"  toolkits in use: clean (no metrics.jsonl reading yet; real ground truth is {ti['real']})")
    elif ti["clean"]:
        lines.append(f"  toolkits in use: clean ({ti['real']} real toolkit(s), metrics.jsonl's {ti['claimed_date']} reading agrees)")
    else:
        lines.append(
            f"  toolkits in use: BROKEN -- metrics.jsonl's {ti['claimed_date']} reading claims {ti['claimed']}, "
            f"real ground truth is {ti['real']} -- STRATEGY.md's adoption metric is misreporting live, escalate now"
        )
    cu = result["connected_users"]
    if cu["claimed"] is None:
        lines.append(f"  connected users (OAuth): clean (no metrics.jsonl reading yet; real ground truth is {cu['real']})")
    elif cu["clean"]:
        lines.append(f"  connected users (OAuth): clean ({cu['real']} real connected user(s), metrics.jsonl's {cu['claimed_date']} reading agrees)")
    else:
        lines.append(
            f"  connected users (OAuth): BROKEN -- metrics.jsonl's {cu['claimed_date']} reading claims {cu['claimed']}, "
            f"real ground truth is {cu['real']} -- STRATEGY.md's adoption metric is misreporting live, escalate now"
        )
    cd = result["cluster_day"]
    lines.append("  " + _cluster_day_check().format_cadence(cd))
    wm = result["what_moved"]
    lines.append("  " + _what_moved_check().format_cadence(wm))
    tg = result["thegap"]
    lines.append("  " + _thegap_check().format_cadence(tg))
    nt = result["nyx_traffic"]
    lines.append("  " + _nyx_traffic_check().format_cadence(nt))
    st = result["strategy_targets"]
    for line in _strategy_targets_check().format_strategy_targets(st).split("\n"):
        lines.append("  " + line)
    nb = result["network_boundary"]
    if nb["clean"]:
        lines.append(f"  network boundary: clean ({nb['count']} file(s) claiming \"no network\", all hold it)")
    else:
        lines.append(
            f"  network boundary: BROKEN -- {len(nb['broken'])} of {nb['count']} file(s) claim "
            f"\"no network\" but don't: {sorted(nb['broken'])}, escalate now"
        )
    sl = result["site_links"]
    if sl["clean"]:
        lines.append("  site links: clean (every internal docs/ link resolves)")
    else:
        lines.append(
            f"  site links: {sl['count']} BROKEN LINK(S) -- Ogun's own charter duty is unmet, escalate now"
        )
    hl = result["house_links"]
    if hl["clean"]:
        lines.append("  house links: clean (every houses/ link resolves, GitHub-browsed rule)")
    else:
        lines.append(
            f"  house links: {hl['count']} BROKEN LINK(S) -- a house's own front door is unmet, escalate now"
        )
    fl = result["fencepost_links"]
    if fl["clean"]:
        lines.append("  fencepost links: clean (every fencepost/ link resolves, GitHub-browsed rule)")
    else:
        lines.append(
            f"  fencepost links: {fl['count']} BROKEN LINK(S) -- the flagship's own front door is unmet, escalate now"
        )
    itl = result["issue_template_links"]
    if itl["clean"]:
        lines.append(
            "  issue template links: clean (every .github/ISSUE_TEMPLATE/ link resolves, GitHub-browsed rule, "
            "all five expected templates present)"
        )
    elif itl["missing_templates"]:
        lines.append(
            f"  issue template links: MISSING TEMPLATE(S) {', '.join(itl['missing_templates'])} -- "
            f"Esu's own gate is unmet, escalate now"
        )
    else:
        lines.append(
            f"  issue template links: {itl['count']} BROKEN LINK(S) -- Esu's own gate is unmet, escalate now"
        )
    hl2 = result["hand_links"]
    if hl2["clean"]:
        lines.append("  hand links: clean (every HAND/ link resolves, GitHub-browsed rule)")
    else:
        lines.append(
            f"  hand links: {hl2['count']} BROKEN LINK(S) -- the Hand's own record is unmet, escalate now"
        )
    cl2 = result["chronicle_links"]
    if cl2["clean"]:
        lines.append("  chronicle links: clean (every chronicle/ link resolves, GitHub-browsed rule)")
    else:
        lines.append(
            f"  chronicle links: {cl2['count']} BROKEN LINK(S) -- Ananse's own record is unmet, escalate now"
        )
    lines.append("  " + _chronicle_readme_check().format_result(result["chronicle_readme"]))
    lines.append("  " + _proclamation_count_check().format_result(result["proclamation_count"]))
    lines.append("  " + _badge_freshness_check().format_badge_freshness(result["badge_freshness"]))
    lines.append("  " + _recipe_readme_check().format_result(result["recipe_readme"]))
    lines.append("  " + _site_recipe_check().format_result(result["site_recipe_readme"]))
    lines.append("  " + _recipe_command_check().format_result(result["recipe_commands"]))
    stp = result["strategy_true_positive"]
    if stp["clean"]:
        lines.append(
            f"  strategy true-positive rate: clean ({stp['live_rate_pct']}% over {stp['live_total']} "
            f"claim(s), meets STRATEGY.md's >={stp['strategy_target_pct']}% bar)"
        )
    else:
        lines.append(
            f"  strategy true-positive rate: BROKEN -- live rate {stp['live_rate_pct']}% over "
            f"{stp['live_total']} claim(s) does not meet STRATEGY.md's >={stp['strategy_target_pct']}% "
            "bar, escalate now"
        )
    gtp = result["gap_true_positive"]
    if gtp["claimed"] is None:
        real = "none audited yet" if gtp["real"] is None else f"{round(gtp['real'] * 100, 4)}%"
        lines.append(f"  gap true-positive rate: clean (no metrics.jsonl reading yet; real ground truth is {real})")
    elif gtp["real"] is None:
        lines.append(
            f"  gap true-positive rate: BROKEN -- metrics.jsonl's {gtp['claimed_date']} reading claims "
            f"{gtp['claimed']}, but the real Ledger has audited zero gaps, escalate now"
        )
    elif gtp["clean"]:
        lines.append(
            f"  gap true-positive rate: clean ({round(gtp['real'] * 100, 4)}% real, "
            f"metrics.jsonl's {gtp['claimed_date']} reading agrees)"
        )
    else:
        lines.append(
            f"  gap true-positive rate: BROKEN -- metrics.jsonl's {gtp['claimed_date']} reading claims "
            f"{round(gtp['claimed'] * 100, 4)}%, real ground truth is {round(gtp['real'] * 100, 4)}% -- "
            "STRATEGY.md's own Ogun's-law metric is misreporting live, escalate now"
        )
    rs = result["report_shipped"]
    if rs["claimed"] is None:
        lines.append("  reports shipped today: clean (no metrics.jsonl reading yet; nothing to cross-check)")
    elif rs["clean"]:
        lines.append(
            f"  reports shipped today: clean (metrics.jsonl's {rs['claimed_date']} reading claims "
            f"{rs['claimed']}, real ground truth agrees)"
        )
    else:
        lines.append(
            f"  reports shipped today: BROKEN -- metrics.jsonl's {rs['claimed_date']} reading claims "
            f"{rs['claimed']}, real ground truth (fencepost/REPORTS/{rs['claimed_date']}.md's own existence) "
            f"is {rs['real']} -- STRATEGY.md's off-by-one row is misreporting live, escalate now"
        )
    ts = result["tasks_shipped"]
    if ts["claimed"] is None:
        lines.append("  tasks shipped today: clean (no metrics.jsonl reading yet; nothing to cross-check)")
    elif ts["real"] is None:
        lines.append(
            f"  tasks shipped today: clean (metrics.jsonl's {ts['claimed_date']} reading claims "
            f"{ts['claimed']}; no daily-aggregate BUILDLOG.md row found for that date, nothing to cross-check)"
        )
    elif ts["clean"]:
        lines.append(
            f"  tasks shipped today: clean (metrics.jsonl's {ts['claimed_date']} reading claims "
            f"{ts['claimed']}, real ground truth (BUILDLOG.md's own dated rows before that day's "
            "aggregate task) agrees)"
        )
    else:
        lines.append(
            f"  tasks shipped today: BROKEN -- metrics.jsonl's {ts['claimed_date']} reading claims "
            f"{ts['claimed']}, real ground truth (BUILDLOG.md's own dated rows before that day's "
            f"aggregate task) is {ts['real']} -- misreporting live, escalate now"
        )
    gs = result["github_stars"]
    if gs["claimed"] is None:
        if gs["real"] is None:
            lines.append("  github stars: clean (no metrics.jsonl reading and no live check recorded yet)")
        else:
            lines.append(f"  github stars: clean (no metrics.jsonl reading yet; last live count is {gs['real']})")
    elif gs["real"] is None:
        lines.append(
            f"  github stars: clean (metrics.jsonl's {gs['claimed_date']} reading claims "
            f"{gs['claimed']}; no live check recorded yet, nothing to cross-check)"
        )
    elif gs["clean"]:
        lines.append(
            f"  github stars: clean ({gs['real']} real star(s), metrics.jsonl's "
            f"{gs['claimed_date']} reading agrees)"
        )
    else:
        lines.append(
            f"  github stars: BROKEN -- metrics.jsonl's {gs['claimed_date']} reading claims "
            f"{gs['claimed']}, real live count is {gs['real']} -- STRATEGY.md's off-by-one row "
            "is misreporting live, escalate now"
        )
    lines.append("  " + _escape_sequence_check().format_result(result["escape_sequences"]))
    lines.append(
        "  " + _metrics_field_completeness_check().format_result(result["metrics_field_completeness"])
    )
    return "\n".join(lines)


class RitualCheckArgError(ValueError):
    """A --<flag> file argument to this CLI parsed as valid JSON but not
    into the top-level shape that flag expects. Raised here, naming the
    flag and the real type, instead of the wrong-shape value reaching
    `compute_square_state`/`compute_app_state`/`check_ci`/`check_cron`/
    `check_child_work`/`check_voice_window` unguarded and crashing with a
    bare `AttributeError`/`TypeError` two or three frames deeper."""


def _load_json_arg(path: str, flag: str, expected: str) -> dict[str, object] | list[object]:
    """Load `path` as JSON and confirm its top-level shape matches
    `expected` ("dict" or "list"), raising `RitualCheckArgError` naming the
    flag and the actual type otherwise. A bare scalar (int/bool/null/
    string), or a dict where a list was expected (or vice versa), is
    exactly the malformed-CLI-input shape the closed `fencepost/
    seam_engine` campaigns (tasks 355-362) already guard at their own
    entry points -- this is the same discipline at the one entry point
    those scans never reached: this file's own CLI."""
    with open(path) as f:
        raw = json.load(f)
    py_type = {"dict": dict, "list": list}[expected]
    if not isinstance(raw, py_type):
        raise RitualCheckArgError(
            f"--{flag}: expected a JSON {expected}, got {type(raw).__name__}"
        )
    return cast(dict[str, object] | list[object], raw)


def main(argv: list[str]) -> int:
    now = None
    base = DEFAULT_FENCEPOST_BASE
    square_state = None
    arcade_apps_state = None
    gateway_toolset_state = None
    good_first_issues_state = None
    ci_checks = None
    cron_checks = None
    child_files = None
    voice_window_commits = None
    github_stars_count = None
    i = 0
    while i < len(argv):
        if argv[i] == "--now" and i + 1 < len(argv):
            now = datetime.fromisoformat(argv[i + 1].replace("Z", "+00:00")).astimezone(timezone.utc)
            i += 2
        elif argv[i] == "--fencepost-base" and i + 1 < len(argv):
            base = argv[i + 1]
            i += 2
        elif argv[i] == "--square-state" and i + 1 < len(argv):
            raw = cast(dict[str, object], _load_json_arg(argv[i + 1], "square-state", "dict"))
            sq = _square_check()
            square_state = sq.compute_square_state(raw.get("issues", []), raw.get("prs", []))
            i += 2
        elif argv[i] == "--arcade-apps-state" and i + 1 < len(argv):
            raw = cast(dict[str, object], _load_json_arg(argv[i + 1], "arcade-apps-state", "dict"))
            aw = _arcade_app_watch()
            arcade_apps_state = aw.compute_app_state(raw.get("apps", []))
            i += 2
        elif argv[i] == "--gateway-toolset" and i + 1 < len(argv):
            raw = cast(dict[str, object], _load_json_arg(argv[i + 1], "gateway-toolset", "dict"))
            gt = _gateway_toolset_check()
            gateway_toolset_state = gt.compute_toolset_state(raw.get("tool_names", []))
            i += 2
        elif argv[i] == "--good-first-issues" and i + 1 < len(argv):
            good_first_issues_state = cast(list[dict[str, object]], _load_json_arg(argv[i + 1], "good-first-issues", "list"))
            i += 2
        elif argv[i] == "--ci-checks" and i + 1 < len(argv):
            ci_checks = cast(list[dict[str, object]], _load_json_arg(argv[i + 1], "ci-checks", "list"))
            i += 2
        elif argv[i] == "--cron-checks" and i + 1 < len(argv):
            cron_checks = cast(list[dict[str, object]], _load_json_arg(argv[i + 1], "cron-checks", "list"))
            i += 2
        elif argv[i] == "--child-files" and i + 1 < len(argv):
            child_files = cast(list[dict[str, object]], _load_json_arg(argv[i + 1], "child-files", "list"))
            i += 2
        elif argv[i] == "--voice-window-commits" and i + 1 < len(argv):
            voice_window_commits = cast(list[dict[str, object]], _load_json_arg(argv[i + 1], "voice-window-commits", "list"))
            i += 2
        elif argv[i] == "--github-stars" and i + 1 < len(argv):
            github_stars_count = int(argv[i + 1])
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
        arcade_apps_state=arcade_apps_state,
        gateway_toolset_state=gateway_toolset_state,
        good_first_issues_state=good_first_issues_state,
        ci_checks=ci_checks,
        cron_checks=cron_checks,
        child_files=child_files,
        voice_window_commits=voice_window_commits,
        github_stars_count=github_stars_count,
        # Task 374: this is the one real hourly CLI entrypoint -- the only
        # caller that should durably record this hour's real scribe sizes.
        record_scribe_growth=True,
        # Task 375: same reasoning, same one real caller, for words.
        record_words=True,
        # Task 420: same reasoning, same one real caller, for github_stars.
        record_github_stars=True,
    )
    if "--json" in argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_ritual_check(result))
    return 1 if result["broken"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
