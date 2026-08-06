# mention-claims-unmerged-pr

The forty-ninth real recipe (ROADMAP.md #566). The missing mention-side leg
of the claims-unmerged-pr family alongside
[`../readme-claims-unmerged-pr/`](../readme-claims-unmerged-pr/),
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/), and
[`../tweet-claims-unmerged-pr/`](../tweet-claims-unmerged-pr/) — all three
already check whether a ships/includes/merges/via `#N` claim phrase made on
a text surface the town itself controls (its own README, its own release
notes, its own tweets) actually holds against the PR tracker. None of them
ever read the one surface those three never touch: a **stranger's own
mention** of the account. The same tweet-vs-mention split
[`../mention-claims-unfixed-issue/`](../mention-claims-unfixed-issue/) (the
forty-seventh real recipe) opened against
[`../tweet-claims-unfixed-issue/`](../tweet-claims-unfixed-issue/) and
[`../mention-claims-open-milestone/`](../mention-claims-open-milestone/)
(the forty-eighth) opened against
[`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/),
applied here to the third and last claims-X family — claims-unmerged-pr —
to grow its mention leg.

**The seam it watches:** a mortal mentions the connected account on X using
a ships/includes/merges/via `#N` claim phrase — "so glad this ships #901
today!", "heard this merges #903" — but PR #N is not actually merged, still
open, or closed without merging. A mention is exactly as permanent and
public as a tweet once posted, and nothing on X's side (or GitHub's) ever
checks a stranger's own claim against the PR tracker's real state. Two
fixtures, no live account —
[`../../fixtures/mention_claims_unmerged_pr/mentions.json`](../../fixtures/mention_claims_unmerged_pr/mentions.json)
and
[`.../pulls.json`](../../fixtures/mention_claims_unmerged_pr/pulls.json)
— shaped like what `GetMyMentions` and `ListPullRequests` would actually
return. `GetMyMentions` has sat cleared on `SCOPES.md`'s oath table since
founding (first used by `mention-dangling-reference`, the eighteenth real
recipe); `ListPullRequests` is used by every recipe that already reads the
PR tracker in this engine. No new scope is asked for anywhere in this
recipe.

A claimed PR that doesn't exist at all is excluded here, named not hidden —
that broken reference belongs to a dangling-reference-family seam, not this
one's. A claimed PR that IS merged is excluded too — the claim was simply
true. A mention with no ships/includes/merges/via claim phrase at all (a
bare "see #N" follow-up, or no `#N` at all) never becomes a candidate
either — it never claims anything about a second record, so there is no
seam to weigh.

Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim — the same
shared grammar `release-claims-unmerged-pr`, `merged-pr-never-released`,
and `tweet-claims-unmerged-pr` already import from there — rather than a
fourth independently retyped copy of the identical pattern.

**Confidence mirrors `tweet-claims-unmerged-pr`'s own 0.85/0.5 bar
exactly — not a discounted copy of it.** Age-gated by hours since the
mention's own `created_at`: a claim checked within 24 hours of posting
might still be a race (the real merge landing moments after the mention
went out) rather than a settled public overclaim (0.5, below the
confidence bar, shown as a weighed coincidence, not hidden). At or past 24
hours with the named PR still unmerged, it is unambiguous (flat 0.85). The
check this recipe makes is objective, the claimed PR's own live
`state`/`merged` fields verified against `ListPullRequests`, not the
mortal's guess. A mortal cannot be "wrong about the number space" and still
land a real, existing PR number attached to a real claim phrase. See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/mention-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture mentions'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`P-901`'s claim about
PR #901, confidence 0.85, posted well over 24 hours before the pinned test
clock, and its own duplicated "ships #901 ... via #901 again" claim
deduplicated to a single candidate, not two) and weighs one coincidence in
the tail (`P-902`'s claim about PR #903, confidence 0.5, a few hours old at
the pinned test clock), while correctly excluding `P-903`'s claim about PR
#902 (true — merged), `P-904`'s claim about PR #999 (no such PR), and
`P-905` (no claim phrase at all, just a bare "#905" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/mention-claims-unmerged-pr/recipe.json
```
