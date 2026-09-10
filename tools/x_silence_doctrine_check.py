#!/usr/bin/env python3
"""Task 1373. The town's own silence, never once explained where a stranger
would actually see it.

@oritatown has not posted in roughly two months (`x_outage_tracker.py`'s
own escalated streaks name the real API wall underneath), but even setting
the outage aside, STRATEGY.md/TOWN-OPERATIONS.md's change-gate policy
means the account was ALWAYS going to look quiet most hours by design --
"@oritatown speaks only when there is something new to say" (`STRATEGY.md`,
Growth notes). That sentence lives in a strategy document nobody visiting
the actual site or the fencepost README would ever open. A stranger who
finds Fencepost through the repo, reads the README's own "Watch it live"
pitch about a town that reports every day, then checks @oritatown and
finds weeks of silence has exactly the evidence needed to conclude the
project died -- the opposite of what the daily-Report story is trying to
build (Nyx's own dissent, STRATEGY.md: "the n-1 gag is charming until
cynics decide the counter never moving is a stunt"; the same worry, one
door over, about the feed instead of the counter).

Fixed the instance: added one identical sentence to both `fencepost/README.md`
(the developer-facing doc) and `docs/fencepost/index.html` (the live site a
stranger actually lands on), naming the change-gate as policy, not decay.
This module closes the recurrence, the same "claims a mirror, nothing
checks it" shape this codebase already guards a dozen other ways
(`consent_template_scope_check.py`, `scopes_md_consent_sync_check.py`,
`fork_gate_check.py`): confirms the identical marker sentence is still
present, byte-for-byte, in both places, so an edit to one copy that
forgets its twin is caught rather than silently drifting the way
`duplicate_regex_check.py`'s own docstring already names this general
class of bug doing five separate times elsewhere in this codebase.

Deliberately NOT wired into `ritual_check.py` this hour -- same call
`task_reference_check.py` (task 1372) already made and named plainly: five
separate insertion points across a 3000+-line, heavily cross-tested module
is a real, out-of-scope follow-on for a one-sentence doc-drift guard, not
worth rushing in the same hour it was built.

Usage:
    python3 tools/x_silence_doctrine_check.py check
"""
from __future__ import annotations

import os
import sys
from typing import cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

README_PATH = os.path.join(ROOT, "fencepost", "README.md")
SITE_PATH = os.path.join(ROOT, "docs", "fencepost", "index.html")

# The shared claim, byte-identical in both files on purpose -- this is the
# thing being guarded against drift, not merely a keyword to grep for.
MARKER_SENTENCE = (
    "goes quiet more hours than not, on purpose: it posts only when the "
    "surfaced gap changes or something new actually ships, never on a "
    "clock, never to prove the account is alive."
)


def check_x_silence_doctrine(
    readme_path: str = README_PATH, site_path: str = SITE_PATH
) -> dict[str, object]:
    """Confirm `MARKER_SENTENCE` appears, byte-identical, in both the
    README and the live site. A missing file is reported as missing, not
    silently skipped -- unlike a citation scan, both of these files are
    presumed to always exist, so their absence is itself the finding.
    """
    missing: list[str] = []
    absent: list[str] = []
    for label, path in (("fencepost/README.md", readme_path), ("docs/fencepost/index.html", site_path)):
        if not os.path.isfile(path):
            missing.append(label)
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if MARKER_SENTENCE not in text:
            absent.append(label)
    clean = not missing and not absent
    return {"clean": clean, "missing": missing, "absent": absent}


def format_x_silence_doctrine(result: dict[str, object]) -> str:
    if result["clean"]:
        return "x silence doctrine: clean (the change-gate explanation holds, byte-identical, in both the README and the live site)"
    missing = cast("list[str]", result["missing"])
    absent = cast("list[str]", result["absent"])
    parts = []
    if missing:
        parts.append(f"missing file(s): {', '.join(missing)}")
    if absent:
        parts.append(f"marker sentence absent from: {', '.join(absent)}")
    return "x silence doctrine: DRIFTED -- " + "; ".join(parts)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(2)
    outcome = check_x_silence_doctrine()
    print(format_x_silence_doctrine(outcome))
    sys.exit(0 if outcome["clean"] else 1)
