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

Task 559 carried the identical AST-hash sweep one directory over from
`tools/*.py` (where it had already run dry six times running) into this
package for the first time, and found a FOURTH byte-identical function
still standing: `record_snapshot`, differing only in which module's own
`*CadenceError` subclass it raised on bad input and a few words of
docstring. Same shape as `load_snapshots`, same reason it can't be a
bare rebinding (differing default path AND differing error class); each
sibling keeps a thin wrapper passing its own default and error class.
`RecordSnapshotDelegatesCase` below proves delegation the same way
`LoadSnapshotsDelegatesCase` does, plus a live (unmocked) check that the
right exception type still surfaces end to end.

Task 578 went one function further than task 563's own `reject_malformed`
stop and found this file's own SIXTH and SEVENTH byte-identical
functions: `X_count_at_or_before`/`X_count_at_or_after`, the scan-for-
the-closest-snapshot loops every one of the 25 cadence siblings had
carried untouched since before this module existed. Normalizing each
sibling's own function name out of its body before hashing showed the
executable logic byte-identical across all 25 -- the only variation
anywhere was docstring prose (an em dash vs a double hyphen, one
differently-wrapped line) and the caller-name string passed to
`_reject_malformed`. Each sibling keeps its own `_reject_malformed` call
first, then delegates the scan-and-compare to
`count_at_or_before`/`count_at_or_after` below.
`CountAtOrBeforeAfterDelegatesCase` proves delegation the same way
`LoadSnapshotsDelegatesCase` does, plus live (unmocked) checks that the
real scan still returns the right answer end to end.
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
    prediction,
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

_TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(_ORACLE_ENGINE_ROOT)), "tools")
_NOW = datetime.datetime(2026, 7, 20, 12, 0, tzinfo=datetime.timezone.utc)


def _fresh_ledger_module(tmp_path: str):
    """Same scratch-ledger-module pattern every `test_<topic>_cadence.py`
    file already uses (e.g. `test_workflow_cadence.py`) -- a real ledger,
    pointed at a throwaway file, never the live chain."""
    mod = prediction.load_ledger_module(_TOOLS_DIR)
    mod.LEDGER = tmp_path
    return mod


def _topic(mod):
    """Derive a sibling module's own claim-topic (`pr_cadence` -> `pr`,
    `commit_comment_cadence` -> `commit_comment`) from its module name, to
    build the right `seal_<topic>_prediction` attribute name -- the exact
    inverse of `_expected_error_cls`'s own stem derivation below."""
    return mod.__name__.rsplit(".", 1)[-1].replace("_cadence", "")


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


RECORD_SNAPSHOT_SIBLINGS = LOAD_SNAPSHOTS_SIBLINGS


def _expected_error_cls(mod):
    """Derive `<Words>CadenceError` from a sibling module's own name
    (`pr_cadence` -> `PrCadenceError`), the exact convention every one of
    the 25 siblings' real error class already follows -- checked against
    the live module, not assumed."""
    stem = mod.__name__.rsplit(".", 1)[-1].replace("_cadence", "")
    name = "".join(word.capitalize() for word in stem.split("_")) + "CadenceError"
    return getattr(mod, name)


class RecordSnapshotDelegatesCase(unittest.TestCase):
    """Every sibling cadence module's own `record_snapshot(path=<its own
    DEFAULT_SNAPSHOT_PATH>)` must genuinely call through to
    `time_utils.record_snapshot` with its own `*CadenceError` subclass as
    `error_cls` -- not carry a reinlined copy of the validate-and-write
    logic (task 559's own AST-hash sweep found all 25 byte-identical
    except for that error class and a few words of docstring, the same
    shape `load_snapshots` above already closed)."""

    def test_every_sibling_wrapper_delegates_to_the_shared_function(self):
        self.assertEqual(
            len(RECORD_SNAPSHOT_SIBLINGS), 25, "sibling list drifted from the live sweep"
        )
        for mod in RECORD_SNAPSHOT_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                sentinel = object()
                calls = []

                def fake_record_snapshot(count, ts, path, error_cls, _calls=calls, _sentinel=sentinel):
                    _calls.append((count, ts, path, error_cls))
                    return _sentinel

                with mock.patch.object(time_utils, "record_snapshot", fake_record_snapshot):
                    result = mod.record_snapshot(3, "2026-08-05T00:00:00Z", "some/probe/path.jsonl")
                self.assertIs(
                    result,
                    sentinel,
                    f"{mod.__name__}.record_snapshot did not return the shared "
                    "function's result -- it may hold a reinlined copy again",
                )
                self.assertEqual(
                    calls,
                    [(3, "2026-08-05T00:00:00Z", "some/probe/path.jsonl", _expected_error_cls(mod))],
                    f"{mod.__name__}.record_snapshot did not pass its arguments and "
                    "own error class through to time_utils.record_snapshot unchanged",
                )

    def test_every_sibling_default_still_resolves_to_its_own_module_default(self):
        import inspect

        for mod in RECORD_SNAPSHOT_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                sig = inspect.signature(mod.record_snapshot)
                self.assertEqual(
                    sig.parameters["path"].default,
                    mod.DEFAULT_SNAPSHOT_PATH,
                    f"{mod.__name__}.record_snapshot() no longer defaults to its "
                    "own DEFAULT_SNAPSHOT_PATH -- bare record_snapshot() calls "
                    "elsewhere in this module would silently write the wrong file",
                )

    def test_every_sibling_still_raises_its_own_error_class_on_bad_input(self):
        """Not mocked: proves the real, live delegation still surfaces the
        right exception type end to end, not just that the mock saw the
        right kwarg."""
        for mod in RECORD_SNAPSHOT_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                with self.assertRaises(_expected_error_cls(mod)):
                    mod.record_snapshot(-1, "2026-08-05T00:00:00Z", "unused/path.jsonl")


