"""Task 63 (interlude): every cadence module's `_default_http_get` shares
one unauthenticated-GitHub-REST rate-limit bucket -- `seam-scan.yml` hit it
for real on 2026-07-14T13:39Z. `github_headers()` is the fix: send
`GITHUB_TOKEN` as a bearer credential when present (CI), degrade to the
original Accept-only header when absent (everywhere else), never touch what
capability the request has -- it's still a bare GET either way.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))

from oracle_engine.github_auth import github_headers  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
