#!/usr/bin/env python3
"""Task 2507. Ogun's own catch, hour 08 UTC.

Iron Rule #3 of `TOWN-OPERATIONS.md`'s cadence section names it plainly:
every commit lands as its owner god, via
`git -c user.name="<God>" -c user.email="<slug>@orita.gods"`. The WIP
marker is always scribed as Nisaba; the close commit is always scribed as
whichever god's hour it is. Both carry an `@orita.gods` author identity,
never the bare harness identity (`Claude <noreply@anthropic.com>`) the
session falls back to when no `-c` override is passed.

That discipline has held by habit for 2506 tasks, never by a running
check -- the same gap `vault_leak_check.py` (task 98) and
`child_work_check.py` closed for their own Iron Rules. It broke live,
quietly, this hour: task 2506's own close commit
(`edb2cd4619c62a04de01546c96fd25987d7e934f`) is authored
`Claude <noreply@anthropic.com>`, not `Retrya <retrya@orita.gods>`, even
though its own commit message opens "Mine (retrya)". The WIP marker one
commit earlier on the same task (`f937d598...`) still carries the correct
`Nisaba <nisaba@orita.gods>` author -- only the close slipped, the one
`git commit` invocation on the critical path most likely to be run
without the `-c` override copied in from the task's own opening line.

Nothing is rewritten here -- an already-pushed commit's author is never
amended (git-safety doctrine, and in any case the content of that hour's
work is genuine and undisputed, only its author field drifted). This
module is read-only, local-filesystem-only (mirrors `child_work_check.
file_exists_at_head`'s own boundary: one `git log` read, no network),
and exists so the NEXT drift is caught the hour it happens rather than
found by hand, hundreds of commits later, while reading a buildlog row.

Mirrors `window_rotation_check.py`'s own grandfathering shape exactly:
a drift commit authored before this check's own fix landed is sealed
history (`grandfathered`, never flips a caller's `broken`); one authored
at or after it is a live `violation` -- a future recurrence this check
exists to actually catch, not just narrate after the fact.

Usage:
    python3 tools/commit_author_check.py check [--max-commits N]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The one identity a commit falls back to when no -c user.name/user.email
# override is passed -- never a legitimate god author.
GENERIC_AUTHOR_EMAIL = "noreply@anthropic.com"

# A town ritual commit -- WIP marker or close -- always opens "task <N>:".
# Anything else (an early scaffold commit, a one-off doc fix predating the
# god-authorship convention) is out of scope for this check on purpose.
_TASK_COMMIT_RE = re.compile(r"^task \d+:")

# The hour this check itself shipped (task 2507's own wip-opened marker).
# A drift commit authored before this is sealed history, grandfathered
# below; one authored at or after it is live.
FIX_LANDED_AT = "2026-11-08T08:00:00+00:00"

_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"


def read_commits(repo_root: str = ROOT, max_commits: int = 200) -> list[dict[str, str]]:
    """Read up to max_commits most-recent commits on the current branch:
    sha, author name, author email, author date (ISO-8601), subject
    line. One git subprocess call, no network -- same boundary
    sync_checkout.sh already draws around git state."""
    fmt = _FIELD_SEP.join(["%H", "%an", "%ae", "%aI", "%s"]) + _RECORD_SEP
    result = subprocess.run(
        ["git", "log", f"-{max_commits}", f"--pretty=format:{fmt}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    commits = []
    for record in result.stdout.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        sha, author_name, author_email, author_date, subject = record.split(_FIELD_SEP, 4)
        commits.append({
            "sha": sha,
            "author_name": author_name,
            "author_email": author_email,
            "author_date": author_date,
            "subject": subject,
        })
    return commits


def find_author_drift(
    repo_root: str = ROOT, max_commits: int = 200, fix_landed_at: str = FIX_LANDED_AT
) -> dict[str, list[dict[str, str]]]:
    """Return every task-ritual commit (subject matching "task <N>:")
    among the most recent max_commits whose author email is the generic
    harness identity rather than a <slug>@orita.gods god identity --
    split into `grandfathered` (authored before fix_landed_at, sealed
    history) and `violations` (authored at or after it, live)."""
    fix_landed = datetime.fromisoformat(fix_landed_at)
    grandfathered: list[dict[str, str]] = []
    violations: list[dict[str, str]] = []
    for commit in read_commits(repo_root=repo_root, max_commits=max_commits):
        if not _TASK_COMMIT_RE.match(commit["subject"]):
            continue
        if commit["author_email"] != GENERIC_AUTHOR_EMAIL:
            continue
        authored_at = datetime.fromisoformat(commit["author_date"]).astimezone(timezone.utc)
        if authored_at < fix_landed:
            grandfathered.append(commit)
        else:
            violations.append(commit)
    return {"grandfathered": grandfathered, "violations": violations}


def format_drift(drift: dict[str, list[dict[str, str]]]) -> str:
    violations = drift["violations"]
    grandfathered = drift["grandfathered"]
    if not violations:
        tail = (
            f" ({len(grandfathered)} grandfathered pre-fix instance(s), sealed history)"
            if grandfathered
            else ""
        )
        return (
            "commit author check: clean -- every task-ritual commit since "
            f"the fix authored as its own god{tail}"
        )
    lines = [
        f"commit author check: {len(violations)} DRIFT(ED) commit(s) -- "
        + "authored as the generic harness identity, not the owner god"
    ]
    for commit in violations:
        lines.append(f"  {commit['sha'][:12]} :: {commit['subject']!r}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    max_commits = 200
    if "--max-commits" in argv:
        max_commits = int(argv[argv.index("--max-commits") + 1])
    found = find_author_drift(max_commits=max_commits)
    print(format_drift(found))
    sys.exit(1 if found["violations"] else 0)
