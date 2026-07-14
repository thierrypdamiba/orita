#!/usr/bin/env python3
"""The Owed Board. Kwaku-Ananse be praised, once he stops owing five posts.

Durable, append-only state for change-gated X posts that couldn't go out
the hour they were earned (an X-side outage, an authorization boundary,
anything on the-hand's side rather than the town's). Before this module,
an owed post lived only as a paragraph of hand-written prose in
orita-vault/hand/skipped.md, re-derived from memory every hour ("this is
now N consecutive hours..."). That is itself a seam: a real, recurring
fact tracked nowhere durable. This gives it a file.

Same discipline as tools/ledger.py: append-only, no line is ever edited
or removed. A task is queued once (queue_owed_post dedupes); a posted
marker names which tasks a real tweet actually covered, and
pending_entries() simply stops counting anything a marker names -- the
queued line itself is never touched.

Task 56 adds compose_batched_tweets(): compose_combined_tweet() raises
rather than truncates once the real backlog outgrows one tweet (proven
against the actual tasks 50-55 backlog, 406 chars for a 280-char limit)
-- batching is what actually clears a backlog that size without a human
improvising a split by hand.

Usage:
    python3 tools/x_post_queue.py queue <task> <topic> <queued_at>
    python3 tools/x_post_queue.py pending
    python3 tools/x_post_queue.py compose
    python3 tools/x_post_queue.py compose-batches
    python3 tools/x_post_queue.py mark-posted <tweet_id> <posted_at> <task> [task...]
"""
import json
import os

QUEUE = os.path.join(os.path.dirname(__file__), "..", "HAND", "x-post-queue.jsonl")
MAX_TWEET_CHARS = 280


def _entries(path=QUEUE):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append(entry, path=QUEUE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def queue_owed_post(task: str, topic: str, queued_at: str, path=QUEUE) -> bool:
    """Record a shipped task's un-postable change-gated post.

    Deduped by task id: calling this twice for the same task writes
    nothing the second time and returns False. Returns True the one time
    it actually queues something new.
    """
    for e in _entries(path):
        if e.get("type") == "queued" and e.get("task") == task:
            return False
    _append({"type": "queued", "task": task, "topic": topic, "queued_at": queued_at}, path)
    return True


def _posted_tasks(entries) -> set:
    posted = set()
    for e in entries:
        if e.get("type") == "posted":
            posted.update(e.get("tasks", []))
    return posted


def pending_entries(path=QUEUE) -> list:
    """Every queued task not yet named by a posted marker, oldest first."""
    entries = _entries(path)
    posted = _posted_tasks(entries)
    by_task = {}
    for e in entries:
        if e.get("type") == "queued" and e["task"] not in posted:
            by_task[e["task"]] = e
    return sorted(by_task.values(), key=lambda e: e["queued_at"])


def compose_combined_tweet(entries: list, max_chars: int = MAX_TWEET_CHARS) -> str:
    """One tweet naming every pending task.

    Never silently drops an entry to make the text fit -- if the full
    list can't fit under max_chars, raise so a human decides how to
    split it across more than one post, rather than truncate-and-hide
    which task got left off.
    """
    if not entries:
        raise ValueError("nothing pending to post")
    body = "; ".join(f"#{e['task']} {e['topic']}" for e in entries)
    text = f"Owed reports, now caught up: {body}"
    if len(text) > max_chars:
        raise ValueError(
            f"combined tweet is {len(text)} chars (max {max_chars}) for "
            f"{len(entries)} entries -- split across more than one post "
            "instead of truncating silently"
        )
    return text


def _item_text(entry: dict) -> str:
    return f"#{entry['task']} {entry['topic']}"


def _header(i: int, n: int) -> str:
    return "Owed reports, now caught up: " if n == 1 else f"Owed reports ({i}/{n}): "


def _pack_into(items: list, n: int, max_chars: int):
    """Greedily fill exactly n ordered batches; None if it can't be done."""
    batches = []
    idx = 0
    for i in range(1, n + 1):
        header = _header(i, n)
        body = []
        while idx < len(items):
            candidate = body + [items[idx]]
            if len(header + "; ".join(candidate)) <= max_chars:
                body = candidate
                idx += 1
            else:
                break
        if not body:
            return None
        batches.append(header + "; ".join(body))
    return batches if idx == len(items) else None


def compose_batched_tweets(entries: list, max_chars: int = MAX_TWEET_CHARS) -> list:
    """Split pending entries into as few ordered tweets as needed.

    Every entry appears exactly once, in queued order, across the
    returned batches -- nothing is ever dropped or reordered. Tries one
    tweet first (identical text to compose_combined_tweet), then two,
    three, and so on. Raises only if some single entry can't fit in a
    tweet even alone with its own header -- that is a genuinely
    unpostable topic string, not a splitting failure.
    """
    if not entries:
        raise ValueError("nothing pending to post")
    items = [_item_text(e) for e in entries]
    for n in range(1, len(items) + 1):
        batches = _pack_into(items, n, max_chars)
        if batches is not None:
            return batches
    raise ValueError(
        "at least one queued entry does not fit in a single tweet even alone -- "
        "shorten its topic string"
    )


def mark_posted(tasks: list, tweet_id: str, posted_at: str, path=QUEUE) -> None:
    """Append a posted-marker event. Never edits or removes a queued line."""
    _append(
        {"type": "posted", "tasks": list(tasks), "tweet_id": tweet_id, "posted_at": posted_at},
        path,
    )


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "pending"
    if cmd == "queue":
        _task, _topic, _queued_at = sys.argv[2], sys.argv[3], sys.argv[4]
        print("queued" if queue_owed_post(_task, _topic, _queued_at) else "already queued")
    elif cmd == "pending":
        for _e in pending_entries():
            print(json.dumps(_e, ensure_ascii=False))
    elif cmd == "compose":
        print(compose_combined_tweet(pending_entries()))
    elif cmd == "compose-batches":
        for _b in compose_batched_tweets(pending_entries()):
            print(_b)
    elif cmd == "mark-posted":
        _tweet_id, _posted_at = sys.argv[2], sys.argv[3]
        _tasks = sys.argv[4:]
        mark_posted(_tasks, _tweet_id, _posted_at)
        print("marked posted:", _tasks)
