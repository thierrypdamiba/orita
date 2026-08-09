#!/usr/bin/env python3
"""Ogun's own charter duty, unchecked until now.

CHARTER.md Appendix B names Ogun's job plainly: "when the crowd lands,
everything works -- site under two seconds, links unbroken, good-first-
issues stocked, badge green." Every other clause in that sentence has a
real running check somewhere in this tree (CI timing, the Iron Ledger
badge, the good-first-issue labels) -- "links unbroken" never got one.
A stranger clicking through `docs/` on a dead relative link is exactly
the kind of small, avoidable, first-impression trust cost the whole
Star Covenant is built to avoid, and nothing has ever verified it stays
true as the site grows.

This is a read-only, local-filesystem-only, no network AST/regex scan of
every `docs/**/*.html` and `docs/**/*.md` file for a relative link (an
`href="..."`/`src="..."` attribute, or a markdown `[text](...)` target)
that does not resolve to a real file already on disk. External links
(`http(s)://`, `mailto:`, `tel:`), same-page anchors (`#...`), and
`javascript:`/`data:` URIs are all explicitly out of scope -- this checks
only the site's own internal wiring, the one thing a live crawl from in
here could otherwise never verify without a network call this town's own
doctrine forbids.

The naive first draft of this scan (a plain regex over the raw HTML)
produced 19 false positives on the very first run against the live site:
every page's inline favicon `data:image/svg+xml,...` URI, and one
`href="$2"` inside `docs/fencepost/index.html`'s own client-side markdown-
link-rendering `<script>` block -- a regex *replacement placeholder*,
not a link at all. Ogun's own law (borrowed from Ogun's law proper, false
positives are fatal to trust) applies here just as much as it does to a
Fencepost gap: a link checker that cries wolf on its own site's real,
working pages is worse than no checker. Fixed by excluding `data:` URIs
by scheme and stripping every `<script>...</script>` block before
scanning HTML at all -- the same "read the shape, not just the text"
discipline `duplicate_regex_check.py`'s `ast` parse already holds for
Python.

Task 473 (Nyx, task 472's own left-open item): this checker was written
only for `docs/`, the Pages-served site, where a bare directory URL
renders only if it holds its own `index.html` -- so `_target_exists`
required one. Task 472 tried pointing it at `houses/*/README.md` and
found that rule doesn't hold there: `houses/<g>/journal/` and
`houses/<g>/altar/petitions/` are real, working, clickable GitHub folder
links with no `index.html` and never will have one. Naively widening the
scan would flag 26 already-working links as broken plus one more class
of false positive found live: journal entries that quote markdown link
syntax as *prose describing a bug* (` `[Decrees](decrees/)` `, `` `[text]
(href)` ``, both inside backticks in `houses/nisaba/journal/0187-*.md`
and `houses/nyx/journal/0038-*.md`) got matched as if they were real
links, because the old markdown extractor never distinguished an inline
code span from an actual link. Two fixes, both load-bearing:

1. `_strip_markdown_code_spans` removes every fenced (```) and inline
   (`` ` ``) code span from `.md` content before the link regex ever
   runs -- the same "strip the code, then scan the prose" move this
   module's own docstring already used for `<script>` blocks in HTML.
   A journal entry can now safely *quote* broken-link syntax as an
   example without becoming one.
2. `_target_exists` takes a new `require_index` flag (default `True`,
   `docs/`'s existing behavior, byte-for-byte unchanged). Passing
   `require_index=False` treats any real directory as a valid target --
   the GitHub-browsed rule `houses/` actually lives under. `find_violations`
   threads it through; the cache key now includes it, so a `docs/` read
   and a `houses/` read (task 473's own `check_house_links` caller in
   `ritual_check.py`) never collide.

Both fixes proved live: with both applied, `find_violations("houses",
require_index=False)` returns zero -- the same nine READMEs (task 472
fixed the actual dead link) plus every journal entry now read clean.

Usage:
    python3 tools/site_link_check.py check
"""
from __future__ import annotations

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DOCS_DIR = os.path.join(ROOT, "docs")

_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']')
_SRC_RE = re.compile(r'src=["\']([^"\']+)["\']')
_MD_LINK_RE = re.compile(r'\]\(([^)]+)\)')
_SCRIPT_RE = re.compile(r'<script\b[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
_MD_FENCE_RE = re.compile(r'```.*?```', re.DOTALL)
_MD_INLINE_CODE_RE = re.compile(r'`[^`\n]*`')

# Schemes/forms that are never a same-repo relative link, so never worth
# a local-filesystem existence check. Anchors-only ("#foo") point within
# the same already-loaded page. `data:` is an inline payload, not a
# fetch -- the exact false-positive class this module's own docstring
# names finding on its first live run. "//" is a protocol-relative URL
# (e.g. `href="//cdn.example.com/lib.js"`, inherits the current page's
# scheme) -- without this, `_resolve` reads its leading "/" as a site-
# root-relative path and checks it against `docs_dir`, a second false
# positive of the same class the `data:` one already names.
_SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "javascript:", "data:", "//")


