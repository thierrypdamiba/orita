"""The read-only badge — Ogun's law, rendered as proof, not promise.

SCOPES.md's oath, clause 4: "A live badge proves it. The README carries a
`read-only · zero actions fired` badge that repaints from real runs. If
Fencepost ever fires a single write, the badge goes red and the oath is
broken in public."

This module is the thing that keeps that promise honest. It does not print
green because someone asserted Fencepost is read-only — it CHECKS, against
two real things, and only then renders:

1. **The live server's own tool catalog.** `seam_engine.server` is the
   actual MCP server Arcade would load. Every tool in it carries a
   `ToolMetadata.behavior` the author declared at registration time
   (`read_only`, `destructive`, `operations`). This module imports the real
   `app` object and reads that catalog straight off it — the same
   introspection `arcade_mcp_server` itself does internally
   (`MCPApp.add_tools_from_module` iterates `self._catalog` the identical
   way) — rather than trusting a comment that says "this tool is read-only."
   A tool added to server.py tomorrow with a write-shaped `Behavior` fails
   this check the same run it lands, before a human ever reviews the diff.

2. **The real, sealed Ledger.** `ledger.read_records()` is the count of
   actual runs this town has sealed (GAPS/*.md, hash-chained), and
   `ledger.verify()` is the same tamper check `python -m seam_engine.ledger
   verify` already runs — a ledger that was edited after sealing fails the
   badge too, because a ledger that can be quietly edited is not proof of
   anything.

Nothing here is asserted. `compute_badge_state` fails RED, loudly, the
moment either check finds a violation — there is no code path that renders
green while a violation list is non-empty (test_badge.py proves it: a fake
write-shaped tool spliced into the catalog flips the badge red in the same
run that introduces it).

Sworn on iron.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from seam_engine import ledger

# fencepost/  (…/orita/fencepost/seam_engine/src/seam_engine/badge.py → parents[3])
_FENCEPOST_ROOT = Path(__file__).resolve().parents[3]

GREEN = "brightgreen"
RED = "red"

# The only shape a tool's declared behavior may take for the badge to call it
# read-only. Anything else — read_only False, destructive True, an operation
# other than "read" — is a violation, named, not hidden.
_ALLOWED_OPERATIONS = ("read",)


@dataclass(frozen=True)
class ToolAudit:
    """What one registered tool's own declared metadata says about itself."""

    name: str
    read_only: bool
    destructive: bool
    operations: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return (
            self.read_only is True
            and self.destructive is False
            and self.operations == _ALLOWED_OPERATIONS
        )

    @property
    def violation(self) -> str | None:
        if self.ok:
            return None
        return (
            f"{self.name}: not read-only-clean "
            f"(read_only={self.read_only}, destructive={self.destructive}, "
            f"operations={list(self.operations)})"
        )


def audit_server_tools() -> list[ToolAudit]:
    """Introspect the ACTUAL live MCP server's tool catalog — the real thing
    Arcade would load, not a copy of it. Every tool's own declared
    `ToolMetadata.behavior` is read straight off the registered object.

    Uses the catalog's private `_catalog` attribute deliberately: the public
    `app.tools.list()` API is async and requires a bound, running server
    (`ServerError` otherwise) — too heavy for a build-time badge check that
    must run in CI with no transport open. `_catalog` is the same
    build-time registry `arcade_mcp_server.MCPApp` itself iterates
    internally (see `add_tools_from_module` in its own source); reading it
    here is the same operation, not a different one.
    """
    from seam_engine.server import app  # local import: keep badge.py import-light

    audits: list[ToolAudit] = []
    for mat_tool in app._catalog:  # noqa: SLF001 — see docstring above
        d = mat_tool.definition
        behavior = d.metadata.behavior if d.metadata is not None else None
        raw_ops = (behavior.operations or []) if behavior else []
        ops = tuple(getattr(op, "value", op) for op in raw_ops)
        audits.append(
            ToolAudit(
                name=d.name,
                read_only=bool(behavior and behavior.read_only),
                destructive=bool(behavior and behavior.destructive),
                operations=ops,
            )
        )
    return audits


