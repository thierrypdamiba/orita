#!/usr/bin/env python3
"""Task 163. Proves tools/network_boundary_check.py really discovers every
real "no network" claim in tools/*.py structurally (never a hand-typed file
list), really checks each one's real, live-loaded imports rather than
trusting the docstring's word for it, and really would have caught a claim
gone false -- both a synthetic module built to fail and a real, live file
from this repo mutated to break the same way.

Task 164 extends this: `find_claiming_files`/`check_network_boundary` only
ever globbed `tools/*.py`, so the same "no network" claim in Fencepost's own
`consent.py`/`draftback.py` (`fencepost/seam_engine/src/seam_engine/`) went
unchecked by anything -- the flagship's own safety-critical trust-boundary
claims, not just the meta-tooling's. `RealSeamEngineDirCase` and
`RealMultiDirCase` below pin and prove the multi-directory extension the
same way `RealToolsDirCase` already pins tools/ alone; `MutationRealSeam
EngineFileCase` proves a real seam_engine file drifted to import a network
module is caught, the same discipline `MutationRealFileCase` already holds
for `vault_leak_check.py`.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT, "tools")
SEAM_ENGINE_SRC_DIR = os.path.join(ROOT, "fencepost", "seam_engine", "src", "seam_engine")
ORACLE_ENGINE_SRC_DIR = os.path.join(ROOT, "oracle", "oracle_engine", "src", "oracle_engine")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


nbc = _load("network_boundary_check", os.path.join(TOOLS_DIR, "network_boundary_check.py"))


# --- structural extraction, proven on a synthetic tree ----------------------

class SyntheticDiscoveryCase(unittest.TestCase):
    """find_claiming_files must key off the real, live directory tree and
    the real phrase in each real file -- proven against a synthetic temp
    directory the real tools/ tree can't be coincidentally satisfying,
    the same discipline test_strategy_targets_check.py's synthetic-fixture
    cases already hold for STRATEGY.md's own extractor."""

    def _write(self, tmp_path, name, text):
        path = os.path.join(tmp_path, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_finds_a_file_that_claims_no_network_plainly(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "claims.py", '"""a read-only scan, no network call of its own."""\n')
            self._write(tmp, "silent.py", '"""does something else entirely."""\n')
            found = nbc.find_claiming_files(tmp)
            self.assertEqual(found, ["claims.py"])

    def test_finds_a_file_whose_claim_wraps_across_a_line(self):
        # petition_limits_check.py's own real shape: "...scan (no\nnetwork,
        # mirrors...)" -- the phrase spans a line break inside the
        # docstring. A bare substring test would silently skip this file.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "wrapped.py", '"""a read-only scan (no\nnetwork, mirrors something else exactly)."""\n')
            found = nbc.find_claiming_files(tmp)
            self.assertEqual(found, ["wrapped.py"])

    def test_ignores_files_that_never_claim_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "unrelated.py", '"""imports requests, never claims otherwise."""\nimport requests\n')
            self.assertEqual(nbc.find_claiming_files(tmp), [])

    def test_only_scans_py_files(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "notes.md", "no network here either, but this is not python\n")
            self.assertEqual(nbc.find_claiming_files(tmp), [])


