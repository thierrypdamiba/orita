#!/usr/bin/env python3
"""Task 546. The rendering half `scan_files.py`/`text_patterns.py` left duplicated.

`scan_files.py` (task 513/515) unified the file-walk and memoization
boilerplate five of these checks share; `text_patterns.py` (task 418)
unified their shared regex patterns. Neither ever touched the one function
all six still carried independently, byte-identical once each check's own
label/detail/key-field text is treated as a parameter rather than a
difference: `format_violations`, the "clean" one-liner or "N VIOLATION(S)
FOUND" header plus one `file:line [key] :: snippet` line per violation.
`duplicate_regex_check.py` never caught it -- it only inspects
`re.compile()` call sites, never duplicated function bodies (scan_files.py's
own docstring, task 513, already named this exact blind spot for a
different pair of duplicates).

Found by an AST-hash sweep of every `tools/*.py` function body with
constant values normalized before hashing (the six copies' message text
differs by design -- that's a difference in constants, not in code shape,
the same normalization task 538 used to catch its own three-file loader
duplicate hiding behind one differing string): `petition_limits_check.py`,
`no_grading_check.py`, `hand_lore_check.py`, `star_covenant_check.py`,
`arcade_hero_check.py`, and `rider_check.py` all define the identical
four-line body under different label/detail/key-field constants. All six
already carry a violation dict shaped `{"file", "line", "snippet", <key>}`
where `<key>` is `"pattern"` (four files), `"shape"` (hand_lore_check.py),
or `"rider"` (rider_check.py) -- confirmed live before writing this module,
not assumed from the names.

Consolidated here as one real `format_violations(...)`, parameterized on
the label ("petition limits check"), the clean-state detail sentence, the
broken-state detail sentence, and the violation dict's own key field name.
Every sibling's own module-level `format_violations(violations)` now
exists only as a one-line delegating wrapper baking in its own constants;
the public call shape (`format_violations(result)`) is unchanged in every
file, and `tests/test_violation_format.py` proves each wrapper's output is
byte-identical to what it produced before this refactor, plus an identity
check (each wrapper's own source calls `violation_format.format_violations`
exactly once) so a future edit to one wrapper is not silently a fork.

Usage: imported only, never run directly.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import violation_format
"""
from __future__ import annotations


def format_violations(
    label: str,
    violations: list[dict[str, object]],
    key_field: str,
    clean_detail: str,
    broken_detail: str,
) -> str:
    """Shared renderer behind six of tools/*.py's own `format_violations`
    wrappers. `label` is the check's own name as it appears in every line
    ("rider check", "star covenant check", ...). `key_field` names which
    key in each violation dict holds that check's own per-violation tag
    word (`"pattern"`, `"shape"`, `"rider"`). `clean_detail` is the tail
    of the all-clear sentence ("no rider violation found in any public
    file"); `broken_detail` is the tail of the violations-found header
    ("a rider is broken"). Every violation dict is expected to carry
    `file`, `line`, and `snippet` -- the three fields common to all six
    real callers -- plus whatever `key_field` names."""
    if not violations:
        return f"{label}: clean -- {clean_detail}"
    lines = [f"{label}: {len(violations)} VIOLATION(S) FOUND -- {broken_detail}"]
    for v in violations:
        lines.append(f"  {v['file']}:{v['line']} [{v[key_field]}] :: {v['snippet']!r}")
    return "\n".join(lines)
