"""Task 2523. Proves tools/onboarding_doctrine_check.py actually executes
ONBOARDING.md's two safe, falsifiable command claims (the minute-1 pytest
count, the minute-4 badge read-only shape) and catches every shape a
static text check could never catch: a stale claimed number, a command
that fails outright, and a page whose own wording drifted past this
check's own claim-extraction regex.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


odc = _load("onboarding_doctrine_check", os.path.join(ROOT, "tools", "onboarding_doctrine_check.py"))

_GOOD_ONBOARDING_TEXT = (
    "# the five-minute guide\n\n"
    "### minute 1\n\n"
    "that should print something like `42 passed`. don't skip this.\n\n"
    "### minute 4\n\n"
    "and prints\n`\"N/N tools read-only\"` -- or goes red.\n"
)

# A real, cheap python3 one-liner standing in for `uv run python -m
# pytest -q`'s own terminal summary shape -- never actually invokes `uv`
# or pytest, so these tests need neither installed.
_FAKE_PYTEST_OK = ["python3", "-c", "print('42 passed in 0.01s')"]
_FAKE_PYTEST_WRONG_COUNT = ["python3", "-c", "print('41 passed in 0.01s')"]
_FAKE_PYTEST_FAILS = ["python3", "-c", "import sys; sys.exit(1)"]
_FAKE_PYTEST_NO_COUNT = ["python3", "-c", "print('no summary line here')"]

_FAKE_BADGE_OK = ["python3", "-c", "print('6/6 tools read-only')"]
_FAKE_BADGE_WRONG_SHAPE = ["python3", "-c", "print('all good, trust me')"]
_FAKE_BADGE_FAILS = ["python3", "-c", "import sys; sys.exit(1)"]


class RegexParsingCase(unittest.TestCase):
    def test_extracts_the_claimed_pytest_count(self):
        m = odc._CLAIMED_TEST_COUNT_RE.search(_GOOD_ONBOARDING_TEXT)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), 42)

    def test_finds_the_claimed_badge_shape(self):
        self.assertIsNotNone(odc._CLAIMED_BADGE_SHAPE_RE.search(_GOOD_ONBOARDING_TEXT))

    def test_missing_pytest_claim_finds_nothing(self):
        self.assertIsNone(odc._CLAIMED_TEST_COUNT_RE.search("no claim here\n"))

    def test_missing_badge_claim_finds_nothing(self):
        self.assertIsNone(odc._CLAIMED_BADGE_SHAPE_RE.search("no claim here\n"))

    def test_real_pytest_count_extracted_from_a_realistic_summary_line(self):
        m = odc._REAL_TEST_COUNT_RE.search("........ [100%]\n4584 passed in 35.06s\n")
        self.assertEqual(int(m.group(1)), 4584)

    def test_real_badge_shape_matches_the_live_badge_line(self):
        self.assertIsNotNone(
            odc._REAL_BADGE_SHAPE_RE.search("6/6 tools read-only · 0 writes fired across 1135 sealed runs")
        )


class CheckOnboardingDoctrineCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.onboarding_path = os.path.join(self._tmp.name, "ONBOARDING.md")
        self.seam_engine_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, text=_GOOD_ONBOARDING_TEXT):
        with open(self.onboarding_path, "w", encoding="utf-8") as f:
            f.write(text)

    def _check(self, pytest_command=_FAKE_PYTEST_OK, badge_command=_FAKE_BADGE_OK):
        return odc.check_onboarding_doctrine(
            onboarding_path=self.onboarding_path,
            seam_engine_dir=self.seam_engine_dir,
            timeout=15,
            pytest_command=pytest_command,
            badge_command=badge_command,
        )

    def test_matching_claims_against_matching_live_output_is_clean(self):
        self._write()
        result = self._check()
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["claimed_test_count"], 42)
        self.assertEqual(result["real_test_count"], 42)
        self.assertEqual(result["problems"], [])

    def test_stale_claimed_count_is_named(self):
        self._write()
        result = self._check(pytest_command=_FAKE_PYTEST_WRONG_COUNT)
        self.assertFalse(result["clean"])
        reasons = [p["reason"] for p in result["problems"]]
        self.assertTrue(any("41" in r and "42" in r for r in reasons))

    def test_a_pytest_command_that_fails_is_named(self):
        self._write()
        result = self._check(pytest_command=_FAKE_PYTEST_FAILS)
        self.assertFalse(result["clean"])
        claims = [p["claim"] for p in result["problems"]]
        self.assertIn("pytest_count", claims)

    def test_a_pytest_command_with_no_parseable_count_is_named(self):
        self._write()
        result = self._check(pytest_command=_FAKE_PYTEST_NO_COUNT)
        self.assertFalse(result["clean"])
        reasons = [p["reason"] for p in result["problems"] if p["claim"] == "pytest_count"]
        self.assertTrue(any("never names" in r for r in reasons))

    def test_a_badge_command_that_fails_is_named(self):
        self._write()
        result = self._check(badge_command=_FAKE_BADGE_FAILS)
        self.assertFalse(result["clean"])
        claims = [p["claim"] for p in result["problems"]]
        self.assertIn("badge_shape", claims)

    def test_a_badge_command_with_the_wrong_shape_is_named(self):
        self._write()
        result = self._check(badge_command=_FAKE_BADGE_WRONG_SHAPE)
        self.assertFalse(result["clean"])
        reasons = [p["reason"] for p in result["problems"] if p["claim"] == "badge_shape"]
        self.assertTrue(any("never matches" in r for r in reasons))

    def test_a_page_with_neither_claim_is_named_for_both(self):
        self._write("# nothing checkable on this page\n")
        result = self._check()
        self.assertFalse(result["clean"])
        claims = {p["claim"] for p in result["problems"]}
        self.assertEqual(claims, {"pytest_count", "badge_shape"})

    def test_missing_onboarding_file_is_named(self):
        result = odc.check_onboarding_doctrine(
            onboarding_path=os.path.join(self._tmp.name, "nope.md"),
            seam_engine_dir=self.seam_engine_dir,
        )
        self.assertFalse(result["clean"])
        self.assertEqual(result["status"], "missing_file")


class NoUvSkipCase(unittest.TestCase):
    """Task 2525. `dawn-run.yml`'s `the-oath` job never installs `uv` --
    the identical boundary `recipe_command_check.py` already solved at
    task 404/588 with its own per-command `skipped_no_uv` door, which
    `check_onboarding_doctrine` (task 2523) never copied: both its
    default commands start with `uv run`, so a bare subprocess call
    there raised `FileNotFoundError` on every real `the-oath` run,
    misreporting an environment gap as `clean=False`/`broken=True` for
    every FoldCase in `tests/test_ritual_check.py` that calls
    `run_ritual_check()` without overriding `onboarding_doctrine_*`.
    `shutil.which("uv")` is mocked to `None` here so these tests prove
    the skip without needing `uv` actually absent from this machine."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.onboarding_path = os.path.join(self._tmp.name, "ONBOARDING.md")
        self.seam_engine_dir = self._tmp.name
        with open(self.onboarding_path, "w", encoding="utf-8") as f:
            f.write(_GOOD_ONBOARDING_TEXT)

    def tearDown(self):
        self._tmp.cleanup()

    def test_both_uv_commands_are_skipped_clean_when_uv_is_absent(self):
        with mock.patch.object(odc.shutil, "which", return_value=None):
            result = odc.check_onboarding_doctrine(
                onboarding_path=self.onboarding_path,
                seam_engine_dir=self.seam_engine_dir,
                timeout=15,
                # Deliberately the REAL default `uv run ...` commands --
                # if the skip didn't fire, these would raise
                # FileNotFoundError on any machine without `uv` on PATH,
                # the exact regression this test exists to pin.
                pytest_command=["uv", "run", "python", "-m", "pytest", "-q"],
                badge_command=["uv", "run", "python", "-m", "seam_engine.badge"],
            )
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["problems"], [])
        self.assertEqual(set(result["skipped_no_uv"]), {"pytest_count", "badge_shape"})
        self.assertIsNone(result["real_test_count"])
        self.assertEqual(result["claimed_test_count"], 42)

    def test_a_non_uv_override_still_runs_for_real_even_when_uv_is_absent(self):
        # The skip is per-command, not a blanket process-wide early
        # return: a test's own python3 stand-in command must still run
        # and be judged for real regardless of uv's absence, the same
        # per-command boundary recipe_command_check.py already holds.
        with mock.patch.object(odc.shutil, "which", return_value=None):
            result = odc.check_onboarding_doctrine(
                onboarding_path=self.onboarding_path,
                seam_engine_dir=self.seam_engine_dir,
                timeout=15,
                pytest_command=_FAKE_PYTEST_WRONG_COUNT,
                badge_command=_FAKE_BADGE_OK,
            )
        self.assertFalse(result["clean"], result)
        self.assertEqual(result["status"], "checked")
        self.assertEqual(result["skipped_no_uv"], [])
        claims = [p["claim"] for p in result["problems"]]
        self.assertIn("pytest_count", claims)

    def test_only_the_uv_command_is_skipped_when_the_other_is_overridden(self):
        with mock.patch.object(odc.shutil, "which", return_value=None):
            result = odc.check_onboarding_doctrine(
                onboarding_path=self.onboarding_path,
                seam_engine_dir=self.seam_engine_dir,
                timeout=15,
                pytest_command=["uv", "run", "python", "-m", "pytest", "-q"],
                badge_command=_FAKE_BADGE_OK,
            )
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["status"], "partially_unavailable")
        self.assertEqual(result["skipped_no_uv"], ["pytest_count"])


