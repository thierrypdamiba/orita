#!/usr/bin/env python3
"""Task 545. Nyx: the episode roll call nobody ever actually took.

`tools/ritual_check.py`'s `check_chronicle_links` (task 524) points
`site_link_check.py` at `chronicle/` and proves every link IN
`chronicle/README.md` resolves to a real file. It never asks the reverse
question: does every real numbered episode ON DISK actually have a link
pointing at it? Those are two different claims -- `recipe_readme_check.py`
(task 426) drew the same distinction for `fencepost/README.md` and built
both directions; `chronicle/README.md` only ever got the one `site_link_
check.py` already covers for every other directory in its family.

Confirmed live before writing this: `chronicle/003-right-on-time.md`
("Episode 3: Right On Time") shipped task 500 (2026-08-03) and has sat on
disk, real and finished, ever since -- but `chronicle/README.md`'s own
"## Episodes" table of contents still lists only Episodes 0-2. A forward
link check reads this as perfectly clean (every link it finds does
resolve); nothing anywhere reads the directory itself and asks whether a
real file went unlisted. `cluster_day_check.py` doesn't catch it either --
it globs `chronicle/NNN-*.md` directly for its own cadence math and never
reads `README.md`'s prose at all.

`chronicle_readme_check.py` reads the SAME live ground truth `cluster_day_
check.py` already trusts (`_episode_numbers()`, never a second hand-typed
list) and structurally parses every `[Episode N: ...](NNN-slug.md)` link
inside the README's own "## Episodes" section (bounded the same
next-`## `-header way `recipe_readme_check.py`'s section reader already
holds), then checks both things a bare "do the existing links resolve"
scan cannot:

1. every real numbered episode has a matching link (`missing_from_readme`
   -- the direction this task's own live find proves was never checked,
   anywhere);
2. every linked episode number still names a real chronicle file
   (`stale_in_readme` -- symmetric with `recipe_readme_check.py`'s own
   `stale_in_readme`, for the day an episode is ever renumbered or removed).

Local-filesystem-only, no network call, the same cheap always-on class
`check_wip_reclaim`/`check_scopes_completeness`/`check_recipe_readme`
already hold.

Usage:
    python3 tools/chronicle_readme_check.py check
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_README_PATH = os.path.join(ROOT, "chronicle", "README.md")
DEFAULT_CHRONICLE_DIR = os.path.join(ROOT, "chronicle")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cluster_day_check  # noqa: E402
import text_patterns  # noqa: E402

_SECTION_HEADER = re.compile(r"^## Episodes\s*$", re.MULTILINE)
_NEXT_HEADER = text_patterns.NEXT_MARKDOWN_HEADER
_EPISODE_LINK_RE = re.compile(r"\[Episode (\d+):[^\]]*\]\(([^)]+)\)")


def _episodes_section(readme_text: str) -> str:
    """The text strictly between the "## Episodes" header and the next
    `## ` header (or end of file) -- the same bounded-section read
    `recipe_readme_check.py`'s `_community_recipes_section` already holds
    for `fencepost/README.md`. Empty string if the header itself is
    missing -- a real gap, not silently treated as vacuously documented."""
    header_match = _SECTION_HEADER.search(readme_text)
    if header_match is None:
        return ""
    start = header_match.end()
    next_match = _NEXT_HEADER.search(readme_text, pos=start)
    end = next_match.start() if next_match else len(readme_text)
    return readme_text[start:end]


def _linked_episode_numbers(section_text: str) -> list[int]:
    """Every `[Episode N: ...](href)` link's own N found in the section,
    in document order, duplicates included -- the caller decides what to
    do with a number linked more than once."""
    return [int(num) for num, _href in _EPISODE_LINK_RE.findall(section_text)]


def check_chronicle_readme(
    readme_path: str = DEFAULT_README_PATH,
    chronicle_dir: str = DEFAULT_CHRONICLE_DIR,
) -> dict:
    """Cross-check `chronicle/README.md`'s "## Episodes" section against
    the real, live `chronicle/` tree (`cluster_day_check._episode_numbers`,
    never a second hand-typed list). Returns `clean: True` only when every
    real episode is linked and every link names a real episode; otherwise
    `clean: False` naming exactly which episode numbers are missing or
    stale, never a bare pass/fail."""
    with open(readme_path, encoding="utf-8") as f:
        readme_text = f.read()
    section = _episodes_section(readme_text)
    linked_numbers = set(_linked_episode_numbers(section))

    real_numbers = set(cluster_day_check._episode_numbers(chronicle_dir))

    missing_from_readme = sorted(real_numbers - linked_numbers)
    stale_in_readme = sorted(linked_numbers - real_numbers)

    clean = not (missing_from_readme or stale_in_readme)
    return {
        "clean": clean,
        "real_count": len(real_numbers),
        "linked_count": len(linked_numbers),
        "missing_from_readme": missing_from_readme,
        "stale_in_readme": stale_in_readme,
    }


def format_result(result: dict) -> str:
    if result["clean"]:
        return (
            f"chronicle readme: clean ({result['real_count']} real episode(s), "
            f"chronicle/README.md's Episodes section names every one)"
        )
    problems = []
    if result["missing_from_readme"]:
        nums = ", ".join(str(n) for n in result["missing_from_readme"])
        problems.append(f"unlinked real episode(s): {nums}")
    if result["stale_in_readme"]:
        nums = ", ".join(str(n) for n in result["stale_in_readme"])
        problems.append(f"link(s) to an episode that no longer exists: {nums}")
    return "chronicle readme: BROKEN -- " + "; ".join(problems)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_chronicle_readme()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
