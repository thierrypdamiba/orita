"""Task 55. The owed-X-post queue: durable, tested state replacing hand-
written skipped.md prose for change-gated posts an X-side outage delayed.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "x_post_queue", os.path.join(ROOT, "tools", "x_post_queue.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


xpq = _load()


class _TempQueueCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.path)  # queue_owed_post/_append must create it fresh

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)


class TestQueueOwedPost(_TempQueueCase):
    def test_queuing_a_new_task_returns_true_and_writes_a_line(self):
        added = xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        self.assertTrue(added)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_queuing_the_same_task_twice_is_a_deduped_no_op(self):
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        added_again = xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        self.assertFalse(added_again)
        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_queuing_distinct_tasks_writes_distinct_lines(self):
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        xpq.queue_owed_post("51", "tag cadence", "2026-07-14T02:05:50Z", path=self.path)
        pending = xpq.pending_entries(path=self.path)
        self.assertEqual({e["task"] for e in pending}, {"50", "51"})


class TestPendingEntries(_TempQueueCase):
    def test_pending_is_empty_for_a_missing_file(self):
        self.assertEqual(xpq.pending_entries(path=self.path), [])

    def test_a_posted_marker_removes_its_tasks_from_pending_without_editing_the_queued_line(self):
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        xpq.queue_owed_post("51", "tag cadence", "2026-07-14T02:05:50Z", path=self.path)
        xpq.mark_posted(["50"], "999", "2026-07-14T06:30:00Z", path=self.path)

        pending = xpq.pending_entries(path=self.path)
        self.assertEqual([e["task"] for e in pending], ["51"])

        with open(self.path) as f:
            lines = [ln for ln in f if ln.strip()]
        self.assertEqual(len(lines), 3)  # 2 queued + 1 posted marker, nothing rewritten

    def test_pending_is_ordered_oldest_queued_first(self):
        xpq.queue_owed_post("52", "label cadence", "2026-07-14T03:12:00Z", path=self.path)
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        pending = xpq.pending_entries(path=self.path)
        self.assertEqual([e["task"] for e in pending], ["50", "52"])


class TestEntriesMalformedLine(_TempQueueCase):
    """Task 240: a line that isn't valid JSON any more must not crash
    _entries() -- mirroring tools/ledger.py's and tools/change_gate.py's
    own convention from tasks 238/239."""

    def test_entries_marks_a_malformed_line_instead_of_raising(self):
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write('{"type": "posted", "tasks": ["50"] <<<< not json\n')
        entries = xpq._entries(self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_pending_entries_raises_on_a_malformed_posted_marker_not_a_crash(self):
        # Pre-fix this raised an uncaught json.JSONDecodeError; it must now
        # raise the named QueueTamperedError instead of guessing past a
        # marker that might be hiding an already-posted task.
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write('{"type": "posted", "tasks": ["50"] <<<< not json\n')
        with self.assertRaises(xpq.QueueTamperedError):
            xpq.pending_entries(path=self.path)

    def test_pending_entries_raises_on_a_malformed_queued_line_too(self):
        # Not just a posted marker -- a malformed line anywhere is refused,
        # since a queued line and a posted marker look identical once broken.
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write('{"type": "queued", "task": "51" <<<< not json\n')
        with self.assertRaises(xpq.QueueTamperedError):
            xpq.pending_entries(path=self.path)

    def test_a_clean_queue_is_unaffected_by_the_new_guard(self):
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        xpq.queue_owed_post("51", "tag cadence", "2026-07-14T02:05:50Z", path=self.path)
        xpq.mark_posted(["50"], "999", "2026-07-14T06:30:00Z", path=self.path)
        pending = xpq.pending_entries(path=self.path)
        self.assertEqual([e["task"] for e in pending], ["51"])

    def test_entries_marks_a_valid_but_non_dict_line_as_malformed(self):
        # Task 320: a line that parses cleanly to a non-dict JSON value (a
        # bare number, null, list, or stray string) must not sail through
        # unmarked -- it's just as unreadable as a decode failure.
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("5\n")
        entries = xpq._entries(self.path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])
        self.assertIn("_error", entries[1])

    def test_pending_entries_raises_tampered_error_on_a_non_dict_line_instead_of_crashing(self):
        # Pre-fix this raised an uncaught AttributeError ('int' object has
        # no attribute 'get'); it must now raise the named QueueTamperedError.
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path, "a") as f:
            f.write("5\n")
        with self.assertRaises(xpq.QueueTamperedError):
            xpq.pending_entries(path=self.path)


class TestComposeCombinedTweet(unittest.TestCase):
    def test_raises_on_no_pending_entries(self):
        with self.assertRaises(ValueError):
            xpq.compose_combined_tweet([])

    def test_names_every_pending_task(self):
        entries = [
            {"task": "50", "topic": "subscriber cadence", "queued_at": "x"},
            {"task": "51", "topic": "tag cadence", "queued_at": "x"},
        ]
        text = xpq.compose_combined_tweet(entries)
        self.assertIn("#50", text)
        self.assertIn("#51", text)
        self.assertIn("subscriber cadence", text)
        self.assertIn("tag cadence", text)

    def test_stays_under_the_character_limit_for_a_realistic_backlog(self):
        entries = [
            {"task": str(n), "topic": f"cadence {n}", "queued_at": "x"} for n in range(50, 55)
        ]
        text = xpq.compose_combined_tweet(entries)
        self.assertLessEqual(len(text), xpq.MAX_TWEET_CHARS)

    def test_raises_rather_than_silently_truncates_when_too_long(self):
        entries = [
            {"task": str(n), "topic": "x" * 40, "queued_at": "x"} for n in range(100, 130)
        ]
        with self.assertRaises(ValueError) as ctx:
            xpq.compose_combined_tweet(entries)
        self.assertIn("split across more than one post", str(ctx.exception))


class TestComposeBatchedTweets(unittest.TestCase):
    def test_raises_on_no_pending_entries(self):
        with self.assertRaises(ValueError):
            xpq.compose_batched_tweets([])

    def test_a_backlog_that_fits_in_one_tweet_returns_a_single_batch(self):
        entries = [
            {"task": "50", "topic": "subscriber cadence", "queued_at": "x"},
            {"task": "51", "topic": "tag cadence", "queued_at": "x"},
        ]
        batches = xpq.compose_batched_tweets(entries)
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0], xpq.compose_combined_tweet(entries))

    def test_splits_the_real_backlog_that_compose_combined_tweet_rejects(self):
        # The actual tasks 50-55 topic strings from HAND/x-post-queue.jsonl,
        # 406 chars combined -- proven this hour to raise on compose_combined_tweet.
        entries = [
            {"task": "50", "topic": "subscriber cadence -- the town's own GitHub watcher count", "queued_at": "1"},
            {"task": "51", "topic": "tag cadence -- the town's own GitHub tag count", "queued_at": "2"},
            {"task": "52", "topic": "label cadence -- the town's own GitHub repository label count", "queued_at": "3"},
            {"task": "53", "topic": "topic cadence -- the town's own GitHub repository topic count", "queued_at": "4"},
            {"task": "54", "topic": "open pull-request cadence -- the town's own currently-open PR count", "queued_at": "5"},
            {"task": "55", "topic": "the owed-post queue itself -- tools/x_post_queue.py", "queued_at": "6"},
        ]
        with self.assertRaises(ValueError):
            xpq.compose_combined_tweet(entries)

        batches = xpq.compose_batched_tweets(entries)
        self.assertGreater(len(batches), 1)
        for b in batches:
            self.assertLessEqual(len(b), xpq.MAX_TWEET_CHARS)

        covered = []
        for b in batches:
            for e in entries:
                if f"#{e['task']} {e['topic']}" in b:
                    covered.append(e["task"])
        self.assertEqual(covered, [e["task"] for e in entries])  # every entry once, in order

    def test_a_single_entry_too_long_for_one_tweet_raises(self):
        entries = [{"task": "99", "topic": "x" * 300, "queued_at": "x"}]
        with self.assertRaises(ValueError):
            xpq.compose_batched_tweets(entries)

    def test_batches_are_numbered_when_more_than_one_is_needed(self):
        entries = [
            {"task": str(n), "topic": "y" * 60, "queued_at": str(n)} for n in range(10)
        ]
        batches = xpq.compose_batched_tweets(entries)
        self.assertGreater(len(batches), 1)
        n = len(batches)
        for i, b in enumerate(batches, start=1):
            self.assertTrue(b.startswith(f"Owed reports ({i}/{n}): "))


class TestBatchEntries(unittest.TestCase):
    def test_matches_compose_batched_tweets_text_exactly(self):
        entries = [
            {"task": "50", "topic": "subscriber cadence -- the town's own GitHub watcher count", "queued_at": "1"},
            {"task": "51", "topic": "tag cadence -- the town's own GitHub tag count", "queued_at": "2"},
            {"task": "52", "topic": "label cadence -- the town's own GitHub repository label count", "queued_at": "3"},
            {"task": "53", "topic": "topic cadence -- the town's own GitHub repository topic count", "queued_at": "4"},
            {"task": "54", "topic": "open pull-request cadence -- the town's own currently-open PR count", "queued_at": "5"},
            {"task": "55", "topic": "the owed-post queue itself -- tools/x_post_queue.py", "queued_at": "6"},
        ]
        groups = xpq.batch_entries(entries)
        n = len(groups)
        rebuilt = [
            xpq._header(i, n) + "; ".join(xpq._item_text(e) for e in g)
            for i, g in enumerate(groups, start=1)
        ]
        self.assertEqual(rebuilt, xpq.compose_batched_tweets(entries))

    def test_every_entry_appears_in_exactly_one_group_in_order(self):
        entries = [{"task": str(n), "topic": "y" * 60, "queued_at": str(n)} for n in range(10)]
        groups = xpq.batch_entries(entries)
        flattened = [e["task"] for g in groups for e in g]
        self.assertEqual(flattened, [e["task"] for e in entries])


class TestNextPostPlan(unittest.TestCase):
    def test_raises_on_no_pending_entries(self):
        with self.assertRaises(ValueError):
            xpq.next_post_plan([])

    def test_single_batch_backlog_has_zero_remaining(self):
        entries = [
            {"task": "50", "topic": "subscriber cadence", "queued_at": "x"},
            {"task": "51", "topic": "tag cadence", "queued_at": "x"},
        ]
        plan = xpq.next_post_plan(entries)
        self.assertEqual(plan["tasks"], ["50", "51"])
        self.assertEqual(plan["remaining_batches"], 0)
        self.assertEqual(plan["text"], xpq.compose_combined_tweet(entries))

    def test_multi_batch_backlog_returns_only_the_first_batch(self):
        entries = [{"task": str(n), "topic": "y" * 60, "queued_at": str(n)} for n in range(10)]
        full_batches = xpq.compose_batched_tweets(entries)
        self.assertGreater(len(full_batches), 1)

        plan = xpq.next_post_plan(entries)
        self.assertEqual(plan["text"], full_batches[0])
        self.assertEqual(plan["remaining_batches"], len(full_batches) - 1)
        self.assertLessEqual(len(plan["text"]), xpq.MAX_TWEET_CHARS)

    def test_draining_one_batch_at_a_time_never_posts_more_than_one_per_call(self):
        entries = [{"task": str(n), "topic": "y" * 60, "queued_at": str(n)} for n in range(18)]
        remaining = list(entries)
        posted_order = []
        calls = 0
        while remaining:
            calls += 1
            plan = xpq.next_post_plan(remaining)
            self.assertLessEqual(len(plan["text"]), xpq.MAX_TWEET_CHARS)
            posted_order.extend(plan["tasks"])
            remaining = [e for e in remaining if e["task"] not in plan["tasks"]]
            self.assertEqual(plan["remaining_batches"], len(xpq.batch_entries(remaining)) if remaining else 0)
        self.assertEqual(posted_order, [e["task"] for e in entries])
        self.assertGreater(calls, 1)  # never drained in a single burst call

    def test_one_permanently_unpostable_entry_does_not_block_the_rest(self):
        """Reproduces the real live bug found on HAND/x-post-queue.jsonl:
        task 185's real, already-queued topic string (295 chars) cannot fit
        in a single tweet no matter how it is packed. Before the fix,
        next_post_plan(entries) handed the WHOLE list straight to
        batch_entries(), which raised ValueError the moment it found that
        one entry -- silently blocking every other, perfectly postable
        entry in the backlog from ever being planned or drained."""
        unpostable_topic = "x" * 295  # mirrors the real task 185 topic length
        entries = [
            {"task": "50", "topic": "subscriber cadence", "queued_at": "1"},
            {"task": "185", "topic": unpostable_topic, "queued_at": "2"},
            {"task": "51", "topic": "tag cadence", "queued_at": "3"},
        ]
        # The unpostable entry alone still correctly raises via batch_entries
        # / compose_batched_tweets -- this fix does not weaken that contract.
        with self.assertRaises(ValueError):
            xpq.compose_batched_tweets(entries)

        plan = xpq.next_post_plan(entries)
        self.assertEqual(plan["tasks"], ["50", "51"])
        self.assertEqual(plan["blocked_tasks"], ["185"])
        self.assertLessEqual(len(plan["text"]), xpq.MAX_TWEET_CHARS)

    def test_all_entries_unpostable_raises_a_distinct_clear_message(self):
        entries = [{"task": "1", "topic": "x" * 295, "queued_at": "a"}]
        with self.assertRaises(ValueError) as ctx:
            xpq.next_post_plan(entries)
        self.assertIn("unpostable", str(ctx.exception))

    def test_fits_in_any_batch_matches_batch_entries_own_raise_condition(self):
        short = {"task": "1", "topic": "short topic", "queued_at": "a"}
        long_ = {"task": "2", "topic": "x" * 295, "queued_at": "b"}
        self.assertTrue(xpq._fits_in_any_batch(short))
        self.assertFalse(xpq._fits_in_any_batch(long_))
        with self.assertRaises(ValueError):
            xpq.batch_entries([long_])

    def test_a_boundary_entry_alone_is_blocked_cleanly_not_an_uncaught_crash(self):
        """_fits_in_any_batch used min(len(_header(1,1)), len(_header(1,2)))
        as its safety margin -- the SHORT n>=2 header's 20 chars of room,
        not the LONG n==1 header's 29. A 258-char item_text (254-char
        topic) fits under the 260-char room that wrongly implied, but
        not under the real 251-char room a lone entry (n forced to 1)
        actually gets. That let it into `postable`, where batch_entries
        found n==1 the only value it could ever try for a single-entry
        list, failed to pack it, and raised ValueError('...does not fit
        in a single tweet even alone...') straight out of next_post_plan
        -- the exact uncaught crash blocked_tasks exists to prevent."""
        boundary_topic = "x" * 254  # item_text is 258 chars: 251 < 258 <= 260
        entry = {"task": "199", "topic": boundary_topic, "queued_at": "a"}
        self.assertFalse(xpq._fits_in_any_batch(entry))
        with self.assertRaises(ValueError) as ctx:
            xpq.next_post_plan([entry])
        self.assertIn("unpostable", str(ctx.exception))

    def test_a_boundary_entry_alongside_others_is_blocked_not_a_crash(self):
        """Same boundary entry as above, but sitting in a real multi-entry
        backlog (mirrors how it would actually appear in HAND/x-post-queue.jsonl):
        the two short entries must still plan and post fine, and the
        boundary entry must land in blocked_tasks rather than taking the
        whole call down."""
        boundary_topic = "x" * 254
        entries = [
            {"task": "50", "topic": "subscriber cadence", "queued_at": "1"},
            {"task": "199", "topic": boundary_topic, "queued_at": "2"},
            {"task": "51", "topic": "tag cadence", "queued_at": "3"},
        ]
        plan = xpq.next_post_plan(entries)
        self.assertEqual(plan["tasks"], ["50", "51"])
        self.assertEqual(plan["blocked_tasks"], ["199"])
        self.assertLessEqual(len(plan["text"]), xpq.MAX_TWEET_CHARS)


class TestMarkPosted(_TempQueueCase):
    def test_mark_posted_never_mutates_a_prior_queued_line(self):
        xpq.queue_owed_post("50", "subscriber cadence", "2026-07-14T01:09:00Z", path=self.path)
        with open(self.path) as f:
            before = f.readlines()

        xpq.mark_posted(["50"], "999", "2026-07-14T06:30:00Z", path=self.path)

        with open(self.path) as f:
            after = f.readlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(len(after), len(before) + 1)


if __name__ == "__main__":
    unittest.main()
