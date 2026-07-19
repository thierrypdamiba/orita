"""Doctrine tests: the public-facing consent artifact must never drift from

the code that actually gates on it. `.github/ISSUE_TEMPLATE/point-fencepost.md`
is where a real human types their scope confirm; `consent.REQUIRED_SCOPES` is
what `enforce_consent_gate` actually checks it against. If the table on the
issue template ever falls out of sync with the code, a human could type a
"correct" confirm straight off the template and still get blocked — the
worst possible failure for a consent flow, since it makes the gate look
broken rather than working as sworn. This file fails red the day that
happens, the same discipline `test_connect_doctrine.py` holds
`READ_ONLY_CAPABILITIES` to.

Task 136 adds a second, older drift this file never checked. `consent.py`'s
own comment on `REQUIRED_SCOPES` says it is "mirrored verbatim from
SCOPES.md's 'Fencepost uses' column. Not paraphrased... If SCOPES.md ever
grows a new toolkit, this dict grows with it or a consent for that toolkit
can never pass" — a direct claim about `fencepost/SCOPES.md`, the actual
Read-Only Oath the whole gate exists to enforce. Every test above this
point proves `REQUIRED_SCOPES` agrees with the issue template — a SECOND
hand-typed copy of the same list. None of them ever read SCOPES.md itself.
Two hand-typed copies agreeing with each other says nothing about whether
either one still agrees with the source both claim to mirror; SCOPES.md
could gain, drop, or rename a scope on its own table and every test in this
file would keep passing while the gate quietly checked a confirm against
scopes the Oath no longer swears to (or refused one the Oath grants). The
tests below parse SCOPES.md's real table structurally and check the claim
for the first time — the same class of doc-vs-code drift tasks 130, 131,
133, and 135 already found and closed, one file over, aimed here at last.
"""
from __future__ import annotations

import re
from pathlib import Path

from seam_engine.consent import REQUIRED_SCOPES

REPO_ROOT = Path(__file__).resolve().parents[3]  # .../orita
TEMPLATE = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "point-fencepost.md"
FENCEPOST_ROOT = Path(__file__).resolve().parents[2]  # .../orita/fencepost
SCOPES_MD = FENCEPOST_ROOT / "SCOPES.md"
SCAN_PY = FENCEPOST_ROOT / "seam_engine" / "src" / "seam_engine" / "scan.py"

# Matches one three-cell markdown table row (`| a | b | c |`), one line at a
# time — re.MULTILINE is load-bearing here (task 135's own buildlog entry
# records shipping a row regex missing exactly this flag, which silently
# matched zero rows; that mistake is not repeated here).
_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", re.MULTILINE)


def _template_text() -> str:
    assert TEMPLATE.exists(), f"missing {TEMPLATE} — task 9's intent-forcing template must still exist"
    return TEMPLATE.read_text(encoding="utf-8")


def _scopes_md_text() -> str:
    assert SCOPES_MD.exists(), f"missing {SCOPES_MD} — the Read-Only Oath itself must still exist"
    return SCOPES_MD.read_text(encoding="utf-8")


def _normalize_toolkit_name(raw: str) -> str:
    """"Gmail (v0.2)" -> "gmail"; "Google Calendar (v0.2)" -> "google_calendar" —
    matches `consent.REQUIRED_SCOPES`'s own key convention (lowercase, spaces
    to underscores). The "(v0.2)" suffix is stripped because it labels the
    doc row's maturity, not the toolkit's identity — `consent.py` has no
    separate "v0.2" toolkit key and was never meant to.
    """
    name = re.sub(r"\s*\(v0\.2\)\s*$", "", raw.strip())
    return name.lower().replace(" ", "_")


def _parse_toolkit_table(text: str) -> dict[str, frozenset[str]]:
    """Structurally parse SCOPES.md's "Fencepost uses" column — the exact
    section `consent.REQUIRED_SCOPES`'s own comment names as its source.
    Isolated to the "Concretely, on the toolkits in use:" table only; the
    later "Every connected app, accounted for" table (task 135) is a
    different shape (app_id/status, not toolkit/scopes) and must not be
    parsed as one of these rows.
    """
    start_marker = "Concretely, on the toolkits in use:"
    if start_marker not in text:
        return {}
    start = text.index(start_marker)
    end_marker = "**WIP note"
    end = text.index(end_marker, start) if end_marker in text[start:] else len(text)
    table_text = text[start:end]
    rows: dict[str, frozenset[str]] = {}
    for toolkit_cell, uses_cell, _never_cell in _ROW_RE.findall(table_text):
        toolkit_cell = toolkit_cell.strip()
        if not toolkit_cell or set(toolkit_cell) <= {"-"}:
            continue  # the `|--|--|--|` separator row
        if toolkit_cell.lower() == "toolkit":
            continue  # the header row itself
        key = _normalize_toolkit_name(toolkit_cell)
        rows[key] = frozenset(s.strip() for s in uses_cell.split(",") if s.strip())
    return rows


