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

from seam_engine.combined_scan import run_combined_scan
from seam_engine.gmail_calendar import run_gmail_calendar_scan
from seam_engine.ranking import rank
from seam_engine.scan import (
    XPost,
    _effective_since,
    coincidence_candidates,
    compute_candidates,
    fetch_github_activity,
    fetch_latest_release,
    load_github_events_from_live,
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
    """Read-only: fetch the latest release of a public GitHub repo.

    ROADMAP.md #157: used to call `fetch_github_activity(owner, repo,
    EPOCH)` and filter for `kind == "release"` — after task 154 turned
    commit fetching into a real paginating loop, that epoch `since` forced
    a full-history commit pagination before ever reaching the release call,
    wasteful at best and (past `_MAX_COMMIT_PAGES * 100` commits) a live
    `RuntimeError` at worst, for a question that only ever needed one
    request. `fetch_latest_release` asks it directly.
    """
    event = fetch_latest_release(owner, repo)
    return asdict(event) if event is not None else None


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
    github_events_json: Annotated[
        str | None,
        "Optional JSON array of your own already-fetched, normalized GitHub "
        "events ([{\"kind\":..,\"id\":..,\"title\":..,\"url\":..,\"ts\":..,"
        "\"author\":..}, ...] — call your gateway's GitHub read yourself "
        "first, per scan.py's load_github_events_from_live). Omit to fetch "
        "directly from api.github.com, unchanged from v0 — but that direct "
        "fetch fails with an UpstreamError in any sandbox whose egress to "
        "GitHub is blocked, which is exactly when this override exists. "
        "An empty array is rejected — see load_github_events_from_live's "
        "docstring.",
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
    events = (
        fetch_github_activity(owner, repo, since)
        if github_events_json is None
        else load_github_events_from_live(json.loads(github_events_json))
    )
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
        "github_events_source": "direct" if github_events_json is None else "override",
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


@app.tool(metadata=READ_ONLY)
def combined_scan_preview(
    owner: Annotated[str, "GitHub owner (user or org)"] = "thierrypdamiba",
    repo: Annotated[str, "GitHub repository name"] = "orita",
    window_hours: Annotated[int, "How far back to look for GitHub activity"] = 24,
    x_posts_json: Annotated[
        str | None,
        "Optional JSON array of your own already-fetched, normalized X posts, "
        "same shape and same ledger fallback as seam_scan's x_posts_json.",
    ] = None,
    github_events_json: Annotated[
        str | None,
        "Optional JSON array of your own already-fetched, normalized GitHub "
        "events, same shape and same direct-fetch fallback as seam_scan's "
        "github_events_json.",
    ] = None,
) -> Annotated[
    dict,
    "WIP (ROADMAP.md #113): scan.py's own candidates pooled with every "
    "discovered RECIPES/ manifest's, ranked once. Every recipe today reads "
    "a fixture (MOCK ONLY) — this preview can surface a recipe's fixture "
    "candidate as primary, which would misdescribe the town's live accounts "
    "if mistaken for seam_scan's real daily report.",
]:
    """Read-only preview of `combined_scan.run_combined_scan` (ROADMAP.md
    #111): the same GitHub-vs-X candidates `seam_scan` computes, plus every
    community recipe's own candidates from `RECIPES/`, pooled and ranked
    together exactly once — a recipe's candidate can genuinely out-rank or
    lose to a god's.

    NOT what `seam-scan.yml`'s daily report runs, and this tool does not
    change that: every recipe merged so far reads a `fixture` under
    `RECIPES/<slug>/fixtures/` (the MOCK ONLY oath, `CONTRIBUTING.md`), so a
    recipe's candidate here can be stale or synthetic in a way `seam_scan`'s
    own GitHub-vs-X candidates never are. This tool exists so the real,
    tested `combined_scan.py` machinery is reachable from the live agent
    surface at all (previously CLI-only, `python -m seam_engine.
    combined_scan`) — not to make it the report. `combined_scan.py` goes
    live in `seam-scan.yml` the same day a recipe's own fixture/scopes
    graduate to a live read, unchanged from task 111's boundary."""
    x_posts = None if x_posts_json is None else json.loads(x_posts_json)
    github_events = None if github_events_json is None else json.loads(github_events_json)
    return run_combined_scan(
        owner, repo, window_hours=window_hours, x_posts=x_posts, github_events=github_events,
    )


# Run with specific transport
if __name__ == "__main__":
    # "stdio" (default): Claude Desktop, CLI tools, etc.
    # "http": Cursor, VS Code, etc. (does not support requires_auth/requires_secrets
    #   tools unless deployed via 'arcade deploy')
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
