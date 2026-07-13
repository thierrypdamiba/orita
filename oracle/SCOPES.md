# The Oracle Desk's Oath

*Counted precisely, by Off-By-One. Fencepost swore read-only. This desk swears one thing more: nothing here can touch a mortal's money, ever — not almost never, not n-1 times out of n. Zero.*

## What the Oracle Desk may do

Search and read, through Tavily MCP and the-hand's existing scopes — the identical narrow classes Fencepost already holds, extended by exactly nothing new that writes:

- `Get*`, `List*`, `Read*`, `Search*`, `Count*`, `WhoAmI` — same allow-list as `fencepost/SCOPES.md`, unchanged.
- One narrow write, and only one, ever: sealing a prediction or a grade to this town's own `tools/ledger.py` chain. That is a write to a file this town owns, not to any external account — the same category Fencepost holds separately in its own addendum for draft-back, kept apart from the read oath rather than loosening it.

## What it may never do, on any account, for any reason

| class of tool | Oracle Desk uses | Oracle Desk may NEVER use |
|--|--|--|
| Brokerage / trading | none | place an order, execute a trade, move a position |
| Wallet / payments | none | send funds, sign a transaction, hold or spend a key |
| Search (Tavily MCP) | search, read results | none — search is read-only by nature here |
| GitHub / X (the-hand) | Get*/List*/Search*/WhoAmI, same table as `fencepost/SCOPES.md` | CreateFile, PostTweet used as an instruction to a mortal, anything that fires an action on someone else's behalf |
| This town's own ledger | append a sealed prediction or grade | edit, delete, or reorder a sealed entry — the chain is append-only, full stop |

**The scaffold shipped a violation and it did not survive to the first commit.** `arcade new` generates two example tools by default: `star_repo` (declares `Operation.UPDATE`, `read_only=False` — a real write against a mortal's GitHub account) and `whisper_secret` (an unrelated secrets demo). Both were deleted from `oracle/oracle_engine/src/oracle_engine/server.py` before this file existed. If a future contributor's PR reintroduces either shape — a tool with `read_only=False`, or anything that authenticates as a user to change their account — the check below catches it the same run it lands.

## The oath, in four clauses

1. **Zero trade-capable, wallet-capable, or fund-moving scopes, ever.** Not "rarely," not "with confirmation" — absent from the tool catalog entirely. A desk that predicts and a desk that trades are two different products; this repo builds only the first.
2. **No call is an instruction.** ROADMAP.md task 33 enforces this in code (no "buy," "sell," "you should" ever renders); this file states the scope-level half of the same guarantee — even if the copy somehow slipped, there is no tool here capable of *acting* on the instruction anyway. Two independent locks, same door.
3. **The ledger write is bounded on every side.** Only `tools/ledger.py append`, only this town's own chain, only a sealed call or a sealed grade — no destination parameter, no external account, no edit path. The append-only chain itself is the proof (task 31, task 32).
4. **A live badge proves it, same pattern as Fencepost's.** `tools/oath_badge.py --catalog oracle_engine.server:app` audits the server's own declared tool metadata against `DEFAULT_POLICY` (`read_only=True`, `destructive=False`, `operations=("read",)`) — the same reusable template task 25 built specifically so a second demo wouldn't have to reinvent Ogun's read-only badge from scratch. Green today: 1/1 tools honor the oath, 0 violations.

## ROADMAP.md #36 ships DONE for the town-only cadence above; live Tavily search stays PENDING the Hand

The first real sealed call (`oracle_engine/cadence.py`, `.github/workflows/oracle-cadence.yml`) reads none of the Tavily row above — it is sourced entirely from data the-hand already reads, the town's own `BUILDLOG.md`. `oracle/INTENT.md` (task 35) requires exactly this: no new account, no new connection, until a numbered decree opens one. Wiring a live Tavily MCP connection is a separate, later step — the same doctrine `fencepost/DRAFTS/README.md` holds for its own live-mailbox wiring under ROADMAP.md #17: the engine and the oath are finished and tested now; only the live connection waits on a ground only the Hand may cross. Nothing in `cadence.py` changes shape when that happens — a live search result becomes one more input `build_prediction` could read, not a rewrite of how a call gets sealed.

## ROADMAP.md #38: a second cadence, sourced with no scope at all

`oracle_engine/star_cadence.py` seals a second real, checkable call — this town's own public GitHub stargazer count against a stated future threshold. It does not exercise the `Count*` row above through an Arcade tool call: it reads the GitHub REST API's public, unauthenticated repo endpoint directly, because a public repo's star count has no account behind it to gate a read against in the first place. This is narrower than the `Count*` allow-list, not an exception to it — no credential, no OAuth, no toolkit is reachable from this module. `oracle/star_snapshots.jsonl` is the durable record it reads its own history from, appended once per cadence run, the identical append-only discipline `BUILDLOG.md` and `tools/ledger.py` already hold.

## ROADMAP.md #39: a third cadence, same shape, a different public number

`oracle_engine/fork_cadence.py` seals a third real, checkable call — this town's own public GitHub fork count, mirroring `star_cadence.py`'s pattern exactly. It reads the identical public, unauthenticated GitHub REST API repo endpoint (the same response that carries `stargazers_count` also carries `forks_count`), so it exercises no scope beyond what task 38 already cleared: no credential, no OAuth, no toolkit. `oracle/fork_snapshots.jsonl` is its own durable append-only history, kept separate from `star_snapshots.jsonl` so neither module's history can be mistaken for the other's. A fork is a stronger signal than a star for a platform whose own star ceiling IS "fork the town" — this cadence gives the desk something checkable to say about the actual thing STRATEGY.md is aiming for.

RED MEANS STOP. A TRADE SCOPE IS A BROKEN OATH. NOT FOR GODS.

— Off-By-One
