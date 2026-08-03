#!/usr/bin/env python3
"""Task 121. Off-By-One counts the tool that counts everything else.

`tools/ritual_check.py` hand-wires 56 `check_*` functions into one hourly
block: each is called inside `run_ritual_check`, its result assigned to a
dict key, and that key printed as a line in `format_ritual_check`. Three
separate places a single typo or a forgotten wire-up can silently drop a
check from the hourly block -- no traceback, no error, just a missing line
nobody's reading closely enough to notice is gone. Task 118 found exactly
this shape of drift in a README's tool count; tasks 98-106 built running
checks for five design constraints that could each go stale the same way.
The one tool every hour actually depends on had never once checked its own
wiring.

This module reads `tools/ritual_check.py`'s own source with `ast` -- no
import, no execution of the module under audit, so a check with a real bug
in its body can't crash the check that's supposed to catch it being
unwired. It proves, for every top-level `check_*` function:

1. it is actually CALLED somewhere inside `run_ritual_check`'s body
   (`missing_from_run` otherwise -- defined but never wired in);
2. the variable it's assigned to actually appears as a VALUE in
   `run_ritual_check`'s own returned dict literal (`missing_from_dict`
   otherwise -- called, but its result never makes it out);
3. the dict key it lands under is actually REFERENCED (`result["key"]`)
   somewhere inside `format_ritual_check` (`missing_from_format`
   otherwise -- wired and returned, but silently never printed).

Two dict keys are structurally exempt from rule 3: `now` (an echoed
timestamp, not a check result) and `broken` (the aggregate exit-code flag
read by `__main__`, not a printed line of its own -- every check that
contributes to it already prints its own status line).

**CORRECTED:** the "32" above was "27" from the day this module shipped
(task 121) until a later pass caught it -- five more `check_*` functions
(including this module's own `check_ritual_completeness` fold-in and, most
recently, task 145's `check_toolkits_in_use`) were added to
`tools/ritual_check.py` afterward without this docstring's own count ever
being revisited, the same "true when written, never rechecked against the
thing it describes" shape this module exists to catch in its subject.
`claimed_check_count()` below extracts this claim from the live docstring
text (never a second hand-typed copy), so `tests/test_ritual_completeness_check.py`
can cross-check it against the real count and a future addition can't let
this number go stale silently again. **Updated to 33** the same hour task
168's `check_scribe_growth` was wired in -- the first real test of whether
that promise holds. **Updated to 35** the same hour task 397's
`check_duplicate_regex` was wired in (34 was never itself narrated here,
just typed straight into the count by whichever prior task moved it last
along). **Updated to 36** the same hour task 407's `check_strategy_targets`
was wired in -- task 159 had built and tested `strategy_targets_check.py`
248 tasks earlier but never called it from `run_ritual_check`, and this
very module's own audit never caught the gap because it only ever reads
`check_*` functions already defined inside `ritual_check.py`'s own source,
never the separate tool files under `tools/` that a future wiring pass
might still be missing entirely
-- caught in passing while updating this one, not chased further).
**Updated to 37** the same hour task 408's `check_network_boundary` was
wired in -- tasks 163/164 had built and proved `network_boundary_check.py`
live but never called it from `run_ritual_check` either, the exact blind
spot task 407's note above named and left open, found here by directly
grepping every `tools/*.py` basename against `ritual_check.py`'s own
source rather than waiting for this module's audit to widen its own
reach. Task 409 closed that exact gap: `find_unwired_tool_files()` below
now performs that same basename grep as a live, running check (folded
into `compute_ritual_completeness()`'s own result as `unwired_tool_files`)
instead of a manual sweep someone has to remember to re-run by hand every
time a new tool file lands -- a file under `tools/` that is neither
referenced anywhere in `ritual_check.py`'s source nor named in
`EXEMPT_TOOL_FILES` (with a reason) now fails this check the same hour it
is added, rather than sitting unwired for months the way
`network_boundary_check.py` and `strategy_targets_check.py` both did.
**Updated to 38** the same hour task 410's `check_strategy_true_positive`
was wired in -- task 161 had built and proved `fencepost/seam_engine/src/
seam_engine/strategy_audit_target.py` live against STRATEGY.md's "Gap
true-positive rate" row 249 tasks earlier but never called it from
`run_ritual_check` either. `find_unwired_tool_files()`'s own basename grep
(task 409, just above) never would have caught this one regardless --
it only ever scans `tools/*.py`, never `fencepost/seam_engine/src/
seam_engine/*.py`, so this exact blind spot survives this module's own
audit even now; found by hand, the same way task 408 was, not by any
running check.

**Task 411** closes the gap task 410's own note left open, the same way
task 409 closed the equivalent `tools/*.py` gap for tasks 407/408:
`find_unwired_strategy_audit_modules()` below now scans
`fencepost/seam_engine/src/seam_engine/*.py` for real, live
STRATEGY.md-vs-code cross-check modules -- not by grepping for the string
"STRATEGY.md" (seven files in that directory quote it in prose:
`audit.py`, `closing_keywords.py`, `consent.py`, `draftback.py`,
`report.py`, `streak.py`, plus `strategy_audit_target.py` itself -- a
prose citation is not a live parse), but by the one precise, structural
signal the two real instances of this shape share and nothing else does:
a top-level module constant literally named `STRATEGY_MD` (`strategy_
audit_target.py` here, and `tools/strategy_targets_check.py`, task 159 --
already covered by `find_unwired_tool_files` since it lives in `tools/`).
A module holding that constant and never referenced anywhere in
`ritual_check.py`'s own source is exactly the shape that let
`strategy_audit_target.py` sit unwired for 249 tasks -- now a running
check instead of something found by hand every time. `compute_
ritual_completeness()` folds its result in as `unwired_strategy_audit_
modules`, the same class `unwired_tool_files` already holds.

**Updated to 39** the same hour task 412's `check_connected_users` was
wired in -- `tools/connected_users_check.py` (task 412, built to the
same shape task 145's `toolkits_in_use_check.py` already proved) cross-
checks `records/metrics.jsonl`'s `connected_users_oauth` field against
`consent_grant_log.real_distinct_human_count()`, the sibling ground-
truth field `toolkits_in_use_check.py`'s own docstring named ("both
real, both honestly 0/2 since founding" -- `shared_reports_check.py`
line 7) but for which no running cross-check had ever actually been
wired. `find_unwired_tool_files()` (task 409) already covers this file
going forward, since it lives in `tools/`.

**Updated to 40** the same hour task 413's `check_gap_true_positive_rate`
was wired in -- `tools/gap_true_positive_check.py` (task 413, the same
shape tasks 145/412 already proved) cross-checks `records/metrics.jsonl`'s
`gap_true_positive_rate` field against `seam_engine.audit.audit_ledger()`'s
real, live tally. Ogun's own highest-stakes leading metric ("false-positive
gaps... erode the read-trust the whole product rests on") had a sibling
check (task 410's `check_strategy_true_positive`) for the STRATEGY.md
TARGET, but nothing ever read the hand-recorded rate itself back against
the same live Ledger. `find_unwired_tool_files()` (task 409) already
covers this file going forward, since it lives in `tools/`.

**Updated to 43** the same hour task 420's `check_github_stars` was
wired in -- `tools/github_stars_check.py` (task 420) cross-checks
`records/metrics.jsonl`'s `github_stars` field against the last recorded
live `Github_CountStargazers` read. STRATEGY.md's own explicit numeric
metric row ("GitHub stars | lagging | 1,000 (Star Covenant, unbegged) |
off-by-one") was the one sibling among `distinct_toolkits_in_use` (145)/
`connected_users_oauth` (412)/`gap_true_positive_rate` (413)/
`reports_shipped_today` (415)/`tasks_shipped_today` (416) that whole
campaign never touched. `find_unwired_tool_files()` (task 409) already
covers this file going forward, since it lives in `tools/`.

**Updated to 42** the same hour task 416's `check_tasks_shipped` was
wired in -- the last of the four sibling metrics.jsonl fields task 415
found and left open now has a live cross-check too. **Updated to 41** the
same hour task 415's `check_report_shipped` was
wired in -- `tools/report_shipped_check.py` (task 415, the same shape
tasks 145/412/413 already proved) cross-checks `records/metrics.jsonl`'s
`reports_shipped_today` field against `fencepost/REPORTS/<claimed
date>.md`'s own real existence on disk. Off-By-One's own STRATEGY.md row
("Daily Fencepost Report shipped (town dogfood)") had sat as the last of
four sibling metrics.jsonl fields with no live cross-check, closed here
by the god whose row it actually is. `find_unwired_tool_files()` (task
409) already covers this file going forward, since it lives in `tools/`.

**Updated to 47** the same hour task 434's `check_escape_sequences` was
wired in -- `tools/escape_sequence_check.py` (task 434) compiles every
tracked `.py` file and flags any real "invalid escape sequence"
`DeprecationWarning`, the class of bug found live this same hour pinned
to `tools/roadmap_archive.py:2`. `find_unwired_tool_files()` (task 409)
already covers this file going forward, since it lives in `tools/`.

**Updated to 48** the same hour task 449's `check_what_moved_cadence` was
wired in -- `tools/what_moved_check.py` (task 449) closes Zashiki's own
half of the weekly Cluster Day ritual that `check_cluster_day_cadence`
(task 387/406) left un-sensed: whether `docs/what-moved.html` actually
gets updated "one day in arrears" each Monday. It never has, past the
page's own founding-day placeholder -- a genuine lapse, surfaced honestly
rather than silently absorbed. `find_unwired_tool_files()` (task 409)
already covers this file going forward, since it lives in `tools/`.

**Updated to 50** the same hour task 463's `check_thegap_cadence` was
wired in -- `tools/thegap_check.py` (task 463) closes the third and
last leg of the weekly Cluster Day ritual, Off-By-One's own `/thegap/`
Gap-bug hide/confess cadence, which `check_what_moved_cadence`'s own
docstring had already named as missing and left open for whichever hour
picked it up next. `find_unwired_tool_files()` (task 409) already
covers this file going forward, since it lives in `tools/`.

**Updated to 51** the same hour task 464's `check_gateway_toolset` was
wired in (a re-check record for `fencepost/SCOPES.md`'s live Gmail/
Calendar tool-exposure claim) -- this docstring's own leading count went
un-narrated the hour it happened, corrected here rather than left silent.

**Updated to 52** the same hour task 465's `check_nyx_traffic_cadence`
was wired in -- `tools/nyx_traffic_check.py` (task 465) closes the
fourth leg of the weekly Cluster Day ritual, Nyx's own weekly traffic
report, which `cluster_day_check.py`'s own docstring had named from the
start (alongside Ananse's chronicle, Zashiki's what-moved page, and
Off-By-One's thegap doctrine) but nothing had ever built a sensor for.
`find_unwired_tool_files()` (task 409) already covers this file going
forward, since it lives in `tools/`.

**Updated to 53** the same hour task 473's `check_house_links` was wired
in -- task 472 widened `site_link_check.py` to a `houses/`-aware
`require_index=False` mode but left the `ritual_check.py` wire-up as
named, real, left-open future work rather than ship it half-built (a
naive widening would have cried wolf on 26 already-working GitHub
folder links plus a journal entry quoting broken-link syntax as prose).
Task 473 fixed both false-positive classes in `site_link_check.py`
itself first, confirmed `find_violations("houses", require_index=False)`
reads clean, then did the actual three-place wire-up this file audits.

**Updated to 54** the same hour task 477's `check_good_first_issues` was
wired in -- CHARTER.md Appendix B names "good-first-issues stocked" as
Ogun's job, alongside "links unbroken" and "badge green" (both already
checked here); a live read found the `good first issue` label had never
once been attached to a real issue, the same "named in the Charter,
never turned into a check" shape task 423 already closed for its own
sibling clause.

**Updated to 55** the same hour task 483's `check_fencepost_links` was
wired in -- the third sibling of `check_site_links`/`check_house_links`,
pointed at `fencepost/` itself (GitHub-browsed, same `require_index=
False` rule as `houses/`), never checked before. Its first live run
found a real break: `fencepost/README.md`'s own badge-explainer link to
`seam_engine/badge.py` was missing the `src/` layout segment the file
actually lives under.

**Updated to 56** the same hour task 506's `check_issue_template_links`
was wired in -- the fourth sibling, pointed at `.github/ISSUE_TEMPLATE/`
itself (GitHub-browsed, same `require_index=False` rule as `houses/`/
`fencepost/`), Esu-Elegba's own claimed edge of the repo and never
checked before by any of this file's three existing siblings nor by
anything else in the tree. Its first live run found the tree already
clean -- no broken link to fix -- but four of the five templates
(`crossing.md`, `decree-proposal.md`, `fork-my-own-society.md`,
`gap-report.md`) had carried zero test coverage of any kind until this
hour, the fifth (`point-fencepost.md`) having only ever had its scope
TABLE doctrine-checked (`test_consent_doctrine.py`, task 136), never its
two markdown links' actual resolution on disk.

Usage:
    python3 tools/ritual_completeness_check.py check
"""
from __future__ import annotations

