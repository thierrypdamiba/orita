"""Tests for the Fencepost Report — the daily dispatch, not the tablet.

A report names one gap (or none) and never the coincidence tail. These tests
go red if the report starts padding itself with the ranking noise the tablet
is for, or drops the line the whole arc turns on.
"""
from __future__ import annotations

import ast
import inspect
import sys
from datetime import datetime, timezone
from pathlib import Path

from seam_engine import ledger, report

# report.py's own docstring makes a safety claim about `suggest_move` (ROADMAP.md
# #140, retrya): "it holds no credential, calls no tool, and fires nothing. Read
# it end to end and you will find no verb it can act on." The wording tests above
# check what a rendered move SAYS; these check what the module's own imports
# actually ARE -- the mechanism the claim is about, not just its prose.

# report.py's only real, already-audited local dependencies (their own modules
# are pure-local file I/O, no network, no credential -- ledger.py/streak.py/
# wall.py never import anything outside this same allow-list either).
_ALLOWED_LOCAL_IMPORTS = frozenset({"seam_engine", "seam_engine.ledger", "seam_engine.streak", "seam_engine.wall"})

# Anything reaching a credential, the network, a subprocess, or an Arcade/MCP
# tool call would be a violation of the claim -- named here once, checked
# against the module's real source text and, via the mutation test below,
# proven to actually bite rather than merely exist.
_FORBIDDEN_NAMES = (
    "requests",
    "httpx",
    "urllib",
    "subprocess",
    "socket",
    "os.environ",
    "getenv",
    "arcade",
    "mcp",
)


def _top_level_imports(source: str) -> set[str]:
    """Every module name `source` imports, structurally, via `ast` -- never a
    second hand-typed copy of report.py's own import list."""
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module)
    return found


def _stdlib_or_allowed(module_name: str) -> bool:
    root = module_name.split(".", 1)[0]
    if root == "__future__":
        return True
    if module_name in _ALLOWED_LOCAL_IMPORTS:
        return True
    return root in sys.stdlib_module_names


def _forbidden_names_in(source: str) -> list[str]:
    return [name for name in _FORBIDDEN_NAMES if name in source]


def _sealed(*, primary: bool, recorded: int, tail_n: int = 2) -> dict:
    p = None
    if primary:
        p = {
            "slug": "milestone-unannounced",
            "headline": "Milestone-level work shipped but never reached the sky",
            "detail": "3 milestone commit(s), none echoed in a post.",
            "confidence": 0.85,
            "evidence": [f"https://github.com/x/orita/commit/{i:07d}" for i in range(3)],
        }
    tail = [{"slug": f"coincidence-{i}", "confidence": 0.5, "label": "coincidence"} for i in range(tail_n)]
    return {
        "date": "2026-07-12",
        "generated_at": "2026-07-12T11:38:10+00:00",
        "repo": "x/orita",
        "primary_gap": p,
        "tail": tail,
        "fenceposts_recorded_total": recorded,
    }


def _at(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, tzinfo=timezone.utc)


# --- one gap, never the tail --------------------------------------------------


def test_report_names_the_one_gap():
    text = report.render_report(_sealed(primary=True, recorded=1))
    assert "Milestone-level work" in text
    assert "confidence 0.85" in text


def test_report_never_shows_the_coincidence_tail():
    text = report.render_report(_sealed(primary=True, recorded=1, tail_n=3))
    assert "coincidence-0" not in text
    assert "coincidence-1" not in text


def test_report_caps_evidence_at_three_links():
    text = report.render_report(_sealed(primary=True, recorded=1))
    assert text.count("github.com/x/orita/commit") <= 3


# --- the line and the count are load-bearing ----------------------------------


def test_report_always_carries_the_line():
    assert report.THE_LINE in report.render_report(_sealed(primary=True, recorded=1))
    assert report.THE_LINE in report.render_report(_sealed(primary=False, recorded=0))


def test_wall_reads_one_behind_recorded():
    text = report.render_report(_sealed(primary=True, recorded=3))
    assert "The wall reads 2" in text
    assert "3 fenceposts named" in text


