"""Task 474. Zashiki-warashi fixes her own front-door hint.

`docs/index.html`'s console-log Easter egg is the doorway into her own
`docs/attic/` mystery drawer -- the line a mortal sees only by opening
devtools, reading `you looked. the child likes you.` and following the
path it names. A live read this hour found two real, previously
unnoticed bugs in that one line:

1. Wrong path. `.github/workflows/pages.yml` deploys `path: docs` as the
   Pages artifact root, so the site serves under the repo-name prefix
   (`https://thierrypdamiba.github.io/orita/...`, not `.../docs/...`) --
   `docs/index.html`'s own `og:url` meta tag and `docs/cards/
   first-firing.html`'s real attic image URLs both already prove this
   convention live. The console hint pointed at `/docs/attic/`, a path
   that 404s on the real deployed site, instead of `/orita/attic/`.
2. Double-escaped newline. The JS string literal held `\\\\n` (a
   backslash-escaped backslash followed by a literal `n`) instead of
   `\\n` (the newline escape), so the message printed as one line with a
   literal `\\n` inline rather than the intended three poetic lines.

`tools/site_link_check.py` never had a chance to catch either: it
strips `<script>` blocks before scanning, by design, so a broken path
living inside a JS string literal is structurally invisible to it.

This module cross-checks against the file's own stated facts (the real
`og:url` prefix, `pages.yml`'s real deploy path) rather than hardcoding
a second copy of "orita" as an expected literal, so a future rename of
either wouldn't leave this test silently proving the wrong thing.
"""
from __future__ import annotations

import os
import re
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
INDEX_PATH = os.path.join(REPO_ROOT, "docs", "index.html")
PAGES_WORKFLOW_PATH = os.path.join(REPO_ROOT, ".github", "workflows", "pages.yml")

_CONSOLE_LOG = re.compile(r"console\.log\('(?P<body>.*?)'\);")
_OG_URL = re.compile(r'<meta property="og:url" content="https://[^/]+/(?P<repo>[^/]+)/">')
_PAGES_PATH = re.compile(r"^\s*path:\s*(?P<dir>\S+)\s*$", re.MULTILINE)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _console_egg_body() -> str:
    html = _read(INDEX_PATH)
    m = _CONSOLE_LOG.search(html)
    if not m:
        raise AssertionError("no console.log('...') Easter egg found in docs/index.html")
    return m.group("body")


def _real_site_repo_prefix() -> str:
    """The repo-name path segment GitHub Pages actually serves under,
    read from docs/index.html's own og:url meta tag rather than
    hardcoded, so a real repo rename keeps this test honest."""
    html = _read(INDEX_PATH)
    m = _OG_URL.search(html)
    if not m:
        raise AssertionError("no og:url meta tag found in docs/index.html to derive the real site prefix from")
    return m.group("repo")


def _pages_deploy_dir() -> str:
    yml = _read(PAGES_WORKFLOW_PATH)
    m = _PAGES_PATH.search(yml)
    if not m:
        raise AssertionError("no 'path: <dir>' line found in .github/workflows/pages.yml")
    return m.group("dir")


class ConsoleEggPathDoctrineTest(unittest.TestCase):
    def test_pages_deploys_docs_not_a_repo_named_directory(self):
        # Establishes the premise the rest of this test class relies on:
        # the deployed root is docs/, so URLs are repo-prefixed, never
        # docs-prefixed.
        self.assertEqual(_pages_deploy_dir(), "docs")

    def test_egg_does_not_point_at_the_source_directory_name(self):
        body = _console_egg_body()
        self.assertNotIn("/docs/attic/", body)

    def test_egg_points_at_the_real_deployed_site_prefix(self):
        body = _console_egg_body()
        prefix = _real_site_repo_prefix()
        self.assertIn(f"/{prefix}/attic/", body)

    def test_egg_names_a_directory_that_actually_exists(self):
        body = _console_egg_body()
        prefix = _real_site_repo_prefix()
        # Pull the path back out of the fixed body and confirm docs/attic/
        # (the real on-disk location Pages serves it from) is real.
        self.assertIn(f"/{prefix}/attic/", body)
        attic_dir = os.path.join(REPO_ROOT, "docs", "attic")
        self.assertTrue(os.path.isdir(attic_dir), f"{attic_dir} does not exist")
        self.assertTrue(os.listdir(attic_dir), f"{attic_dir} is empty")


class ConsoleEggEscapingDoctrineTest(unittest.TestCase):
    def test_no_double_escaped_newline(self):
        """A raw double-backslash-n (one escaped backslash + a literal
        'n') is the exact pre-fix bug: it prints as a literal backslash-n
        instead of breaking the line."""
        html = _read(INDEX_PATH)
        self.assertNotIn("\\\\n", html)

    def test_egg_body_carries_real_newline_escapes(self):
        """The fixed body must carry the single-backslash JS newline
        escape (source bytes: one backslash then 'n') so the console
        message actually renders on three lines."""
        body = _console_egg_body()
        self.assertIn("\\n", body)
        self.assertEqual(body.count("\\n"), 2, "expected exactly two newline escapes (three lines)")


if __name__ == "__main__":
    unittest.main()