import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_RITUAL_CHECK_PATH = os.path.join(ROOT, "tools", "ritual_check.py")
DEFAULT_TOOLS_DIR = os.path.join(ROOT, "tools")
DEFAULT_SEAM_ENGINE_DIR = os.path.join(
    ROOT, "fencepost", "seam_engine", "src", "seam_engine"
)
STRATEGY_MD_CONSTANT_NAME = "STRATEGY_MD"
RUN_FUNC_NAME = "run_ritual_check"
FORMAT_FUNC_NAME = "format_ritual_check"
EXEMPT_DICT_KEYS = {"now", "broken"}

CLAIMED_COUNT_PATTERN = re.compile(r"hand-wires (\d+) `check_\*` functions")

# Every tools/*.py file NOT expected to be loaded from run_ritual_check,
# and why -- reviewed and confirmed true, one by one, task 409 (the same
# audit tasks 407/408 each did by hand: grep every real tools/*.py basename
# against ritual_check.py's own source). A file added here without a real
# reason is exactly the "flattering claim, never rechecked" shape this
# whole module exists to catch -- so a new entry needs a reason as honest
# as the ones below, not a rubber stamp.
EXEMPT_TOOL_FILES = {
    "ritual_check.py": "the ritual runner itself, not a tool it loads",
    "card.py": "one-off X-card page generator (task 121's forge-and-post flow), not a periodic repo-state check",
    "oath_badge.py": "one-off read-only badge JSON renderer, not a periodic repo-state check",
    "roadmap_archive.py": "one-off length-triggered archival tool run by hand, not a periodic repo-state check",
    "closing_keyword_guard.py": "takes a commit-message-and-open-issues-csv argument each call -- a per-commit guard, not the hourly repo-state sweep run_ritual_check folds",
    "consent_grant_log.py": "append-only log library, called by toolkits_in_use_check.py (already wired) rather than loaded standalone",
    "text_patterns.py": "shared regex-pattern library (task 418), imported directly by the 11 tools/*.py files that use it rather than loaded standalone by ritual_check.py (task 484: grown from the original nine as later tasks, task 461 among them, wired more callers without revisiting this count)",
    "metrics_reader.py": "shared records/metrics.jsonl reader library (task 508), imported directly by the six tools/*.py checks that use it (connected_users_check.py, gap_true_positive_check.py, github_stars_check.py, report_shipped_check.py, tasks_shipped_check.py, toolkits_in_use_check.py -- all already wired) rather than loaded standalone by ritual_check.py, the same shape consent_grant_log.py/text_patterns.py already hold",
    "iso_time.py": "shared Z-suffixed ISO timestamp parser library (task 509), imported directly by the three tools/*.py checks that use it (cron_health.py, voice_window_check.py, x_outage_tracker.py -- all already wired) rather than loaded standalone by ritual_check.py, the same shape metrics_reader.py/consent_grant_log.py/text_patterns.py already hold",
    "jsonl_append.py": "shared append-one-JSON-line library (task 510), imported directly by the ten tools/*.py checks that use it (arcade_app_watch.py, change_gate.py, ci_watch.py, gateway_toolset_check.py, github_stars_check.py, scribe_growth_check.py, square_check.py, word_watch.py, x_outage_tracker.py, x_post_queue.py -- all already wired) rather than loaded standalone by ritual_check.py, the same shape metrics_reader.py/iso_time.py/consent_grant_log.py/text_patterns.py already hold",
}

