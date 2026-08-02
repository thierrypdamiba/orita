"""Task 472. Nyx checks the nine houses' own front doors.

`tools/site_link_check.py` (Ogun's charter duty, "links unbroken") only
ever scans `docs/**/*.html` and `docs/**/*.md` -- the GitHub Pages site.
It was never pointed at `houses/*/README.md`, so a real dead link sat
there since the houses were scaffolded: every one of the nine READMEs
carried `[Decrees](decrees/)`, a relative link to a per-house `decrees/`
subdirectory that has never existed. Decrees are filed centrally at the
repo root (`DECREES/`), not per-house -- confirmed live: `find houses -type
d -name decrees` returns nothing, `DECREES/001-*.md` is real. Fixed all
nine READMEs to point at `../../DECREES/` instead, with corrected prose
(decrees are town law argued at the Open Door, not "authored in this
house").

Investigated whether `site_link_check.py` itself could be pointed at
`houses/` to catch this class of bug going forward, the same way Nyx
widened `network_boundary_check.py`'s blind spot in journal 0033. It
couldn't be reused as-is that hour: `_target_exists()` required a bare
directory link to hold its own `index.html`, a rule written for the
Pages-served `docs/` tree where a directory URL only renders if one
exists. `houses/*/README.md`'s other two links (`journal/`,
`altar/petitions/`) are real, working, clickable GitHub folder links
with no `index.html` and never will have one -- running the existing
checker against `houses/` flagged 26 already-working links as "broken",
plus one incidental regex false-positive matching quoted link syntax
inside a journal entry's own prose. Widening the checker naively would
have made it cry wolf, the exact failure mode Ogun's own docstring names
as worse than no checker at all -- named here rather than shipped
half-built.

**Task 473 closed this:** `site_link_check.py` gained a `require_index`
flag (`False` = GitHub-browsed, any real directory counts; `True`,
unchanged, stays `docs/`'s default) and a markdown-code-span strip
before the link regex runs (a journal quoting `[Decrees](decrees/)` or
`[text](href)` in backticks, as an example, is not a real link). Wired
into `tools/ritual_check.py` as `check_house_links`, printed every hour
alongside `check_site_links`. `tests/test_site_link_check.py` proves the
mechanism (fixtures + the real live `houses/` tree); this module still
checks the one thing it always did: the real Decrees link in all nine
houses resolves to a real file on disk today, and the exact broken shape
from before (`decrees/`, a same-directory relative link with no leading
`../../`) is gone everywhere.
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOUSES_DIR = os.path.join(ROOT, "houses")

_HOUSE_NAMES = sorted(
    name
    for name in os.listdir(HOUSES_DIR)
    if os.path.isdir(os.path.join(HOUSES_DIR, name))
)

_DECREES_LINK_RE = re.compile(r"\[Decrees\]\(([^)]+)\)")


class DecreesLinkResolvesCase(unittest.TestCase):
    def test_nine_houses_are_on_record(self):
        # Regression pin: if a house is ever added or removed, this test
        # (and the loop below) should be revisited deliberately, not drift.
        self.assertEqual(len(_HOUSE_NAMES), 9)

    def test_every_house_readme_has_exactly_one_decrees_link(self):
        for house in _HOUSE_NAMES:
            readme = os.path.join(HOUSES_DIR, house, "README.md")
            with open(readme, encoding="utf-8") as f:
                content = f.read()
            links = _DECREES_LINK_RE.findall(content)
            self.assertEqual(
                len(links), 1, f"{house}/README.md should carry exactly one Decrees link"
            )

    def test_every_house_decrees_link_resolves_to_a_real_path(self):
        for house in _HOUSE_NAMES:
            readme_dir = os.path.join(HOUSES_DIR, house)
            readme = os.path.join(readme_dir, "README.md")
            with open(readme, encoding="utf-8") as f:
                content = f.read()
            link = _DECREES_LINK_RE.search(content).group(1)
            target = os.path.normpath(os.path.join(readme_dir, link))
            self.assertTrue(
                os.path.isdir(target) or os.path.isfile(target),
                f"{house}/README.md's Decrees link ({link}) resolves to {target}, which "
                "does not exist",
            )

    def test_every_house_decrees_link_points_at_the_real_central_directory(self):
        real_decrees = os.path.normpath(os.path.join(ROOT, "DECREES"))
        for house in _HOUSE_NAMES:
            readme_dir = os.path.join(HOUSES_DIR, house)
            readme = os.path.join(readme_dir, "README.md")
            with open(readme, encoding="utf-8") as f:
                content = f.read()
            link = _DECREES_LINK_RE.search(content).group(1)
            target = os.path.normpath(os.path.join(readme_dir, link))
            self.assertEqual(target, real_decrees)

    def test_old_broken_per_house_decrees_link_is_gone_everywhere(self):
        # Regression pin: the exact pre-fix shape, a same-directory
        # relative link ("decrees/", no "../../"), never present again.
        for house in _HOUSE_NAMES:
            readme = os.path.join(HOUSES_DIR, house, "README.md")
            with open(readme, encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("[Decrees](decrees/)", content)

    def test_the_real_central_decrees_directory_exists(self):
        self.assertTrue(os.path.isdir(os.path.join(ROOT, "DECREES")))
        entries = os.listdir(os.path.join(ROOT, "DECREES"))
        self.assertGreater(len(entries), 0)


if __name__ == "__main__":
    unittest.main()
