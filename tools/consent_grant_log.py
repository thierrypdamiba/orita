#!/usr/bin/env python3
"""Task 145. Nisaba corrects a flattering number in her own ledger.

`records/metrics.jsonl` recorded a `distinct_toolkits_in_use` reading
every day from 2026-07-12 through 2026-07-18 -- and every single one of
those readings said `2`. `tools/arcade_app_watch.py`'s own docstring
(task 122, six days into that streak) says plainly what this field is
supposed to mean: distinct toolkits OUTSIDE REAL USERS have connected to
their OWN forked Fencepost instance, "honestly 0, since no real outside
user has ever connected anything." The very first metrics.jsonl entry
(2026-07-12) even said so in its own prose -- "Fencepost still dogfooding
on the-hand only (GitHub + X); no outside OAuth connections yet" -- while
the structured field on that same line read `2`. A ledger that flatters
is a ledger that lies; this task (145) corrected every one of those
historical entries to the honest 0, in the open, with a dated note on
each. What was still missing, and is the actual point of this module: the
one durable fact that would keep this field honest going forward --
whether a real, gate-passing human consent has EVER actually happened.

`fencepost/seam_engine/src/seam_engine/consent.py` (Esu's own door) is
deliberately pure -- "This module reads nothing and writes nothing itself
... it is pure judgment, not action." Nothing durable was ever built to
remember a REAL consent once `enforce_consent_gate` actually granted one.
This module is that durable memory, the same shape `arcade_app_watch.py`,
`x_outage_tracker.py`, and `ci_watch.py` already hold for their own
facts: local-filesystem-only, append-only, never edits or removes a prior
line, and -- unlike those three -- never writes a line the gate itself
did not just approve. `record_grant` re-runs `enforce_consent_gate` before
appending anything; a caller cannot durably claim a consent that would not
itself pass the two locks (public issue + verbatim scope confirm).

As of this task, zero real human consents have ever been granted (no
`ConsentRecord` has ever existed for a real account, per `fencepost/
SCOPES.md`'s own WIP note) -- so this log is empty, and
`real_distinct_toolkit_count()` honestly returns 0. It stays 0 until a
real human actually clears the gate; nothing here guesses or backfills
that day, the same discipline `metrics_cadence_check.py` already holds
for a missing daily reading.

Usage:
    python3 tools/consent_grant_log.py count
"""
from __future__ import annotations

import json
import os
import sys
from typing import cast

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "fencepost", "seam_engine", "src",
    ),
)
from seam_engine.consent import ConsentRecord, enforce_consent_gate  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonl_read  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "HAND", "consent-grants-log.jsonl")


def _entries(path: str = LOG) -> list[dict[str, object]]:
    """Every real recorded grant, oldest first. Delegates to
    jsonl_read.read_jsonl_entries (task 540) -- see that module's own
    docstring for the fourteen-copy history this replaced.
    real_distinct_toolkit_count() is the one that decides a malformed line
    here is never safe to ignore."""
    return jsonl_read.read_jsonl_entries(path)


