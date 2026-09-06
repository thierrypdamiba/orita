#!/usr/bin/env python3
"""Task 1294. Off-By-One counts the count that ranks everything else.

`fencepost/seam_engine/src/seam_engine/ranking.py` casts Ogun's law into
one pure function: `rank()` sorts candidates by confidence, elects at most
one PRIMARY (must clear `CONFIDENCE_BAR` AND lead the runner-up by
`SEPARATION_MARGIN`), and labels everything else CONTENDER or COINCIDENCE.
Every sealed `fencepost/candidates/<date>.json` snapshot (54 of them, one
per scan since founding) is exactly that function's own output, written to
disk the day it ran and never touched again -- the Ledger's own append-
only law extended to a second, until-now-unwatched tree.

No check anywhere in `tools/` had ever read the `candidates/` directory or
imported `ranking.py` at all (confirmed live this hour: a grep for both
names across every `tools/*.py` file came back empty before this module
existed). That is a real doctrine gap for off-by-one's own remit -- Seam
Engine, "the scan that reads across connected accounts and surfaces
exactly one high-confidence gap, plus the ranked candidate list beneath
it" (STRATEGY.md) -- because nothing stood between a future edit to
`ranking.py`'s constants or election logic and every sealed snapshot
silently reading back as if a DIFFERENT law had produced it. A change to
`CONFIDENCE_BAR`/`SEPARATION_MARGIN`, or a bug in the tie-break/lead-
rounding logic `margin_law.py`'s own docstring already worries about,
would not touch the JSON on disk -- only the label future code reruns
would recompute -- and nothing would ever notice the two had drifted
apart.

This module closes that gap the same way `verdict_provenance_check.py`
(task 102) and `report_regression_check.py` (task 773) closed their own:
read-only, no network, no rewrite of sealed history. For every sealed
`fencepost/candidates/*.json` file (skipping `github-events-cache.json`,
which is the cache `github_events_cache.py` owns, not a scan result),
this rebuilds the exact `GapCandidate` list the file's own `primary_gap` +
`tail` entries describe, REPLAYS `ranking.rank()` against them using that
same file's own recorded `confidence_bar`/`separation_margin`, and
compares the replayed `(label, rank, lead)` for every slug against what
the sealed file actually recorded. A mismatch means the law and the
sealed history it produced have drifted apart -- a live bug, a hand edit,
or a silent constant change -- and is reported, never silently repaired.

Live run this hour replayed all 54 sealed snapshots: zero mismatches.
Genuinely clean, not a fabricated finding (Ogun's law cuts both ways --
this hour's own-remit sweep doesn't invent a crack to justify itself).

Usage:
    python3 tools/ranking_replay_check.py check
"""
from __future__ import annotations

import glob
import json
import os
import sys
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CANDIDATES_DIR = os.path.join(ROOT, "fencepost", "candidates")
_SEAM_ENGINE_SRC = os.path.join(ROOT, "fencepost", "seam_engine", "src")
if _SEAM_ENGINE_SRC not in sys.path:
    sys.path.insert(0, _SEAM_ENGINE_SRC)

from seam_engine import ranking  # noqa: E402
from seam_engine.scan import GapCandidate  # noqa: E402

_SKIP_FILES = frozenset({"github-events-cache.json"})


def _iter_candidate_files(candidates_dir: str) -> list[str]:
    return sorted(
        p
        for p in glob.glob(os.path.join(candidates_dir, "*.json"))
        if os.path.basename(p) not in _SKIP_FILES
    )


def _replay_one(path: str) -> list[dict[str, object]]:
    """Replay `ranking.rank()` against one sealed snapshot's own recorded
    candidates and confidence law, returning every slug whose replayed
    (label, rank, lead) disagrees with what the file recorded. Trusts the
    file's own `confidence_bar`/`separation_margin` over the module's
    current defaults -- a snapshot sealed under a since-changed constant
    should replay under the LAW IT WAS SEALED UNDER, exactly like
    `report_accuracy_check.py` never re-scores an old tablet against
    today's rules."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    recorded: list[dict[str, Any]] = []
    primary = data.get("primary_gap")
    if primary is not None:
        recorded.append(primary)
    recorded.extend(data.get("tail", []))

    candidates = [
        GapCandidate(
            slug=c["slug"],
            headline=c["headline"],
            detail=c["detail"],
            confidence=c["confidence"],
            evidence=list(c.get("evidence", [])),
        )
        for c in recorded
    ]
    bar = data.get("confidence_bar", ranking.CONFIDENCE_BAR)
    margin = data.get("separation_margin", ranking.SEPARATION_MARGIN)
    replayed = ranking.rank(candidates, bar=bar, margin=margin)
    replayed_by_slug = {g.slug: (g.label, g.rank, g.lead) for g in replayed.ranked}

    mismatches: list[dict[str, object]] = []
    for c in recorded:
        want = (c["label"], c["rank"], c["lead"])
        got = replayed_by_slug.get(c["slug"])
        if got != want:
            mismatches.append({
                "file": path,
                "slug": c["slug"],
                "recorded": {"label": want[0], "rank": want[1], "lead": want[2]},
                "replayed": (
                    {"label": got[0], "rank": got[1], "lead": got[2]} if got is not None else None
                ),
            })
    return mismatches


def find_mismatches(candidates_dir: str = DEFAULT_CANDIDATES_DIR) -> list[dict[str, object]]:
    """Task 1294: replay `ranking.rank()` against every sealed
    `fencepost/candidates/*.json` snapshot, returning every mismatch
    found. Empty when the ranking law and every sealed snapshot still
    agree exactly."""
    mismatches: list[dict[str, object]] = []
    for path in _iter_candidate_files(candidates_dir):
        mismatches.extend(_replay_one(path))
    return mismatches


def format_mismatches(mismatches: list[dict[str, object]], count: int | None = None) -> str:
    if not mismatches:
        suffix = f" ({count} snapshot(s) replayed)" if count is not None else ""
        return f"ranking replay check: clean -- every sealed candidate snapshot replays identically{suffix}"
    lines = [f"ranking replay check: {len(mismatches)} MISMATCH(ES) FOUND -- the ranking law has drifted from sealed history"]
    for m in mismatches:
        lines.append(f"  {m['file']} [{m['slug']}]: recorded={m['recorded']!r} replayed={m['replayed']!r}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    files = _iter_candidate_files(DEFAULT_CANDIDATES_DIR)
    result = find_mismatches()
    print(format_mismatches(result, count=len(files)))
    sys.exit(1 if result else 0)
