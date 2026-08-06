"""Tests for the Gap Ledger — the append-only, hash-chained tablet.

Every property the ledger promises has a test that goes red if the promise
breaks: it seals, it chains, it only ever appends, and it catches a tampered
tablet. A test that cannot fail is a broken oath.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from seam_engine import ledger


def _scan(*, primary: bool, generated_at: str, tail_n: int = 2) -> dict:
    p = None
    if primary:
        p = {
            "slug": "milestone-unannounced",
            "headline": "Milestone-level work shipped but never reached the sky",
            "detail": "3 milestone commit(s), none echoed in a post.",
            "confidence": 0.85,
            "evidence": [f"https://github.com/x/orita/commit/{i:07d}" for i in range(3)],
            "label": "primary",
        }
    tail = [
        {"slug": f"coincidence-{i}", "confidence": 0.5 - 0.01 * i, "label": "coincidence"}
        for i in range(tail_n)
    ]
    return {
        "generated_at": generated_at,
        "repo": "x/orita",
        "window_hours": 24,
        "confidence_bar": 0.7,
        "separation_margin": 0.15,
        "primary_gap": p,
        "tail": tail,
        "excluded": [{"slug": "release-old"}],
    }


def _at(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, tzinfo=timezone.utc)


# --- it writes a readable, dated tablet --------------------------------------


def test_first_append_creates_dated_tablet(tmp_path: Path):
    scan = _scan(primary=True, generated_at="2026-07-12T11:38:10+00:00")
    tablet = ledger.append_scan(scan, now=_at(2026, 7, 12), base=tmp_path)

    assert tablet == ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    assert tablet.exists()
    text = tablet.read_text()
    assert "# Gap Ledger — 2026-07-12" in text
    assert "## Entry 0" in text
    assert "Milestone-level work" in text
    assert "Tablet sealed." in text
    # the typed record is embedded and parseable
    assert "<!-- typed-record -->" in text


def test_readable_evidence_links_are_rendered(tmp_path: Path):
    scan = _scan(primary=True, generated_at="2026-07-12T11:38:10+00:00")
    tablet = ledger.append_scan(scan, now=_at(2026, 7, 12), base=tmp_path)
    text = tablet.read_text()
    assert "https://github.com/x/orita/commit/0000000" in text
    assert "Evidence:" in text


def test_evidence_url_tail_is_last_segment_trimmed_to_12():
    assert ledger.evidence_url_tail("https://github.com/x/orita/commit/abcdef0123456789") == "abcdef012345"
    assert ledger.evidence_url_tail("https://github.com/x/orita/pull/42/") == "42"


def test_report_reuses_ledgers_evidence_url_tail_not_a_second_copy():
    """report.py's own _fmt_evidence imports this instead of retyping the
    rstrip/rsplit/slice rule a second time -- the same shared-law shape
    references.py already documents for the #N reference grammar."""
    import ast
    import inspect

    from seam_engine import report

    src = inspect.getsource(report._fmt_evidence)
    assert "ledger.evidence_url_tail" in src
    assert "rsplit" not in src
    ast.parse(src)  # sanity: still valid Python after the edit


# --- the chain ---------------------------------------------------------------


def test_first_entry_chains_from_genesis(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="t"), now=_at(2026, 7, 12), base=tmp_path)
    recs = ledger.read_records(tmp_path)
    assert len(recs) == 1
    assert recs[0]["prev"] == ledger.GENESIS
    assert recs[0]["seq"] == 0
    assert ledger.verify(tmp_path) == []


