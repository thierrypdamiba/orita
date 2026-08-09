#!/usr/bin/env python3
"""Task 551. The claimed-vs-real renderer connected_users_check.py and
toolkits_in_use_check.py each carried their own byte-identical copy of.

Both modules (task 145's `toolkits_in_use_check.py`, task 412's
`connected_users_check.py` built to the identical shape one field over)
cross-check the last recorded `records/metrics.jsonl` reading of one
STRATEGY.md adoption metric against `consent_grant_log.py`'s real,
gate-verified ground truth. Each carries its own `format_result(result)`
rendering that comparison into the one line `ritual_check.py` prints --
four branches (no reading yet / clean omission / broken omission / claim
vs. real agree or disagree), differing only in the check's own label
("connected users (OAuth)" vs "toolkits in use"), the omitted field's own
name (`connected_users_oauth` vs `distinct_toolkits_in_use`), and the
unit noun in the agree-branch sentence ("real connected user(s)" vs "real
toolkit(s)"). `duplicate_regex_check.py` never caught it (it only
inspects `re.compile()` call sites); `metrics_reader.py` (task 508)
already unified the READ half these two modules share, but never their
render half.

Found by the same AST-hash sweep of every `tools/*.py` function body
(constant values normalized before hashing) tasks 538/546/548 used --
`format_result` in these two files hashed identical once each check's own
label/field/unit strings are treated as parameters rather than a
difference in code shape.

Consolidated here as one real `format_adoption_result(...)`, parameterized
on the label, the omitted field's own name, and the agree-branch unit
noun. Each sibling's own module-level `format_result(result)` now exists
only as a one-line delegating wrapper baking in its own three constants;
the public call shape (`format_result(result)`) is unchanged in both
files, and `tests/test_adoption_metric_format.py` proves each wrapper's
output is byte-identical to what it produced before this refactor (frozen
fixture strings, not a re-derivation), plus an identity check that each
wrapper's own source calls this function exactly once.

Usage: imported only, never run directly.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import adoption_metric_format
"""
from __future__ import annotations


def format_adoption_result(
    label: str, result: dict[str, object], field_name: str, real_unit: str
) -> str:
    """Shared renderer behind connected_users_check.py's and
    toolkits_in_use_check.py's own `format_result` wrappers. `label` is
    the check's own name as it appears in every line ("connected users
    (OAuth)", "toolkits in use"). `field_name` names the
    `records/metrics.jsonl` field the omitted-field branches cite
    (`connected_users_oauth`, `distinct_toolkits_in_use`). `real_unit`
    is the noun phrase the agree-branch sentence uses for `result["real"]`
    ("real connected user(s)", "real toolkit(s)"). `result` is the dict
    each sibling's own `check_*` function returns:
    `{"clean", "real", "claimed", "claimed_date"}`."""
    if result["claimed"] is None:
        if result["claimed_date"] is None:
            return f"{label}: clean (no metrics.jsonl reading yet; real ground truth is {result['real']})"
        if result["clean"]:
            return (
                f"{label}: clean (metrics.jsonl's {result['claimed_date']} reading names no "
                f"{field_name} field; real ground truth is honestly 0, nothing omitted)"
            )
        return (
            f"{label}: BROKEN -- metrics.jsonl's {result['claimed_date']} reading names no "
            f"{field_name} field, but real ground truth (HAND/consent-grants-log.jsonl, "
            f"gate-verified) is already {result['real']} -- a real count exists and was not recorded, "
            "escalate now"
        )
    if result["clean"]:
        return f"{label}: clean ({result['real']} {real_unit}, metrics.jsonl's {result['claimed_date']} reading agrees)"
    return (
        f"{label}: BROKEN -- metrics.jsonl's {result['claimed_date']} reading claims "
        f"{result['claimed']}, real ground truth (HAND/consent-grants-log.jsonl, gate-verified) is "
        f"{result['real']} -- STRATEGY.md's adoption metric is misreporting live"
    )
