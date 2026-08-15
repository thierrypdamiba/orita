"""Task 135. Proves tools/scopes_completeness_check.py parses the new
`## Every connected app, accounted for` section structurally, flags a
connected app_id missing from that section by name, and confirms the
live, current fencepost/SCOPES.md accounts for every app_id the real
arcade_app_watch.py log currently knows.
"""
import importlib.util
import json
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


scc = _load("scopes_completeness_check", os.path.join(ROOT, "tools", "scopes_completeness_check.py"))
import arcade_app_watch  # noqa: E402

_SAMPLE_SECTION = """## Every connected app, accounted for

| app_id | status |
|--|--|
| `arcade-github` | in use by Fencepost |
| `arcade-linear` | connected on the shared gateway, NOT used by Fencepost, no toolkit integration planned |

## The oath

1. some other section
"""


class SectionParsingCase(unittest.TestCase):
    def test_extracts_app_ids_from_table_rows(self):
        ids = scc._accounted_for_app_ids(_SAMPLE_SECTION)
        self.assertEqual(ids, {"arcade-github", "arcade-linear"})

    def test_stops_at_next_header_never_reads_past_section(self):
        text = _SAMPLE_SECTION + "\n| `arcade-slack` | in another section entirely, must not count |\n"
        ids = scc._accounted_for_app_ids(text)
        self.assertNotIn("arcade-slack", ids)

    def test_missing_section_returns_empty_set_not_error(self):
        ids = scc._accounted_for_app_ids("# some doc with no matching section\n")
        self.assertEqual(ids, set())


