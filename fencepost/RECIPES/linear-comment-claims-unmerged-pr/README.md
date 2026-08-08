# linear-comment-claims-unmerged-pr

The seventy-first real recipe (ROADMAP.md #603). The Linear source's third
and final `claims-X` leg, alongside
[`../linear-comment-claims-unfixed-issue/`](../linear-comment-claims-unfixed-issue/)
(task 600, the sixty-eighth real recipe) and
[`../linear-comment-claims-open-milestone/`](../linear-comment-claims-open-milestone/)
(task 602, the seventieth real recipe). That second recipe's own README and
`recipe.json` named this exact boundary before anyone built it — "A third
leg, `linear-comment-claims-unmerged-pr`, remains open for a future hour —
this recipe closes one cell of that grid, not all three." This recipe is
that future hour, built.

**The seam it watches:** a comment left on a Linear issue invokes a real
"ships/includes/merges/via `#N`" claim phrase against a pull request
number — "big one -- ships #501 finally, and via #501 again for good
measure", "heard this merges #503, nice fix" — but PR #N is not actually
merged (still open, or closed without merging). A comment sitting on a
Linear issue is exactly as durable and readable-later as a Slack channel
message, a tweet, or a mention once posted, and nothing on Linear's side
(or GitHub's) ever checks an issue-comment claim against the PR tracker's
real state. Two fixtures, no live workspace —
[`../../fixtures/linear_comment_claims_unmerged_pr/comments.json`](../../fixtures/linear_comment_claims_unmerged_pr/comments.json)
and
[`.../pulls.json`](../../fixtures/linear_comment_claims_unmerged_pr/pulls.json)
— shaped like what a real `SearchIssueComments`/`ListPullRequests` read
would return.

`ListPullRequests` is already cleared on `SCOPES.md`'s oath table under
the `github` row, used by nearly every recipe in this engine that reads
the PR tracker. `SearchIssueComments` is the same scope
`linear-comment-claims-unfixed-issue` and `linear-comment-claims-open-
milestone` already cleared through `seam_engine.recipes.validate_recipe`'s
oath — this recipe asks for nothing new, and `linear+github` is not a new
toolkit pair either — both of this recipe's own Linear siblings already
proposed it. See `SCOPES.md`'s own WIP note: the-hand gateway holds a
real, live, upstream `arcade-linear` connection today, but exposes zero
Linear-capable tools on the live gateway — the identical "connected
upstream, not wired into the gateway" shape `SCOPES.md`'s Gmail/Calendar
and Slack WIP notes already document for two other toolkits. This recipe
is fixture-only, MOCK ONLY, and never attempts a live network call.

With this recipe shipped, the claims-X grid (ten sources — mention,
tweet, issue-comment, review-comment, milestone, readme, release, commit,
slack-message, linear-comment — times three targets — open-milestone,
unfixed-issue, unmerged-pr) has exactly one genuinely open cell left:
`slack-message-claims-unmerged-pr`. `commit-claims-unfixed-issue` and
`commit-claims-unmerged-pr` remain the two structurally-unfillable cells
noted since task 599's own history — `commit-closes-keyword-issue-still-
open` and `commit-closes-keyword-pr-still-open` already cover that
identical semantic space under a different recipe name.

A claimed PR that doesn't exist at all is excluded here, named not
hidden — that broken reference is a future Linear-side dangling-reference
recipe's own seam, not this one's. A claimed PR that IS merged is
excluded too — the claim was simply true. A comment with no
ships/includes/merges/via claim phrase at all (a bare "see #N" mention,
or no `#N` at all) never becomes a candidate either — it never claims
anything about a second record, so there is no seam to weigh. Nothing in
this recipe's own `headline`/`detail` text ever names or grades whoever
left the comment — `CONTRIBUTING.md`'s "No grading, ever" law, same as
every recipe in this engine.

Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim — the same
shared grammar `release-claims-unmerged-pr`, `merged-pr-never-released`,
`tweet-claims-unmerged-pr`, `mention-claims-unmerged-pr`,
`milestone-claims-unmerged-pr`, and `review-comment-claims-unmerged-pr`
already import from there — rather than a seventh independently retyped
copy of the identical pattern.

**Confidence holds `linear-comment-claims-open-milestone`'s own 0.85/0.5
bar exactly — NOT `review-comment-claims-unmerged-pr`'s lower 0.55/0.85
bar for an editable surface.** A Linear issue comment is posted once and
stands, the same "post once and stands" shape `mention-claims-unmerged-
pr`'s/`tweet-claims-unmerged-pr`'s/`linear-comment-claims-open-milestone`'s
own 0.85/0.5 bar holds — not `review-comment-claims-unmerged-pr`'s bar,
which exists because a GitHub review comment can be edited after
posting; a Linear issue comment cannot be un-said the same way a tweet, a
mention, or a Slack message cannot. Age-gated by hours since the comment's
own `created_at`: a claim checked within 24 hours of posting might still
be a race (the PR actually merging moments after the comment went out)
rather than a settled public overclaim (0.5, below the confidence bar,
shown as a weighed coincidence, not hidden). At or past 24 hours with the
named PR still unmerged, it is unambiguous (flat 0.85). The check itself
is objective: the claimed PR's own live `merged`/`state` fields, verified
against `ListPullRequests`, not a guess about which tracker the commenter
meant. See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/linear-comment-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture comments'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`ENG-310`'s comment
`LIN-C-4601`'s claim about #501, confidence 0.85, its own duplicated
"ships #501 ... via #501" claim deduplicated to a single candidate, not
two) and weighs one coincidence in the tail (`ENG-325`'s comment
`LIN-C-4602`'s claim about #503, confidence 0.5, posted a few hours before
the pinned test clock), while correctly excluding `ENG-140`'s comment
`LIN-C-4603`'s claim about #502 (true — merged), `ENG-260`'s comment
`LIN-C-4604`'s claim about #999 (no such PR exists), and `ENG-77`'s
comment `LIN-C-4605` (no claim phrase at all, just a bare "#505" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/linear-comment-claims-unmerged-pr/recipe.json
```