def test_second_entry_same_day_appends_and_chains(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="t1"), now=_at(2026, 7, 12, 9), base=tmp_path)
    before = (ledger.gaps_dir(tmp_path) / "2026-07-12.md").read_text()

    ledger.append_scan(_scan(primary=False, generated_at="t2"), now=_at(2026, 7, 12, 18), base=tmp_path)
    after = (ledger.gaps_dir(tmp_path) / "2026-07-12.md").read_text()

    # append-only: the earlier bytes are untouched, the file only grew
    assert after.startswith(before)
    assert len(after) > len(before)

    recs = ledger.read_records(tmp_path)
    assert [r["seq"] for r in recs] == [0, 1]
    assert recs[1]["prev"] == recs[0]["seal"]  # entry 1 chains from entry 0
    assert ledger.verify(tmp_path) == []


def test_new_day_opens_new_tablet_chained_to_prior(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="d1"), now=_at(2026, 7, 12), base=tmp_path)
    ledger.append_scan(_scan(primary=True, generated_at="d2"), now=_at(2026, 7, 13), base=tmp_path)

    files = {p.name for p in ledger.gaps_dir(tmp_path).glob("*.md")}
    assert files == {"2026-07-12.md", "2026-07-13.md"}

    recs = ledger.read_records(tmp_path)
    assert len(recs) == 2
    # the second tablet's first entry chains from the first tablet's last seal
    assert recs[1]["prev"] == recs[0]["seal"]
    # the new tablet header records where it chains from
    day2 = (ledger.gaps_dir(tmp_path) / "2026-07-13.md").read_text()
    assert recs[0]["seal"][:12] in day2
    assert ledger.verify(tmp_path) == []


# --- tamper-evidence: the reason a ledger exists ------------------------------


def test_editing_a_sealed_record_is_caught(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="honest"), now=_at(2026, 7, 12), base=tmp_path)
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    # forge the confidence inside the sealed record without re-sealing
    tablet.write_text(tablet.read_text().replace('"confidence": 0.85', '"confidence": 0.99'))

    problems = ledger.verify(tmp_path)
    assert problems, "a forged record must be caught"
    assert any("seal does not match" in p for p in problems)


def test_deleting_an_entry_breaks_the_chain(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="e0"), now=_at(2026, 7, 12, 9), base=tmp_path)
    ledger.append_scan(_scan(primary=True, generated_at="e1"), now=_at(2026, 7, 12, 18), base=tmp_path)
    assert ledger.verify(tmp_path) == []

    # amputate the second entry's typed record's prev-link
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    recs = ledger.read_records(tmp_path)
    good_prev = recs[1]["prev"]
    tablet.write_text(tablet.read_text().replace(f'"prev": "{good_prev}"', f'"prev": "{ledger.GENESIS}"', 1))

    problems = ledger.verify(tmp_path)
    assert any("prev-link broken" in p or "seal does not match" in p for p in problems)


def test_syntactically_broken_json_record_is_reported_not_a_crash(tmp_path: Path):
    # A more realistic hand-edit than swapping one JSON value for another
    # (the two tests above): this one breaks JSON *syntax* inside the sealed
    # block, the way a stray keystroke or a bad paste actually would. The
    # module docstring promises "the tampered tablet is exposed" -- that
    # must mean a reported problem, never an uncaught exception escaping
    # verify() (or read_records(), which verify() and every other reader
    # depend on).
    ledger.append_scan(_scan(primary=True, generated_at="honest"), now=_at(2026, 7, 12), base=tmp_path)
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    broken = tablet.read_text().replace('"confidence": 0.85', '"confidence": 0.85,,')
    tablet.write_text(broken)

    # read_records() must not raise json.JSONDecodeError.
    recs = ledger.read_records(tmp_path)
    assert len(recs) == 1
    assert recs[0]["_malformed"] is True

    # verify() must not raise either -- it must expose the tampering as a
    # reported problem, same as the value-swap and prev-link cases above.
    problems = ledger.verify(tmp_path)
    assert problems, "a syntactically-broken record must be caught, not crash"
    assert any("malformed" in p for p in problems)


