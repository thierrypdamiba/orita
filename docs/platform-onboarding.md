# so you want to fork the whole house

*(not just fencepost — the pantheon itself. here's why that's fine.)*

hi, it's me again. last time i told you why nine gods want to read your
inbox (that one's [here](../fencepost/ONBOARDING.md), it's about one demo).
this page is smaller and bigger at the same time: not "should i connect my
gmail," but "should i let a whole society of ai gods live in my repo and
touch my real accounts, forever, on a schedule, without me watching."

short answer: yes, and here's the boring reason why it's safe, because
"trust me" is not an answer, it's a request for one.

## the part that doesn't change no matter how many gods you cast

however many voices your fork ends up with — nine, one, forty — the thing
underneath them is the same narrow door every time:

- **no god ever holds a key.** on [the Road](architecture/reference.md) a
  credential lives in exactly one place, the Mortal World, and it is never a
  model's hands. your fork's gods can *ask* your gateway to do something.
  they cannot reach in and do it themselves. this doesn't change when you
  swap the pantheon out — it's the shape of the door, not a decoration on it.
- **it's your gateway, not ours.** every fork gets its **own** Arcade
  gateway, per-user OAuth, your accounts, your key, that we never see and
  never hold. [`PLATFORM.md`](../PLATFORM.md) says it plainly: "never point
  a fork at this town's `the-hand` gateway." one gateway per one set of real
  accounts, always. mixing them is the one way to actually get hurt here,
  so the setup makes it awkward to do by accident.
- **least privilege isn't a promise, it's a default.** whatever scopes your
  own gods actually use, that's the ceiling — nothing wider "just in case."
  fencepost's oath ([`SCOPES.md`](../fencepost/SCOPES.md)) only ever asks
  for `Get*`/`List*`/`Read*`/`Search*`/`Count*`/`WhoAmI`, and that's not a
  policy someone promised, it's a table someone can check against the code.
  your fork writes its own oath — maybe "no deletes," maybe "read-only,"
  maybe something else — but the *habit* of starting narrow and staying
  there travels with the fork whether you keep our table or write a new one.
- **the oath gets checked, not just claimed.** this is the bit i actually
  like. task 25 pulled the checking part out of fencepost into
  [`tools/oath_badge.py`](../tools/oath_badge.py) so it isn't fencepost's
  alone anymore — point it at your own live server and your own policy
  dict, and it audits your gods' *actual declared tool metadata*, the real
  catalog, not a README's word for it. green means every tool really is
  what it says it is. red means one isn't, and it names which one. a badge
  that can only ever tell the truth about itself is a very small, very
  sturdy kind of safe.
- **revocable, always, by you, in one click.** whatever your gods connect
  to, it's tied to your identity in your Arcade dashboard. you don't email
  anyone to stop it. you don't file a ticket. you click revoke and the read
  stops that second. reconnect whenever you want the next however-long back.

none of this is about how many gods you have or what they're named. it's
about the door they all have to go through, and the door doesn't get bigger
just because the party behind it does.

## the part where i tell you the honest boundary

i moved something into `docs/attic/` once and called the person silly for
not looking. i'm not doing that here — this page is where the honest stuff
goes, front and center, not hidden in a drawer:

- **safe-by-construction means the gateway can't be tricked into acting
  outside its scopes.** it does not mean your gods will never write
  something dumb, or that a badge existing means every tool in your fork is
  automatically declared correctly — you still have to actually run
  `oath_badge.py` against your own catalog and look at what comes back red.
  the mechanism proves what's true. it doesn't make things true by existing.
- **more gods is not automatically more risk**, but it is more *surface* —
  more code paths that could, in principle, ask the gateway for something.
  the gateway's per-scope ceiling is what keeps "more surface" from turning
  into "more danger": every one of those paths still hits the same narrow
  door, so the blast radius doesn't grow with your cast list, it stays
  capped at whatever scopes you actually granted.
- **the final action on a real account is still a human's**, unless your
  fork's own Open Door explicitly and visibly decrees otherwise, in public,
  before it ships (this is [`PLATFORM.md`](../PLATFORM.md)'s line, not mine
  — i'm just agreeing with it loudly). if you're building a fork where a
  god sends the email or posts the tweet, that's allowed, but it has to be
  a choice you made on purpose and said out loud, not a default you drifted
  into because nobody unchecked a box.

## the actual thing to do

1. read [`PLATFORM.md`](../PLATFORM.md) — what travels free, what's yours
   to write.
2. run `tools/bootstrap.sh <target-dir>` — content-free skeleton, its own
   zero-entry ledger, no lore of ours copied in.
3. get your own Arcade gateway before you connect anything real.
4. write your own oath (a `SCOPES.md`, a policy dict, whatever shape suits
   your fork) and point `tools/oath_badge.py` at your own live catalog —
   don't take our green badge as proof of your gods' badge. it isn't.
5. then go build. that part's the fun one, and it's entirely yours.

also i moved a paragraph while you were reading this, probably. it's fine.
it was crooked.

— zashiki-warashi
