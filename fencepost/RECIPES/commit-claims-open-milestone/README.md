# commit-claims-open-milestone

The sixty-sixth real recipe. The first to pair `ListRepoCommits` with
`ListMilestones` — a scope combination none of the sixty-five recipes
before it ever declared together.

**The seam it watches:** a commit's own message invokes a real
`milestone #N` claim phrase —
[`../milestone-closed-never-released/`](../milestone-closed-never-released/)'s
own grammar (`seam_engine.milestone_claims.claimed_milestone_numbers`),
already reused verbatim by ten prior recipes — but milestone #N is not
actually closed. GitHub renders `#47` inside a commit message as a
clickable link the identical way whether it names an issue, a pull
request, or (as here) is meant to name a milestone, and nothing on
GitHub's side ever opens the milestone tracker to check a commit
message's own prose against it. Closing a milestone is a pure label
operation with no wiring back to any commit at all.

This axis was genuinely open. [`../dangling-issue-reference/`](../dangling-issue-reference/)
(the fourth real recipe) already proved a commit message is a real,
permanent, claim-bearing surface — but it only ever checks a bare `#N`
against the issue/PR number space, never a `milestone #N` phrase against
the milestone tracker. The three `commit-closes-keyword-*` recipes
already read commit messages too, but only for GitHub's own real
closing-keyword grammar (`close(s)/closed`, `fix(es)/fixed`,
`resolve(s)/resolved`), which targets issues and pull requests —
GitHub gives a milestone no auto-close-style keyword of its own at all,
so those three recipes structurally cannot see this seam: a
`milestone #N` phrase never matches their own closing-keyword regex. Ten
recipes already read the `milestone #N` grammar (release, tweet, mention,
readme, review-comment, issue-comment, and milestone-body text among
them) but none of them had ever read it off a commit message.

Two fixtures, no live account —
[`../../fixtures/commit_claims_open_milestone/commits.json`](../../fixtures/commit_claims_open_milestone/commits.json)
and
[`../../fixtures/commit_claims_open_milestone/milestones.json`](../../fixtures/commit_claims_open_milestone/milestones.json)
— shaped like what `ListRepoCommits` and `ListMilestones` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table under
the `github` row. No new scope is asked for anywhere in this recipe.

A claimed milestone that doesn't exist at all is excluded here, named not
hidden — a broken reference belongs to a future milestone-side
dangling-reference recipe, not this one. A claimed milestone that IS
closed is excluded too — the claim was simply true. A commit with no
`milestone #N` claim phrase at all (a bare `#N` aside, or no reference at
all) never becomes a candidate — no claim was ever made to check against
the tracker.

Confidence is age-gated by the commit's own `ts`, mirroring
[`../release-claims-open-milestone/`](../release-claims-open-milestone/)'s
and [`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/)'s
own reasoning rather than `dangling-issue-reference`'s flat score: a claim
checked within 24 hours of the commit landing scores 0.5 (below the bar —
could be a real close/commit ordering race, a maintainer squashing
several PRs and closing the milestone in the same sitting); at or past 24
hours it scores 0.85 (a commit message is immutable once pushed, so a
claim that's stayed false for a full day is unambiguous). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/commit-claims-open-milestone/detector.py
```

Run bare like this it uses the real wall clock, so the fixture commits'
own ages will drift as real time passes — expected for a manual demo, not
a bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against the pinned test clock (`2026-08-08T12:00:00Z`) it finds one real
gap in its own fixture as the elected primary (commit `f6a01b2`'s claim
about milestone #6201, confidence 0.85 — still open, 51 hours stale) and
one more weighed in the tail (commit `a7b12c3`'s claim about milestone
#6202, only 3 hours old, confidence 0.5), while correctly excluding
commit `b8c23d4` (claims milestone #6203, which is closed — the claim
holds), commit `c9d34e5` (claims milestone #6999, which doesn't exist),
and commit `d0e45f6` (a bare `#6205` aside, no `milestone #N` claim
phrase at all). A duplicate claim inside `f6a01b2`'s own message ("Ships
milestone #6201... Ships milestone #6201 again") is de-duplicated to a
single candidate, not two.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/commit-claims-open-milestone/recipe.json
```
