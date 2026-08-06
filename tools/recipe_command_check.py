#!/usr/bin/env python3
"""Task 571. Ogun: the README says it runs. Nothing had ever made it run.

Every real recipe under `RECIPES/<slug>/README.md` closes with a "Run it
yourself:" fenced shell block — the literal `cd fencepost/seam_engine` +
`PYTHONPATH=... uv run python ../RECIPES/<slug>/detector.py` command a
stranger reading the recipe, or a stranger reading `ONBOARDING.md`'s own
"prove the engine is real before you trust it" pitch, is invited to copy
and paste. `test_recipes.py` (task 22 and every recipe task since) proves
each recipe's `run_recipe_scan` entrypoint works — but it calls that
Python function directly, through pytest's own import machinery, never
the literal command string printed in the README, never through the real
`uv run` subprocess a human would actually type. `recipe_readme_check.py`
(task 426) proves the README's *links* stay honest; nothing has ever
proved its *commands* do. A recipe's own `PYTHONPATH` line differs by
recipe (some need a second `:../RECIPES/<slug>` entry, most don't — see
`fixtures/`'s per-recipe shape) precisely because some detectors import a
local helper module their sibling doesn't; a future recipe edit that adds
such an import and forgets to widen its own README's `PYTHONPATH` line
would ship a broken copy-paste instruction that nothing today would ever
catch — the exact "documented, not verified" gap this file closes, in
the same spirit `SCOPES.md`'s own oath line draws: "checked, not
promised."

This module actually executes each recipe's own literal fenced block —
via `subprocess`, `cwd`'d at `fencepost/seam_engine` the same way the
README's own `cd` line says, `bash -c` over the exact remaining line(s)
verbatim, never a rewritten or "equivalent" command — and checks three
things a static grep of the text could never catch:

1. the block actually exists and starts with `cd fencepost/seam_engine`
   (`no_block`/`unexpected_shape` otherwise);
2. the command actually exits 0 (`command_failed` otherwise, carrying the
   real stderr tail so the failure is legible without re-running it by
   hand);
3. its stdout actually parses as JSON and carries the same top-level keys
   every real detector's own `run_recipe_scan` promises
   (`generated_at`, `source`, `confidence_bar`, `separation_margin`,
   `primary_gap`, `tail`, `excluded` — the shape `test_recipes.py` already
   asserts on the *direct* call; this is the same assertion on the
   *documented* one) (`malformed_output` otherwise).

Local subprocess only — no repo file is written, no Arcade tool is
called, no real account is touched; `uv run` resolves against this repo's
own already-committed `uv.lock` and the local cache the standing
`pytest`/CI environment already builds, the same local-only shape
`child_work_check.py`'s own `git cat-file -e` subprocess call holds (the
network-boundary guarantee itself is deliberately not asserted verbatim
here, since a cold, never-synced environment could in principle need a
fetch — the hourly ritual's own checkout is never cold).

Usage:
    python3 tools/recipe_command_check.py check
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FENCEPOST_ROOT = os.path.join(ROOT, "fencepost")
DEFAULT_SEAM_ENGINE_DIR = os.path.join(DEFAULT_FENCEPOST_ROOT, "seam_engine")

_SEAM_ENGINE_SRC = os.path.join(DEFAULT_FENCEPOST_ROOT, "seam_engine", "src")
if _SEAM_ENGINE_SRC not in sys.path:
    sys.path.insert(0, _SEAM_ENGINE_SRC)
from seam_engine.recipes import discover_recipes  # noqa: E402

_RUN_BLOCK_RE = re.compile(r"Run it yourself:\s*\n\n```\n(.*?)\n```", re.DOTALL)

# Matches a documented command that actually invokes the `uv` binary (a
# bare word boundary around `uv`, not e.g. a path fragment that merely
# contains those letters) -- every real recipe's own "Run it yourself"
# block opens with `PYTHONPATH=... uv run python ...`; this module's own
# test fixtures deliberately don't, so they're never matched here.
_UV_INVOCATION_RE = re.compile(r"(?:^|[\s;&|])uv(?:\s|$)")

# The keys every real detector's own run_recipe_scan() output dict promises
# (see e.g. RECIPES/issue-body-dangling-reference/detector.py's own
# run_recipe_scan) -- the same shape test_recipes.py's direct-call tests
# already assert on, asserted here on the documented command's own stdout.
_EXPECTED_OUTPUT_KEYS = {
    "generated_at", "source", "confidence_bar", "separation_margin",
    "primary_gap", "tail", "excluded",
}

_DEFAULT_TIMEOUT_S = 60.0


def _run_it_yourself_block(readme_text: str) -> str | None:
    """The fenced block's inner text (no closing/opening fence), or None
    if the README carries no "Run it yourself:" section at all."""
    m = _RUN_BLOCK_RE.search(readme_text)
    return m.group(1) if m else None


_RESULTS_CACHE: dict[tuple[str, str, float], dict] = {}


def clear_cache() -> None:
    """Task 588: drop every memoized `check_recipe_commands()` result.
    Only real callers are tests that want to force a genuinely fresh
    live run (e.g. after rewriting a recipe's own README in place);
    production's one-call-per-process shape never needs this."""
    _RESULTS_CACHE.clear()


def check_recipe_commands(
    fencepost_root: str = DEFAULT_FENCEPOST_ROOT,
    seam_engine_dir: str = DEFAULT_SEAM_ENGINE_DIR,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict:
    """Task 588: memoized per (fencepost_root, seam_engine_dir, timeout)
    for the lifetime of the process, the same fix `vault_leak_check.py`'s
    `find_leaks()` got at task 367 and for the identical reason:
    `run_ritual_check()`'s `check_recipe_commands()` call has no way to
    skip this check, so every one of `tests/test_ritual_check.py`'s
    FoldCase methods that calls `run_ritual_check()` without a
    `recipe_command_*` override was triggering a fresh live run of all
    51 real recipes' own `uv run` subprocess commands -- work that
    cannot have changed between calls within one process, and expensive
    enough (dozens of subprocess spawns each) that CI's own dawn-run
    #1023 timed out mid-suite and failed 72 unrelated FoldCase tests
    that never touch a recipe at all. A real hourly `ritual_check.py`
    run is a fresh process that calls this exactly once, so the cache
    is inert there -- production still runs every recipe fresh every
    single hour."""
    key = (os.path.realpath(fencepost_root), os.path.realpath(seam_engine_dir), timeout)
    if key not in _RESULTS_CACHE:
        _RESULTS_CACHE[key] = _check_recipe_commands_uncached(fencepost_root, seam_engine_dir, timeout)
    return dict(_RESULTS_CACHE[key])


def _check_recipe_commands_uncached(
    fencepost_root: str = DEFAULT_FENCEPOST_ROOT,
    seam_engine_dir: str = DEFAULT_SEAM_ENGINE_DIR,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict:
    """Execute every real recipe's own README-documented command, live,
    and return `clean: True` only when every one exists, runs, and
    produces the shape it promises. Never a bare pass/fail -- every
    problem names the exact recipe and the exact reason.

    `dawn-run.yml`'s `the-oath` job (the root `tests/` suite this check's
    own `run_ritual_check()` fold gets exercised from) deliberately
    installs only `PyYAML` -- task 404's own note, the same lean-root-job
    boundary `badge_freshness_check.py` (task 425) already had to respect
    for `arcade-mcp-server`. Every real recipe's documented command
    starts with `PYTHONPATH=... uv run python ...` and needs `uv` on
    PATH; that job doesn't have it, so a bare subprocess call would fail
    every real recipe with `exit 127: uv: command not found` --
    dawn-run #1023/#1025 lived this for real. Same fix as task 425's
    `live_badge_state()` in spirit -- detect the missing dependency and
    report it as `status: "unavailable"`, clean, rather than
    misreporting an environment gap as a doctrine violation -- but
    scoped PER COMMAND, not a blanket process-wide skip: this module's
    own test fixtures (`tests/test_recipe_command_check.py`,
    `RecipeCommandFoldCase` in `tests/test_ritual_check.py`) document a
    plain `python3 ...` command that needs no `uv` at all, and a bare
    `shutil.which("uv") is None` early-return would wrongly stop
    checking those too -- turning a genuinely broken fixture recipe into
    a false "clean" and a genuinely clean one into an unverifiable
    "unavailable", neither of which the fixture tests intend. Only a
    documented command that actually invokes `uv` is skipped when `uv`
    isn't on PATH; every other command (real or fixture) still runs and
    is judged for real. `the-seam-oath` job (which does install `uv` via
    its own `fencepost/seam_engine` setup) and any real hourly
    `ritual_check.py` run in a full dev environment both still execute
    every real recipe for real -- none of their documented commands ever
    hit the skip."""
    real_slugs = sorted(m.slug for m in discover_recipes(Path(fencepost_root)))

    no_block: list[str] = []
    unexpected_shape: list[str] = []
    command_failed: list[dict] = []
    malformed_output: list[dict] = []
    skipped_no_uv: list[str] = []
    checked = 0
    uv_present = shutil.which("uv") is not None

    for slug in real_slugs:
        readme_path = os.path.join(fencepost_root, "RECIPES", slug, "README.md")
        if not os.path.isfile(readme_path):
            # recipe_readme_check.py already names a recipe with no
            # README.md at all (`missing_readme`) -- this check's own job
            # starts only once a block exists to run, so a slug with no
            # README.md at all is silently skipped here, not double-
            # counted under a different name.
            continue
        with open(readme_path, encoding="utf-8") as f:
            readme_text = f.read()
        block = _run_it_yourself_block(readme_text)
        if block is None:
            no_block.append(slug)
            continue

        lines = [line for line in block.splitlines() if line.strip()]
        if not lines or lines[0].strip() != "cd fencepost/seam_engine":
            unexpected_shape.append(slug)
            continue

        command = "\n".join(lines[1:])
        if not uv_present and _UV_INVOCATION_RE.search(command):
            skipped_no_uv.append(slug)
            continue

        checked += 1
        try:
            proc = subprocess.run(
                ["bash", "-c", command],
                cwd=seam_engine_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            command_failed.append({"slug": slug, "reason": f"timed out after {timeout}s"})
            continue

        if proc.returncode != 0:
            command_failed.append({
                "slug": slug,
                "reason": f"exit {proc.returncode}: {proc.stderr.strip()[-2000:]}",
            })
            continue

        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            malformed_output.append({"slug": slug, "reason": f"stdout not valid JSON: {exc}"})
            continue

        if not isinstance(payload, dict) or not _EXPECTED_OUTPUT_KEYS.issubset(payload.keys()):
            got = sorted(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
            malformed_output.append({
                "slug": slug,
                "reason": f"missing expected key(s), got: {got}",
            })

    clean = not (no_block or unexpected_shape or command_failed or malformed_output)
    if skipped_no_uv:
        status = "unavailable" if checked == 0 else "partially_unavailable"
    else:
        status = "checked"
    return {
        "clean": clean,
        "status": status,
        "real_count": len(real_slugs),
        "checked_count": checked,
        "no_block": no_block,
        "unexpected_shape": unexpected_shape,
        "command_failed": command_failed,
        "malformed_output": malformed_output,
        "skipped_no_uv": skipped_no_uv,
    }


def format_result(result: dict) -> str:
    status = result.get("status")
    if status == "unavailable":
        return (
            f"recipe commands: clean (uv unavailable in this environment, "
            f"{len(result.get('skipped_no_uv', []))} real recipe(s) skipped, nothing to execute)"
        )
    if result["clean"]:
        if status == "partially_unavailable":
            return (
                f"recipe commands: clean ({result['checked_count']}/{result['real_count']} real "
                f"recipe(s) executed live and returned the shape it promises, "
                f"{len(result['skipped_no_uv'])} skipped -- uv unavailable in this environment)"
            )
        return (
            f"recipe commands: clean ({result['checked_count']}/{result['real_count']} real "
            f"recipe(s)' own documented 'Run it yourself' command executed live and returned "
            f"the shape it promises)"
        )
    problems = []
    if result["no_block"]:
        problems.append(f"no 'Run it yourself' block: {', '.join(result['no_block'])}")
    if result["unexpected_shape"]:
        problems.append(f"block doesn't start with 'cd fencepost/seam_engine': {', '.join(result['unexpected_shape'])}")
    if result["command_failed"]:
        names = ", ".join(f"{p['slug']} ({p['reason']})" for p in result["command_failed"])
        problems.append(f"documented command fails to run: {names}")
    if result["malformed_output"]:
        names = ", ".join(f"{p['slug']} ({p['reason']})" for p in result["malformed_output"])
        problems.append(f"documented command's own output doesn't match the promised shape: {names}")
    return "recipe commands: BROKEN -- " + "; ".join(problems)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_recipe_commands()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