def _live_scopes_md_table() -> dict[str, frozenset[str]]:
    return _parse_toolkit_table(_scopes_md_text())


def test_template_file_exists():
    _template_text()


def test_template_names_a_public_issue_and_an_explicit_scope_confirm():
    text = _template_text().lower()
    assert "second lock" in text or "scope confirm" in text
    assert "verbatim" in text


def test_template_points_at_the_real_consent_module():
    text = _template_text()
    assert "seam_engine/src/seam_engine/consent.py" in text
    assert "enforce_consent_gate" in text


def test_every_required_scope_name_appears_verbatim_on_the_template():
    text = _template_text()
    for toolkit, scopes in REQUIRED_SCOPES.items():
        for scope in scopes:
            assert scope in text, (
                f"{toolkit}/{scope} is in consent.REQUIRED_SCOPES but does not appear "
                "verbatim on point-fencepost.md — the template has drifted from the gate"
            )


def test_template_never_asks_the_human_to_confirm_a_write_scope():
    text = _template_text()
    write_prefixes = ("Create", "Update", "Delete", "Send", "Post", "Reply", "Merge", "Modify", "Trash")
    # Only check inside the scope-confirm table rows (backtick-quoted lists),
    # so prose sentences that legitimately name a forbidden verb ("cannot
    # write, send, delete") to warn about it don't false-positive here.
    for line in text.splitlines():
        if not (line.strip().startswith("|") and "`" in line):
            continue
        for cell in line.split("`")[1::2]:
            for name in cell.split(","):
                name = name.strip()
                if not name:
                    continue
                assert not name.startswith(write_prefixes), (
                    f"{name!r} on the scope-confirm table looks write-capable"
                )


def test_scopes_md_table_parses_at_least_one_row():
    """A parser that silently matches zero rows would make every test below
    it vacuously true — the exact failure mode task 135's own buildlog names
    for a row regex missing `re.MULTILINE`. Fail loudly here first."""
    parsed = _live_scopes_md_table()
    assert len(parsed) > 0, "the toolkit table parsed to zero rows — check the section markers or the row regex"


def test_scopes_md_table_names_exactly_the_toolkits_required_scopes_knows():
    parsed = _live_scopes_md_table()
    assert set(parsed) == set(REQUIRED_SCOPES), (
        f"SCOPES.md's table parses to toolkits {sorted(parsed)}, but "
        f"consent.REQUIRED_SCOPES holds {sorted(REQUIRED_SCOPES)} — a toolkit "
        "was added to (or removed from) one side without the other"
    )


def test_required_scopes_matches_scopes_md_table_verbatim_per_toolkit():
    """The claim `consent.py`'s own comment makes — "mirrored verbatim from
    SCOPES.md's 'Fencepost uses' column. Not paraphrased" — checked against
    the real file for the first time. A confirm typed exactly off SCOPES.md
    must never be refused as "does not match ... verbatim" by
    `check_scope_confirm`, and a confirm the gate accepts must never grant
    more (or less) than SCOPES.md actually swears to.
    """
    parsed = _live_scopes_md_table()
    for toolkit, doc_scopes in parsed.items():
        assert toolkit in REQUIRED_SCOPES, (
            f"SCOPES.md names toolkit {toolkit!r} with no matching entry in "
            "consent.REQUIRED_SCOPES — a human could confirm this toolkit's "
            "scopes exactly as SCOPES.md prints them and enforce_consent_gate "
            "would still refuse it as an 'unknown toolkit'"
        )
        assert doc_scopes == REQUIRED_SCOPES[toolkit], (
            f"consent.REQUIRED_SCOPES[{toolkit!r}] = {sorted(REQUIRED_SCOPES[toolkit])} "
            f"has drifted from SCOPES.md's own table = {sorted(doc_scopes)} — the "
            "gate is no longer checking a confirm against what the Oath actually swears"
        )