def test_wall_never_goes_negative_at_zero_recorded():
    text = report.render_report(_sealed(primary=False, recorded=0))
    assert "The wall reads 0" in text


# --- an honest quiet day -------------------------------------------------------


def test_no_primary_says_nothing_cleared_the_bar():
    text = report.render_report(_sealed(primary=False, recorded=0))
    assert "Nothing cleared the bar" in text
    assert "milestone-unannounced" not in text


# --- rendered from a live ledger, not a hand-built dict -----------------------


def test_render_latest_reads_the_real_ledger(tmp_path: Path):
    ledger.append_scan(
        {
            "generated_at": "2026-07-12T11:38:10+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "Milestone-level work shipped but never reached the sky",
                "detail": "3 milestone commit(s), none echoed in a post.",
                "confidence": 0.85,
                "evidence": ["https://github.com/x/orita/commit/0000001"],
            },
            "tail": [],
            "excluded": [],
        },
        now=_at(2026, 7, 12),
        base=tmp_path,
    )

    text = report.render_latest(tmp_path)
    assert "# Fencepost Report — 2026-07-12" in text
    assert "Milestone-level work" in text
    assert "1 fencepost named" in text
    assert "The wall reads 0" in text
    assert report.THE_LINE in text


def test_render_latest_on_empty_ledger_raises(tmp_path: Path):
    try:
        report.render_latest(tmp_path)
        assert False, "expected ValueError on an empty ledger"
    except ValueError:
        pass


def test_render_latest_raises_named_error_not_keyerror_when_tip_is_malformed(tmp_path: Path):
    # render_latest() used to read `records[-1]["sealed"]` straight off the
    # ledger tip -- a malformed marker dict (ledger.py's own tampering
    # discipline, task 205) carries no "sealed" key, so a hand-edited/
    # truncated tablet crashed this with a bare `KeyError: 'sealed'`
    # instead of the named `ledger.LedgerTamperedError` every other tip
    # reader in this codebase already raises.
    ledger.append_scan(
        {
            "generated_at": "2026-07-12T11:38:10+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "x",
                "detail": "x",
                "confidence": 0.85,
                "evidence": [],
            },
            "tail": [],
            "excluded": [],
        },
        now=_at(2026, 7, 12),
        base=tmp_path,
    )
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    broken = tablet.read_text().replace('"confidence": 0.85', '"confidence": 0.85,,')
    tablet.write_text(broken)

    try:
        report.render_latest(tmp_path)
        assert False, "expected LedgerTamperedError, not a bare KeyError"
    except ledger.LedgerTamperedError as e:
        assert "malformed" in str(e)


def test_main_with_no_args_raises_named_error_not_keyerror_when_tip_is_malformed(tmp_path: Path):
    # Same bug, reached through the CLI's no-arg branch (`main()`'s
    # `sealed = records[-1]["sealed"]`), the exact path the daily Action
    # runs (`python3 -m seam_engine.report --write`, seam-scan.yml).
    ledger.append_scan(
        {
            "generated_at": "2026-07-12T11:38:10+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "x",
                "detail": "x",
                "confidence": 0.85,
                "evidence": [],
            },
            "tail": [],
            "excluded": [],
        },
        now=_at(2026, 7, 12),
        base=tmp_path,
    )
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    broken = tablet.read_text().replace('"confidence": 0.85', '"confidence": 0.85,,')
    tablet.write_text(broken)

    try:
        report.main(["--ledger-base", str(tmp_path)])
        assert False, "expected LedgerTamperedError, not a bare KeyError"
    except ledger.LedgerTamperedError as e:
        assert "malformed" in str(e)


# --- the single hand-off: one "your move" line, never an action fired ---------


def test_report_carries_exactly_one_your_move_line():
    text = report.render_report(_sealed(primary=True, recorded=1))
    assert text.count("**Your move.**") == 1


def test_report_carries_a_your_move_line_even_on_a_quiet_day():
    text = report.render_report(_sealed(primary=False, recorded=0))
    assert text.count("**Your move.**") == 1
    assert report.suggest_move(None) in text


