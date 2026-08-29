# issue-body-claims-dangling-milestone

The ninety-fifth real recipe.

**The seam it watches:** an issue or pull request's own OPENING BODY
invokes a real `milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../issue-body-claims-open-milestone/`](../issue-body-claims-open-milestone/)
(the ninety-second real recipe) drew this exact line in its own
docstring: a claimed milestone number that names no real milestone at
all was excluded there, named not hidden, as "belonging to
issue-body-dangling-reference's own seam, not this one's." That was only
half true —
[`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)
(the twenty-fourth real recipe) only ever watches a bare `#N` against
GitHub's shared issue/PR number sequence and never opens
`ListMilestones` at all, so the milestone-claim leg of this surface had
never actually been built anywhere. This recipe is that seam — the
issue/PR-body-sourced sibling of
[`../commit-claims-dangling-milestone/`](../commit-claims-dangling-milestone/)
(the seventy-sixth real recipe), which closed the identical seam for a
commit message.

Three fixtures, no live account —
[`../../fixtures/issue_body_claims_dangling_milestone/issues.json`](../../fixtures/issue_body_claims_dangling_milestone/issues.json),
[`pulls.json`](../../fixtures/issue_body_claims_dangling_milestone/pulls.json),
and
[`milestones.json`](../../fixtures/issue_body_claims_dangling_milestone/milestones.json)
— shaped like what `ListIssues`, `ListPullRequests`, and `ListMilestones`
would actually return. All three scopes already sit on `SCOPES.md`'s
cleared oath table; `source: "fixture"` in `run_recipe_scan`'s own
output is the honest MOCK ONLY marker CONTRIBUTING.md requires of every
recipe on the day it merges, not a claim the underlying scopes are
unavailable.

A claimed milestone number that DOES resolve to a real milestone is
excluded here, named not hidden, whether that milestone is open or
closed — whether the claim itself is true is
`issue-body-claims-open-milestone`'s own seam, not this one's. A body
with no `milestone #N` claim phrase at all (a bare `#N` aside), or no
body at all, never becomes a candidate either.

Confidence is flat (0.8), not age-gated, mirroring
`commit-claims-dangling-milestone`'s own reasoning rather than
`issue-body-claims-open-milestone`'s 24-hour edit-grace bar: a
milestone number that does not exist right now will not spontaneously
start existing later, so there is no grace period that means anything
here. This holds even though an issue or PR body, like a timeline
comment, stays editable forever: the editability of the surface has no
bearing on whether the milestone *number* it names exists. See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-body-claims-dangling-milestone/detector.py
```

Against the shipped fixture it finds one real gap as the elected
primary: issue `#80`'s own body claims milestone `#8999` twice
(deduplicated to one candidate, confidence 0.8 — no such milestone
exists). It correctly excludes issue `#81` and PR `#56` (both claim
milestone `#8301`, which is real and open — no seam, that's
`issue-body-claims-open-milestone`'s own remit), issue `#82` and PR
`#57` (both claim milestone `#8302`, which is real and closed), issue
`#83` (a bare `#5` aside, no `milestone #N` claim phrase at all), and
issue `#84` (no body at all — never examined). The PR-side surfaced
path (a PR body naming a genuinely nonexistent milestone) is exercised
directly in `tests/test_issue_body_claims_dangling_milestone_detector.py`
rather than in the shipped fixture — this recipe's confidence is flat,
so two surfaced dangling candidates in the same fixture would tie inside
`rank()`'s own separation margin and elect no primary at all, exactly
the way `issue-comment-claims-dangling-milestone`'s own shipped fixture
stays deliberately limited to one surfaced candidate for the same
reason.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-body-claims-dangling-milestone/recipe.json
```