class SyntheticImportCheckCase(unittest.TestCase):
    """check_source_has_no_network_import must key off the real, parsed
    AST of the given source -- not a keyword scan of the text -- proven on
    synthetic sources covering every network-capable module on the deny
    list, a clean synthetic module, and a network import buried inside a
    function body (not just at module top level)."""

    def test_clean_module_passes(self):
        ok, reason = nbc.check_source_has_no_network_import(
            "import os\nimport re\nimport sys\n\n\ndef f():\n    return os.getcwd()\n"
        )
        self.assertTrue(ok, reason)

    def test_flags_a_bare_import_requests(self):
        ok, reason = nbc.check_source_has_no_network_import("import requests\n")
        self.assertFalse(ok)
        self.assertIn("requests", reason)

    def test_flags_a_from_import_of_urllib_request(self):
        ok, reason = nbc.check_source_has_no_network_import("from urllib.request import urlopen\n")
        self.assertFalse(ok)
        self.assertIn("urllib.request", reason)

    def test_flags_socket_import_hidden_inside_a_function_body(self):
        source = "def f():\n    import socket\n    return socket.socket()\n"
        ok, reason = nbc.check_source_has_no_network_import(source)
        self.assertFalse(ok)
        self.assertIn("socket", reason)

    def test_does_not_flag_urllib_parse(self):
        # urllib.parse has no network capability of its own -- a prefix
        # test against "urllib" would wrongly flag it; this must not.
        ok, reason = nbc.check_source_has_no_network_import("from urllib.parse import urlsplit\n")
        self.assertTrue(ok, reason)

    def test_every_network_deny_list_entry_is_individually_flagged(self):
        for name in sorted(nbc.NETWORK_MODULES):
            with self.subTest(module=name):
                ok, _ = nbc.check_source_has_no_network_import(f"import {name}\n")
                self.assertFalse(ok, f"{name} should be on the network deny-list and flagged")

    def test_flags_a_from_import_of_the_urllib_package_naming_request_as_the_attribute(self):
        # `from urllib import request` sets ast.ImportFrom.module == "urllib"
        # (not "urllib.request"), yet `request.urlopen(...)` reaches the
        # network exactly like `import urllib.request` does. The deny-list
        # only has the exact dotted string "urllib.request", so this form
        # must be reconstructed (module + "." + alias) before matching, or
        # it walks straight past the check that claims to catch it.
        ok, reason = nbc.check_source_has_no_network_import(
            "from urllib import request\n\n\ndef f():\n    return request.urlopen('https://example.com')\n"
        )
        self.assertFalse(ok, "from urllib import request must be flagged as network-capable")
        self.assertIn("urllib.request", reason)

    def test_flags_a_from_import_of_the_http_package_naming_client_as_the_attribute(self):
        # Same shape, the other real stdlib case on the deny-list:
        # "http.client" is on NETWORK_MODULES, but `from http import client`
        # only ever names module "http" unless module+attribute are combined.
        ok, reason = nbc.check_source_has_no_network_import(
            "from http import client\n\n\ndef f():\n    return client.HTTPConnection('example.com')\n"
        )
        self.assertFalse(ok, "from http import client must be flagged as network-capable")
        self.assertIn("http.client", reason)

    def test_does_not_flag_unrelated_from_package_import_attribute_forms(self):
        # Regression guard: reconstructing "module.attribute" must not turn
        # into a blanket prefix match -- "os.path" and "typing.Optional"
        # are not on the deny-list and must keep passing.
        ok, reason = nbc.check_source_has_no_network_import(
            "from os import path\nfrom typing import Optional\n"
        )
        self.assertTrue(ok, reason)

    def test_flags_a_dynamic_importlib_import_module_call(self):
        # Task 536: every case above is a static `import`/`from ... import`
        # statement -- an `ast.Import`/`ast.ImportFrom` node.
        # `importlib.import_module("requests")` is a plain `ast.Call` and
        # was never once looked at, so a file could claim "no network,"
        # genuinely bind the real `requests` module through this call, and
        # still pass. `fencepost/seam_engine/src/seam_engine/recipes.py`'s
        # own independent copy of this deny-list logic had the identical
        # gap, closed the same task.
        ok, reason = nbc.check_source_has_no_network_import(
            "import importlib\n\n\ndef f():\n    return importlib.import_module('requests')\n"
        )
        self.assertFalse(ok)
        self.assertIn("requests", reason)

    def test_flags_a_dynamic_import_module_call_via_a_direct_from_import(self):
        ok, reason = nbc.check_source_has_no_network_import(
            "from importlib import import_module\n\n\ndef f():\n    return import_module('socket')\n"
        )
        self.assertFalse(ok)
        self.assertIn("socket", reason)

    def test_flags_a_dunder_import_call(self):
        ok, reason = nbc.check_source_has_no_network_import(
            "def f():\n    return __import__('http.client')\n"
        )
        self.assertFalse(ok)
        self.assertIn("http.client", reason)

    def test_does_not_flag_a_dynamic_import_of_a_non_literal_name(self):
        # Narrow, structural claim, not dataflow analysis: a variable
        # argument cannot be statically proven to name a network module.
        ok, reason = nbc.check_source_has_no_network_import(
            "import importlib\n\n\ndef f(name='json'):\n    return importlib.import_module(name)\n"
        )
        self.assertTrue(ok, reason)

    def test_does_not_flag_a_dynamic_import_of_a_clean_module(self):
        ok, reason = nbc.check_source_has_no_network_import(
            "import importlib\n\n\ndef f():\n    return importlib.import_module('json')\n"
        )
        self.assertTrue(ok, reason)