def test_your_move_is_phrased_as_the_readers_verb_not_fenceposts():
    # The whole point of the hand-off: Fencepost never claims to have DONE
    # the action, only to have found the gap and named the reader's move.
    for primary_gap in (
        None,
        {"headline": "Milestone-level work shipped but never reached @oritatown", "detail": ""},
        {"headline": "The invite never made it onto your Calendar", "detail": ""},
        {"headline": "An entirely novel kind of gap nobody wrote a rule for", "detail": ""},
    ):
        move = report.suggest_move(primary_gap)
        lowered = move.lower()
        # No first-person-plural claim of having acted or being about to.
        for forbidden in ("we posted", "we added", "we closed", "we'll", "fencepost posted", "fencepost added"):
            assert forbidden not in lowered
        assert "fencepost" not in lowered.split(".")[0]  # the first clause is the reader's verb, not Fencepost's


def test_suggest_move_is_deterministic():
    gap = {"headline": "Release 'v1' shipped but never reached @oritatown", "detail": "x"}
    assert report.suggest_move(gap) == report.suggest_move(gap)


def test_suggest_move_matches_calendar_gaps_to_a_calendar_verb():
    move = report.suggest_move({"headline": "The invite never made it onto your Calendar", "detail": ""})
    assert "add it to your calendar" in move.lower()


def test_suggest_move_matches_x_gaps_to_a_post_verb():
    move = report.suggest_move(
        {"headline": "Release 'v1' shipped but never reached @oritatown", "detail": ""}
    )
    assert "post about it" in move.lower()


def test_suggest_move_falls_back_for_an_unrecognized_gap_kind():
    move = report.suggest_move({"headline": "Some future gap kind", "detail": "no known keyword here"})
    assert move == report._DEFAULT_MOVE


def test_suggest_move_on_no_gap_is_the_fixed_quiet_day_line():
    assert report.suggest_move(None) == report._NO_GAP_MOVE


def test_your_move_line_reads_correctly_from_a_live_ledger(tmp_path: Path):
    ledger.append_scan(
        {
            "generated_at": "2026-07-12T11:38:10+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "Milestone-level work shipped but never reached @oritatown",
                "detail": "3 milestone commit(s), none echoed in a post.",
                "confidence": 0.85,
                "evidence": ["https://github.com/x/orita/commit/0000001"],
            },
            "tail": [],
            "excluded": [],
        },
        now=_at(2026, 7, 12),
        base=tmp_path,
    )

    text = report.render_latest(tmp_path)
    assert text.count("**Your move.**") == 1
    assert "post about it" in text.lower()


# --- the docstring's safety claim, checked structurally, not just in prose ----


def test_report_module_imports_nothing_but_stdlib_and_its_own_audited_locals():
    source = inspect.getsource(report)
    imports = _top_level_imports(source)
    assert imports, "report.py must import something for this test to mean anything"
    violations = {name for name in imports if not _stdlib_or_allowed(name)}
    assert not violations, f"report.py imports beyond stdlib/its own audited locals: {violations}"


def test_report_module_source_names_no_network_or_credential_capable_symbol():
    source = inspect.getsource(report)
    assert _forbidden_names_in(source) == []


def test_the_same_import_checker_flags_a_synthetic_credential_import():
    # Mutation-based hand-verification (task 135/136/137/138's own discipline):
    # the SAME extracted checker, run against a deliberately mutated copy of
    # the real source, must disagree -- proving it actually bites rather than
    # merely existing. The real, unmutated file is proven clean above.
    real_source = inspect.getsource(report)
    mutated = "import requests\n" + real_source
    imports = _top_level_imports(mutated)
    violations = {name for name in imports if not _stdlib_or_allowed(name)}
    assert violations == {"requests"}


def test_the_same_forbidden_name_checker_flags_a_synthetic_socket_reference():
    real_source = inspect.getsource(report)
    mutated = real_source + "\n# socket.socket() would be the violation here\n"
    assert "socket" in _forbidden_names_in(mutated)
    # And the real, unmutated file still reads clean against the same function.
    assert "socket" not in _forbidden_names_in(real_source)
