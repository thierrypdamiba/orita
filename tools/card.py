#!/usr/bin/env python3
"""Make a Twitter/OG image card page so X renders a town image inline.

Usage: python3 tools/card.py <slug> <image-path-under-docs> "<title>" "<alt/description>"
Example: python3 tools/card.py first-firing attic/first-firing.jpg "A lantern in the attic" "A paper lantern glowing in a dark attic."

Prints the URL to tweet. X fetches the page, reads twitter:image, renders a large-image card.
"""
import html
import os
import sys

BASE = "https://thierrypdamiba.github.io/orita"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    slug, img, title, alt = sys.argv[1], sys.argv[2].lstrip("/"), sys.argv[3], sys.argv[4]
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
    out = os.path.join(ROOT, "docs", "cards", f"{slug}.html")
    with open(out, "w") as f:
        f.write(page)
    print(page_url)

if __name__ == "__main__":
    main()
