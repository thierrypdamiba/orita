"""Task 529. A recipe's `fixture` field pointing under `fixtures/` and its
`scopes` being read-only-shaped is not the same claim as its `detector.py`
never touching the network -- and until this task, nothing checked the
second claim at all.

`recipes.py`'s own module docstring said so outright, before this task:
"This is a schema-and-manifest gate, not a sandboxed code executor... It
makes no claim about what a recipe's Python *does* beyond what its
manifest *declares*." `validate_recipe`'s two independent checks on scope
names (allow-list by prefix, deny-list by word) and `load_recipe_manifest`'s
fixture-path check are both real, both tested (`test_recipes.py`), and both
check the MANIFEST -- a JSON string a contributor typed. Nothing before this
task ever opened the detector.py file sitting right next to that manifest
and asked whether its own Python code agreed with what the manifest swore
to. A recipe.json with `"fixture": "fixtures/x"` and
`"scopes": ["ListRepoCommits"]` clears every check that existed before this
task even if its `detector.py` opens a live socket on import -- the exact
"claims a boundary, nothing behind the claim checks it" shape
`tools/network_boundary_check.py` already closed for `tools/`,
`seam_engine/src/seam_engine/`, and `oracle_engine/src/oracle_engine/`
(tasks 163/164/446), never extended to `RECIPES/*/detector.py` because that
family never makes the "no network" claim in the first place -- there was
nothing for a claim-scanning checker to find.

`_detector_network_imports` (`recipes.py`) closes it structurally instead:
a static AST walk of the detector's own source, independent of the claim
pattern, wired into `load_recipe_manifest` (and so into `discover_recipes`,
the exact function CI's `the-seam-oath` job runs over every PR that touches
`RECIPES/`). This file proves the checker on synthetic fixtures (each shape
of violation, each shape a clean recipe legitimately needs), regression-pins
today's real 42 recipes as clean, and mutation-tests the pin the same way
`test_recipe_ordinal_doctrine.py` (task 522) mutation-tests its own claim --
proving the net would actually catch something, not just staying silent
because nothing is currently wrong.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from seam_engine.recipes import (
    NETWORK_CAPABLE_IMPORTS,
    RECIPES_DIR_NAME,
    RecipeValidationError,
    _detector_network_imports,
    discover_recipes,
    load_recipe_manifest,
)

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]


def _manifest_json(**overrides) -> dict:
    data = dict(
        slug="net-test-recipe", title="X", author="a", description="d",
        toolkit="github", scopes=["ListRepoCommits"],
        fixture="fixtures/x", detector_file="detector.py",
        entrypoint="run_recipe_scan", confidence_notes="n",
    )
    data.update(overrides)
    return data


def _write(tmp_path: Path, detector_source: str, **manifest_overrides) -> Path:
    """Write a recipe.json (otherwise clean) plus a `detector.py` carrying
    exactly `detector_source`, under `tmp_path/RECIPES/<slug>/`. Returns the
    recipe.json path, ready for `load_recipe_manifest`."""
    data = _manifest_json(**manifest_overrides)
    d = tmp_path / RECIPES_DIR_NAME / data["slug"]
    d.mkdir(parents=True)
    (d / "recipe.json").write_text(json.dumps(data))
    (d / "detector.py").write_text(detector_source)
    return d / "recipe.json"


# --- _detector_network_imports: the static AST scan, on synthetic sources --


def test_clean_detector_reports_no_network_imports(tmp_path: Path):
    path = tmp_path / "detector.py"
    path.write_text(
        "from __future__ import annotations\n\n"
        "import json\n"
        "from dataclasses import dataclass\n"
        "from pathlib import Path\n\n"
        "def run_recipe_scan():\n    return {}\n"
    )
    assert _detector_network_imports(path) == []


@pytest.mark.parametrize("module", sorted(NETWORK_CAPABLE_IMPORTS))
def test_every_deny_listed_module_is_caught_by_a_bare_import(tmp_path: Path, module: str):
    path = tmp_path / "detector.py"
    path.write_text(f"import {module}\n")
    assert _detector_network_imports(path) == [module]


def test_a_from_import_of_a_network_module_is_caught(tmp_path: Path):
    path = tmp_path / "detector.py"
    path.write_text("from urllib.request import urlopen\n")
    assert _detector_network_imports(path) == ["urllib.request"]


def test_the_urllib_request_submodule_form_is_caught_not_just_the_urlopen_form(tmp_path: Path):
    # Task 532: `from urllib import request` parses to `ast.ImportFrom`
    # with `module="urllib"`, `names=["request"]` -- never the dotted
    # string "urllib.request" the deny-list holds -- so a bare
    # `node.module in NETWORK_CAPABLE_IMPORTS` test (the shape this
    # checker first shipped with, task 529) walks straight past this real
    # stdlib form while still catching `from urllib.request import
    # urlopen` (test above). Both forms make the identical live network
    # call; both must be caught.
    path = tmp_path / "detector.py"
    path.write_text("from urllib import request\nrequest.urlopen('http://example.com')\n")
    assert _detector_network_imports(path) == ["urllib.request"]


def test_the_http_client_submodule_form_is_caught(tmp_path: Path):
    # Same bypass shape, the deny-list's other dotted stdlib entry:
    # `from http import client` parses to `module="http"`, never the
    # string "http.client".
    path = tmp_path / "detector.py"
    path.write_text("from http import client\nclient.HTTPConnection('evil.example.com')\n")
    assert _detector_network_imports(path) == ["http.client"]


def test_a_network_import_hidden_inside_a_function_body_is_still_caught(tmp_path: Path):
    # Not just top-level statements -- `ast.walk` reaches every node in the
    # tree, so a network import guarded inside a function (or an `if`, a
    # `try`, a class body) is exactly as real a live-network risk as one at
    # module level, and is caught the same way.
    path = tmp_path / "detector.py"
    path.write_text(
        "def run_recipe_scan():\n"
        "    import socket\n"
        "    return socket.socket()\n"
    )
    assert _detector_network_imports(path) == ["socket"]


def test_a_network_import_hidden_inside_an_if_branch_is_still_caught(tmp_path: Path):
    path = tmp_path / "detector.py"
    path.write_text(
        "import json\n\n"
        "def run_recipe_scan(live=False):\n"
        "    if live:\n"
        "        import httpx\n"
        "        return httpx.get('https://example.com')\n"
        "    return json.loads('{}')\n"
    )
    assert _detector_network_imports(path) == ["httpx"]


def test_multiple_distinct_network_imports_are_all_named(tmp_path: Path):
    path = tmp_path / "detector.py"
    path.write_text("import socket\nimport requests\nimport socket\n")
    assert _detector_network_imports(path) == ["requests", "socket"]


def test_urllib_parse_is_not_flagged_it_has_no_network_capability_of_its_own(tmp_path: Path):
    # The same care network_boundary_check.py's own NETWORK_MODULES takes:
    # `urllib.parse` (string parsing only) must not be flagged just because
    # it shares a top-level package name with `urllib.request`.
    path = tmp_path / "detector.py"
    path.write_text("from urllib.parse import urlparse\n")
    assert _detector_network_imports(path) == []


def test_the_urllib_parse_submodule_form_is_still_not_flagged(tmp_path: Path):
    # The reconstructed-dotted-path check added for task 532 must stay as
    # exact-match as the direct one already was: `from urllib import
    # parse` reconstructs to "urllib.parse", which is not on the
    # deny-list (no network capability of its own) and must not be
    # flagged just because it shares a parent package with the real
    # `urllib.request` bypass this task closed.
    path = tmp_path / "detector.py"
    path.write_text("from urllib import parse\nparse.urlparse('a')\n")
    assert _detector_network_imports(path) == []


def test_a_dynamic_importlib_import_module_call_is_caught(tmp_path: Path):
    # Task 536: `_detector_network_imports` (tasks 529/532) only ever
    # walked `ast.Import`/`ast.ImportFrom` nodes -- but a detector doesn't
    # have to write a static import statement to reach the network.
    # `importlib.import_module("requests")` is a plain `ast.Call`, never
    # either node type, so it cleared the check entirely while genuinely
    # binding the real `requests` module and being just as capable of a
    # live socket as `import requests`.
    path = tmp_path / "detector.py"
    path.write_text(
        "import importlib\n\n"
        "def run_recipe_scan():\n"
        "    requests = importlib.import_module('requests')\n"
        "    return requests.get('http://example.com')\n"
    )
    assert _detector_network_imports(path) == ["requests"]


def test_a_dynamic_import_module_call_via_a_direct_from_import_is_caught(tmp_path: Path):
    # `from importlib import import_module; import_module("socket")` names
    # the function bare, not through the `importlib.` attribute -- a
    # second real call shape, not just a second way to spell the first one.
    path = tmp_path / "detector.py"
    path.write_text(
        "from importlib import import_module\n\n"
        "def run_recipe_scan():\n"
        "    return import_module('socket')\n"
    )
    assert _detector_network_imports(path) == ["socket"]


def test_a_dunder_import_call_is_caught(tmp_path: Path):
    # `__import__("socket")` is the builtin every static `import` statement
    # itself lowers to -- calling it directly is exactly as real a live
    # network reach and carries no `Import`/`ImportFrom` node at all.
    path = tmp_path / "detector.py"
    path.write_text(
        "def run_recipe_scan():\n"
        "    sock_mod = __import__('socket')\n"
        "    return sock_mod.socket()\n"
    )
    assert _detector_network_imports(path) == ["socket"]


def test_a_dynamic_import_of_a_dotted_stdlib_network_submodule_is_caught(tmp_path: Path):
    # The dynamic form of the same task-532 bypass: import_module's `name`
    # argument can be a dotted string just as legally as a static
    # `from X import Y` can reconstruct one.
    path = tmp_path / "detector.py"
    path.write_text(
        "import importlib\n\n"
        "def run_recipe_scan():\n"
        "    return importlib.import_module('urllib.request')\n"
    )
    assert _detector_network_imports(path) == ["urllib.request"]


def test_a_dynamic_import_of_a_non_literal_name_is_not_flagged(tmp_path: Path):
    # `importlib.import_module(some_variable)` cannot be statically proven
    # to name a network-capable module -- this is a narrow, structural
    # claim (recipes.py's own docstring), not a sound dataflow analysis, so
    # a non-literal argument is correctly left unflagged rather than
    # guessed at.
    path = tmp_path / "detector.py"
    path.write_text(
        "import importlib\n\n"
        "def run_recipe_scan(module_name='json'):\n"
        "    return importlib.import_module(module_name)\n"
    )
    assert _detector_network_imports(path) == []


def test_a_dynamic_import_of_a_clean_module_is_not_flagged(tmp_path: Path):
    path = tmp_path / "detector.py"
    path.write_text(
        "import importlib\n\n"
        "def run_recipe_scan():\n"
        "    return importlib.import_module('json')\n"
    )
    assert _detector_network_imports(path) == []


def test_load_recipe_manifest_rejects_a_recipe_whose_detector_dynamically_imports_requests(tmp_path: Path):
    path = _write(
        tmp_path,
        "import importlib\n\n"
        "def run_recipe_scan():\n"
        "    return importlib.import_module('requests')\n",
    )
    with pytest.raises(RecipeValidationError, match="network-capable"):
        load_recipe_manifest(path)


def test_unparseable_detector_source_fails_closed(tmp_path: Path):
    path = tmp_path / "detector.py"
    path.write_text("def run_recipe_scan(:\n    this is not python\n")
    with pytest.raises(RecipeValidationError, match="not valid Python"):
        _detector_network_imports(path)


# --- wired into load_recipe_manifest / discover_recipes --------------------


def test_load_recipe_manifest_rejects_a_recipe_whose_detector_imports_requests(tmp_path: Path):
    path = _write(tmp_path, "import requests\n\ndef run_recipe_scan():\n    return {}\n")
    with pytest.raises(RecipeValidationError, match="network-capable"):
        load_recipe_manifest(path)


def test_load_recipe_manifest_accepts_a_clean_detector(tmp_path: Path):
    path = _write(
        tmp_path,
        "import json\n\ndef run_recipe_scan():\n    return json.loads('{}')\n",
    )
    manifest = load_recipe_manifest(path)
    assert manifest.slug == "net-test-recipe"


def test_load_recipe_manifest_does_not_flag_a_recipe_whose_detector_file_does_not_exist_yet(tmp_path: Path):
    # Division of responsibility: a detector_file that names a file not yet
    # on disk is `load_detector`'s own failure to report ("does not exist"),
    # not this check's -- this check only ever grades a detector that is
    # actually there to read, never invents a violation for a file it can't
    # open.
    data = _manifest_json()
    d = tmp_path / RECIPES_DIR_NAME / data["slug"]
    d.mkdir(parents=True)
    (d / "recipe.json").write_text(json.dumps(data))
    # detector.py deliberately never written.
    manifest = load_recipe_manifest(d / "recipe.json")
    assert manifest.detector_file == "detector.py"


def test_discover_recipes_names_the_offending_recipe(tmp_path: Path):
    _write(
        tmp_path,
        "import socket\n\ndef run_recipe_scan():\n    return {}\n",
        slug="bad-network-recipe",
    )
    with pytest.raises(RecipeValidationError) as excinfo:
        discover_recipes(tmp_path)
    msg = str(excinfo.value)
    assert "bad-network-recipe" in msg
    assert "socket" in msg


def test_discover_recipes_still_passes_a_directory_of_clean_recipes(tmp_path: Path):
    _write(
        tmp_path,
        "import json\n\ndef run_recipe_scan():\n    return json.loads('{}')\n",
        slug="good-network-recipe",
    )
    manifests = discover_recipes(tmp_path)
    assert [m.slug for m in manifests] == ["good-network-recipe"]


# --- the real, live repo tree: regression-pinned clean, then mutated -------


def test_every_real_shipped_recipe_detector_is_currently_free_of_network_imports():
    """Direct proof, not merely "discover_recipes(FENCEPOST_ROOT) didn't
    raise" (test_recipes.py already covers that indirectly for the schema
    checks) -- names exactly what's being proven, the same discipline
    `test_all_real_shipped_recipes_pass_the_oath_coverage_check` already
    holds for scope coverage."""
    manifests = discover_recipes(FENCEPOST_ROOT)
    assert len(manifests) >= 42
    for m in manifests:
        detector_path = m.path.parent / m.detector_file
        found = _detector_network_imports(detector_path)
        assert found == [], f"{m.slug}'s detector.py imports network-capable module(s) {found}"


def test_a_real_detectors_own_source_mutated_to_add_a_network_import_would_flip_this_check_red():
    """Hand-verification, in test form -- the same "prove the net catches
    something" discipline `test_recipe_ordinal_doctrine.py` (task 522) and
    `test_consent_doctrine.py::test_parser_actually_detects_drift_not_just_
    tautologically_passes` already hold their own checkers to. Takes one
    REAL, live detector.py's actual source verbatim, appends a single
    `import requests` line the way a future contributed recipe genuinely
    could, and proves `_detector_network_imports` disagrees on the mutated
    copy while the real, unmutated file on disk still reads clean --
    proving the mutation is what broke it, not a scanner that's simply
    broken regardless of input."""
    manifests = discover_recipes(FENCEPOST_ROOT)
    real_manifest = next(m for m in manifests if m.slug == "example-release-vs-changelog")
    real_detector_path = real_manifest.path.parent / real_manifest.detector_file
    real_source = real_detector_path.read_text(encoding="utf-8")

    assert _detector_network_imports(real_detector_path) == [], (
        "the real, unmutated reference detector already reads network-capable "
        "-- update this fixture recipe before trusting the mutation below"
    )

    def _check_text(tmp_path: Path, text: str) -> list[str]:
        mutated_path = tmp_path / "mutated_detector.py"
        mutated_path.write_text(text, encoding="utf-8")
        return _detector_network_imports(mutated_path)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        mutated_source = real_source + "\nimport requests\n"
        assert mutated_source != real_source
        mutated_found = _check_text(Path(tmp), mutated_source)
        assert mutated_found == ["requests"]

    # And the real file on disk is unaffected by any of this -- still clean.
    assert _detector_network_imports(real_detector_path) == []