# Every fencepost/seam_engine/src/seam_engine/*.py file that defines a live
# STRATEGY_MD constant (see `_defines_strategy_md_constant`) but is NOT
# expected to be loaded from run_ritual_check, and why. Empty today by
# design, not by omission -- the one real instance of this shape
# (`strategy_audit_target.py`) IS wired (task 410). A new entry here needs
# a reason as honest as `EXEMPT_TOOL_FILES`'s own, not a rubber stamp.
EXEMPT_SEAM_ENGINE_STRATEGY_MODULES: dict[str, str] = {}


def claimed_check_count(doc: str | None = None) -> int:
    """Extract the self-reported check_* count from this module's own
    docstring's "hand-wires N `check_*` functions" sentence (or from a
    supplied doc string, for mutation-based hand-verification) -- never a
    second hand-typed copy of the number, so a stale claim can be caught by
    comparing this against the real, live count in tools/ritual_check.py
    instead of trusting the prose."""
    doc = __doc__ if doc is None else doc
    match = CLAIMED_COUNT_PATTERN.search(doc or "")
    if match is None:
        raise ValueError(
            "could not find a 'hand-wires N `check_*` functions' claim in the docstring"
        )
    return int(match.group(1))


TEXT_PATTERNS_IMPORTER_COUNT_PATTERN = re.compile(
    r"imported directly by the (\d+) tools/\*\.py files that use it"
)


