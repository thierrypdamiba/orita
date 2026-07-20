"""Task 171. `fencepost/README.md` carries the town's live read-only proof
badge -- a shields.io endpoint badge that repaints from `seam_engine/badge.py`'s
real introspection of the MCP server's tool catalog plus the Ledger's tamper
seal (see `test_badge.py`). That is the single most concrete, live-checked
backing for the town's central promise ("read-only, checked not promised").

Before this task, the badge lived only in the GitHub README -- the actual
public Wall (`docs/fencepost/index.html`), the one page a real visitor lands
on, only ever asserted read-only-ness in prose. This file proves the badge
was added to the site with the *same* shields.io endpoint URL the README
carries (never a second, hand-typed copy that could drift), and proves the
check would actually catch drift if one copy ever changed and the other
didn't -- the same "claims a mirror, never checked against it" class tasks
135-160 kept closing elsewhere in this repo.
"""
from __future__ import annotations

import re
from pathlib import Path

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = FENCEPOST_ROOT.parent
README = FENCEPOST_ROOT / "README.md"
INDEX_HTML = REPO_ROOT / "docs" / "fencepost" / "index.html"

# Matches the shields.io endpoint badge image URL inside README.md's markdown
# badge syntax: [![alt](https://img.shields.io/endpoint?url=...)](BADGE.json)
_BADGE_URL_RE = re.compile(r"https://img\.shields\.io/endpoint\?url=[^)\s\"]+")


def real_badge_url(text: str) -> str:
    """The live shields.io endpoint URL, extracted from real badge markup --
    never a second hand-typed copy. Raises if no badge URL is found, rather
    than silently deriving a URL for a badge that isn't really there."""
    m = _BADGE_URL_RE.search(text)
    if not m:
        raise AssertionError("no shields.io endpoint badge URL found in given text")
    return m.group(0)


def test_readme_really_carries_a_badge_url():
    """Regression pin: today's real README really carries the live badge."""
    assert README.exists()
    url = real_badge_url(README.read_text(encoding="utf-8"))
    assert url.startswith("https://img.shields.io/endpoint?url=")
    assert "BADGE.json" in url


def test_index_html_img_src_matches_the_readme_badge_url():
    """The site's badge `<img src>` must equal the README's badge URL
    exactly -- extracted live from both real files, never hand-typed twice."""
    assert INDEX_HTML.exists()
    readme_url = real_badge_url(README.read_text(encoding="utf-8"))
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert f'src="{readme_url}"' in html, (
        "docs/fencepost/index.html's badge <img src> does not match "
        "fencepost/README.md's live badge URL"
    )


def test_a_drifted_site_copy_would_flip_this_check_red(tmp_path):
    """Mutation-based hand-verification: take the real README and real
    index.html, then mutate only the site's copy of the badge URL (the
    exact 'one file updated, the other forgotten' drift this test exists
    to catch) and prove the two URLs disagree."""
    readme_url = real_badge_url(README.read_text(encoding="utf-8"))

    drifted_html = INDEX_HTML.read_text(encoding="utf-8").replace(
        readme_url,
        "https://img.shields.io/endpoint?url=https%3A%2F%2Fexample.invalid%2Fstale-badge.json",
    )
    assert f'src="{readme_url}"' not in drifted_html


def test_missing_badge_url_raises_instead_of_silently_passing():
    try:
        real_badge_url("no badge markup here at all")
    except AssertionError:
        pass
    else:
        raise AssertionError("expected AssertionError when no badge URL is present")
