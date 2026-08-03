"""Proves `time_utils.parse_ts` behaves correctly, and that every one of
the twenty-six cadence/autograde modules it was extracted from now holds
the identical function object at its own `_parse_ts` name -- not just
identical source text. An AST-hash sweep this hour found all twenty-six
carrying a byte-identical private copy (parse an ISO-8601 string; if it
names no timezone, assume UTC), invisible to `tools/duplicate_regex_check.py`
(which only ever scans `re.compile()` call sites, never duplicated function
bodies) -- the same class of drift `tools/iso_time.py` (task 509) already
closed one directory over. Identity, not equality, is the guarantee that
matters: two independently-maintained copies with the same source today
can still drift apart on the next edit to just one of them; an `is` check
on the same function object makes that class of drift structurally
impossible going forward.
"""
from __future__ import annotations

import datetime
import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))

from oracle_engine import (  # noqa: E402
    autograde,
    branch_cadence,
    collaborator_cadence,
    comment_cadence,
    commit_cadence,
    commit_comment_cadence,
    contributor_cadence,
    deployment_cadence,
    follower_cadence,
    following_cadence,
    fork_cadence,
    issue_cadence,
    issue_comment_cadence,
    label_cadence,
    listed_cadence,
    media_cadence,
    milestone_cadence,
    pr_cadence,
    release_cadence,
    run_cadence,
    star_cadence,
    subscriber_cadence,
    tag_cadence,
    time_utils,
    topic_cadence,
    tweet_cadence,
    workflow_cadence,
)

SIBLINGS = [
    autograde,
    branch_cadence,
    collaborator_cadence,
    comment_cadence,
    commit_cadence,
    commit_comment_cadence,
    contributor_cadence,
    deployment_cadence,
    follower_cadence,
    following_cadence,
    fork_cadence,
    issue_cadence,
    issue_comment_cadence,
    label_cadence,
    listed_cadence,
    media_cadence,
    milestone_cadence,
    pr_cadence,
    release_cadence,
    run_cadence,
    star_cadence,
    subscriber_cadence,
    tag_cadence,
    topic_cadence,
    tweet_cadence,
    workflow_cadence,
]


class IdentityAcrossSiblingsCase(unittest.TestCase):
    """Every sibling's `_parse_ts` must BE `time_utils.parse_ts` (same
    function object), not merely equal source -- the only guarantee that
    makes the twenty-six-independent-copies drift this task closed
    structurally unable to recur one module at a time."""

    def test_every_sibling_shares_the_one_parser_object(self):
        self.assertEqual(len(SIBLINGS), 26, "sibling list drifted from the live sweep")
        for mod in SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                self.assertIs(
                    mod._parse_ts,
                    time_utils.parse_ts,
                    f"{mod.__name__}._parse_ts is a separate copy again, "
                    "not the shared oracle_engine.time_utils function",
                )


class ParseTsCase(unittest.TestCase):
    def test_z_suffixed_timestamp_parses_as_utc(self):
        dt = time_utils.parse_ts("2026-08-03T12:00:00+00:00")
        self.assertEqual(dt.tzinfo, datetime.timezone.utc)
        self.assertEqual(dt, datetime.datetime(2026, 8, 3, 12, 0, tzinfo=datetime.timezone.utc))

    def test_naive_timestamp_is_assumed_utc_not_local(self):
        dt = time_utils.parse_ts("2026-08-03T12:00:00")
        self.assertEqual(dt.tzinfo, datetime.timezone.utc)

    def test_aware_non_utc_timestamp_keeps_its_own_offset(self):
        dt = time_utils.parse_ts("2026-08-03T12:00:00+05:00")
        self.assertEqual(dt.utcoffset(), datetime.timedelta(hours=5))


if __name__ == "__main__":
    unittest.main()
