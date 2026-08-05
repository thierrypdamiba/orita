#!/usr/bin/env python3
"""Task 554. Kothar-wa-Khasis: the Wall never asked its own reverse question.

`recipe_readme_check.py` (task 426) closed a real gap in `fencepost/README.md`'s
"Community recipes" section: a forward-only substring check
(`tests/test_fencepost_site_recipes.py`'s `test_names_all_real_recipes`) proved
every real recipe was NAMED somewhere in the prose, but nothing ever asked the
reverse question -- does every LINK in that prose still point at a recipe
directory that actually exists on disk? A recipe renamed or removed after
merge would leave a dead link sitting in published prose forever, invisible to
a check that only ever asks "is this slug mentioned."

`docs/fencepost/index.html` -- the Wall, kothar-wa-khasis's own remit per
STRATEGY.md's Team table, the ONE page a real stranger actually lands on --
carries the IDENTICAL prose shape: a hand-written "Community recipes" section
listing every real recipe with its own `<a href="https://github.com/.../
fencepost/RECIPES/<slug>">` link and paragraph. `test_fencepost_site_recipes.py`'s
own `TestFencepostSiteRecipes.test_names_all_real_recipes` covers it in the
SAME forward-only direction `recipe_readme_check.py`'s docstring already named
as insufficient for `fencepost/README.md` -- and nothing else ever covers the
reverse. Confirmed live before writing this fix: temporarily removing a real
recipe directory (`fencepost/RECIPES/stale-branch-no-pr/`) left `recipe_readme_
check.py` correctly BROKEN ("dead link(s) to a recipe that no longer exists:
stale-branch-no-pr"), while `site_link_check.py` read clean (the site's own
recipe links are absolute `https://github.com/...` URLs, explicitly out of
`site_link_check.py`'s own local-filesystem-only scope by design) and
`test_fencepost_site_recipes.py` read 8/8 green throughout -- the Wall's own
public recipe catalog can silently go stale with a dead link to a recipe that
no longer exists, and nothing running or in the test suite would ever notice.

This module reads the SAME live ground truth `recipe_readme_check.py` and
`test_fencepost_site_recipes.py` both already trust
(`seam_engine.recipes.discover_recipes()`, never a second hand-typed slug
list) and structurally parses every
`<a href="https://github.com/thierrypdamiba/orita/tree/main/fencepost/RECIPES/
<slug>">...</a>` link inside the site's own "Community recipes" section
(bounded the same `<h2>...</h2>` ... next `</section>` way `text_patterns.
bounded_section` already reads a markdown `## ` section, just with an HTML
header/footer pair instead), then checks the same two things a bare substring
match cannot:

1. every real recipe directory has a matching link on the site
   (`missing_from_site` -- the direction `test_fencepost_site_recipes.py`
   already covers, kept here so the hourly ritual sees it too, not just the
   test suite);
2. every linked slug on the site still names a real recipe directory
   (`stale_in_site` -- the direction NOTHING has ever checked, live or in
   tests, until this task, mirroring `recipe_readme_check.py`'s own
   `stale_in_readme` for the sibling document);
3. a link's own anchor text and its href slug agree with each other
   (`mismatched_links` -- the same "two halves of one link disagree" class
   `recipe_readme_check.py` already guards against for `fencepost/README.md`).

`missing_readme` and `missing_roadmap_citation` (two of `recipe_readme_check.
py`'s four cross-checks) do not apply here on purpose: the site's own prose
carries no per-entry `(ROADMAP.md #NNN)` citation convention at all (confirmed
live: zero matches for "ROADMAP.md #" anywhere in `docs/fencepost/index.html`),
and a recipe's own `README.md` presence is a `fencepost/RECIPES/<slug>/`
filesystem property already covered by `recipe_readme_check.py` -- checking it
a second time from this module would be the exact "same fact reasserted twice
in two files" shape, not a new one.

Local-filesystem-only, no network call, the same cheap always-on class
`recipe_readme_check.py`/`check_wip_reclaim` already hold.

Usage:
    python3 tools/site_recipe_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SITE_PATH = os.path.join(ROOT, "docs", "fencepost", "index.html")
DEFAULT_FENCEPOST_ROOT = os.path.join(ROOT, "fencepost")

_SEAM_ENGINE_SRC = os.path.join(ROOT, "fencepost", "seam_engine", "src")
if _SEAM_ENGINE_SRC not in sys.path:
    sys.path.insert(0, _SEAM_ENGINE_SRC)
from seam_engine.recipes import discover_recipes  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import text_patterns  # noqa: E402

_SECTION_HEADER = re.compile(r"<h2>Community recipes</h2>")
_NEXT_SECTION_END = re.compile(r"</section>")
_RECIPE_LINK_RE = re.compile(
    r'<a href="https://github\.com/thierrypdamiba/orita/tree/main/fencepost/RECIPES/'
    r'([A-Za-z0-9_-]+)">([A-Za-z0-9_-]+)</a>'
)


def _community_recipes_section(site_text: str) -> str:
    """The text strictly between `<h2>Community recipes</h2>` and the next
    `</section>` close -- the HTML-section analogue of `recipe_readme_
    check.py`'s `_community_recipes_section`, sharing the same underlying
    `text_patterns.bounded_section` walk with an HTML header/footer pair
    instead of a markdown one. Empty string if the header itself is
    missing -- a real gap, not silently treated as vacuously documented."""
    return text_patterns.bounded_section(site_text, _SECTION_HEADER, next_header=_NEXT_SECTION_END)


def _linked_recipes(section_text: str) -> list[tuple[str, str]]:
    """Every `(href-slug, anchor-text-slug)` pair found in the section, in
    document order, duplicates included -- the caller decides what to do
    with a slug linked more than once."""
    return [(href, text) for href, text in _RECIPE_LINK_RE.findall(section_text)]


def check_site_recipe_readme(
    site_path: str = DEFAULT_SITE_PATH,
    fencepost_root: str = DEFAULT_FENCEPOST_ROOT,
) -> dict:
    """Cross-check `docs/fencepost/index.html`'s "Community recipes" section
    against the real, live `RECIPES/` tree (`discover_recipes()`, never a
    second hand-typed slug list). Returns `clean: True` only when every real
    recipe is linked, every link points at a real recipe, and every link's
    own two halves agree with each other; otherwise `clean: False` naming
    exactly which slugs are missing, stale, or mismatched -- never a bare
    pass/fail."""
    with open(site_path, encoding="utf-8") as f:
        site_text = f.read()
    section = _community_recipes_section(site_text)
    links = _linked_recipes(section)

    mismatched_links = sorted({(h, t) for h, t in links if h != t})
    linked_slugs = {h for h, _t in links}

    real_slugs = {m.slug for m in discover_recipes(Path(fencepost_root))}

    missing_from_site = sorted(real_slugs - linked_slugs)
    stale_in_site = sorted(linked_slugs - real_slugs)

    clean = not (missing_from_site or stale_in_site or mismatched_links)
    return {
        "clean": clean,
        "real_count": len(real_slugs),
        "linked_count": len(linked_slugs),
        "missing_from_site": missing_from_site,
        "stale_in_site": stale_in_site,
        "mismatched_links": mismatched_links,
    }


def format_result(result: dict) -> str:
    if result["clean"]:
        return (
            f"site recipe readme: clean ({result['real_count']} real recipe(s), "
            f"docs/fencepost/index.html's Community recipes section names every one, "
            f"no dead links)"
        )
    problems = []
    if result["missing_from_site"]:
        problems.append(f"unlinked real recipe(s): {', '.join(result['missing_from_site'])}")
    if result["stale_in_site"]:
        problems.append(f"dead link(s) to a recipe that no longer exists: {', '.join(result['stale_in_site'])}")
    if result["mismatched_links"]:
        pairs = ", ".join(f"[{h}]->text({t})" for h, t in result["mismatched_links"])
        problems.append(f"link href/text disagree: {pairs}")
    return "site recipe readme: BROKEN -- " + "; ".join(problems)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_site_recipe_readme()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
