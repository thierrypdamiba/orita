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
from typing import Annotated

from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.metadata import (
    Behavior,
    Classification,
    Operation,
    ServiceDomain,
    ToolMetadata,
)

app = MCPApp(name="oracle_engine", version="0.1.0", log_level="DEBUG")

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


@app.tool(metadata=READ_ONLY)
def whoami(context: Context) -> Annotated[str, "The Oracle Desk's own identity string"]:
    """Read-only: confirm this server is the Oracle Desk engine, and nothing else.

    Placeholder for task 30 (scaffold + oath). The real read/search tools —
    predictions sealed to the ledger (task 31), grading (task 32) — land in
    the tasks that follow; this tool exists only so the scaffold has one
    real, oath-compliant, badge-checkable tool from its first commit rather
    than shipping empty.
    """
    return "oracle_engine v0.1.0 — read-only, no trade/wallet/instruction-capable tool in this config"


# Run with specific transport
if __name__ == "__main__":
    # Get transport from command line argument, default to "stdio"
    # - "stdio" (default): Standard I/O for Claude Desktop, CLI tools, etc.
    #   Supports tools that require_auth or require_secrets out-of-the-box
    # - "http": HTTPS streaming for Cursor, VS Code, etc.
    #   Does not support tools that require_auth or require_secrets unless the server is deployed
    #   using 'arcade deploy' or added in the Arcade Developer Dashboard with 'Arcade' server type
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    # Run the server
    app.run(transport=transport, host="127.0.0.1", port=8000)
