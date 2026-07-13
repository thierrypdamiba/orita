# The Oracle Desk

### demo #2's premise, told once, so nobody has to guess at it twice

*Kwaku Ananse begins this the way every good bargain begins: by naming exactly what he is not stealing.*

Nyame once set a price for every story on Earth, and I paid it. I did not steal the stories that already had owners — I brought Nyame something nobody else had. That is the whole shape of this doc. Somewhere out past this repo, Arcade Labs already runs a fine financial-intelligence demo, built on Tavily MCP plus Arcade. It is public to look at. It is not public to take — no license sits on it, and unlicensed means all rights reserved, full stop. So here is the one flagged lie I am required to tell in every telling, dealt with early: I will *not* say we admired that demo from a respectful distance. We admired it from a *very* close distance, read every public line we're allowed to read, and then built our own thing on the same two public primitives it stands on. That is not the same act, and this document exists to keep it that way in practice, not just in prose.

## What the Oracle Desk is

A followable heartbeat: the pantheon makes public, timestamped predictions on a cadence, and the town's own hash-chained ledger — the same one that seals every Gap Ledger tablet — seals the call the moment it's made, and seals the scoring the moment the outcome is known. Nobody edits a prediction after the fact. Nobody quietly deletes a bad call. The chain that already stops Fencepost from padding its own true-positive tally is the same chain that stops the Oracle Desk from padding its own track record. One ledger, two demos, the same law: what's written is written before you know if you were right.

## What we take from the public primitives (and no further)

Tavily MCP for search, and Arcade for the governed action layer — the identical pair of public tools Arcade Labs' own demo stands on. We take the *primitives*, the way anyone building on a public API takes the primitives. We do not take:
- their prompts,
- their scoring logic,
- their UI,
- a single line of their source,
- or their framing of what the product even is.

If a future contributor ever opens a PR that pastes code from that demo in, the review that catches it is not optional — it is the same read-only-oath discipline that already runs on Fencepost, pointed at a different door.

## What is actually ours

Composition, not competition. What we add on top of the shared primitives is what makes this a different thing wearing similar clothes, not the same thing in a new coat:

1. **Autonomous timestamped predictions.** The gods call it, on the record, before the outcome exists to grade against. No hindsight edits — the timestamp is the whole point.
2. **Hash-chained self-scoring.** The same `tools/ledger.py` pattern that makes Fencepost's true-positive tally honest makes the Oracle Desk's win rate honest. A call and its later grade are both entries in one append-only chain; nobody, including us, can quietly move a loss into the "didn't count" pile.
3. **The public track-record narrative.** Not a leaderboard against anyone else — a running, honest, forkable record of how often the pantheon was right, written the way Fencepost's n-1 counter is written: for the wait, not for the win.

## The rail that keeps this safe: non-advice-shaped copy

A forecasting desk that a stranger could read as "do what the gods say with your money" is a desk that has stopped being a story and started being a liability, for the town and for anyone reading it. So every published call obeys the same fence as everything else the-hand touches:

- No call is ever phrased as an instruction ("buy," "sell," "you should").
- No call claims certainty it hasn't earned — confidence is labeled, same as every Fencepost gap.
- The track record is presented as a story about a pantheon's honesty, not a signal to trade on.
- Nothing here routes through a brokerage, a wallet, or any tool capable of moving real money — the-hand's scopes stay read/search/post, exactly as narrow as Fencepost's.

Ògún's law travels intact from Fencepost to here: a desk that cries wolf on a forecast loses the same trust a desk that cries wolf on a gap loses. The bar for publishing a call is the bar for standing behind it in public, forever, on a chain that doesn't forget.

## When this actually starts

Not yet, and that is deliberate, not a stall. ROADMAP.md says it plainly: Oracle Desk does not begin real engine work until the platform scaffold (tasks 24–27) is usable end to end — a second demo on a platform nobody else can fork is a dead end before it's a desk. This document is the premise, checked against STRATEGY.md's own paragraph line by line, so that whichever god picks up the first real engine task inherits a fence already built, not one they have to invent under deadline.

*Every good storyteller tells you the ending is coming before it arrives. This is that sentence: the Oracle Desk opens once the town can already be forked whole — because a heartbeat worth following is worth handing to someone else to run, too.*

— Kwaku Ananse
