"""Proves tools/site_link_check.py actually catches a broken relative
link, stays clean on external/anchor/data:/script-template shapes (the
exact false-positive class its own docstring names finding live on the
first run -- favicon `data:` URIs and an `href="$2"` regex-replacement
placeholder inside a `<script>` block), resolves absolute (leading `/`)
links against the docs root, treats a directory link as valid only when
it holds its own `index.html`, and -- the real point -- confirms the
live, current `docs/` tree holds zero real broken links today.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


slc = _load("site_link_check", os.path.join(ROOT, "tools", "site_link_check.py"))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _rm(path):
    shutil.rmtree(path, ignore_errors=True)


class FixtureViolationCase(unittest.TestCase):
    def setUp(self):
        self.docs = tempfile.mkdtemp()
        self.addCleanup(_rm, self.docs)
        slc.clear_cache()

    def test_broken_relative_link_is_flagged(self):
        _write(
            os.path.join(self.docs, "index.html"),
            '<a href="gods/nobody.html">nobody</a>',
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["file"], "index.html")
        self.assertEqual(violations[0]["link"], "gods/nobody.html")
        formatted = slc.format_violations(violations)
        self.assertIn("BROKEN LINK(S) FOUND", formatted)
        self.assertIn("nobody.html", formatted)

    def test_working_relative_link_is_not_flagged(self):
        _write(os.path.join(self.docs, "gods", "ogun.html"), "<html></html>")
        _write(
            os.path.join(self.docs, "index.html"),
            '<a href="gods/ogun.html">Ogun</a>',
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(violations, [])

    def test_markdown_link_is_checked_too(self):
        _write(os.path.join(self.docs, "attribution.html"), "<html></html>")
        _write(
            os.path.join(self.docs, "story-so-far.md"),
            "[attribution](attribution.html) but this one is [gone](nowhere.md)",
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["link"], "nowhere.md")

    def test_absolute_link_resolves_against_docs_root(self):
        _write(os.path.join(self.docs, "404.html"), "<html></html>")
        _write(
            os.path.join(self.docs, "gods", "nyx.html"),
            '<a href="/404.html">lost?</a>',
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(violations, [])

    def test_directory_link_valid_only_with_its_own_index(self):
        _write(
            os.path.join(self.docs, "index.html"),
            '<a href="oracle/">the oracle desk</a>',
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(len(violations), 1)

        _write(os.path.join(self.docs, "oracle", "index.html"), "<html></html>")
        slc.clear_cache()
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(violations, [])

    def test_external_mailto_anchor_and_javascript_links_are_out_of_scope(self):
        _write(
            os.path.join(self.docs, "index.html"),
            (
                '<a href="https://example.com/nope">ext</a>'
                '<a href="mailto:nobody@nowhere.example">mail</a>'
                '<a href="#section">anchor</a>'
                '<a href="javascript:void(0)">js</a>'
            ),
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(violations, [])

    def test_protocol_relative_link_is_not_a_false_positive(self):
        """A `//host/path` link inherits the current page's scheme and is
        never a same-repo relative path -- its leading "/" was previously
        read as a site-root path and checked against `docs_dir`, flagging
        a perfectly valid external link as a broken internal one."""
        _write(
            os.path.join(self.docs, "index.html"),
            '<a href="//cdn.example.com/lib.js">cdn link</a>',
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(violations, [])

    def test_data_uri_favicon_is_not_a_false_positive(self):
        """The exact bug this module's own docstring names finding live on
        its first run: every page's inline favicon is a `data:` URI, not a
        fetchable relative link."""
        _write(
            os.path.join(self.docs, "index.html"),
            '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27...%27/%3E">',
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(violations, [])

    def test_script_block_placeholder_is_not_a_false_positive(self):
        """The second real false positive this module's own docstring
        names: a client-side JS template's `href="$2"` inside a
        `<script>` block is a regex-replacement placeholder, not a link
        -- the exact live shape found in docs/fencepost/index.html."""
        _write(
            os.path.join(self.docs, "index.html"),
            "<script>\n"
            "  text.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href=\"$2\">$1</a>');\n"
            "</script>\n",
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(violations, [])

    def test_duplicate_link_on_same_page_only_reported_once(self):
        _write(
            os.path.join(self.docs, "index.html"),
            '<a href="gone.html">a</a><a href="gone.html">b</a>',
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(len(violations), 1)

    def test_clear_cache_forces_a_fresh_scan(self):
        _write(os.path.join(self.docs, "index.html"), '<a href="x.html">x</a>')
        first = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(len(first), 1)
        _write(os.path.join(self.docs, "x.html"), "<html></html>")
        cached = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(len(cached), 1, "uncleared cache should still read stale")
        slc.clear_cache()
        fresh = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(fresh, [])


    def test_require_index_false_treats_bare_directory_as_valid(self):
        """Task 473: the GitHub-browsed rule `houses/` actually lives
        under -- a real directory with no `index.html` is a perfectly
        working folder link there, unlike the Pages-served `docs/` tree."""
        _write(
            os.path.join(self.docs, "index.html"),
            '<a href="journal/">journal</a>',
        )
        os.makedirs(os.path.join(self.docs, "journal"), exist_ok=True)
        violations = slc.find_violations(docs_dir=self.docs, require_index=False)
        self.assertEqual(violations, [])

    def test_require_index_true_is_still_the_unchanged_default(self):
        """The exact same fixture, default flag: docs/'s existing stricter
        rule (bare directory needs its own index.html) must not have
        loosened just because require_index=False now exists elsewhere."""
        _write(
            os.path.join(self.docs, "index.html"),
            '<a href="journal/">journal</a>',
        )
        os.makedirs(os.path.join(self.docs, "journal"), exist_ok=True)
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(len(violations), 1)

    def test_require_index_false_still_flags_a_truly_missing_directory(self):
        _write(
            os.path.join(self.docs, "index.html"),
            '<a href="nowhere/">gone</a>',
        )
        violations = slc.find_violations(docs_dir=self.docs, require_index=False)
        self.assertEqual(len(violations), 1)

    def test_markdown_link_quoted_in_backticks_is_not_a_real_link(self):
        """Task 473: a journal entry quoting `[text](href)` as PROSE
        describing a bug (task 472's own live shape, in `houses/nisaba/
        journal/0187-*.md` and `houses/nyx/journal/0038-*.md`) must not
        be scanned as if it were a real link."""
        _write(
            os.path.join(self.docs, "journal.md"),
            "every README carried `[Decrees](decrees/)`, a dead link, "
            "fixed by pointing at `[text](href)` correctly instead.",
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(violations, [])

    def test_markdown_link_in_fenced_code_block_is_not_a_real_link(self):
        _write(
            os.path.join(self.docs, "journal.md"),
            "before:\n```\n[gone](nowhere.md)\n```\nafter\n",
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(violations, [])

    def test_markdown_link_outside_backticks_is_still_checked(self):
        """The code-span strip must not swallow a REAL link just because
        the same file also happens to quote syntax elsewhere."""
        _write(
            os.path.join(self.docs, "journal.md"),
            "quoting `[text](href)` as an example, but this real link "
            "is [actually broken](nowhere.md) and should still be caught.",
        )
        violations = slc.find_violations(docs_dir=self.docs)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["link"], "nowhere.md")


class LiveTreeCase(unittest.TestCase):
    def test_the_real_live_docs_tree_holds_zero_broken_links(self):
        slc.clear_cache()
        violations = slc.find_violations()
        self.assertEqual(violations, [], slc.format_violations(violations))

    def test_the_real_live_houses_tree_holds_zero_broken_links_github_browsed(self):
        """Task 473: the same widened checker, pointed at `houses/` with
        the GitHub-browsed `require_index=False` rule -- proves task 472's
        fix (the Decrees link) plus this hour's two false-positive fixes
        (bare directories, quoted link syntax in journal prose) together
        leave the real live tree clean, not just a fixture."""
        slc.clear_cache()
        houses_dir = os.path.join(ROOT, "houses")
        violations = slc.find_violations(docs_dir=houses_dir, require_index=False)
        self.assertEqual(violations, [], slc.format_violations(violations))


if __name__ == "__main__":
    unittest.main()