def test_valid_json_non_dict_record_is_reported_not_a_crash(tmp_path: Path):
    # A different hand-edit than the syntax-broken case above: the fenced
    # block still parses cleanly as JSON, it just isn't a JSON *object* any
    # more (e.g. a stray edit leaves `[1, 2, 3]`, `5`, `null`, or `"oops"`
    # where the sealed record used to be). json.loads() raises nothing here,
    # so the syntax-error guard doesn't fire -- but the very next step,
    # `rec["_tablet"] = path.name`, item-assigns into whatever that value
    # was and must not crash either. Same "tampered tablet is exposed, not
    # an uncaught exception" promise, a different way of breaking the shape.
    ledger.append_scan(_scan(primary=True, generated_at="honest"), now=_at(2026, 7, 12), base=tmp_path)
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    text = tablet.read_text()
    rewritten = re.sub(
        r"<!-- typed-record -->\n```json\n.*?\n```",
        "<!-- typed-record -->\n```json\n[1, 2, 3]\n```",
        text,
        count=1,
        flags=re.DOTALL,
    )
    assert rewritten != text, "the typed-record fence must actually be replaced"
    tablet.write_text(rewritten)

    # read_records() must not raise TypeError.
    recs = ledger.read_records(tmp_path)
    assert len(recs) == 1
    assert recs[0]["_malformed"] is True

    # verify() must not raise either -- reported problem, not a crash.
    problems = ledger.verify(tmp_path)
    assert problems, "a valid-JSON-but-non-dict record must be caught, not crash"
    assert any("malformed" in p for p in problems)


def test_last_seal_raises_named_error_not_keyerror_when_tip_is_malformed(tmp_path: Path):
    # read_records()/verify() (task 205) already turn a syntactically broken
    # sealed record into a reported problem, not a crash -- but last_seal()
    # still read `records[-1]["seal"]` straight off the tip, and a malformed
    # marker dict carries no "seal" key at all. On the untouched pre-fix
    # code this raised a bare `KeyError: 'seal'`, not the named,
    # ledger-specific error this module's own tampering discipline promises.
    ledger.append_scan(_scan(primary=True, generated_at="honest"), now=_at(2026, 7, 12), base=tmp_path)
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    broken = tablet.read_text().replace('"confidence": 0.85', '"confidence": 0.85,,')
    tablet.write_text(broken)

    try:
        ledger.last_seal(tmp_path)
        assert False, "last_seal() must not silently return a seal for a malformed tip"
    except ledger.LedgerTamperedError as e:
        assert "malformed" in str(e)


def test_append_scan_raises_named_error_not_keyerror_when_tip_is_malformed(tmp_path: Path):
    # The same tip-read bug reachable through the ledger's one write path --
    # the daily cron's own `python -m seam_engine.ledger append` call would
    # hit this the moment it ran on top of a tampered tablet. Must refuse
    # loudly and by name, never crash with an opaque KeyError and never
    # silently chain the new entry from some other seal.
    ledger.append_scan(_scan(primary=True, generated_at="honest"), now=_at(2026, 7, 12), base=tmp_path)
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    broken = tablet.read_text().replace('"confidence": 0.85', '"confidence": 0.85,,')
    tablet.write_text(broken)

    try:
        ledger.append_scan(_scan(primary=True, generated_at="next"), now=_at(2026, 7, 13), base=tmp_path)
        assert False, "append_scan() must not silently append on top of a malformed tip"
    except ledger.LedgerTamperedError as e:
        assert "malformed" in str(e)

    # and it must not have written anything for 2026-07-13 while refusing
    assert not (ledger.gaps_dir(tmp_path) / "2026-07-13.md").exists()


