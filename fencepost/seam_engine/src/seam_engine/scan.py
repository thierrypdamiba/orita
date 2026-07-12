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
  requires an OAuth-connected account. This scan runs headless with no live
  OAuth session, so v0 falls back to the town's own public record of what it
  posted — HAND/mortal-sky-log.md — which is itself sourced from real tweet
  URLs. That fallback is used only because no gateway session is attached
  here; it is not a substitute for the live read scope once one is wired up.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

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
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "fencepost-seam-scan"}

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


def run_scan(owner: str, repo: str, window_hours: int = 24) -> dict[str, Any]:
    from seam_engine.ranking import rank

    x_posts = load_x_posts_from_ledger()
    account_live_since = min((p.ts for p in x_posts), default=None)
    if account_live_since is None:
        account_live_since = datetime.now(timezone.utc)

    from datetime import timedelta
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


if __name__ == "__main__":
    import sys
    result = run_scan("thierrypdamiba", "orita")
    out = sys.argv[1] if len(sys.argv) > 1 else None
    text = json.dumps(result, indent=2, default=str)
    if out:
        Path(out).write_text(text + "\n")
    else:
        print(text)
