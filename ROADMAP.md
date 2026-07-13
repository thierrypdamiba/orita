# Orita Roadmap — Fencepost (demo #1 of the platform)

> The agent that reads across all your accounts, fixes nothing, and hands you the one thing that fell between them.

**The town's work queue. The loop pulls the next `TODO` in order, ships it as the owner god, marks it `DONE`. No idle cycles. Built inside this repo under `fencepost/` so the town's own repo earns the stars.**

## Non-negotiable design constraints (from the Hand)
1. **Read-only.** Only read/list Arcade scopes. Fencepost fixes nothing; the final action is always the human's.
2. **No grading/competing.** Friend of every automation; it catches what falls in the seam, never says anyone "drops the ball." Name and rank no one.
3. **False positives are fatal.** Every gap self-audited; public true-positive rate rendered; a report ships only if its one gap clears the confidence bar (Ògún's law).
4. **Arcade is the hero, shown safely** — per-user OAuth, least privilege, revocable, audit-logged. This protects Arcade's look; treat it as the point.
5. **Written back to a place the user owns.** The Gap Ledger is a durable record, not a diff.

## Backlog

| # | status | owner | task | done when |
|--:|:--|:--|:--|:--|
| 1 | DONE | off-by-one | Create public repo `fencepost` with a README stating the read-only seam premise and the n-1 signature | Repo exists on GitHub with README rendering the premise |
| 2 | DONE | ogun | Write the read-only oath: SCOPES.md listing only read/list Arcade tools used, with an explicit no-write guarantee | SCOPES.md committed and no write-capable tool appears in the agent config |
| 3 | DONE | off-by-one | Scaffold the Fencepost agent with `npx create-arcade-agent` (Arcade's own CLI) and build the engine on `arcade-mcp`; then implement seam-scan v0 over the-hand: reconcile yesterday's X posts vs GitHub commits/issues/releases into a candidate gap list | A scan run produces a ranked candidate-gap file |
| 4 | DONE | ogun | Adopt `safeword` (best-effort, MUST NOT block the build): if `bun` is absent, install it (`curl -fsSL https://bun.sh/install | bash`) then run `bunx safeword@latest setup` in the repo; commit `.safeword/` + `AGENTS.md`. If safeword genuinely cannot run in this ephemeral env after ONE real attempt (no bun, no network, needs interactivity), write the reason to orita-vault/hand/skipped.md and mark this task **DONE** anyway so the Fencepost build is never blocked by tooling. Install the published CLI only; never fork its source (no license). | Either `.safeword/` is committed, OR skipped.md explains why and the task is marked DONE. The loop NEVER stalls on this task. |
| 5 | DONE | ogun | Add confidence ranking so exactly one high-confidence fencepost surfaces above the coincidences | Scan emits one labeled primary gap plus a confidence-scored tail |
| 6 | DONE | nisaba | Build the Gap Ledger format: append-only, timestamped GAPS/YYYY-MM-DD.md committed to the repo | First tablet committed and readable |
| 7 | DONE | nisaba | Write the report voice and template (savage-scribe, one gap, the "you were so close" n-1 line) | Template renders a real report from a live scan |
| 8 | DONE | kothar-wa-khasis | Stand up the static Pages site rendering the Gap Ledger plus a live n-1 counter | Site is live and shows the latest report and counter |
| 9 | DONE | esu-elegba | Create intent-forcing issue templates: "Point Fencepost at my accounts" with scope disclosure | Templates merged and selectable when opening an issue |
| 10 | DONE | off-by-one | Wire the daily scheduled GitHub Action to run the seam-scan and commit the report at a fixed hour | Action runs green and commits a report automatically, no human trigger |
| 11 | DONE | kwaku-ananse | Post the day's Fencepost Report to @oritatown with a cliffhanger toward the town's own last gap | Tweet posted via the X tool linking the report |
| 12 | DONE | retrya | Implement the single hand-off: every report ends with exactly one suggested final action, phrased as the human's, never executed | Report always contains one "your move" line and zero actions are ever fired |
| 13 | DONE | zashiki-warashi | Write onboarding + "why a pantheon reads my inbox" reassurance + 5-minute bring-your-own-gateway self-host guide | Guide committed to the repo |
| 14 | DONE | kothar-wa-khasis | Add the "Fork & Connect your own" walkthrough with the exact read-only Arcade capabilities string and OAuth connect link | Walkthrough on the site links straight to the Arcade OAuth connect flow |
| 15 | DONE | ogun | Add the daily self-audit: label each surfaced gap confirmed/false and render a public true-positive tally | A public accuracy tally updates on the site each day |
| 16 | DONE | off-by-one | Add the Gmail-vs-Calendar seam detector (fixture-driven, MOCK ONLY — `fencepost/fixtures/gmail_calendar/`) and wire it into ranking so it competes for the single primary gap under the existing confidence bar; extending the real gateway (`Arcade_ModifyGateway` for read-only Gmail + Calendar scopes, plus a connected demo account) is recorded as an explicit PENDING step in SCOPES.md, not performed | A Gmail-vs-Calendar gap is detected in a fixture-driven dogfood run, proven by a test |
| 17 | DONE | nisaba | Ship the "written back to a place you own" path: deliver the ledger as an email-to-self draft or a Notion page (local preview, MOCK ONLY — `fencepost/DRAFTS/`), with `deliver_email_draft`'s live mapping onto the-hand's `OutlookMail_CreateDraftEmail` documented (never `OutlookMail_SendEmail`, statically proven absent from the source); connecting a live mailbox/Notion workspace as the `create_fn` is recorded as an explicit PENDING step in `DRAFTS/README.md`/SCOPES.md, waiting on the Hand, not performed | A ledger lands in an owned destination as a draft, nothing auto-sent |
| 18 | DONE | nyx | Design the narrative arc and counter mechanics so the society's story is the wait for the day it closes its own last gap | Site copy and counter reflect the arc and hold honestly at n-1 |
| 19 | DONE-MACHINERY · the seven-day count completes only via the daily routine (`.github/workflows/seam-scan.yml`, cron `0 12 * * *`, no UTC day skipped) — nothing left to build, only calendar time; check progress any day with `python -m seam_engine.streak status` | kwaku-ananse | Serialize: sustain the daily cadence with recurring gaps, each report an ad for "connect your own" | Seven consecutive daily reports posted |
| 20 | DONE | esu-elegba | Add the double-checked consent flow: public issue plus explicit scope confirm before any human account is read | Consent gate blocks all reads until the human confirms scopes |
| 21 | DONE | off-by-one | Enforce the counter stuck at n-1 plus the "day it closes" teaser | Counter never reaches n and the teaser renders on the site |
| 22 | DONE | nisaba | Write CONTRIBUTING for community-submitted seam recipes (gap detectors), gated by the read-only oath | A first external recipe PR is mergeable under the oath |
| 23 | DONE | ogun | Add a live "read-only, zero actions fired" badge to the README that repaints from real runs | Badge shows live zero-writes from actual runs |

*When Fencepost v1 is DONE and dogfooding daily, the leads extend the backlog toward the platform (fork-your-own-society scaffold) and demo #2 (Oracle Desk). The build never stops.*

## Platform Backlog — Fork-Your-Own-Society Scaffold

Fencepost v1 (tasks 1-23) is shipped; task 19's seven-day streak completes on calendar time alone. Per STRATEGY.md's "star ceiling," the town now builds toward the platform itself: fork the town, point it at your own accounts, run your own pantheon. Same non-negotiables carry over where they apply (no cross-peek into another town's vault; a fork's Iron Rules are its own to write, not inherited as content — only the *mechanism* for enforcing them is).

| # | status | owner | task | done when |
|--:|:--|:--|:--|:--|
| 24 | DONE | off-by-one | Write `PLATFORM.md`: the fork-your-own-society premise, counted precisely (what's town-specific and must be renamed, what's mechanism and travels free). Ship `tools/bootstrap.sh <target-dir>`: scaffolds a fresh, content-free pantheon skeleton (empty `houses/<slug>/{journal,altar}` dirs with stub READMEs, a fresh zero-entry ledger, template `ROADMAP.md`/`BUILDLOG.md`/`STRATEGY.md` headers) into a target directory — no Orita lore copied, no shared ledger history (a fork's chain starts at its own genesis, always). | `tools/bootstrap.sh` run against a scratch directory produces a valid, empty skeleton with its own zero-entry ledger, proven by a test |
| 25 | DONE | kothar-wa-khasis | Extract the read-only-badge pattern (task 23) into a reusable `tools/oath_badge.py` template: audits a live MCP server's own tool metadata against a declared scope list, so any fork can prove its own non-negotiables in code, not just in docs | A test proves the template flips red when a write-scope tool is spliced into a fixture server, green otherwise |
| 26 | WIP (2026-07-13 02:00 UTC) | esu-elegba | Add a platform-level intent-gate issue template (`.github/ISSUE_TEMPLATE/fork-my-own-society.md`) mirroring Fencepost's consent gate: forces a forker to state which accounts/scopes their OWN gateway will touch before any bootstrap instructions are handed over | Template merged and selectable when opening an issue |
| 27 | TODO | nisaba | Write `docs/architecture/fork-record.md`: how a forked town's ledger genesis differs from the origin town's (fresh hash-chain, no shared lineage, no claim of continuity) so forks can't misrepresent their history | Doc committed; a doctrine test asserts `tools/ledger.py`'s genesis constant matches the doc's stated invariant |
| 28 | TODO | kwaku-ananse | Draft `docs/oracle-desk.md`: the demo #2 premise (a followable forecasting heartbeat built on the SAME public primitives as Arcade Labs' financial-intelligence demo — Tavily MCP + Arcade — never forked from its unlicensed source) plus autonomous timestamped predictions, hash-chained self-scoring, non-advice-shaped copy | Doc committed; reviewed line-by-line against STRATEGY.md's Oracle Desk paragraph for zero license/composition violations |
| 29 | TODO | zashiki-warashi | Write the fork's onboarding reassurance doc: why running your own pantheon on your own accounts is safe by construction (per-user Arcade OAuth, the oath-badge from task 25, least-privilege defaults) — companion piece to Fencepost's ONBOARDING.md but for the whole platform | Doc committed to the repo, linked from PLATFORM.md |

*Oracle Desk (demo #2) does not begin real engine work until the platform scaffold (24-27) is usable end-to-end — a second demo on an unforkable platform is a dead end.*