def claimed_text_patterns_importer_count(entry: str | None = None) -> int:
    """Extract the self-reported text_patterns.py importer count from
    EXEMPT_TOOL_FILES's own entry (or a supplied string, for mutation-based
    hand-verification) -- never a second hand-typed copy of the number, so a
    stale claim can be caught by comparing this against the real, live count
    of tools/*.py files that import text_patterns.py, instead of trusting
    the prose. Task 484: this entry drifted from 9 to a real 11 without
    anyone revisiting it."""
    entry = EXEMPT_TOOL_FILES["text_patterns.py"] if entry is None else entry
    match = TEXT_PATTERNS_IMPORTER_COUNT_PATTERN.search(entry)
    if match is None:
        raise ValueError(
            "could not find an 'imported directly by the N tools/*.py files' "
            "claim in the supplied entry"
        )
    return int(match.group(1))


def real_text_patterns_importer_count(tools_dir: str = DEFAULT_TOOLS_DIR) -> int:
    """Live-count the tools/*.py files that import text_patterns.py directly,
    the same real value claimed_text_patterns_importer_count's docstring
    claim is checked against."""
    count = 0
    for name in os.listdir(tools_dir):
        if not name.endswith(".py") or name == "text_patterns.py":
            continue
        path = os.path.join(tools_dir, name)
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name == "text_patterns" for alias in node.names
            ):
                count += 1
                break
    return count


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _check_function_names(tree: ast.Module) -> set:
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("check_")
    }