def record_grant(
    human: str,
    toolkit: str,
    issue_url: str,
    confirmed_scopes: "frozenset[str]",
    recorded_at: str,
    path: str = LOG,
) -> dict[str, object]:
    """Durably record ONE real, already-gated consent grant.

    Re-runs `enforce_consent_gate` itself before writing a single byte --
    a caller cannot durably claim a consent the gate would refuse.
    Raises `seam_engine.consent.ConsentRequiredError` and writes nothing
    if the record does not actually clear both locks. Append-only: never
    edits or removes a prior line, mirroring `arcade_app_watch.record`'s
    own discipline.
    """
    record = ConsentRecord(
        human=human,
        issue_url=issue_url,
        toolkit=toolkit,
        confirmed_scopes=confirmed_scopes,
    )
    enforce_consent_gate(record, toolkit=toolkit)  # raises if either lock fails; writes nothing
    entry: dict[str, object] = {
        "human": human,
        "toolkit": toolkit,
        "issue_url": issue_url,
        "confirmed_scopes": sorted(confirmed_scopes),
        "recorded_at": recorded_at,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


class ConsentLogTamperedError(RuntimeError):
    """Raised by distinct_toolkits()/real_distinct_toolkit_count() when any
    line in the log is unreadable.

    Unlike tools/ledger.py's hash chain, a toolkit-bearing grant here can
    sit anywhere in the file, not just at the tip -- mirroring
    tools/x_post_queue.py's own stricter any-line rule (task 240):
    silently skipping just the unreadable line would let STRATEGY.md's
    leading toolkit-count metric quietly undercount a real recorded grant,
    the same "guessing past corruption hides real state" risk the sibling
    fixes already refuse to take."""


def distinct_toolkits(entries: list[dict[str, object]]) -> set[str]:
    """The set of distinct toolkit names across every real recorded
    grant -- never a count of grants themselves (one human confirming
    both Gmail and Calendar is two toolkits, not two "users").

    Refuses via ConsentLogTamperedError if any entry is malformed -- see
    that class's docstring for why a partial read here is unsafe."""
    malformed = [e for e in entries if e.get("_malformed")]
    if malformed:
        raise ConsentLogTamperedError(
            f"distinct_toolkits(): refusing -- {len(malformed)} unreadable line(s) "
            "could be hiding a real recorded grant, and guessing past that risks "
            "silently undercounting STRATEGY.md's toolkit metric. Repair the log "
            f"by hand, then re-run. First error: {malformed[0]['_error']}"
        )
    return {cast(str, e["toolkit"]) for e in entries}


def real_distinct_toolkit_count(path: str = LOG) -> int:
    """STRATEGY.md's actual leading metric, computed from ground truth
    instead of hand-typed: how many distinct read-only toolkits has at
    least one REAL outside human actually, verifiably connected. Zero
    until this log holds a real line -- and it never fabricates one."""
    return len(distinct_toolkits(_entries(path)))


def distinct_humans(entries: list[dict[str, object]]) -> set[str]:
    """The set of distinct human identities across every real recorded
    grant -- never a count of grants themselves (one human confirming
    both Gmail and Calendar is still ONE connected user, not two).
    Task 412: this is `records/metrics.jsonl`'s `connected_users_oauth`
    field's actual ground truth, the same role `distinct_toolkits` already
    plays for `distinct_toolkits_in_use` -- STRATEGY.md's own separate row,
    "'Connect your own' OAuth completions across users | leading | 100
    connected users in 60 days | kothar-wa-khasis," counts USERS, not
    toolkits, and until now nothing in this log distinguished the two.

    Refuses via ConsentLogTamperedError if any entry is malformed -- see
    that class's docstring for why a partial read here is unsafe."""
    malformed = [e for e in entries if e.get("_malformed")]
    if malformed:
        raise ConsentLogTamperedError(
            f"distinct_humans(): refusing -- {len(malformed)} unreadable line(s) "
            "could be hiding a real recorded grant, and guessing past that risks "
            "silently undercounting STRATEGY.md's connected-users metric. Repair "
            f"the log by hand, then re-run. First error: {malformed[0]['_error']}"
        )
    return {cast(str, e["human"]) for e in entries}


def real_distinct_human_count(path: str = LOG) -> int:
    """STRATEGY.md's "'Connect your own' OAuth completions across users"
    row, computed from ground truth instead of hand-typed: how many
    distinct REAL humans have actually, verifiably cleared the consent
    gate for at least one toolkit. Zero until this log holds a real line
    -- and it never fabricates one. Deliberately separate from
    `real_distinct_toolkit_count`: one human clearing Gmail AND Calendar
    is one connected user and two connected toolkits, and STRATEGY.md's
    metrics table tracks both as distinct rows with distinct owners
    (nisaba for toolkit breadth, kothar-wa-khasis for user completions) --
    collapsing them into a single number would misreport whichever row
    borrowed the other's count."""
    return len(distinct_humans(_entries(path)))


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "count":
        print(__doc__)
        sys.exit(1)
    n = real_distinct_toolkit_count()
    h = real_distinct_human_count()
    print(f"real distinct toolkits in use (outside users, gate-verified): {n}")
    print(f"real distinct connected users (outside humans, gate-verified): {h}")
    sys.exit(0)
