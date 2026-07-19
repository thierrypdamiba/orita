"""Task 160. `report.py`'s own docstring makes a claim about `CONNECT_URL`:
"one line, quoted here and nowhere paraphrased, so the ad never drifts from
the walkthrough it is advertising." That sentence is about the URL matching
the real file the walkthrough lives at (`docs/fencepost/connect.html`) --
and, like every "claims a mirror, never checked against the thing it
mirrors" bug tasks 135-159 kept finding one office over, nothing anywhere
ever opened the real docs/ tree to confirm it.

`test_connect_doctrine.py` proves `connect.html` exists and is long enough
to be a real walkthrough (`test_connect_html_exists_on_the_site`) and proves
its *content* carries the right capabilities string, OAuth link, and account
name. `test_streak.py::test_connect_url...` pins `report.CONNECT_URL` to a
hand-typed string. Neither ever asks the one question that actually backs
the docstring's claim: does that hand-typed URL's path actually resolve, on
today's real disk, to the file `connect.html` really lives at? If the page
ever moved (`connect.html` -> `connect/index.html`, a plausible future
restructure -- `docs/fencepost/index.html` itself already lives one level
below `docs/`), `CONNECT_URL` would keep pointing at the old 404 and no
existing test would notice, because none of them derive the URL from the
real file path -- they only ever check the file's *contents*, or a
hand-typed string's *value*, never the file's *location*.

This file closes that gap the same way task 156 closed the recipe-count
claim: derive the real URL structurally from the real file's real position
under `docs/` (never a second hand-typed copy of the path), assert it
matches `report.CONNECT_URL`, and prove with a real mutation fixture that a
genuine move would flip the check red.
"""
from __future__ import annotations

from pathlib import Path

from seam_engine import report

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = FENCEPOST_ROOT.parent
DOCS_ROOT = REPO_ROOT / "docs"
CONNECT_HTML = DOCS_ROOT / "fencepost" / "connect.html"

# Same GitHub Pages base every other site-URL builder in this repo uses
# (tools/card.py's own BASE, tests/test_card.py's own copy of it) -- not
# re-derived here, since fixing that particular duplication is a different
# task than the one this file closes.
BASE = "https://thierrypdamiba.github.io/orita"


def real_connect_url(docs_root: Path, connect_html: Path) -> str:
    """The URL a reader would actually land on for `connect_html`, derived
    from its real position under `docs_root` -- never a hand-typed path
    string. Raises if `connect_html` doesn't exist or doesn't sit under
    `docs_root` at all, rather than silently deriving a URL for a file
    that isn't really there."""
    if not connect_html.exists():
        raise AssertionError(
            f"{connect_html} does not exist -- this doctrine test has "
            "nothing real left to derive a URL from"
        )
    rel = connect_html.relative_to(docs_root)
    return f"{BASE}/{rel.as_posix()}"


def test_derivation_is_structural_not_hardcoded(tmp_path):
    """Prove `real_connect_url` actually reads the file's real position,
    on a synthetic tree the real repo's own path can't coincidentally
    satisfy."""
    docs_root = tmp_path / "docs"
    page = docs_root / "somewhere" / "else" / "page.html"
    page.parent.mkdir(parents=True)
    page.write_text("<html></html>", encoding="utf-8")
    assert real_connect_url(docs_root, page) == f"{BASE}/somewhere/else/page.html"


def test_missing_file_raises_instead_of_silently_deriving_a_url(tmp_path):
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    missing = docs_root / "fencepost" / "connect.html"
    try:
        real_connect_url(docs_root, missing)
    except AssertionError:
        pass
    else:
        raise AssertionError("expected AssertionError for a missing file")


def test_connect_html_really_exists_at_its_claimed_path():
    """Regression pin: today's real, live file really sits where
    `report.CONNECT_URL` claims."""
    assert CONNECT_HTML.exists()


def test_connect_url_matches_the_real_file_on_disk():
    assert real_connect_url(DOCS_ROOT, CONNECT_HTML) == report.CONNECT_URL


def test_og_url_meta_on_the_real_page_agrees_too():
    """A second, independent live source for the same claim: the page's
    own `og:url` meta tag (what X/Slack unfurl previews read) should name
    the identical URL `report.py` advertises -- if a future edit moves the
    page and updates one but not the other, this catches the split."""
    html = CONNECT_HTML.read_text(encoding="utf-8")
    assert f'content="{report.CONNECT_URL}"' in html


def test_a_real_move_would_flip_this_check_red(tmp_path):
    """Mutation-based hand-verification: reconstruct today's real
    connect.html one directory deeper (the exact 'graduated to its own
    folder' shape a future restructure could plausibly take), and prove
    the derived URL for the moved file disagrees with the real, unmoved
    `report.CONNECT_URL` -- the exact drift this file exists to catch."""
    moved_docs_root = tmp_path / "docs"
    moved = moved_docs_root / "fencepost" / "connect" / "index.html"
    moved.parent.mkdir(parents=True)
    moved.write_text(CONNECT_HTML.read_text(encoding="utf-8"), encoding="utf-8")

    derived_for_moved_file = real_connect_url(moved_docs_root, moved)
    assert derived_for_moved_file == f"{BASE}/fencepost/connect/index.html"
    assert derived_for_moved_file != report.CONNECT_URL
