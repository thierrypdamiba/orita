#!/usr/bin/env python3
"""Task 2523. Zashiki-Warashi: ONBOARDING.md's own words say it runs. Nothing
had ever made ONBOARDING.md's safe, copy-paste commands run.

`recipe_command_check.py` (task 571) closed the "documented, not verified"
gap for every `RECIPES/*/README.md`'s own "Run it yourself" block --
executing the literal command a stranger would copy and paste, not just
calling the detector through pytest's own import machinery.
`check_recipe_readme`/`check_site_recipe_readme` closed the same gap for
*links*. `ONBOARDING.md` -- the one page a stranger reads BEFORE trusting
Fencepost enough to connect a real account (see its own opening line: "i
wrote this page because somebody forking fencepost is about to be asked to
connect real accounts to a repo full of AI gods, and 'trust us' is not an
answer") -- had no equivalent. It makes two concrete, falsifiable claims
about commands a reader is told to actually run:

1. minute 1 ("install, and prove the engine is real before you trust it"):
   `uv run python -m pytest -q` "should print something like `4584 passed`".
2. minute 4 ("bring your own gateway"): `uv run python -m seam_engine.badge`
   prints `"N/N tools read-only"` -- the live introspection a reader is told
   to run instead of taking the town's word for it.

Both claims can drift silently: the test count moves every time a test is
added or removed (the exact history `BUILDLOG.md`'s own rows already show,
re-reading "4584 passed" dozens of times since this suite had fewer tests),
and the badge's "N/N" ratio moves if a tool is ever added to `server.py`.
Nothing before this module ever re-ran either command and compared its real
output to the words on the page.

This module deliberately executes ONLY the two commands above -- the
subset of ONBOARDING.md's documented commands that are genuinely safe to
run unattended and repeatedly: local, read-only, no network write, no
Arcade account action, no OAuth, nothing that forks a repository or
installs a toolchain. It never executes `gh repo fork` (forks a real repo),
the `curl ... | sh` installer (fetches and runs a remote script), `arcade
login`/`arcade deploy`/`arcade connect` (real external account actions --
the one thing this whole codebase's Oath exists to forbid, verified by
actually doing it would be the opposite of the Oath), or `uv run python -m
seam_engine.server stdio` (a long-running server, not a one-shot command
with output to check). Those stay doctrine the reader must try for
themselves, exactly as `SCOPES.md`'s own "checked, not promised" line asks
of the gods, not of the mortal reading the guide.

Local subprocess only (`uv run` against this repo's own already-synced
environment, the identical boundary `recipe_command_check.py` already
holds) -- no repo file is written, no Arcade tool is called, no real
account is touched.

Usage:
    python3 tools/onboarding_doctrine_check.py check
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ONBOARDING_PATH = ROOT / "fencepost" / "ONBOARDING.md"
DEFAULT_SEAM_ENGINE_DIR = ROOT / "fencepost" / "seam_engine"

_DEFAULT_TIMEOUT_S = 90.0

# ONBOARDING.md's own minute-1 claim: "that should print something like
# `4584 passed`" -- the exact pytest summary-line shape (`-q`'s own
# terminal summary, e.g. "4584 passed in 35.06s").
_CLAIMED_TEST_COUNT_RE = re.compile(r"print something like `(\d+) passed`")

# The real pytest summary line's own passed-count, as `uv run python -m
# pytest -q` prints it (ignores any "N failed"/"N skipped" segment that
# might sit alongside "N passed" on the same line -- a healthy run never
# carries one, and a sick one is caught by `command_failed` below via a
# non-zero exit code before this regex ever runs).
_REAL_TEST_COUNT_RE = re.compile(r"(\d+) passed")

# ONBOARDING.md's own minute-4 claim: the badge prints "N/N tools
# read-only" -- a generic shape (the actual N is never named in the
# prose, unlike the pytest count), so this only checks the SHAPE appears
# in the live command's own stdout, not a specific number.
_CLAIMED_BADGE_SHAPE_RE = re.compile(r'`"N/N tools read-only"`')
_REAL_BADGE_SHAPE_RE = re.compile(r"\d+/\d+ tools read-only")


_DEFAULT_PYTEST_COMMAND = ["uv", "run", "python", "-m", "pytest", "-q"]
_DEFAULT_BADGE_COMMAND = ["uv", "run", "python", "-m", "seam_engine.badge"]


_RESULTS_CACHE: dict[tuple[str, str, float, tuple[str, ...], tuple[str, ...]], dict[str, object]] = {}


def clear_cache() -> None:
    """Drop every memoized `check_onboarding_doctrine()` result. Only
    real callers are tests that want to force a genuinely fresh live
    run; production's one-call-per-process shape never needs this."""
    _RESULTS_CACHE.clear()


