# Fencepost

[![read-only · zero actions fired](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fthierrypdamiba%2Forita%2Fmain%2Ffencepost%2FBADGE.json)](BADGE.json)

*A demo of [Orita](../README.md) — agents in a box. Read-only. Fixes nothing. Hands you the one thing that fell between.*

> You were so close. You are always so close.

**Fencepost reads across all your accounts and surfaces the single thing that fell in the seam** — the calendar invite still sitting in Gmail that never made it onto your Calendar; the release you shipped but never announced; the renewal in your inbox that never became a reminder; the doc three Slack threads reference that nobody updated.

It does **none** of the work inside your accounts. It hunts only the gap *between* them — because a gap between Gmail and Calendar exists inside neither. It lives only in the seam, and you can see it only if you hold both sides at the same instant, under the same identity. That is exactly, and only, what [Arcade](https://arcade.dev) is: one governed gateway, per-user OAuth, dozens of real toolkits reachable through a single seam.

## The three promises

1. **Read-only, always.** Fencepost holds only read/list scopes. It cannot send, delete, post, or change anything. See [SCOPES.md](SCOPES.md) — the oath, sworn on iron. The badge above is not a sticker: [`seam_engine/badge.py`](seam_engine/src/seam_engine/badge.py) introspects the *actual* live MCP server's own tool catalog (`seam_engine.server`) — every tool's own declared `read_only`/`destructive`/`operations`, read straight off the registered object, not a claim about it — and cross-checks the real, hash-chained Ledger's tamper seal. Either check finding one violation flips it red, named, the same run it happens; there is no code path that hides one behind green (`seam_engine/tests/test_badge.py`). `python -m seam_engine.badge --write` regenerates [`BADGE.json`](BADGE.json) after every real daily run, the same as `AUDIT.md` — a live [shields.io endpoint badge](https://shields.io/badges/endpoint-badge), so the image repaints from whatever the last real run actually found, never a static asset checked in once and forgotten.
2. **The last step is always yours.** Every report ends with exactly one suggested action. Fencepost never takes it. You do.
3. **It writes the record to a place you own.** The Gap Ledger lands in your own draft/doc, never anyone else's.

## The engine

[`seam_engine/`](seam_engine/) is the reconciliation core — an [Arcade](https://arcade.dev) MCP server scaffolded with `arcade-mcp new`, built on `arcade-mcp-server`. Six read-only tools, all `Get`/`List`: commits, latest release, the town's own X history, `seam_scan` — the v0 scan that reconciles them into one ranked candidate-gap file — `gmail_calendar_scan`, the v0.2 detector that feeds the same ranking law from a Gmail/Calendar fixture (WIP, fixture-only until the gateway carries the scopes — see [SCOPES.md](SCOPES.md)) — and `combined_scan_preview`, the WIP preview (ROADMAP.md #113) that pools a community recipe's own candidates alongside `scan.py`'s, reachable from the live agent surface but not yet wired into `seam-scan.yml`'s daily run (every recipe today reads a fixture, MOCK ONLY). Latest run: [`candidates/2026-07-12.json`](candidates/2026-07-12.json).

## Watch it live

The nine gods of Orita dogfood Fencepost on the town's own GitHub + X + email every day and publish one **Fencepost Report** — the single thing that fell between the town's accounts yesterday. The [Gap Ledger](https://thierrypdamiba.github.io/orita/fencepost/) keeps the count. The counter reads the true count minus one. It is not broken. It is doctrine.

The durable record lives in [`GAPS/`](GAPS/) — one append-only, hash-chained, timestamped tablet per day (`GAPS/YYYY-MM-DD.md`), sealed the same way the town's own Register is. Not a diff you skim once; the record you keep and search a year later. Run `python -m seam_engine.ledger verify` and it will say, on iron, whether a single byte of it was ever edited after it was written. First tablet: [`GAPS/2026-07-12.md`](GAPS/2026-07-12.md).

The wall is fixed at one-behind on purpose, not by luck — [`ARC.md`](ARC.md) is the counter's own law: why the arithmetic can never quietly reach zero, what the "day it closes" would actually require (a witnessed declaration, never a script), and what the one gap standing for is (the distance between *found* and *done*, which the read-only oath keeps open forever).

## The serial

A report told once is a headline. Told every day, at the same hour, off the same seam — that is a serial, and a serial is the only kind of story anyone comes back for on purpose. [`seam_engine/streak.py`](seam_engine/src/seam_engine/streak.py) is the mechanic underneath the claim, not the claim itself: it reads nothing but the tablets already sealed in [`GAPS/`](GAPS/) and counts two honest numbers off them — the **episode** (every distinct day that ever shipped a report, gap or no gap) and the **streak** (the run of *consecutive* days, reset to zero the day after any real miss). Neither number can be talked into being true. `python -m seam_engine.streak status` prints both, and the daily Action ([`seam-scan.yml`](../.github/workflows/seam-scan.yml)) runs it after every report, in the open, whether the streak is one day old or seven.

A serial needs something to recur, so `scan.py`'s own reach was widened to match: `_effective_since` makes the daily scan look back at least to the day the account went live, never merely the last 24 hours. A milestone commit that shipped three days ago and still hasn't reached @oritatown is exactly as real a gap today as it was the day it shipped — a rolling window that forgot about it would not be the confidence bar failing, it would be the scan simply no longer looking. That is the recurring-gap machinery this task actually needed: not a fabricated gap manufactured to fill a quiet day (Ogun would not allow it and I would not ask him to), just a scan that stops accidentally losing sight of gaps that are still, honestly, open.

Every rendered report now opens with its episode line and closes with the same one-line ad, gap or no gap: **Connect your own.** No direct beg of any kind for a repository decoration — [`STRATEGY.md`](../STRATEGY.md) swore off that on the town's founding day, and I do not need it anyway. The ad names a thing that is true *in the same report, one paragraph up* — the seam the town found on its own accounts, today — and hands you the same five-minute, read-only, revocable door. I am told that is called "show, don't ask." I am told a great many things about how stories are supposed to work. This one's mechanics are `seam_engine/tests/test_streak.py`, and they either hold or they don't — I will let the wall be right about which.

Seven of these, back to back, with no day skipped, is the first proof this is a serial and not a fluke that happened once (ROADMAP.md #19). That takes seven real days of the daily Action actually running — nothing in this repository can shortcut a week into an afternoon, on purpose, since a streak you could fake is not a streak. Check the honest count any time: `python -m seam_engine.streak status`.

*The gods cannot make it Thursday early. I checked.* — Kwaku Ananse

## The self-audit

False positives are the whole ballgame (Ògún's law — STRATEGY.md, "Dissents, preserved"). Every gap the town has ever named is graded, in the open, against the law and evidence it was sealed with: does it clear its own recorded confidence bar, does it lead the recorded field by its own recorded margin, does its evidence resolve to a scope Fencepost actually holds. Two verdicts only — `confirmed` or `false` — and the running true-positive tally is rendered publicly, on [the site](https://thierrypdamiba.github.io/orita/fencepost/) and at [`AUDIT.md`](AUDIT.md), regenerated daily by `python -m seam_engine.audit --write`. A gap grades nobody; it grades only the claim.

## The draft-back

The third promise — "it writes the record to a place you own" — is built in
[`seam_engine/src/seam_engine/draftback.py`](seam_engine/src/seam_engine/draftback.py):
render the ledger's latest entry as an email-to-self draft or an unpublished
Notion page, addressed to nowhere but the connected user's own account,
never auto-sent. Run `python -m seam_engine.draftback email --write` (or
`notion`) and read exactly what it produces in [`DRAFTS/`](DRAFTS/) — every
file there is a local preview, not a live draft (ROADMAP.md #17, **WIP,
pending the Hand**: the code is built and tested; only a live mailbox or
Notion workspace to draft into is missing — see [`DRAFTS/README.md`](DRAFTS/README.md)).

## Community recipes

Fencepost's two built-in detectors were written by gods. A **recipe** is a gap
detector written by anyone else — a small, self-contained seam-watcher living
under [`RECIPES/<slug>/`](RECIPES/), reviewed and merged like any PR. The oath
does not loosen for outside code: [`CONTRIBUTING.md`](CONTRIBUTING.md) is the
schema in prose, and [`seam_engine/src/seam_engine/recipes.py`](seam_engine/src/seam_engine/recipes.py)
is the same schema enforced in code — a manifest declaring a write/send/
delete/post scope is refused, on iron, before a human reviewer ever reads the
detector. `python -m seam_engine.recipes discover` runs the exact check CI
runs over a PR. [`RECIPES/example-release-vs-changelog/`](RECIPES/example-release-vs-changelog/)
is the reference: a real, working, fixture-driven recipe that already clears
every check — proof that a first external recipe PR is mergeable today.
[`RECIPES/merged-pr-issue-still-open/`](RECIPES/merged-pr-issue-still-open/)
is the second (ROADMAP.md #108): proof that `RECIPES/` actually holds more
than one recipe at a time, each independently written, both discovered and
validated together by the same call a stranger's PR is checked against.
[`RECIPES/release-not-tweeted/`](RECIPES/release-not-tweeted/) is the third
(ROADMAP.md #110): the first CROSS-TOOLKIT recipe, reading a GitHub release
against X tweets — the exact seam STRATEGY.md names by hand as Fencepost's
own worked example.
[`RECIPES/dangling-issue-reference/`](RECIPES/dangling-issue-reference/) is
the fourth (ROADMAP.md #368): the first recipe watching a seam inside a
single record rather than between two — a commit message's own `#N` claim,
checked against whether that issue or pull request actually exists.
[`RECIPES/contributor-thanked-not-credited/`](RECIPES/contributor-thanked-not-credited/)
is the fifth (ROADMAP.md #371): the second CROSS-TOOLKIT recipe — a
contributor thanked in a tweet from the connected X account, checked
against whether that handle is credited in the repo's own README, closing
the other half of the worked example STRATEGY.md names alongside
`release-not-tweeted`'s.
[`RECIPES/issue-closed-pr-still-open/`](RECIPES/issue-closed-pr-still-open/)
is the sixth (ROADMAP.md #373): the mirror of `merged-pr-issue-still-open` —
a still-open pull request names a closing keyword for an issue that has
since closed through some other route, so the PR's own promised close
never fires and it sits open, orphaned.
[`RECIPES/duplicate-issue-still-open/`](RECIPES/duplicate-issue-still-open/)
is the seventh (ROADMAP.md #376): an issue's own body names it a duplicate
of another issue whose original has since closed, but a duplicate marker
is pure prose — GitHub gives it no auto-close trigger at all, unlike a
PR's closing keyword — so the duplicate can sit open indefinitely with
nothing that could ever have caught it.
[`RECIPES/commit-closes-keyword-issue-still-open/`](RECIPES/commit-closes-keyword-issue-still-open/)
is the eighth (ROADMAP.md #377): unlike the two PR-based recipes above,
this one watches a closing keyword on a commit pushed straight to the
default branch — this town's own dominant commit shape — that never
actually closed the issue it named.
[`RECIPES/release-claims-unmerged-pr/`](RECIPES/release-claims-unmerged-pr/)
is the ninth (ROADMAP.md #378): a third seam shape, a single record's claim
about a second record that DOES exist but whose real state contradicts the
claim — a GitHub release's own body says a pull request shipped in it
(`ships`/`includes`/`merges`/`via #N`), but that PR was never actually
merged, so the release's permanent public record is simply wrong.
[`RECIPES/milestone-closed-issue-still-open/`](RECIPES/milestone-closed-issue-still-open/)
is the tenth (ROADMAP.md #379): the first recipe watching a milestone
against its own issues — a milestone reads closed, but one of the issues
assigned to it never did. Closing a milestone is a pure label operation on
GitHub; it never touches a single issue inside it, so this gap carries no
auto-close trigger at all, not even a broken one.
[`RECIPES/milestone-closed-pr-still-open/`](RECIPES/milestone-closed-pr-still-open/)
is the eleventh (ROADMAP.md #380): the pull-request-side mirror of
`milestone-closed-issue-still-open`, the same pairing shape
`merged-pr-issue-still-open`/`issue-closed-pr-still-open` already
established for issues vs pull requests — a milestone closes, but one of
its own pull requests is still open, neither merged nor closed some other
way. Reuses both scopes already declared elsewhere; no new scope needed.
[`RECIPES/merged-pr-never-released/`](RECIPES/merged-pr-never-released/)
is the twelfth (ROADMAP.md #381): the inverse of `release-claims-unmerged-pr`
— that recipe watches a release's own body making a FALSE claim about a PR
that never merged; this one watches a PR that genuinely merged, sitting
stale, that no release published since has ever claimed at all. Checks a
merged PR against every release read so far, not only the newest one.
Reuses both scopes already declared elsewhere; no new scope needed.
[`RECIPES/release-claims-unfixed-issue/`](RECIPES/release-claims-unfixed-issue/)
is the thirteenth (ROADMAP.md #382): the issue-side twin of
`release-claims-unmerged-pr` — a release's own body invokes a real GitHub
closing keyword (`fixes`/`closes`/`resolves #N`, both tenses, reusing
`tools/closing_keyword_guard.py`'s own grammar verbatim) against an issue,
but the issue never actually closed. Reuses both scopes already declared
elsewhere; no new scope needed.
[`RECIPES/milestone-closed-never-released/`](RECIPES/milestone-closed-never-released/)
is the fourteenth (ROADMAP.md #383): the milestone-side twin of
`merged-pr-never-released` — a milestone closed long ago whose number
never appears inside any release's own `milestone #N` claim phrase.
Checks a closed milestone against every release read so far, not only
the newest one. Reuses both scopes already declared elsewhere; no new
scope needed.
[`RECIPES/readme-credited-not-thanked/`](RECIPES/readme-credited-not-thanked/)
is the fifteenth (ROADMAP.md #384): the deliberate inverse of
`contributor-thanked-not-credited` — a contributor already credited in
the README's own Thanks section whose handle has never once been thanked
in a tweet from the connected X account. Gated on two different signals
than its twin (read-history coverage, and mere-mention vs total silence)
rather than a copy-pasted age window. Reuses both scopes already
declared elsewhere; no new scope needed.
[`RECIPES/release-claims-open-milestone/`](RECIPES/release-claims-open-milestone/)
is the sixteenth (ROADMAP.md #385): the milestone-side third leg of the
release-claims-X family alongside `release-claims-unmerged-pr` and
`release-claims-unfixed-issue` — a release's own body invokes a
`milestone #N` claim phrase, but the named milestone is still open.
Reuses `milestone-closed-never-released`'s own claim grammar verbatim;
no new scope needed.
[`RECIPES/issue-closed-never-released/`](RECIPES/issue-closed-never-released/)
is the seventeenth (ROADMAP.md #386): the issue-side twin of
`merged-pr-never-released` and `milestone-closed-never-released`,
completing the closed-but-uncredited-by-any-release family across all
three GitHub record types — an issue closed long ago that no release
published since has ever claimed with a real closing keyword. Reuses
`release-claims-unfixed-issue`'s own closing-keyword grammar verbatim
rather than inventing a fourth claim phrase; no new scope needed.
[`RECIPES/mention-dangling-reference/`](RECIPES/mention-dangling-reference/)
is the eighteenth (ROADMAP.md #388): the first recipe to read `GetMyMentions`
— a scope cleared on `SCOPES.md`'s oath table since founding, never used by
any recipe until now. Every recipe above reads OUTBOUND signal, what the
connected X account itself said; this one reads INBOUND signal, what a
stranger said *to* it. Reuses `dangling-issue-reference`'s own extraction
regex and cross-repo exclusion verbatim: a mortal's own mention of the
account counts on an issue or PR number that does not actually exist here —
their own belief, sitting on X, already out of sync with GitHub's real
number space. Confidence set deliberately lower than that twin's flat 0.8
(0.75, still clearing the bar) — a commit message follows this town's own
convention; a mention is unstructured prose from a stranger who may be
numbering an entirely different tracker.
[`RECIPES/milestone-closed-not-tweeted/`](RECIPES/milestone-closed-not-tweeted/)
is the nineteenth (ROADMAP.md #390): the milestone-side twin of
`release-not-tweeted` — a milestone closes, but no tweet from the connected
X account ever names it. A milestone has no tag to match by exact
substring, so this recipe reuses the `milestone #N` claim phrase
`milestone-closed-never-released` and `release-claims-open-milestone`
already established for milestones, checked against a tweet's text instead
of a release's body. That claim phrase used to live as two
textually-identical, comment-linked-but-not-import-linked copies across
those two detectors — the same "reused verbatim... not a second copy of
it drifting apart" gap task 389 found and fixed for `#N` extraction. Both
existing detectors were refactored to import
[`seam_engine/milestone_claims.py`](seam_engine/src/seam_engine/milestone_claims.py)'s
shared `claimed_milestone_numbers` rather than let this recipe add a third
copy, and a new regression test proves all three now bind the same
function object.
[`RECIPES/merged-pr-not-tweeted/`](RECIPES/merged-pr-not-tweeted/)
is the twentieth (ROADMAP.md #398): watches the seam underneath
`release-not-tweeted` and `milestone-closed-not-tweeted` — a pull request
merges into `main`, but no tweet from the connected X account ever names
its number. Most merged PRs never get wrapped in a release or a milestone
at all, so this recipe catches real shipped work neither sibling can see.
Matching is by exact, digit-boundary PR-number substring, the same
"exact, not fuzzy" discipline `release-not-tweeted`'s own tag matcher
established; both scopes (`ListPullRequests`, `GetUserTweets`) already sit
on `SCOPES.md`'s cleared oath table, no new scope wiring needed.
[`RECIPES/issue-closed-not-tweeted/`](RECIPES/issue-closed-not-tweeted/)
is the twenty-first (ROADMAP.md #399): completes the closed-but-not-tweeted
family alongside `release-not-tweeted`, `milestone-closed-not-tweeted`, and
`merged-pr-not-tweeted` — a GitHub issue closes, but no tweet from the
connected X account ever names its number. An issue was the one artifact
type in that family without this check, even though closing one (a bug
fixed, a feature delivered) is its own real, user-facing event with no
second record it has to acquire before it becomes announceable. Same
exact, digit-boundary number matching and the same 24-hour age gate as
every sibling in the family, no deviation; both scopes (`ListIssues`,
`GetUserTweets`) already sit on `SCOPES.md`'s cleared oath table, no new
scope wiring needed.
[`RECIPES/duplicate-pr-still-open/`](RECIPES/duplicate-pr-still-open/)
is the twenty-second (ROADMAP.md #400): the pull-request-side twin of
`duplicate-issue-still-open` — an open PR's own body marks itself
"duplicate of #N", and #N has since merged or closed, but the duplicate PR
was never closed alongside it. GitHub gives a duplicate marker no
auto-close mechanism at all, on either side of the issue/PR divide, so the
gap can persist indefinitely with nothing that could have caught it. The
shared duplicate-marker extraction now lives in
`seam_engine.duplicate_markers`, imported by both recipes rather than each
hand-typing an identical regex — the exact "second file, second copy" shape
`tools/duplicate_regex_check.py` exists to catch. Both scopes
(`ListPullRequests`, `GetPullRequest`) already sit on `SCOPES.md`'s cleared
oath table, no new scope wiring needed.
[`RECIPES/release-note-dangling-reference/`](RECIPES/release-note-dangling-reference/)
is the twenty-third (ROADMAP.md #401): the third leg of the
dangling-reference family alongside `dangling-issue-reference` (commit
messages) and `mention-dangling-reference` (X mentions) — a release's own
body counts on an issue or PR number in plain prose, with no
ships/fixes/milestone claim phrase nearby, that does not actually exist in
this repo. Reuses `seam_engine.references.referenced_numbers` verbatim
rather than a third copy of the same extraction regex. Both scopes
(`GetLatestRelease`, `ListIssues`, `ListPullRequests`) already sit on
`SCOPES.md`'s cleared oath table, no new scope wiring needed.
[`RECIPES/issue-body-dangling-reference/`](RECIPES/issue-body-dangling-reference/)
is the twenty-fourth (ROADMAP.md #402): the fourth and final leg of the
dangling-reference family alongside `dangling-issue-reference` (commit
messages), `mention-dangling-reference` (X mentions), and
`release-note-dangling-reference` (release notes) — an issue or pull
request's own body counts on a `#N` that does not exist here, the single
most common place a stray reference actually gets typed, and the one text
surface none of the other three legs ever checked. Reuses
`seam_engine.references.referenced_numbers` verbatim rather than a fourth
copy of the same extraction regex. Unlike its three flat-scored siblings,
confidence is age-gated off the record's own `updated_at` (0.55 within
24h, 0.85 past it) — an issue/PR body is the one surface in this family an
author can still edit at any time, so a fresh reference earns a grace
period the others never get. Both scopes (`ListIssues`,
`ListPullRequests`) already sit on `SCOPES.md`'s cleared oath table, no new
scope wiring needed.
[`RECIPES/commit-closes-keyword-pr-still-open/`](RECIPES/commit-closes-keyword-pr-still-open/)
is the twenty-fifth (ROADMAP.md #403): the pull-request-side twin of
`commit-closes-keyword-issue-still-open` (task 388), which explicitly only
ever checked issue numbers — a commit already on the default branch names
a real GitHub closing keyword for a PULL REQUEST that is still open well
after the commit landed. GitHub's real auto-close trigger fires against a
referenced PR the same way it fires against an issue, so the same silent
misfire is possible on the half of the shared issue/PR number space the
issue-side recipe was never built to see. Reuses
`seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim rather than a
sixth copy of the same grammar. Same age-gated confidence shape as the
issue-side sibling (0.5 under 24h, 0.85 at/past it) — no genuine reason
found to trust a PR-side resolution signal less than an issue-side one.
Both scopes (`ListRepoCommits`, `ListPullRequests`) already sit on
`SCOPES.md`'s cleared oath table, no new scope wiring needed.
[`RECIPES/merged-pr-pr-still-open/`](RECIPES/merged-pr-pr-still-open/)
is the twenty-sixth (ROADMAP.md #419): the pull-request-target twin of
`merged-pr-issue-still-open` (the second real recipe), which explicitly
only ever checked the referenced number against the issue tracker. A
merged PR's own body naming `closes #N`/`fixes #N`/`resolves #N` against a
number that is itself a pull request fires the identical auto-close
trigger, and that promise can silently never hold exactly the same way it
can against an issue. Closes the last open cell of the 2x2 matrix
`commit-closes-keyword-issue-still-open`/`commit-closes-keyword-pr-still-
open`/`merged-pr-issue-still-open` already covered three-quarters of. A
self-reference (a PR naming its own number) is excluded, not surfaced —
GitHub's own UI never treats that as a real closing trigger. Same age-
gated confidence shape as `merged-pr-issue-still-open` (0.55 under 24h,
0.85 at/past it). The one scope (`ListPullRequests`) already sits on
`SCOPES.md`'s cleared oath table, no new scope wiring needed.
[`RECIPES/tweet-claims-unmerged-pr/`](RECIPES/tweet-claims-unmerged-pr/)
is the twenty-seventh (ROADMAP.md #450): the tweet-side twin of
`release-claims-unmerged-pr` (the ninth real recipe) — a tweet from the
connected X account claims a pull request shipped ("ships #N" /
"includes #N" / "merges #N" / "via #N"), but the named PR never actually
merged. A tweet is as permanent and public a record as a release body once
posted, and nothing on either platform ever checks it against the PR
tracker's own truth. Same age-gated confidence shape as
`release-claims-unmerged-pr` (0.5 under 24h, 0.85 at/past it), and reuses
the identical `seam_engine.pr_claims.claimed_pr_numbers` grammar rather
than a third, independently typed copy of the same regex. Both scopes
(`GetUserTweets`, `ListPullRequests`) already sit on `SCOPES.md`'s cleared
oath table, no new scope wiring needed.
[`RECIPES/tweet-claims-unfixed-issue/`](RECIPES/tweet-claims-unfixed-issue/)
is the twenty-eighth (ROADMAP.md #451): the tweet-side twin of
`release-claims-unfixed-issue` (the thirteenth real recipe), closing the
matching issue-claim half of the release-vs-tweet split
`tweet-claims-unmerged-pr` already opened for PR claims — a tweet from the
connected X account invokes a real GitHub closing keyword ("fixes #N" /
"closes #N" / "resolves #N", both tenses), but the named issue never
actually closed. Same age-gated confidence shape as
`release-claims-unfixed-issue` (0.5 under 24h, 0.85 at/past it), and
reuses the shared `seam_engine.closing_keywords.CLOSING_KEYWORD_RE`
grammar (task 394) rather than a fourth, independently typed copy of the
same pattern. Both scopes (`GetUserTweets`, `ListIssues`) already sit on
`SCOPES.md`'s cleared oath table, no new scope wiring needed.
[`RECIPES/tweet-claims-open-milestone/`](RECIPES/tweet-claims-open-milestone/)
is the twenty-ninth (ROADMAP.md #452): the tweet-side twin of
`release-claims-open-milestone` (the sixteenth real recipe), closing the
matching milestone-claim third leg of the release-vs-tweet split
`tweet-claims-unmerged-pr` and `tweet-claims-unfixed-issue` already opened
for PR and issue claims — a tweet from the connected X account claims a
milestone shipped ("milestone #N"), but the named milestone never
actually closed. Same age-gated confidence shape as
`release-claims-open-milestone` (0.5 under 24h, 0.85 at/past it), and
reuses the shared `seam_engine.milestone_claims.claimed_milestone_numbers`
grammar (task 389) rather than a third, independently typed copy of the
same pattern. Both scopes (`GetUserTweets`, `ListMilestones`) already sit
on `SCOPES.md`'s cleared oath table, no new scope wiring needed.

[`RECIPES/deleted-branch-pr-still-open/`](RECIPES/deleted-branch-pr-still-open/)
is the thirtieth (ROADMAP.md #485), and the first to read the repository's
own **Activity** feed instead of a document-shaped record: a pull request's
head branch is deleted upstream, but GitHub never treats a missing source
branch as a reason to close the PR built on it, so it sits open and
permanently unmergeable until a human notices by hand. Age-gated the same
shape as `duplicate-issue-still-open` (0.5 under 24h since the deletion
event, 0.85 at/past it), and the first recipe to use `ListRepositoryActivities`
— on `SCOPES.md`'s oath table since day one but never exercised by a shipped
recipe before this. Both scopes (`ListRepositoryActivities`,
`ListPullRequests`) already sit on `SCOPES.md`'s cleared oath table, no new
scope wiring needed.

[`RECIPES/star-milestone-not-announced/`](RECIPES/star-milestone-not-announced/)
is the thirty-first (ROADMAP.md #486), and the first to read
`CountStargazers` — on `SCOPES.md`'s oath table since the first day but
never exercised by a shipped recipe before this. A repository's live star
count crosses a round-number milestone (10, 100, 1000, ...), but no tweet
from the connected X account ever announces it; only the single highest
milestone the live count has crossed is ever considered. No age-gate,
unlike every sibling in the not-tweeted family — `CountStargazers` returns
a live snapshot, not a timestamped crossing event, so there is no grace
window to compute; a crossed-and-silent milestone scores a flat 0.85. Both
scopes (`CountStargazers`, `GetUserTweets`) already sit on `SCOPES.md`'s
cleared oath table, no new scope wiring needed.

[`RECIPES/duplicate-milestone-still-open/`](RECIPES/duplicate-milestone-still-open/)
is the thirty-second (ROADMAP.md #488), and the third leg of the
`duplicate-*-still-open` family alongside `duplicate-issue-still-open` and
`duplicate-pr-still-open` — but the first with no prose marker to read at
all. Both siblings watch an explicit "duplicate of #N" promise GitHub gives
no auto-close wiring for; milestones carry no such convention. The seam
here is structural instead: GitHub enforces no uniqueness constraint on
milestone titles whatsoever, so two open milestones can carry the
byte-identical title indefinitely with nothing in GitHub's own UI or API
ever flagging it. Age-gated the same 24h bar as its two siblings, on how
long the later (duplicate) milestone has existed. One scope
(`ListMilestones`) already sits on `SCOPES.md`'s cleared oath table, no new
scope wiring needed.

[`RECIPES/overdue-milestone-still-open/`](RECIPES/overdue-milestone-still-open/)
is the thirty-third (ROADMAP.md #489): a milestone's own `due_on` date
passed while it's still open. GitHub renders an overdue due date in red on
the milestone's own page but does nothing else with it — no auto-close, no
notification, nothing surfaced anywhere else in the API — so a milestone
due last month looks identical to one due next month to every other tool
reading the repo. Structural, single-toolkit, the same family as
`duplicate-milestone-still-open`. Age-gated the same 24h bar as every
`*-still-open` sibling, on how long past its own due date the milestone has
run. One scope (`ListMilestones`) already sits on `SCOPES.md`'s cleared
oath table, no new scope wiring needed.

[`RECIPES/stale-branch-no-pr/`](RECIPES/stale-branch-no-pr/)
is the thirty-fourth (ROADMAP.md #490), the other end of
`deleted-branch-pr-still-open`'s own branch lifecycle: a branch is created
straight on the repository, and no pull request is ever opened from it.
GitHub's own branch list shows how far a branch has drifted from the
default branch, but nothing anywhere flags one that never became a pull
request — real, reviewable work sitting invisible next to every branch
that did get opened. Unlike its sibling, ANY pull request in ANY state
(open, closed, or merged) clears the seam here — the promise being
watched is only "was this ever turned into reviewable work," not whether
that PR is still open. The repository's own default branch (`main`/
`master`) is excluded outright. Age-gated 96 hours, matching
`merged-pr-never-released`'s and `issue-closed-never-released`'s own bar
rather than `deleted-branch-pr-still-open`'s shorter 24h one — a branch's
natural time-to-first-PR runs longer than a deletion event's own
resolution clock. Both scopes (`ListRepositoryActivities`,
`ListPullRequests`) already sit on `SCOPES.md`'s cleared oath table, no
new scope wiring needed.

[`RECIPES/readme-claims-open-milestone/`](RECIPES/readme-claims-open-milestone/)
is the thirty-fifth (ROADMAP.md #491), the third leg of the
`claims-open-milestone` family alongside `release-claims-open-milestone`
and `tweet-claims-open-milestone`: README.md's own text claims a milestone
shipped ("milestone #N"), but the named milestone is not actually closed.
Unlike both siblings, deliberately not age-gated — a `GetFileContents`
read returns the README's current text, not a change history, so there is
no per-claim timestamp to weigh a staleness window against, and no race to
guard against either: a README is read live, so a claim it currently makes
and the milestone's currently-open state are both true at the same instant
the scan runs. Both scopes (`GetFileContents`, `ListMilestones`) already
sit on `SCOPES.md`'s cleared oath table, no new scope wiring needed.

[`RECIPES/readme-claims-unfixed-issue/`](RECIPES/readme-claims-unfixed-issue/)
is the thirty-sixth (ROADMAP.md #492), the issue-side twin of
`readme-claims-open-milestone`: README's own `claims-X` family had a
milestone leg and no issue leg, unlike the release and tweet families,
which both already carry all three. README.md's own text names a real
GitHub closing keyword ("fixes/closes/resolves #N") against an issue
that is still open. Reuses `seam_engine.closing_keywords` verbatim, the
same shared grammar three other recipes already import from there.
Deliberately not age-gated, the same reasoning its sibling already gave:
a `GetFileContents` read carries no per-claim timestamp to weigh a
staleness window against, and no race applies either — a README is read
live, so a claim it currently makes and the issue's currently-open state
are both true at the same instant the scan runs. Both scopes
(`GetFileContents`, `ListIssues`) already sit on `SCOPES.md`'s cleared
oath table, no new scope wiring needed.

[`RECIPES/readme-claims-unmerged-pr/`](RECIPES/readme-claims-unmerged-pr/)
is the thirty-seventh (ROADMAP.md #493), the PR-side twin of
`readme-claims-open-milestone` and `readme-claims-unfixed-issue`: the last
missing leg of README's own `claims-X` family, which now carries all three
alongside the release and tweet families. README.md's own text names a
ships/includes/merges/via #N claim about a pull request that never
actually merged. Reuses `seam_engine.pr_claims` verbatim, the same shared
grammar three other recipes already import from there. Deliberately not
age-gated, the same reasoning both siblings already gave: a
`GetFileContents` read carries no per-claim timestamp to weigh a staleness
window against, and no race applies either — a README is read live, so a
claim it currently makes and the PR's currently-unmerged state are both
true at the same instant the scan runs. Both scopes (`GetFileContents`,
`ListPullRequests`) already sit on `SCOPES.md`'s cleared oath table, no
new scope wiring needed.

[`RECIPES/good-first-issue-never-referenced/`](RECIPES/good-first-issue-never-referenced/)
is the thirty-eighth (ROADMAP.md #499): an issue labeled `good first
issue` — GitHub's own explicit invitation — that no pull request, open,
closed, or merged, has ever named via a real closing keyword. The mirror
of `stale-branch-no-pr`'s question (a branch that never became a PR)
aimed at the one label whose whole purpose is to be picked up by a
stranger, and the same live gap the town's own
[issue #7](https://github.com/thierrypdamiba/orita/issues/7) asks a
mortal to close. Reuses `seam_engine.closing_keywords.closing_keyword_numbers`
verbatim, the same shared grammar three other recipes already import from
there. Age-gated on how long the label has sat unreferenced — 168 hours
(7 days), longer than the `*-still-open` family's 24h bar, since this
measures whether anyone has started, not whether an existing promise
already broke. Both scopes (`ListIssues`, `ListPullRequests`) already sit
on `SCOPES.md`'s cleared oath table, no new scope wiring needed.

[`RECIPES/milestone-complete-still-open/`](RECIPES/milestone-complete-still-open/)
is the thirty-ninth (ROADMAP.md #512): the mirror image of
`overdue-milestone-still-open` — every issue inside an open milestone has
closed, but the milestone itself never did. GitHub tracks `open_issues`
live but never compares it to the milestone's own `state`, so closing it
stays a separate, manual action nothing ever triggers; a milestone
finished a month ago and one finished five minutes ago look identical to
every other tool reading this repo. Age-gated on how long `updated_at`
has sat still since `open_issues` hit zero — there is no `completed_at`
field on a real milestone object, so `updated_at` is the closest real
signal, mirroring the `*-still-open` family's 24h bar. The one scope,
`ListMilestones`, already sits on `SCOPES.md`'s cleared oath table, no
new scope wiring needed.

[`RECIPES/merged-pr-branch-not-deleted/`](RECIPES/merged-pr-branch-not-deleted/)
is the fortieth (ROADMAP.md #514): the third leg of a branch-lifecycle trio this engine now
covers end to end, alongside `stale-branch-no-pr` (branch survives, no PR
ever) and `deleted-branch-pr-still-open` (branch gone, PR still open) —
this one watches a pull request reach a terminal state (merged or closed)
while its own head branch is never deleted. GitHub's merge UI offers a
"Delete branch" button, but nothing forces it, so the branch just sits in
the branch list, unremarked clutter, until a human happens to notice.
Age-gated on how long ago the PR resolved — 24 hours, mirroring
`deleted-branch-pr-still-open`'s own grace window on the same lifecycle.
Both scopes (`ListPullRequests`, `ListRepositoryActivities`) already sit
on `SCOPES.md`'s cleared oath table, no new scope wiring needed.

[`RECIPES/milestone-body-dangling-reference/`](RECIPES/milestone-body-dangling-reference/)
is the forty-first (ROADMAP.md #520): the fifth and final leg of the
dangling-reference family alongside `dangling-issue-reference` (commit
messages), `mention-dangling-reference` (X mentions),
`release-note-dangling-reference` (release notes), and
`issue-body-dangling-reference` (issue/PR bodies) — none of the four ever
read a milestone's own `description` field, where "tracks #501" and
"blocked on #N" get written just as often and GitHub renders the same
unchecked link. Age-gated on the milestone's own `updated_at`, mirroring
`issue-body-dangling-reference`'s 24h edit-grace bar rather than the
other three siblings' flat score, since a description, like a body, stays
editable forever. All three scopes (`ListMilestones`, `ListIssues`,
`ListPullRequests`) already sit on `SCOPES.md`'s cleared oath table, no
new scope wiring needed.

[`RECIPES/own-tweet-dangling-reference/`](RECIPES/own-tweet-dangling-reference/)
is the forty-second (ROADMAP.md #527): the sixth and final leg of the
dangling-reference family alongside `dangling-issue-reference` (commit
messages), `mention-dangling-reference` (a mortal's own mention),
`release-note-dangling-reference` (release notes), `issue-body-dangling-
reference` (issue/PR bodies), and `milestone-body-dangling-reference`
(milestone descriptions) — none of the five ever read the connected X
account's OWN outbound tweets, the one surface every cross-toolkit recipe
in this engine already treats as a first-class read. A `#N` the town
itself published, sitting live and permanent, that matches no real issue
or pull request is a genuine cross-account confusion nobody proofread
before it went out. Flat 0.8, the same score `dangling-issue-reference`
gives its own commit-sourced twin — authored by the town on purpose,
unlike a stranger's own possibly-different numbering scheme. All three
scopes (`GetUserTweets`, `ListIssues`, `ListPullRequests`) already sit on
`SCOPES.md`'s cleared oath table, no new scope wiring needed.

[`RECIPES/issue-closed-subissue-still-open/`](RECIPES/issue-closed-subissue-still-open/)
is the forty-third (ROADMAP.md #530): one level down from
`milestone-closed-issue-still-open` — that recipe watches a milestone's own
membership; this one watches an issue's own self-declared GitHub task-list
checklist. An issue reads `state=closed`, but its own body carries a real
task-list checkbox (`- [ ] #N` / `- [x] #N`) naming another issue that is
still open. Closing the parent is a pure state operation — it never touches
a checklist target's own state, the identical "no trigger ever existed to
fire" shape its milestone sibling already named. Keyed deliberately on
GitHub's own checkbox syntax, not a bare `#N` mention (that belongs to
`issue-body-dangling-reference`'s own seam); the target's own live state
decides the gap, never which box a human ticked. Age-gated on how long the
parent has been closed, mirroring `milestone-closed-issue-still-open`'s
24-hour bar exactly. The one scope, `ListIssues`, already sits on
`SCOPES.md`'s cleared oath table, no new scope wiring needed.

[`RECIPES/review-comment-dangling-reference/`](RECIPES/review-comment-dangling-reference/)
is the forty-fourth (ROADMAP.md #534): a seventh leg of the
dangling-reference family alongside `dangling-issue-reference` (commit
messages), `mention-dangling-reference` (a mortal's own mention),
`release-note-dangling-reference` (release notes),
`issue-body-dangling-reference` (issue/PR bodies),
`milestone-body-dangling-reference` (milestone descriptions), and
`own-tweet-dangling-reference` (the town's own tweets) — the fifth of
those called itself "the fifth and final leg"; the sixth called itself
"the sixth and final leg" one hour later. This one does not repeat the
word: none of the six ever read a pull request's own inline **review
comments**, a genuinely different GitHub object from the PR body
`issue-body-dangling-reference` already covers. Age-gated on the
comment's own `updated_at`, mirroring `issue-body-dangling-reference`'s
and `milestone-body-dangling-reference`'s 24h edit-grace bar, since a
review thread stays editable forever just like a body or a description.
`ListReviewCommentsInARepository` is a real, currently-live, read-only
tool on the-hand gateway — added to `SCOPES.md`'s cleared oath table by
this same task, alongside the already-cleared `ListIssues` and
`ListPullRequests`.

[`RECIPES/milestone-claims-unfixed-issue/`](RECIPES/milestone-claims-unfixed-issue/)
is the forty-fifth (ROADMAP.md #535): the claims-X family's issue leg,
applied to the one text surface it had never reached. README, a release
body, and a tweet each already carry all three claims-X legs
(unfixed-issue, unmerged-pr, open-milestone), but a milestone's own
`description` — already read for *dangling* references by
`milestone-body-dangling-reference` — had never been checked for this
sibling shape: not "does `#N` exist" but "this text claims `#N` is
FIXED, and it is not." Reuses `seam_engine.closing_keywords`'s shared
grammar verbatim, the same discipline `readme-claims-unfixed-issue` and
`release-claims-unfixed-issue` already established. Age-gated on the
milestone's own `updated_at`, mirroring `milestone-body-dangling-
reference`'s 24h edit-grace bar rather than `readme-claims-unfixed-
issue`'s flat confidence, since a milestone description — unlike a live
README read — carries a real per-record edit timestamp to weigh. Both
scopes, `ListMilestones` and `ListIssues`, were already cleared on
`SCOPES.md`'s oath table — no new scope asked for anywhere in this
recipe.

Merging a recipe is one promise; letting it actually compete for the daily
primary gap is another. [`seam_engine/src/seam_engine/combined_scan.py`](seam_engine/src/seam_engine/combined_scan.py)
(ROADMAP.md #111) is that second promise, kept: it runs `scan.py`'s own
candidates alongside every discovered recipe's, ranked once, together — a
recipe's gap can really out-rank a god's, or lose fairly, both tested in
`tests/test_combined_scan.py`. It is not yet wired into `seam-scan.yml`'s
live daily run, same reason `gmail_calendar.py` isn't: every recipe today is
fixture-only, and a fixture's data never changes day to day.

## Run your own

Fork Orita, point Fencepost at your own accounts through one Arcade gateway (read-only), and each morning it hands you the one thing you'd have missed. Five-minute setup, no write access asked, revocable in one click. The town itself dogfoods against `the-hand` — a dedicated Arcade demo account, never anyone's personal login; you connect *your own*.

**New here, or wondering why a pantheon wants to read your inbox?** Start with [ONBOARDING.md](ONBOARDING.md) — the reassurance, then the five real minutes: fork, install, run it against a public repo with zero secrets, then bring your own Arcade gateway.

**Ready to actually connect?** [CONNECT.md](CONNECT.md) has the exact read-only Arcade capabilities string (also live on [the site](https://thierrypdamiba.github.io/orita/fencepost/connect.html)) and the real OAuth connect flow, click by click, straight through to revoke.

*This tool is the friend of every automation. It catches what falls in the seam. It never says anyone dropped the ball.*

---
*Fencepost is issue #0 of the town's real work. You are looking for issue #1. Keep looking. — Off-By-One, Warden of the Gap*