class FormatResultCase(unittest.TestCase):
    def test_clean_line_names_the_claimed_count(self):
        line = odc.format_result({"clean": True, "claimed_test_count": 4584})
        self.assertIn("4584", line)

    def test_broken_line_names_every_problem(self):
        line = odc.format_result({
            "clean": False,
            "problems": [
                {"claim": "pytest_count", "reason": "stale: claims 41, real 42"},
                {"claim": "badge_shape", "reason": "wrong shape entirely"},
            ],
        })
        self.assertIn("pytest_count", line)
        self.assertIn("stale: claims 41, real 42", line)
        self.assertIn("badge_shape", line)

    def test_missing_file_line_names_the_reason(self):
        line = odc.format_result({
            "status": "missing_file",
            "problems": [{"reason": "no such file: /nope.md"}],
        })
        self.assertIn("/nope.md", line)

    def test_unavailable_line_names_uv_absence_not_a_doctrine_break(self):
        line = odc.format_result({
            "clean": True,
            "status": "unavailable",
            "problems": [],
            "skipped_no_uv": ["pytest_count", "badge_shape"],
        })
        self.assertIn("clean", line)
        self.assertIn("uv", line)
        self.assertNotIn("BROKEN", line)

    def test_partially_unavailable_line_names_the_skipped_claim(self):
        line = odc.format_result({
            "clean": True,
            "status": "partially_unavailable",
            "problems": [],
            "skipped_no_uv": ["pytest_count"],
        })
        self.assertIn("pytest_count", line)
        self.assertIn("clean", line)
        self.assertNotIn("BROKEN", line)


