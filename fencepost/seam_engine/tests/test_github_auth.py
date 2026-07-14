"""Task 63 (interlude): `fetch_github_activity`'s unauthenticated GitHub
REST calls hit the 60/hr anonymous rate limit for real on 2026-07-14T13:39Z
(`seam-scan.yml`'s first-ever CI failure). `github_headers()` sends
`GITHUB_TOKEN` as a bearer credential when present (CI), degrades to the
original Accept/User-Agent-only header when absent -- same GET, same scope,
just no longer sharing the anonymous-tier ceiling with every other cadence
module on the same runner IP.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from seam_engine.github_auth import github_headers


class GithubHeadersTests(unittest.TestCase):
    def test_no_token_omits_authorization(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_TOKEN", None)
            os.environ.pop("GH_TOKEN", None)
            headers = github_headers()
        self.assertEqual(
            headers, {"Accept": "application/vnd.github+json", "User-Agent": "fencepost-seam-scan"}
        )
        self.assertNotIn("Authorization", headers)

    def test_github_token_env_adds_bearer_authorization(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "ghs_faketoken"}, clear=False):
            os.environ.pop("GH_TOKEN", None)
            headers = github_headers()
        self.assertEqual(headers["Authorization"], "Bearer ghs_faketoken")
        self.assertEqual(headers["User-Agent"], "fencepost-seam-scan")

    def test_gh_token_env_used_as_fallback(self):
        with mock.patch.dict(os.environ, {"GH_TOKEN": "gho_faketoken"}, clear=False):
            os.environ.pop("GITHUB_TOKEN", None)
            headers = github_headers()
        self.assertEqual(headers["Authorization"], "Bearer gho_faketoken")


if __name__ == "__main__":
    unittest.main()