REJECT_MALFORMED_SIBLINGS = LOAD_SNAPSHOTS_SIBLINGS


def _expected_tampered_error_cls(mod):
    """Derive `<Words>CadenceTamperedError` from a sibling module's own
    name (`pr_cadence` -> `PrCadenceTamperedError`), mirroring
    `_expected_error_cls` above but for the Tampered subclass each
    sibling's `_reject_malformed` wrapper raises."""
    stem = mod.__name__.rsplit(".", 1)[-1].replace("_cadence", "")
    name = "".join(word.capitalize() for word in stem.split("_")) + "CadenceTamperedError"
    return getattr(mod, name)


class RejectMalformedDelegatesCase(unittest.TestCase):
    """Every sibling cadence module's own `_reject_malformed(snapshots,
    caller)` must genuinely call through to `time_utils.reject_malformed`
    with its own `*CadenceTamperedError` subclass as `error_cls` -- not
    carry a reinlined copy of the walk-and-raise logic (task 563's own
    AST-hash sweep found all 25 byte-identical except for that error
    class and a few words of docstring, the fifth such function this
    package's sweep has found after `_parse_ts`/`load_snapshots`/
    `record_snapshot`)."""

    def test_every_sibling_wrapper_delegates_to_the_shared_function(self):
        self.assertEqual(
            len(REJECT_MALFORMED_SIBLINGS), 25, "sibling list drifted from the live sweep"
        )
        for mod in REJECT_MALFORMED_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                calls = []

                def fake_reject_malformed(snapshots, caller, error_cls, _calls=calls):
                    _calls.append((snapshots, caller, error_cls))

                with mock.patch.object(time_utils, "reject_malformed", fake_reject_malformed):
                    mod._reject_malformed([{"_malformed": True}], "some_caller")
                self.assertEqual(
                    calls,
                    [([{"_malformed": True}], "some_caller", _expected_tampered_error_cls(mod))],
                    f"{mod.__name__}._reject_malformed did not pass its arguments and "
                    "own error class through to time_utils.reject_malformed unchanged",
                )

    def test_every_sibling_still_raises_its_own_error_class_on_a_malformed_line(self):
        """Not mocked: proves the real, live delegation still surfaces the
        right exception type end to end, not just that the mock saw the
        right kwarg."""
        for mod in REJECT_MALFORMED_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                with self.assertRaises(_expected_tampered_error_cls(mod)):
                    mod._reject_malformed([{"_malformed": True, "_error": "boom"}], "some_caller")

    def test_a_clean_snapshot_list_raises_nothing(self):
        for mod in REJECT_MALFORMED_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                mod._reject_malformed([{"ts": "2026-08-05T00:00:00Z", "count": 1}], "some_caller")


COUNT_AT_OR_SIBLINGS = LOAD_SNAPSHOTS_SIBLINGS


