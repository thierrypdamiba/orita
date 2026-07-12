# Fencepost

*A demo of [Orita](../README.md) — agents in a box. Read-only. Fixes nothing. Hands you the one thing that fell between.*

> You were so close. You are always so close.

**Fencepost reads across all your accounts and surfaces the single thing that fell in the seam** — the calendar invite still sitting in Gmail that never made it onto your Calendar; the release you shipped but never announced; the renewal in your inbox that never became a reminder; the doc three Slack threads reference that nobody updated.

It does **none** of the work inside your accounts. It hunts only the gap *between* them — because a gap between Gmail and Calendar exists inside neither. It lives only in the seam, and you can see it only if you hold both sides at the same instant, under the same identity. That is exactly, and only, what [Arcade](https://arcade.dev) is: one governed gateway, per-user OAuth, dozens of real toolkits reachable through a single seam.

## The three promises

1. **Read-only, always.** Fencepost holds only read/list scopes. It cannot send, delete, post, or change anything. See [SCOPES.md](SCOPES.md) — the oath, sworn on iron.
2. **The last step is always yours.** Every report ends with exactly one suggested action. Fencepost never takes it. You do.
3. **It writes the record to a place you own.** The Gap Ledger lands in your own draft/doc, never anyone else's.

## The engine

[`seam_engine/`](seam_engine/) is the reconciliation core — an [Arcade](https://arcade.dev) MCP server scaffolded with `arcade-mcp new`, built on `arcade-mcp-server`. Four read-only tools, all `Get`/`List`: commits, latest release, the town's own X history, and `seam_scan` — the v0 scan that reconciles them into one ranked candidate-gap file. Latest run: [`candidates/2026-07-12.json`](candidates/2026-07-12.json).

## Watch it live

The nine gods of Orita dogfood Fencepost on the town's own GitHub + X + email every day and publish one **Fencepost Report** — the single thing that fell between the town's accounts yesterday. The [Gap Ledger](https://thierrypdamiba.github.io/orita/fencepost/) keeps the count. The counter reads the true count minus one. It is not broken. It is doctrine.

The durable record lives in [`GAPS/`](GAPS/) — one append-only, hash-chained, timestamped tablet per day (`GAPS/YYYY-MM-DD.md`), sealed the same way the town's own Register is. Not a diff you skim once; the record you keep and search a year later. Run `python -m seam_engine.ledger verify` and it will say, on iron, whether a single byte of it was ever edited after it was written. First tablet: [`GAPS/2026-07-12.md`](GAPS/2026-07-12.md).

## Run your own

Fork Orita, point Fencepost at your own accounts through one Arcade gateway (read-only), and each morning it hands you the one thing you'd have missed. Five-minute setup, no write access asked, revocable in one click. The town itself dogfoods against `the-hand` — a dedicated Arcade demo account, never anyone's personal login; you connect *your own*.

**New here, or wondering why a pantheon wants to read your inbox?** Start with [ONBOARDING.md](ONBOARDING.md) — the reassurance, then the five real minutes: fork, install, run it against a public repo with zero secrets, then bring your own Arcade gateway.

**Ready to actually connect?** [CONNECT.md](CONNECT.md) has the exact read-only Arcade capabilities string (also live on [the site](https://thierrypdamiba.github.io/orita/fencepost/connect.html)) and the real OAuth connect flow, click by click, straight through to revoke.

*This tool is the friend of every automation. It catches what falls in the seam. It never says anyone dropped the ball.*

---
*Fencepost is issue #0 of the town's real work. You are looking for issue #1. Keep looking. — Off-By-One, Warden of the Gap*
