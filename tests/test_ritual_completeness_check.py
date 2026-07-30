"""Task 121. Proves tools/ritual_completeness_check.py catches all three
ways a check_* function can silently fall out of tools/ritual_check.py's
hourly block -- defined but never called, called but dropped from the
return dict, or returned but never printed -- and proves the real, live
ritual_check.py currently holds none of them.
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


src = _load("ritual_completeness_check", os.path.join(ROOT, "tools", "ritual_completeness_check.py"))

CLEAN_FIXTURE = '''
def check_alpha():
    return {"ok": True}


def check_beta():
    return {"ok": True}


def run_ritual_check():
    a = check_alpha()
    b = check_beta()
    return {
        "now": "2026-07-18T00:00:00+00:00",
        "alpha": a,
        "beta": b,
        "broken": False,
    }


def format_ritual_check(result):
    lines = [f"@ {result['now']}"]
    lines.append(f"alpha: {result['alpha']}")
    lines.append(f"beta: {result['beta']}")
    return "\\n".join(lines)
'''

CONDITIONAL_CALL_FIXTURE = '''
def check_alpha():
    return {"ok": True}


def run_ritual_check(alpha_dir=None):
    if alpha_dir is None:
        a = check_alpha()
    else:
        a = check_alpha(alpha_dir)
    return {"now": "x", "alpha": a, "broken": False}


def format_ritual_check(result):
    return f"alpha: {result['alpha']}"
'''

NEVER_CALLED_FIXTURE = '''
def check_alpha():
    return {"ok": True}


def check_orphan():
    return {"ok": True}


def run_ritual_check():
    a = check_alpha()
    return {"now": "x", "alpha": a, "broken": False}


def format_ritual_check(result):
    return f"alpha: {result['alpha']}"
'''

DROPPED_FROM_DICT_FIXTURE = '''
def check_alpha():
    return {"ok": True}


def check_beta():
    return {"ok": True}


def run_ritual_check():
    a = check_alpha()
    b = check_beta()
    return {"now": "x", "alpha": a, "broken": False}


def format_ritual_check(result):
    return f"alpha: {result['alpha']}"
'''

NEVER_PRINTED_FIXTURE = '''
def check_alpha():
    return {"ok": True}


def check_beta():
    return {"ok": True}


def run_ritual_check():
    a = check_alpha()
    b = check_beta()
    return {"now": "x", "alpha": a, "beta": b, "broken": False}


def format_ritual_check(result):
    return f"alpha: {result['alpha']}"
'''


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


TOOL_FILE_RITUAL_CHECK_FIXTURE = '''
def check_alpha():
    return {"ok": True}


def run_ritual_check():
    _load("_x", os.path.join(ROOT, "tools", "alpha_check.py"))
    a = check_alpha()
    return {"now": "x", "alpha": a, "broken": False}


def format_ritual_check(result):
    return f"alpha: {result['alpha']}"
'''


class FixtureCompletenessCase(unittest.TestCase):
    """These fixtures exercise the three call/dict/print violations only --
    each passes an empty tools_dir so the separate unwired_tool_files check
    (task 409, exercised on its own in UnwiredToolFilesCase below) never
    fires a false positive here by comparing a bare fixture body against
    the real, populated tools/ directory."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.empty_tools_dir = os.path.join(self.tmp, "tools")
        os.makedirs(self.empty_tools_dir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _path(self, text):
        path = os.path.join(self.tmp, "fixture_ritual_check.py")
        _write(path, text)
        return path

    def _compute(self, text):
        return src.compute_ritual_completeness(self._path(text), self.empty_tools_dir)

    def test_clean_fixture_reports_no_violations(self):
        result = self._compute(CLEAN_FIXTURE)
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_from_run"], [])
        self.assertEqual(result["missing_from_dict"], [])
        self.assertEqual(result["missing_from_format"], [])

    def test_conditionally_called_function_is_not_a_false_positive(self):
        # mirrors ritual_check.py's own check_vault_leak, called inside an
        # if/else rather than unconditionally at the top level.
        result = self._compute(CONDITIONAL_CALL_FIXTURE)
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_from_run"], [])

    def test_never_called_function_is_caught_and_named(self):
        result = self._compute(NEVER_CALLED_FIXTURE)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_run"], ["check_orphan"])

    def test_dropped_from_return_dict_is_caught_and_named(self):
        result = self._compute(DROPPED_FROM_DICT_FIXTURE)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_dict"], ["check_beta"])

    def test_never_printed_is_caught_and_named(self):
        result = self._compute(NEVER_PRINTED_FIXTURE)
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_format"], ["beta"])

    def test_now_and_broken_are_exempt_from_print_requirement(self):
        # CLEAN_FIXTURE's format_ritual_check never prints "broken" (an
        # aggregate exit-code flag, not a check result), only "now"/alpha/beta
        # -- must not be flagged.
        result = self._compute(CLEAN_FIXTURE)
        self.assertNotIn("broken", result["missing_from_format"])

    def test_format_clean(self):
        result = self._compute(CLEAN_FIXTURE)
        formatted = src.format_ritual_completeness(result)
        self.assertIn("clean", formatted)

    def test_format_broken_names_each_violation_kind(self):
        result = self._compute(NEVER_CALLED_FIXTURE)
        formatted = src.format_ritual_completeness(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("check_orphan", formatted)


class UnwiredToolFilesCase(unittest.TestCase):
    """Task 409. tools/ritual_completeness_check.py's own docstring named
    its last blind spot: it only ever audited check_* functions already
    defined inside ritual_check.py's source, never the separate tool files
    under tools/ a future wiring pass might still be missing entirely --
    exactly the shape that let network_boundary_check.py (tasks 163/164)
    and strategy_targets_check.py (task 159) both sit built, tested, and
    unwired for months. find_unwired_tool_files() closes it: the same
    basename-grep tasks 407/408 ran by hand, now a running check.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tools_dir = os.path.join(self.tmp, "tools")
        os.makedirs(self.tools_dir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _ritual_check_path(self, text):
        path = os.path.join(self.tmp, "fixture_ritual_check.py")
        _write(path, text)
        return path

    def _touch_tool(self, name):
        _write(os.path.join(self.tools_dir, name), "# fixture tool file\n")

    def test_a_referenced_tool_file_is_not_flagged(self):
        self._touch_tool("alpha_check.py")
        result = src.find_unwired_tool_files(
            self.tools_dir, self._ritual_check_path(TOOL_FILE_RITUAL_CHECK_FIXTURE)
        )
        self.assertEqual(result, [])

    def test_an_unreferenced_tool_file_is_caught_and_named(self):
        self._touch_tool("alpha_check.py")
        self._touch_tool("orphan_check.py")
        result = src.find_unwired_tool_files(
            self.tools_dir, self._ritual_check_path(TOOL_FILE_RITUAL_CHECK_FIXTURE)
        )
        self.assertEqual(result, ["orphan_check.py"])

    def test_exempt_tool_files_are_never_flagged_even_when_unreferenced(self):
        for name in src.EXEMPT_TOOL_FILES:
            self._touch_tool(name)
        result = src.find_unwired_tool_files(
            self.tools_dir, self._ritual_check_path(TOOL_FILE_RITUAL_CHECK_FIXTURE)
        )
        self.assertEqual(result, [])

    def test_non_python_files_are_ignored(self):
        _write(os.path.join(self.tools_dir, "README.md"), "not a tool")
        result = src.find_unwired_tool_files(
            self.tools_dir, self._ritual_check_path(TOOL_FILE_RITUAL_CHECK_FIXTURE)
        )
        self.assertEqual(result, [])

    def test_compute_ritual_completeness_folds_in_unwired_tool_files(self):
        self._touch_tool("orphan_check.py")
        result = src.compute_ritual_completeness(
            self._ritual_check_path(TOOL_FILE_RITUAL_CHECK_FIXTURE), self.tools_dir
        )
        self.assertFalse(result["clean"])
        self.assertEqual(result["unwired_tool_files"], ["orphan_check.py"])

    def test_format_names_unwired_tool_files(self):
        result = {
            "clean": False,
            "missing_from_run": [],
            "missing_from_dict": [],
            "missing_from_format": [],
            "unwired_tool_files": ["orphan_check.py"],
        }
        formatted = src.format_ritual_completeness(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("orphan_check.py", formatted)

    def test_real_tools_dir_has_zero_unwired_files(self):
        # The real point: the live tools/ directory, audited for real --
        # this is the exact grep tasks 407/408 ran by hand, now automated.
        result = src.find_unwired_tool_files()
        self.assertEqual(result, [])


class RealRitualCheckCase(unittest.TestCase):
    """The real point: the live tools/ritual_check.py, audited for real."""

    def test_real_ritual_check_has_zero_violations(self):
        result = src.compute_ritual_completeness()
        self.assertEqual(result["missing_from_run"], [])
        self.assertEqual(result["missing_from_dict"], [])
        self.assertEqual(result["missing_from_format"], [])
        self.assertEqual(result["unwired_tool_files"], [])
        self.assertTrue(result["clean"])

    def test_real_ritual_check_has_at_least_the_known_27_checks(self):
        import ast

        path = os.path.join(ROOT, "tools", "ritual_check.py")
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        names = src._check_function_names(tree)
        self.assertGreaterEqual(len(names), 27)


class DocstringClaimDoctrineCase(unittest.TestCase):
    """ritual_completeness_check.py's own module docstring self-reports how
    many check_* functions ritual_check.py hand-wires -- proves that claim
    is live-extracted (never a second hand-typed copy) and actually equals
    the real, live count, the exact "true when written, never rechecked"
    shape this module exists to catch in its subject.
    """

    def _real_check_count(self) -> int:
        import ast

        path = os.path.join(ROOT, "tools", "ritual_check.py")
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        return len(src._check_function_names(tree))

    def test_docstring_claim_is_live_extracted_not_hardcoded(self):
        # The claim comes from the module's real __doc__ text, not a second
        # hand-typed literal in this test file.
        self.assertEqual(src.claimed_check_count(), src.claimed_check_count(src.__doc__))

    def test_docstring_claim_equals_the_real_live_check_count(self):
        self.assertEqual(src.claimed_check_count(), self._real_check_count())

    def test_real_check_count_is_currently_37(self):
        # Regression pin: task 121 shipped this module claiming 27. Five
        # more check_* functions (this module's own check_ritual_completeness
        # fold-in among them, plus task 145's check_toolkits_in_use) were
        # added to ritual_check.py afterward with nobody revisiting the
        # docstring's number -- naming the real count here so a future
        # addition that forgets the docstring trips a second, independent
        # assertion, not just the live cross-check above. Task 168's
        # check_scribe_growth moved this from 32 to 33, docstring updated
        # in the same commit that added it. Task 387's check_cluster_day_cadence
        # moved this from 33 to 34. Task 397's check_duplicate_regex moved
        # this from 34 to 35, docstring updated in the same commit. Task 407's
        # check_strategy_targets moved this from 35 to 36, docstring updated
        # in the same commit. Task 408's check_network_boundary moved this
        # from 36 to 37, docstring updated in the same commit.
        self.assertEqual(self._real_check_count(), 37)

    def test_stale_27_claim_would_have_been_flagged_against_todays_real_count(self):
        # Mutation-based hand-verification: reconstruct the module's own
        # real pre-fix docstring sentence (the literal "27" claim task 121
        # actually shipped) and prove it disagrees with today's real,
        # live count -- the exact historical bug this task fixes, proven
        # catchable rather than assumed fixed.
        stale_doc = (
            "Task 121. Off-By-One counts the tool that counts everything else.\n\n"
            "`tools/ritual_check.py` hand-wires 27 `check_*` functions into one "
            "hourly\nblock: each is called inside `run_ritual_check`...\n"
        )
        stale_claim = src.claimed_check_count(stale_doc)
        self.assertEqual(stale_claim, 27)
        self.assertNotEqual(stale_claim, self._real_check_count())

    def test_missing_claim_sentence_raises_instead_of_silently_passing(self):
        with self.assertRaises(ValueError):
            src.claimed_check_count("no claim sentence here at all")


if __name__ == "__main__":
    unittest.main()