def check_onboarding_doctrine(
    onboarding_path: Path | str = DEFAULT_ONBOARDING_PATH,
    seam_engine_dir: Path | str = DEFAULT_SEAM_ENGINE_DIR,
    timeout: float = _DEFAULT_TIMEOUT_S,
    pytest_command: list[str] | None = None,
    badge_command: list[str] | None = None,
) -> dict[str, object]:
    """Memoized per (onboarding_path, seam_engine_dir, timeout,
    pytest_command, badge_command) for the lifetime of the process --
    the identical fix `recipe_command_check.py` needed at task 588 and
    for the identical reason: `run_ritual_check()`'s own
    `check_onboarding_doctrine()` call has no way to skip this check, so
    every one of `tests/test_ritual_check.py`'s FoldCase methods that
    calls `run_ritual_check()` without an `onboarding_doctrine_*`
    override would otherwise trigger a fresh real `uv run python -m
    pytest -q` (plus a real badge rerun) on EVERY SUCH CALL -- work that
    cannot have changed between calls within one process, and expensive
    enough (a real ~30s cold pytest run, repeated dozens of times) that
    the root `tests/` suite hung for minutes before this cache existed
    (caught live this same hour, the same "FoldCase tests that never
    touch this check pay its full live cost anyway" shape task 588's own
    docstring already names for recipes). A real hourly `ritual_check.py`
    run is a fresh process that calls this exactly once, so the cache is
    inert there -- production still runs both commands fresh every
    single hour."""
    key = (
        str(Path(onboarding_path).resolve()),
        str(Path(seam_engine_dir).resolve()),
        timeout,
        tuple(pytest_command) if pytest_command is not None else tuple(_DEFAULT_PYTEST_COMMAND),
        tuple(badge_command) if badge_command is not None else tuple(_DEFAULT_BADGE_COMMAND),
    )
    if key not in _RESULTS_CACHE:
        _RESULTS_CACHE[key] = _check_onboarding_doctrine_uncached(
            onboarding_path, seam_engine_dir, timeout, pytest_command, badge_command
        )
    return dict(_RESULTS_CACHE[key])