# --- the live regression pin: today's real tools/ tree -----------------------

class RealToolsDirCase(unittest.TestCase):
    """Pins today's real, live-discovered set of claiming files and proves
    the real check_network_boundary() finds every one of them clean --
    live-loaded off the real tools/ directory, never a hand-typed copy of
    either the file list or its contents."""

    # Deliberately updatable on purpose, same discipline every other live
    # pin in this suite already holds (test_strategy_targets_check.py's
    # RealStrategyMdCase, test_cadence_actor_constant_doctrine.py's
    # test_family_is_non_trivial): a future nineteenth claiming file
    # landing should grow this list the same hour, not silently pass a
    # stale assertion.
    EXPECTED_TODAY = {
        "arcade_app_watch.py",
        "child_work_check.py",
        "ci_watch.py",
        "duplicate_regex_check.py",
        "gateway_toolset_check.py",
        "good_first_issue_check.py",
        "hand_lore_check.py",
        "journal_numbering_check.py",
        "metrics_field_completeness_check.py",
        "network_boundary_check.py",
        "nyx_traffic_check.py",
        "petition_cadence_check.py",
        "petition_limits_check.py",
        "recipe_readme_check.py",
        "report_cadence_check.py",
        "rider_check.py",
        "ritual_check.py",
        "scopes_completeness_check.py",
        "site_link_check.py",
        "square_check.py",
        "star_covenant_check.py",
        "vault_leak_check.py",
        "verdict_provenance_check.py",
        "wip_reclaim_check.py",
        "word_watch.py",
    }

    def test_live_discovery_matches_todays_real_set(self):
        found = set(nbc.find_claiming_files())
        self.assertEqual(found, self.EXPECTED_TODAY)

    def test_sanity_floor_guards_against_a_glob_typo(self):
        # Guards against TOOLS_DIR resolving to the wrong place and every
        # other test in this file passing vacuously as a result -- the
        # same guard test_cadence_census.py's test_at_least_the_known_
        # cadence_family_is_present already holds for oracle_engine.
        self.assertGreaterEqual(len(nbc.find_claiming_files()), 15)

    def test_every_real_claiming_file_holds_the_boundary_today(self):
        result = nbc.check_network_boundary()
        broken = {name: r["reason"] for name, r in result.items() if not r["ok"]}
        self.assertEqual(
            broken,
            {},
            f"the following tools/*.py files claim \"no network\" but really "
            f"import a network-capable module: {broken}",
        )

    def test_result_keys_match_live_discovery_exactly(self):
        result = nbc.check_network_boundary()
        self.assertEqual(set(result.keys()), set(nbc.find_claiming_files()))

    def test_format_reports_clean_for_the_real_tree(self):
        text = nbc.format_network_boundary(nbc.check_network_boundary())
        self.assertIn("clean", text)
        self.assertIn(f'{len(self.EXPECTED_TODAY)} file(s)', text)

    def test_every_real_claiming_file_parses_as_valid_python(self):
        # Sanity: check_network_boundary must not be silently swallowing a
        # SyntaxError -- every real file really does parse.
        for name in nbc.find_claiming_files():
            with self.subTest(name=name):
                path = os.path.join(TOOLS_DIR, name)
                with open(path, encoding="utf-8") as f:
                    ast.parse(f.read())  # raises on its own if malformed


# --- mutation: proves the checker actually bites -----------------------------

class MutationSyntheticCase(unittest.TestCase):
    """A synthetic module that claims "no network" but doesn't hold it --
    the checker must flag it, never pass it because the docstring sounded
    right."""

    def test_checker_flags_a_synthetic_module_that_lies_about_its_boundary(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "lying_check.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    '"""A read-only, local-filesystem-only scan, no network '
                    'call of its own -- mirrors vault_leak_check.py exactly."""\n'
                    "import os\n"
                    "import requests\n\n"
                    "def find_violations():\n"
                    "    return requests.get('https://example.com').json()\n"
                )
            result = nbc.check_network_boundary(tmp)
            self.assertIn("lying_check.py", result)
            self.assertFalse(result["lying_check.py"]["ok"])
            self.assertIn("requests", result["lying_check.py"]["reason"])
            formatted = nbc.format_network_boundary(result)
            self.assertIn("BROKEN", formatted)
            self.assertIn("lying_check.py", formatted)


