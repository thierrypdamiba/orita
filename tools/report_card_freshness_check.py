#!/usr/bin/env python3
"""Task 1369. Kwaku-Ananse's own share card, checked against what it says
of itself -- the identical "claims a mirror, never checked against it"
shape `badge_freshness_check.py` (task 425/574) and `draftback_freshness_check.py`
(task 1367) already closed, found a third time in this same remit's own tool.

`tools/report_card.py` (task 1355) builds `docs/fencepost/reports/<date>.html`,
a per-day share card carrying that day's real headline in its `<meta>` tags
-- `docs/fencepost/index.html`'s own client-side script links to it as
"share today's report", reading the date off the live report's own title
line. But `seam-scan.yml`'s daily cron reseals the Ledger, rewrites the
Report, reruns the audit, and repaints the badge every single day -- and,
until this same task wired it in, never once called `report_card.py`. The
card for the founding day of the tool (2026-09-08) sat alone in
`docs/fencepost/reports/` for a full day while the Report moved on to
2026-09-09: the site's own "share today's report" link pointed at a page
that had never been built, a live 404 on the town's own site every single
day the tool existed. Confirmed live before writing this: `report_card.py
latest` against today's real sealed report produced a file that did not
yet exist on disk.

This checker compares the latest sealed `fencepost/REPORTS/<date>.md`
against `docs/fencepost/reports/<date>.html` for that SAME date: missing
entirely (nobody has run the CLI since the report sealed) or present but
built from stale bytes (a fresh `build_report_card` re-render disagrees
with what's committed) both count as stale. Never edits or regenerates
anything itself -- a real drift found here is the god-on-duty's own hour
to fix (`python3 tools/report_card.py latest`, commit the fresh file), not
something this check silently repairs, the same restraint
`draftback_freshness_check.py` already holds.

Usage:
    python3 tools/report_card_freshness_check.py check
"""
from __future__ import annotations

import os
import sys
from typing import Any, cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REPORTS_DIR = os.path.join(ROOT, "fencepost", "REPORTS")
DEFAULT_CARDS_DIR = os.path.join(ROOT, "docs", "fencepost", "reports")
_DATE_LEN = len("YYYY-MM-DD")

# Sentinel distinguishing "caller passed no live state, compute it fresh"
# from "caller explicitly passed a live state of None, meaning
# unavailable" -- the same seam `draftback_freshness_check.py`'s own
# `_COMPUTE_FRESH` already holds.
_COMPUTE_FRESH = object()


def _report_card_module() -> Any:
    """Import the real `tools/report_card.py` module directly by path --
    it lives beside this file, not under `fencepost/seam_engine/src`, so
    this uses `ritual_check.py`'s own `_load_once`-by-path convention
    rather than a package import."""
    import importlib.util

    path = os.path.join(ROOT, "tools", "report_card.py")
    spec = importlib.util.spec_from_file_location("_report_card_freshness_report_card", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load report_card module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _latest_sealed_date(reports_dir: str) -> str | None:
    try:
        names = os.listdir(reports_dir)
    except OSError:
        return None
    dates = sorted(f[: -len(".md")] for f in names if f.endswith(".md") and len(f) == _DATE_LEN + len(".md"))
    return dates[-1] if dates else None


def live_card_state(reports_dir: str = DEFAULT_REPORTS_DIR) -> dict[str, str] | None:
    """Recompute the latest sealed date's card fresh, off the CURRENT
    report text -- the identical rendering `python3 tools/report_card.py
    latest` would produce right now. Returns `None` if no report has ever
    been sealed, or on any import/parse failure -- never lets an
    environment or startup-order gap crash the caller."""
    date = _latest_sealed_date(reports_dir)
    if date is None:
        return None
    report_path = os.path.join(reports_dir, f"{date}.md")
    try:
        with open(report_path, encoding="utf-8") as f:
            report_text = f.read()
        mod = _report_card_module()
        page, _url = mod.build_report_card(date, report_text)
    except Exception:  # noqa: BLE001 -- "can't verify" must never mean "verified broken"
        return None
    return {"date": date, "page": page}


def check_report_card_freshness(
    reports_dir: str = DEFAULT_REPORTS_DIR,
    cards_dir: str = DEFAULT_CARDS_DIR,
    live: object = _COMPUTE_FRESH,
) -> dict[str, object]:
    """Compares the latest sealed report's date against
    `docs/fencepost/reports/<date>.html` for that same date. `live`
    defaults to computing it now via `live_card_state()`; pass an explicit
    `{"date", "page"} | None` to control the comparison directly -- the
    same dependency-injection seam `draftback_freshness_check.py`'s own
    `check_draftback_freshness` holds."""
    live_state: dict[str, str] | None
    if live is _COMPUTE_FRESH:
        live_state = live_card_state(reports_dir)
    else:
        live_state = cast("dict[str, str] | None", live)

    if live_state is None:
        return {"clean": True, "status": "unavailable"}

    committed_path = os.path.join(cards_dir, f"{live_state['date']}.html")
    if not os.path.exists(committed_path):
        return {
            "clean": False,
            "status": "STALE",
            "reason": f"missing -- no {os.path.basename(committed_path)} for the latest sealed report's own date",
            "expected_date": live_state["date"],
        }
    with open(committed_path, encoding="utf-8") as f:
        committed_text = f.read()
    agree = committed_text == live_state["page"]
    result: dict[str, object] = {
        "clean": agree,
        "status": "current" if agree else "STALE",
        "path": committed_path,
        "date": live_state["date"],
    }
    if not agree:
        result["reason"] = "byte mismatch -- dated correctly but the rendered content has drifted"
    return result


def format_report_card_freshness(result: dict[str, object]) -> str:
    if result["status"] == "unavailable":
        return "report card freshness: clean (unavailable -- no sealed report yet)"
    if result["clean"]:
        return f"report card freshness: clean (date={result['date']})"
    return (
        f"report card freshness: STALE -- {result['reason']} -- "
        "Kwaku-Ananse's own share card is misreporting the site, escalate now"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(2)
    outcome = check_report_card_freshness()
    print(format_report_card_freshness(outcome))
    sys.exit(0 if outcome["clean"] else 1)
