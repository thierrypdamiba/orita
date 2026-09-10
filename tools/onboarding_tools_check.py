#!/usr/bin/env python3
"""Task 1374. `fencepost/ONBOARDING.md`'s "minute 3" section (zashiki-warashi's
own house) named the server's tool catalog by hand: "four tools come up:
`list_repo_commits`, `get_latest_release`, `get_recent_x_posts`,
`seam_scan`". `server.py` has grown two more `@app.tool(metadata=READ_ONLY)`
functions since (`gmail_calendar_scan`, task 16/653's v0.2 fixture detector;
`combined_scan_preview`, ROADMAP.md #113) with nothing re-checking the
onboarding page's hand-written roll call against the real server -- the
exact "claims a mirror, nothing checks it" shape `draftback_freshness_check.py`
(task 1367), `report_card_freshness_check.py` (task 1369), and
`task_reference_check.py` (task 1372) already closed for a rendered value or
a citation number, here showing up instead as a hand-typed tool-name list.
A reader running `uv run python -m seam_engine.server stdio` after reading
the doc would watch six tools come up where the sentence promised four, and
wonder what the other two were doing there unannounced.

Fixed the instance (`ONBOARDING.md` now names all six, count corrected).
This module closes the recurrence: it parses `server.py`'s own source for
every `@app.tool(metadata=READ_ONLY)`-decorated `def name(` (the same
snake_case identifiers a reader sees in the file, not `badge.py`'s
PascalCase `ToolAudit.name` registry form) and confirms `ONBOARDING.md`'s
"minute 3" paragraph names that exact set, in order, with a matching count
word. Never edits anything; a real drift is a god-on-duty escalation
(rewrite the sentence to match the live tool list), not something this
check silently repairs.

Usage:
    python3 tools/onboarding_tools_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from typing import cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERVER_PATH = os.path.join(
    ROOT, "fencepost", "seam_engine", "src", "seam_engine", "server.py"
)
ONBOARDING_PATH = os.path.join(ROOT, "fencepost", "ONBOARDING.md")

# `@app.tool(metadata=READ_ONLY)` immediately followed (allowing the
# `# type: ignore[...]` comment this file always carries on that line, and
# any blank lines) by `def name(` -- matches every real tool definition in
# server.py without needing a full AST parse.
_TOOL_DEF_RE = re.compile(
    r"@app\.tool\(metadata=READ_ONLY\)[^\n]*\n(?:\s*\n)*def\s+(\w+)\s*\("
)

_NUMBER_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
}

# "six tools come up:" (or any count word) followed by a run of
# backtick-quoted names up to the em-dash that starts the next clause.
_ONBOARDING_LIST_RE = re.compile(
    r"(\w+) tools come up:\s*((?:`\w+`,?\s*)+)—", re.MULTILINE
)


def live_server_tools(server_path: str = SERVER_PATH) -> list[str]:
    """Every `@app.tool(metadata=READ_ONLY)`-decorated function name in
    `server.py`, in source order. Empty list (not a crash) if the file is
    missing -- the same "can't find it here must never mean broken"
    discipline this town's other freshness checks already hold."""
    if not os.path.isfile(server_path):
        return []
    with open(server_path, encoding="utf-8") as f:
        text = f.read()
    return _TOOL_DEF_RE.findall(text)


def onboarding_claimed_tools(onboarding_path: str = ONBOARDING_PATH) -> dict[str, object]:
    """Parse ONBOARDING.md's "minute 3" roll call. Returns
    {"found": bool, "count_word": str|None, "names": [...]}. `found=False`
    (not an error) if the paragraph's shape isn't there at all -- a
    checker that can't locate its own target names that plainly instead of
    guessing."""
    if not os.path.isfile(onboarding_path):
        return {"found": False, "count_word": None, "names": []}
    with open(onboarding_path, encoding="utf-8") as f:
        text = f.read()
    m = _ONBOARDING_LIST_RE.search(text)
    if not m:
        return {"found": False, "count_word": None, "names": []}
    count_word = m.group(1)
    names = re.findall(r"`(\w+)`", m.group(2))
    return {"found": True, "count_word": count_word, "names": names}


def check_onboarding_tools(
    server_path: str | None = None, onboarding_path: str | None = None
) -> dict[str, object]:
    """Confirm ONBOARDING.md's minute-3 tool roll call matches the live
    server's real tool catalog: same names, same order, and a count word
    that agrees with the real count.

    Returns {"clean": bool, "live_tools": [...], "claimed": {...},
    "problems": [...]}.
    """
    server = server_path or SERVER_PATH
    onboarding = onboarding_path or ONBOARDING_PATH
    live = live_server_tools(server)
    claimed = onboarding_claimed_tools(onboarding)

    problems: list[str] = []
    if not claimed["found"]:
        problems.append("ONBOARDING.md's minute-3 tool roll call was not found")
    else:
        names = cast(list[str], claimed["names"])
        if names != live:
            missing = [n for n in live if n not in names]
            extra = [n for n in names if n not in live]
            detail_bits = []
            if missing:
                detail_bits.append(f"missing {missing}")
            if extra:
                detail_bits.append(f"stale {extra}")
            if not detail_bits:
                detail_bits.append(f"order differs: claims {names}, real order {live}")
            problems.append("tool list mismatch -- " + "; ".join(detail_bits))
        expected_word = _NUMBER_WORDS.get(len(live), str(len(live)))
        if claimed["count_word"] != expected_word:
            problems.append(
                f"count word {claimed['count_word']!r} does not match the real "
                f"tool count ({len(live)}, {expected_word!r})"
            )

    return {
        "clean": not problems,
        "live_tools": live,
        "claimed": claimed,
        "problems": problems,
    }


def format_onboarding_tools(result: dict[str, object]) -> str:
    if result["clean"]:
        n = len(result["live_tools"])  # type: ignore[arg-type]
        return f"onboarding tools: clean ({n} live server tool(s), ONBOARDING.md's minute-3 roll call matches exactly)"
    detail = "; ".join(result["problems"])  # type: ignore[arg-type]
    return f"onboarding tools: STALE -- {detail}"


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(2)
    outcome = check_onboarding_tools()
    print(format_onboarding_tools(outcome))
    sys.exit(0 if outcome["clean"] else 1)
