# milestone-claims-open-milestone

The fifty-first real recipe: the last remaining leg of the
"claims-open-milestone" family, applied to the one text surface it had
never reached — a milestone's own description.
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/),
[`../release-claims-open-milestone/`](../release-claims-open-milestone/),
`tweet-claims-open-milestone`, and
[`../mention-claims-open-milestone/`](../mention-claims-open-milestone/)
all already check a `milestone #N` claim phrase against the milestone
tracker's own live state — but none of them ever read a milestone's OWN
`description` field, the same text surface
[`../milestone-claims-unfixed-issue/`](../milestone-claims-unfixed-issue/)
(task 535) and
[`../milestone-claims-unmerged-pr/`](../milestone-claims-unmerged-pr/)
(task 567) already opened for the sibling claims-unfixed-issue and
claims-unmerged-pr families. This recipe closes the identical gap for
the third and last claim shape, completing the full grid: five surfaces
(mention, milestone, readme, release, tweet) crossed with three claim
types (open-milestone, unfixed-issue, unmerged-pr) — fifteen legs, all
now shipped.

**The seam it watches:** a milestone's description routinely says "ships
alongside milestone #40" or "depends on milestone #52" the same way a
README or a release body does, and nothing on GitHub's side ever checks
it against the OTHER milestone's own real state. Unlike every other
sibling in this family, both halves of the comparison live in the same
list — a milestone claiming a milestone is a same-toolkit, same-call
comparison, so this recipe reads only one fixture (`milestones.json`)
rather than two.

Deliberately reuses
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py)
verbatim — the same shared grammar
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/),
[`../release-claims-open-milestone/`](../release-claims-open-milestone/),
`tweet-claims-open-milestone`, and
[`../mention-claims-open-milestone/`](../mention-claims-open-milestone/)
already import from — rather than a sixth independently-retyped copy of
the identical pattern.

One fixture list, no live account —
[`../../fixtures/milestone_claims_open_milestone/milestones.json`](../../fixtures/milestone_claims_open_milestone/milestones.json)
— shaped like what a single `ListMilestones` call would actually return.
That scope already sits on `SCOPES.md`'s cleared oath table. No new scope
is asked for anywhere in this recipe, and the `toolkit` stays
`github`-only — the total recipe count grows, the plus-joined count does
not.

A milestone naming ITSELF is excluded outright, named not hidden — a
milestone repeating its own number is not a claim about a second record,
so there is no seam to weigh (a shape none of this family's other four
siblings can even produce, since none of them ARE a milestone). A
claimed milestone that doesn't exist at all is excluded here — that
broken reference is `milestone-body-dangling-reference`'s own seam, not
this one's. A claimed milestone that IS closed is excluded too — the
claim was simply true. A milestone with no description at all never
becomes a candidate — it never claims anything about a second record.

**Confidence is age-gated off the claiming milestone's own `updated_at`,**
mirroring `milestone-claims-unfixed-issue`'s and
`milestone-claims-unmerged-pr`'s identical reasoning rather than
`readme-claims-open-milestone`'s flat 0.85: a milestone description,
like an issue or PR body, is a text surface its author can edit at any
time. A claim less than 24 hours old scores 0.55 (may still get fixed);
one untouched for at least 24 hours scores 0.85 (nobody is coming back
for it). See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/milestone-claims-open-milestone uv run python ../RECIPES/milestone-claims-open-milestone/detector.py
```

Against its own fixture it elects one primary gap (milestone #70's stale
claim that "milestone #701" shipped, 24+ hours since its own last
update, confidence 0.85) and weighs one coincidence in the tail
(milestone #71's fresh claim about milestone #702, confidence 0.55). It
correctly excludes milestone #72's claim about the real, already-closed
milestone #703 (the claim was true), milestone #73's claim about #9999
(no such milestone exists — that's `milestone-body-dangling-reference`'s
own seam), milestone #76's claim about itself (not a claim about a
second record), a milestone with no description at all (#74), and a
milestone whose description carries no `milestone #N` claim at all
(#75).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/milestone-claims-open-milestone/recipe.json
```