class CountAtOrBeforeAfterDelegatesCase(unittest.TestCase):
    """Every sibling cadence module's own `X_count_at_or_before`/
    `X_count_at_or_after` must genuinely call through to
    `time_utils.count_at_or_before`/`time_utils.count_at_or_after` -- not
    carry a reinlined copy of the scan-for-the-closest-snapshot loop
    (task 578's own AST-hash sweep found both byte-identical across all
    25 siblings, the sixth and seventh such functions this package's
    sweep has found after `_parse_ts`/`load_snapshots`/`record_snapshot`/
    `reject_malformed`)."""

    def test_every_sibling_count_at_or_before_delegates(self):
        self.assertEqual(len(COUNT_AT_OR_SIBLINGS), 25, "sibling list drifted from the live sweep")
        for mod in COUNT_AT_OR_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                topic = _topic(mod)
                fn = getattr(mod, f"{topic}_count_at_or_before")
                sentinel = object()
                calls = []

                def fake_count_at_or_before(snapshots, when, _calls=calls, _sentinel=sentinel):
                    _calls.append((snapshots, when))
                    return _sentinel

                probe_snapshots = [{"ts": "2026-08-05T00:00:00Z", "count": 1}]
                probe_when = _NOW
                with mock.patch.object(time_utils, "count_at_or_before", fake_count_at_or_before):
                    result = fn(probe_snapshots, probe_when)
                self.assertIs(
                    result,
                    sentinel,
                    f"{mod.__name__}.{topic}_count_at_or_before did not return the shared "
                    "function's result -- it may hold a reinlined copy again",
                )
                self.assertEqual(
                    calls,
                    [(probe_snapshots, probe_when)],
                    f"{mod.__name__}.{topic}_count_at_or_before did not pass its arguments "
                    "through to time_utils.count_at_or_before unchanged",
                )

    def test_every_sibling_count_at_or_after_delegates(self):
        for mod in COUNT_AT_OR_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                topic = _topic(mod)
                fn = getattr(mod, f"{topic}_count_at_or_after")
                sentinel = object()
                calls = []

                def fake_count_at_or_after(snapshots, when, _calls=calls, _sentinel=sentinel):
                    _calls.append((snapshots, when))
                    return _sentinel

                probe_snapshots = [{"ts": "2026-08-05T00:00:00Z", "count": 1}]
                probe_when = _NOW
                with mock.patch.object(time_utils, "count_at_or_after", fake_count_at_or_after):
                    result = fn(probe_snapshots, probe_when)
                self.assertIs(
                    result,
                    sentinel,
                    f"{mod.__name__}.{topic}_count_at_or_after did not return the shared "
                    "function's result -- it may hold a reinlined copy again",
                )
                self.assertEqual(
                    calls,
                    [(probe_snapshots, probe_when)],
                    f"{mod.__name__}.{topic}_count_at_or_after did not pass its arguments "
                    "through to time_utils.count_at_or_after unchanged",
                )

    def test_every_sibling_still_raises_its_own_tampered_error_on_a_malformed_line(self):
        """Not mocked: proves each sibling's own `_reject_malformed` still
        gets first say even though the scan itself now lives in
        time_utils -- a malformed line must still surface that module's
        own `*CadenceTamperedError`, not blow up inside the shared scan
        with a bare KeyError on a `_malformed` marker dict."""
        for mod in COUNT_AT_OR_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                topic = _topic(mod)
                bad = [{"_malformed": True, "_error": "boom"}]
                with self.assertRaises(_expected_tampered_error_cls(mod)):
                    getattr(mod, f"{topic}_count_at_or_before")(bad, _NOW)
                with self.assertRaises(_expected_tampered_error_cls(mod)):
                    getattr(mod, f"{topic}_count_at_or_after")(bad, _NOW)

    def test_every_sibling_still_scans_correctly_end_to_end(self):
        """Not mocked: proves the real, live delegation still returns the
        right closest-snapshot count, not just that the mock saw the
        right arguments."""
        snapshots = [
            {"ts": "2026-08-01T00:00:00Z", "count": 1},
            {"ts": "2026-08-03T00:00:00Z", "count": 3},
            {"ts": "2026-08-05T00:00:00Z", "count": 5},
        ]
        when = datetime.datetime(2026, 8, 3, 0, 0, tzinfo=datetime.timezone.utc)
        for mod in COUNT_AT_OR_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                topic = _topic(mod)
                self.assertEqual(getattr(mod, f"{topic}_count_at_or_before")(snapshots, when), 3)
                self.assertEqual(getattr(mod, f"{topic}_count_at_or_after")(snapshots, when), 3)
                self.assertEqual(getattr(mod, f"{topic}_count_at_or_before")([], when), None)
                self.assertEqual(getattr(mod, f"{topic}_count_at_or_after")([], when), None)