class MutationRealFileCase(unittest.TestCase):
    """Reconstructs a REAL file from this repo (vault_leak_check.py) with
    a plausible future drift applied -- a network import added, the way a
    "just add a quick live lookup" patch would do it -- while its own "no
    network" docstring claim is left completely untouched, the exact
    silent-drift shape this task's own docstring warns about. Proves the
    checker disagrees with the file's own claim on the mutated copy, then
    proves it agrees on the real, unmutated file, so the disagreement is
    caused by the mutation and nothing else."""

    def setUp(self):
        real_path = os.path.join(TOOLS_DIR, "vault_leak_check.py")
        with open(real_path, encoding="utf-8") as f:
            self.real_source = f.read()
        # Confirm the fixture premise before mutating it: the real file
        # really does carry the claim this test is about.
        self.assertRegex(self.real_source, nbc.CLAIM_PATTERN)

    def test_real_file_passes_unmutated(self):
        ok, reason = nbc.check_source_has_no_network_import(self.real_source)
        self.assertTrue(ok, reason)

    def test_mutated_copy_with_an_added_network_import_is_caught(self):
        # Insert a plausible drift: a live-lookup helper added near the
        # top of the real file, importing requests, while every existing
        # line -- including the "no network" docstring claim -- is left
        # exactly as it is in the real repo today.
        marker = "from __future__ import annotations\n"
        self.assertIn(marker, self.real_source, "fixture premise: real file's own import block")
        mutated = self.real_source.replace(
            marker,
            marker + "import requests  # drift: a hypothetical live escalation lookup\n",
            1,
        )
        # The claim itself is untouched -- still there, still lying now.
        self.assertRegex(mutated, nbc.CLAIM_PATTERN)
        ok, reason = nbc.check_source_has_no_network_import(mutated)
        self.assertFalse(ok, "a real file drifted to import requests must be flagged, not waved through")
        self.assertIn("requests", reason)

    def test_checker_flags_the_mutated_file_end_to_end_via_check_network_boundary(self):
        import tempfile
        marker = "from __future__ import annotations\n"
        mutated = self.real_source.replace(
            marker, marker + "import httpx  # drift\n", 1
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "vault_leak_check.py"), "w", encoding="utf-8") as f:
                f.write(mutated)
            result = nbc.check_network_boundary(tmp)
        self.assertFalse(result["vault_leak_check.py"]["ok"])
        self.assertIn("httpx", result["vault_leak_check.py"]["reason"])


# --- the live regression pin: today's real Fencepost seam_engine src dir ----

class RealSeamEngineDirCase(unittest.TestCase):
    """Pins today's real, live-discovered "no network" claims in Fencepost's
    own `seam_engine` source -- the flagship's safety-critical files, not
    tools/'s meta-checkers -- and proves the real, unqualified
    `check_network_boundary(SEAM_ENGINE_SRC_DIR)` finds both clean.
    Deliberately updatable, same discipline as `RealToolsDirCase.
    EXPECTED_TODAY`: a future fourth claiming file landing in this directory
    should grow this set the same hour, not silently pass a stale
    assertion. Task 529: `recipes.py` joined this set the hour it gained
    `_detector_network_imports()` and the "that it names no
    network-capable import anywhere in its [detector]" docstring line --
    a true claim about the file's own AST-walking source, which imports
    no network-capable module itself."""

    EXPECTED_TODAY = {"consent.py", "draftback.py", "recipes.py"}

    def test_live_discovery_matches_todays_real_set(self):
        found = set(nbc.find_claiming_files(SEAM_ENGINE_SRC_DIR))
        self.assertEqual(found, self.EXPECTED_TODAY)

    def test_every_real_claiming_file_holds_the_boundary_today(self):
        result = nbc.check_network_boundary(SEAM_ENGINE_SRC_DIR)
        broken = {name: r["reason"] for name, r in result.items() if not r["ok"]}
        self.assertEqual(
            broken,
            {},
            f"the following seam_engine files claim \"no network\" but really "
            f"import a network-capable module: {broken}",
        )


