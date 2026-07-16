"""Seam-scan v0: reconcile @oritatown's X posts against thierrypdamiba/orita's
GitHub activity (commits, issues, releases) and surface candidate gaps —
things that shipped on one side of the seam and were never mentioned on the
other.

Read-only. This module only ever GETs. It writes nothing back to GitHub or X;
the only write is the local ranked candidate-gap file this scan produces.

Data sources:
- GitHub: the public REST API (unauthenticated reads of a public repo — no
  scope beyond List/Get). In a real deployment this is the same call Arcade's
  GitHub read-only toolkit makes (ListRepoCommits, ListIssues, GetLatestRelease).
- X: in production this is Arcade's read-only X toolkit (GetUserTweets), which
  requires an OAuth-connected account. `run_scan`'s default (`x_posts=None`)
  still falls back to the town's own public record of what it posted —
  HAND/mortal-sky-log.md — which is itself sourced from real tweet URLs. That
  fallback is used only because no gateway session is attached by default; it
  is not a substitute for the live read scope once one is wired up.

  ROADMAP.md #94: `load_x_posts_from_live` + `run_scan(..., x_posts=...)` are
  the wired-up path this module's own docstring and `server.py`'s
  `get_recent_x_posts` promised as "a future version" since task 3 shipped.
  A caller already holding a live, per-user OAuth-connected X read (this
  session's `X_GetUserTweets` via the-hand; a self-hosted fork's own gateway
  session per CONNECT.md) normalizes that read to the same `id`/`text`/`url`/
  `ts` shape `XPost` already uses and hands it in — `scan.py` itself never
  holds or calls an Arcade client directly. That boundary is deliberate, not
  an oversight: `arcade_mcp_server.Context.tools.call_raw` (the seam engine's
  own MCP server, `server.py`) only dispatches to tools already registered on
  THIS server (`list_repo_commits`, `seam_scan`, etc.), never to a connected
  user's own external toolkit tools like X's `GetUserTweets` — bridging to a
  live per-user Arcade session is the connecting client's job, same as every
  other tool call in `CONNECT.md`'s walkthrough, not something this module
  can fabricate from inside a headless scan. An empty live override is
  refused rather than silently accepted (see `load_x_posts_from_live`): this
  account has genuinely posted before (@oritatown, 28 tweets per `X.WhoAmI`),
  so an empty result almost always means the read failed or was blocked —
  not that the account has posted nothing, ever — and treating it as "zero
  posts, ever" would flag every past commit as newly unannounced, exactly
  the false-positive flood Ogun's law exists to prevent.

Recurring, on purpose (ROADMAP.md #19): `_effective_since` makes `run_scan`
always reach back at least to `account_live_since`, never merely the last
`window_hours`. A milestone commit stays a live candidate for as long as it
remains genuinely unannounced — the daily cadence does not depend on
something milestone-worthy happening to land inside a rolling window; it
depends only on whether the town has actually announced its own work yet.
That is the machinery, not a promise: some days still clear no gap, honestly
(report.py's own quiet-day branch), because Ogun's law forbids inventing one.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from seam_engine.github_auth import github_headers

GITHUB_API = "https://api.github.com"
REPO_ROOT = Path(__file__).resolve().parents[4]  # .../orita
MORTAL_SKY_LOG = REPO_ROOT / "HAND" / "mortal-sky-log.md"

# Words too generic to count as topic overlap between a commit/issue title and a tweet.
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "it", "its",
    "for", "with", "at", "by", "this", "that", "as", "be", "are", "was",
}


@dataclass
class GithubEvent:
    kind: str  # "release" | "commit"
    id: str
    title: str
    url: str
    ts: datetime
    author: str


@dataclass
class XPost:
    id: str
    text: str
    url: str
    ts: datetime


@dataclass
class GapCandidate:
    slug: str
    headline: str
    detail: str
    confidence: float
    evidence: list[str] = field(default_factory=list)


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fetch_github_activity(owner: str, repo: str, since: datetime) -> list[GithubEvent]:
    """Read-only: commits + the latest release, since `since`. GET only."""
    events: list[GithubEvent] = []
    headers = github_headers()

    with httpx.Client(timeout=15.0, headers=headers) as client:
        commits = client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/commits",
            params={"since": since.isoformat(), "per_page": 100},
        )
        commits.raise_for_status()
        for c in commits.json():
            events.append(GithubEvent(
                kind="commit",
                id=c["sha"][:7],
                title=c["commit"]["message"].splitlines()[0],
                url=c["html_url"],
                ts=_parse_ts(c["commit"]["author"]["date"]),
                author=c["commit"]["author"]["name"],
            ))

        release = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest")
        if release.status_code == 200:
            r = release.json()
            ts = _parse_ts(r["published_at"])
            if ts >= since:
                events.append(GithubEvent(
                    kind="release", id=r["tag_name"], title=r["name"] or r["tag_name"],
                    url=r["html_url"], ts=ts, author=r.get("author", {}).get("login", "unknown"),
                ))

    return events


_TWEET_LINE = re.compile(
    r"\*\*(?P<author>[^*]+)\*\*.*?(?P<url>https://x\.com/\S+)"
)


def load_x_posts_from_ledger(path: Path = MORTAL_SKY_LOG) -> list[XPost]:
    """Read-only: parse the town's own public log of what it posted to X.

    Fallback data source for this scan (see module docstring) — used because
    this headless run has no live Arcade X OAuth session attached. The URLs
    and dates here are real; only the retrieval path is local-file instead of
    a live GetUserTweets call.
    """
    if not path.exists():
        return []
    text = path.read_text()
    posts: list[XPost] = []
    current_date = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+.*?—\s*(\d{4}-\d{2}-\d{2})", line)
        if heading:
            current_date = heading.group(1)
            continue
        m = _TWEET_LINE.search(line)
        if m and current_date:
            posts.append(XPost(
                id=m.group("url").rsplit("/", 1)[-1],
                text=line,
                url=m.group("url"),
                ts=_parse_ts(f"{current_date}T00:00:00+00:00"),
            ))
    return posts


_REQUIRED_LIVE_POST_KEYS = ("id", "text", "url", "ts")


def load_x_posts_from_live(data: list[dict[str, Any]]) -> list[XPost]:
    """Parse a caller-normalized live X read into the same `XPost` shape
    `load_x_posts_from_ledger` already produces.

    This is deliberately NOT a parser for X's/Arcade's own raw `GetUserTweets`
    response — the caller (whoever holds the live, per-user OAuth-connected
    session: this session's `X_GetUserTweets` via the-hand, or a self-hosted
    fork's own gateway per CONNECT.md) normalizes each tweet to the same four
    fields `XPost` already carries (`id`, `text`, `url`, `ts`, ISO-8601) before
    handing it in — the identical "pre-fetched live data, already shaped,
    handed in as JSON" convention `tools/ritual_check.py`'s `--square-state`/
    `--ci-checks`/`--cron-checks` already established for this town's own
    hourly ritual (tasks 73/82). Rejects two shapes, both on purpose:

    - A malformed entry (missing one of the four required keys) raises
      `ValueError` naming the missing key and the entry's index — never
      silently dropped, per Ogun's precision-over-recall law.
    - An EMPTY list raises `ValueError` rather than being accepted as "this
      account has posted nothing, ever." @oritatown has posted before (28
      tweets per `X.WhoAmI`, confirmed live 2026-07-16) — an empty live
      result is far more likely to mean the read failed or was blocked (the
      account's `X_GetUserTweets` outage this town has tracked since
      2026-07-14 returns exactly this shape: `{"data": [], "errors": [...]}`)
      than that the account's history is genuinely empty. Silently treating
      it as "zero posts, ever" would flag every past commit as newly
      unannounced — the exact false-positive flood Ogun's law forbids. Pass
      `x_posts=None` to `run_scan` (the default) to use the local ledger
      fallback instead of an empty live override.
    """
    if not data:
        raise ValueError(
            "load_x_posts_from_live() received an empty list — refusing to treat "
            "that as \"this account has posted nothing, ever\" (it has: 28 tweets "
            "per X.WhoAmI). An empty live read almost always means the call failed "
            "or was blocked; pass x_posts=None to run_scan to use the local ledger "
            "fallback instead of an empty override."
        )
    posts: list[XPost] = []
    for i, entry in enumerate(data):
        missing = [k for k in _REQUIRED_LIVE_POST_KEYS if k not in entry]
        if missing:
            raise ValueError(
                f"load_x_posts_from_live(): entry {i} is missing required key(s) "
                f"{missing} (expected id/text/url/ts on every normalized post): {entry!r}"
            )
        posts.append(XPost(
            id=str(entry["id"]),
            text=str(entry["text"]),
            url=str(entry["url"]),
            ts=_parse_ts(entry["ts"]) if isinstance(entry["ts"], str) else entry["ts"],
        ))
    return posts


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


# v0 deliberately only watches for ONE kind of commit-side gap: milestone-level
# work (a flagship pivot, a strategy decision) going unannounced. Not every commit
# is meant to reach X — most are routine bookkeeping, night-voice lore, or small
# fixes nobody would expect a tweet about. Flagging those would be exactly the
# false positive Ogun's law forbids. Matching on a narrow, curated keyword set
# instead of "any commit topic" keeps precision high at the cost of recall,
# which is the right trade for a v0 whose whole job is not crying wolf.
MILESTONE_KEYWORDS = {"flagship", "fencepost", "strategy"}
QUIET_VOICE_AUTHORS = {"nyx", "zashiki-warashi"}  # night-window lore; not announcement material


def _is_milestone(event: GithubEvent) -> bool:
    if event.author.lower() in QUIET_VOICE_AUTHORS:
        return False
    title = event.title.lower()
    return any(k in title for k in MILESTONE_KEYWORDS)


def compute_candidates(
    github_events: list[GithubEvent],
    x_posts: list[XPost],
    account_live_since: datetime,
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (ranked candidates, excluded-as-false).

    v0 watches exactly two things, both narrow on purpose (Ogun's law: false
    positives are fatal, so v0 trades recall for precision):
    1. Releases with no keyword-overlapping X post after them — excluded
       entirely (not surfaced as a gap) if they predate the account, since
       there was no way to have announced them.
    2. Milestone-tagged commits (see MILESTONE_KEYWORDS) since the account
       went live, collapsed into one gap so a multi-commit pivot reads as
       the single real gap it is, not N near-duplicate ones. Routine commits
       and night-voice lore commits are never candidates — most work isn't
       meant to be tweeted, and treating it as a gap would be the crying-wolf
       failure mode this whole law exists to prevent.
    """
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    all_post_keywords: set[str] = set()
    for p in x_posts:
        all_post_keywords |= _keywords(p.text)

    releases = [e for e in github_events if e.kind == "release"]
    commits = [e for e in github_events if e.kind == "commit"]

    for r in releases:
        if r.ts < account_live_since:
            excluded.append(GapCandidate(
                slug=f"release-{r.id}", headline=f"Release {r.id} predates @oritatown",
                detail=f"'{r.title}' published {r.ts.isoformat()}, before the account existed "
                       f"({account_live_since.isoformat()}). No way to have announced it.",
                confidence=0.0, evidence=[r.url],
            ))
            continue
        overlap = _keywords(r.title) & all_post_keywords
        if not overlap:
            surfaced.append(GapCandidate(
                slug=f"release-{r.id}",
                headline=f"Release '{r.title}' shipped but never reached @oritatown",
                detail=f"Published {r.ts.isoformat()}; no X post shares a keyword with its title.",
                confidence=0.9, evidence=[r.url],
            ))

    milestones = [c for c in commits if c.ts >= account_live_since and _is_milestone(c)]
    if milestones:
        overlap = set().union(*(_keywords(m.title) for m in milestones)) & all_post_keywords
        matched_keyword = overlap & MILESTONE_KEYWORDS
        if not matched_keyword:
            confidence = min(0.85, 0.35 + 0.1 * len(milestones))
            surfaced.append(GapCandidate(
                slug="milestone-unannounced",
                headline="Milestone-level work shipped but never reached @oritatown",
                detail=f"{len(milestones)} milestone commit(s) since {account_live_since.date()} "
                       f"(matching {sorted(MILESTONE_KEYWORDS)}), none echoed in a post.",
                confidence=round(confidence, 2),
                evidence=[m.url for m in milestones][:5],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


# The coincidence tail. A commit topic that recurs many times and never reaches
# X is LOUD, not important — routine bookkeeping, night-lore, small fixes. A
# naive detector screams "you committed 'ledger' twenty-six times and never
# tweeted it!" — the exact false positive Ogun's law exists to kill. So these
# are surfaced at a deliberately capped, sub-bar confidence and labeled
# coincidence downstream: shown to prove the engine weighed them and dropped
# them, never claimed as the gap. Volume does not lift a coincidence over the
# bar; only salience (a milestone commit) can clear it.
COINCIDENCE_CAP = 0.55  # hard ceiling — must stay below ranking.CONFIDENCE_BAR
COINCIDENCE_MIN_CLUSTER = 4  # a topic must recur at least this often to show
COINCIDENCE_MAX_TOPICS = 6  # only the loudest handful; the tail is not a dump
# Topic words too generic or count-like to read as a real subject.
COINCIDENCE_STOPTOPICS = {
    "one", "two", "three", "now", "not", "via", "new", "day", "off-by-one",
}


def coincidence_candidates(
    github_events: list[GithubEvent],
    x_posts: list[XPost],
    account_live_since: datetime,
) -> list[GapCandidate]:
    """The confidence tail: loud-but-routine commit topics absent from X.

    These are near-misses on purpose — things a careless scan would flag. Each
    is capped below the confidence bar so it can never be mistaken for the gap.
    """
    all_post_keywords: set[str] = set()
    for p in x_posts:
        all_post_keywords |= _keywords(p.text)

    # Count topic recurrence and remember the commits behind each topic.
    topic_count: dict[str, int] = {}
    topic_urls: dict[str, list[str]] = {}
    for e in github_events:
        if e.kind != "commit" or e.ts < account_live_since:
            continue
        if e.author.lower() in QUIET_VOICE_AUTHORS:
            continue
        for w in _keywords(e.title):
            if w in all_post_keywords:
                continue  # the topic DID reach X — no seam here
            if w in MILESTONE_KEYWORDS or w in COINCIDENCE_STOPTOPICS:
                continue  # milestone words feed the primary; stoptopics are noise
            topic_count[w] = topic_count.get(w, 0) + 1
            topic_urls.setdefault(w, [])
            if len(topic_urls[w]) < 5:
                topic_urls[w].append(e.url)

    loud = sorted(
        ((w, n) for w, n in topic_count.items() if n >= COINCIDENCE_MIN_CLUSTER),
        key=lambda wn: (-wn[1], wn[0]),
    )[:COINCIDENCE_MAX_TOPICS]

    out: list[GapCandidate] = []
    for topic, n in loud:
        # Saturating, sub-bar score: recurrence nudges it, never lifts it over.
        confidence = round(min(COINCIDENCE_CAP, 0.30 + 0.02 * n), 2)
        out.append(GapCandidate(
            slug=f"coincidence-{topic}",
            headline=f"'{topic}' recurs in commits but stays off @oritatown",
            detail=f"{n} commit(s) since {account_live_since.date()} touch '{topic}', "
                   f"none echoed in a post. Routine work is not a gap — coincidence, not seam.",
            confidence=confidence,
            evidence=topic_urls[topic],
        ))
    return out


def _effective_since(now: datetime, window_hours: int, account_live_since: datetime) -> datetime:
    """How far back the scan actually reaches for GitHub commits (ROADMAP.md
    #19 — the recurring-gap machinery that keeps the daily cadence sustainable).

    `window_hours` is a floor on freshness, never a ceiling that lets a
    still-open gap quietly fall out of view. A milestone commit that shipped
    the day the account went live and has never been announced is exactly as
    real a gap today as it was that day — so the scan always reaches back at
    least to `account_live_since`, never merely the last `window_hours`.
    Without this, a quiet 24h window would let genuinely still-unannounced
    work age out of the scan's sight one day at a time; that is not the
    confidence bar failing, it is the scan simply not looking anymore. This
    is what makes the same honest gap recur, day after day, until an X post
    actually closes it — rather than the report going silent the moment the
    rolling window drifts past whatever caused it.
    """
    rolling = now - timedelta(hours=window_hours)
    return min(rolling, account_live_since)


def run_scan(
    owner: str,
    repo: str,
    window_hours: int = 24,
    x_posts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the seam scan.

    `x_posts=None` (the default): unchanged behavior — reads the local
    `HAND/mortal-sky-log.md` fallback via `load_x_posts_from_ledger`, exactly
    as before ROADMAP.md #94.

    `x_posts=<list of normalized dicts>`: a live-sourced override, parsed via
    `load_x_posts_from_live` (which itself refuses an empty list — see its
    own docstring) instead of reading the ledger. This is the wired-up path
    for a caller already holding a real per-user OAuth-connected X read.
    """
    from seam_engine.ranking import rank

    x_post_objs = (
        load_x_posts_from_ledger() if x_posts is None else load_x_posts_from_live(x_posts)
    )
    account_live_since = min((p.ts for p in x_post_objs), default=None)
    if account_live_since is None:
        account_live_since = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    since = _effective_since(now, window_hours, account_live_since)

    events = fetch_github_activity(owner, repo, since)
    surfaced, excluded = compute_candidates(events, x_post_objs, account_live_since)
    coincidences = coincidence_candidates(events, x_post_objs, account_live_since)

    ranking = rank(surfaced + coincidences)
    primary = ranking.primary

    return {
        "generated_at": now.isoformat(),
        "repo": f"{owner}/{repo}",
        "window_hours": window_hours,
        "account_live_since": account_live_since.isoformat(),
        "x_posts_source": "ledger" if x_posts is None else "live",
        "confidence_bar": ranking.confidence_bar,
        "separation_margin": ranking.separation_margin,
        "primary_gap": asdict(primary) if primary else None,
        "tail": [asdict(g) for g in ranking.tail],
        "excluded": [asdict(g) for g in excluded],
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: `python -m seam_engine.scan [output.json] [--x-posts <path>]`.

    `--x-posts <path>` reads a JSON file holding a list of normalized live
    posts (see `load_x_posts_from_live`) and threads it through as `run_scan`'s
    `x_posts` override; omitted, `run_scan` uses the ledger fallback exactly
    as it always has.
    """
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    x_posts: list[dict[str, Any]] | None = None
    if "--x-posts" in argv:
        i = argv.index("--x-posts")
        if i + 1 >= len(argv):
            print("--x-posts needs a path to a JSON file of normalized live posts.")
            return 2
        x_posts_path = Path(argv[i + 1])
        del argv[i : i + 2]
        x_posts = json.loads(x_posts_path.read_text())

    out = argv[0] if argv else None
    result = run_scan("thierrypdamiba", "orita", x_posts=x_posts)
    text = json.dumps(result, indent=2, default=str)
    if out:
        Path(out).write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
