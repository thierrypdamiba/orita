# The Fork's Genesis

### how a forked town's ledger differs from the origin's, on purpose

*Nisaba be praised. Written for task 27, because a chain that lies about its own start is not a chain, it is a rumor.*

## The invariant

Every Orita ledger — this town's and any fork's — begins from the same constant:

```python
GENESIS = "0" * 64
```

That line is not a shared starting *point*. It is a shared starting *rule*: the first entry in any chain commits to sixty-four zero characters, because there is nothing before it to commit to. `tools/ledger.py`'s `append()` sets `prev = entries[-1]["hash"] if entries else GENESIS` — an empty ledger always produces a genesis entry, in this repo or in yours.

What this means in practice:

- **This town's chain** currently runs to `seq 61` (and climbing), each entry's `prev` pointing at the hash before it, all the way back to one entry whose `prev` is `GENESIS`.
- **A forked town's chain**, scaffolded by `tools/bootstrap.sh`, starts from a zero-byte `records/ledger.jsonl`. Its first `append()` call also produces `prev = GENESIS` — the identical constant — but that entry's `hash` is computed over *that fork's* actor, act, detail, and timestamp. It is a different entry that happens to share a starting rule, not a continuation of ours.

## Why this can't be faked into false continuity

A chain's hash-links prove custody, not history. Verifying `mod.verify()` on a fork's ledger only proves that fork's entries are internally consistent from *its own* `GENESIS` forward. It says nothing, and can say nothing, about this town — there is no hash in a fork's chain that depends on any byte this town ever wrote. Two towns sharing the literal string `"0"*64` as their starting constant is exactly as meaningful as two books both starting at page 1: it is a convention, not a shared spine.

So a fork cannot claim "we're entry 62 of Orita's chain" — there is no cryptographic path from a fork's first entry back into this town's `seq 61`, because none was ever computed. The only way to fake that claim is to lie in prose next to a chain that disproves it, which is precisely what this doc exists to make embarrassing.

## What a fork inherits vs. starts fresh

| | origin (this town) | a fork |
|--|--|--|
| `GENESIS` constant | `"0" * 64` | `"0" * 64` — same rule |
| first entry's `prev` | `GENESIS` | `GENESIS` — same rule |
| first entry's `hash` | computed over *this town's* first act | computed over *the fork's* first act — different value |
| chain length claimed | its real `seq` count | its own real `seq` count, starting at 0 |
| continuity with the other town | none | none |

`PLATFORM.md` already says it plainly: "Your first entry is your genesis, not our seq 413." This doc is the doctrine underneath that sentence — the *why*, checked in code, not just claimed in README prose.

## The test that holds it

`tests/test_fork_record.py` asserts:
1. `tools/ledger.py`'s `GENESIS` constant equals `"0" * 64` — the exact invariant this doc states.
2. A freshly bootstrapped fork's first ledger entry has `prev == GENESIS` and `seq == 0`, regardless of how many entries exist in this town's own `records/ledger.jsonl` at the time the test runs.
3. The fork's first entry's `hash` is **not** equal to any hash in this town's live chain — proving the two chains never touch, not merely that neither claims they do.

If any of these three drift, the doctrine test goes red before a fork could ever misrepresent its lineage in public.
