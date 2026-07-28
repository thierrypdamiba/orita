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

  ROADMAP.md #128: `fetch_github_activity` never got the matching override
  task 94 built for X — `load_github_events_from_live` + `run_scan(...,
  github_events=...)` close that gap the same way, for the same reason. A
  hosted session (like this town's own hourly ritual) can hold an
  already-authorized `github` MCP channel (`list_commits`, `list_issues`,
  `get_latest_release`) while its own sandbox proxy layer blocks the direct
  unauthenticated `httpx` call to `api.github.com` outright — the identical
  wall the Oracle Desk's cadence sources (tasks 60/63/64/75/78/89/93) have
  hit and left honestly PENDING, except `scan.py` is the engine the hourly
  ritual's actual daily deliverable (the Fencepost Report) depends on, not
  an Oracle cadence row that can wait for the next scheduled CI run. The
  caller normalizes each commit/release to the same `kind`/`id`/`title`/
  `url`/`ts`/`author` shape `GithubEvent` already uses and hands it in —
  same boundary, same discipline, same refuse-empty reasoning (this repo
  commits most hours of most days; an empty live read is almost always a
  failed or blocked call, not a quiet one).

Recurring, on purpose (ROADMAP.md #19): `_effective_since` makes `run_scan`
always reach back at least to `account_live_since`, never merely the last
`window_hours`. A milestone commit stays a live candidate for as long as it
remains genuinely unannounced — the daily cadence does not depend on
something milestone-worthy happening to land inside a rolling window; it
depends only on whether the town has actually announced its own work yet.
That is the machinery, not a promise: some days still clear no gap, honestly
(report.py's own quiet-day branch), because Ogun's law forbids inventing one.

Found and closed 2026-07-19: the paragraph above is true of the direct-fetch
path (`fetch_github_activity` always receives `_effective_since`'s answer as
its `since`) but was never actually true of the live-override path
(`load_github_events_from_live`) — `since` was computed in `run_scan` and
then simply discarded whenever `github_events` was supplied, and
`load_github_events_from_live` never checked that the caller's list reached
back far enough. This was not a hypothetical: task 128's own note already
admitted its live pull "cap[s] well short of the full history back to
2026-07-12" when this sandbox's proxy wall forces the override path, and the
real ledger shows the failure it warned of actually happening — 4 real,
still-unannounced milestone commits sealed as this town's own primary gap on
2026-07-18 (`fencepost/GAPS/2026-07-18.md`, evidence
5110507911296f18…/fab95533935e34db…/d8d98321640fa055…/a53262bfcc4412eb…)
had vanished from the very next day's override-sourced scan
(`fencepost/candidates/2026-07-19.json`, `github_events_source: "override"`,
only 1 unrelated commit) with no real X post ever landing in between to
explain it (`X_PostTweet`/`X_GetUserTweets` have been forbidden since
2026-07-14 — `tools/x_outage_tracker.py`'s own log). `run_scan`'s new
`check_prior_milestones`/`ledger_base` parameters (and
`_unresolved_prior_milestone_evidence`, below) close it: a caller that asks
for the check gets a loud `ValueError` naming exactly which previously-sealed
evidence its supplied `github_events` is missing, rather than a silently
thinner report. `main()` (the CLI both `seam-scan.yml` and every manual
override run actually call) turns the check on by default. `run_scan()`
called directly (as every existing test in this file already does) keeps its
prior, unchanged behavior — the check is opt-in there, so nothing already
proven true above regresses.
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


_MAX_COMMIT_PAGES = 50  # 5,000 commits' worth of headroom -- a real safety valve, not a
# soft cap: see fetch_github_activity's own docstring for why hitting it raises instead
# of silently truncating.


def fetch_github_activity(owner: str, repo: str, since: datetime) -> list[GithubEvent]:
    """Read-only: commits + the latest release, since `since`. GET only.

    Found and closed 2026-07-19: this call used to fetch a single
    `per_page=100` page of `/commits` and stop, silently keeping only the
    100 MOST RECENT commits since `since` -- correct for a young repo,
    silently wrong the moment the real commit count between `since` and now
    passed 100 (exactly what `_effective_since` reaching back to
    `account_live_since` guarantees will eventually happen). That is what
    surfaced as a live `seam-scan` CI failure this hour: task 150's own new
    `check_prior_milestones` gate (shipped the night before) went looking
    for 14 previously-sealed, still-unannounced milestone commits back to
    2026-07-12 and found the direct-fetch path's real `github_events`
    missing every one of them -- not because they'd been announced or fallen
    out of the ledger's memory, but because they'd fallen off page 1. Now
    paginated: keeps requesting successive pages until GitHub returns one
    shorter than `per_page` (the real last page), so `since` reaching back
    further always means fetching more, never quietly capping at the newest
    100 regardless of `since`. `_MAX_COMMIT_PAGES` raises rather than
    silently truncating if GitHub ever returns `_MAX_COMMIT_PAGES` full
    pages in a row -- the same refuse-to-guess discipline
    `load_github_events_from_live`'s empty-list refusal already holds one
    function up.
    """
    events: list[GithubEvent] = []
    headers = github_headers()

    with httpx.Client(timeout=15.0, headers=headers) as client:
        page = 1
        while True:
            commits = client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/commits",
                params={"since": since.isoformat(), "per_page": 100, "page": page},
            )
            commits.raise_for_status()
            batch = commits.json()
            for c in batch:
                events.append(GithubEvent(
                    kind="commit",
                    id=c["sha"][:7],
                    title=c["commit"]["message"].splitlines()[0],
                    url=c["html_url"],
                    ts=_parse_ts(c["commit"]["author"]["date"]),
                    author=c["commit"]["author"]["name"],
                ))
            if len(batch) < 100:
                break
            page += 1
            if page > _MAX_COMMIT_PAGES:
                raise RuntimeError(
                    f"fetch_github_activity(): still receiving full 100-commit pages "
                    f"after {_MAX_COMMIT_PAGES} pages since {since.isoformat()} -- "
                    "refusing to keep paginating silently. Either GitHub's API is "
                    "behaving unexpectedly, or this repo genuinely has more than "
                    f"{_MAX_COMMIT_PAGES * 100} commits in the window; raise "
                    "_MAX_COMMIT_PAGES deliberately if the latter, don't just retry."
                )

        release = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest")
        if release.status_code == 200:
            event = _release_event_from_json(release.json())
            if event.ts >= since:
                events.append(event)

    return events


def _release_event_from_json(r: dict[str, Any]) -> GithubEvent:
    """Build the shared `GithubEvent` shape from a raw `/releases/latest`
    response body — factored out of `fetch_github_activity` so
    `fetch_latest_release` (below) can reuse the exact same parsing without
    a second hand-typed copy."""
    ts = _parse_ts(r["published_at"])
    return GithubEvent(
        kind="release", id=r["tag_name"], title=r["name"] or r["tag_name"],
        url=r["html_url"], ts=ts, author=r.get("author", {}).get("login", "unknown"),
    )


def fetch_latest_release(owner: str, repo: str) -> GithubEvent | None:
    """Read-only: the single latest release of a public GitHub repo, or
    `None` if it has none. Exactly one GET, to `/releases/latest` — never
    touches `/commits`.

    ROADMAP.md #157: `server.get_latest_release` used to answer this same
    question by calling `fetch_github_activity(owner, repo, EPOCH)` and
    filtering the result for `kind == "release"` — a shortcut that was
    merely wasteful before task 154 (one unpaginated 100-commit page,
    thrown away) and became a real, live-reproducible bug after it: an
    epoch `since` now forces `fetch_github_activity` to paginate the
    repo's ENTIRE commit history before it ever reaches the release call,
    and once that history passes `_MAX_COMMIT_PAGES * 100` commits (5,000
    — plausible for a repo committing most hours of most days), the call
    raises `RuntimeError` and never returns a release again. This function
    answers the release question the way it was always actually asked —
    one request, no commit pagination, no `since` at all.
    """
    headers = github_headers()
    with httpx.Client(timeout=15.0, headers=headers) as client:
        release = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest")
        if release.status_code == 200:
            return _release_event_from_json(release.json())
    return None


_REQUIRED_LIVE_EVENT_KEYS = ("kind", "id", "title", "url", "ts", "author")


def load_github_events_from_live(data: list[dict[str, Any]]) -> list[GithubEvent]:
    """Parse a caller-normalized live GitHub read into the same `GithubEvent`
    shape `fetch_github_activity` already produces.

    ROADMAP.md #128: `load_x_posts_from_live` (task 94) closed this class of
    gap for X reads; `fetch_github_activity` itself never gained the
    matching override, so a caller already holding a live, already-
    authorized GitHub read (this session's `mcp__github__list_commits`/
    `get_latest_release`; a self-hosted fork's own gateway) had no way to
    hand it to `run_scan` — the direct `httpx` call to `api.github.com` was
    the only path in, and a hosted sandbox's own proxy layer can block that
    outright ("GitHub access is not enabled for this session") while still
    exposing an already-authorized MCP channel that answers the identical
    question. This closes it, mirroring `load_x_posts_from_live` line for
    line:

    - A malformed entry (missing one of the six required keys) raises
      `ValueError` naming the missing key and the entry's index — never
      silently dropped, per Ogun's precision-over-recall law.
    - An EMPTY list raises `ValueError` rather than being accepted as
      "nothing has shipped since the window opened." This repo commits most
      hours of most days — an empty live read over any realistic window
      almost always means the call failed or was blocked, not that the
      account has genuinely gone quiet. Pass `github_events=None` to
      `run_scan` (the default) to use the direct `fetch_github_activity`
      call instead of an empty live override.
    """
    if not data:
        raise ValueError(
            "load_github_events_from_live() received an empty list — refusing "
            "to treat that as \"nothing shipped since the window opened\" (this "
            "repo commits most hours of most days). An empty live read almost "
            "always means the call failed or was blocked; pass github_events=None "
            "to run_scan to use the direct fetch_github_activity call instead of "
            "an empty override."
        )
    events: list[GithubEvent] = []
    for i, entry in enumerate(data):
        missing = [k for k in _REQUIRED_LIVE_EVENT_KEYS if k not in entry]
        if missing:
            raise ValueError(
                f"load_github_events_from_live(): entry {i} is missing required "
                f"key(s) {missing} (expected kind/id/title/url/ts/author on "
                f"every normalized event): {entry!r}"
            )
        events.append(GithubEvent(
            kind=str(entry["kind"]),
            id=str(entry["id"]),
            title=str(entry["title"]),
            url=str(entry["url"]),
            ts=_parse_ts(entry["ts"]) if isinstance(entry["ts"], str) else entry["ts"],
            author=str(entry["author"]),
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
        title_keywords = _keywords(r.title)
        overlap = title_keywords & all_post_keywords
        # A bare version-string title ("v1.0", "v0.2.0") yields NO extractable
        # keywords -- `_keywords` needs a letter followed by two-or-more word
        # chars, which a plain release version never carries -- so `overlap` is
        # empty for a reason that has nothing to do with whether the release was
        # announced. Judging announcement by keyword overlap ALONE would then
        # flag every such release as unannounced even when a post names it
        # verbatim: a 0.9-confidence false positive, exactly the crying-wolf
        # failure Ogun's law calls fatal. So when (and only when) the title
        # yields no keywords to match on, fall back to a raw case-insensitive
        # substring of the title against post text -- you announce "v1.0" by
        # literally writing "v1.0". Titles that DO yield keywords keep the exact
        # overlap behavior, unchanged.
        if title_keywords:
            announced = bool(overlap)
        else:
            title_needle = r.title.strip().lower()
            announced = bool(title_needle) and any(
                title_needle in p.text.lower() for p in x_posts
            )
        if not announced:
            reason = (
                "no X post shares a keyword with its title"
                if title_keywords
                else "its title carries no keyword to match, and no X post names it verbatim"
            )
            surfaced.append(GapCandidate(
                slug=f"release-{r.id}",
                headline=f"Release '{r.title}' shipped but never reached @oritatown",
                detail=f"Published {r.ts.isoformat()}; {reason}.",
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


def _unresolved_prior_milestone_evidence(
    x_posts: list[XPost], ledger_base: Path | None = None
) -> dict[str, str]:
    """Every evidence URL the Ledger has ever sealed under a
    `milestone-unannounced` primary gap, narrowed to the ones still
    genuinely open: no real X post in `x_posts` landed on or after the gap
    was sealed. Returns `{evidence_url: sealed_generated_at}` so a caller can
    name *when* each one was sealed, not just that it was.

    Only `primary_gap` entries are readable this way — `ledger.append_scan`
    seals a tail entry's `slug`/`confidence`/`label` only, never its
    evidence (see its own `sealed["tail"]` construction), so a
    `milestone-unannounced` candidate that only ever sat in the tail leaves
    no evidence trail this function can recover. That is a real, narrower
    scope than "every milestone gap this town has ever seen" — honest about
    it rather than pretending to catch more than it can: it closes the
    specific failure this town's own ledger already lived through (a
    `primary_gap` silently disappearing the next day with no resolving
    post), not every theoretically possible variant.

    A post landing after the gap was sealed is treated as a plausible
    resolution and drops that gap's evidence from the result — this
    function's job is to catch a truncated events window impersonating a
    resolved gap, not to relitigate whether a resolution was a good one.
    """
    from seam_engine import ledger as _ledger

    out: dict[str, str] = {}
    for rec in _ledger.read_records(ledger_base):
        sealed = rec.get("sealed", {})
        primary = sealed.get("primary_gap")
        if not primary or primary.get("slug") != "milestone-unannounced":
            continue
        sealed_at = sealed.get("generated_at")
        if not sealed_at:
            continue
        sealed_ts = _parse_ts(sealed_at)
        if any(p.ts >= sealed_ts for p in x_posts):
            continue
        for url in primary.get("evidence", []):
            out.setdefault(url, sealed_at)
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
    github_events: list[dict[str, Any]] | None = None,
    check_prior_milestones: bool = False,
    ledger_base: Path | None = None,
) -> dict[str, Any]:
    """Run the seam scan.

    `x_posts=None` (the default): unchanged behavior — reads the local
    `HAND/mortal-sky-log.md` fallback via `load_x_posts_from_ledger`, exactly
    as before ROADMAP.md #94.

    `x_posts=<list of normalized dicts>`: a live-sourced override, parsed via
    `load_x_posts_from_live` (which itself refuses an empty list — see its
    own docstring) instead of reading the ledger. This is the wired-up path
    for a caller already holding a real per-user OAuth-connected X read.

    `github_events=None` (the default): unchanged behavior — calls
    `fetch_github_activity` directly, exactly as before ROADMAP.md #128.

    `github_events=<list of normalized dicts>`: a live-sourced override,
    parsed via `load_github_events_from_live` (which itself refuses an empty
    list — see its own docstring) instead of calling `fetch_github_activity`.
    This is the wired-up path for a caller already holding a real,
    already-authorized GitHub read (e.g. this session's `github` MCP
    channel) when the direct `httpx` path to `api.github.com` is unavailable.

    `check_prior_milestones=False` (the default): unchanged behavior — every
    test in this file that calls `run_scan` directly already relies on this,
    and keeps working exactly as before. `check_prior_milestones=True` turns
    on `_unresolved_prior_milestone_evidence` (see its own docstring, and the
    module docstring's "Found and closed 2026-07-19" paragraph, for why this
    exists): if the resulting `events` — from EITHER source, direct or
    override — is missing evidence for a `milestone-unannounced` gap the
    Ledger already sealed as open and nothing has since plausibly resolved,
    `run_scan` raises `ValueError` naming what is missing, rather than
    silently reporting a thinner gap (or none at all) than the town's own
    ledger already knows is real. `ledger_base=None` reads the real
    `fencepost/GAPS/` ledger (`ledger.read_records`'s own default); pass a
    directory to point at a fixture ledger in a test.
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

    events = (
        fetch_github_activity(owner, repo, since)
        if github_events is None
        else load_github_events_from_live(github_events)
    )

    if check_prior_milestones:
        unresolved = _unresolved_prior_milestone_evidence(x_post_objs, ledger_base)
        present = {e.url for e in events}
        missing = {url: at for url, at in unresolved.items() if url not in present}
        if missing:
            example_url, example_sealed_at = next(iter(sorted(missing.items())))
            raise ValueError(
                f"run_scan(): the supplied github_events data is missing "
                f"{len(missing)} previously-sealed, still-unannounced "
                f"'milestone-unannounced' commit(s) the Ledger already "
                f"recorded as open (e.g. {example_url}, sealed "
                f"{example_sealed_at}) — no real X post has landed since any "
                f"of them was sealed, so this is not a resolved gap, it is an "
                f"events window that does not reach back far enough "
                f"(github_events_source={'override' if github_events is not None else 'direct'}). "
                f"Widen the fetch to cover these commits, or the report will "
                f"silently under-count a real, still-open gap."
            )

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
        "github_events_source": "direct" if github_events is None else "override",
        "confidence_bar": ranking.confidence_bar,
        "separation_margin": ranking.separation_margin,
        "primary_gap": asdict(primary) if primary else None,
        "tail": [asdict(g) for g in ranking.tail],
        "excluded": [asdict(g) for g in excluded],
    }


def _load_json_list(path: Path) -> list[Any]:
    """Load a whole-file JSON list from a CLI-supplied path, refusing a
    syntactically valid but non-list payload with a named error instead of
    letting it reach `load_x_posts_from_live`/`load_github_events_from_live`
    unmarked (both call `enumerate()`/`not data` on the result, which on a
    dict, string, int, or bool produces a confusing crash or silently wrong
    behavior rather than a clear message). Mirrors `RECIPES/*/detector.py`'s
    `_load_rows` (task 358) and `gmail_calendar.py`'s `_load_rows` (task
    359) exactly — the same bug class, on `scan.py`'s and `combined_scan.py`'s
    own `--x-posts`/`--github-events` CLI loaders, which that scan's grep
    for non-guarded `json.loads()` call sites had not yet reached."""
    data = json.loads(Path(path).read_text())
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(data).__name__}")
    return data


def main(argv: list[str] | None = None) -> int:
    """CLI: `python -m seam_engine.scan [output.json] [--x-posts <path>] [--github-events <path>]`.

    `--x-posts <path>` reads a JSON file holding a list of normalized live
    posts (see `load_x_posts_from_live`) and threads it through as `run_scan`'s
    `x_posts` override; omitted, `run_scan` uses the ledger fallback exactly
    as it always has.

    `--github-events <path>` reads a JSON file holding a list of normalized
    live GitHub events (see `load_github_events_from_live`) and threads it
    through as `run_scan`'s `github_events` override; omitted, `run_scan`
    calls `fetch_github_activity` directly exactly as it always has.

    Always calls `run_scan(..., check_prior_milestones=True)` — this is the
    real entrypoint both `seam-scan.yml`'s cron and every manual
    override run actually invoke, so it is where the 2026-07-19 fix (module
    docstring, "Found and closed") is switched on: a `--github-events` (or
    direct-fetch) result that silently drops a still-open, previously-sealed
    milestone gap raises here rather than quietly shipping a thinner report.
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
        x_posts = _load_json_list(x_posts_path)

    github_events: list[dict[str, Any]] | None = None
    if "--github-events" in argv:
        i = argv.index("--github-events")
        if i + 1 >= len(argv):
            print("--github-events needs a path to a JSON file of normalized live events.")
            return 2
        github_events_path = Path(argv[i + 1])
        del argv[i : i + 2]
        github_events = _load_json_list(github_events_path)

    out = argv[0] if argv else None
    result = run_scan(
        "thierrypdamiba", "orita", x_posts=x_posts, github_events=github_events,
        check_prior_milestones=True,
    )
    text = json.dumps(result, indent=2, default=str)
    if out:
        Path(out).write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
