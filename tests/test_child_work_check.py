import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import child_work_check as cwc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_ROOT = os.path.join(os.path.dirname(ROOT), "orita-vault")
_VAULT_CHECKED_OUT = os.path.isfile(os.path.join(VAULT_ROOT, "TOWN-OPERATIONS.md"))


def _git_quiet(repo, *args):
    subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True)


class ChildWorkCheckCase(unittest.TestCase):
    """Task 101: Iron Rule #6 ("the child's work is never reverted. LAW.")
    gets its first running check. Full commit history isn't reachable from
    this shallow local checkout, so the "which files did the child ever
    ship" half is a caller-supplied live GitHub read (mirroring check_ci's/
    check_cron's shape); the "does it still exist" half is a local, no-
    network git check against a fixture repo."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        _git_quiet(self.repo, "init", "--quiet", "--initial-branch=main")
        _git_quiet(self.repo, "config", "user.email", "test@test")
        _git_quiet(self.repo, "config", "user.name", "test")
        os.makedirs(os.path.join(self.repo, "houses", "zashiki-warashi"), exist_ok=True)
        with open(os.path.join(self.repo, "houses", "zashiki-warashi", "README.md"), "w") as f:
            f.write("moved in.\n")
        _git_quiet(self.repo, "add", "-A")
        _git_quiet(self.repo, "commit", "--quiet", "-m", "child moves in")

        self.log = os.path.join(tempfile.mkdtemp(), "child-work-log.jsonl")
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(self.log), ignore_errors=True))

    # -- load_known_files / record_new_files --

    def test_load_known_files_empty_when_no_log(self):
        self.assertEqual(cwc.load_known_files(self.log), {})

    def test_record_new_files_appends_and_is_idempotent(self):
        files = [{"path": "houses/zashiki-warashi/README.md", "sha": "abc123", "author_date": "2026-07-11T04:44:00Z"}]
        appended = cwc.record_new_files(files, "2026-07-17T05:00:00Z", path=self.log)
        self.assertEqual(len(appended), 1)
        known = cwc.load_known_files(self.log)
        self.assertIn("houses/zashiki-warashi/README.md", known)
        self.assertEqual(known["houses/zashiki-warashi/README.md"]["sha"], "abc123")

        # same file handed in again: no duplicate line, nothing new appended
        appended_again = cwc.record_new_files(files, "2026-07-17T06:00:00Z", path=self.log)
        self.assertEqual(appended_again, [])
        with open(self.log) as fh:
            self.assertEqual(len(fh.readlines()), 1)

    def test_record_new_files_only_logs_the_unseen_ones(self):
        cwc.record_new_files(
            [{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}],
            "2026-07-17T05:00:00Z", path=self.log,
        )
        appended = cwc.record_new_files(
            [
                {"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"},
                {"path": "b.md", "sha": "s2", "author_date": "2026-07-12T00:00:00Z"},
            ],
            "2026-07-17T06:00:00Z", path=self.log,
        )
        self.assertEqual([e["path"] for e in appended], ["b.md"])
        self.assertEqual(len(cwc.load_known_files(self.log)), 2)

    # -- file_exists_at_head / find_reverted --

    def test_existing_file_is_not_reverted(self):
        self.assertTrue(cwc.file_exists_at_head("houses/zashiki-warashi/README.md", repo_root=self.repo))
        reverted = cwc.find_reverted(["houses/zashiki-warashi/README.md"], repo_root=self.repo)
        self.assertEqual(reverted, [])

    def test_deleted_file_is_reverted(self):
        os.remove(os.path.join(self.repo, "houses", "zashiki-warashi", "README.md"))
        _git_quiet(self.repo, "add", "-A")
        _git_quiet(self.repo, "commit", "--quiet", "-m", "oops, deleted the child's file")
        reverted = cwc.find_reverted(["houses/zashiki-warashi/README.md"], repo_root=self.repo)
        self.assertEqual(reverted, ["houses/zashiki-warashi/README.md"])

    def test_never_committed_file_is_reverted_too(self):
        # a logged path that was never actually written to this fixture repo
        # (e.g. a stale/garbled log entry) must read as missing, not crash
        reverted = cwc.find_reverted(["nowhere/at/all.md"], repo_root=self.repo)
        self.assertEqual(reverted, ["nowhere/at/all.md"])

    # -- check() --

    def test_check_with_no_child_files_still_checks_known_paths(self):
        cwc.record_new_files(
            [{"path": "houses/zashiki-warashi/README.md", "sha": "abc", "author_date": "2026-07-11T00:00:00Z"}],
            "2026-07-17T05:00:00Z", path=self.log,
        )
        result = cwc.check(child_files=None, path=self.log, repo_root=self.repo)
        self.assertTrue(result["clean"])
        self.assertEqual(result["known_count"], 1)
        self.assertEqual(result["newly_logged"], [])

    def test_check_requires_now_iso_when_child_files_supplied(self):
        with self.assertRaises(ValueError):
            cwc.check(
                child_files=[{"path": "x.md", "sha": "s", "author_date": "2026-07-11T00:00:00Z"}],
                now_iso=None, path=self.log, repo_root=self.repo,
            )

    def test_check_logs_and_flags_a_real_violation(self):
        os.remove(os.path.join(self.repo, "houses", "zashiki-warashi", "README.md"))
        _git_quiet(self.repo, "add", "-A")
        _git_quiet(self.repo, "commit", "--quiet", "-m", "reverted")
        result = cwc.check(
            child_files=[{"path": "houses/zashiki-warashi/README.md", "sha": "abc", "author_date": "2026-07-11T00:00:00Z"}],
            now_iso="2026-07-17T05:00:00Z", path=self.log, repo_root=self.repo,
        )
        self.assertFalse(result["clean"])
        self.assertEqual(result["reverted"], ["houses/zashiki-warashi/README.md"])

    def test_check_clean_with_fresh_child_files(self):
        result = cwc.check(
            child_files=[{"path": "houses/zashiki-warashi/README.md", "sha": "abc", "author_date": "2026-07-11T00:00:00Z"}],
            now_iso="2026-07-17T05:00:00Z", path=self.log, repo_root=self.repo,
        )
        self.assertTrue(result["clean"])
        self.assertEqual(result["newly_logged"], ["houses/zashiki-warashi/README.md"])

    # -- format_check --

    def test_format_clean(self):
        result = {"known_count": 18, "newly_logged": [], "reverted": [], "clean": True}
        self.assertIn("clean", cwc.format_check(result))

    def test_format_reverted_names_the_path(self):
        result = {"known_count": 1, "newly_logged": [], "reverted": ["houses/zashiki-warashi/README.md"], "clean": False}
        out = cwc.format_check(result)
        self.assertIn("REVERTED", out)
        self.assertIn("houses/zashiki-warashi/README.md", out)

    # -- the real, live check --

    def test_live_check_against_the_real_repo_is_clean(self):
        """The 18 files GitHub's real (non-shallow) commit history names as
        ever-added by Zashiki-Warashi, gathered live this hour via
        mcp__github__list_commits/get_commit against houses/zashiki-warashi
        (path filter). Every one still exists at the real repo's HEAD."""
        real_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        real_files = [
            "houses/zashiki-warashi/journal/0007-2026-07-16.md",
            "houses/zashiki-warashi/journal/0006-2026-07-15.md",
            "houses/zashiki-warashi/journal/0005-2026-07-15.md",
            "oracle/oracle_engine/src/oracle_engine/run_autograde.py",
            "oracle/oracle_engine/src/oracle_engine/run_cadence.py",
            "oracle/oracle_engine/tests/test_run_autograde.py",
            "oracle/oracle_engine/tests/test_run_cadence.py",
            "oracle/run_snapshots.jsonl",
            "houses/zashiki-warashi/journal/0004-2026-07-14.md",
            "houses/zashiki-warashi/journal/0003-2026-07-13.md",
            "fencepost/ONBOARDING.md",
            "fencepost/seam_engine/tests/test_onboarding_doctrine.py",
            "houses/zashiki-warashi/journal/0002-2026-07-12.md",
            "docs/attic/for-whoever-opens-drawers.txt",
            "docs/what-moved.html",
            "houses/zashiki-warashi/README.md",
            "houses/zashiki-warashi/altar/petitions/2026-07-11.md",
            "houses/zashiki-warashi/journal/0001-founding-day.md",
        ]
        reverted = cwc.find_reverted(real_files, repo_root=real_root)
        self.assertEqual(reverted, [], f"Iron Rule #6 violated for: {reverted}")