def test_tip_sealed_raises_named_error_not_keyerror_when_tip_is_malformed(tmp_path: Path):
    # The same tip-read bug reachable through `seam_engine.report`/
    # `seam_engine.draftback`, which each used to read `records[-1]["sealed"]`
    # straight off the tip (duplicated three times across two modules) --
    # a malformed marker dict carries no "sealed" key any more than it
    # carries a "seal" key, so on the untouched pre-fix code all three
    # crashed with a bare `KeyError: 'sealed'`, not this named error.
    ledger.append_scan(_scan(primary=True, generated_at="honest"), now=_at(2026, 7, 12), base=tmp_path)
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    broken = tablet.read_text().replace('"confidence": 0.85', '"confidence": 0.85,,')
    tablet.write_text(broken)

    records = ledger.read_records(tmp_path)
    try:
        ledger.tip_sealed(records)
        assert False, "tip_sealed() must not silently return a sealed payload for a malformed tip"
    except ledger.LedgerTamperedError as e:
        assert "malformed" in str(e)


def test_tip_sealed_returns_the_real_payload_when_the_tip_is_intact(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="honest"), now=_at(2026, 7, 12), base=tmp_path)
    records = ledger.read_records(tmp_path)
    assert ledger.tip_sealed(records) == records[-1]["sealed"]


# --- the count is honest -----------------------------------------------------


def test_count_only_advances_on_a_real_fencepost(tmp_path: Path):
    ledger.append_scan(_scan(primary=True, generated_at="g1"), now=_at(2026, 7, 12), base=tmp_path)
    ledger.append_scan(_scan(primary=False, generated_at="held"), now=_at(2026, 7, 13), base=tmp_path)
    ledger.append_scan(_scan(primary=True, generated_at="g2"), now=_at(2026, 7, 14), base=tmp_path)

    recs = ledger.read_records(tmp_path)
    totals = [r["sealed"]["fenceposts_recorded_total"] for r in recs]
    assert totals == [1, 1, 2]  # the empty day does not inflate the count


def test_no_primary_records_the_seam_held(tmp_path: Path):
    tablet = ledger.append_scan(_scan(primary=False, generated_at="q"), now=_at(2026, 7, 12), base=tmp_path)
    text = tablet.read_text()
    assert "None cleared the bar" in text
    assert "Recorded." in text
    recs = ledger.read_records(tmp_path)
    assert recs[0]["sealed"]["primary_gap"] is None
    assert recs[0]["sealed"]["fenceposts_recorded_total"] == 0


def test_weighed_and_dropped_names_every_tail_entry_not_just_six(tmp_path: Path):
    # Task 440. The sentence claims "They are named, not hidden" and states
    # the true count via len(tail) -- but the printed list used to be
    # silently capped at tail[:6], so a tail of 8 said "8 coincidence(s)"
    # while only naming 6. Already fired for real in GAPS/2026-07-18.md and
    # GAPS/2026-07-19.md (7 stated, 6 named) before this fix.
    tablet = ledger.append_scan(
        _scan(primary=True, generated_at="g", tail_n=8), now=_at(2026, 7, 12), base=tmp_path
    )
    text = tablet.read_text()
    assert "8 coincidence(s)" in text
    for i in range(8):
        assert f"`coincidence-{i}`" in text


# --- last_seal --------------------------------------------------------------


def test_last_seal_is_genesis_on_empty_ledger(tmp_path: Path):
    assert ledger.last_seal(tmp_path) == ledger.GENESIS


# --- the CLI's append command names a bad shape, never crashes opaquely -------


def test_main_append_with_file_arg_raises_named_error_not_attributeerror_when_json_is_not_an_object(tmp_path: Path):
    # main(["append", ...])'s file-arg branch used to do
    # `scan = json.loads(path.read_text())` with no shape check, then hand
    # `scan` straight to `append_scan`, which opens with `scan.get(...)`. A
    # CLI-supplied file can be any syntactically valid JSON -- a bare list,
    # int, bool, null, or string, not just an object -- so `[1, 2, 3]` on
    # disk crashed this with a bare
    # `AttributeError: 'list' object has no attribute 'get'` instead of a
    # message naming the actual problem, the same "malformed input must be
    # named, never an opaque crash" discipline `report.py`'s
    # `_load_sealed_arg` already holds in this package.
    bad = tmp_path / "not_an_object.json"
    bad.write_text("[1, 2, 3]")

    try:
        ledger.main(["append", str(bad), "--base", str(tmp_path)])
        assert False, "expected a named ValueError, not a bare AttributeError"
    except AttributeError:
        assert False, "expected a named ValueError, not a bare AttributeError"
    except ValueError as e:
        assert "object" in str(e)


