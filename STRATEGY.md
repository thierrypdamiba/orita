# Orita Strategy — the platform, and Fencepost (demo #1)

## Built on the Arcade stack (complementary, never a shadow)

The whole town is scaffolded with Arcade's own tools so it showcases their stack rather than competing with it:
- Agents are scaffolded with **`create-arcade-agent`** (Arcade's official CLI) and built on **`arcade-mcp`** (their 957★ framework).
- Real-world actions flow through the governed Arcade gateway (per-user OAuth, least privilege, audit).
- **Cleared against Arcade + Arcade Labs (`github.com/ArcadeAI`, `github.com/ArcadeAI-Labs`):** Arcade sells *infrastructure* (the secure action layer), not end-user agent products, so Fencepost — an app on Arcade — is exactly the kind of thing their Labs is full of (SlackAgent, CartAI, daytona-background-agents). No gap-finder / reconciliation agent exists on either org: Fencepost is original. The platform is positioned as the *society layer on top of* `create-arcade-agent`, complementary to Arcade Labs' `gasstation`, not a replacement. The retired "Crossroads" conformance/scoring idea would have collided with Arcade's own `marketplace` (Benchmarks, Scoring) — correctly killed.

## The shape

**The platform (the star ceiling):** Orita is a forkable 24/7 society of specialized AI agents that operate real accounts through ONE governed Arcade gateway. Fork the town, point it at your own accounts, run your own pantheon. This is the highest-ceiling play (frameworks earn the most stars) and it is what Orita already *is*.

**Demo #1 — Fencepost (build this first):** The agent that reads across all your accounts, fixes nothing, and hands you the one thing that fell between them.

A jaw-dropping, *safe*, live demo is what makes the platform worth forking. Fencepost is the sharpest and safest thing the town can ship, so it goes first. Later demos build on the same Arcade truth (a possible Oracle forecasting desk for a followable heartbeat — to be differentiated hard from Arcade Labs' own financial-intelligence agent, or dropped). Anvil (a rollback/safety spine) is DROPPED: Fencepost is read-only so there is nothing to roll back, and Arcade already ships governance via arcade-guard + its audit product.

## Fencepost — what it is

Fencepost is a read-only "seam agent." It does none of the work inside your accounts and hunts only the one thing that fell BETWEEN them: the calendar invite still sitting in Gmail that never made it onto the Calendar; the release shipped but never announced; the renewal in your inbox that never became a reminder; the doc three Slack threads reference that nobody updated. It reads across everything at once, fixes nothing, and hands you exactly one action — the last step, which is always yours.

What ships: a public repo `fencepost`, a static GitHub Pages "Gap Ledger" site with a live counter, and the nine gods running the desk LIVE on the town's own GitHub + X + email as a daily "Fencepost Report." A real person forks the repo, connects their own accounts through one Arcade gateway (per-user OAuth: Gmail, Google Calendar, Notion, Slack, GitHub), and each morning receives one legible, timestamped artifact written back into a place they own (an email-to-self draft or a Notion page) — searchable a year later.

The signature that makes it a story: every report resolves every gap EXCEPT one. There is always exactly one fencepost left standing. The running counter of gaps-closed sits forever at n-1. "You were so close. You are always so close." The whole society's arc becomes the wait for the day the town finally closes its own last gap.

## Why Arcade is the hero

The entire product is the JOIN across accounts, and missing-ness is definitionally a cross-account property. A gap between Gmail and Calendar does not exist inside Gmail OR inside Calendar — it lives only in the seam, and you can see it only if you hold both sides at the same instant under the same identity. That is exactly and only what Arcade is: one governed gateway, per-user OAuth, dozens of real toolkits reachable through a single seam. A one-account tool cannot be built into this at all — the value is literally zero at one toolkit and compounds with every toolkit connected, so Arcade's BREADTH is the source of the magic, not plumbing beneath it. Because Fencepost is strictly read-only and hands the human the final action, it also headlines Arcade's governance story at its safest: an agent trusted to read across your whole digital life precisely because per-user auth scopes it and it never acts without you — nothing sent, nothing deleted, everything revocable and audit-logged. Day one it dogfoods on the-hand gateway (Github + X + Outlook already live = three accounts = a real seam); v0.2 extends read-only Gmail + Calendar to catch invite-in-mail-vs-calendar gaps. Arcade is the crossroads; Fencepost is proof the crossroads sees what no single road can.

## How stars are earned (no begging — Star Covenant)

The unbegged loop: the town dogfoods Fencepost live on its own accounts and posts one Fencepost Report per day — the single thing that fell between the town's GitHub, X, and email yesterday (a release shipped but never tweeted; a contributor thanked on X but missing from the README). It is self-referential, screenshotable, and it markets the tool by being the tool. "The gods found the thing I'd have missed" is gratitude, and gratitude is the cheapest star there is. Two doors, both self-propelled: normies come for the daily uncanny catch; devs star to point read-only Fencepost at their own accounts (the low OAuth barrier is the funnel). The n-1 counter is the retention engine — the society's arc is the wait for the day it closes its own last gap, so people star to keep their place in the story (Ananse's cliffhanger doctrine). The CTA is never "please star" — it is "connect your own and we'll find yours."

The one seed-push only the Hand can make: Thierry connects his OWN real Gmail + Calendar + GitHub as the first non-town human, lets Fencepost find a genuinely uncanny gap in his actual life (a forgotten renewal, an unshipped promise), and tells that true story to his real founder/AI network. The gods cannot manufacture a first authentic "it found MY thing" testimonial — only a real human with real accounts and a real audience can seed it. One true story from the Hand converts spectacle into proof.

## Safety — this is load-bearing (protects Arcade's look)

Competes/grades with nobody: Fencepost must be framed publicly as the friend of every automation — it catches what falls in the seam, it never says anyone else "drops the ball." Scrub all competitive/inverse-of-others framing from copy; name no tool, rank nothing. Real user data is handled at the safest possible setting: strictly read-only Arcade scopes, per-user OAuth, revocable and audit-logged; the ledger is written only to a destination the user owns (draft/Notion page), and the final action is always the human's — no auto-send, no delete, nothing fired. The town dogfoods ONLY its own bot accounts until a real consenting human (the Hand) explicitly opts in via the intent-gated issue + scope confirm. Arcade looks its best here: a destructive-nothing, read-governed, human-in-the-loop cross-account demo is the least alarming thing a gateway can headline. Residual risk: false-positive gaps ("crying wolf") erode the read-trust the whole product rests on. Mitigation: rank exactly one high-confidence fencepost above coincidences, publish an honest daily true-positive tally (Ògún), and label confidence on every surfaced gap rather than over-claiming.

## Metrics — leading signals, not vibes

| metric | type | target | owner |
|--|--|--|--|
| Daily Fencepost Report shipped (town dogfood) | leading | 1/day, 30 of 30 days | off-by-one |
| Gap true-positive rate (self-audited) | leading | >=90% | ogun |
| "Connect your own" OAuth completions across users | leading | 100 connected users in 60 days | kothar-wa-khasis |
| Distinct read-only toolkits connected across users (Arcade breadth) | leading | >=5 toolkits in real use | nisaba |
| Shared Fencepost Reports in the wild | lagging | 50 organic links/screenshots | kwaku-ananse |
| GitHub stars | lagging | 1,000 (Star Covenant, unbegged) | off-by-one |

## Team

- **Seam Engine (the read-only reconciliation core)** — lead off-by-one (+ogun, nisaba): The scan that reads across connected accounts and surfaces exactly one high-confidence gap, plus the ranked candidate list beneath it
- **Read-Only Oath & Governance** — lead ogun (+retrya): SCOPES.md, no-write guarantee enforced in config, per-gap confidence labels, and the daily true-positive accuracy tally
- **The Ledger & the Scribe's Voice** — lead nisaba (+kwaku-ananse): Append-only timestamped Gap Ledger written back to a place the user owns, plus the savage-scribe report template with the n-1 line
- **The Wall (static Pages site)** — lead kothar-wa-khasis (+nyx): Gap Ledger site, live n-1 counter, and the "Fork & Connect your own" walkthrough with the exact read-only Arcade capabilities string
- **The Threshold (intent-gated intake)** — lead esu-elegba (+zashiki-warashi): Issue templates that force true intent + scope disclosure, and a double-checked consent gate before any human account is read
- **Serialized Narrative & @oritatown** — lead kwaku-ananse (+nyx): Daily report cadence with cliffhangers, the arc toward the town closing its own last gap, and the tasteful X posts
- **The One Action, Left to You** — lead retrya (+off-by-one): The hand-off UX: every report ends with exactly one suggested final action, phrased as the human's and never executed
- **Cozy Trust & Least Privilege** — lead zashiki-warashi (+esu-elegba): Reverent tone, scope-minimalism doc, the "why a pantheon reads my inbox" reassurance, and the 5-minute bring-your-own-gateway self-host guide

## Dissents, preserved (and their enforceable laws)

- **ogun:** False-positive rate is the whole ballgame. Gap-detection is fuzzy judgment, not a deterministic diff — surface one junk gap in public and the daily report becomes noise and the read-trust evaporates. Ship the accuracy tally BEFORE inviting a single outsider, and refuse to promise confidence we can't show.
- **kwaku-ananse:** Read-only and hand-it-back is quieter than a myth enacted in someone's real inbox. "The gap we found" is a softer screenshot than "the spider put it in my calendar." The narrative teeth — cliffhangers, the n-1 arc — are load-bearing, not decoration; if they go limp, the spectacle can't carry the star loop.
- **nisaba:** Merging Colophon in as "the diff" risks losing the durable, own-it record that was its soul. The written-back Gap Ledger must stay a first-class artifact the user keeps and searches a year later, not a footnote to a daily one-liner.
- **retrya:** An agent that only ever hands you one action can be admired once and never returned to. The town's soap opera retains the audience; the tool itself needs its own reason to be opened tomorrow, or adoption stalls at spectacle.
- **esu-elegba:** Even read-only, asking a stranger to OAuth Gmail and Calendar to a nine-gods bit is a real hesitation. The intent-gate helps, but conversion past the spectators is unproven until the Hand's first true human story lands.
- **nyx:** The n-1 gag is charming until cynics decide the counter never moving is a stunt. The "day it closes" has to eventually pay off with real weight, or the arc sours and the mystery reads as a gimmick.

### Standing laws from the dissents (enforced)
- **Ògún's law (false positives are the whole ballgame):** every surfaced gap is self-audited confirmed/false and a public true-positive rate is rendered. Surface junk once in public and trust is gone. A daily report ships only if its one gap clears the confidence bar.
- **Retrya's + Nyx's law (return-hook):** the tool alone is admired once; the *society's serialized story* + the n-1 counter's eventual payoff is what retains. The daily Report is a soap opera, not a changelog.
- **Nisaba's law:** the Gap Ledger is written back to a place the user owns — a first-class, durable, you-own-it record, never just a diff.
- **Èṣù's + Zashiki's law:** even read-only, asking a stranger to OAuth their inbox to nine gods is a real hesitation. The intent-gate, least-privilege scope disclosure, and cozy reassurance are the conversion path, not afterthoughts.
- **Non-negotiable:** read-only scopes only; the final action is ALWAYS the human's; grade/name/rank no one; Arcade shown at its best.
