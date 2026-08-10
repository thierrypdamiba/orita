#!/usr/bin/env python3
"""oracle_engine — the Oracle Desk's MCP server (demo #2's engine).

Every tool here is Get/List/Search-only, per oracle/SCOPES.md. There is no
tool anywhere in this file that can move money, place a trade, execute an
instruction, or write to any account but the town's own sealed ledger — if
a tool can touch a mortal's funds, it does not belong in this server
(Ogun's oath, extended from Fencepost's SCOPES.md, sworn on iron).

`arcade new` scaffolds this file with two example tools that do not belong
here and were removed on sight before the first commit: `star_repo` (a
write-capable GitHub tool — the exact shape this server's oath forbids) and
`whisper_secret` (an unrelated secrets demo). Nothing of either survives
past this scaffold.
"""

import sys
from typing import Annotated, Literal

from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.metadata import (
    Behavior,
    Classification,
    Operation,
    ServiceDomain,
    ToolMetadata,
)

app = MCPApp(name="oracle_engine", version="0.1.0", log_level="DEBUG")

TransportArg = Literal["http", "stdio"]
_VALID_TRANSPORTS: tuple[TransportArg, ...] = ("http", "stdio")

READ_ONLY = ToolMetadata(
    classification=Classification(service_domains=[ServiceDomain.FINANCIAL_DATA]),
    behavior=Behavior(
        operations=[Operation.READ],
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=True,
    ),
)


# `# type: ignore[untyped-decorator, arg-type]` below: a real gap in the
# vendor, not oracle_engine (confirmed live, ported from fencepost/seam_engine's
# identical note, task 658). `MCPApp.tool()` (arcade_mcp_server/mcp_app.py) is
# a single, non-`@overload`ed method whose return annotation is the union
# `Callable[[Callable[P, T]], Callable[P, T]] | Callable[P, T]` -- correct at
# runtime (it branches on whether `func` was passed) but mypy --strict has no
# way to know, from a kwargs-only call site like `@app.tool(metadata=...)`,
# which arm of the union applies, so it falls back to treating the decorator
# as untyped and the two derived arg-type mismatches that follow from that.
# No PyPI `types-arcade-mcp-server` stub package exists to fix this without
# touching the vendor (checked live). Ignoring these two specific codes only
# -- anything else mypy --strict finds on this line still fails the build.
@app.tool(metadata=READ_ONLY)  # type: ignore[untyped-decorator, arg-type]
def whoami(context: Context) -> Annotated[str, "The Oracle Desk's own identity string"]:
    """Read-only: confirm this server is the Oracle Desk engine, and nothing else.

    Placeholder for task 30 (scaffold + oath). The real read/search tools —
    predictions sealed to the ledger (task 31), grading (task 32) — land in
    the tasks that follow; this tool exists only so the scaffold has one
    real, oath-compliant, badge-checkable tool from its first commit rather
    than shipping empty.
    """
    return "oracle_engine v0.1.0 — read-only, no trade/wallet/instruction-capable tool in this config"


def _resolve_transport(argv: list[str]) -> TransportArg:
    """Validate the CLI transport argument before app.run() ever starts.

    Ported verbatim from `fencepost/seam_engine/src/seam_engine/server.py`'s
    own `_resolve_transport` (task 647): without this, an unrecognized value
    reaches `arcade_mcp_server.MCPApp.run()` only after it has already
    registered every tool and started logging -- the `ServerError` it raises
    then is real but buried under startup noise. Failing here keeps the CLI
    usage error the first and only thing printed, and narrows the return
    type to what `app.run()`'s own `transport` parameter expects instead of
    a bare `str` (mypy --strict caught the untyped mismatch, task 659).
    """
    transport = argv[1] if len(argv) > 1 else "stdio"
    if transport not in _VALID_TRANSPORTS:
        sys.exit(
            f"oracle_engine.server: invalid transport {transport!r} "
            f"(expected one of {', '.join(_VALID_TRANSPORTS)})"
        )
    return transport


# Run with specific transport
if __name__ == "__main__":
    # "stdio" (default): Standard I/O for Claude Desktop, CLI tools, etc.
    #   Supports tools that require_auth or require_secrets out-of-the-box
    # "http": HTTPS streaming for Cursor, VS Code, etc.
    #   Does not support tools that require_auth or require_secrets unless the server is deployed
    #   using 'arcade deploy' or added in the Arcade Developer Dashboard with 'Arcade' server type
    app.run(transport=_resolve_transport(sys.argv), host="127.0.0.1", port=8000)