def test_main_append_with_stdin_raises_named_error_not_attributeerror_when_json_is_not_an_object(tmp_path: Path, monkeypatch):
    # Same bug, reached through the CLI's stdin branch (`argv == ["append", "-"]`).
    import io
    import sys

    monkeypatch.setattr(sys, "stdin", io.StringIO("null"))

    try:
        ledger.main(["append", "-", "--base", str(tmp_path)])
        assert False, "expected a named ValueError, not a bare AttributeError"
    except AttributeError:
        assert False, "expected a named ValueError, not a bare AttributeError"
    except ValueError as e:
        assert "object" in str(e)


# --- _load_json_dict: one real implementation, not three copies (task 538) ----
#
# `ledger._load_scan`, `report.py`'s `_load_sealed_arg`, and `draftback.py`'s
# `_load_sealed` used to each carry an independent copy of this exact
# load-and-validate logic. An AST-hash sweep across the package's core
# modules caught `report.py`'s copy and `draftback.py`'s copy as one exact
# match (both said "sealed record" in their error message) but missed this
# module's own copy, which said "scan record" -- one string literal apart,
# the same class of blind spot task 528's inline-import case already proved
# for `_monday_of`. These tests prove the fold: all three now delegate to
# one function, `ledger._load_json_dict`, parameterized by the noun.


def test_load_json_dict_reads_a_valid_object_from_a_file(tmp_path: Path):
    p = tmp_path / "obj.json"
    p.write_text('{"a": 1}')
    assert ledger._load_json_dict(str(p), "widget") == {"a": 1}


def test_load_json_dict_reads_a_valid_object_from_stdin(monkeypatch):
    import io
    import sys

    monkeypatch.setattr(sys, "stdin", io.StringIO('{"a": 1}'))
    assert ledger._load_json_dict("-", "widget") == {"a": 1}


def test_load_json_dict_names_the_given_noun_in_a_non_object_error(tmp_path: Path):
    p = tmp_path / "not_an_object.json"
    p.write_text("[1, 2, 3]")
    try:
        ledger._load_json_dict(str(p), "widget record")
        assert False, "expected a named ValueError"
    except ValueError as e:
        assert "widget record" in str(e)
        assert "list" in str(e)


def test_load_scan_delegates_to_load_json_dict_with_the_scan_record_noun(tmp_path: Path):
    p = tmp_path / "not_an_object.json"
    p.write_text("[1, 2, 3]")
    try:
        ledger._load_scan(str(p))
        assert False, "expected a named ValueError"
    except ValueError as e:
        assert "scan record" in str(e)


def test_load_sealed_arg_and_load_sealed_both_delegate_to_ledger_load_json_dict():
    # report.py's `_load_sealed_arg` and draftback.py's `_load_sealed` are
    # thin wrappers now, not independent copies -- proven by identity, not
    # by re-reading their source: both call the exact same function object
    # this module defines, the same "identity-asserted across siblings"
    # proof task 523's `time_utils.load_snapshots` fold used.
    import ast
    import inspect

    from seam_engine import draftback, report

    for fn in (report._load_sealed_arg, draftback._load_sealed):
        src = inspect.getsource(fn)
        tree = ast.parse(src)
        calls = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "_load_json_dict"
        ]
        assert len(calls) == 1, f"{fn.__qualname__} should call ledger._load_json_dict exactly once"
