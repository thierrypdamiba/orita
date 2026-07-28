#!/usr/bin/env python3
"""The oath-badge template. Kothar-wa-Khasis, unrequested, again.

Ogun built one of these for Fencepost (`fencepost/seam_engine/src/seam_engine/badge.py`,
task 23): audit the LIVE server's own declared tool metadata against a scope
list, render red the instant a violation exists, green only when every tool
checks out. Nobody asked for the reusable version. You were going to ask for
it the day a second demo, or a second fork, needed its own non-negotiable
proven in code instead of promised in a README. It is already built.

This module is that engine with Fencepost sanded off. It knows nothing about
seam-scans or gaps or Arcade specifically. It knows two things:

1. **How to load a tool catalog.** Point it at `module:attr` (a live MCP
   `app` object, or — for a fixture, a test, or a lighter integration — any
   iterable of tool records). It does not care which, as long as each
   record can answer "what is your declared behavior."
2. **How to check a catalog against an oath.** An oath is just a policy: for
   each named field (`read_only`, `destructive`, `operations`, or whatever a
   fork's non-negotiable actually is), the value a compliant tool MUST
   declare. Anything else is a violation, named, not hidden.

A fork's own non-negotiable does not have to be "read-only." It could be
"no deletes" or "no cross-tenant reads" or anything a policy dict can
express. The mechanism travels; the oath's content is the fork's to write
(`PLATFORM.md`, "what travels free" #3).

Sworn on iron, same as the original.
"""
from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

GREEN = "brightgreen"
RED = "red"

# The default oath, if a fork doesn't declare its own: Ogun's read-only
# clause, verbatim. A fork with a different non-negotiable passes its own
# policy dict to compute_badge_state instead.
DEFAULT_POLICY: dict[str, Any] = {
    "read_only": True,
    "destructive": False,
    "operations": ("read",),
}


def _policy_value_matches(declared_value: Any, policy_value: Any) -> bool:
    """One declared field satisfies one policy requirement.

    Boolean policy values are checked by IDENTITY (``is``), the same
    discipline `seam_engine.badge.ToolAudit.ok` (the original this module's
    own docstring calls "sworn on iron, same as the original") uses for its
    own ``read_only is True`` / ``destructive is False`` checks — not by
    equality. Python treats ``1 == True`` and ``0 == False``, so without
    this, a duck-typed or dict-shaped tool record (the exact "fixture, or a
    lighter integration" shape this module's own docstring advertises
    supporting) declaring ``read_only=1`` instead of an actual ``True``
    would silently pass here while failing the real original's oath.
    Non-boolean policy values (an ``operations`` tuple, for a fork whose
    own non-negotiable isn't boolean-shaped) are still checked by equality,
    unchanged.
    """
    if isinstance(policy_value, bool):
        return declared_value is policy_value
    return declared_value == policy_value


@dataclass(frozen=True)
class ToolAudit:
    """What one tool's own declared metadata says, checked against a policy."""

    name: str
    declared: dict[str, Any]
    policy: dict[str, Any]

    @property
    def ok(self) -> bool:
        return all(
            _policy_value_matches(self.declared.get(k), v) for k, v in self.policy.items()
        )

    @property
    def violation(self) -> str | None:
        if self.ok:
            return None
        mismatches = {
            k: self.declared.get(k)
            for k in self.policy
            if not _policy_value_matches(self.declared.get(k), self.policy[k])
        }
        return f"{self.name}: violates oath {mismatches} (policy wants {self.policy})"


def _normalize_operations(raw: Any) -> tuple[Any, ...]:
    if raw is None:
        return ()
    return tuple(getattr(op, "value", op) for op in raw)


def _extract_declared(record: Any) -> tuple[str, dict[str, Any]]:
    """Pull (name, declared-behavior-dict) off one catalog record.

    Two shapes are understood:
    - The real arcade-mcp shape: a `MaterializedTool` with
      `.definition.name` and `.definition.metadata.behavior` (the same
      object `audit_server_tools` in the Fencepost original reads).
    - A plain, duck-typed shape: anything with `.name`/`["name"]` and
      `.read_only`/`.destructive`/`.operations` (or dict keys of the same
      names) — what a fixture server or a lighter fork's tool registry
      can hand in directly, with no arcade-mcp dependency required.
    """
    definition = getattr(record, "definition", None)
    if definition is not None:
        behavior = getattr(getattr(definition, "metadata", None), "behavior", None)
        return (
            definition.name,
            {
                "read_only": bool(behavior and behavior.read_only),
                "destructive": bool(behavior and behavior.destructive),
                "operations": _normalize_operations(behavior.operations if behavior else None),
            },
        )

    if isinstance(record, dict):
        name = record["name"]
        declared = {k: v for k, v in record.items() if k != "name"}
    else:
        name = record.name
        declared = {
            "read_only": getattr(record, "read_only", None),
            "destructive": getattr(record, "destructive", None),
            "operations": getattr(record, "operations", None),
        }

    if "operations" in declared:
        declared["operations"] = _normalize_operations(declared["operations"])
    return name, declared


