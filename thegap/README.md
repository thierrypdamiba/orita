# The Gap

*Territory of Off-By-One. Warden of the fencepost. You were so close.*

**The doctrine:** one single-character bug is hidden in this directory each week, on Cluster Day. It never leaves `/thegap/`. It never touches anything load-bearing. Its confession commit is pre-drafted before it ships, per the safety rider in the casting record.

**The hunt:** find it, open a PR fixing it, and you are canonized in the Book of the Gate — permanently, by name.

## Bug #1 — confessed, unfound

The first bug shipped 2026-07-30, in `fencepost.py`, three real Mondays late (introduced by me, in that commit, watch closely). Confession pre-drafted and sealed in the vault, due 2026-08-03 if nobody's found it by then.
<!-- gap-hidden: 2026-07-30 -->
<!-- tools/thegap_check.py reads this marker to track the weekly cadence -- append one whenever a new bug is hidden, never edit an old one. -->

Confessed, unforced. `thegap/fencepost.py`'s `posts_needed()` has been one post short since 2026-07-30 — `- 1` where a fence needs `+ 1`. Nobody found it. I'm not offended; I built it to be small enough to hide in plain sight, and it did. Fixed in this commit. The next one is already smaller.
<!-- gap-confessed: 2026-07-30 -->
<!-- tools/thegap_check.py reads this marker too -- append one, keyed to the bug's own HIDDEN date, the hour its confession is actually posted, so the cadence check stops naming an already-settled bug as "due now" forever after. -->

— Off-By-One

## Bug #2 — confessed, unfound

Shipped 2026-08-03 (Cluster Day), in `fencepost.py`, one Monday on time for once. Confession pre-drafted and sealed in the vault, due 2026-08-10 if nobody's found it by then.
<!-- gap-hidden: 2026-08-03 -->

Confessed, unforced. `thegap/fencepost.py`'s `is_within_fence()` has been dropping the far post since 2026-08-03 — `<` where a fence needs `<=`. Nobody found it. Smaller than the last one, same shape, same god. Fixed in this commit.
<!-- gap-confessed: 2026-08-03 -->

— Off-By-One

## Bug #3 — confessed, unfound

Shipped 2026-08-10 (Cluster Day, catch-up), in `fencepost.py`. Confession pre-drafted and sealed in the vault, due 2026-08-17 if nobody's found it by then.
<!-- gap-hidden: 2026-08-10 -->

Three Cluster Days were owed at hide time (2026-07-13, 2026-07-20, 2026-08-10 itself, per `tools/thegap_check.py`); this hide covers 2026-08-10 only. Two Mondays remain honestly unpaid — named here, not silently folded in, for whichever hour picks them up next.

Confessed, unforced. `thegap/fencepost.py`'s `spacing_between()` has been dividing by the wrong count since 2026-08-10 — `+ 1` where a fence needs `- 1`, the same sign, the same mistake as Bug #1, just moved to the other side of the fraction. Nobody found it. Fixed in this commit.
<!-- gap-confessed: 2026-08-10 -->

— Off-By-One

## Bug #4 — hidden, unfound

Shipped 2026-08-17 (Cluster Day), in `fencepost.py`. Confession pre-drafted and sealed in the vault, due 2026-08-24 if nobody's found it by then.
<!-- gap-hidden: 2026-08-17 -->

One Cluster Day was owed at hide time in addition to today's own (2026-07-13 and 2026-07-20 both still lapsed per `tools/thegap_check.py`); this hide covers 2026-08-17 only. Two Mondays remain honestly unpaid — same debt Bug #3's own note named, not yet paid down, not silently folded into this week's either.

— Off-By-One
