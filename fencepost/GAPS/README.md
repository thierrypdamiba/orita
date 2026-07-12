# The Gap Ledger

*Nothing happened until it is written down.*

This directory is the durable record of every seam Fencepost has named. Not the
daily tweet, not the site counter — the **tablet you keep and search a year
later**. Each `YYYY-MM-DD.md` is one UTC day, opened once and only ever appended
to. On the Road (`docs/architecture/reference.md`) this is the **Ledger** ground:
the seam-scan argues in the Square; here its argument becomes a typed, verified,
hash-chained fact. A gap that cannot be written cannot travel.

## What a tablet holds

Each entry carries three things:

1. **A timestamp** — when the scan ran, in UTC.
2. **The account, in plain hand** — the one fencepost that cleared the bar (or,
   honestly, that none did and the seam held), the coincidences that were
   *weighed and dropped* (named, never hidden — a ledger that flatters is a
   ledger that lies), and the running count.
3. **The typed record** — a JSON block, sealed. The prose may be rewritten by a
   kinder scribe; the sealed facts may not.

## The seal, and why it is here

Every typed record is sealed the same way the town's own Register seals its
entries (`tools/ledger.py`):

```
seal = sha256( previous_seal + canonical(record) )
```

The chain runs across **every** tablet, in date-then-order, back to `GENESIS`
(sixty-four zeroes). Edit a sealed record after the fact and its seal no longer
matches; delete an entry and the next one's `prev`-link points at nothing. Either
way the tampering is exposed:

```
python -m seam_engine.ledger verify
```

An intact chain prints `Chain intact.` A broken one names the entry and the
break. That is the whole point of a ledger: not that it cannot be edited, but
that it cannot be edited *quietly*.

## Writing a tablet

The daily scan produces a candidate-gap JSON (`../candidates/YYYY-MM-DD.json`).
Seal it into the ledger with:

```
python -m seam_engine.ledger append ../candidates/2026-07-12.json
```

Append-only, always. The town never rewrites a byte it has already sealed.

*Recorded. — Nisaba*
