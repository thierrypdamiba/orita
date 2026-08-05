"""Tests for `seam_engine.closing_keywords` -- the shared GitHub
closing-keyword ("closes/fixes/resolves #N") law.

Three recipes each defined their own textually-identical copy of this
regex -- `commit-closes-keyword-issue-still-open` (as `CLOSING_KEYWORD_RE`),
`issue-closed-never-released` (as `CLAIM_RE`), and
`release-claims-unfixed-issue` (as a second `CLOSING_KEYWORD_RE`) -- each
with a comment claiming to mirror `tools/closing_keyword_guard.py` or one
of the other two recipes, but none of those comments were ever backed by
an import. This is the same "textually identical... nothing stopping them
from drifting apart" shape task 389 found and fixed for `#N` extraction
(`references.py`), task 390 found and fixed a second time for the
"milestone #N" claim phrase (`milestone_claims.py`), and task 393 found and
fixed a third time for the "ships/includes/merges/via #N" claim phrase
(`pr_claims.py`), found here a fourth time (task 394) and fixed the same
way. This module is now the one real source; these tests check its own
behavior directly, and `TestAllNineDetectorsShareTheLaw` below is the
regression test that is supposed to go red the moment any recipe's
detector goes back to defining its own local copy instead of importing
this one.

Task 544: that regression test's own `_CASES` list only ever grew by
hand, one migration at a time (task 394's original three, task 543's two
more) -- it was never swept against the real, current set of detectors
that import `CLOSING_KEYWORD_RE`/`CLAIM_RE` directly from this module.
Four more recipes had quietly joined that set by the time they shipped,
correctly importing from here from birth, never touched by a migration
task and so never added to `_CASES` either:
`commit-closes-keyword-pr-still-open` (25th recipe),
`merged-pr-pr-still-open` (26th), `tweet-claims-unfixed-issue` (28th), and
`milestone-claims-unfixed-issue` (45th). Proven live before this task
touched anything: hand-reverting `tweet-claims-unfixed-issue/detector.py`
to its own local `re.compile` copy (the exact regression this class exists
to catch) left every test in this file green -- the class's own docstring
claim was false for those four detectors. `tools/duplicate_regex_check.py`
(a separate, repo-wide sweep) still caught that same hand-revert, so the
gap was never a totally silent one -- but this file's own regression net,
the one this class's docstring specifically promises, missed it. `_CASES`
now names all nine real `CLOSING_KEYWORD_RE`/`CLAIM_RE` consumers; two
further recipes (`good-first-issue-never-referenced`,
`readme-claims-unfixed-issue`) import the wrapper function
`closing_keyword_numbers` instead of the raw regex and are a genuinely
different shape (no module-level regex attribute to assert parity on),
out of scope for this class same as before.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from seam_engine.closing_keywords import CLOSING_KEYWORD_RE, closing_keyword_numbers

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]

# NOTE on why the regression class below reads source text rather than
# comparing `detector.CLOSING_KEYWORD_RE is CLOSING_KEYWORD_RE`: Python's
# `re.compile` memoizes -- two independently written `re.compile(same
# pattern, same flags)` calls anywhere in the process return the SAME
# cached Pattern object (verified live: `re.compile(p) is re.compile(p)`
# is True for this exact pattern). An `is` check on the regex object would
# therefore pass even if a detector went back to defining its own local
# copy with byte-identical source -- exactly the false-negative this test
# exists to prevent. `pr_claims.py`'s own identity test works because it
# checks a FUNCTION object instead (`claimed_pr_numbers`), and functions
# are never memoized the way compiled regexes are; this module's shared
# surface is the regex itself (existing call sites use `.finditer`/
# `.findall` directly), so the real regression signal has to come from the
# source text: does the file import the shared name, and does it NOT also
# define its own `re.compile` for it.


def _load_detector(recipe_slug: str, test_module_name: str):
    """Load a recipe's `detector.py` the same way `seam_engine.recipes.
    load_detector` loads any recipe at runtime -- same discipline as
    `test_pr_claims.py`'s own `_load_detector`."""
    path = FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py"
    spec = importlib.util.spec_from_file_location(test_module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[test_module_name] = module
    spec.loader.exec_module(module)
    return module


def _detector_source(recipe_slug: str) -> str:
    return (FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py").read_text()


class TestClosingKeywordNumbers:
    def test_present_tense_closes(self) -> None:
        assert closing_keyword_numbers("closes #1") == [1]

    def test_present_tense_fixes(self) -> None:
        assert closing_keyword_numbers("fixes #2") == [2]

    def test_present_tense_resolves(self) -> None:
        assert closing_keyword_numbers("resolves #3") == [3]

    def test_past_tense_closed(self) -> None:
        assert closing_keyword_numbers("closed #4") == [4]

    def test_past_tense_fixed(self) -> None:
        assert closing_keyword_numbers("fixed #5") == [5]

    def test_past_tense_resolved(self) -> None:
        assert closing_keyword_numbers("resolved #6") == [6]

    def test_bare_verb_close(self) -> None:
        assert closing_keyword_numbers("close #7") == [7]

    def test_bare_verb_fix(self) -> None:
        assert closing_keyword_numbers("fix #8") == [8]

    def test_bare_verb_resolve(self) -> None:
        assert closing_keyword_numbers("resolve #9") == [9]

    def test_optional_colon(self) -> None:
        assert closing_keyword_numbers("Closes: #10") == [10]

    def test_case_insensitive(self) -> None:
        assert closing_keyword_numbers("CLOSES #11") == [11]

    def test_present_participle_never_matches(self) -> None:
        # Iron Rule #8's own prescribed safe phrasing -- "closing #N" is
        # outside GitHub's real closing-keyword grammar.
        assert closing_keyword_numbers("closing #12") == []

    def test_no_keyword(self) -> None:
        assert closing_keyword_numbers("routine cleanup, nothing here") == []

    def test_bare_hash_with_no_keyword_is_not_a_match(self) -> None:
        assert closing_keyword_numbers("see #13 for background") == []

    def test_multiple_matches_in_order(self) -> None:
        assert closing_keyword_numbers("closes #1 and fixes #2") == [1, 2]

    def test_duplicate_number_kept_not_deduplicated(self) -> None:
        assert closing_keyword_numbers("fixes #1, closes #1") == [1, 1]


class TestClosingKeywordRe:
    def test_pattern_source(self) -> None:
        assert (
            CLOSING_KEYWORD_RE.pattern
            == r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#(\d+)\b"
        )


class TestAllNineDetectorsShareTheLaw:
    """The regression test: all nine closing-keyword-grammar recipes must
    actually IMPORT `CLOSING_KEYWORD_RE` from `seam_engine.closing_keywords`
    and must NOT also define their own local `re.compile` for it. Checked
    two ways for each detector: (1) the loaded module's own attribute still
    behaves exactly like the shared regex (functional parity -- cheap to
    keep even though it can't prove import-vs-coincidence on its own,
    since `re.compile` memoizes identical patterns to the same cached
    object); (2) the detector's SOURCE TEXT names the real import and
    contains no local `re.compile(` call of its own -- the actual
    regression signal, since a reverted detector would still pass (1) via
    `re`'s cache but would fail (2) immediately.

    ROADMAP.md #543 added `merged-pr-issue-still-open` and
    `issue-closed-pr-still-open`: they used to carry their own deliberately
    narrower, present-tense-only `_CLOSES_RE` (ruled a real, working,
    intentional two-copy law when this module was first written -- see this
    module's own docstring) -- migrated here once that narrower grammar was
    shown to actually miss real past-tense closing promises GitHub itself
    honors.

    ROADMAP.md #544 added the remaining four: `commit-closes-keyword-
    pr-still-open`, `merged-pr-pr-still-open`, `tweet-claims-unfixed-issue`,
    and `milestone-claims-unfixed-issue` -- each already correctly imported
    the shared regex from the day it shipped, so this was never a live bug
    in those detectors, only a hole in this class's own coverage of them."""

    _CASES = [
        ("commit-closes-keyword-issue-still-open", "CLOSING_KEYWORD_RE"),
        ("commit-closes-keyword-pr-still-open", "CLOSING_KEYWORD_RE"),
        ("issue-closed-never-released", "CLAIM_RE"),
        ("release-claims-unfixed-issue", "CLOSING_KEYWORD_RE"),
        ("merged-pr-issue-still-open", "CLOSING_KEYWORD_RE"),
        ("merged-pr-pr-still-open", "CLOSING_KEYWORD_RE"),
        ("issue-closed-pr-still-open", "CLOSING_KEYWORD_RE"),
        ("tweet-claims-unfixed-issue", "CLOSING_KEYWORD_RE"),
        ("milestone-claims-unfixed-issue", "CLOSING_KEYWORD_RE"),
    ]

    def test_functional_parity(self) -> None:
        for slug, attr_name in self._CASES:
            detector = _load_detector(
                slug, f"seam_engine._recipe_{slug.replace('-', '_')}_closing_keywords_test"
            )
            local_re = getattr(detector, attr_name)
            assert local_re.pattern == CLOSING_KEYWORD_RE.pattern
            assert local_re.findall("closes #1, closing #2, fixed #3") == ["1", "3"]

    def test_source_imports_the_shared_module_not_a_local_copy(self) -> None:
        for slug, attr_name in self._CASES:
            source = _detector_source(slug)
            assert "from seam_engine.closing_keywords import" in source, (
                f"{slug}/detector.py no longer imports seam_engine.closing_keywords"
            )
            assert f"{attr_name} = re.compile(" not in source, (
                f"{slug}/detector.py defines its own local {attr_name}"
                " again instead of importing the shared one"
            )
