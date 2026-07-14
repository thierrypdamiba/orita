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
