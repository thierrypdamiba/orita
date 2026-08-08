# draft-pr-closes-keyword-issue

The sixty-fifth real recipe (ROADMAP.md #597). It reads a field none of the sixty-four
prior recipes has ever read: a pull request's own `draft` field — GitHub's
real, structured record of whether the author has explicitly said this
work is not ready yet.

**The seam it watches:** an open, unmerged pull request's own body already
carries a real GitHub closing keyword (`closes #N`, `fixes #N`,
`resolves #N`, case-insensitive, past or present tense) while the PR's own
`draft` field still reads `true`. Nine prior recipes already parse a PR or
commit's own prose for that exact closing-keyword grammar (reusing
[`seam_engine.closing_keywords.CLOSING_KEYWORD_RE`](../../seam_engine/src/seam_engine/closing_keywords.py),
the shared, single source), but every one of them either reads a commit
message — permanent the instant it's pushed — or requires the PR to have
already merged before it looks at the body at all
([`merged-pr-issue-still-open`](../merged-pr-issue-still-open/),
[`merged-pr-pr-still-open`](../merged-pr-pr-still-open/)). None of them
ever reads a PR's own body while the PR sits open and unmerged, and none
of them has ever read `draft`. GitHub renders the "will close #N" note on
the issue's own sidebar identically whether the linked PR is a draft or
not — a maintainer skimming the issue sees "a PR will close this" with no
indication the PR is still explicitly marked not-ready. Nothing on
GitHub's side ever compares `draft` to the PR's own body text; the two
fields simply sit next to each other, unreconciled, for as long as the
draft sits open.

This is a genuinely different axis from every family this repo has already
saturated. It is not the claims-X grid — a PR's own body is not one of the
seven external text surfaces that grid crosses against three claim
phrases (readme, release, milestone, tweet, mention, issue comment, review
comment), and this recipe never crosses the toolkit boundary into X at
all. It is not the dangling-reference grid — this recipe never looks up
the named issue at all, real or not; whether `#N` exists, and whether it's
open or closed, is a fact about a SECOND record this recipe deliberately
never reads, the same "holding only what one call already returns"
discipline
[`locked-resolved-issue-still-open`](../locked-resolved-issue-still-open/)
established for its own `locked`/`active_lock_reason` pair. It is not
`merged-pr-issue-still-open`'s seam — that recipe requires
`state == "merged"` before it reads a body at all, and watches whether a
SECOND record (the referenced issue) caught up; this recipe requires
`draft == true` and never advances past `state != "open"`, so the same PR
can never appear in both recipes' surfaced output. It is not
`commit-closes-keyword-issue-still-open`'s seam either — a commit message
is immutable the instant it's pushed, while a PR's own body stays mutable
right up until the PR closes, so this recipe's claim is only ever about
the body's latest read. It shares only the general *shape* of
`locked-resolved-issue-still-open` and
[`commit-closes-keyword-issue-closed-not-planned`](../commit-closes-keyword-issue-closed-not-planned/)
— a single record's own fields disagreeing with each other, read off one
list, no second source needed — but watches `draft` against the record's
own body text, a pair neither of those recipes, nor any other, has ever
paired.

The claim stays narrow on purpose, the same no-grading law every sibling
holds: this recipe never claims the author did anything wrong, or that
the promise is false. A brand-new draft PR carrying `closes #N` in its own
opening scaffolding is completely ordinary — plenty of contributors open a
draft with the intended closing keyword already written, exactly so
reviewers can see the target up front while the work is still in
progress. That is not a seam; it is simply what "draft" is for. The gap
only exists once the same tension has sat unresolved for a while with
nothing in the record itself explaining why.

A body that merely mentions the issue number in passing (`related to #N`,
`see #N for context`) makes no closing promise and is excluded, not
guessed into either bucket. A draft PR with no body at all (`body` is
`null`, a real, valid GitHub state) is excluded the same way — no claim
was made to check against anything. A PR that isn't a draft at all is
excluded outright — nothing about `draft` to compare against its own
body. A draft PR whose own closing keyword sits on a PR that has since
closed WITHOUT merging is excluded — the PR itself is dead, its one-time
claim moot, not a live gap sitting in front of anyone. A `draft == true`
PR whose own `state` reads `"merged"` is excluded as malformed — GitHub's
own API refuses to merge a pull request while it's still marked draft (the
author must explicitly mark it "ready for review" first, which flips
`draft` to `false` in the same action), so that combination never occurs
for real.

One fixture, no live account —
[`../../fixtures/draft_pr_closes_keyword_issue/pull_requests.json`](../../fixtures/draft_pr_closes_keyword_issue/pull_requests.json)
— shaped like what `ListPullRequests` would actually return. `ListPullRequests`
already sits on `SCOPES.md`'s cleared oath table under the `github` row —
no new scope is asked for anywhere in this recipe.

Confidence is age-gated on how long `updated_at` has sat still while the
tension holds. There is no `marked_draft_at` field on a real GitHub
pull-request object, so `updated_at` (the closest real signal GitHub
exposes) stands in, the same way
[`locked-resolved-issue-still-open`](../locked-resolved-issue-still-open/)
already uses it in place of a missing `locked_at`. Under 24 hours scores
0.5, weighed in the tail — a fresh draft's own closing keyword may just be
scaffolding nobody's touched since. At or past 24 hours it scores a flat
0.85. See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/draft-pr-closes-keyword-issue/detector.py
```

Run bare like this it uses the real wall clock, so the fixture PRs' own
ages (and therefore which ones clear 24 hours) will drift as real time
passes — expected for a manual demo, not a bug, the same documented
property every age-gated MOCK-only fixture in this repo already carries.
The test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against the pinned test clock (`2026-08-08T12:00:00Z`) it finds one real
gap in its own fixture as the elected primary (PR #2001, still a draft
243 hours after its own body already promised to close #501, confidence
0.85), one more weighed in the tail (PR #2002, only 6 hours since it
promised to close #502), and correctly excludes: PR #2003 (a closing
keyword, but `draft=false` — nothing to compare), PR #2004 (a draft, but
no closing keyword in its own body at all), PR #2005 (a draft with a
`null` body), PR #2006 (a draft that only mentions `#506` in passing,
never a real closing keyword), PR #2007 (a draft that already closed
without merging — its claim is moot), PR #2008 (a malformed record:
`draft=true` with `state="merged"`), and PR #2009 (not a draft, closed,
no closing keyword either).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/draft-pr-closes-keyword-issue/recipe.json
```