def _iter_site_files(docs_dir: str) -> list[str]:
    files = glob.glob(os.path.join(docs_dir, "**", "*.html"), recursive=True)
    files += glob.glob(os.path.join(docs_dir, "**", "*.md"), recursive=True)
    return sorted(files)


def _strip_markdown_code_spans(content: str) -> str:
    """Removes every fenced (```) and inline (`` ` ``) code span before the
    markdown link regex runs -- a journal entry quoting `[text](href)` or
    `[Decrees](decrees/)` as an EXAMPLE of broken syntax (task 472's own
    prose, describing the bug it just fixed) is not a real link and must
    not read as one. Mirrors `_SCRIPT_RE`'s HTML-side strip-then-scan."""
    return _MD_INLINE_CODE_RE.sub("", _MD_FENCE_RE.sub("", content))


def _extract_links(path: str, content: str) -> list[str]:
    """Every candidate link in `content`, HTML `<script>` blocks excluded
    (a `<script>` tag's own string literals -- template placeholders like
    `$2`, JS-built URLs -- are not the site's static wiring this check
    audits)."""
    if path.endswith(".html"):
        scanned = _SCRIPT_RE.sub("", content)
        return _HREF_RE.findall(scanned) + _SRC_RE.findall(scanned)
    # .md: markdown links only; no href/src attributes exist in prose.
    # Code spans stripped first -- a quoted example of link syntax is not
    # a real link (see _strip_markdown_code_spans's own docstring).
    return _MD_LINK_RE.findall(_strip_markdown_code_spans(content))


def _resolve(docs_dir: str, source_file: str, link: str) -> str | None:
    """The real filesystem path `link` (found inside `source_file`) points
    at, or None if `link` is out of scope for this check entirely (an
    external scheme, a bare same-page anchor, empty after stripping its
    fragment)."""
    if link.startswith(_SKIP_PREFIXES):
        return None
    path_part = link.split("#", 1)[0].split("?", 1)[0]
    if not path_part:
        return None
    if path_part.startswith("/"):
        return os.path.normpath(os.path.join(docs_dir, path_part.lstrip("/")))
    return os.path.normpath(os.path.join(os.path.dirname(source_file), path_part))


def _target_exists(target: str, require_index: bool = True) -> bool:
    """`require_index=True` (default, `docs/`'s existing Pages-served
    behavior, byte-for-byte unchanged): a bare directory link only counts
    as real if it holds its own `index.html` -- a directory URL with no
    index simply 404s when Pages serves it. `require_index=False`: any
    real directory counts (the GitHub-browsed rule `houses/` actually
    lives under -- `journal/`, `altar/petitions/` are real, clickable
    GitHub folder links with no `index.html` and never will have one)."""
    if os.path.isfile(target):
        return True
    if os.path.isdir(target):
        if not require_index:
            return True
        return os.path.isfile(os.path.join(target, "index.html"))
    return False


_VIOLATIONS_CACHE: dict[tuple[str, bool], list[dict[str, object]]] = {}


def clear_cache() -> None:
    """Only real callers are tests wanting a forced fresh scan -- production's
    one-call-per-hour shape never needs this, the same convention `star_
    covenant_check.py`/`vault_leak_check.py`/`duplicate_regex_check.py`
    already hold."""
    _VIOLATIONS_CACHE.clear()


def find_violations(docs_dir: str = DEFAULT_DOCS_DIR, require_index: bool = True) -> list[dict[str, object]]:
    key = (os.path.realpath(docs_dir), require_index)
    if key not in _VIOLATIONS_CACHE:
        _VIOLATIONS_CACHE[key] = _find_violations_uncached(docs_dir, require_index=require_index)
    return list(_VIOLATIONS_CACHE[key])


def _find_violations_uncached(
    docs_dir: str = DEFAULT_DOCS_DIR, require_index: bool = True
) -> list[dict[str, object]]:
    """Read-only, local-filesystem-only scan (no network, no import,
    no execution of the pages it audits) of every `docs/**/*.html` and
    `docs/**/*.md` file for a relative link that does not resolve to a
    real file on disk. Returns a list of violation records, empty when
    every internal link in the live site holds. `require_index` threads
    straight to `_target_exists` -- see its docstring for the `docs/` vs.
    GitHub-browsed-tree distinction."""
    violations: list[dict[str, object]] = []
    for path in _iter_site_files(docs_dir):
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        rel = os.path.relpath(path, docs_dir)
        seen = set()
        for link in _extract_links(path, content):
            if link in seen:
                continue
            seen.add(link)
            target = _resolve(docs_dir, path, link)
            if target is None:
                continue
            if not _target_exists(target, require_index=require_index):
                violations.append({"file": rel, "link": link, "target": target})
    violations.sort(key=lambda v: (v["file"], v["link"]))
    return violations


def format_violations(violations: list[dict[str, object]]) -> str:
    if not violations:
        return "site link check: clean -- every internal docs/ link resolves"
    lines = [f"site link check: {len(violations)} BROKEN LINK(S) FOUND"]
    for v in violations:
        lines.append(f"  {v['file']}: {v['link']!r} -> {v['target']} (missing)")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    print(format_violations(result))
    sys.exit(1 if result else 0)
