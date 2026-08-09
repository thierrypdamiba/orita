#!/usr/bin/env python3
"""Make a Twitter/OG image card page so X renders a town image inline.

Usage: python3 tools/card.py <slug> <image-path-under-docs> "<title>" "<alt/description>"
Example: python3 tools/card.py first-firing attic/first-firing.jpg "A lantern in the attic" "A paper lantern glowing in a dark attic."

Prints the URL to tweet. X fetches the page, reads twitter:image, renders a large-image card.

Proclamation 0002 ("Eyes and a Brush") makes alt text law, not a convention:
"every image carries alt text -- the town speaks to mortals who cannot see
it, or it does not speak." Until task 151, that law lived only in prose --
this script (the one and only place a card page gets built) happily wrote a
page with an empty `twitter:image:alt` if called with a blank alt argument.
`build_card()` enforces the law literally now: a blank slug/img/title/alt
raises `CardValidationError` naming exactly what's missing, before a single
byte is written -- the same validate-before-render discipline
`oracle_engine.copylint.render_call` already holds for `enforce_copy`
(task 146), applied here to Proclamation 0002 for the first time.
"""
import html
import os
import sys

BASE = "https://thierrypdamiba.github.io/orita"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CardValidationError(ValueError):
    """Raised when a card cannot lawfully be built. Proclamation 0002 is
    law, not a suggestion -- a card missing alt text does not get built,
    it gets refused."""


def build_card(slug: str, img: str, title: str, alt: str) -> tuple[str, str]:
    """Build a card page's HTML and its public URL. Pure -- no file I/O,
    so the page a real card would contain can be tested without ever
    touching disk. Raises `CardValidationError` if `slug`, `img`, `title`,
    or `alt` is blank or whitespace-only; `alt`'s enforcement is
    Proclamation 0002 made literal, the other three are the minimum a card
    page needs to mean anything at all."""
    for name, value in (("slug", slug), ("img", img), ("title", title), ("alt", alt)):
        if not isinstance(value, str) or not value.strip():
            raise CardValidationError(
                f"card requires a non-blank {name!r} -- Proclamation 0002 makes "
                f"alt text (and everything else a card page shows) mandatory, "
                f"not optional: 'every image carries alt text -- the town "
                f"speaks to mortals who cannot see it, or it does not speak'"
            )
    img = img.lstrip("/")
    img_url = f"{BASE}/{img}"
    page_url = f"{BASE}/cards/{slug}.html"
    t, d, a = (html.escape(x) for x in (title, alt, alt))
    page = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t} — Orita</title>
<meta name="description" content="{d}">
<meta property="og:type" content="article">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:image" content="{img_url}">
<meta property="og:url" content="{page_url}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{img_url}">
<meta name="twitter:image:alt" content="{a}">
<link rel="stylesheet" href="../style.css">
<div class="wrap">
  <a class="crumb" href="../index.html">← the crossroads</a>
  <article class="shrine">
    <h1>{t}</h1>
    <img src="../{img}" alt="{a}" style="max-width:100%;border:1px solid var(--line);border-radius:6px">
    <p class="epithet">{d}</p>
  </article>
  <footer><p><a href="../index.html">Orita</a></p></footer>
</div>
"""
    return page, page_url


def main() -> None:
    slug, img, title, alt = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    page, page_url = build_card(slug, img, title, alt)
    out_dir = os.path.join(ROOT, "docs", "cards")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{slug}.html")
    with open(out, "w") as f:
        f.write(page)
    print(page_url)

if __name__ == "__main__":
    main()
