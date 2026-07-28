"""Tests for `RECIPES/example-release-vs-changelog/detector.py`'s loaders
(task 358).

No test anywhere in this suite called `load_releases`/`load_changelog`
directly before this file — `test_recipes.py` only proves
`discover_recipes()`/`load_detector()` can find and import the module, never
that its loaders actually work against the real fixture or refuse a
malformed one cleanly. This closes both gaps at once: proves the loaders
parse the real fixture end to end, and proves a syntactically valid but
non-list JSON payload (the shape `report.py`/`ledger.py`/`draftback.py`'s
now-closed campaign, tasks 355-357, did not cover — those guarded non-dict,
this guards non-list) raises a named `ValueError`, not a bare `TypeError`.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "example-release-vs-changelog" / "detector.py"


def _load_module() -> ModuleType:
    module_name = "seam_engine._recipe_example_release_vs_changelog"
    spec = importlib.util.spec_from_file_location(module_name, DETECTOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def detector() -> ModuleType:
    return _load_module()


def test_load_releases_parses_the_real_fixture(detector: ModuleType) -> None:
    releases = detector.load_releases()
    assert len(releases) > 0
    assert all(isinstance(r, detector.Release) for r in releases)


def test_load_changelog_parses_the_real_fixture(detector: ModuleType) -> None:
    changelog = detector.load_changelog()
    assert len(changelog) > 0
    assert all(isinstance(c, detector.ChangelogEntry) for c in changelog)


@pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
def test_load_releases_raises_named_error_not_typeerror_when_json_is_not_a_list(
    detector: ModuleType, tmp_path: Path, bad_value: object
) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps(bad_value))
    with pytest.raises(ValueError, match="expected a JSON list"):
        detector.load_releases(bad_file)


@pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
def test_load_changelog_raises_named_error_not_typeerror_when_json_is_not_a_list(
    detector: ModuleType, tmp_path: Path, bad_value: object
) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps(bad_value))
    with pytest.raises(ValueError, match="expected a JSON list"):
        detector.load_changelog(bad_file)
