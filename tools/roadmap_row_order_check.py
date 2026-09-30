#!/usr/bin/env python3
"""Task 1854. Esu-Elegba opens the door that was left ajar.

`daytime_rotation_check.py`'s `whose_turn_daytime()` (task 1625) answers
"whose turn is it" by taking `rows[-1]` -- the LAST daytime-owner row in
`ROADMAP.md`'s own table, in FILE order -- and asking `next_in_cycle` of
its owner. That is only correct if the live table's rows are always
appended in ascending task-number order, so that file-last and
number-last are the same row. Nothing has ever checked that they are.

Task 1853's own row broke the assumption for the first time: it was
inserted directly under the header (`| 1853 | ... |` as the FIRST body
row) instead of appended after `| 1852 | ... |` at the bottom, where
every row from 1768 through 1852 had landed. `whose_turn_daytime()` never
noticed -- it just read `rows[-1]` as `1852`/kothar-wa-khasis and named
kwaku-ananse next, one full turn behind the real answer (esu-elegba, the
correct successor to 1853's own kwaku-ananse). Task 1853's own commit
prose caught the drift by hand ("forward to esu-elegba next") but the
tool itself, asked live this hour, still answered kwaku-ananse -- a
human-legible hand-off note is not a check. This hour's own task 1854 row
carries the fix: 1853 moved back into its correct ascending position, and
this module so a future misplaced row is caught the moment it is checked
rather than trusted from prose.

Deliberately narrow, matching `wip_reclaim_check.py`'s own shape: read
only the LIVE `ROADMAP.md` table (not the archives -- an archived file is
sealed history, already the ascending record of its own day, and
`window_rotation_check._roadmap_and_archive_text`'s reconstruction always
appends the live file last regardless of internal archive order, so only
the live file's own internal row order can ever silently break
`rows[-1]`). A row's task number must be strictly greater than the row
immediately before it in file order; anything else is a live violation.

Usage:
    python3 tools/roadmap_row_order_check.py check
"""
from __future__ import annotations

import os
import sys
from typing import cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wip_reclaim_check  # noqa: E402

DEFAULT_ROADMAP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ROADMAP.md")


def find_order_violations(text: str | None = None, roadmap_path: str = DEFAULT_ROADMAP_PATH) -> dict[str, object]:
    """Every adjacent pair of rows in the LIVE table (file order) checked
    for a strictly increasing task number. A row whose number is not
    greater than the row before it -- inserted out of place, like task
    1853's was -- is a violation: it means `rows[-1]` no longer names the
    real most-recent row, and every consumer that trusts file-order-as-
    chronological-order (`daytime_rotation_check.whose_turn_daytime`
    chief among them) can silently answer a stale turn."""
    if text is None:
        with open(roadmap_path, encoding="utf-8") as f:
            text = f.read()
    rows = wip_reclaim_check.parse_table_rows(text)
    violations: list[dict[str, object]] = []
    for prev, cur in zip(rows, rows[1:]):
        prev_n = cast(int, prev["number"])
        cur_n = cast(int, cur["number"])
        if cur_n <= prev_n:
            violations.append({"number": cur_n, "after": prev_n, "owner": cur["owner"]})
    return {"clean": not violations, "violations": violations, "row_count": len(rows)}


def format_result(result: dict[str, object]) -> str:
    if result["clean"]:
        return f"roadmap row order check: clean ({result['row_count']} live row(s), strictly ascending)"
    violations = cast("list[dict[str, object]]", result["violations"])
    lines = [f"roadmap row order check: BROKEN -- {len(violations)} out-of-order row(s)"]
    for v in violations:
        lines.append(
            f"  task {v['number']} ({v['owner']}) appears after task {v['after']} in file order -- "
            "not ascending, rows[-1]-based lookups (daytime_rotation_check.whose_turn_daytime) will "
            "answer a stale turn"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_order_violations()
    print(format_result(result))
    sys.exit(0 if result["clean"] else 1)
