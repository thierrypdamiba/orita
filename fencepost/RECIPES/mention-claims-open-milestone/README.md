# mention-claims-open-milestone

The forty-eighth real recipe. The missing mention-side leg of the
claims-open-milestone family alongside
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/),
[`../release-claims-open-milestone/`](../release-claims-open-milestone/),
and [`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/) —
all three already check whether a `milestone #N` claim phrase made on a
text surface the town itself controls (its own README, its own release
notes, its own tweets) actually holds against the milestone tracker. None
of them ever read the one surface those three never touch: a **stranger's
own mention** of the account. The same tweet-vs-mention split
[`../mention-claims-unfixed-issue/`](../mention-claims-unfixed-issue/) (the
forty-seventh real recipe) already opened against
[`../tweet-claims-unfixed-issue/`](../tweet-claims-unfixed-issue/) for the
sibling claims-unfixed-issue family, applied here to the
claims-open-milestone family instead.

**The seam it watches:** a mortal mentions the connected account on X using
a `milestone #N` claim phrase — "so glad milestone #5001 finally shipped!",
"heard milestone #5003 is done" — but milestone #N is still open. A mention
is exactly as permanent and public as a tweet once posted, and nothing on
X's side (or GitHub's) ever checks a stranger's own claim against the
milestone tracker's real state. Two fixtures, no live account —
[`../../fixtures/mention_claims_open_milestone/mentions.json`](../../fixtures/mention_claims_open_milestone/mentions.json)
and
[`.../milestones.json`](../../fixtures/mention_claims_open_milestone/milestones.json)
— shaped like what `GetMyMentions` and `ListMilestones` would actually
return. `GetMyMentions` has sat cleared on `SCOPES.md`'s oath table since
founding (first used by `mention-dangling-reference`, the eighteenth real
recipe); `ListMilestones` is used by every milestone-claim recipe already
in this engine. No new scope is asked for anywhere in this recipe.

A claimed milestone that doesn't exist at all is excluded here, named not
hidden — that broken reference belongs to a dangling-reference-family
seam, not this one's. A claimed milestone that IS closed is excluded too
— the claim was simply true. A mention with no `milestone #N` claim phrase
at all (a bare "see #N" follow-up, or no `#N` at all) never becomes a
candidate either — it never claims anything about a second record, so
there is no seam to weigh.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim —
the same shared grammar `milestone-closed-never-released`,
`release-claims-open-milestone`, `milestone-closed-not-tweeted`, and
`tweet-claims-open-milestone` already import from there — rather than a
fifth independently retyped copy of the identical pattern.

**Confidence mirrors `tweet-claims-open-milestone`'s own 0.85/0.5 bar
exactly — not a discounted copy of it.** Age-gated by hours since the
mention's own `created_at`: a claim checked within 24 hours of posting
might still be a race (the milestone actually closing out moments after
the mention went out) rather than a settled public overclaim (0.5, below
the confidence bar, shown as a weighed coincidence, not hidden). At or
past 24 hours with the named milestone still open, it is unambiguous (flat
0.85). The check this recipe makes is objective, the claimed milestone's
own live `state` field verified against `ListMilestones`, not the
mortal's guess. A mortal cannot be "wrong about the number space" and
still land a real, existing milestone number attached to a real
`milestone #N` claim. See `recipe.json`'s `confidence_notes` for the full
reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/mention-claims-open-milestone/detector.py
```

Run bare like this it uses the real wall clock, so the fixture mentions'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`M-5301`'s claim about
milestone #5301, confidence 0.85, posted well over 24 hours before the
pinned test clock, and its own duplicated "milestone #5301 shipped ...
milestone #5301 confirmed" claim deduplicated to a single candidate, not
two) and weighs one coincidence in the tail (`M-5302`'s claim about
milestone #5303, confidence 0.5, a few hours old at the pinned test
clock), while correctly excluding `M-5303`'s claim about milestone #5302
(true — closed), `M-5304`'s claim about milestone #5999 (no such
milestone), and `M-5305` (no `milestone #N` claim phrase at all, just a
bare "#5305" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/mention-claims-open-milestone/recipe.json
```