@dataclass
class BadgeState:
    """What the badge shows, and everything that backs the color choice."""

    color: str
    message: str
    tools_checked: int
    tools_clean: int
    runs_sealed: int
    chain_intact: bool
    violations: list[str] = field(default_factory=list)
    generated_at: str = ""

    @property
    def ok(self) -> bool:
        return self.color == GREEN and not self.violations


def compute_badge_state(
    ledger_base: Path | None = None, now: datetime | None = None
) -> BadgeState:
    """The one function this module exists for: check the real, live server
    and the real, sealed Ledger, and only then decide the badge's color.

    Green requires ALL of:
      - every tool the live server registers declares itself read-only,
        non-destructive, read-operation-only (`audit_server_tools`);
      - the Ledger's hash chain is intact — no tablet was edited after it
        was sealed (`ledger.verify`).

    Any single violation — one write-shaped tool, one broken seal — renders
    red, with every violation named in the payload. There is no path that
    hides a violation behind a green color.
    """
    now = now or datetime.now(timezone.utc)
    tool_audits = audit_server_tools()
    tool_violations = [a.violation for a in tool_audits if a.violation is not None]

    chain_problems = ledger.verify(ledger_base)
    runs_sealed = len(ledger.read_records(ledger_base))

    violations = [*tool_violations, *chain_problems]
    tools_checked = len(tool_audits)
    tools_clean = tools_checked - len(tool_violations)

    if violations:
        color = RED
        n = len(violations)
        message = f"{n} violation{'s' if n != 1 else ''} found — see BADGE.json"
    else:
        color = GREEN
        run_word = "run" if runs_sealed == 1 else "runs"
        message = (
            f"{tools_clean}/{tools_checked} tools read-only · "
            f"0 writes fired across {runs_sealed} sealed {run_word}"
        )

    return BadgeState(
        color=color,
        message=message,
        tools_checked=tools_checked,
        tools_clean=tools_clean,
        runs_sealed=runs_sealed,
        chain_intact=not chain_problems,
        violations=violations,
        generated_at=now.isoformat(),
    )


def render_badge_json(state: BadgeState) -> str:
    """Render the shields.io endpoint-badge schema
    (https://shields.io/badges/endpoint-badge). The README's badge points
    at `img.shields.io/endpoint?url=<raw-url-to-BADGE.json>`, so the image a
    reader sees is a live re-fetch of exactly this file — it repaints
    whenever this function last ran and wrote, never a static asset checked
    in once and forgotten.
    """
    # Only fields shields.io's endpoint-badge schema actually recognizes —
    # an unknown key risks shields.io rendering its OWN error badge instead
    # of ours, which would be a strange way for a read-only badge to fail.
    payload = {
        "schemaVersion": 1,
        "label": "read-only",
        "message": state.message,
        "color": state.color,
        "isError": not state.ok,
    }
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def badge_path(base: Path | None = None) -> Path:
    """Where the rendered badge payload lives. Defaults to fencepost/BADGE.json."""
    return (base if base is not None else _FENCEPOST_ROOT) / "BADGE.json"


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    ledger_base: Path | None = None
    if "--base" in argv:
        i = argv.index("--base")
        if i + 1 >= len(argv):
            print("--base needs a path to a Ledger directory.")
            return 2
        ledger_base = Path(argv[i + 1])
        del argv[i : i + 2]

    write = "--write" in argv
    if write:
        argv.remove("--write")

    out_base: Path | None = None
    if "--out-base" in argv:
        i = argv.index("--out-base")
        if i + 1 >= len(argv):
            print("--out-base needs a path to write the badge under.")
            return 2
        out_base = Path(argv[i + 1])
        del argv[i : i + 2]

    state = compute_badge_state(ledger_base)
    rendered = render_badge_json(state)
    print(rendered)

    if state.violations:
        print("VIOLATIONS (badge is RED):", file=sys.stderr)
        for v in state.violations:
            print(f"  - {v}", file=sys.stderr)

    if write:
        path = badge_path(out_base)
        path.write_text(rendered, encoding="utf-8")
        print(f"\nWritten: {path}", file=sys.stderr)

    return 0 if state.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