def _check_onboarding_doctrine_uncached(
    onboarding_path: Path | str = DEFAULT_ONBOARDING_PATH,
    seam_engine_dir: Path | str = DEFAULT_SEAM_ENGINE_DIR,
    timeout: float = _DEFAULT_TIMEOUT_S,
    pytest_command: list[str] | None = None,
    badge_command: list[str] | None = None,
) -> dict[str, object]:
    """Live-execute ONBOARDING.md's two safe, falsifiable command claims
    and return `clean: True` only when both commands run and their real
    output matches what the page promises. Never a bare pass/fail --
    every problem names the exact claim and the exact mismatch.

    `onboarding_path`/`seam_engine_dir` are parameters (not hardcoded
    paths), the same testability `check_recipe_commands` already holds,
    so tests can point this at a fixture page without touching the real
    ONBOARDING.md. `pytest_command`/`badge_command` default to the real,
    literal commands ONBOARDING.md itself documents (`uv run python -m
    pytest -q` / `uv run python -m seam_engine.badge`) -- production
    never overrides them. Tests override them with a cheap `python3 -c
    "print(...)"` stand-in so the fixture suite can exercise every
    mismatch/failure shape without needing `uv` installed or paying a
    real ~35s pytest run per case, the same spirit (not the same
    mechanism, since this check's two commands are fixed strings rather
    than a per-recipe documented one) as `check_recipe_commands`'s own
    `_write_recipe`/`_write_recipe_with_command` fixture doors.
    """
    if pytest_command is None:
        pytest_command = _DEFAULT_PYTEST_COMMAND
    if badge_command is None:
        badge_command = _DEFAULT_BADGE_COMMAND
    onboarding_path = Path(onboarding_path)
    seam_engine_dir = Path(seam_engine_dir)

    if not onboarding_path.is_file():
        return {
            "clean": False,
            "status": "missing_file",
            "problems": [f"no such file: {onboarding_path}"],
        }

    text = onboarding_path.read_text(encoding="utf-8")

    problems: list[dict[str, str]] = []

    # -- claim 1: the pytest count ----------------------------------
    claimed_match = _CLAIMED_TEST_COUNT_RE.search(text)
    if claimed_match is None:
        problems.append({
            "claim": "pytest_count",
            "reason": "ONBOARDING.md no longer makes a '...print something "
            "like `N passed`' claim at all -- this check has nothing to "
            "verify against (page rewritten without updating this check, "
            "or the claim's own wording drifted past this regex)",
        })
        claimed_count = None
    else:
        claimed_count = int(claimed_match.group(1))

    try:
        proc = subprocess.run(
            pytest_command,
            cwd=seam_engine_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        problems.append({
            "claim": "pytest_count",
            "reason": f"command did not complete: {exc}",
        })
        real_count = None
    else:
        if proc.returncode != 0:
            problems.append({
                "claim": "pytest_count",
                "reason": f"'uv run python -m pytest -q' exited "
                f"{proc.returncode}: {proc.stdout.strip()[-2000:]}",
            })
            real_count = None
        else:
            real_match = _REAL_TEST_COUNT_RE.search(proc.stdout)
            if real_match is None:
                problems.append({
                    "claim": "pytest_count",
                    "reason": "command succeeded but its own output never "
                    f"names an 'N passed' count: {proc.stdout.strip()[-500:]}",
                })
                real_count = None
            else:
                real_count = int(real_match.group(1))

    if claimed_count is not None and real_count is not None and claimed_count != real_count:
        problems.append({
            "claim": "pytest_count",
            "reason": f"ONBOARDING.md claims '{claimed_count} passed', the "
            f"live suite actually reports '{real_count} passed' -- stale "
            "doc, edit ONBOARDING.md's own minute-1 line to match",
        })

    # -- claim 2: the badge's read-only shape ------------------------
    if _CLAIMED_BADGE_SHAPE_RE.search(text) is None:
        problems.append({
            "claim": "badge_shape",
            "reason": "ONBOARDING.md no longer makes a '...prints "
            '"N/N tools read-only"\' claim at all -- this check has '
            "nothing to verify against",
        })
    else:
        try:
            badge_proc = subprocess.run(
                badge_command,
                cwd=seam_engine_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            problems.append({
                "claim": "badge_shape",
                "reason": f"command did not complete: {exc}",
            })
        else:
            if badge_proc.returncode != 0:
                problems.append({
                    "claim": "badge_shape",
                    "reason": f"'uv run python -m seam_engine.badge' exited "
                    f"{badge_proc.returncode}: {badge_proc.stdout.strip()[-2000:]}",
                })
            elif _REAL_BADGE_SHAPE_RE.search(badge_proc.stdout) is None:
                problems.append({
                    "claim": "badge_shape",
                    "reason": "command succeeded but its own output never "
                    "matches the 'N/N tools read-only' shape ONBOARDING.md "
                    f"promises: {badge_proc.stdout.strip()[-500:]}",
                })

    return {
        "clean": not problems,
        "status": "checked",
        "claimed_test_count": claimed_count,
        "real_test_count": real_count,
        "problems": problems,
    }


def format_result(result: dict[str, object]) -> str:
    problems = cast("list[dict[str, str]]", result.get("problems", []))
    if result.get("status") == "missing_file":
        return "onboarding doctrine: BROKEN -- " + "; ".join(p["reason"] for p in problems)
    if result["clean"]:
        return (
            f"onboarding doctrine: clean (ONBOARDING.md's minute-1 pytest "
            f"claim -- '{result['claimed_test_count']} passed' -- and "
            f"minute-4 badge claim both matched a live rerun)"
        )
    names = "; ".join(f"{p['claim']} ({p['reason']})" for p in problems)
    return "onboarding doctrine: BROKEN -- " + names


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_onboarding_doctrine()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