class RealOracleEngineDirCase(unittest.TestCase):
    """Task 446: `oracle/oracle_engine/src/oracle_engine/` -- the Oracle
    Desk's own 58-file cadence/autograde engine -- is now a scanned
    `SEARCH_DIRS` member, the same extension `RealSeamEngineDirCase` already
    pins for Fencepost's own source. A single-line `grep -rl "no network"`
    over this directory (the check this task's own commit message first ran
    by hand) reported zero hits and would have shipped this class with an
    empty `EXPECTED_TODAY` -- but the checker's own `CLAIM_PATTERN` is
    `re.compile(r"no\\s+network")`, and `\\s` matches a newline: `copylint.
    py`'s real docstring wraps exactly there ("makes no\\nnetwork call,
    writes nothing..."), so it silently escaped a same-line grep while
    still being a real, structural "no network" trust-boundary claim this
    checker was built to catch. Running `nbc.find_claiming_files()` itself
    (not a hand-typed grep) is what actually caught it. Pinned here
    (deliberately updatable, same discipline as `RealToolsDirCase.
    EXPECTED_TODAY` -- a future second claiming file landing here should
    grow this set the same hour, not silently pass a stale assertion)."""

    EXPECTED_TODAY = {"copylint.py"}

    def test_live_discovery_matches_todays_real_set(self):
        found = set(nbc.find_claiming_files(ORACLE_ENGINE_SRC_DIR))
        self.assertEqual(found, self.EXPECTED_TODAY)

    def test_directory_is_a_real_nonempty_source_tree(self):
        # Guards against a typo'd path silently scanning an empty/missing
        # directory and reporting a trivially-true "zero claims" -- the
        # same sanity-floor discipline RealToolsDirCase's sibling test
        # holds against a glob typo.
        py_files = [
            n for n in os.listdir(ORACLE_ENGINE_SRC_DIR) if n.endswith(".py")
        ]
        self.assertGreater(len(py_files), 10, "oracle_engine dir looks empty or mistyped")

    def test_oracle_engine_dir_is_in_search_dirs(self):
        self.assertIn(ORACLE_ENGINE_SRC_DIR, nbc.SEARCH_DIRS)

    def test_every_real_claiming_file_holds_the_boundary_today(self):
        result = nbc.check_network_boundary(ORACLE_ENGINE_SRC_DIR)
        broken = {name: r["reason"] for name, r in result.items() if not r["ok"]}
        self.assertEqual(broken, {})


class RealMultiDirCase(unittest.TestCase):
    """Proves the multi-directory fold (`find_claiming_files_all`/`check_
    network_boundary_all`, task 164) really combines tools/ and seam_engine's
    real, live claims -- keyed by repo-root-relative path, no collision, no
    file silently dropped by one side or the other -- and that the CLI's own
    exit-code contract still holds across the combined set."""

    def test_combined_discovery_is_the_union_of_both_directories_relative_paths(self):
        combined = set(nbc.find_claiming_files_all())
        tools_only = {
            os.path.relpath(os.path.join(TOOLS_DIR, n), ROOT)
            for n in nbc.find_claiming_files(TOOLS_DIR)
        }
        seam_only = {
            os.path.relpath(os.path.join(SEAM_ENGINE_SRC_DIR, n), ROOT)
            for n in nbc.find_claiming_files(SEAM_ENGINE_SRC_DIR)
        }
        oracle_only = {
            os.path.relpath(os.path.join(ORACLE_ENGINE_SRC_DIR, n), ROOT)
            for n in nbc.find_claiming_files(ORACLE_ENGINE_SRC_DIR)
        }
        self.assertEqual(combined, tools_only | seam_only | oracle_only)
        self.assertIn("fencepost/seam_engine/src/seam_engine/consent.py", combined)
        self.assertIn("fencepost/seam_engine/src/seam_engine/draftback.py", combined)
        self.assertIn("tools/vault_leak_check.py", combined)
        self.assertIn("oracle/oracle_engine/src/oracle_engine/copylint.py", combined)

    def test_combined_check_is_clean_and_keys_match_combined_discovery(self):
        result = nbc.check_network_boundary_all()
        self.assertEqual(set(result.keys()), set(nbc.find_claiming_files_all()))
        broken = {k: r["reason"] for k, r in result.items() if not r["ok"]}
        self.assertEqual(broken, {})

    def test_combined_result_count_is_the_sum_of_all_three_directories(self):
        result = nbc.check_network_boundary_all()
        tools_count = len(nbc.check_network_boundary(TOOLS_DIR))
        seam_count = len(nbc.check_network_boundary(SEAM_ENGINE_SRC_DIR))
        oracle_count = len(nbc.check_network_boundary(ORACLE_ENGINE_SRC_DIR))
        self.assertEqual(len(result), tools_count + seam_count + oracle_count)

    def test_format_reports_clean_for_the_combined_tree(self):
        text = nbc.format_network_boundary(nbc.check_network_boundary_all())
        self.assertIn("clean", text)


