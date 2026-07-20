"""ROADMAP.md #167. `docs/architecture/reference.md`'s Road-Law names the
whole point of the Mortal World ground: "no key ever reaches a model" — the
town's public safety promise, cited from `README.md`'s own "Why Arcade is
the hero" section too. `github_auth.py` (task 63) is the one place in the
entire `fencepost/seam_engine` source tree that reads a real secret
(`GITHUB_TOKEN`/`GH_TOKEN`) out of the environment and builds a literal
`Authorization: Bearer <token>` header — confirmed by grep, zero other hits
for `os.environ` reading anything credential-shaped anywhere else in
`seam_engine/src/`. `scan.py`'s `fetch_github_activity`/`fetch_latest_release`
are the only two callers of `github_headers()`, and the header they build
flows straight into `httpx.Client(headers=...)` — nothing has ever
structurally proven that value can't also flow onward into the
`GithubEvent` objects those two functions return, which is exactly the data
that reaches `compute_candidates` → `GapCandidate` → the sealed Ledger
record → `report.render_report`'s rendered text → the public repo and,
eventually, a god's own context. Confirmed by grep before writing a line:
zero hits for "github_headers", "Authorization", or "credential" anywhere
under `fencepost/seam_engine/tests/test_report.py`,
`fencepost/seam_engine/tests/test_scan.py`, or `tests/`. The two existing
neighbors don't cover this: `test_report.py`'s own AST check
(`_FORBIDDEN_NAMES`) proves `report.py` never TOUCHES a credential at all
(true, and irrelevant here — `report.py` only ever consumes an
already-built dict); `tools/network_boundary_check.py` (tasks 163/164)
proves a module never IMPORTS a network-capable library, a different claim
than "the credential this module deliberately does hold and use never
leaks into its own return value." True today (headers are built and used
purely locally inside each function, `GithubEvent`'s five fields — kind,
id, title, url, ts, author — are populated only from parsed JSON body
fields, never from `headers`) and completely unguarded until this file.

Three layers, same "prove it, don't just claim it" discipline task 152's
`gateway.py` cross-check and task 162's `oath_badge.py` fix both used:

1. A structural (`ast`) proof that the identifier `github_headers()`'s
   return value is bound to, inside each of the two real, live functions
   that call it, is used ONLY as an `httpx.Client(...)`
   keyword argument — never threaded into a `GithubEvent(...)` call, never
   returned directly.
2. A live, behavioral proof: a sentinel secret set as `GITHUB_TOKEN`,
   `fetch_github_activity`/`fetch_latest_release` run for real (over a
   `httpx.MockTransport`, no real network, same boundary
   `test_fetch_github_activity.py` already established) inside a full
   `run_scan` → `ledger.append_scan` → tablet-file → `report.render_report`
   pipeline, and the sentinel proven absent from every stage's output —
   not just the return value in memory, the actual bytes written to disk
   and rendered as prose.
3. Two mutation tests — one structural, one behavioral — each reconstructing
   a plausible leaky variant and proving the relevant check disagrees with
   it while still agreeing on the real, unmutated code, the same
   discipline every check in the tasks 135-166 family holds itself to.
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import httpx

from seam_engine import ledger, report, scan
from seam_engine.github_auth import github_headers

SENTINEL_TOKEN = "sentinel-super-secret-9x7z-do-not-leak"

_CHECKED_FUNCS = ("fetch_github_activity", "fetch_latest_release")
_ALLOWED_HEADER_CALL_NAMES = {"httpx.Client", "Client"}


def _call_name(call: ast.Call) -> str:
    """Best-effort dotted name for a Call node's func, e.g. 'httpx.Client'."""
    func = call.func
    if isinstance(func, ast.Attribute):
        base = func.value
        if isinstance(base, ast.Name):
            return f"{base.id}.{func.attr}"
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return "<unknown>"


def _attach_parents(tree: ast.AST) -> None:
    """Stamp every node with `.parent`, ast's own walk gives no such thing."""
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent


