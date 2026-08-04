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

Task 523: the identical AST-hash sweep, re-run over the same 25
`*_cadence.py` files, found a THIRD byte-identical function this
sibling's own earlier pass (task 516) missed: `load_snapshots`. Unlike
`_parse_ts`, a bare `load_snapshots = time_utils.load_snapshots` name
rebinding is wrong here -- every sibling's own `load_snapshots(path=
DEFAULT_SNAPSHOT_PATH)` default differs (each cadence writes its own
snapshot file) and each module's own scan functions call
`load_snapshots()` bare, relying on that default. So each sibling keeps
a thin wrapper with its own default; `LoadSnapshotsDelegatesCase` below
proves every wrapper genuinely calls through to the one shared
`time_utils.load_snapshots` (by patching it and observing every sibling
call the patch), not a reinlined copy of the old logic.
"""
from __future__ import annotations

import datetime
import os
import sys
import unittest
from unittest import mock

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


LOAD_SNAPSHOTS_SIBLINGS = [mod for mod in SIBLINGS if mod is not autograde]


class LoadSnapshotsDelegatesCase(unittest.TestCase):
    """Every sibling cadence module's own `load_snapshots(path=<its own
    DEFAULT_SNAPSHOT_PATH>)` must genuinely call through to
    `time_utils.load_snapshots` -- not carry a reinlined copy of the
    read-and-mark-malformed logic. A bare `assertIs` on the function
    object (the `_parse_ts` pattern above) doesn't fit here because each
    sibling's own wrapper is a distinct function object by necessity (its
    default argument differs module to module); patching the shared
    target and observing every sibling's call reach it is the identity
    guarantee's equivalent for a wrapper-with-its-own-default shape."""

    def test_every_sibling_wrapper_delegates_to_the_shared_function(self):
        self.assertEqual(
            len(LOAD_SNAPSHOTS_SIBLINGS), 25, "sibling list drifted from the live sweep"
        )
        for mod in LOAD_SNAPSHOTS_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                sentinel = object()
                calls = []

                def fake_load_snapshots(path, _calls=calls, _sentinel=sentinel):
                    _calls.append(path)
                    return _sentinel

                with mock.patch.object(time_utils, "load_snapshots", fake_load_snapshots):
                    result = mod.load_snapshots("some/probe/path.jsonl")
                self.assertIs(
                    result,
                    sentinel,
                    f"{mod.__name__}.load_snapshots did not return the shared "
                    "function's result -- it may hold a reinlined copy again",
                )
                self.assertEqual(
                    calls,
                    ["some/probe/path.jsonl"],
                    f"{mod.__name__}.load_snapshots did not pass its path through "
                    "to time_utils.load_snapshots unchanged",
                )

    def test_every_sibling_default_still_resolves_to_its_own_module_default(self):
        import inspect

        for mod in LOAD_SNAPSHOTS_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                sig = inspect.signature(mod.load_snapshots)
                self.assertEqual(
                    sig.parameters["path"].default,
                    mod.DEFAULT_SNAPSHOT_PATH,
                    f"{mod.__name__}.load_snapshots() no longer defaults to its "
                    "own DEFAULT_SNAPSHOT_PATH -- bare load_snapshots() calls "
                    "elsewhere in this module would silently read the wrong file",
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