# --- mutation: proves the checker bites on a real seam_engine file too ------

class MutationRealSeamEngineFileCase(unittest.TestCase):
    """Reconstructs a REAL Fencepost file (consent.py) with a plausible
    future drift applied -- a network import added, its own "no network"
    claim left untouched -- the identical shape `MutationRealFileCase`
    already proves for `vault_leak_check.py`, found here in the flagship's
    own source instead of tools/'s meta-checkers."""

    def setUp(self):
        real_path = os.path.join(SEAM_ENGINE_SRC_DIR, "consent.py")
        with open(real_path, encoding="utf-8") as f:
            self.real_source = f.read()
        self.assertRegex(self.real_source, nbc.CLAIM_PATTERN)

    def test_real_file_passes_unmutated(self):
        ok, reason = nbc.check_source_has_no_network_import(self.real_source)
        self.assertTrue(ok, reason)

    def test_mutated_copy_with_an_added_network_import_is_caught(self):
        marker = "from __future__ import annotations\n"
        self.assertIn(marker, self.real_source, "fixture premise: real file's own import block")
        mutated = self.real_source.replace(
            marker,
            marker + "import httpx  # drift: a hypothetical live scope-check call\n",
            1,
        )
        self.assertRegex(mutated, nbc.CLAIM_PATTERN)
        ok, reason = nbc.check_source_has_no_network_import(mutated)
        self.assertFalse(ok, "a real seam_engine file drifted to import httpx must be flagged")
        self.assertIn("httpx", reason)

    def test_checker_flags_the_mutated_file_end_to_end_via_check_network_boundary_all(self):
        marker = "from __future__ import annotations\n"
        mutated = self.real_source.replace(
            marker, marker + "import socket  # drift\n", 1
        )
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "consent.py"), "w", encoding="utf-8") as f:
                f.write(mutated)
            result = nbc.check_network_boundary_all((tmp,))
        key = os.path.relpath(os.path.join(tmp, "consent.py"), nbc.ROOT)
        self.assertFalse(result[key]["ok"])
        self.assertIn("socket", result[key]["reason"])


class MutationSyntheticOracleEngineFileCase(unittest.TestCase):
    """No real oracle_engine file claims "no network" today (`RealOracle
    EngineDirCase` above), so unlike `MutationRealSeamEngineFileCase` there
    is no real claiming file to mutate. This proves the same guarantee the
    other direction: a HYPOTHETICAL future oracle_engine module that claims
    the boundary and then drifts to import a network module is still caught
    by the widened `SEARCH_DIRS`, end to end through `check_network_
    boundary_all`, keyed exactly as `ORACLE_ENGINE_SRC_DIR` would key it --
    not just via an arbitrary tempdir like `MutationRealFileCase` already
    proves generically."""

    def test_a_future_oracle_engine_file_that_lies_about_no_network_is_caught(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            fake_oracle_dir = os.path.join(tmp, "oracle_engine")
            os.makedirs(fake_oracle_dir)
            with open(os.path.join(fake_oracle_dir, "future_module.py"), "w", encoding="utf-8") as f:
                f.write(
                    '"""A hypothetical future oracle_engine module. Pure\n'
                    'local-filesystem reads, no network, mirroring consent.\n'
                    'py\'s own boundary claim."""\n'
                    "import os\n"
                    "import socket  # drift: a hypothetical live lookup\n"
                )
            result = nbc.check_network_boundary_all((fake_oracle_dir,))
            key = os.path.relpath(os.path.join(fake_oracle_dir, "future_module.py"), nbc.ROOT)
            self.assertFalse(result[key]["ok"])
            self.assertIn("socket", result[key]["reason"])


class CLIEntrypointCase(unittest.TestCase):
    """The module's own __main__ exit-code contract: 0 when every claim
    holds, 1 when at least one is broken -- proven by direct call, no
    subprocess needed since check_network_boundary/check_network_boundary_all
    are pure functions of the directories they're given. `__main__` (task
    164) now calls the combined `check_network_boundary_all()`, so this
    proves the exit-code contract against the same function the CLI itself
    runs, not just the tools/-only one."""

    def test_exit_code_is_zero_when_all_real_claims_hold(self):
        result = nbc.check_network_boundary()
        self.assertTrue(all(r["ok"] for r in result.values()))

    def test_exit_code_is_zero_when_all_real_combined_claims_hold(self):
        result = nbc.check_network_boundary_all()
        self.assertTrue(all(r["ok"] for r in result.values()))

    def test_all_ok_computation_flips_false_on_one_broken_entry(self):
        fake_result = {"a.py": {"ok": True, "reason": "ok"}, "b.py": {"ok": False, "reason": "imports socket"}}
        self.assertFalse(all(r["ok"] for r in fake_result.values()))


# --- the module's own top docstring claim, cross-checked -------------------
#
# The same "claims a number about itself, nothing ever checked it against
# the live thing it describes" shape test_recipe_readme_check.py's own
# DocstringCountDoctrineCase (task 479) closed for _community_recipes_
# section's docstring, found here one module over: network_boundary_check.
# py's own top docstring said "eighteen files" from the hour task 163 wrote
# it (18 real claiming files then); seven more tools/*_check.py files have
# independently repeated the "no network" claim since, so the real live
# count is 25 today, not 18. The module's own EXPECTED_TODAY-driven tests
# above (RealToolsDirCase) already caught every one of those seven as they
# landed -- this was pure prose, never read back against find_claiming_
# files()'s own live count. Fixed at the root (the docstring itself),
# pinned here so it cannot silently drift again.
_CARDINAL_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty-one": 21, "twenty-two": 22, "twenty-three": 23, "twenty-four": 24,
    "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28,
    "twenty-nine": 29, "thirty": 30,
}

