#!/usr/bin/env python3
"""Task 425. Ogun's badge, finally cross-checked against itself.

`seam_engine/badge.py` (task 23) computes the read-only oath's badge fresh
every day: audit the live MCP server's tool catalog plus the sealed
Ledger's tamper chain, then render `fencepost/BADGE.json` red the instant
either finds a violation. `seam-scan.yml`'s own "repaint the read-only
badge" step runs that computation daily at noon UTC -- but deliberately
non-blocking (`python3 -m seam_engine.badge --write || true`; the step's
own comment reads "a red badge IS the report"). That means a real failure
INSIDE `compute_badge_state()` itself -- an import error, an exception
walking the Ledger, anything short of a clean render -- leaves whatever
`BADGE.json` last happened to say sitting in the repo, silently stale,
with the daily workflow still reporting green regardless.

Nothing anywhere re-derives the committed `fencepost/BADGE.json` against a
fresh live recomputation on any cadence shorter than "the next time
`seam-scan.yml` happens to run cleanly." `test_badge.py` and
`test_badge_site_doctrine.py` (`fencepost/seam_engine/tests/`) both prove
`compute_badge_state()` is correct in isolation and that the badge URL is
wired into the site -- neither ever re-runs the computation and diffs the
result against the file actually checked into the repo. That is the exact
"claims a mirror, never checked against it" shape STRATEGY.md's numeric
targets (task 159/421) and the recipe-scope oath (task 424) already closed
elsewhere in this repo, just never turned on Ogun's own badge.

`arcade-mcp-server` (the one real external dependency `seam_engine.server`
needs to build its live tool catalog) is not installed in every context
this checker might run in -- `dawn-run.yml`'s root test job installs only
PyYAML, on purpose (task 404's own note: arcade-mcp-server is the SECOND
job's dependency, kept out of the root suite). This checker's caller,
`tools/ritual_check.py`, runs unconditionally every hour and must not go
down over a missing optional dependency, so `live_badge_state()` catches
any exception from the live recompute and returns `None` rather than
raising -- `check_badge_freshness` then reports `status: "unavailable"`,
clean, never misreporting an environment gap as a doctrine violation.

Task 574. That "unavailable" default had never once flipped to a real
cross-check, anywhere -- `arcade-mcp-server` was never on the CALLING
interpreter's own `sys.path`, but it lives, right now, inside
`fencepost/seam_engine`'s own `uv`-managed venv (the same one
`recipe_command_check.py`, task 571/572, already shells out to for the
identical class of gap). `live_badge_state()` now falls back to invoking
`uv run python -c ...` inside `fencepost/seam_engine` when the direct
in-process import fails, parsing the single-line JSON `{color, message}`
it prints to stdout (its own diagnostic logging lands on stderr only,
confirmed live before writing this). `uv` absent, the subprocess failing,
or its stdout not parsing as the expected shape all still fall through to
`None` -- exactly `dawn-run.yml`'s lean root job's existing, correct
"unavailable" outcome, unchanged.

Usage:
    python3 tools/badge_freshness_check.py check
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BADGE_PATH = os.path.join(ROOT, "fencepost", "BADGE.json")
SEAM_ENGINE_DIR = os.path.join(ROOT, "fencepost", "seam_engine")
DEFAULT_UV_TIMEOUT = 60.0

# Printed as the last line of stdout by the uv subprocess below -- kept a
# single `json.dumps` call on one line so a trailing newline is the only
# thing to strip, no multi-line stdout parsing needed.
_LIVE_BADGE_SCRIPT = (
    "import json, sys; sys.path.insert(0, 'src'); "
    "import seam_engine.badge as badge; "
    "state = badge.compute_badge_state(); "
    "print(json.dumps({'color': state.color, 'message': state.message}))"
)

# Sentinel distinguishing "caller passed no live state, compute it fresh"
# from "caller explicitly passed live=None, meaning unavailable" -- a bare
# `None` default would conflate the two, the same ambiguity this repo's
# other optional-live-input checks (`check_ci`/`check_square`) avoid by
# using presence/absence of the keyword argument itself.
_COMPUTE_FRESH = object()


def _seam_badge():
    """Import the real `seam_engine.badge` module, the same `sys.path`
    convention `tools/ritual_check.py`'s own `_seam_ledger()` already uses
    to reach into the engine's `src/` layout from outside it."""
    src = os.path.join(ROOT, "fencepost", "seam_engine", "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    import seam_engine.badge as badge  # noqa: PLC0415

    return badge


def _live_badge_state_via_uv(
    seam_engine_dir: str = SEAM_ENGINE_DIR, timeout: float = DEFAULT_UV_TIMEOUT
) -> dict | None:
    """Fall back to the `fencepost/seam_engine` `uv` venv itself, the one
    place `arcade-mcp-server` is actually installed, when a bare in-process
    import can't reach it. Returns `None` on any of: no `uv` on PATH, the
    subprocess failing or timing out, or stdout not parsing as the exact
    `{color, message}` shape -- every failure mode collapses to the same
    "can't verify here" `None` the in-process path already returns, never a
    crash and never a guess."""
    if shutil.which("uv") is None:
        return None
    try:
        proc = subprocess.run(
            ["uv", "run", "python", "-c", _LIVE_BADGE_SCRIPT],
            cwd=seam_engine_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    stdout = proc.stdout.strip()
    if not stdout:
        return None
    try:
        payload = json.loads(stdout.splitlines()[-1])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or not {"color", "message"}.issubset(payload.keys()):
        return None
    return {"color": payload["color"], "message": payload["message"]}


def live_badge_state() -> dict | None:
    """Recompute the badge fresh -- the identical live introspection
    `seam_engine.badge.compute_badge_state()` performs -- reduced to the
    same `{color, message}` shape `fencepost/BADGE.json` holds on disk.

    Tries a bare in-process import first (unchanged from task 425); if that
    raises -- `arcade-mcp-server` not on THIS interpreter's `sys.path`, the
    common case -- falls back to running the same computation inside
    `fencepost/seam_engine`'s own `uv` venv, where the dependency actually
    lives. Returns `None` only once both paths have failed -- never lets an
    environment gap crash the caller."""
    try:
        badge = _seam_badge()
        state = badge.compute_badge_state()
    except Exception:  # noqa: BLE001 -- "can't verify" must never mean "verified broken"
        return _live_badge_state_via_uv()
    return {"color": state.color, "message": state.message}


def check_badge_freshness(badge_path: str = DEFAULT_BADGE_PATH, live=_COMPUTE_FRESH) -> dict:
    """Compares the committed `fencepost/BADGE.json` against a fresh live
    recomputation. `live` defaults to computing it now via
    `live_badge_state()`; pass an explicit dict (or `None`, meaning
    "treat as unavailable") to control the comparison directly -- the same
    dependency-injection seam every other doctrine check in this repo
    holds for its own live-vs-committed comparison."""
    if live is _COMPUTE_FRESH:
        live = live_badge_state()

    with open(badge_path, encoding="utf-8") as f:
        committed = json.load(f)
    committed_view = {"color": committed.get("color"), "message": committed.get("message")}

    if live is None:
        return {"clean": True, "status": "unavailable", "committed": committed_view, "live": None}

    agree = committed_view == live
    return {
        "clean": agree,
        "status": "current" if agree else "STALE",
        "committed": committed_view,
        "live": live,
    }


def format_badge_freshness(result: dict) -> str:
    if result["status"] == "unavailable":
        return "badge freshness: clean (live recompute unavailable in this environment, nothing to cross-check)"
    if result["clean"]:
        return f"badge freshness: clean (fencepost/BADGE.json matches a fresh live recompute: {result['committed']['message']!r})"
    return (
        f"badge freshness: STALE -- fencepost/BADGE.json says {result['committed']!r}, "
        f"a fresh live recompute says {result['live']!r} -- Ogun's oath badge is misreporting live, escalate now"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = check_badge_freshness()
    print(format_badge_freshness(out))
    sys.exit(0 if out["clean"] else 1)
