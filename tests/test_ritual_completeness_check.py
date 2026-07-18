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


class FixtureCompletenessCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _path(self, text):
        path = os.path.join(self.tmp, "fixture_ritual_check.py")
        _write(path, text)
        return path

    def test_clean_fixture_reports_no_violations(self):
        result = src.compute_ritual_completeness(self._path(CLEAN_FIXTURE))
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_from_run"], [])
        self.assertEqual(result["missing_from_dict"], [])
        self.assertEqual(result["missing_from_format"], [])

    def test_conditionally_called_function_is_not_a_false_positive(self):
        # mirrors ritual_check.py's own check_vault_leak, called inside an
        # if/else rather than unconditionally at the top level.
        result = src.compute_ritual_completeness(self._path(CONDITIONAL_CALL_FIXTURE))
        self.assertTrue(result["clean"])
        self.assertEqual(result["missing_from_run"], [])

    def test_never_called_function_is_caught_and_named(self):
        result = src.compute_ritual_completeness(self._path(NEVER_CALLED_FIXTURE))
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_run"], ["check_orphan"])

    def test_dropped_from_return_dict_is_caught_and_named(self):
        result = src.compute_ritual_completeness(self._path(DROPPED_FROM_DICT_FIXTURE))
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_dict"], ["check_beta"])

    def test_never_printed_is_caught_and_named(self):
        result = src.compute_ritual_completeness(self._path(NEVER_PRINTED_FIXTURE))
        self.assertFalse(result["clean"])
        self.assertEqual(result["missing_from_format"], ["beta"])

    def test_now_and_broken_are_exempt_from_print_requirement(self):
        # CLEAN_FIXTURE's format_ritual_check never prints "broken" (an
        # aggregate exit-code flag, not a check result), only "now"/alpha/beta
        # -- must not be flagged.
        result = src.compute_ritual_completeness(self._path(CLEAN_FIXTURE))
        self.assertNotIn("broken", result["missing_from_format"])

    def test_format_clean(self):
        result = src.compute_ritual_completeness(self._path(CLEAN_FIXTURE))
        formatted = src.format_ritual_completeness(result)
        self.assertIn("clean", formatted)

    def test_format_broken_names_each_violation_kind(self):
        result = src.compute_ritual_completeness(self._path(NEVER_CALLED_FIXTURE))
        formatted = src.format_ritual_completeness(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("check_orphan", formatted)


class RealRitualCheckCase(unittest.TestCase):
    """The real point: the live tools/ritual_check.py, audited for real."""

    def test_real_ritual_check_has_zero_violations(self):
        result = src.compute_ritual_completeness()
        self.assertEqual(result["missing_from_run"], [])
        self.assertEqual(result["missing_from_dict"], [])
        self.assertEqual(result["missing_from_format"], [])
        self.assertTrue(result["clean"])

    def test_real_ritual_check_has_at_least_the_known_27_checks(self):
        import ast

        path = os.path.join(ROOT, "tools", "ritual_check.py")
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        names = src._check_function_names(tree)
        self.assertGreaterEqual(len(names), 27)


if __name__ == "__main__":
    unittest.main()
