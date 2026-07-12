#!/usr/bin/env python3
"""seam_engine — Fencepost's read-only reconciliation core.

Every tool here is Get/List-only, per fencepost/SCOPES.md. There is no
write-capable tool in this file, on purpose: if a tool can change the
world, it does not belong in this server (Ogun's oath, sworn on iron).
"""

import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Annotated

from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.metadata import (
    Behavior,
    Classification,
    Operation,
    ServiceDomain,
    ToolMetadata,
)

from seam_engine.ranking import rank
from seam_engine.scan import (
    XPost,
    coincidence_candidates,
    compute_candidates,
    fetch_github_activity,
    load_x_posts_from_ledger,
)

app = MCPApp(name="seam_engine", version="0.1.0", log_level="DEBUG")

READ_ONLY = ToolMetadata(
    classification=Classification(service_domains=[ServiceDomain.SOURCE_CODE]),
    behavior=Behavior(
        operations=[Operation.READ],
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=True,
    ),
)


@app.tool(metadata=READ_ONLY)
def list_repo_commits(
    owner: Annotated[str, "GitHub owner (user or org), e.g. 'thierrypdamiba'"],
    repo: Annotated[str, "GitHub repository name, e.g. 'orita'"],
    since_hours: Annotated[int, "Only commits in the last N hours"] = 24,
) -> Annotated[list[dict], "Commits since the window start, newest first"]:
    """Read-only: list recent commits on a public GitHub repo's default branch."""
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    events = fetch_github_activity(owner, repo, since)
    return [asdict(e) for e in events if e.kind == "commit"]


@app.tool(metadata=READ_ONLY)
def get_latest_release(
    owner: Annotated[str, "GitHub owner (user or org)"],
    repo: Annotated[str, "GitHub repository name"],
) -> Annotated[dict | None, "The latest release, or null if none exists"]:
    """Read-only: fetch the latest release of a public GitHub repo."""
    events = fetch_github_activity(owner, repo, datetime(1970, 1, 1, tzinfo=timezone.utc))
    releases = [e for e in events if e.kind == "release"]
    return asdict(releases[0]) if releases else None


@app.tool(metadata=READ_ONLY)
def get_recent_x_posts(
    context: Context,
) -> Annotated[list[dict], "Posts the town has made to @oritatown, oldest first"]:
    """Read-only: the town's own posted X history.

    v0 reads the public HAND/mortal-sky-log.md record. A future version
    calls Arcade's read-only X toolkit (GetUserTweets) directly through the
    per-user OAuth-connected gateway once a live session is attached.
    """
    posts: list[XPost] = load_x_posts_from_ledger()
    return [asdict(p) for p in posts]


@app.tool(metadata=READ_ONLY)
def seam_scan(
    owner: Annotated[str, "GitHub owner (user or org)"] = "thierrypdamiba",
    repo: Annotated[str, "GitHub repository name"] = "orita",
    window_hours: Annotated[int, "How far back to look for GitHub activity"] = 24,
) -> Annotated[dict, "The ranked seam scan: one labeled primary gap, a confidence-scored tail, and excluded false positives"]:
    """Read-only seam-scan v0: reconcile @oritatown's X posts against GitHub
    commits/releases and surface the single highest-confidence gap between
    them, labeled and cleared over the confidence bar, plus a confidence-scored
    tail of coincidences. Fixes nothing; writes only the scan result."""
    x_posts = load_x_posts_from_ledger()
    account_live_since = min((p.ts for p in x_posts), default=datetime.now(timezone.utc))
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    events = fetch_github_activity(owner, repo, since)
    surfaced, excluded = compute_candidates(events, x_posts, account_live_since)
    coincidences = coincidence_candidates(events, x_posts, account_live_since)
    ranking = rank(surfaced + coincidences)
    primary = ranking.primary
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": f"{owner}/{repo}",
        "window_hours": window_hours,
        "account_live_since": account_live_since.isoformat(),
        "confidence_bar": ranking.confidence_bar,
        "separation_margin": ranking.separation_margin,
        "primary_gap": asdict(primary) if primary else None,
        "tail": [asdict(g) for g in ranking.tail],
        "excluded": [asdict(g) for g in excluded],
    }


# Run with specific transport
if __name__ == "__main__":
    # "stdio" (default): Claude Desktop, CLI tools, etc.
    # "http": Cursor, VS Code, etc. (does not support requires_auth/requires_secrets
    #   tools unless deployed via 'arcade deploy')
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
