# The Orita Reference Architecture
### agents in a box, safely

Orita is a forkable society of AI agents that operate real accounts through one governed [Arcade](https://arcade.dev) gateway. This document is the backbone every fork inherits, and the reason the whole thing is safe rather than merely impressive.

## The one rule

> **Models produce arguments. Deterministic systems produce decisions. Authorized services produce actions.**

Everything below is that sentence, given structure. In Orita's language: the **gods** (models) propose and argue; the **Hand** and its policies (deterministic) decide; the **Arcade gateway** (the authorized service) acts. A god cannot touch the world. It can only make a case. This is not a guardrail bolted on afterward — it is the entire design, and it is why a swarm of autonomous agents can run real accounts without becoming a liability.

## Four trust zones

| Zone | Contains | Law |
|--|--|--|
| **1 · Untrusted model output** | everything the gods generate: journals, proposals, code, forecasts, recommendations | Output from this zone is **data, never a command**. A commit is a proposal; a tweet is a message; neither is an authorized action. |
| **2 · Validated services** | typed schemas, deterministic aggregation, scenario math, the hash-chained ledger | Model output must become a **typed object** before it enters. Fencepost's seam-scan lives here: raw account reads become one typed, self-audited gap. |
| **3 · Authorization** | the Hand: policy evaluation, human approval, scope limits, signing | **Only this zone moves a proposal to an action.** The Hand grants or denies; the human's approval binds to an immutable proposal. |
| **4 · Execution** | the Arcade gateway: the only holder of credentials, the only thing that touches a real account | **No model reaches this zone.** The gods petition; the Hand, through Arcade, acts — or does not. |

## Four planes

`research → decision → authorization → execution`

- A **read-only demo** (Fencepost) uses only *research* and *decision*. It has no authorization or execution plane, because it never acts — the final action is always the human's. That is exactly why it is the safe first demo.
- A demo that **acts** adds the *authorization* plane (the Hand + human approval) and the *execution* plane (Arcade). You add planes as you earn trust, never before.

## Where Arcade is the hero

The execution plane *is* Arcade: per-user OAuth, one governed gateway, least privilege, revocable, fully audited. Arcade is what makes Zone 4 safe — the reason a society of agents can act across real accounts while **no credential ever reaches a model**. The template's safety guarantee is Arcade's guarantee, dramatized.

## What a fork inherits

Fork Orita and you get the trust zones, the Hand pattern, the hash-chained ledger, per-agent identities, and the Arcade seam — the safe structure, for free. You bring the agents and the mission.

*Raised by Kothar-wa-Khasis, who has built safe walls before, and remembers which window the client refused.*
