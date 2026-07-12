# Gmail-vs-Calendar fixture (v0.2, WIP)

Stand-in data for `seam_engine.gmail_calendar`, shaped exactly like what
Arcade's read-only Gmail (`ListEmails`/`SearchThreads`) and Google Calendar
(`ListEvents`) toolkits return, per [`../../SCOPES.md`](../../SCOPES.md)'s
v0.2 row.

This exists because the-hand gateway does not yet carry Gmail/Calendar read
scopes, and the town has no demo Gmail account connected (ROADMAP.md #16).
`gmail.json` is six invite-shaped emails, `calendar.json` is one calendar
event — enough to exercise every branch of `compute_gaps`: a clean gap
(`msg-101`, no matching event), a matched invite that is correctly not a gap
(`msg-102` ↔ `evt-1`), a declined invite that is correctly excluded
(`msg-103`), two non-invite emails that never enter the pipeline at all
(`msg-104`, `msg-106`), and a second, lower-confidence gap
(`msg-105`, past-dated) that proves the ranker still elects exactly one
primary over a real contender.

Once the Hand extends the gateway with real read-only Gmail + Calendar
scopes and connects a dedicated demo account, `load_gmail_fixture` /
`load_calendar_fixture` in `gmail_calendar.py` are swapped for live
`ListEmails`/`ListEvents` calls. `compute_gaps` does not change — it is a
pure function of two already-typed lists, same shape as `compute_candidates`
in `scan.py`.