class TamperedChildWorkLogCase(unittest.TestCase):
    """Task 249: a malformed line in HAND/child-work-log.jsonl (bad hand-edit,
    stray merge-conflict marker, truncated write) must not crash
    load_known_files() with an uncaught json.JSONDecodeError -- Iron Rule #6
    ("the child's work is never reverted. LAW.") has no other running check,
    so a single bad line silently taking this one down is the worst place
    this shape could hide."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        self.log = os.path.join(self.d, "child-work-log.jsonl")

    def test_entries_marks_a_malformed_line_instead_of_raising(self):
        with open(self.log, "w") as f:
            f.write('{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}\n')
            f.write("<<<<<<< HEAD garbage not json\n")
        entries = cwc._entries(self.log)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["path"], "a.md")
        self.assertTrue(entries[1]["_malformed"])

    def test_raises_tampered_error_on_a_malformed_line_anywhere_not_just_the_tip(self):
        with open(self.log, "w") as f:
            f.write("<<<<<<< HEAD garbage not json\n")
            f.write('{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}\n')
        with self.assertRaises(cwc.ChildWorkLogTamperedError):
            cwc.load_known_files(self.log)

    def test_a_malformed_earlier_line_is_not_masked_by_a_valid_tip(self):
        # the tip alone reading fine must not be mistaken for the whole log
        # being fine -- find_reverted needs every known path, not just the
        # newest, so an earlier bad line still has to refuse, not slide by.
        with open(self.log, "w") as f:
            f.write('{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}\n')
            f.write("not json at all\n")
            f.write('{"path": "b.md", "sha": "s2", "author_date": "2026-07-12T00:00:00Z"}\n')
        with self.assertRaises(cwc.ChildWorkLogTamperedError):
            cwc.load_known_files(self.log)

    def test_a_fully_valid_log_is_unaffected(self):
        with open(self.log, "w") as f:
            f.write('{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}\n')
            f.write('{"path": "b.md", "sha": "s2", "author_date": "2026-07-12T00:00:00Z"}\n')
        known = cwc.load_known_files(self.log)
        self.assertEqual(set(known), {"a.md", "b.md"})

    def test_entries_marks_a_non_dict_json_value_as_malformed_too(self):
        # task 310: a line that parses cleanly to a non-dict JSON value (a
        # bare number, null, list, or string -- e.g. a hand-tampered or
        # truncated write that still happens to be syntactically valid)
        # must not be treated as a real logged entry.
        with open(self.log, "w") as f:
            f.write('{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}\n')
            f.write("5\n")
        entries = cwc._entries(self.log)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])

    def test_load_known_files_raises_tampered_error_on_a_non_dict_json_line(self):
        # pre-fix this crashed with an uncaught AttributeError
        # ('int' object has no attribute 'get') instead of the named error.
        with open(self.log, "w") as f:
            f.write('{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}\n')
            f.write("5\n")
        with self.assertRaises(cwc.ChildWorkLogTamperedError):
            cwc.load_known_files(self.log)


class TestLoadFilesJsonArgGuard(unittest.TestCase):
    """--files-json used to hand a bare `json.load(f)` result straight to
    `record_new_files`, which crashed with a bare, unhelpful TypeError on
    anything but a real list -- the same valid-JSON-wrong-shape crash class
    task 364 fixed for ritual_check.py's own CLI. `_load_files_json` must
    now raise the named `ChildWorkArgError` instead."""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

    def tearDown(self):
        os.remove(self.path)

    def _write(self, obj):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(obj, f)

    def test_dict_payload_raises_named_error(self):
        self._write({"a": 1})
        with self.assertRaises(cwc.ChildWorkArgError):
            cwc._load_files_json(self.path)

    def test_bool_payload_raises_named_error(self):
        self._write(True)
        with self.assertRaises(cwc.ChildWorkArgError):
            cwc._load_files_json(self.path)

    def test_string_payload_raises_named_error(self):
        self._write("x")
        with self.assertRaises(cwc.ChildWorkArgError):
            cwc._load_files_json(self.path)

    def test_well_formed_list_still_loads(self):
        self._write([{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}])
        loaded = cwc._load_files_json(self.path)
        self.assertEqual(loaded, [{"path": "a.md", "sha": "s1", "author_date": "2026-07-11T00:00:00Z"}])


# --- Task 481: child_work_check.py's own docstring claimed "seven laws" ----
# for the live Iron Rules count, unchecked since task 101 -- the same
# hardcoded-cardinal-word-never-cross-checked shape task 480 fixed one file
# over in network_boundary_check.py. TOWN-OPERATIONS.md has since grown an
# eighth Iron Rule (task 183/184's commit-message-is-a-live-instruction
# lesson); nothing re-verified the prose claim against the live rulebook.

_CARDINAL_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12,
}

_LAW_COUNT_CLAIM_RE = re.compile(r"name ([a-z-]+) laws that")
_IRON_RULE_ITEM_RE = re.compile(r"^\d+\.\s", re.MULTILINE)


def claimed_law_count(doc_text: str) -> int:
    """Live-extracts child_work_check.py's own "name N laws that" claim --
    never a second hand-typed eight. Raises if the sentence is missing or
    uses a cardinal word this check doesn't recognize, rather than silently
    passing an unchecked claim through."""
    match = _LAW_COUNT_CLAIM_RE.search(doc_text.replace("\n", " "))
    if not match:
        raise AssertionError(
            "child_work_check.py's own docstring no longer contains a "
            "'name N laws that' sentence -- this doctrine test has nothing "
            "left to cross-check"
        )
    word = match.group(1).lower()
    if word not in _CARDINAL_WORDS:
        raise AssertionError(
            f"child_work_check.py's docstring uses an unrecognized cardinal "
            f"word {word!r} -- add it to _CARDINAL_WORDS before trusting "
            "this check"
        )
    return _CARDINAL_WORDS[word]


def _live_iron_rule_count(vault_root: str = VAULT_ROOT) -> int:
    """Structurally counts TOWN-OPERATIONS.md's own numbered
    '## Iron rules (never bend)' list items -- never a hand-typed number."""
    with open(os.path.join(vault_root, "TOWN-OPERATIONS.md"), encoding="utf-8") as f:
        text = f.read()
    section = text.split("## Iron rules (never bend)", 1)[1].split("\n## ", 1)[0]
    return len(_IRON_RULE_ITEM_RE.findall(section))


def _word_for(n: int) -> str:
    for word, value in _CARDINAL_WORDS.items():
        if value == n:
            return word
    raise AssertionError(f"no cardinal word registered for {n}")


class IronRulesCountDoctrineCase(unittest.TestCase):
    def test_claim_extraction_is_structural_not_hardcoded(self):
        self.assertEqual(
            claimed_law_count("Iron Rules name eight laws that never bend"),
            8,
        )

    def test_claim_missing_sentence_raises(self):
        with self.assertRaises(AssertionError):
            claimed_law_count("Nothing here about a law count.")

    @unittest.skipUnless(
        _VAULT_CHECKED_OUT,
        "orita-vault sibling checkout not present (expected in public CI, which checks out only orita)",
    )
    def test_real_live_iron_rule_count_is_currently_eight(self):
        # Regression pin: today's real, live TOWN-OPERATIONS.md rule count.
        self.assertEqual(_live_iron_rule_count(), 8)

    @unittest.skipUnless(
        _VAULT_CHECKED_OUT,
        "orita-vault sibling checkout not present (expected in public CI, which checks out only orita)",
    )
    def test_docstring_matches_the_real_live_count(self):
        real_count = _live_iron_rule_count()
        claimed = claimed_law_count(cwc.__doc__)
        self.assertEqual(
            claimed, real_count,
            msg=f"child_work_check.py's own docstring claims {claimed} Iron "
                f"Rules 'never bend', but TOWN-OPERATIONS.md's live count is "
                f"{real_count}",
        )

    @unittest.skipUnless(
        _VAULT_CHECKED_OUT,
        "orita-vault sibling checkout not present (expected in public CI, which checks out only orita)",
    )
    def test_one_fewer_law_in_the_claim_would_flip_this_check_red(self):
        """Mutation-based hand-verification: proves this doctrine test
        actually flags a real drift, not just that it happens to pass
        today (same discipline test_network_boundary_doctrine.py's
        analogous case holds itself to)."""
        real_count = _live_iron_rule_count()
        wrong_word = _word_for(real_count - 1)
        wrong_doc = cwc.__doc__.replace("eight laws", f"{wrong_word} laws")
        claimed = claimed_law_count(wrong_doc)
        self.assertNotEqual(claimed, real_count)


if __name__ == "__main__":
    unittest.main()
