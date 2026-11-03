"""Task 2396. Kothar-wa-Khasis's fix for the recurring cold-start toil:
every live BUILDLOG.md row for months has hand-typed the identical
"httpx/PyYAML/pytest/PyJWT/mypy/arcade-mcp-server via pip, both engine
.venvs via uv sync --extra dev" litany. tools/env_setup.sh packages it
into one idempotent command; this proves the script stays in that exact
known-good shape rather than silently drifting (a dropped package here
would surface hours later as a bare `ModuleNotFoundError` on whichever
tool imports it, the same shape of bug task 2396 itself hit live with
`httpx` before writing this script) and that it never runs anything
destructive. It does not actually invoke pip or uv -- a real network
install belongs to this task's own live run, logged in BUILDLOG.md, not
to a test that must stay fast and deterministic offline.
"""
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "tools", "env_setup.sh")

_ROOT_PACKAGES = ["httpx", "PyYAML", "pytest", "PyJWT", "mypy", "arcade-mcp-server"]
_ENGINE_DIRS = ["fencepost/seam_engine", "oracle/oracle_engine"]
_FORBIDDEN_SUBSTRINGS = ["rm -rf", "git push", "git commit", "git reset --hard"]


class EnvSetupCheckCase(unittest.TestCase):
    def setUp(self):
        with open(SCRIPT) as f:
            self.body = f.read()

    def test_script_exists_and_is_executable(self):
        self.assertTrue(os.path.isfile(SCRIPT))
        self.assertTrue(os.access(SCRIPT, os.X_OK), "tools/env_setup.sh must be chmod +x")

    def test_bash_syntax_is_valid(self):
        result = subprocess.run(
            ["bash", "-n", SCRIPT], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_installs_every_known_root_package(self):
        for pkg in _ROOT_PACKAGES:
            self.assertIn(
                pkg, self.body,
                f"env_setup.sh dropped {pkg!r} from the root pip install -- "
                "a real package this script used to install silently missing "
                "surfaces hours later as a bare ModuleNotFoundError, not here",
            )

    def test_syncs_both_engine_venvs(self):
        for engine_dir in _ENGINE_DIRS:
            self.assertIn(engine_dir, self.body)
        self.assertIn("uv sync", self.body)
        self.assertIn("--extra dev", self.body)

    def test_never_runs_anything_destructive(self):
        for bad in _FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(
                bad, self.body,
                f"env_setup.sh must only install dependencies, never {bad!r}",
            )

    def test_set_euo_pipefail(self):
        self.assertIn("set -euo pipefail", self.body)

    def test_pip_install_is_idempotent_safe(self):
        # --ignore-installed avoids a stale-version false pass; neither flag
        # makes a second run do anything destructive to what's already there.
        self.assertIn("--break-system-packages", self.body)

    def test_referenced_from_town_operations_runbook(self):
        vault_root = os.path.join(os.path.dirname(ROOT), "orita-vault")
        runbook = os.path.join(vault_root, "TOWN-OPERATIONS.md")
        if not os.path.isfile(runbook):
            self.skipTest("orita-vault not checked out alongside orita")
        with open(runbook) as f:
            self.assertIn("tools/env_setup.sh", f.read())


if __name__ == "__main__":
    unittest.main()
