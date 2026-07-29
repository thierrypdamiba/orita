# Fencepost

[![read-only · zero actions fired](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fthierrypdamiba%2Forita%2Fmain%2Ffencepost%2FBADGE.json)](BADGE.json)

*A demo of [Orita](../README.md) — agents in a box. Read-only. Fixes nothing. Hands you the one thing that fell between.*

> You were so close. You are always so close.

**Fencepost reads across all your accounts and surfaces the single thing that fell in the seam** — the calendar invite still sitting in Gmail that never made it onto your Calendar; the release you shipped but never announced; the renewal in your inbox that never became a reminder; the doc three Slack threads reference that nobody updated.

It does **none** of the work inside your accounts. It hunts only the gap *between* them — because a gap between Gmail and Calendar exists inside neither. It lives only in the seam, and you can see it only if you hold both sides at the same instant, under the same identity. That is exactly, and only, what [Arcade](https://arcade.dev) is: one governed gateway, per-user OAuth, dozens of real toolkits reachable through a single seam.

## The three promises

1. **Read-only, always.** Fencepost holds only read/list scopes. It cannot send, delete, post, or change anything. See [SCOPES.md](SCOPES.md) — the oath, sworn on iron. The badge above is not a sticker: [`seam_engine/badge.py`](seam_engine/badge.py) introspects the *actual* live MCP server's own tool catalog (`seam_engine.server`) — every tool's own declared `read_only`/`destructive`/`operations`, read straight off the registered object, not a claim about it — and cross-checks the real, hash-chained Ledger's tamper seal. Either check finding one violation flips it red, named, the same run it happens; there is no code path that hides one behind green (`seam_engine/tests/test_badge.py`). `python -m seam_engine.badge --write` regenerates [`BADGE.json`](BADGE.json) after every real daily run, the same as `AUDIT.md` — a live [shields.io endpoint badge](https://shields.io/badges/endpoint-badge), so the image repaints from whatever the last real run actually found, never a static asset checked in once and forgotten.
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
