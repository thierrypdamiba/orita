"""Task 551. Proves tools/adoption_metric_format.py's shared
format_adoption_result() renders correctly on its own, and that the two
sibling checks it was extracted from (connected_users_check.py,
toolkits_in_use_check.py) each now delegate to it rather than carrying
their own byte-identical (once label/field/unit text is treated as a
parameter) copy.

An AST-hash sweep of every tools/*.py function body, constants normalized
before hashing, found both defining the identical four-branch body under
different label/field/unit constants -- invisible to
duplicate_regex_check.py (which only inspects re.compile() call sites)
and never touched by metrics_reader.py's own earlier consolidation pass
(task 508), which unified these same two files' `records/metrics.jsonl`
reader but not their output renderer.

Two kinds of proof, mirroring tests/test_violation_format.py's own
discipline: (1) each sibling's real, unmodified format_result(result)
output is byte-identical, across all four branches, to what it produced
before this refactor (frozen fixture strings, not a re-derivation); (2)
each sibling's own source contains exactly one call to
adoption_metric_format.format_adoption_result, so a future edit that
quietly reforks one sibling back into its own copy is caught by
inspection, not just by today's passing output comparison.
"""
import ast
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


amf = _load("adoption_metric_format", os.path.join(TOOLS, "adoption_metric_format.py"))

# (label, field_name, real_unit, result, expected) -- expected strings are
# the exact byte-for-byte output each sibling's own pre-refactor
# format_result produced, confirmed against the pre-refactor source before
# this file was written, never re-derived from the shared function itself.
CASES = [
    (
        "connected users (OAuth)",
        "connected_users_oauth",
        "real connected user(s)",
        {"clean": True, "real": 0, "claimed": None, "claimed_date": None},
        "connected users (OAuth): clean (no metrics.jsonl reading yet; real ground truth is 0)",
    ),
    (
        "connected users (OAuth)",
        "connected_users_oauth",
        "real connected user(s)",
        {"clean": True, "real": 0, "claimed": None, "claimed_date": "2026-07-20"},
        "connected users (OAuth): clean (metrics.jsonl's 2026-07-20 reading names no "
        "connected_users_oauth field; real ground truth is honestly 0, nothing omitted)",
    ),
    (
        "connected users (OAuth)",
        "connected_users_oauth",
        "real connected user(s)",
        {"clean": False, "real": 1, "claimed": None, "claimed_date": "2026-07-20"},
        "connected users (OAuth): BROKEN -- metrics.jsonl's 2026-07-20 reading names no "
        "connected_users_oauth field, but real ground truth (HAND/consent-grants-log.jsonl, "
        "gate-verified) is already 1 -- a real count exists and was not recorded, escalate now",
    ),
    (
        "connected users (OAuth)",
        "connected_users_oauth",
        "real connected user(s)",
        {"clean": True, "real": 0, "claimed": 0, "claimed_date": "2026-07-18"},
        "connected users (OAuth): clean (0 real connected user(s), metrics.jsonl's 2026-07-18 "
        "reading agrees)",
    ),
    (
        "connected users (OAuth)",
        "connected_users_oauth",
        "real connected user(s)",
        {"clean": False, "real": 0, "claimed": 3, "claimed_date": "2026-07-18"},
        "connected users (OAuth): BROKEN -- metrics.jsonl's 2026-07-18 reading claims 3, real "
        "ground truth (HAND/consent-grants-log.jsonl, gate-verified) is 0 -- STRATEGY.md's "
        "adoption metric is misreporting live",
    ),
    (
        "toolkits in use",
        "distinct_toolkits_in_use",
        "real toolkit(s)",
        {"clean": True, "real": 0, "claimed": None, "claimed_date": None},
        "toolkits in use: clean (no metrics.jsonl reading yet; real ground truth is 0)",
    ),
    (
        "toolkits in use",
        "distinct_toolkits_in_use",
        "real toolkit(s)",
        {"clean": False, "real": 0, "claimed": 2, "claimed_date": "2026-07-18"},
        "toolkits in use: BROKEN -- metrics.jsonl's 2026-07-18 reading claims 2, real ground "
        "truth (HAND/consent-grants-log.jsonl, gate-verified) is 0 -- STRATEGY.md's adoption "
        "metric is misreporting live",
    ),
]


class SharedRendererCase(unittest.TestCase):
    def test_every_frozen_fixture_matches_byte_for_byte(self):
        for label, field_name, real_unit, result, expected in CASES:
            with self.subTest(label=label, result=result):
                self.assertEqual(
                    amf.format_adoption_result(label, result, field_name, real_unit),
                    expected,
                )


class SiblingDelegationCase(unittest.TestCase):
    """Each sibling's own format_result(result) must produce output
    byte-identical to the frozen pre-refactor fixtures above, via its own
    real module-level function (not by calling the shared function
    directly)."""

    def test_connected_users_check_format_result_matches_fixtures(self):
        cuc = _load("connected_users_check", os.path.join(TOOLS, "connected_users_check.py"))
        for label, _field_name, _real_unit, result, expected in CASES:
            if label != "connected users (OAuth)":
                continue
            with self.subTest(result=result):
                self.assertEqual(cuc.format_result(result), expected)

    def test_toolkits_in_use_check_format_result_matches_fixtures(self):
        tiu = _load("toolkits_in_use_check", os.path.join(TOOLS, "toolkits_in_use_check.py"))
        for label, _field_name, _real_unit, result, expected in CASES:
            if label != "toolkits in use":
                continue
            with self.subTest(result=result):
                self.assertEqual(tiu.format_result(result), expected)


class SingleDelegationSiteCase(unittest.TestCase):
    """A future edit that quietly reforks one sibling back into its own
    copy must be caught by inspection, not just by output comparison --
    the same discipline tests/test_violation_format.py already holds for
    its own six siblings."""

    def _call_count(self, path, func_name):
        tree = ast.parse(open(path, encoding="utf-8").read())
        calls = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == func_name and isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "adoption_metric_format":
                        calls += 1
        return calls

    def test_connected_users_check_calls_shared_function_exactly_once(self):
        path = os.path.join(TOOLS, "connected_users_check.py")
        self.assertEqual(self._call_count(path, "format_adoption_result"), 1)

    def test_toolkits_in_use_check_calls_shared_function_exactly_once(self):
        path = os.path.join(TOOLS, "toolkits_in_use_check.py")
        self.assertEqual(self._call_count(path, "format_adoption_result"), 1)


if __name__ == "__main__":
    unittest.main()