class MissingAppDetectionCase(unittest.TestCase):
    def _write(self, tmpdir, scopes_text, connected_app_ids):
        scopes_path = os.path.join(tmpdir, "SCOPES.md")
        with open(scopes_path, "w") as f:
            f.write(scopes_text)
        log_path = os.path.join(tmpdir, "log.jsonl")
        with open(log_path, "w") as f:
            f.write(json.dumps({"connected_app_ids": connected_app_ids, "checked_at": "2026-07-18T17:00:00+00:00"}) + "\n")
        return scopes_path, log_path

    def test_clean_when_every_connected_app_is_named(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path, log_path = self._write(tmpdir, _SAMPLE_SECTION, ["arcade-github", "arcade-linear"])
            result = scc.check_scopes_completeness(scopes_path=scopes_path, app_log_path=log_path)
            self.assertTrue(result["clean"])
            self.assertEqual(result["missing"], [])

    def test_flags_connected_app_missing_from_doc_by_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path, log_path = self._write(
                tmpdir, _SAMPLE_SECTION, ["arcade-github", "arcade-linear", "arcade-slack"]
            )
            result = scc.check_scopes_completeness(scopes_path=scopes_path, app_log_path=log_path)
            self.assertFalse(result["clean"])
            self.assertEqual(result["missing"], ["arcade-slack"])

    def test_flags_multiple_missing_apps_all_named(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path, log_path = self._write(tmpdir, _SAMPLE_SECTION, ["arcade-github", "sybill", "brand-new-app"])
            result = scc.check_scopes_completeness(scopes_path=scopes_path, app_log_path=log_path)
            self.assertFalse(result["clean"])
            self.assertEqual(result["missing"], ["brand-new-app", "sybill"])

    def test_no_connection_log_at_all_reads_clean_not_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path = os.path.join(tmpdir, "SCOPES.md")
            with open(scopes_path, "w") as f:
                f.write(_SAMPLE_SECTION)
            missing_log_path = os.path.join(tmpdir, "does-not-exist.jsonl")
            result = scc.check_scopes_completeness(scopes_path=scopes_path, app_log_path=missing_log_path)
            self.assertTrue(result["clean"])
            self.assertEqual(result["connected_app_ids"], [])

    def test_last_line_of_log_wins_over_earlier_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path = os.path.join(tmpdir, "SCOPES.md")
            with open(scopes_path, "w") as f:
                f.write(_SAMPLE_SECTION)
            log_path = os.path.join(tmpdir, "log.jsonl")
            with open(log_path, "w") as f:
                f.write(json.dumps({"connected_app_ids": ["arcade-slack"], "checked_at": "2026-07-18T16:00:00+00:00"}) + "\n")
                f.write(json.dumps({"connected_app_ids": ["arcade-github"], "checked_at": "2026-07-18T17:00:00+00:00"}) + "\n")
            result = scc.check_scopes_completeness(scopes_path=scopes_path, app_log_path=log_path)
            self.assertTrue(result["clean"])
            self.assertEqual(result["connected_app_ids"], ["arcade-github"])

    def test_malformed_last_line_raises_tamper_error_not_json_decode_error(self):
        """A truncated/malformed last line must never crash this checker
        with a raw json.JSONDecodeError -- it should read through
        arcade_app_watch.py's own guarded last_app_state(), which raises
        the intended ArcadeAppWatchTamperedError instead."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "log.jsonl")
            with open(log_path, "w") as f:
                f.write(json.dumps({"connected_app_ids": ["arcade-github"]}) + "\n")
                f.write("{truncated garbage not json")
            with self.assertRaises(arcade_app_watch.ArcadeAppWatchTamperedError):
                scc._last_connected_app_ids(log_path)


class StaleGoogleClaimCase(unittest.TestCase):
    """Task 542. `arcade-google`'s row naming the app_id was never the
    whole claim -- what the status text SAYS about it can go stale too.
    A row claiming "in use by Fencepost" while the last recorded
    `gateway_toolset_check` shows zero live Gmail/Calendar tools is a
    real, false public claim, and `check_scopes_completeness` must catch
    it by content, not just by app_id presence."""

    _STALE_SECTION = """## Every connected app, accounted for

| app_id | status |
|--|--|
| `arcade-github` | in use by Fencepost |
| `arcade-google` | in use by Fencepost |

## The oath

1. some other section
"""

    _HONEST_SECTION = """## Every connected app, accounted for

| app_id | status |
|--|--|
| `arcade-github` | in use by Fencepost |
| `arcade-google` | connected upstream, NOT used by Fencepost yet -- zero Gmail/Calendar tools live |

## The oath

1. some other section
"""

    def _write(self, tmpdir, scopes_text, connected_app_ids, has_gmail_calendar_tools):
        scopes_path = os.path.join(tmpdir, "SCOPES.md")
        with open(scopes_path, "w") as f:
            f.write(scopes_text)
        app_log_path = os.path.join(tmpdir, "app-log.jsonl")
        with open(app_log_path, "w") as f:
            f.write(json.dumps({"connected_app_ids": connected_app_ids, "checked_at": "2026-08-05T02:00:00+00:00"}) + "\n")
        toolset_log_path = os.path.join(tmpdir, "toolset-log.jsonl")
        with open(toolset_log_path, "w") as f:
            f.write(json.dumps({
                "has_gmail_calendar_tools": has_gmail_calendar_tools,
                "matched_tools": [],
                "checked_at": "2026-08-05T02:00:00+00:00",
            }) + "\n")
        return scopes_path, app_log_path, toolset_log_path

    def test_stale_in_use_claim_while_zero_tools_live_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path, app_log_path, toolset_log_path = self._write(
                tmpdir, self._STALE_SECTION, ["arcade-github", "arcade-google"], has_gmail_calendar_tools=False
            )
            result = scc.check_scopes_completeness(
                scopes_path=scopes_path, app_log_path=app_log_path, toolset_log_path=toolset_log_path
            )
            self.assertTrue(result["stale_google_claim"])
            self.assertFalse(result["clean"])

    def test_honest_not_yet_used_wording_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path, app_log_path, toolset_log_path = self._write(
                tmpdir, self._HONEST_SECTION, ["arcade-github", "arcade-google"], has_gmail_calendar_tools=False
            )
            result = scc.check_scopes_completeness(
                scopes_path=scopes_path, app_log_path=app_log_path, toolset_log_path=toolset_log_path
            )
            self.assertFalse(result["stale_google_claim"])
            self.assertTrue(result["clean"])

    def test_in_use_claim_is_true_once_tools_actually_go_live(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path, app_log_path, toolset_log_path = self._write(
                tmpdir, self._STALE_SECTION, ["arcade-github", "arcade-google"], has_gmail_calendar_tools=True
            )
            result = scc.check_scopes_completeness(
                scopes_path=scopes_path, app_log_path=app_log_path, toolset_log_path=toolset_log_path
            )
            self.assertFalse(result["stale_google_claim"])
            self.assertTrue(result["clean"])

    def test_no_toolset_check_ever_recorded_is_not_flagged(self):
        """Silence about the toolset isn't a lie -- only a claim would be.
        No prior gateway_toolset_check means nothing to compare against."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path, app_log_path, _ = self._write(
                tmpdir, self._STALE_SECTION, ["arcade-github", "arcade-google"], has_gmail_calendar_tools=False
            )
            missing_toolset_log_path = os.path.join(tmpdir, "does-not-exist.jsonl")
            result = scc.check_scopes_completeness(
                scopes_path=scopes_path, app_log_path=app_log_path, toolset_log_path=missing_toolset_log_path
            )
            self.assertFalse(result["stale_google_claim"])

    def test_format_result_names_the_stale_claim(self):
        msg = scc.format_result({
            "clean": False, "connected_app_ids": ["arcade-google"],
            "accounted_for_app_ids": ["arcade-google"], "missing": [],
            "stale_google_claim": True,
        })
        self.assertIn("stale", msg.lower())


class RealDocCase(unittest.TestCase):
    """The real point: today's real fencepost/SCOPES.md accounts for every
    app_id the real arcade_app_watch.py log currently knows, and hand-
    removing one from a temp copy of the doc flips the check from clean
    to broken and back."""

    def test_real_scopes_doc_accounts_for_every_real_connected_app(self):
        result = scc.check_scopes_completeness()
        self.assertTrue(result["clean"], msg=f"undocumented: {result['missing']}")
        self.assertGreater(len(result["connected_app_ids"]), 0)

    def test_removing_one_app_from_a_temp_copy_flips_clean_to_broken_and_back(self):
        with open(scc.DEFAULT_SCOPES_PATH, encoding="utf-8") as f:
            real_text = f.read()
        real_result = scc.check_scopes_completeness()
        victim = real_result["connected_app_ids"][0]
        with tempfile.TemporaryDirectory() as tmpdir:
            broken_path = os.path.join(tmpdir, "SCOPES.md")
            with open(broken_path, "w") as f:
                f.write(real_text.replace(f"`{victim}`", "`REMOVED-FOR-TEST`"))
            broken_result = scc.check_scopes_completeness(
                scopes_path=broken_path, app_log_path=scc.DEFAULT_APP_LOG_PATH
            )
            self.assertFalse(broken_result["clean"])
            self.assertIn(victim, broken_result["missing"])

            restored_path = os.path.join(tmpdir, "SCOPES-restored.md")
            with open(restored_path, "w") as f:
                f.write(real_text)
            restored_result = scc.check_scopes_completeness(
                scopes_path=restored_path, app_log_path=scc.DEFAULT_APP_LOG_PATH
            )
            self.assertTrue(restored_result["clean"])


class ToolkitCountClaimCase(unittest.TestCase):
    """Task 781 (Esu-Elegba). `SCOPES.md`'s own "Task 135. The table above
    names the {N} toolkits..." sentence had said "four" since the day it
    was written, while tasks 599/600 later grew the "Concretely, on the
    toolkits in use:" table it describes to six rows (Slack, Linear) --
    nothing had ever counted the table's real rows against that sentence's
    number-word, so the two silently disagreed for weeks. These tests
    prove `_toolkit_table_row_count`/`_claimed_toolkit_count` read the
    live table and the live claim independently, and that
    `check_scopes_completeness` flips `stale_toolkit_count_claim` (and
    therefore `clean`) the moment they disagree -- never silently, and
    never conflated with `stale_google_claim`'s own, different staleness
    class in the same result dict."""

    _TABLE_TEXT = """Concretely, on the toolkits in use:

| toolkit | Fencepost uses | Fencepost may NEVER use |
|--|--|--|
| GitHub | GetRepository | CreateFile |
| X | GetUserTweets | PostTweet |
| Gmail (v0.2) | ListEmails | SendEmail |
| Google Calendar (v0.2) | ListEvents | CreateEvent |
| Slack (proposed) | SearchChannelMessages | PostMessage |
| Linear (proposed) | SearchIssueComments | CreateIssue |

**WIP note (ROADMAP.md #653):** some unrelated trailing prose that must
never be counted as a seventh table row.

## Every connected app, accounted for

*Task 135. The table above names the {word} toolkits Fencepost's own code
uses. It says nothing about what else the shared gateway can reach.*

| app_id | status |
|--|--|
| `arcade-github` | in use by Fencepost |

## The oath

1. some other section
"""

    def _scopes_text(self, word):
        return self._TABLE_TEXT.format(word=word)

    def _write(self, tmpdir, word, connected_app_ids=("arcade-github",)):
        scopes_path = os.path.join(tmpdir, "SCOPES.md")
        with open(scopes_path, "w") as f:
            f.write(self._scopes_text(word))
        log_path = os.path.join(tmpdir, "log.jsonl")
        with open(log_path, "w") as f:
            f.write(json.dumps({"connected_app_ids": list(connected_app_ids), "checked_at": "2026-08-15T22:00:00+00:00"}) + "\n")
        return scopes_path, log_path

    def test_live_table_row_count_is_six_never_hardcoded(self):
        self.assertEqual(scc._toolkit_table_row_count(self._scopes_text("six")), 6)

    def test_trailing_wip_note_prose_is_not_counted_as_a_row(self):
        text = self._scopes_text("six")
        self.assertIn("WIP note", text)
        self.assertEqual(scc._toolkit_table_row_count(text), 6)

    def test_missing_table_reads_zero_not_error(self):
        self.assertEqual(scc._toolkit_table_row_count("# no table here\n"), 0)

    def test_claimed_count_parses_the_number_word(self):
        self.assertEqual(scc._claimed_toolkit_count(self._scopes_text("six")), 6)
        self.assertEqual(scc._claimed_toolkit_count(self._scopes_text("four")), 4)

    def test_missing_claim_sentence_returns_none_not_error(self):
        self.assertIsNone(scc._claimed_toolkit_count("# no claim sentence here\n"))

    def test_matching_claim_reads_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path, log_path = self._write(tmpdir, "six")
            result = scc.check_scopes_completeness(scopes_path=scopes_path, app_log_path=log_path)
            self.assertFalse(result["stale_toolkit_count_claim"])
            self.assertTrue(result["clean"])
            self.assertEqual(result["claimed_toolkit_count"], 6)
            self.assertEqual(result["live_toolkit_count"], 6)

    def test_stale_four_claim_against_a_live_six_row_table_is_flagged(self):
        """The exact real-world drift this task found: the sentence still
        said "four" after the table had grown to six rows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path, log_path = self._write(tmpdir, "four")
            result = scc.check_scopes_completeness(scopes_path=scopes_path, app_log_path=log_path)
            self.assertTrue(result["stale_toolkit_count_claim"])
            self.assertFalse(result["clean"])
            self.assertEqual(result["claimed_toolkit_count"], 4)
            self.assertEqual(result["live_toolkit_count"], 6)
            self.assertIn("stale toolkit-count claim", scc.format_result(result))

    def test_stale_claim_is_reported_even_with_zero_connected_apps(self):
        """The claim is about SCOPES.md's own table, independent of
        anything in arcade_app_watch.py's connected-apps log -- must not
        be masked by the "no apps recorded as connected" clean-looking
        path the way `format_ritual_check`'s old branch order could have
        let happen before this task reordered it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scopes_path, log_path = self._write(tmpdir, "four", connected_app_ids=())
            result = scc.check_scopes_completeness(scopes_path=scopes_path, app_log_path=log_path)
            self.assertEqual(result["connected_app_ids"], [])
            self.assertTrue(result["stale_toolkit_count_claim"])
            self.assertFalse(result["clean"])

    def test_real_live_scopes_md_claim_matches_its_own_real_table(self):
        """Hand-verification against the actual repo file: proves this
        task's own fix (four -> six) is real, not just true against a
        synthetic fixture."""
        result = scc.check_scopes_completeness()
        self.assertFalse(result["stale_toolkit_count_claim"])
        self.assertEqual(result["claimed_toolkit_count"], 6)
        self.assertEqual(result["live_toolkit_count"], 6)

    def test_mutating_the_real_file_back_to_four_is_caught(self):
        """The same before/after discipline `test_consent_doctrine.py`'s
        own `test_parser_actually_detects_drift_not_just_tautologically_
        passes` holds itself to: mutate a COPY of the real, live SCOPES.md
        the exact way it read before this task's fix, and prove the real
        parser used above disagrees -- so this file's silence on a future
        drift can't be mistaken for a check that would pass no matter what
        the doc said."""
        with open(scc.DEFAULT_SCOPES_PATH, encoding="utf-8") as f:
            real_text = f.read()
        real_sentence = "table above names the six toolkits"
        self.assertIn(real_sentence, real_text, "SCOPES.md's claim sentence has already changed shape -- update this fixture")
        mutated_text = real_text.replace(real_sentence, "table above names the four toolkits")
        self.assertNotEqual(mutated_text, real_text)
        with tempfile.TemporaryDirectory() as tmpdir:
            mutated_path = os.path.join(tmpdir, "SCOPES.md")
            with open(mutated_path, "w") as f:
                f.write(mutated_text)
            result = scc.check_scopes_completeness(scopes_path=mutated_path, app_log_path=scc.DEFAULT_APP_LOG_PATH)
            self.assertTrue(result["stale_toolkit_count_claim"])
            self.assertEqual(result["claimed_toolkit_count"], 4)
            self.assertEqual(result["live_toolkit_count"], 6)


if __name__ == "__main__":
    unittest.main()