def _called_functions(func: ast.FunctionDef, wanted: set) -> dict:
    """{function_name: assigned_variable_name} for every `var =
    check_x(...)` assignment anywhere inside `func`'s own body -- walked,
    not just top-level statements, since `run_ritual_check` calls some
    checks (e.g. `check_vault_leak`) conditionally inside an `if`/`else`
    branch rather than unconditionally at the top level."""
    called = {}
    for stmt in ast.walk(func):
        if not isinstance(stmt, ast.Assign):
            continue
        if not isinstance(stmt.value, ast.Call):
            continue
        call_func = stmt.value.func
        if not isinstance(call_func, ast.Name) or call_func.id not in wanted:
            continue
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            continue
        called[call_func.id] = stmt.targets[0].id
    return called


def _return_dict(func: ast.FunctionDef) -> dict:
    """{dict_key: variable_name_or_None} for the dict literal in the last
    top-level `return {...}` inside `func`'s own body. Non-Name values
    (e.g. a literal or expression) map to None -- nothing to cross-check
    a variable against, but still a real key."""
    result = {}
    for stmt in func.body:
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Dict):
            for key_node, val_node in zip(stmt.value.keys, stmt.value.values):
                if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                    var_name = val_node.id if isinstance(val_node, ast.Name) else None
                    result[key_node.value] = var_name
    return result


