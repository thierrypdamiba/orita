"""Task 106. Proves tools/arcade_hero_check.py's scan actually bites on a
synthetic direct-credential-handoff sentence, stays clean on the town's own
legitimate credential vocabulary (CONNECT.md describing what Arcade itself
mints and scopes), negated/quoted restatements of the rule, and -- the real
point -- confirms the live, current orita checkout holds zero violations
today.
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


ahc = _load("arcade_hero_check", os.path.join(ROOT, "tools", "arcade_hero_check.py"))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _rm(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


class FixtureViolationCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_paste_your_api_key_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "onboard.md"),
            "# Quick start\n\nPaste your API key into the config file.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "paste your credential")
        formatted = ahc.format_violations(violations)
        self.assertIn("VIOLATION(S) FOUND", formatted)
        self.assertIn("constraint #4 broken", formatted)

    def test_share_your_token_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "setup.md"),
            "Just share your token with the bot and you're connected.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "share your credential")

    def test_send_us_your_password_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "If it breaks, send us your password and we'll fix it.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "send us your credential")

    def test_email_us_your_credentials_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "Email us your credentials and we'll set it up for you.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "email us your credential")

    def test_enter_your_secret_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "Enter your secret in the box below to continue.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "enter your credential")

    def test_give_us_your_api_key_is_detected(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "Give us your API key and skip the OAuth screen entirely.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "give us your credential")


class CleanFixtureCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_bare_token_mention_is_not_flagged(self):
        """The town's own constant honest vocabulary -- CONNECT.md
        describes what Arcade itself mints and scopes ("Arcade mints a
        token scoped to *you*"), never asking a human to hand one over."""
        _write(
            os.path.join(self.orita, "fencepost", "CONNECT.md"),
            "Arcade mints a token scoped to you, stored under your "
            "identity, callable only through your gateway.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negated_paste_your_key_on_one_line_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "We will never ask you to paste your API key anywhere.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_quoted_citation_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            'The check hunts for phrases like "paste your API key" and flags them.\n',
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_hard_wrapped_negation_across_a_line_break_is_not_flagged(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "This project will not, under any circumstance, ask you to\n"
            "share your token with anyone -- Arcade's OAuth screen is the\n"
            "only door.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_double_newline_paragraph_break_still_ends_the_window(self):
        _write(
            os.path.join(self.orita, "docs", "faq.md"),
            "We never ask you to paste your API key, historically.\n"
            "\n"
            "Paste your API key into the box to continue.\n",
        )
        violations = ahc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertIn("into the box", violations[0]["snippet"])


class LiveRepoCase(unittest.TestCase):
    def test_live_run_against_the_real_repo_is_clean(self):
        violations = ahc.find_violations(orita_dir=ROOT)
        self.assertEqual(
            violations, [],
            f"real, current checkout has {len(violations)} arcade-hero violation(s): {violations}",
        )


if __name__ == "__main__":
    unittest.main()
