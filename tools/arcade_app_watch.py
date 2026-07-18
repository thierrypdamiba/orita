#!/usr/bin/env python3
"""Task 122. The gateway's own connected apps, given a durable memory.

`Arcade_ListApps` answers "what does the-hand gateway have connected right
now" every time it is called, but nothing before this module ever wrote the
answer down. The 2026-07-18T03:0x ritual called it live for the first time
in memory and found Google, Slack, and Linear connected alongside the
long-known GitHub and X -- a real change from what `fencepost/SCOPES.md`'s
WIP note (#16) still claimed ("no demo Gmail/Calendar account is
connected"). Nobody could say when any of those three actually connected,
because nothing durable was ever recording "what was connected last time
anyone looked" -- the identical recalled-not-recorded shape
`tools/x_outage_tracker.py` (task 57), `tools/square_check.py` (task 70),
`tools/word_watch.py` (task 74), and the escalation-tier suppression key
(task 92) each already closed for a different number. This closes it for
the gateway's own app list.

This is NOT `records/metrics.jsonl`'s `distinct_toolkits_in_use` field.
That field is STRATEGY.md's Fencepost-adoption metric (owner nisaba):
distinct toolkits OUTSIDE USERS have connected to their OWN forked
Fencepost instance -- honestly 0, since no real outside user has ever
connected anything. What this module tracks is a different fact entirely:
what the-hand's OWN gateway (the town's single shared Arcade connection)
currently has connected, which may include apps connected for reasons that
have nothing to do with Fencepost at all. Folding this module's count into
`distinct_toolkits_in_use` would misrepresent the adoption metric it exists
to keep honest -- so this module never writes that field, and nothing here
should ever be read as "N users have connected N toolkits."

Same discipline as `square_check.py`: this makes no network call of its
own. The caller (the god on duty, holding this hour's real `Arcade_ListApps`
read) hands in the list of apps; this module only records and compares.

Usage:
    python3 tools/arcade_app_watch.py check <apps.json>
    python3 tools/arcade_app_watch.py record <apps.json> <checked_at>

<apps.json> shape: the raw `Arcade_ListApps` response, i.e.
    {"apps": [{"app_id": "...", "name": "...", "connected": true,
               "account": "...", "permissions": ["...", ...]}, ...]}
An app with no `permissions` key (the two town-internal `ap_...`/plain
entries `Arcade_ListApps` sometimes returns) is treated as an empty scope
list, not an error.
"""
import json
import os

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "arcade-app-check-log.jsonl")


def compute_app_state(apps: list[dict]) -> dict:
    """Fold a live `Arcade_ListApps` read into the durable comparison shape.

    Only apps with `connected: true` are kept -- an app that has never been
    connected is not a fact worth a durable record, and the (long, mostly
    unchanging) list of never-connected default providers would otherwise
    drown every real delta in noise. Keyed by `app_id` (stable across
    renames of the human-readable `name`); each value is the sorted list of
    granted `permissions` (empty list if the field is absent).
    """
    connected = {}
    for app in apps:
        if not app.get("connected"):
            continue
        app_id = app["app_id"]
        connected[app_id] = sorted(app.get("permissions") or [])
    return {"connected_app_ids": sorted(connected), "scopes_by_app": connected}


def _entries(path=LOG):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append(entry, path=LOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def last_app_state(path=LOG):
    """The most recently recorded real app-connection check, or None."""
    entries = _entries(path)
    return entries[-1] if entries else None


def record_app_check(state: dict, checked_at: str, path=LOG) -> None:
    """Append one real observed gateway app-connection state. Never edits or removes a prior line."""
    entry = dict(state)
    entry["checked_at"] = checked_at
    _append(entry, path)


def app_delta(state: dict, path=LOG):
    """Whether this hour's live app-connection read differs from the last recorded check.

    Returns (changed: bool, reason: str). No prior check recorded: due
    (first check), naming every connected app. A newly connected app: due,
    named by app_id. A newly disconnected app (was connected last time,
    absent or no longer connected now): due, named by app_id. A
    scope-list change on an app connected both times: due, naming the
    added/removed permissions -- distinguished from a connect/disconnect
    because the app itself never dropped off the gateway. Otherwise: not
    due, and the reason names the unchanged connected-app set.
    """
    last = last_app_state(path)
    if last is None:
        apps = ", ".join(state["connected_app_ids"]) or "(none)"
        return True, f"no prior app check recorded -- due, currently connected: {apps}"

    prev_ids = set(last["scopes_by_app"])
    curr_ids = set(state["scopes_by_app"])

    newly_connected = sorted(curr_ids - prev_ids)
    newly_disconnected = sorted(prev_ids - curr_ids)
    if newly_connected or newly_disconnected:
        parts = []
        if newly_connected:
            parts.append(f"newly connected: {', '.join(newly_connected)}")
        if newly_disconnected:
            parts.append(f"newly disconnected: {', '.join(newly_disconnected)}")
        return True, "; ".join(parts)

    scope_changes = []
    for app_id in sorted(curr_ids):
        prev_scopes = set(last["scopes_by_app"][app_id])
        curr_scopes = set(state["scopes_by_app"][app_id])
        if prev_scopes != curr_scopes:
            added = sorted(curr_scopes - prev_scopes)
            removed = sorted(prev_scopes - curr_scopes)
            detail = []
            if added:
                detail.append(f"+{','.join(added)}")
            if removed:
                detail.append(f"-{','.join(removed)}")
            scope_changes.append(f"{app_id} ({' '.join(detail)})")
    if scope_changes:
        return True, f"scope change on already-connected app(s): {'; '.join(scope_changes)}"

    apps = ", ".join(state["connected_app_ids"]) or "(none)"
    return False, f"unchanged, still connected: {apps}"


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, apps_path = argv[1], argv[2]
    with open(apps_path) as f:
        raw = json.load(f)
    state = compute_app_state(raw.get("apps", []))
    if cmd == "check":
        changed, reason = app_delta(state, path=LOG)
        print(f"{'changed' if changed else 'unchanged'} -- {reason}")
        return 0
    elif cmd == "record":
        if len(argv) < 4:
            print("usage: record <apps.json> <checked_at>")
            return 1
        record_app_check(state, argv[3], path=LOG)
        print(f"recorded: {state}")
        return 0
    print(f"unknown command: {cmd!r}")
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv))