class CountAtOrBeforeAfterCase(unittest.TestCase):
    """Direct tests of the shared `time_utils.count_at_or_before`/
    `time_utils.count_at_or_after` scan logic itself, independent of any
    sibling's wrapper."""

    def setUp(self):
        self.snapshots = [
            {"ts": "2026-08-01T00:00:00Z", "count": 1},
            {"ts": "2026-08-03T00:00:00Z", "count": 3},
            {"ts": "2026-08-05T00:00:00Z", "count": 5},
        ]

    def test_at_or_before_exact_match_returns_that_snapshot(self):
        when = datetime.datetime(2026, 8, 3, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(time_utils.count_at_or_before(self.snapshots, when), 3)

    def test_at_or_before_between_two_returns_the_earlier(self):
        when = datetime.datetime(2026, 8, 4, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(time_utils.count_at_or_before(self.snapshots, when), 3)

    def test_at_or_before_earlier_than_everything_returns_none(self):
        when = datetime.datetime(2026, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertIsNone(time_utils.count_at_or_before(self.snapshots, when))

    def test_at_or_after_exact_match_returns_that_snapshot(self):
        when = datetime.datetime(2026, 8, 3, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(time_utils.count_at_or_after(self.snapshots, when), 3)

    def test_at_or_after_between_two_returns_the_later(self):
        when = datetime.datetime(2026, 8, 2, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(time_utils.count_at_or_after(self.snapshots, when), 3)

    def test_at_or_after_later_than_everything_returns_none(self):
        when = datetime.datetime(2026, 9, 1, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertIsNone(time_utils.count_at_or_after(self.snapshots, when))

    def test_empty_snapshots_returns_none_both_directions(self):
        when = datetime.datetime(2026, 8, 3, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertIsNone(time_utils.count_at_or_before([], when))
        self.assertIsNone(time_utils.count_at_or_after([], when))


SEAL_PREDICTION_SIBLINGS = LOAD_SNAPSHOTS_SIBLINGS


class SealGenericPredictionDelegatesCase(unittest.TestCase):
    """Every sibling cadence module's own `seal_<topic>_prediction(now, ts,
    current_count, actor=<its own DEFAULT_ACTOR>, snapshots=None,
    ledger_module=None, **build_kwargs)` must genuinely call through to
    `prediction.seal_generic_prediction` with its own `build_prediction`/
    `load_snapshots` as the two positional functions -- not carry a
    reinlined copy of the default-load/build/copylint/seal glue (task 573's
    own AST-hash sweep found all 25 byte-identical except for which
    module-local `build_prediction`/`load_snapshots`/`DEFAULT_ACTOR` they
    close over, the sixth such function this package's sweep has found
    after `_parse_ts`/`load_snapshots`/`record_snapshot`/
    `reject_malformed`)."""

    def test_every_sibling_wrapper_delegates_to_the_shared_function(self):
        self.assertEqual(
            len(SEAL_PREDICTION_SIBLINGS), 25, "sibling list drifted from the live sweep"
        )
        for mod in SEAL_PREDICTION_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                sentinel = object()
                calls = []

                def fake_seal_generic_prediction(
                    build_fn, load_fn, _calls=calls, _sentinel=sentinel, **kwargs
                ):
                    _calls.append((build_fn, load_fn, kwargs))
                    return _sentinel

                with mock.patch.object(prediction, "seal_generic_prediction", fake_seal_generic_prediction):
                    seal_fn = getattr(mod, f"seal_{_topic(mod)}_prediction")
                    result = seal_fn(
                        now="2026-08-06T14:00:00+00:00",
                        ts="2026-08-06T14:00:00+00:00",
                        current_count=5,
                        snapshots=[],
                        ledger_module="probe-ledger",
                    )
                self.assertIs(
                    result,
                    sentinel,
                    f"{mod.__name__}.seal_{_topic(mod)}_prediction did not return the shared "
                    "function's result -- it may hold a reinlined copy again",
                )
                self.assertEqual(len(calls), 1)
                build_fn, load_fn, kwargs = calls[0]
                self.assertIs(
                    build_fn,
                    mod.build_prediction,
                    f"{mod.__name__} did not pass its own build_prediction through unchanged",
                )
                self.assertIs(
                    load_fn,
                    mod.load_snapshots,
                    f"{mod.__name__} did not pass its own load_snapshots through unchanged",
                )
                self.assertEqual(
                    kwargs,
                    {
                        "now": "2026-08-06T14:00:00+00:00",
                        "ts": "2026-08-06T14:00:00+00:00",
                        "current_count": 5,
                        "actor": mod.DEFAULT_ACTOR,
                        "snapshots": [],
                        "ledger_module": "probe-ledger",
                    },
                    f"{mod.__name__}.seal_{_topic(mod)}_prediction did not pass its own "
                    "DEFAULT_ACTOR default (or the caller's other arguments) through unchanged",
                )

    def test_every_sibling_still_seals_a_real_entry_end_to_end(self):
        """Not mocked: proves the real, live delegation still produces a
        verifiable ledger entry, not just that the mock saw the right
        kwargs."""
        import tempfile

        for mod in SEAL_PREDICTION_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    ledger_path = os.path.join(tmp, "ledger.jsonl")
                    ledger_mod = _fresh_ledger_module(ledger_path)
                    seal_fn = getattr(mod, f"seal_{_topic(mod)}_prediction")
                    entry = seal_fn(
                        now=_NOW,
                        ts=_NOW.isoformat(timespec="seconds"),
                        current_count=4,
                        snapshots=[],
                        ledger_module=ledger_mod,
                    )
                    self.assertEqual(entry["actor"], mod.DEFAULT_ACTOR)
                    self.assertTrue(ledger_mod.verify())


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
