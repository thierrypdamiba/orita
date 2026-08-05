"""Task 545. Proves tools/chronicle_readme_check.py cross-checks
chronicle/README.md's Episodes section against the live chronicle/ tree
in BOTH directions: every real numbered episode is linked, and every
link points at a real episode -- the reverse direction check_chronicle_
links' forward-only link scan never covered.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


crc = _load("chronicle_readme_check", os.path.join(ROOT, "tools", "chronicle_readme_check.py"))

_SAMPLE_SECTION = """## Episodes

Some intro prose.

- **[Episode 0: The Casting](000-the-casting.md)** — nine gods found.
- **[Episode 1: The Founding](001-the-founding.md)** — nine addresses.

## How to follow the story

Not this section's problem.
"""


class SectionParsingCase(unittest.TestCase):
    def test_extracts_bounded_section_only(self):
        section = crc._episodes_section(_SAMPLE_SECTION)
        self.assertIn("The Casting", section)
        self.assertIn("The Founding", section)
        self.assertNotIn("Not this section's problem", section)

    def test_missing_header_returns_empty_string_not_error(self):
        section = crc._episodes_section("# some doc with no matching section\n")
        self.assertEqual(section, "")

    def test_linked_episode_numbers_extracts_every_number(self):
        section = crc._episodes_section(_SAMPLE_SECTION)
        self.assertEqual(crc._linked_episode_numbers(section), [0, 1])

    def test_a_link_outside_the_section_is_never_counted(self):
        text = _SAMPLE_SECTION + "\n- **[Episode 9: Elsewhere](009-elsewhere.md)** — in another section.\n"
        section = crc._episodes_section(text)
        self.assertNotIn(9, crc._linked_episode_numbers(section))


class CrossCheckCase(unittest.TestCase):
    def _fixture(self, readme_text, episode_nums):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, tmpdir, ignore_errors=True)
        for num in episode_nums:
            with open(os.path.join(tmpdir, f"{num:03d}-ep.md"), "w", encoding="utf-8") as f:
                f.write(f"# Episode {num}\n")
        readme_path = os.path.join(tmpdir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_text)
        return readme_path, tmpdir

    def test_matching_readme_and_disk_is_clean(self):
        readme_path, chronicle_dir = self._fixture(_SAMPLE_SECTION, [0, 1])
        result = crc.check_chronicle_readme(readme_path=readme_path, chronicle_dir=chronicle_dir)
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_from_readme"], [])
        self.assertEqual(result["stale_in_readme"], [])
        self.assertEqual(result["real_count"], 2)
        self.assertEqual(result["linked_count"], 2)

    def test_real_episode_never_linked_is_caught(self):
        # Episode 2 exists on disk but the README's Episodes section
        # never mentions it -- the exact live gap task 545 found in
        # chronicle/README.md for the real Episode 3.
        readme_path, chronicle_dir = self._fixture(_SAMPLE_SECTION, [0, 1, 2])
        result = crc.check_chronicle_readme(readme_path=readme_path, chronicle_dir=chronicle_dir)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_readme"], [2])
        self.assertEqual(result["stale_in_readme"], [])

    def test_stale_link_to_a_removed_episode_is_caught(self):
        # Episode 1 is linked in the README but has no file on disk.
        readme_path, chronicle_dir = self._fixture(_SAMPLE_SECTION, [0])
        result = crc.check_chronicle_readme(readme_path=readme_path, chronicle_dir=chronicle_dir)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_readme"], [])
        self.assertEqual(result["stale_in_readme"], [1])

    def test_real_tree_is_clean_after_task_545s_own_fix(self):
        """The live cross-check this task exists to run: chronicle/
        README.md against the real chronicle/ directory, unmodified."""
        result = crc.check_chronicle_readme()
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_from_readme"], [])
        self.assertEqual(result["stale_in_readme"], [])
        self.assertGreaterEqual(result["real_count"], 4)


class FormatResultCase(unittest.TestCase):
    def test_clean_result_names_the_count(self):
        formatted = crc.format_result(
            {"clean": True, "real_count": 4, "linked_count": 4, "missing_from_readme": [], "stale_in_readme": []}
        )
        self.assertIn("clean", formatted)
        self.assertIn("4 real episode", formatted)

    def test_broken_result_names_missing_and_stale(self):
        formatted = crc.format_result(
            {
                "clean": False,
                "real_count": 2,
                "linked_count": 2,
                "missing_from_readme": [3],
                "stale_in_readme": [9],
            }
        )
        self.assertIn("BROKEN", formatted)
        self.assertIn("unlinked real episode(s): 3", formatted)
        self.assertIn("no longer exists: 9", formatted)


if __name__ == "__main__":
    unittest.main()
