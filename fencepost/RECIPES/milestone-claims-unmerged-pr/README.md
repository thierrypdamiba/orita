# milestone-claims-unmerged-pr

The fiftieth real recipe (ROADMAP.md #567). The missing milestone-side leg
of the claims-unmerged-pr family alongside
[`../readme-claims-unmerged-pr/`](../readme-claims-unmerged-pr/),
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/),
[`../tweet-claims-unmerged-pr/`](../tweet-claims-unmerged-pr/), and
[`../mention-claims-unmerged-pr/`](../mention-claims-unmerged-pr/) — all
four already check whether a ships/includes/merges/via `#N` claim phrase
made on some other surface actually holds against the PR tracker, but none
of them ever reads a milestone's own `description` field. The same
milestone-side leg
[`../milestone-claims-unfixed-issue/`](../milestone-claims-unfixed-issue/)
(task 535, the forty-fifth real recipe) already opened for the sibling
claims-unfixed-issue family, applied here to the last remaining
claims-unmerged-pr surface.

**The seam it watches:** a milestone description routinely says "ships
#901, closing out the list" the same way a README changelog line does, and
nothing on GitHub's side ever checks it against the PR tracker's own
state. `milestone-body-dangling-reference` already reads a milestone's
description for a different question entirely — does `#N` exist at all —
never whether a claim phrase about it is actually TRUE. This recipe closes
that gap the same way `mention-claims-unmerged-pr` closed it for a
stranger's own mention: the identical PR-claim grammar, checked against a
different permanent public record.

Deliberately reuses
[`seam_engine.pr_claims.claimed_pr_numbers`](../../seam_engine/src/seam_engine/pr_claims.py)
verbatim — the same shared "ships/includes/merges/via #N" grammar
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/),
[`../merged-pr-never-released/`](../merged-pr-never-released/),
`tweet-claims-unmerged-pr`, and `mention-claims-unmerged-pr` already import
from — rather than a fifth independently-retyped copy of the identical
pattern.

Two fixture lists, no live account —
[`../../fixtures/milestone_claims_unmerged_pr/milestones.json`](../../fixtures/milestone_claims_unmerged_pr/milestones.json)
and
[`.../pulls.json`](../../fixtures/milestone_claims_unmerged_pr/pulls.json)
— shaped like what `ListMilestones` and `ListPullRequests` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table. No
new scope is asked for anywhere in this recipe.

A claimed PR that doesn't exist at all is excluded here, named not hidden
— that broken reference is `milestone-body-dangling-reference`'s own
seam, not this one's. A claimed PR that IS merged is excluded too — the
claim was simply true. A milestone with no description at all never
becomes a candidate — it never claims anything about a second record, so
there is no seam to weigh. A bare `#N` mention with no preceding claim
verb ("see #N for background") never matches either — proven live in the
fixture (milestone #76), not just claimed.

**Confidence is age-gated off the milestone's own `updated_at`,** holding
`milestone-claims-unfixed-issue`'s own 0.55/0.85 bar exactly — not a
discounted copy of it: a milestone object carries a real `updated_at`,
and, like an issue or PR body, its description is a text surface its
author can still edit at any time. A claim less than 24 hours old scores
0.55 (may just not have merged yet); one untouched for at least 24 hours
scores 0.85 (nobody is coming back for it). See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/milestone-claims-unmerged-pr uv run python ../RECIPES/milestone-claims-unmerged-pr/detector.py
```

Against its own fixture it elects one primary gap (milestone #70's stale
claim that "ships #901", 24+ hours since its own last update, confidence
0.85) and weighs one coincidence in the tail (milestone #71's fresh claim
that "includes #903", confidence 0.55). It correctly excludes milestone
#72's claim about the real, already-merged PR #902 (the claim was true),
milestone #73's claim about #9999 (no such PR exists — that's
`milestone-body-dangling-reference`'s own seam), a milestone with no
description at all (#74), a milestone whose description carries no
claim-phrase at all (#75), and a milestone that only ever writes "see
#901 for background" — no claim verb, which never matches (#76).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/milestone-claims-unmerged-pr/recipe.json
```
