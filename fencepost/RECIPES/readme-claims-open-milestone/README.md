# readme-claims-open-milestone

The thirty-fifth real recipe (ROADMAP.md #491). The third leg of the
"claims-open-milestone" family alongside
[`../release-claims-open-milestone/`](../release-claims-open-milestone/)
(a release's own body) and
[`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/) (a
tweet's own text): the identical shape, watched inside a third place the
town writes a permanent, public "shipped it" claim — the flagship's own
front door, README.md, the document a stranger reads first.

**The seam it watches:** README.md claims a milestone shipped ("milestone
#N"), but the named milestone is not actually closed. A README is as
public and as easy to leave stale as a release note or a tweet, and
nothing on GitHub's side ever checks its prose against the milestone
tracker's own truth. Two fixtures, no live account —
[`../../fixtures/readme_claims_open_milestone/readme.json`](../../fixtures/readme_claims_open_milestone/readme.json)
and
[`../../fixtures/readme_claims_open_milestone/milestones.json`](../../fixtures/readme_claims_open_milestone/milestones.json)
— shaped like what a read-only `GetFileContents` call on this repo's own
README and `ListMilestones` would actually return. Both scopes already
sit on `SCOPES.md`'s cleared oath table. No new scope is asked for
anywhere in this recipe.

A claimed milestone that doesn't exist at all is excluded here, named not
hidden — that broken reference is a dangling-reference seam, not this
one's. A claimed milestone that IS closed is excluded too — the claim was
simply true.

Confidence is deliberately **not** age-gated, unlike both siblings in this
family. A `GetFileContents` read returns README.md's current text, not a
change history, so there is no per-claim "when was this written"
timestamp to weigh a staleness window against — the same absence
`readme-credited-not-thanked`'s own docstring already named for its own
README read. There is also no race to guard against: a README is read
live, right now, so a claim it currently makes and the milestone's
currently-open state are both true at the same instant the scan runs. A
flat 0.85 applies to every surfaced claim. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim,
the same shared grammar `release-claims-open-milestone` and
`tweet-claims-open-milestone` already import from there (task 389) — a
fourth independently retyped copy of the identical pattern was exactly the
drift that centralization exists to prevent.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/readme-claims-open-milestone/detector.py
```

The shipped fixture elects the primary gap for real:

```json
{
  "slug": "readme-claims-open-milestone-12",
  "headline": "README.md claims milestone #12 shipped, but it's still open",
  "confidence": 0.85
}
```

...and correctly excludes milestone #7 (claim holds, closed) and milestone
#99 (no such milestone — a dangling reference, not this recipe's seam).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/readme-claims-open-milestone/recipe.json
```
