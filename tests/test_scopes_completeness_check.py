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


if __name__ == "__main__":
    unittest.main()