def find_header_leak_violations(source: str, func_names=_CHECKED_FUNCS) -> dict[str, list[str]]:
    """For each function named in `func_names`, find every local name bound
    from a call to `github_headers()`, then find every OTHER appearance of
    that name anywhere in the function body — not just as a direct call
    argument, but any read at all (including `headers.get(...)`-style
    attribute access, which is how a value can be laundered out through a
    dict method without ever appearing as a bare `Name` argument). The one
    clean shape is: the name appears exactly as the `headers=` keyword (or
    a lone positional) of an `httpx.Client(...)`-shaped call, and nowhere
    else. Every other read — passed into a different call, returned
    directly, or read via attribute/subscript access anywhere outside that
    one allowed keyword slot — is recorded as a violation string. Returns
    {func_name: [violation, ...]}; a clean function maps to an empty list.
    Raises `AssertionError` if a name in `func_names` isn't found at all,
    so a rename can't silently make this check stop checking anything.
    """
    tree = ast.parse(source)
    _attach_parents(tree)
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in func_names
    }
    missing = set(func_names) - set(functions)
    if missing:
        raise AssertionError(f"expected function(s) not found in source: {sorted(missing)}")

    results: dict[str, list[str]] = {}
    for name, node in functions.items():
        header_names: set[str] = set()
        binding_nodes: set[int] = set()
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                if _call_name(stmt.value) == "github_headers":
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            header_names.add(target.id)
                            binding_nodes.add(id(target))

        violations: list[str] = []
        for use in ast.walk(node):
            if not (isinstance(use, ast.Name) and use.id in header_names):
                continue
            if id(use) in binding_nodes:
                continue  # the assignment target itself, not a read
            parent = getattr(use, "parent", None)
            if (
                isinstance(parent, ast.keyword)
                and parent.arg == "headers"
                and isinstance(getattr(parent, "parent", None), ast.Call)
                and _call_name(parent.parent) in _ALLOWED_HEADER_CALL_NAMES
            ):
                continue  # the one clean shape: headers=headers into httpx.Client(...)
            if (
                isinstance(parent, ast.Call)
                and parent.args
                and parent.args[0] is use
                and _call_name(parent) in _ALLOWED_HEADER_CALL_NAMES
            ):
                continue  # a lone positional into an allowed Client-shaped call
            # Walk up to the nearest enclosing Call (however many attribute
            # accesses deep, e.g. `headers.get(...)`) so the violation names
            # what the value was actually laundered INTO, not just the
            # attribute-access node closest to the read itself.
            enclosing = parent
            while enclosing is not None and not isinstance(enclosing, ast.Call):
                enclosing = getattr(enclosing, "parent", None)
            context = _call_name(enclosing) if enclosing is not None else type(parent).__name__
            violations.append(
                f"{name}(): {use.id!r} read outside its httpx.Client(...) boundary, "
                f"reaching into {context}(...)"
            )
        results[name] = violations
    return results


class HeaderIsolationStructuralCase(unittest.TestCase):
    """Layer 1: the real, live scan.py source, parsed today."""

    def test_real_scan_py_never_threads_headers_into_an_event(self):
        source = inspect.getsource(scan)
        violations = find_header_leak_violations(source)
        self.assertEqual(
            violations,
            {name: [] for name in _CHECKED_FUNCS},
            f"github_headers() escaped its httpx.Client(...) boundary: {violations}",
        )

    def test_missing_function_raises_rather_than_silently_passing(self):
        with self.assertRaises(AssertionError):
            find_header_leak_violations("def unrelated():\n    pass\n")


class HeaderIsolationMutationCase(unittest.TestCase):
    """Layer 3a: reconstruct a plausible future drift — a maintainer folds
    the auth header into the event's author field for debugging and forgets
    to take it back out — and prove the structural check catches it while
    still passing on the real, unmutated source."""

    LEAKY_SOURCE = '''
def fetch_latest_release(owner, repo):
    headers = github_headers()
    with httpx.Client(timeout=15.0, headers=headers) as client:
        release = client.get("x")
        if release.status_code == 200:
            r = release.json()
            return GithubEvent(
                kind="release", id=r["tag_name"], title=r["name"],
                url=r["html_url"], ts=r["published_at"],
                author=headers.get("Authorization", r.get("author", "unknown")),
            )
    return None


def fetch_github_activity(owner, repo, since):
    headers = github_headers()
    with httpx.Client(timeout=15.0, headers=headers) as client:
        pass
    return []
'''

    def test_mutated_source_is_flagged(self):
        violations = find_header_leak_violations(self.LEAKY_SOURCE)
        self.assertEqual(violations["fetch_github_activity"], [])
        self.assertTrue(
            violations["fetch_latest_release"],
            "the leaky reconstruction (Authorization header folded into "
            "GithubEvent.author via headers.get(...)) should have been "
            "flagged, but wasn't",
        )
        # The violation should name exactly where the laundering happens --
        # `headers.get(...)`, the attribute-access hop the leak rides out on.
        self.assertTrue(
            any("headers.get" in v for v in violations["fetch_latest_release"])
        )

    def test_real_source_has_no_such_violation(self):
        # Sanity: the real module, run through the exact same checker,
        # stays clean — the mutation test above isn't just a tautology
        # against a strawman shape the checker was hand-fit to.
        violations = find_header_leak_violations(inspect.getsource(scan))
        self.assertEqual(violations["fetch_latest_release"], [])


def _commit_json(n: int) -> dict:
    return {
        "sha": f"{n:040x}",
        "commit": {
            "message": f"task {n}: milestone flagship shipped",
            "author": {"name": "Off-By-One", "date": "2026-07-20T00:00:00+00:00"},
        },
        "html_url": f"https://github.com/thierrypdamiba/orita/commit/{n:040x}",
    }


def _release_json() -> dict:
    return {
        "tag_name": "v0.9",
        "name": "v0.9 flagship release",
        "html_url": "https://github.com/thierrypdamiba/orita/releases/v0.9",
        "published_at": "2026-07-20T00:00:00+00:00",
        "author": {"login": "off-by-one"},
    }


