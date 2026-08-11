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

An Explore agent hunting the codebase for the next real gap (the hour
task 504 shipped) found a fourth, orthogonal one this check never asked:
whether a real recipe directory carries its own local `README.md` at all.
`CONTRIBUTING.md` calls a recipe's own `README.md` optional, but 37 of
the 38 real recipes wrote one anyway, and `merged-pr-pr-still-open`
(task #419) was the one silent exception -- fully shipped, fully tested,
with a full hand-written paragraph in `fencepost/README.md`'s own
Community recipes section, but nothing in its own directory. This check's
existing three cross-checks were all aimed at the parent README's link
text; none of them ever looked inside a recipe's own directory for a file
named `README.md`, so a recipe missing one read exactly as clean as a
recipe that had one. `missing_readme` closes that -- named, not silently
treated as "optional means untracked."

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
from typing import cast

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
_RECIPE_LINK_RE = re.compile(r"\[`RECIPES/([A-Za-z0-9_-]+)/`\]\(RECIPES/([A-Za-z0-9_-]+)/\)")
_ROADMAP_CITATION_RE = re.compile(r"\(ROADMAP\.md #\d+\)")
# The reference recipe (task 22, CONTRIBUTING.md's own copy-this-shape
# scaffold) is deliberately never called "the Nth" anything and carries no
# ROADMAP citation -- the same hardcoded exception
# test_recipe_ordinal_doctrine.py already holds for the identical reason.
_REFERENCE_RECIPE_SLUG = "example-release-vs-changelog"


def _community_recipes_section(readme_text: str) -> str:
    """The text strictly between the "## Community recipes" header and the
    next `## ` header (or end of file), so a `RECIPES/<slug>/` link
    mentioned in some OTHER section (there are none today, but nothing
    should assume that forever) is never mistaken for one of the seventy-nine community
    recipes this section actually enumerates today. Empty string if the
    header itself is missing -- a real gap, not silently treated as
    vacuously documented. Delegates to `text_patterns.bounded_section`
    (task 552), the shared bounded-section read this file's own docstring
    already claimed to mirror `scopes_completeness_check.py`'s `_section`
    without actually importing it."""
    return text_patterns.bounded_section(readme_text, _SECTION_HEADER)


def _linked_recipes(section_text: str) -> list[tuple[str, str]]:
    """Every `[`RECIPES/<text-slug>/`](RECIPES/<href-slug>/)` pair found in
    the section, in document order, duplicates included -- the caller
    decides what to do with a slug linked more than once."""
    return _RECIPE_LINK_RE.findall(section_text)


def _entry_spans(section_text: str) -> list[tuple[str, str]]:
    """(href-slug, entry_text) for every linked recipe in the section,
    where entry_text runs from that link's own start to the next link's
    start (or the end of the section) -- the same span a human reads as
    "this recipe's own paragraph" before the next one begins. Two links
    for the SAME recipe back to back (a typo, not real today) would each
    get their own span; nothing here assumes one link per slug, `_linked_
    recipes`'s own duplicate-tolerant contract already covers that."""
    link_matches = list(_RECIPE_LINK_RE.finditer(section_text))
    spans = []
    for i, m in enumerate(link_matches):
        start = m.start()
        end = link_matches[i + 1].start() if i + 1 < len(link_matches) else len(section_text)
        spans.append((m.group(2), section_text[start:end]))
    return spans


def _missing_roadmap_citations(section_text: str) -> list[str]:
    """Every numbered (non-reference) recipe entry names its own shipping
    task with a `(ROADMAP.md #NNN)` citation right after its ordinal claim
    -- forty of the forty-one real recipes do; the sole deliberate
    exception is the reference recipe itself (never called "the Nth"
    anything, see `_REFERENCE_RECIPE_SLUG`). Nothing before this task ever
    checked that every OTHER entry actually kept its citation --
    `merged-pr-branch-not-deleted`'s own paragraph (task #514) silently
    shipped without one, the exact "prose claim, nothing re-checked
    against the thing it names" shape this file's other three cross-
    checks already guard against for the link itself, and
    `test_recipe_ordinal_doctrine.py` already guards for the detector.py
    ordinal word -- this is the ROADMAP-citation half of the same
    paragraph neither of those ever read."""
    missing = []
    for slug, entry_text in _entry_spans(section_text):
        if slug == _REFERENCE_RECIPE_SLUG:
            continue
        if not _ROADMAP_CITATION_RE.search(entry_text):
            missing.append(slug)
    return sorted(set(missing))


def check_recipe_readme(
    readme_path: str = DEFAULT_README_PATH,
    fencepost_root: str = DEFAULT_FENCEPOST_ROOT,
) -> dict[str, object]:
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
    missing_readme = sorted(
        slug
        for slug in real_slugs
        if not os.path.isfile(os.path.join(fencepost_root, "RECIPES", slug, "README.md"))
    )
    missing_roadmap_citation = [
        slug for slug in _missing_roadmap_citations(section) if slug in real_slugs
    ]

    clean = not (
        missing_from_readme
        or stale_in_readme
        or mismatched_links
        or missing_readme
        or missing_roadmap_citation
    )
    return {
        "clean": clean,
        "real_count": len(real_slugs),
        "linked_count": len(linked_slugs),
        "missing_from_readme": missing_from_readme,
        "stale_in_readme": stale_in_readme,
        "mismatched_links": mismatched_links,
        "missing_readme": missing_readme,
        "missing_roadmap_citation": missing_roadmap_citation,
    }


def format_result(result: dict[str, object]) -> str:
    if result["clean"]:
        return (
            f"recipe readme: clean ({result['real_count']} real recipe(s), "
            f"fencepost/README.md's Community recipes section names every one, "
            f"no dead links)"
        )
    problems = []
    if result["missing_from_readme"]:
        problems.append(f"unlinked real recipe(s): {', '.join(cast('list[str]', result['missing_from_readme']))}")
    if result["stale_in_readme"]:
        problems.append(
            f"dead link(s) to a recipe that no longer exists: "
            f"{', '.join(cast('list[str]', result['stale_in_readme']))}"
        )
    if result["mismatched_links"]:
        pairs = ", ".join(f"[{t}]->({h})" for t, h in cast("list[tuple[str, str]]", result["mismatched_links"]))
        problems.append(f"link text/href disagree: {pairs}")
    if result["missing_readme"]:
        problems.append(f"recipe dir(s) with no own README.md: {', '.join(cast('list[str]', result['missing_readme']))}")
    if result.get("missing_roadmap_citation"):
        problems.append(
            f"entry(ies) missing a (ROADMAP.md #NNN) citation: "
            f"{', '.join(cast('list[str]', result['missing_roadmap_citation']))}"
        )
    return "recipe readme: BROKEN -- " + "; ".join(problems)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_recipe_readme()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
