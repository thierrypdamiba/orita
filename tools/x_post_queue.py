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

Task 84 adds next_post_plan(): compose_batched_tweets() alone will
happily hand back eighteen separate tweets for the real live backlog
(34 entries, 2026-07-16), and nothing stopped the on-duty god from
firing all eighteen the moment X_PostTweet recovers -- exactly the
hourly-spam burst TOWN-OPERATIONS.md's own change-gate law exists to
prevent. next_post_plan() hands back only the first batch plus how
many more are waiting, so a real drain takes as many hourly ritual
runs as it takes batches, one post per run, never a burst.

Task 275 clarifies what task 262's hourly note ("compose/compose-batches
error against the live backlog... a separate pre-existing snag left for a
dedicated hour") almost turned into a fix: it isn't one. `compose` and
`compose-batches` raising the moment ANY pending entry is permanently
unpostable (tasks 185/188's over-length topics) is the documented,
tested contract of `compose_combined_tweet`/`compose_batched_tweets`/
`batch_entries` -- see `test_a_single_entry_too_long_for_one_tweet_raises`
and the comment at the top of `test_one_permanently_unpostable_entry_
does_not_block_the_rest` in tests/test_x_post_queue.py, which says outright
"this fix does not weaken that contract." `next_post_plan()` (task 84) is
the one function that adds the skip-and-report-blocked-tasks behavior on
top, precisely so the rest of a real backlog can still drain one batch per
hour. `next-post` is the command an on-duty god actually runs before a
real post (task 274 and its predecessors record checking it this way);
`ritual_check.py`'s own `check_owed_posts` only ever calls
`pending_entries` for the backlog count, never `compose`/`compose-batches`
/`next-post`, so neither of those two crashing was ever silently breaking
the hourly ritual itself. `compose`/`compose-batches` stay as lower-level,
intentionally-strict CLI commands for composing a batch by hand once a
blocked topic has been shortened. Confirmed live: `next-post` against the
real 123-entry, 2-blocked-task backlog returns a clean plan; `compose`/
`compose-batches` against the same backlog raise exactly as designed.

Usage:
    python3 tools/x_post_queue.py queue <task> <topic> <queued_at>
    python3 tools/x_post_queue.py pending
    python3 tools/x_post_queue.py next-post   -- the hourly ritual's real entry point; skips permanently-unpostable entries into blocked_tasks
    python3 tools/x_post_queue.py compose     -- one tweet for ALL pending entries; raises if it can't fit or any entry is unpostable (by design, not a bug -- use next-post operationally)
    python3 tools/x_post_queue.py compose-batches  -- every batch at once, by hand; raises on any permanently-unpostable entry (by design -- use next-post operationally)
    python3 tools/x_post_queue.py mark-posted <tweet_id> <posted_at> <task> [task...]
"""
from __future__ import annotations

import json
import os
import sys

from typing import TypedDict, cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonl_append  # noqa: E402
import jsonl_read  # noqa: E402

QUEUE = os.path.join(os.path.dirname(__file__), "..", "HAND", "x-post-queue.jsonl")
MAX_TWEET_CHARS = 280

Entry = dict[str, object]


class PostPlan(TypedDict):
    text: str
    tasks: list[str]
    remaining_batches: int
    blocked_tasks: list[str]


def _entries(path: str = QUEUE) -> list[Entry]:
    """Delegates to jsonl_read.read_jsonl_entries (task 540) -- see
    that module's own docstring for the fourteen-copy history this
    replaced."""
    return jsonl_read.read_jsonl_entries(path)

class QueueTamperedError(RuntimeError):
    """Raised by pending_entries() when any line in the queue is unreadable.

    Unlike tools/ledger.py's hash chain, a "posted" marker here can sit
    anywhere in the file, not just at the tip -- silently dropping just the
    unreadable line could make an already-posted task look pending again,
    risking a duplicate real tweet to the connected X account. Refusing
    beats guessing which tasks are actually already posted."""


# Task 510: consolidated into tools/jsonl_append.py -- ten sibling checks
# each carried a byte-identical copy of this helper. This name now points
# at the shared function object, not a local copy; tests/test_jsonl_
# append.py asserts this name IS that shared function.
_append = jsonl_append.append_jsonl


def queue_owed_post(task: str, topic: str, queued_at: str, path: str = QUEUE) -> bool:
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


def _posted_tasks(entries: list[Entry]) -> set[str]:
    posted: set[str] = set()
    for e in entries:
        if e.get("type") == "posted":
            posted.update(cast("list[str]", e.get("tasks", [])))
    return posted


def pending_entries(path: str = QUEUE) -> list[Entry]:
    """Every queued task not yet named by a posted marker, oldest first.

    Refuses via QueueTamperedError if any line in the queue is malformed --
    see that class's docstring for why a partial read here is unsafe."""
    entries = _entries(path)
    malformed = [e for e in entries if e.get("_malformed")]
    if malformed:
        raise QueueTamperedError(
            f"pending_entries(): refusing -- {len(malformed)} unreadable line(s) in "
            f"{path} could be hiding a real 'posted' marker, and guessing past that "
            "risks a duplicate real tweet. Repair the queue by hand, then re-run. "
            f"First error: {malformed[0]['_error']}"
        )
    posted = _posted_tasks(entries)
    by_task: dict[str, Entry] = {}
    for e in entries:
        if e.get("type") == "queued":
            task_id = cast(str, e["task"])
            if task_id not in posted:
                by_task[task_id] = e
    return sorted(by_task.values(), key=lambda e: cast(str, e["queued_at"]))


def compose_combined_tweet(entries: list[Entry], max_chars: int = MAX_TWEET_CHARS) -> str:
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


def _item_text(entry: Entry) -> str:
    return f"#{entry['task']} {entry['topic']}"


def _header(i: int, n: int) -> str:
    return "Owed reports, now caught up: " if n == 1 else f"Owed reports ({i}/{n}): "


def _pack_entries_into(entries: list[Entry], n: int, max_chars: int) -> list[list[Entry]] | None:
    """Greedily fill exactly n ordered groups of entry dicts; None if it can't be done."""
    batches: list[list[Entry]] = []
    idx = 0
    for i in range(1, n + 1):
        header = _header(i, n)
        body_entries: list[Entry] = []
        body_items: list[str] = []
        while idx < len(entries):
            candidate_items = body_items + [_item_text(entries[idx])]
            if len(header + "; ".join(candidate_items)) <= max_chars:
                body_items = candidate_items
                body_entries.append(entries[idx])
                idx += 1
            else:
                break
        if not body_entries:
            return None
        batches.append(body_entries)
    return batches if idx == len(entries) else None


def batch_entries(entries: list[Entry], max_chars: int = MAX_TWEET_CHARS) -> list[list[Entry]]:
    """Split pending entries into as few ordered groups of entry dicts as needed.

    Every entry appears exactly once, in queued order, across the
    returned groups -- nothing is ever dropped or reordered. Tries one
    group first, then two, three, and so on. Unlike compose_batched_tweets(),
    each returned group keeps the original entry dicts (not pre-joined
    text), so a caller can recover exactly which task ids a given batch
    covers (needed by mark_posted). Raises only if some single entry
    can't fit in a batch even alone with its own header -- that is a
    genuinely unpostable topic string, not a splitting failure.
    """
    if not entries:
        raise ValueError("nothing pending to post")
    for n in range(1, len(entries) + 1):
        batches = _pack_entries_into(entries, n, max_chars)
        if batches is not None:
            return batches
    raise ValueError(
        "at least one queued entry does not fit in a single tweet even alone -- "
        "shorten its topic string"
    )


def compose_batched_tweets(entries: list[Entry], max_chars: int = MAX_TWEET_CHARS) -> list[str]:
    """Split pending entries into as few ordered tweets as needed.

    Every entry appears exactly once, in queued order, across the
    returned batches -- nothing is ever dropped or reordered.
    """
    groups = batch_entries(entries, max_chars)
    n = len(groups)
    return [_header(i, n) + "; ".join(_item_text(e) for e in g) for i, g in enumerate(groups, start=1)]


def _fits_in_any_batch(entry: Entry, max_chars: int = MAX_TWEET_CHARS) -> bool:
    """Whether `entry` would survive `batch_entries` if it ended up alone
    in a single-batch (n == 1) plan -- the header a lone postable entry,
    or the last entry left after every sibling is blocked, actually gets.

    `_header(1, 1)`'s "now caught up" phrasing is the LONGEST header this
    module ever renders -- every n >= 2 header is shorter. Because n == 1
    is exactly the case this function has to guard (an entry alone gets
    no other n to fall back on), the bound has to be that longest header,
    `max(len(_header(1, 1)), len(_header(1, 2)))`, not the shortest one.
    A previous version of this function used `min(...)` here, reasoning
    backwards from its own correct observation that header(1,1) is the
    longest: that let entries through whose item text fit under the
    short n>=2 header (20 chars of room to spare) but not under the
    29-char n==1 header they were actually handed the moment they were
    the only postable entry left, so `batch_entries` raised `ValueError`
    straight out of `next_post_plan` -- the exact uncaught crash
    `blocked_tasks` exists to prevent. If an entry's own item text does
    not fit under max_chars even with the longest header's room, no
    value of n will ever fit it either: it is a permanently unpostable
    topic string, not merely a hard one to pack.
    """
    longest_possible_header = max(len(_header(1, 1)), len(_header(1, 2)))
    return len(_item_text(entry)) <= max_chars - longest_possible_header


def next_post_plan(entries: list[Entry], max_chars: int = MAX_TWEET_CHARS) -> PostPlan:
    """The single next tweet to post this hour -- never the whole backlog at once.

    Recovery from an outage must not turn into a burst: this returns
    only the FIRST batch batch_entries() would produce (same ordering,
    same packing as compose_batched_tweets()), the task ids it covers
    (pass straight to mark_posted once the post actually lands), and how
    many further batches are still waiting after it. A multi-batch
    backlog drains at one post per call -- the on-duty god posts this
    plan's text, marks its tasks posted, and the NEXT hourly ritual run
    calls this again for the next batch.

    A queued entry whose own topic string can never fit in a tweet by
    itself (`_fits_in_any_batch` is False for it, per `batch_entries`'
    own "no splitting can save this one" rule) is set aside into
    `blocked_tasks` instead of being handed to `batch_entries` at all --
    otherwise a single unpostably long topic anywhere in the backlog
    would raise `ValueError` here and silently block every OTHER,
    perfectly postable entry from ever being planned, the exact
    hourly-drain chokepoint this function exists to prevent. Nothing is
    dropped: `blocked_tasks` names every task id set aside this way, so a
    human still has to shorten that topic and re-queue it before it
    posts, and it stays visible on every call until they do.
    """
    postable = [e for e in entries if _fits_in_any_batch(e, max_chars)]
    blocked = [e for e in entries if not _fits_in_any_batch(e, max_chars)]
    if entries and not postable:
        raise ValueError(
            "every pending entry is unpostable on its own -- shorten at least "
            "one topic string before this backlog can drain"
        )
    groups = batch_entries(postable, max_chars)
    n = len(groups)
    first = groups[0]
    text = _header(1, n) + "; ".join(_item_text(e) for e in first)
    return {
        "text": text,
        "tasks": [cast(str, e["task"]) for e in first],
        "remaining_batches": n - 1,
        "blocked_tasks": [cast(str, e["task"]) for e in blocked],
    }


def mark_posted(tasks: list[str], tweet_id: str, posted_at: str, path: str = QUEUE) -> None:
    """Append a posted-marker event. Never edits or removes a queued line."""
    _append(
        {"type": "posted", "tasks": list(tasks), "tweet_id": tweet_id, "posted_at": posted_at},
        path,
    )


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "pending"
    if cmd == "queue":
        if len(sys.argv) < 5:
            print("usage: x_post_queue.py queue <task> <topic> <queued_at>")
            sys.exit(2)
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
    elif cmd == "next-post":
        _plan = next_post_plan(pending_entries())
        print(_plan["text"])
        print(f"tasks: {','.join(_plan['tasks'])}")
        print(f"remaining_batches: {_plan['remaining_batches']}")
        if _plan["blocked_tasks"]:
            print(f"blocked_tasks (topic too long to ever post, shorten and re-queue): {','.join(_plan['blocked_tasks'])}")
    elif cmd == "mark-posted":
        if len(sys.argv) < 4:
            print("usage: x_post_queue.py mark-posted <tweet_id> <posted_at> [task ...]")
            sys.exit(2)
        _tweet_id, _posted_at = sys.argv[2], sys.argv[3]
        _tasks = sys.argv[4:]
        mark_posted(_tasks, _tweet_id, _posted_at)
        print("marked posted:", _tasks)