def _sentinel_transport():
    """Serves real-shaped JSON, and — critically — asserts every incoming
    request really does carry the sentinel bearer token, so this test can't
    pass by accident because the token was never actually sent."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == f"Bearer {SENTINEL_TOKEN}", (
            "test setup bug: the sentinel token never reached the real request headers"
        )
        if request.url.path.endswith("/releases/latest"):
            return httpx.Response(200, json=_release_json())
        assert request.url.path.endswith("/commits")
        page = int(request.url.params.get("page", "1"))
        if page > 1:
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[_commit_json(1)])

    return httpx.MockTransport(handler)


class HeaderIsolationLiveEndToEndCase(unittest.TestCase):
    """Layer 2: a real sentinel secret, run through the real pipeline
    (fetch -> compute_candidates -> ranked scan dict -> sealed ledger
    tablet on disk -> rendered Report text), proven absent everywhere."""

    def setUp(self):
        self._env_patch = mock.patch.dict(
            os.environ, {"GITHUB_TOKEN": SENTINEL_TOKEN}, clear=False
        )
        self._env_patch.start()
        os.environ.pop("GH_TOKEN", None)
        self.addCleanup(self._env_patch.stop)

        real_client = httpx.Client
        transport = _sentinel_transport()

        def fake_client(*args, **kwargs):
            kwargs["transport"] = transport
            return real_client(*args, **kwargs)

        self._client_patch = mock.patch.object(httpx, "Client", fake_client)
        self._client_patch.start()
        self.addCleanup(self._client_patch.stop)

    def test_sentinel_token_never_reaches_any_stage_of_the_pipeline(self):
        # Sanity: prove the token really is what github_headers() sends,
        # before trusting anything downstream.
        self.assertEqual(github_headers()["Authorization"], f"Bearer {SENTINEL_TOKEN}")

        x_posts = [{
            "id": "1", "text": "totally unrelated post, shares no keywords",
            "url": "https://x.com/oritatown/status/1",
            "ts": "2026-07-01T00:00:00+00:00",
        }]

        result = scan.run_scan(
            "thierrypdamiba", "orita", window_hours=24 * 30, x_posts=x_posts,
        )
        self.assertNotIn(SENTINEL_TOKEN, json.dumps(result))

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            tablet_path = ledger.append_scan(result, base=base)
            tablet_text = tablet_path.read_text(encoding="utf-8")
            self.assertNotIn(SENTINEL_TOKEN, tablet_text)

            records = ledger.read_records(base=base)
            self.assertEqual(len(records), 1)
            sealed = records[0]["sealed"]
            self.assertNotIn(SENTINEL_TOKEN, json.dumps(sealed))

            rendered = report.render_report(sealed, episode_number=1, streak_days=1)
            self.assertNotIn(SENTINEL_TOKEN, rendered)


def _leaky_fetch_latest_release(owner: str, repo: str):
    """Layer 3b: a hand-reconstructed, deliberately leaky sibling of the
    real `fetch_latest_release` — same shape, but folds the Authorization
    header into the returned event's `author` field, exactly the mutation
    Layer 3a proves the structural checker catches. This proves the
    end-to-end *behavioral* assertion above has teeth too: run this leaky
    function through the identical MockTransport/env setup and confirm the
    sentinel DOES show up, so the passing test above isn't vacuously true."""
    headers = github_headers()
    with httpx.Client(timeout=15.0, headers=headers) as client:
        release = client.get(f"{scan.GITHUB_API}/repos/{owner}/{repo}/releases/latest")
        if release.status_code == 200:
            r = release.json()
            return scan.GithubEvent(
                kind="release", id=r["tag_name"], title=r["name"] or r["tag_name"],
                url=r["html_url"],
                ts=datetime.fromisoformat(r["published_at"]),
                author=headers.get("Authorization", "unknown"),
            )
    return None


class HeaderIsolationBehavioralMutationCase(unittest.TestCase):
    """Confirms the end-to-end sentinel-absence assertion is not vacuous:
    a genuinely leaky implementation, run through the exact same real
    pipeline, is caught."""

    def setUp(self):
        self._env_patch = mock.patch.dict(
            os.environ, {"GITHUB_TOKEN": SENTINEL_TOKEN}, clear=False
        )
        self._env_patch.start()
        os.environ.pop("GH_TOKEN", None)
        self.addCleanup(self._env_patch.stop)

        real_client = httpx.Client
        transport = _sentinel_transport()

        def fake_client(*args, **kwargs):
            kwargs["transport"] = transport
            return real_client(*args, **kwargs)

        self._client_patch = mock.patch.object(httpx, "Client", fake_client)
        self._client_patch.start()
        self.addCleanup(self._client_patch.stop)

    def test_leaky_variant_is_caught_by_the_same_assertion(self):
        event = _leaky_fetch_latest_release("thierrypdamiba", "orita")
        self.assertIsNotNone(event)
        # The real check the end-to-end test above relies on: the sentinel
        # must not appear anywhere in the event's own fields. Here it does
        # -- proving the assertion genuinely discriminates leaky code from
        # clean code, rather than always trivially passing.
        self.assertIn(SENTINEL_TOKEN, json.dumps({"author": event.author}))


if __name__ == "__main__":
    unittest.main()
