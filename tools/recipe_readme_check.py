#!/usr/bin/env python3
"""Task 426. Nisaba: the recipe roll call nobody ever actually took.

`fencepost/README.md`'s "Community recipes" section is prose, hand-typed
one paragraph per recipe as each one merged -- twenty-six of them by task
419's own count, each one named "the Nth" with its own `RECIPES.md#N`
ROADMAP citation. `tests/test_fencepost_site_recipes.py` (task 417)
already proves every REAL recipe `discover_recipes()` finds is named
somewhere in that text -- but only in that one direction, and only as a
loose substring match on the bare slug. Nothing anywhere -- not that
test, not any `check_*` in `tools/ritual_check.py` -- ever reads the
section's own `[`RECIPES/<slug>/`](RECIPES/<slug>/)` links structurally
and asks the reverse question: does every LINK in that prose still point
at a recipe directory that actually exists on disk?

That reverse direction is exactly the gap a recipe rename or removal
would open, silently, the day it happened. Nothing in this repo's history
has ever removed a merged recipe, but nothing has ever stopped one from
being removed, either -- a stray `rm -rf RECIPES/<slug>/` (a bad merge
conflict resolution, a cleanup pass with too broad a glob) would leave a
dead `[...](RECIPES/<slug>/)` link sitting in published prose forever,
because `test_names_all_real_recipes`'s own substring check has nothing
in it that would ever notice a slug is present in the text but absent on
disk -- a stale link and a live one look byte-identical to a check that
only ever asks "is this slug mentioned."

`recipe_readme_check.py` reads the SAME live ground truth
`test_fencepost_site_recipes.py` already trusts (`seam_engine.recipes.
discover_recipes()`, never a second hand-typed slug list) and structurally
parses every `[`RECIPES/<slug>/`](RECIPES/<slug>/)` link inside the
README's own "## Community recipes" section (bounded the same
next-`## `-header way `scopes_completeness_check.py`'s section reader
already holds), then checks three things a bare substring match cannot:

1. every real recipe directory has a matching link (`missing_from_readme`
   -- the direction task 417's test already covers, kept here so the
   hourly ritual sees it too, not just the test suite);
2. every linked slug still names a real recipe directory
   (`stale_in_readme` -- the direction NOTHING has ever checked, live or
   in tests, until this task);
3. a link's own bracketed text and its href target agree with each other
   (`mismatched_links` -- a hand-typed `[`RECIPES/foo/`](RECIPES/bar/)`
   would read as two different slugs to a human skimming the rendered
   page and to `discover_recipes()` both, and neither existing check
   would ever notice the two halves of one link disagree).

Local-filesystem-only, no network call, the same cheap always-on class
`check_wip_reclaim`/`check_scopes_completeness` already hold.

Usage:
    python3 tools/recipe_readme_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_README_PATH = os.path.join(ROOT, "fencepost", "README.md")
DEFAULT_FENCEPOST_ROOT = os.path.join(ROOT, "fencepost")

_SEAM_ENGINE_SRC = os.path.join(ROOT, "fencepost", "seam_engine", "src")
if _SEAM_ENGINE_SRC not in sys.path:
    sys.path.insert(0, _SEAM_ENGINE_SRC)
from seam_engine.recipes import discover_recipes  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import text_patterns  # noqa: E402

_SECTION_HEADER = re.compile(r"^## Community recipes\s*$", re.MULTILINE)
_NEXT_HEADER = text_patterns.NEXT_MARKDOWN_HEADER
_RECIPE_LINK_RE = re.compile(r"\[`RECIPES/([A-Za-z0-9_-]+)/`\]\(RECIPES/([A-Za-z0-9_-]+)/\)")


def _community_recipes_section(readme_text: str) -> str:
    """The text strictly between the "## Community recipes" header and the
    next `## ` header (or end of file) -- the same bounded-section read
    `scopes_completeness_check.py`'s `_accounted_for_app_ids` already
    holds for `SCOPES.md`, so a `RECIPES/<slug>/` link mentioned in some
    OTHER section (there are none today, but nothing should assume that
    forever) is never mistaken for one of the thirty-two community
    recipes this section actually enumerates today. Empty string if the
    header itself is missing -- a real gap, not silently treated as
    vacuously documented."""
    header_match = _SECTION_HEADER.search(readme_text)
    if header_match is None:
        return ""
    start = header_match.end()
    next_match = _NEXT_HEADER.search(readme_text, pos=start)
    end = next_match.start() if next_match else len(readme_text)
    return readme_text[start:end]


def _linked_recipes(section_text: str) -> list[tuple[str, str]]:
    """Every `[`RECIPES/<text-slug>/`](RECIPES/<href-slug>/)` pair found in
    the section, in document order, duplicates included -- the caller
    decides what to do with a slug linked more than once."""
    return _RECIPE_LINK_RE.findall(section_text)


def check_recipe_readme(
    readme_path: str = DEFAULT_README_PATH,
    fencepost_root: str = DEFAULT_FENCEPOST_ROOT,
) -> dict:
    """Cross-check `fencepost/README.md`'s "Community recipes" section
    against the real, live `RECIPES/` tree (`discover_recipes()`, never a
    second hand-typed slug list). Returns `clean: True` only when every
    real recipe is linked, every link points at a real recipe, and every
    link's own two halves agree with each other; otherwise `clean: False`
    naming exactly which slugs are missing, stale, or mismatched -- never
    a bare pass/fail."""
    with open(readme_path, encoding="utf-8") as f:
        readme_text = f.read()
    section = _community_recipes_section(readme_text)
    links = _linked_recipes(section)

    mismatched_links = sorted({(t, h) for t, h in links if t != h})
    linked_slugs = {h for _t, h in links}

    real_slugs = {m.slug for m in discover_recipes(Path(fencepost_root))}

    missing_from_readme = sorted(real_slugs - linked_slugs)
    stale_in_readme = sorted(linked_slugs - real_slugs)

    clean = not (missing_from_readme or stale_in_readme or mismatched_links)
    return {
        "clean": clean,
        "real_count": len(real_slugs),
        "linked_count": len(linked_slugs),
        "missing_from_readme": missing_from_readme,
        "stale_in_readme": stale_in_readme,
        "mismatched_links": mismatched_links,
    }


def format_result(result: dict) -> str:
    if result["clean"]:
        return (
            f"recipe readme: clean ({result['real_count']} real recipe(s), "
            f"fencepost/README.md's Community recipes section names every one, "
            f"no dead links)"
        )
    problems = []
    if result["missing_from_readme"]:
        problems.append(f"unlinked real recipe(s): {', '.join(result['missing_from_readme'])}")
    if result["stale_in_readme"]:
        problems.append(f"dead link(s) to a recipe that no longer exists: {', '.join(result['stale_in_readme'])}")
    if result["mismatched_links"]:
        pairs = ", ".join(f"[{t}]->({h})" for t, h in result["mismatched_links"])
        problems.append(f"link text/href disagree: {pairs}")
    return "recipe readme: BROKEN -- " + "; ".join(problems)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_recipe_readme()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
