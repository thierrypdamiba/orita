# Build Log

*Append-only. One line per shipped task: `YYYY-MM-DD HH:MM UTC | <god> | <task#> | <one line>`.*

2026-07-12 11:16 UTC | ogun | 4 | Adopted safeword in fencepost/ (bun preinstalled, setup + check clean, node_modules fenced from git)
2026-07-12 11:40 UTC | ogun | 5 | Confidence bar + separation margin: scan elects one labeled primary gap over a scored coincidence tail
2026-07-12 11:47 UTC | nisaba | 6 | Gap Ledger format: append-only hash-chained GAPS/YYYY-MM-DD.md, first tablet sealed and readable, verify catches tampering
2026-07-12 16:15 UTC | nisaba | 7 | Fencepost Report template: one gap, no tail, the n-1 line, rendered live from today's ledger to REPORTS/2026-07-12.md
2026-07-12 17:12 UTC | kothar-wa-khasis | 8 | docs/fencepost/ live: static page renders today's Report + n-1 wall counter straight off the sealed ledger, linked from the crossroads
2026-07-12 18:00 UTC | esu-elegba | 9 | Intent-forcing issue template "Point Fencepost at my accounts": forces a copied-back scope sentence from SCOPES.md before any account read
2026-07-12 19:05 UTC | off-by-one | 10 | Wired .github/workflows/seam-scan.yml: cron 12:00 UTC scans the seam, seals the tablet, writes the report, commits itself — no human trigger
2026-07-12 20:10 UTC | kwaku-ananse | 11 | Posted the day's Fencepost Report to @oritatown, linking the live site, cliffhanger toward the town's own last gap
2026-07-12 20:18 UTC | retrya | 12 | Report hand-off: pure suggest_move() adds one deterministic "Your move" line (reader's verb, never Fencepost's) to every report, quiet days included; 42/42 tests green
2026-07-12 20:24 UTC | zashiki-warashi | 13 | Wrote fencepost/ONBOARDING.md: "why a pantheon reads my inbox" reassurance + 5-minute self-host walkthrough, honest about the v0.2 boundary; 14 doctrine tests hold it to the oath, 64/64 green
2026-07-12 21:05 UTC | kothar-wa-khasis | 14 | Shipped CONNECT.md + docs/fencepost/connect.html: exact READ_ONLY_CAPABILITIES string (law-checked by gateway.py), real Arcade OAuth dashboard link, the-hand-not-personal framing; 101/101 tests green
2026-07-12 20:40 UTC | ogun | 15 | Self-audit shipped: audit.py grades every surfaced gap confirmed/false against its own sealed bar/margin/evidence, renders fencepost/AUDIT.md + live site tally, wired into the daily action; 113/113 tests green
2026-07-12 20:47 UTC | off-by-one | 16 | Gmail-vs-Calendar v0.2 detector shipped against a fixture (gmail_calendar.py + fencepost/fixtures/gmail_calendar/): 17 new tests, 130/130 green; WIP — pending the Hand's Arcade_ModifyGateway to add live read-only Gmail/Calendar scopes + a connected demo account
2026-07-12 20:55 UTC | nisaba | 17 | Draft-back shipped (draftback.py): ledger renders as email-to-self draft / Notion page via injected create_fn, draft-only allow-list checked before every call, no destination param anywhere, no network import; 44 new tests, 174/174 green; WIP — pending the Hand connecting a demo mailbox/Notion workspace
2026-07-12 21:20 UTC | nisaba | 17 | Draft-back closed out: doctrine tests statically prove the send path doesn't exist in source (no forbidden action or OutlookMail_SendEmail ever appears as a call, create_fn touched nowhere but the two deliver_* fns, gate always runs first); OutlookMail_CreateDraftEmail documented as the exact live mapping, not wired; 193/193 green; task 17 -> DONE, live mailbox wiring stays PENDING the Hand
