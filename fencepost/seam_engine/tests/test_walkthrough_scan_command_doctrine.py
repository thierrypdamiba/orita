"""ROADMAP.md #897. The "Fork & Connect your own" walkthrough hands a forker
a literal, copy-pasteable `run_scan(...)` command at the single highest-value
step -- the "it found MY gap" moment that is Kothar's whole OAuth-completion
funnel. `CONNECT.md` step 5 says
`run_scan('YOUR-GITHUB-USER', 'YOUR-REPO', window_hours=24*7)`; `ONBOARDING.md`
says the same shape with `window_hours=24*30`. Both are hand-typed prose
copies of a real call into `seam_engine.scan.run_scan`, cited as if they were
runnable, yet nothing ever checks that shape against the real function.

Reorder `run_scan`'s parameters, rename `window_hours`, or make `repo`
keyword-only, and the walkthrough silently keeps shipping a command that
raises `TypeError` the instant a forker pastes it -- with zero test failure,
at the exact step conversion depends on. This is the same "two authors
independently typing the same contract, never structurally checked" class
this codebase has closed before: the capabilities string
(`test_connect_doctrine.py`, task 152), the connect URL
(`test_connect_url_doctrine.py`, task 160), and the walkthrough verb list
(`test_connect_verbs_doctrine.py`, task 584).

This file parses each doc's `run_scan(...)` call structurally (via `ast`,
never a hardcoded re-spelling of the arguments) and `Signature.bind`s the
parsed call shape against the *real* `inspect.signature(run_scan)` -- so a
drift in either the doc or the function flips it red. It never asserts a
third hardcoded copy of the argument list; it proves the doc's call and the
live signature agree.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from seam_engine.scan import run_scan

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
CONNECT_MD = FENCEPOST_ROOT / "CONNECT.md"
ONBOARDING_MD = FENCEPOST_ROOT / "ONBOARDING.md"

# The two walkthrough docs that hand a forker a runnable run_scan command.
WALKTHROUGH_DOCS = (CONNECT_MD, ONBOARDING_MD)


def _extract_run_scan_call(text: str) -> ast.Call:
    """Find the single `run_scan(...)` call written in a doc and return its
    parsed `ast.Call` node. Balances parentheses from the first `run_scan(`
    so a multiline call (or one nested inside `json.dumps(...)`) is captured
    whole, then parses exactly that call expression -- never the surrounding
    shell/markdown."""
    marker = "run_scan("
    start = text.find(marker)
    assert start != -1, "the doc no longer contains a run_scan( call"
    # Balance parens from the opening '(' of run_scan(.
    open_paren = start + len(marker) - 1
    depth = 0
    end = None
    for i in range(open_paren, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    assert end is not None, "the doc's run_scan( call has no matching close paren"
    call_src = text[start:end]
    expr = ast.parse(call_src, mode="eval").body
    assert isinstance(expr, ast.Call), "parsed run_scan source was not a call expression"
    return expr


def _bindable_arg_names(call: ast.Call) -> tuple[int, list[str]]:
    """(count of positional args, list of keyword names) from a parsed call.
    `**kwargs`/`*args` splats in the doc would be ambiguous to bind-check --
    the walkthrough never uses them, and this refuses one loudly if it ever
    appears rather than silently passing."""
    for kw in call.keywords:
        assert kw.arg is not None, (
            "the doc's run_scan call uses a **kwargs splat -- this checker "
            "binds by explicit name and cannot verify a splat"
        )
    assert not any(isinstance(a, ast.Starred) for a in call.args), (
        "the doc's run_scan call uses a *args splat -- this checker binds by "
        "position and cannot verify a splat"
    )
    return len(call.args), [kw.arg for kw in call.keywords if kw.arg is not None]


def _assert_binds(sig: inspect.Signature, n_positional: int, kw_names: list[str]) -> None:
    """Bind the parsed call *shape* against a signature using placeholder
    values -- proves the arity and keyword names are real, bindable
    parameters of the function, independent of the placeholder strings the
    doc uses."""
    args = [object()] * n_positional
    kwargs = {name: object() for name in kw_names}
    sig.bind(*args, **kwargs)  # raises TypeError on any drift


@pytest.mark.parametrize("doc", WALKTHROUGH_DOCS, ids=lambda p: p.name)
def test_walkthrough_run_scan_command_binds_to_the_real_signature(doc: Path) -> None:
    assert doc.exists(), f"{doc.name} must exist"
    call = _extract_run_scan_call(doc.read_text(encoding="utf-8"))
    n_positional, kw_names = _bindable_arg_names(call)
    # Sanity: the walkthrough passes owner + repo positionally and names
    # window_hours as a keyword. If this ever changes shape, this parser
    # needs a look before the bind below can be trusted.
    assert n_positional == 2, f"{doc.name}: expected 2 positional args (owner, repo), got {n_positional}"
    assert "window_hours" in kw_names, f"{doc.name}: expected window_hours passed by keyword"
    _assert_binds(inspect.signature(run_scan), n_positional, kw_names)


def test_a_renamed_signature_parameter_would_flip_this_check_red() -> None:
    """Mutation on the code side: rename `window_hours` in a stand-in
    signature and the doc's call (which names window_hours by keyword) must
    fail to bind against it."""
    call = _extract_run_scan_call(CONNECT_MD.read_text(encoding="utf-8"))
    n_positional, kw_names = _bindable_arg_names(call)
    real = inspect.signature(run_scan)
    mutated_params = [
        p.replace(name="window_days") if p.name == "window_hours" else p
        for p in real.parameters.values()
    ]
    mutated = real.replace(parameters=mutated_params)
    with pytest.raises(TypeError):
        _assert_binds(mutated, n_positional, kw_names)


def test_a_repo_made_keyword_only_would_flip_this_check_red() -> None:
    """Mutation on the code side: make `repo` keyword-only in a stand-in
    signature and the doc's call (which passes repo positionally) must fail
    to bind against it."""
    call = _extract_run_scan_call(CONNECT_MD.read_text(encoding="utf-8"))
    n_positional, kw_names = _bindable_arg_names(call)
    real = inspect.signature(run_scan)
    # Make `repo` and every parameter after it keyword-only -- the only way
    # to move `repo` off positional binding while keeping the signature
    # itself legal (a keyword-only param may not precede a
    # positional-or-keyword one).
    seen_repo = False
    mutated_params = []
    for p in real.parameters.values():
        if p.name == "repo":
            seen_repo = True
        if seen_repo and p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
            p = p.replace(kind=inspect.Parameter.KEYWORD_ONLY)
        mutated_params.append(p)
    mutated = real.replace(parameters=mutated_params)
    with pytest.raises(TypeError):
        _assert_binds(mutated, n_positional, kw_names)


def test_a_doc_typo_in_the_keyword_would_flip_this_check_red() -> None:
    """Mutation on the doc side: the walkthrough mistypes the keyword and
    the parsed call must fail to bind against the real signature."""
    text = CONNECT_MD.read_text(encoding="utf-8").replace("window_hours=", "window_hourz=", 1)
    call = _extract_run_scan_call(text)
    n_positional, kw_names = _bindable_arg_names(call)
    assert "window_hourz" in kw_names, "sanity: the mutated doc keyword must parse"
    with pytest.raises(TypeError):
        _assert_binds(inspect.signature(run_scan), n_positional, kw_names)


def test_both_walkthrough_docs_carry_a_run_scan_command() -> None:
    """The docs this doctrine guards must not quietly lose the command it is
    guarding -- if a rewrite drops the runnable step, this file would pass
    vacuously otherwise."""
    for doc in WALKTHROUGH_DOCS:
        assert "run_scan(" in doc.read_text(encoding="utf-8"), (
            f"{doc.name} no longer carries a runnable run_scan( command -- "
            f"this doctrine test would pass vacuously; confirm the walkthrough "
            f"step was intentionally removed before deleting the guard."
        )
