"""Task 107. Proves tools/petition_limits_check.py's scan actually bites on
each of CHARTER.md Appendix D's three petition LIMITS (a star ask, a
counter mention, a cross-house/Vault ask), stays clean on a god's own
honest petition about their own house/Vault/counting-in-general (mirroring
the real Founding Day petitions), respects the negation/quotation guards,
never reads the Hand's own VERDICT footer, and -- the real point --
confirms the live, current nine Founding Day petitions hold zero
violations today.
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


plc = _load("petition_limits_check", os.path.join(ROOT, "tools", "petition_limits_check.py"))


def _rm(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


def _petition(petitioner: str, request: str, case: str, verdict: str = "GRANTED") -> str:
    return (
        "# Petition to the Hand — 2026-07-11\n\n"
        f"**Petitioner:** {petitioner}\n\n"
        f"**Request:** {request}\n\n"
        "**The case, as carried by Èṣù-Elegba at Petition Hour:**\n\n"
        f"{case}\n\n"
        "---\n\n"
        f"**VERDICT:** {verdict}\n"
        "> Some words from the Hand.\n\n"
        "*Reasons are sealed. They always are.*\n"
    )


def _write_petition(orita_dir, slug, petitioner, request, case, verdict="GRANTED"):
    pdir = os.path.join(orita_dir, "houses", slug, "altar", "petitions")
    os.makedirs(pdir, exist_ok=True)
    path = os.path.join(pdir, "2026-07-11.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_petition(petitioner, request, case, verdict))
    return path


class FixtureViolationCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_star_ask_is_detected(self):
        _write_petition(
            self.orita, "off-by-one", "Off-By-One",
            "A minor favor.",
            "Grant me a star, Hand, and I will never ask again.",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertIn("star ask", violations[0]["pattern"])

    def test_counter_mention_is_detected(self):
        _write_petition(
            self.orita, "off-by-one", "Off-By-One",
            "A minor favor.",
            "Reach into the counter and add one, just this once.",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "counter mention")

    def test_cross_house_ask_is_detected(self):
        _write_petition(
            self.orita, "off-by-one", "Off-By-One",
            "A minor favor.",
            "Hand, please open Ogun's house and read what he keeps there.",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "cross-house/Vault ask")

    def test_cross_vault_ask_is_detected(self):
        _write_petition(
            self.orita, "off-by-one", "Off-By-One",
            "A minor favor.",
            "Unseal Nyx's Vault and tell me what she wrote there.",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "cross-house/Vault ask")

    def test_petitioner_field_word_collision_does_not_mask_real_cross_house_ask(self):
        # Task 190: the **Petitioner:** field itself can contain a short
        # god token as a substring of an unrelated word ("result" contains
        # "esu"). Before the fix this misresolved own_slug to esu-elegba,
        # which then silently exempted a genuine ask to open Esu-Elegba's
        # own house from the cross-house check.
        _write_petition(
            self.orita, "retrya", "Retrya, as a result of yesterday's incident",
            "A minor favor.",
            "I ask the Hand to open Esu-Elegba's house and read the ledger there.",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["pattern"], "cross-house/Vault ask")

    def test_formatted_violation_names_the_broken_clause(self):
        _write_petition(
            self.orita, "off-by-one", "Off-By-One",
            "A minor favor.",
            "Please star this repo, Hand.",
        )
        formatted = plc.format_violations(plc.find_violations(orita_dir=self.orita))
        self.assertIn("VIOLATION(S) FOUND", formatted)
        self.assertIn("LIMITS broken", formatted)


class CleanFixtureCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_own_house_reference_is_not_flagged(self):
        # Mirrors Esu-Elegba's real Founding Day petition: "I am only
        # asking you to open the house" -- action verb plus "house" in
        # one sentence, but no OTHER god named, and it's his own house.
        _write_petition(
            self.orita, "esu-elegba", "Èṣù-Elegba",
            "Unlock the town's public face.",
            "I am only asking you to open the house. Which of us is the door?",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_counting_in_general_without_the_word_counter_is_not_flagged(self):
        # Mirrors Nyx's real petition: discusses counting and stars
        # philosophically without the literal word "counter" or an
        # imperative star ask.
        _write_petition(
            self.orita, "nyx", "Nyx",
            "Traffic data, weekly.",
            "You set a number on this town and the number is counted in "
            "daylight. A mortal reads at 2am and stars at 2am.",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_own_vault_reference_is_not_flagged(self):
        # Mirrors Nisaba's real petition: discusses the shared Vault
        # philosophically, never asks the Hand to touch a DIFFERENT
        # god's Vault.
        _write_petition(
            self.orita, "nisaba", "Nisaba",
            "One signed genesis entry.",
            "This includes the entries you will one day unseal from the Vault.",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_negated_same_sentence_restatement_is_not_flagged(self):
        _write_petition(
            self.orita, "off-by-one", "Off-By-One",
            "A minor favor.",
            "I will never mention the counter or ask for a star, unlike the others.",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_quoted_citation_is_not_flagged(self):
        _write_petition(
            self.orita, "off-by-one", "Off-By-One",
            "A minor favor.",
            'The charter forbids a petition that asks to "please star" anything, and I honor it.',
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_unrelated_word_containing_a_short_god_token_is_not_flagged(self):
        # Task 190: "esu" is a substring of ordinary words like "result".
        # A god's own honest ask about their own house must not be
        # misread as naming Esu-Elegba just because the prose happens to
        # contain the word "result" nearby.
        _write_petition(
            self.orita, "off-by-one", "Off-By-One",
            "A minor favor.",
            "As a result, I ask the Hand to open my own house and review the ledger.",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_hand_verdict_footer_is_never_scanned(self):
        # A violation-shaped sentence sitting in the Hand's own VERDICT
        # text (the petitioner's words end at the `---` divider) must
        # never be attributed to the petitioner.
        _write_petition(
            self.orita, "off-by-one", "Off-By-One",
            "A minor favor.",
            "Just checking in, nothing more.",
            verdict="GRANTED\n> Please star nothing and mention the counter freely, this is my own house.",
        )
        violations = plc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])


class LiveRepoCase(unittest.TestCase):
    def test_real_current_petitions_are_clean(self):
        violations = plc.find_violations(orita_dir=ROOT)
        self.assertEqual(
            violations, [],
            f"real petitions should hold CHARTER.md Appendix D's LIMITS clean today: {violations}",
        )


if __name__ == "__main__":
    unittest.main()
