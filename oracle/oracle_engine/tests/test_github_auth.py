"""Task 63 (interlude): every cadence module's `_default_http_get` shares
one unauthenticated-GitHub-REST rate-limit bucket -- `seam-scan.yml` hit it
for real on 2026-07-14T13:39Z. `github_headers()` is the fix: send
`GITHUB_TOKEN` as a bearer credential when present (CI), degrade to the
original Accept-only header when absent (everywhere else), never touch what
capability the request has -- it's still a bare GET either way.

This file's own docstring only ever tested `github_headers()`, but this
module's module-level docstring has claimed since task 63 to be shared
"for every cadence module's `_default_http_get`" -- twenty cadence modules
each still carried their own byte-identical private copy of that wrapper
(found live by an AST-hash sweep, the same method `tools/iso_time.py` and
`tools/metrics_reader.py` already used one directory over). `default_http_
get` below is that wrapper, finally living in the one place its own
neighboring docstring already said it did; `IdentityAcrossSiblingsCase`
proves every sibling now points at the same function object, not a copy.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))

from oracle_engine import (  # noqa: E402
    branch_cadence,
    collaborator_cadence,
    comment_cadence,
    commit_cadence,
    commit_comment_cadence,
    contributor_cadence,
    deployment_cadence,
    fork_cadence,
    github_auth,
    issue_cadence,
    issue_comment_cadence,
    label_cadence,
    milestone_cadence,
    pr_cadence,
    release_cadence,
    run_cadence,
    star_cadence,
    subscriber_cadence,
    tag_cadence,
    topic_cadence,
    workflow_cadence,
)
from oracle_engine.github_auth import github_headers  # noqa: E402

HTTP_GET_SIBLINGS = [
    branch_cadence,
    collaborator_cadence,
    comment_cadence,
    commit_cadence,
    commit_comment_cadence,
    contributor_cadence,
    deployment_cadence,
    fork_cadence,
    issue_cadence,
    issue_comment_cadence,
    label_cadence,
    milestone_cadence,
    pr_cadence,
    release_cadence,
    run_cadence,
    star_cadence,
    subscriber_cadence,
    tag_cadence,
    topic_cadence,
    workflow_cadence,
]


class GithubHeadersTests(unittest.TestCase):
    def test_no_token_omits_authorization(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_TOKEN", None)
            os.environ.pop("GH_TOKEN", None)
            headers = github_headers()
        self.assertEqual(headers, {"Accept": "application/vnd.github+json"})
        self.assertNotIn("Authorization", headers)

    def test_github_token_env_adds_bearer_authorization(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "ghs_faketoken"}, clear=False):
            os.environ.pop("GH_TOKEN", None)
            headers = github_headers()
        self.assertEqual(headers["Authorization"], "Bearer ghs_faketoken")
        self.assertEqual(headers["Accept"], "application/vnd.github+json")

    def test_gh_token_env_used_as_fallback(self):
        with mock.patch.dict(os.environ, {"GH_TOKEN": "gho_faketoken"}, clear=False):
            os.environ.pop("GITHUB_TOKEN", None)
            headers = github_headers()
        self.assertEqual(headers["Authorization"], "Bearer gho_faketoken")

    def test_github_token_takes_priority_over_gh_token(self):
        with mock.patch.dict(
            os.environ,
            {"GITHUB_TOKEN": "primary", "GH_TOKEN": "fallback"},
            clear=False,
        ):
            headers = github_headers()
        self.assertEqual(headers["Authorization"], "Bearer primary")

    def test_custom_accept_header_preserved(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_TOKEN", None)
            os.environ.pop("GH_TOKEN", None)
            headers = github_headers(accept="application/vnd.github.v3+json")
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")


class IdentityAcrossSiblingsCase(unittest.TestCase):
    """Every sibling's `_default_http_get` must BE `github_auth.default_
    http_get` (same function object), not merely equal source -- the only
    guarantee that makes the twenty-independent-copies drift this task
    closed structurally unable to recur one module at a time."""

    def test_every_sibling_shares_the_one_http_get_object(self):
        self.assertEqual(len(HTTP_GET_SIBLINGS), 20, "sibling list drifted from the live sweep")
        for mod in HTTP_GET_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                self.assertIs(
                    mod._default_http_get,
                    github_auth.default_http_get,
                    f"{mod.__name__}._default_http_get is a separate copy "
                    "again, not the shared oracle_engine.github_auth function",
                )


class DefaultHttpGetCase(unittest.TestCase):
    def test_gets_the_url_with_github_headers_and_returns_json(self):
        calls = {}

        class FakeResponse:
            def raise_for_status(self):
                calls["raised"] = True

            def json(self):
                return {"ok": True}

        class FakeHttpx:
            @staticmethod
            def get(url, headers, timeout):
                calls["url"] = url
                calls["headers"] = headers
                calls["timeout"] = timeout
                return FakeResponse()

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_TOKEN", None)
            os.environ.pop("GH_TOKEN", None)
            with mock.patch.dict(sys.modules, {"httpx": FakeHttpx}):
                result = github_auth.default_http_get("https://api.github.com/repos/x/y")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls["url"], "https://api.github.com/repos/x/y")
        self.assertEqual(calls["headers"], {"Accept": "application/vnd.github+json"})
        self.assertEqual(calls["timeout"], 10.0)
        self.assertTrue(calls["raised"])


if __name__ == "__main__":
    unittest.main()
