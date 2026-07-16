#!/usr/bin/env python3
"""seam_engine — Fencepost's read-only reconciliation core.

Every tool here is Get/List-only, per fencepost/SCOPES.md. There is no
write-capable tool in this file, on purpose: if a tool can change the
world, it does not belong in this server (Ogun's oath, sworn on iron).
"""

import json
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

from seam_engine.gmail_calendar import run_gmail_calendar_scan
from seam_engine.ranking import rank
from seam_engine.scan import (
    XPost,
    _effective_since,
    coincidence_candidates,
    compute_candidates,
    fetch_github_activity,
    load_x_posts_from_ledger,
    load_x_posts_from_live,
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

    v0 reads the public HAND/mortal-sky-log.md record. To hand `seam_scan`
    (below) a live read instead, call your own gateway's X.GetUserTweets
    directly, normalize each tweet to `{"id", "text", "url", "ts"}`, and pass
    the list as `seam_scan`'s `x_posts_json` argument — this tool itself
    stays the ledger-only read it has always been (ROADMAP.md #94: this
    server dispatches only to tools already registered on itself, never to a
    connected user's own external toolkit tools, so it cannot call
    GetUserTweets on your behalf; your MCP client does that part).
    """
    posts: list[XPost] = load_x_posts_from_ledger()
    return [asdict(p) for p in posts]


@app.tool(metadata=READ_ONLY)
def seam_scan(
    owner: Annotated[str, "GitHub owner (user or org)"] = "thierrypdamiba",
    repo: Annotated[str, "GitHub repository name"] = "orita",
    window_hours: Annotated[int, "How far back to look for GitHub activity"] = 24,
    x_posts_json: Annotated[
        str | None,
        "Optional JSON array of your own already-fetched, normalized X posts "
        "([{\"id\":..,\"text\":..,\"url\":..,\"ts\":..}, ...] — call your "
        "gateway's X.GetUserTweets yourself first, per CONNECT.md). Omit to "
        "use the HAND/mortal-sky-log.md ledger fallback, unchanged from v0. "
        "An empty array is rejected — see load_x_posts_from_live's docstring.",
    ] = None,
) -> Annotated[dict, "The ranked seam scan: one labeled primary gap, a confidence-scored tail, and excluded false positives"]:
    """Read-only seam-scan v0: reconcile @oritatown's X posts against GitHub
    commits/releases and surface the single highest-confidence gap between
    them, labeled and cleared over the confidence bar, plus a confidence-scored
    tail of coincidences. Fixes nothing; writes only the scan result."""
    x_posts = (
        load_x_posts_from_ledger()
        if x_posts_json is None
        else load_x_posts_from_live(json.loads(x_posts_json))
    )
    account_live_since = min((p.ts for p in x_posts), default=datetime.now(timezone.utc))
    now = datetime.now(timezone.utc)
    # Reaches back at least to account_live_since, not just window_hours —
    # same recurring-gap machinery as scan.run_scan (ROADMAP.md #19), so the
    # live MCP tool and the daily Action never disagree about how far a
    # still-unannounced gap can recur before it silently ages out of view.
    since = _effective_since(now, window_hours, account_live_since)
    events = fetch_github_activity(owner, repo, since)
    surfaced, excluded = compute_candidates(events, x_posts, account_live_since)
    coincidences = coincidence_candidates(events, x_posts, account_live_since)
    ranking = rank(surfaced + coincidences)
    primary = ranking.primary
    return {
        "generated_at": now.isoformat(),
        "repo": f"{owner}/{repo}",
        "window_hours": window_hours,
        "account_live_since": account_live_since.isoformat(),
        "x_posts_source": "ledger" if x_posts_json is None else "live",
        "confidence_bar": ranking.confidence_bar,
        "separation_margin": ranking.separation_margin,
        "primary_gap": asdict(primary) if primary else None,
        "tail": [asdict(g) for g in ranking.tail],
        "excluded": [asdict(g) for g in excluded],
    }


@app.tool(metadata=READ_ONLY)
def gmail_calendar_scan() -> Annotated[
    dict,
    "WIP (ROADMAP.md #16): the v0.2 invite-in-Gmail-vs-Calendar gap, computed "
    "against a fixture — the-hand gateway does not yet hold read-only Gmail/"
    "Calendar scopes and no demo Gmail/Calendar account is connected.",
]:
    """Read-only, fixture-backed v0.2 detector: the calendar invite still
    sitting in Gmail that never made it onto the Calendar.

    Runs entirely against fencepost/fixtures/gmail_calendar/ — no live Gmail
    or Calendar scope exists on the-hand gateway yet, so this cannot read a
    real inbox. Result carries "source": "fixture" so a caller can never
    mistake it for a live read. Once the Hand extends the-hand gateway with
    read-only Gmail (ListEmails/SearchThreads) + Calendar (ListEvents) and
    connects a dedicated demo account, this tool's body swaps the fixture
    loaders for those calls; the detection logic in gmail_calendar.py does
    not change."""
    return run_gmail_calendar_scan()


# Run with specific transport
if __name__ == "__main__":
    # "stdio" (default): Claude Desktop, CLI tools, etc.
    # "http": Cursor, VS Code, etc. (does not support requires_auth/requires_secrets
    #   tools unless deployed via 'arcade deploy')
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