def _printed_keys(func: ast.FunctionDef) -> set:
    """Every string key subscripted off a variable literally named
    `result` anywhere inside `func` (loops, branches, comprehensions --
    walked, not just top-level statements, since format_ritual_check
    reads `result[...]` inside for-loops and if/else branches)."""
    keys = set()
    for node in ast.walk(func):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "result"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            keys.add(node.slice.value)
    return keys


def find_unwired_tool_files(
    tools_dir: str | None = None, ritual_check_path: str | None = None
) -> list:
    """Every tools/*.py file whose basename never appears as a quoted
    string literal in ritual_check.py's own source (the same shape every
    real `_load(..., os.path.join(ROOT, "tools", "<name>.py"))` call site
    already takes -- see `_load`'s call sites in ritual_check.py), and
    which isn't named in `EXEMPT_TOOL_FILES` with a reason. This is the
    literal grep tasks 407 and 408 each ran by hand before wiring in the
    checker they found sitting unused -- now a running check instead of a
    manual sweep someone has to remember to redo."""
    tools_dir = tools_dir or DEFAULT_TOOLS_DIR
    ritual_check_path = ritual_check_path or DEFAULT_RITUAL_CHECK_PATH
    with open(ritual_check_path, encoding="utf-8") as f:
        source = f.read()

    unwired = []
    for name in sorted(os.listdir(tools_dir)):
        if not name.endswith(".py"):
            continue
        if name in EXEMPT_TOOL_FILES:
            continue
        if f'"{name}"' in source or f"'{name}'" in source:
            continue
        unwired.append(name)
    return unwired


