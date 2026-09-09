#!/usr/bin/env python3
"""Task 1367. Nisaba's own draft-back, checked against what it says of itself.

`fencepost/DRAFTS/README.md` makes a present-tense promise: running
`python -m seam_engine.draftback {email|notion} --write` "writes the
**exact bytes** a live draft would carry into `DRAFTS/YYYY-MM-DD-<channel>.md`
... This lets anyone read, byte for byte, what the draft-back will say
before a single live account is connected." Two files sat in that
directory, `DRAFTS/2026-07-12-email.md` and `DRAFTS/2026-07-12-notion.md`
-- rendered once, by hand, on the day the module shipped (ROADMAP.md #17),
and never regenerated since. `seam-scan.yml`'s daily cron reseals the
Ledger, rewrites the Report, reruns the audit, and repaints the badge
every single day -- but never once calls `draftback.py`. Confirmed live
before writing this: a fresh `render_preview` off today's real ledger tip
(2026-09-09, 336 milestone commits, 177 fenceposts named) produces
materially different bytes than the committed 2026-07-12 file it sits
next to -- five unlabeled raw evidence URLs and no `TEASER_LINE`/
`CONNECT_YOUR_OWN` block, the exact pre-task-1360 Notion shape, because
this preview predates that fix by 59 days. Anyone who followed the
README's own instruction and actually read that file byte for byte was
reading a lie about what the draft-back says today -- the identical
"claims a mirror, never checked against it" shape `badge_freshness_check.py`
(task 425/574) already closed for `fencepost/BADGE.json`, just never
turned on this module's own committed previews.

This checker compares the newest `DRAFTS/<date>-<channel>.md` file for
each channel against a fresh `seam_engine.draftback.render_preview()` call
off the CURRENT ledger tip. Two distinct ways to be stale, both caught:
the committed file's own date doesn't match the live tip's date (nobody
ran the CLI since the ledger moved on), or the dates agree but the bytes
differ (the renderer's own output shape changed underneath an
already-current file -- exactly what task 1360's Notion-parity fix would
have caused had anyone re-run `--write` that same hour). An empty ledger
(no tip to render against) or a missing `fencepost/seam_engine/src` import
degrades to `status: "unavailable"`, clean -- the same "can't verify here
must never mean verified broken" discipline `badge_freshness_check.py`'s
own `live_badge_state()` already holds, applied to a module with no
external dependency of its own to make unavailable in the first place.

Never edits or regenerates anything itself -- a real drift found here is
the god-on-duty's own hour to fix (re-run the CLI, commit the fresh
bytes), not something this check silently repairs.

Usage:
    python3 tools/draftback_freshness_check.py check
"""
from __future__ import annotations

import os
import sys
from typing import Any, cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DRAFTS_DIR = os.path.join(ROOT, "fencepost", "DRAFTS")
CHANNELS = ("email", "notion")

# Sentinel distinguishing "caller passed no live state, compute it fresh"
# from "caller explicitly passed a channel's live state as None, meaning
# unavailable" -- the same seam `badge_freshness_check.py`'s `_COMPUTE_FRESH`
# already holds for its own live-vs-committed comparison.
_COMPUTE_FRESH = object()


def _seam_modules() -> tuple[Any, Any]:
    """Import the real `seam_engine.ledger`/`seam_engine.draftback` modules,
    the same `sys.path` convention `tools/ritual_check.py`'s own
    `_seam_ledger()` already uses to reach into the engine's `src/` layout
    from outside it. Both are pure-Python, internal-only modules (no
    `arcade-mcp-server`, unlike `badge.py`) -- a bare in-process import is
    always sufficient, no `uv` subprocess fallback needed."""
    src = os.path.join(ROOT, "fencepost", "seam_engine", "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    import seam_engine.draftback as draftback  # noqa: PLC0415
    import seam_engine.ledger as ledger  # noqa: PLC0415

    return ledger, draftback


def live_preview_state(channel: str) -> dict[str, str] | None:
    """Recompute channel's preview fresh, off the CURRENT ledger tip --
    the identical rendering `python -m seam_engine.draftback <channel> --write`
    would produce right now. Returns `None` on an empty ledger or any
    import failure -- never lets an environment or startup-order gap crash
    the caller."""
    try:
        ledger, draftback = _seam_modules()
        records = ledger.read_records()
        if not records:
            return None
        sealed = ledger.tip_sealed(records)
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]
        preview = draftback.render_preview(sealed, channel)
    except Exception:  # noqa: BLE001 -- "can't verify" must never mean "verified broken"
        return None
    return {"date": date, "preview": preview}


def check_draftback_freshness(
    drafts_dir: str = DEFAULT_DRAFTS_DIR, live: object = _COMPUTE_FRESH
) -> dict[str, object]:
    """Compares each channel's newest committed `DRAFTS/<date>-<channel>.md`
    against a fresh live re-render of the current ledger tip. `live`
    defaults to computing both channels now via `live_preview_state()`;
    pass an explicit `{channel: {"date", "preview"} | None}` dict to
    control the comparison directly -- the same dependency-injection seam
    `badge_freshness_check.py`'s own `check_badge_freshness` holds."""
    live_states: dict[str, dict[str, str] | None]
    if live is _COMPUTE_FRESH:
        live_states = {ch: live_preview_state(ch) for ch in CHANNELS}
    else:
        live_states = cast("dict[str, dict[str, str] | None]", live)

    channels: dict[str, dict[str, object]] = {}
    for ch in CHANNELS:
        live_state = live_states.get(ch)
        if live_state is None:
            channels[ch] = {"status": "unavailable", "clean": True}
            continue
        committed_path = os.path.join(drafts_dir, f"{live_state['date']}-{ch}.md")
        if not os.path.exists(committed_path):
            channels[ch] = {
                "status": "STALE",
                "clean": False,
                "reason": f"missing -- no {os.path.basename(committed_path)} for the live ledger tip's own date",
                "expected_date": live_state["date"],
            }
            continue
        with open(committed_path, encoding="utf-8") as f:
            committed_text = f.read()
        agree = committed_text == live_state["preview"]
        channels[ch] = {
            "status": "current" if agree else "STALE",
            "clean": agree,
            "path": committed_path,
        }
        if not agree:
            channels[ch]["reason"] = "byte mismatch -- dated correctly but the rendered content has drifted"

    clean = all(cast(bool, c["clean"]) for c in channels.values())
    return {"clean": clean, "channels": channels}


def format_draftback_freshness(result: dict[str, object]) -> str:
    channels = cast("dict[str, dict[str, object]]", result["channels"])
    if result["clean"]:
        statuses = ", ".join(f"{ch}={c['status']}" for ch, c in channels.items())
        return f"draftback freshness: clean ({statuses})"
    broken = {ch: c for ch, c in channels.items() if not c["clean"]}
    detail = "; ".join(f"{ch}: {c['reason']}" for ch, c in broken.items())
    return f"draftback freshness: STALE -- {detail} -- Nisaba's own drafts are misreporting live, escalate now"


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(2)
    outcome = check_draftback_freshness()
    print(format_draftback_freshness(outcome))
    sys.exit(0 if outcome["clean"] else 1)