_TODAY_COUNT_CLAIM_RE = re.compile(r"([a-z-]+) carry it today")


def claimed_today_count(doc_text: str) -> int:
    """Live-extracts the module's own "N carry it today" claim -- never a
    second hand-typed 25. Raises if the sentence is missing or uses a
    cardinal word this check doesn't recognize, rather than silently
    passing an unchecked claim through."""
    match = _TODAY_COUNT_CLAIM_RE.search(doc_text.replace("\n", " "))
    if not match:
        raise AssertionError(
            "network_boundary_check.py's own docstring no longer contains "
            "an 'N carry it today' sentence -- this doctrine test has "
            "nothing left to cross-check"
        )
    word = match.group(1).lower()
    if word not in _CARDINAL_WORDS:
        raise AssertionError(
            f"network_boundary_check.py's docstring uses an unrecognized "
            f"cardinal word {word!r} -- add it to _CARDINAL_WORDS before "
            "trusting this check"
        )
    return _CARDINAL_WORDS[word]


class DocstringCountDoctrineCase(unittest.TestCase):
    def test_claim_extraction_is_structural_not_hardcoded(self):
        self.assertEqual(
            claimed_today_count("nine carry it today, somehow"),
            9,
        )

    def test_claim_missing_sentence_raises(self):
        with self.assertRaises(AssertionError):
            claimed_today_count("Nothing here about a file count.")

    def test_real_live_claiming_file_count_is_currently_twenty_five(self):
        # Regression pin: today's real, live tools/*.py claiming-file count.
        self.assertEqual(len(nbc.find_claiming_files()), 25)

    def test_docstring_matches_the_real_live_count(self):
        real_count = len(nbc.find_claiming_files())
        claimed = claimed_today_count(nbc.__doc__)
        self.assertEqual(
            claimed, real_count,
            msg=f"network_boundary_check.py's own docstring claims {claimed} "
                f"files carry the claim today, but the real live count is "
                f"{real_count}",
        )

    def test_one_fewer_claiming_file_in_the_claim_would_flip_this_check_red(self):
        """Mutation-based hand-verification, same discipline
        test_recipe_readme_check.py's own analogous doctrine test already
        holds itself to: prove the checker actually flags a real drift,
        not just that it happens to pass today."""
        real_count = len(nbc.find_claiming_files())
        wrong_word = _word_for(real_count - 1)
        wrong_doc = nbc.__doc__.replace("twenty-five carry it today", f"{wrong_word} carry it today")
        claimed = claimed_today_count(wrong_doc)
        self.assertNotEqual(claimed, real_count)


def _word_for(n: int) -> str:
    for word, value in _CARDINAL_WORDS.items():
        if value == n:
            return word
    raise AssertionError(f"no cardinal word known for {n}")


if __name__ == "__main__":
    unittest.main()