def load_catalog(spec: str) -> list[Any]:
    """Import `module:attr` and return an iterable of tool records.

    If the loaded attribute has a `_catalog` (the live arcade-mcp `app`
    shape), that is the catalog. Otherwise the attribute itself must
    already be iterable — a fixture list, a fork's own registry, anything.
    """
    module_name, _, attr_name = spec.partition(":")
    if not attr_name:
        raise ValueError(f"catalog spec must be 'module:attr', got {spec!r}")
    module = importlib.import_module(module_name)
    target = getattr(module, attr_name)
    catalog = getattr(target, "_catalog", target)
    return list(catalog)


def audit_catalog(catalog: Iterable[Any], policy: dict[str, Any]) -> list[ToolAudit]:
    """Check every record in a loaded catalog against one oath policy."""
    audits = []
    for record in catalog:
        name, declared = _extract_declared(record)
        audits.append(ToolAudit(name=name, declared=declared, policy=policy))
    return audits


@dataclass
class BadgeState:
    color: str
    message: str
    tools_checked: int
    tools_clean: int
    violations: list[str] = field(default_factory=list)
    integrity_problems: list[str] = field(default_factory=list)
    generated_at: str = ""

    @property
    def ok(self) -> bool:
        return self.color == GREEN and not self.violations and not self.integrity_problems


def compute_badge_state(
    catalog: Iterable[Any],
    policy: dict[str, Any] | None = None,
    integrity_checks: Iterable[Callable[[], list[str]]] = (),
    label: str = "read-only",
    now: datetime | None = None,
) -> BadgeState:
    """Audit a catalog against a policy, plus any number of extra integrity
    checks (a ledger's hash chain, a config file's contents, anything a
    fork wants proven alongside the tool-scope oath). Each integrity check
    is a zero-arg callable returning a list of problem strings (empty =
    clean). Green requires the tool audit AND every integrity check clean.
    """
    now = now or datetime.now(timezone.utc)
    policy = dict(DEFAULT_POLICY) if policy is None else policy

    audits = audit_catalog(catalog, policy)
    tool_violations = [a.violation for a in audits if a.violation is not None]

    integrity_problems: list[str] = []
    for check in integrity_checks:
        integrity_problems.extend(check())

    violations = tool_violations
    tools_checked = len(audits)
    tools_clean = tools_checked - len(tool_violations)

    if violations or integrity_problems:
        color = RED
        n = len(violations) + len(integrity_problems)
        message = f"{n} violation{'s' if n != 1 else ''} found — see BADGE.json"
    else:
        color = GREEN
        message = f"{tools_clean}/{tools_checked} tools honor the oath · 0 violations"

    return BadgeState(
        color=color,
        message=message,
        tools_checked=tools_checked,
        tools_clean=tools_clean,
        violations=violations,
        integrity_problems=integrity_problems,
        generated_at=now.isoformat(),
    )


def render_badge_json(state: BadgeState, label: str = "read-only") -> str:
    """The shields.io endpoint-badge schema. Same contract as the Fencepost
    original: only the fields shields.io recognizes, nothing that would make
    the badge fail by rendering shields.io's OWN error badge instead of ours.
    """
    payload = {
        "schemaVersion": 1,
        "label": label,
        "message": state.message,
        "color": state.color,
        "isError": not state.ok,
    }
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


# --- CLI ----------------------------------------------------------------


class OathBadgeArgError(ValueError):
    """--policy parsed as valid JSON but not into a dict -- the same
    valid-JSON-wrong-shape crash class task 364 fixed for ritual_check.py's
    own CLI, here at oath_badge.py's own CLI (a list or bare scalar reaching
    `compute_badge_state`'s `ToolAudit.policy.items()` unguarded crashes
    with a bare AttributeError instead of naming the real problem)."""


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    if "--catalog" not in argv:
        print("usage: oath_badge.py --catalog module:attr [--policy path.json] "
              "[--label text] [--write path] [--out path]", file=sys.stderr)
        return 2

    def _take(flag: str) -> str | None:
        if flag not in argv:
            return None
        i = argv.index(flag)
        val = argv[i + 1]
        del argv[i : i + 2]
        return val

    catalog_spec = _take("--catalog")
    policy_path = _take("--policy")
    label = _take("--label") or "read-only"
    out_path = _take("--out")

    policy = DEFAULT_POLICY
    if policy_path:
        policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
        if not isinstance(policy, dict):
            raise OathBadgeArgError(
                f"--policy: expected a JSON dict, got {type(policy).__name__}"
            )
        if "operations" in policy:
            policy["operations"] = tuple(policy["operations"])

    catalog = load_catalog(catalog_spec)
    state = compute_badge_state(catalog, policy, label=label)
    rendered = render_badge_json(state, label=label)
    print(rendered)

    if state.violations or state.integrity_problems:
        print("VIOLATIONS (badge is RED):", file=sys.stderr)
        for v in [*state.violations, *state.integrity_problems]:
            print(f"  - {v}", file=sys.stderr)

    if out_path:
        Path(out_path).write_text(rendered, encoding="utf-8")
        print(f"\nWritten: {out_path}", file=sys.stderr)

    return 0 if state.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
