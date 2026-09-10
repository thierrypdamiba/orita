"""Proves tools/x_silence_doctrine_check.py actually catches a dropped or
drifted change-gate explanation (the marker sentence missing from either
fencepost/README.md or docs/fencepost/index.html, or the two files no
longer holding it byte-identical), stays clean when both carry the same
sentence, reports a missing file as missing rather than silently skipping
it, and confirms the real, currently committed files are clean right now
(the live gap that motivated building it -- no explanation existed
anywhere a stranger would actually see it -- is fixed, not just
theorized about).
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


xsd = _load("x_silence_doctrine_check", os.path.join(ROOT, "tools", "x_silence_doctrine_check.py"))


def _write(tmpdir, name, text):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class TestCheckXSilenceDoctrine(unittest.TestCase):
    def test_clean_when_both_files_carry_the_identical_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            readme = _write(tmp, "README.md", f"Some prose. @oritatown {xsd.MARKER_SENTENCE} More prose.")
            site = _write(tmp, "index.html", f"<p>@oritatown {xsd.MARKER_SENTENCE}</p>")
            result = xsd.check_x_silence_doctrine(readme_path=readme, site_path=site)
            self.assertTrue(result["clean"])
            self.assertEqual(result["missing"], [])
            self.assertEqual(result["absent"], [])

    def test_drifted_when_readme_has_it_but_site_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            readme = _write(tmp, "README.md", f"@oritatown {xsd.MARKER_SENTENCE}")
            site = _write(tmp, "index.html", "<p>nothing about it here</p>")
            result = xsd.check_x_silence_doctrine(readme_path=readme, site_path=site)
            self.assertFalse(result["clean"])
            self.assertEqual(result["missing"], [])
            self.assertEqual(result["absent"], ["docs/fencepost/index.html"])

    def test_drifted_when_the_sentence_is_paraphrased_not_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            readme = _write(tmp, "README.md", f"@oritatown {xsd.MARKER_SENTENCE}")
            paraphrased = xsd.MARKER_SENTENCE.replace("on purpose", "deliberately")
            site = _write(tmp, "index.html", f"<p>@oritatown {paraphrased}</p>")
            result = xsd.check_x_silence_doctrine(readme_path=readme, site_path=site)
            self.assertFalse(result["clean"])
            self.assertEqual(result["absent"], ["docs/fencepost/index.html"])

    def test_missing_file_is_reported_as_missing_not_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            readme = _write(tmp, "README.md", f"@oritatown {xsd.MARKER_SENTENCE}")
            site = os.path.join(tmp, "does-not-exist.html")
            result = xsd.check_x_silence_doctrine(readme_path=readme, site_path=site)
            self.assertFalse(result["clean"])
            self.assertEqual(result["missing"], ["docs/fencepost/index.html"])
            self.assertEqual(result["absent"], [])

    def test_both_missing_reports_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            readme = os.path.join(tmp, "no-readme.md")
            site = os.path.join(tmp, "no-site.html")
            result = xsd.check_x_silence_doctrine(readme_path=readme, site_path=site)
            self.assertFalse(result["clean"])
            self.assertEqual(set(result["missing"]), {"fencepost/README.md", "docs/fencepost/index.html"})


class TestFormatXSilenceDoctrine(unittest.TestCase):
    def test_clean_message_shape(self):
        msg = xsd.format_x_silence_doctrine({"clean": True, "missing": [], "absent": []})
        self.assertTrue(msg.startswith("x silence doctrine: clean"))

    def test_drifted_message_names_the_files(self):
        msg = xsd.format_x_silence_doctrine(
            {"clean": False, "missing": ["docs/fencepost/index.html"], "absent": []}
        )
        self.assertIn("DRIFTED", msg)
        self.assertIn("docs/fencepost/index.html", msg)


class TestRealFiles(unittest.TestCase):
    def test_the_real_committed_files_are_clean_right_now(self):
        result = xsd.check_x_silence_doctrine()
        self.assertTrue(result["clean"], result)


if __name__ == "__main__":
    unittest.main()