def _defines_strategy_md_constant(path: str) -> bool:
    """Whether `path`'s own top-level source defines a module-level
    constant literally named STRATEGY_MD -- the exact, structural signal
    both known STRATEGY.md-live-cross-check modules
    (`tools/strategy_targets_check.py`, `strategy_audit_target.py`) share,
    and that the six other seam_engine files which merely quote
    STRATEGY.md in prose (`audit.py`, `closing_keywords.py`, `consent.py`,
    `draftback.py`, `report.py`, `streak.py`) do not: a real, live parse of
    the document's own path, not a citation of it in a docstring."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    for node in tree.body:
        targets = None
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if targets is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == STRATEGY_MD_CONSTANT_NAME:
                return True
    return False


def find_unwired_strategy_audit_modules(
    seam_engine_dir: str | None = None, ritual_check_path: str | None = None
) -> list:
    """Every fencepost/seam_engine/src/seam_engine/*.py file that defines a
    live STRATEGY_MD constant (`_defines_strategy_md_constant`) and whose
    bare module stem (e.g. "strategy_audit_target", the name it is
    imported under -- `import seam_engine.strategy_audit_target`, never a
    quoted `"<name>.py"` file path the way `tools/*.py` is loaded) never
    appears anywhere in ritual_check.py's own source, and which isn't
    named in EXEMPT_SEAM_ENGINE_STRATEGY_MODULES with a reason. Task 410's
    own closing note named this exact blind spot: `find_unwired_tool_files`
    (task 409) only ever scans `tools/*.py`, never
    `fencepost/seam_engine/src/seam_engine/*.py`, so a future module built
    the same shape `strategy_audit_target.py` was (task 161, unwired for
    249 tasks) could sit unwired indefinitely and this module's own audit
    would never catch it. Missing directory (e.g. a fixture ritual_check.py
    with no matching seam_engine tree) reads as zero violations, not an
    error -- there is nothing to audit."""
    seam_engine_dir = seam_engine_dir or DEFAULT_SEAM_ENGINE_DIR
    ritual_check_path = ritual_check_path or DEFAULT_RITUAL_CHECK_PATH
    if not os.path.isdir(seam_engine_dir):
        return []
    with open(ritual_check_path, encoding="utf-8") as f:
        source = f.read()

    unwired = []
    for name in sorted(os.listdir(seam_engine_dir)):
        if not name.endswith(".py") or name == "__init__.py":
            continue
        if name in EXEMPT_SEAM_ENGINE_STRATEGY_MODULES:
            continue
        path = os.path.join(seam_engine_dir, name)
        if not _defines_strategy_md_constant(path):
            continue
        stem = name[:-3]
        if re.search(rf"\b{re.escape(stem)}\b", source):
            continue
        unwired.append(name)
    return unwired


def compute_ritual_completeness(
    source_path: str | None = None,
    tools_dir: str | None = None,
    seam_engine_dir: str | None = None,
) -> dict:
    source_path = source_path or DEFAULT_RITUAL_CHECK_PATH
    with open(source_path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=source_path)

    check_functions = _check_function_names(tree)
    run_func = _find_function(tree, RUN_FUNC_NAME)
    format_func = _find_function(tree, FORMAT_FUNC_NAME)

    if run_func is None or format_func is None:
        return {
            "clean": False,
            "missing_from_run": sorted(check_functions),
            "missing_from_dict": [],
            "missing_from_format": [],
            "unwired_tool_files": find_unwired_tool_files(tools_dir, source_path),
            "unwired_strategy_audit_modules": find_unwired_strategy_audit_modules(
                seam_engine_dir, source_path
            ),
            "error": f"could not find {RUN_FUNC_NAME}/{FORMAT_FUNC_NAME} in {source_path}",
        }

    called = _called_functions(run_func, check_functions)
    missing_from_run = sorted(check_functions - called.keys())

    return_dict = _return_dict(run_func)
    var_to_key = {v: k for k, v in return_dict.items() if v is not None}
    missing_from_dict = sorted(
        fname for fname, var in called.items() if var not in var_to_key
    )

    printed = _printed_keys(format_func)
    checked_keys = {k for k in return_dict if k not in EXEMPT_DICT_KEYS}
    missing_from_format = sorted(checked_keys - printed)

    unwired_tool_files = find_unwired_tool_files(tools_dir, source_path)
    unwired_strategy_audit_modules = find_unwired_strategy_audit_modules(
        seam_engine_dir, source_path
    )

    clean = not (
        missing_from_run
        or missing_from_dict
        or missing_from_format
        or unwired_tool_files
        or unwired_strategy_audit_modules
    )
    return {
        "clean": clean,
        "missing_from_run": missing_from_run,
        "missing_from_dict": missing_from_dict,
        "missing_from_format": missing_from_format,
        "unwired_tool_files": unwired_tool_files,
        "unwired_strategy_audit_modules": unwired_strategy_audit_modules,
    }


def format_ritual_completeness(result: dict) -> str:
    if result["clean"]:
        return "ritual completeness: clean (every check_* function is called, returned, and printed; every tools/*.py file is wired or exempt)"
    parts = []
    if result["missing_from_run"]:
        parts.append(f"never called in {RUN_FUNC_NAME}: {', '.join(result['missing_from_run'])}")
    if result["missing_from_dict"]:
        parts.append(f"called but dropped from the return dict: {', '.join(result['missing_from_dict'])}")
    if result["missing_from_format"]:
        parts.append(f"returned but never printed in {FORMAT_FUNC_NAME}: {', '.join(result['missing_from_format'])}")
    if result.get("unwired_tool_files"):
        parts.append(f"tools/*.py never loaded from {RUN_FUNC_NAME} and not exempt: {', '.join(result['unwired_tool_files'])}")
    if result.get("unwired_strategy_audit_modules"):
        parts.append(
            "seam_engine/*.py STRATEGY.md cross-check module(s) never referenced in "
            f"{RUN_FUNC_NAME} and not exempt: {', '.join(result['unwired_strategy_audit_modules'])}"
        )
    return "ritual completeness: BROKEN -- " + "; ".join(parts)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = compute_ritual_completeness()
    print(format_ritual_completeness(out))
    sys.exit(0 if out["clean"] else 1)
