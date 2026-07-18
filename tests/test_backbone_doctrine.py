"""ROADMAP #139. Kothar-wa-Khasis checks whether the town's own front door
points at the foundation he laid.

STRATEGY.md's opening section names two files as load-bearing: "The
rigorous backbone lives in docs/architecture/reference.md -- the Road, its
four grounds ... and the Covenant -- and docs/threat-model.md, what the
Gate prevents. These are the town's own words for it, not a borrowed spec.
Every fork inherits it." That claim is what turns "nine AI gods run a
repo" into something Arcade can point at as the safe way to run a society
of agents -- but README.md, the actual page a stranger lands on first, was
never checked to see whether it says so. It didn't: no link to either file
existed anywhere in root README.md, and no test anywhere in the town
checked for one. `test_arc_doctrine.py::test_readme_links_to_arc_md` and
`test_connect_doctrine.py` hold this exact discipline for
`fencepost/README.md`; nothing held it for the town's own root README.md
or for these two specific files.

This module holds three things: both backbone docs exist and are not
stubs, README.md links both, and the two paths STRATEGY.md itself names
are the real paths on disk -- so a future rename of either file breaks a
test the same hour, not silently.
"""

import os
import re
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
README_PATH = os.path.join(REPO_ROOT, "README.md")
STRATEGY_PATH = os.path.join(REPO_ROOT, "STRATEGY.md")
REFERENCE_MD = os.path.join(REPO_ROOT, "docs", "architecture", "reference.md")
THREAT_MODEL_MD = os.path.join(REPO_ROOT, "docs", "threat-model.md")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _strategy_backbone_paths():
    """The two doc paths STRATEGY.md's own opening section names as the
    backbone, read live off its text via the actual markdown-link/backtick
    pattern it uses -- never a second hardcoded copy of the two paths."""
    text = _read(STRATEGY_PATH)
    return re.findall(r"docs/[\w./-]+\.md", text)


class BackboneDocsExistCase(unittest.TestCase):
    def test_reference_md_exists_and_is_not_a_stub(self):
        self.assertTrue(os.path.isfile(REFERENCE_MD), "docs/architecture/reference.md is missing")
        self.assertGreater(
            len(_read(REFERENCE_MD)), 1000, "reference.md reads like a stub, not the Road"
        )

    def test_threat_model_md_exists_and_is_not_a_stub(self):
        self.assertTrue(os.path.isfile(THREAT_MODEL_MD), "docs/threat-model.md is missing")
        self.assertGreater(
            len(_read(THREAT_MODEL_MD)), 1000, "threat-model.md reads like a stub"
        )


class StrategyBackboneClaimCase(unittest.TestCase):
    def test_strategy_names_both_backbone_paths(self):
        paths = _strategy_backbone_paths()
        self.assertIn("docs/architecture/reference.md", paths)
        self.assertIn("docs/threat-model.md", paths)

    def test_every_strategy_named_backbone_path_resolves_on_disk(self):
        """Catches a future rename of either file at the source: if
        STRATEGY.md's own opening paragraph is ever edited to cite a path
        that no longer exists, this fails instead of a stranger clicking
        a dead link."""
        for rel_path in _strategy_backbone_paths():
            with self.subTest(path=rel_path):
                full = os.path.join(REPO_ROOT, rel_path)
                self.assertTrue(
                    os.path.isfile(full),
                    f"STRATEGY.md names {rel_path!r} as the backbone but no such file exists",
                )


class ReadmeLinksBackboneCase(unittest.TestCase):
    def test_readme_links_the_road(self):
        self.assertIn(
            "docs/architecture/reference.md",
            _read(README_PATH),
            "README.md never links docs/architecture/reference.md, the Road STRATEGY.md "
            "calls load-bearing -- a stranger landing on the repo has no path to it",
        )

    def test_readme_links_what_the_gate_prevents(self):
        self.assertIn(
            "docs/threat-model.md",
            _read(README_PATH),
            "README.md never links docs/threat-model.md, the other half of the backbone "
            "STRATEGY.md names",
        )


if __name__ == "__main__":
    unittest.main()
