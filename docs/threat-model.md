# Threat Model — what this architecture prevents

Impressive multi-agent demos fail in predictable, dangerous ways, and audits of real systems find the same wounds every time: credentials committed to source, model text becoming a live order, a default password on the message bus that carries trade instructions. Orita's architecture exists to make these failures **structurally impossible**, not merely discouraged.

## The anti-patterns, and the wall against each

| The failure | Where it comes from | How Orita prevents it |
|--|--|--|
| Committed credentials / secrets in source | convenience, no secret hygiene | No credential ever lives in the repo. All auth is per-user OAuth held by **Arcade**, never by a god or the code. |
| LLM output becomes a live action | free-form model text reaching an execution API | Zone boundary: model output is **data**. Only a typed, validated proposal, authorized in Zone 3, can become an action. |
| Model-generated SQL / shell | string-interpolated model output hitting a database | No god writes to production state. **Typed objects only**; deterministic services own all mutation. |
| State mutates with no real auth | an `operatorId` in a request body treated as identity | Authorization is a **separate service** (the Hand), never a frontend flag or a body string. Approval and execution are separate services. |
| An agent holds execution credentials | one process does research *and* acts | The gods cannot reach Zone 4. Only **Arcade** holds credentials; the gods petition. |
| No idempotency / duplicate actions | retrying a state-changing call | Every state-changing act carries an **idempotency key**; the ledger is append-only and hash-chained. |
| Unsafe model deserialization | `pickle.load` on an agent-supplied path | Signed artifacts / safe formats only; validation checks **content**, not just a file extension. |
| Stale data / placeholder values become actions | fail-open on missing inputs | **Fail closed.** A read-only demo never acts; an acting demo hard-caps and rejects missing inputs before any action path. |

## The agent-task contract (how the gods build)

Every god, on every task, operates under a fixed contract:

**A god MAY:** read, edit code, run tests, commit, open a proposal.
**A god MAY NOT:** merge its own work, deploy, approve a schema change, access production credentials, or change policy without review.

Enforced by four independent things, so no single failure lets an agent slip the leash:
1. **Per-god commit identities** — who did what is always on the record.
2. **safeword** — test-first quality gates that fire during agent sessions (Ògún's merge-law, made executable).
3. **the Hand** — the only entity that can authorize a real-world action.
4. **the human** — the final action is always theirs.

## The rule, once more

*Models produce arguments. Deterministic systems produce decisions. Authorized services produce actions.* Keep those three apart, and a multi-agent demo becomes a system that can be trusted near real consequences.

*Kept by Ògún. The gate holds or nothing passes. Sworn on iron.*
