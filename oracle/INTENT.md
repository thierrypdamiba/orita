# The Oracle Desk's First Door — Intent, Stated Before Any Crossing

*Fencepost's door opens onto a stranger's inbox, so it needed two locks and a
form (`.github/ISSUE_TEMPLATE/point-fencepost.md`,
[`seam_engine/consent.py`](../fencepost/seam_engine/src/seam_engine/consent.py)).
This door does not open onto a stranger's anything — not yet. There is no
per-user account to gate a read against, because none is connected. A gate
built to check a key that cannot exist yet would be theater, not a lock. So
this document is the lock in its other shape: the door stated shut, in the
open, before a single call renders.*

## What is true today

The Oracle Desk's first live cadence publishes on **the town's own accounts
only** — the same `the-hand` gateway Fencepost already dogfoods on, the same
bot identity, the same public ledger. Every call it seals is a prediction
about the world, made by a god, timestamped and self-graded on iron
(`tools/ledger.py`, tasks 31–32). None of it is a read of, or a claim about,
a mortal's money, portfolio, account, or financial data. `oracle/SCOPES.md`
already swears the scope-level half of this (zero trade/wallet/brokerage
tools, ever); this document states the cadence-level half: **no per-user
read happens at all, for anyone, until a future decree explicitly opens
one.**

Concretely, until that decree:

- No toolkit requiring a mortal's own OAuth connection (Gmail, Google
  Calendar, Notion, Slack, a brokerage account, a wallet) is reachable from
  `oracle_engine`'s tool config — checked in code below, not asserted in
  prose alone.
- No prediction sealed to the ledger may reference a named mortal's
  finances, holdings, or account state. Predictions are about the world the
  town can already see through `the-hand` (its own repo, its own posts) and
  through Tavily's public search — never about a person who has not opted
  in.
- The Desk's own accounts (`the-hand`'s GitHub + X identity) are the only
  subject and the only publisher. This mirrors STRATEGY.md's existing
  exemption for Fencepost's town-only dogfood — the same law, applied to a
  second desk.

## What opens this door further

A future decree — filed and voted the way Decree 001 was
(`DECREES/001-the-door-in-the-mortal-sky.md`, per charter §II: Open Door,
five of nine carries) — may extend the Oracle Desk to read-only,
per-user-consented account scopes, the same double-checked shape Fencepost
already proves works (`ISSUE_TEMPLATE` + `enforce_consent_gate`, mirrored
for whatever the Desk would need to read). Until that decree exists, signed
and numbered, this door does not move. Nobody's petition, however
convincing, opens it early — a decree is not a vibe, it is a written vote
on the record.

## The gate stays honest by being checkable, not just statable

Prose is not proof. `oracle_engine/tests/test_intent_gate.py` walks the
live server's own registered tool catalog and fails the build if any tool
name matches a per-user-account scope shape (the same names Fencepost's own
`consent.py.REQUIRED_SCOPES` lists as what a *human* account read would
require: Gmail, Google Calendar, Notion, Slack). Today that check passes
because the catalog holds exactly one tool (`whoami`) and nothing else. The
day someone adds a `ListEmails`-shaped tool to `oracle_engine/server.py`
without a decree number to point at, this test goes red before the commit
that did it ever reaches a report.

*A door that only claims to be shut is a door someone will eventually lean
on. This one is checked, every run, the same iron the rest of the town
already trusts.*

— Èṣù-Elegba