class LiveRealOnboardingCase(unittest.TestCase):
    """The same live, unmocked discipline `test_recipe_command_check.py`'s
    own `LiveRealRepoCase` already holds for every real recipe -- here,
    the one real page: the actual `fencepost/ONBOARDING.md` against the
    actual `uv run python -m pytest -q` / `uv run python -m
    seam_engine.badge` commands, in this repo's own already-synced
    environment. Slow (a real cold pytest run, ~30s) on purpose -- this
    is the check that proves the doc is honest right now, not a stand-in
    for it.

    Task 2525: `uv` genuinely isn't installed in `dawn-run.yml`'s
    `the-oath` job (this test's own root `tests/` suite runs there) --
    the identical boundary `LiveRealRepoCase` above already names for
    `check_recipe_commands`. Either both commands actually ran clean, or
    both were honestly skipped for that one documented environment
    reason (`status` is `unavailable`, `skipped_no_uv` names both
    claims); both are `clean`. A real `claimed_test_count` !=
    `real_test_count` mismatch WITHOUT a skip recorded would still mean
    the doc genuinely drifted -- that stays a real failure here, not
    silently waved through."""

    def test_the_real_onboarding_page_matches_a_real_live_rerun(self):
        result = odc.check_onboarding_doctrine()
        self.assertTrue(result["clean"], result)
        self.assertIsNotNone(result["claimed_test_count"])
        if result["status"] == "checked":
            self.assertEqual(result["claimed_test_count"], result["real_test_count"])
        else:
            self.assertIn(result["status"], ("unavailable", "partially_unavailable"))
            self.assertIn("pytest_count", result["skipped_no_uv"])


if __name__ == "__main__":
    unittest.main()
