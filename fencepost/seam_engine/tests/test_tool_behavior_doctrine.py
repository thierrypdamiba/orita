"""Own-remit sweep, Read-Only Oath & Governance (task 1313, retrya).

Every prior sweep of this doctrine checked the DOCUMENTED claim: server.py's
own module docstring ("There is no write-capable tool in this file"), the
`@app.tool(metadata=READ_ONLY)` decorator's presence in the source text, and
README/BADGE.json's tool count against `app._catalog` (test_readme_tool_count.
py, test_badge.py). None of those ever asked the live Arcade MCP framework
object itself what it thinks each tool's behavior is -- they all stop at
"the decorator is written," never "the decorator's own effect held."

`arcade_mcp_server` attaches a real `ToolMetadata` (with a `Behavior`
sub-object: `read_only`, `destructive`, `operations`) to every tool in
`app._catalog` once registration runs -- this is what a host application
(or a future audit) actually reads at call time to decide whether a tool is
safe to invoke unattended, not the source file's own prose. A future tool
added to server.py with a copy-pasted decorator call that silently dropped
`metadata=READ_ONLY` (or passed a different, less strict `ToolMetadata`)
would still satisfy every existing check -- the module docstring wouldn't
change, the tool count would still match README's number, `test_gateway.py`
only ever inspects `READ_ONLY_CAPABILITIES` (a separate hand-written prose
string, not this per-tool object) -- and would only be caught by a human
rereading the diff.

This closes that gap: it reads `app._catalog` live, exactly as
`test_readme_tool_count.py` already does, and asserts every one of its
tools' `metadata.behavior` actually reads read-only and non-destructive,
with only READ among its operations. Verified failing first against a
locally patched sixth tool with `destructive=True` before writing the real
assertions, then reverted -- the check catches what it claims to catch.
"""
from __future__ import annotations

from arcade_mcp_server.metadata import Operation
from seam_engine.server import app


def _catalog_tools():
    return list(app._catalog)  # noqa: SLF001


def test_catalog_is_not_empty():
    # A vacuously-true sweep below (nothing to check) is worse than no
    # check at all -- fail loud if the catalog ever comes back empty.
    assert len(_catalog_tools()) >= 1


def test_every_registered_tool_is_read_only_and_non_destructive():
    offenders = []
    for mat_tool in _catalog_tools():
        name = mat_tool.definition.name
        metadata = mat_tool.definition.metadata
        behavior = metadata.behavior if metadata is not None else None
        if behavior is None:
            offenders.append(f"{name}: no metadata.behavior set at all")
            continue
        if behavior.read_only is not True:
            offenders.append(f"{name}: behavior.read_only={behavior.read_only!r}")
        if behavior.destructive is not False:
            offenders.append(f"{name}: behavior.destructive={behavior.destructive!r}")
    assert not offenders, (
        "Fencepost's own Read-Only Oath (SCOPES.md, server.py's module "
        "docstring) is violated at the live framework level for: "
        + "; ".join(offenders)
    )


def test_every_registered_tool_declares_only_read_operations():
    offenders = []
    for mat_tool in _catalog_tools():
        name = mat_tool.definition.name
        metadata = mat_tool.definition.metadata
        behavior = metadata.behavior if metadata is not None else None
        ops = list(behavior.operations) if behavior is not None else []
        if ops != [Operation.READ]:
            offenders.append(f"{name}: operations={ops!r}")
    assert not offenders, (
        "a Fencepost tool declares a non-READ operation at the live "
        f"framework level: {'; '.join(offenders)}"
    )