def test_every_required_scopes_toolkit_has_a_scopes_md_row():
    parsed = _live_scopes_md_table()
    for toolkit in REQUIRED_SCOPES:
        assert toolkit in parsed, (
            f"consent.REQUIRED_SCOPES names toolkit {toolkit!r} with no matching "
            "row in SCOPES.md's own table — the gate is checking a toolkit the "
            "Oath never actually swore to"
        )


def test_parser_actually_detects_drift_not_just_tautologically_passes():
    """Hand-verification, in test form. Mutate a COPY of the real table text
    the way a future SCOPES.md edit genuinely could (here: drop
    `GetLatestRelease` from GitHub's row) and prove the same parser used by
    the tests above disagrees with `REQUIRED_SCOPES` on the mutated text —
    the same before/after discipline task 135's own hand-verification held
    its checker to, so this file's silence on a real future drift can't be
    mistaken for a parser that would pass no matter what the doc said.
    """
    real_text = _scopes_md_text()
    real_row = (
        "GetRepository, ListRepoCommits, ListIssues, GetIssue, ListPullRequests, "
        "ListRepositoryActivities, CountStargazers, GetLatestRelease"
    )
    mutated_row = (
        "GetRepository, ListRepoCommits, ListIssues, GetIssue, ListPullRequests, "
        "ListRepositoryActivities, CountStargazers"
    )
    assert real_row in real_text, "SCOPES.md's GitHub row text has already changed shape — update this fixture row"
    mutated_text = real_text.replace(real_row, mutated_row)
    assert mutated_text != real_text

    mutated_parsed = _parse_toolkit_table(mutated_text)
    assert "GetLatestRelease" not in mutated_parsed["github"]
    assert mutated_parsed["github"] != REQUIRED_SCOPES["github"]

    # And the real, unmutated file still parses clean against REQUIRED_SCOPES
    # — proving the mutation above is what broke it, not a parser that's
    # simply broken regardless of input.
    real_parsed = _parse_toolkit_table(real_text)
    assert real_parsed["github"] == REQUIRED_SCOPES["github"]


def _scan_py_claimed_github_tools() -> frozenset[str]:
    """Every test above this point proves REQUIRED_SCOPES agrees with
    SCOPES.md and the issue template — two hand-typed copies and their
    shared source doc. None of them ever checks the actual reading code:
    `scan.py`'s own module docstring names the real GitHub tool calls its
    live-override path expects (`load_github_events_from_live`'s
    `get_latest_release` among them, task 128's addition), and
    `fetch_github_activity` really does call `releases/latest` on every
    run (proven live by `test_scan.py`'s `kind="release"` cases). That
    call was missing from REQUIRED_SCOPES/SCOPES.md/the issue template
    until this test closed the gap — the same doc-vs-code drift class as
    tasks 130/131/133/135/136, aimed at scan.py's own claim for the first
    time.
    """
    text = SCAN_PY.read_text(encoding="utf-8")
    marker = "GitHub read-only toolkit makes ("
    assert marker in text, f"{SCAN_PY} no longer names its own claimed GitHub tool list — update this test's marker"
    start = text.index(marker) + len(marker)
    end = text.index(")", start)
    return frozenset(name.strip() for name in text[start:end].split(",") if name.strip())


def test_scan_py_exists():
    assert SCAN_PY.exists(), f"missing {SCAN_PY} — the seam-scan engine itself must still exist"


def test_scan_py_claimed_github_tools_are_all_in_required_scopes():
    """scan.py's own docstring must never claim to use a GitHub tool the
    sworn Oath doesn't declare — the exact drift this test file's earlier
    tests never checked for, because they only ever compared REQUIRED_SCOPES
    against two OTHER hand-typed copies of the same list, never against the
    reading code itself.
    """
    claimed = _scan_py_claimed_github_tools()
    assert claimed, "parsed zero claimed GitHub tools from scan.py — check the marker text hasn't moved"
    missing = claimed - REQUIRED_SCOPES["github"]
    assert not missing, (
        f"scan.py's docstring claims GitHub tool(s) {sorted(missing)} that "
        "consent.REQUIRED_SCOPES['github'] does not declare — the sworn Oath "
        "is narrower than what the engine actually reads"
    )
