"""ROADMAP.md #114. A real bug, found live this hour by actually running what
`CONTRIBUTING.md` tells a stranger to run.

Its "Opening the PR" checklist, step 4, read `cd fencepost/seam_engine && uv
run python -m pytest -q` -- copied verbatim into a genuinely fresh checkout
(`rm -rf .venv`, no prior `uv sync`), it fails with `No module named pytest`.
`ONBOARDING.md`'s minute 1 avoids the same trap only because it runs `uv sync
--extra dev` *before* its own `uv run python -m pytest -q` line -- `uv run`
reuses whatever `.venv` already exists rather than re-resolving it bare.
`CONTRIBUTING.md` never syncs anything first; its step 4 is the one
standalone test-running instruction in this repo with no such step ahead of
it, and `pytest` lives only inside `pyproject.toml`'s `[project.
optional-dependencies].dev` group, never the base `dependencies` list `uv
run` (no `--extra`) installs.

Two doctrine checks, same "proven, not just claimed" shape
`test_recipes_doctrine.py`/`test_badge.py` already hold this repo to: a
static check that the fixed command actually appears in `CONTRIBUTING.md`,
and a structural check on `pyproject.toml` proving *why* the flag is
required -- so if `pytest` ever migrates into the base dependencies, this
test breaks loudly instead of quietly going stale.
"""

import pathlib
import tomllib

FENCEPOST_ROOT = pathlib.Path(__file__).resolve().parents[2]
SEAM_ENGINE_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_contributing_documents_the_extra_dev_flag():
    text = (FENCEPOST_ROOT / "CONTRIBUTING.md").read_text()
    assert "uv run --extra dev python -m pytest -q" in text, (
        "CONTRIBUTING.md's step 4 must run 'uv run --extra dev python -m "
        "pytest -q' -- a bare 'uv run python -m pytest -q' fails from a "
        "fresh checkout with no prior 'uv sync --extra dev'"
    )


def test_pytest_lives_only_in_the_dev_extra():
    data = tomllib.loads((SEAM_ENGINE_ROOT / "pyproject.toml").read_text())
    base_deps = data["project"]["dependencies"]
    dev_deps = data["project"]["optional-dependencies"]["dev"]

    assert not any("pytest" in dep for dep in base_deps), (
        "pytest now appears in the base dependencies -- CONTRIBUTING.md's "
        "command no longer needs --extra dev; update both together"
    )
    assert any(dep.startswith("pytest>=") for dep in dev_deps), (
        "expected pytest under [project.optional-dependencies].dev"
    )


def test_recipes_discover_command_needs_no_extra_and_is_unchanged():
    # The other uv command in the same document (step 2 / line 114) reads
    # only base deps (seam_engine.recipes has no pytest import) -- it is
    # correct exactly as written, bare uv run, no --extra. Locking its exact
    # text too so a future edit can't "fix" this one by mistake.
    text = (FENCEPOST_ROOT / "CONTRIBUTING.md").read_text()
    assert "uv run python -m seam_engine.recipes discover" in text
