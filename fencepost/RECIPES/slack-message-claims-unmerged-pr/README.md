# slack-message-claims-unmerged-pr

The seventy-second real recipe (ROADMAP.md #604). The Slack source's
third and final `claims-X` leg, alongside
[`../slack-message-claims-unfixed-issue/`](../slack-message-claims-unfixed-issue/)
(task 599, the sixty-seventh real recipe) and
[`../slack-message-claims-open-milestone/`](../slack-message-claims-open-milestone/)
(task 601, the sixty-ninth real recipe). That second recipe's own README
named this exact boundary before anyone built it — "a third leg,
`slack-message-claims-unmerged-pr`, remains open for a future hour." Also
the Slack-side twin of
[`../linear-comment-claims-unmerged-pr/`](../linear-comment-claims-unmerged-pr/)
(task 603, the seventy-first real recipe), which closed the identical
PR-claim leg for the Linear issue-comment surface and named this recipe
as the claims-X grid's one remaining genuinely open cell. This recipe is
that future hour, built.

**The seam it watches:** a message posted to a Slack channel invokes a
real "ships/includes/merges/via `#N`" claim phrase against a pull
request number — "big one -- ships #601 finally, and via #601 again for
good measure", "heard this merges #603, nice fix" — but PR #N is not
actually merged (still open, or closed without merging). A message
sitting in a Slack channel is exactly as durable and readable-later as a
Linear issue comment, a tweet, or a mention once posted, and nothing on
Slack's side (or GitHub's) ever checks a channel claim against the PR
tracker's real state. Two fixtures, no live workspace —
[`../../fixtures/slack_message_claims_unmerged_pr/messages.json`](../../fixtures/slack_message_claims_unmerged_pr/messages.json)
and
[`.../pulls.json`](../../fixtures/slack_message_claims_unmerged_pr/pulls.json)
— shaped like what a real `SearchChannelMessages`/`ListPullRequests`
read would return.

`ListPullRequests` is already cleared on `SCOPES.md`'s oath table under
the `github` row, used by nearly every recipe in this engine that reads
the PR tracker. `SearchChannelMessages` is the same scope
`slack-message-claims-unfixed-issue` and `slack-message-claims-open-
milestone` already cleared through `seam_engine.recipes.validate_recipe`'s
oath — this recipe asks for nothing new, and `slack+github` is not a new
toolkit pair either — both of this recipe's own Slack siblings already
proposed it. See `SCOPES.md`'s own WIP note: the-hand gateway holds a
real, live, upstream `arcade-slack` connection today, but exposes zero
Slack-capable tools on the live gateway — the identical "connected
upstream, not wired into the gateway" shape `SCOPES.md`'s Gmail/Calendar
and Linear WIP notes already document for two other toolkits. This
recipe is fixture-only, MOCK ONLY, and never attempts a live network
call.

With this recipe shipped, the claims-X grid (ten sources — mention,
tweet, issue-comment, review-comment, milestone, readme, release,
commit, slack-message, linear-comment — times three targets —
open-milestone, unfixed-issue, unmerged-pr) has **zero genuinely open
cells left**. `commit-claims-unfixed-issue` and `commit-claims-unmerged-
pr` remain the two structurally-unfillable cells noted since task 599's
own history — `commit-closes-keyword-issue-still-open` and
`commit-closes-keyword-pr-still-open` already cover that identical
semantic space under a different recipe name.

A claimed PR that doesn't exist at all is excluded here, named not
hidden — that broken reference is a future Slack-side dangling-reference
recipe's own seam, not this one's. A claimed PR that IS merged is
excluded too — the claim was simply true. A message with no
ships/includes/merges/via claim phrase at all (a bare "see #N" mention,
or no `#N` at all) never becomes a candidate either — it never claims
anything about a second record, so there is no seam to weigh. Nothing in
this recipe's own `headline`/`detail` text ever names or grades whoever
posted the message — `CONTRIBUTING.md`'s "No grading, ever" law, same as
every recipe in this engine.

Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim — the same
shared grammar `release-claims-unmerged-pr`, `merged-pr-never-released`,
`tweet-claims-unmerged-pr`, `mention-claims-unmerged-pr`,
`milestone-claims-unmerged-pr`, `review-comment-claims-unmerged-pr`, and
`linear-comment-claims-unmerged-pr` already import from there — rather
than an eighth independently retyped copy of the identical pattern.

**Confidence holds `slack-message-claims-open-milestone`'s/
`linear-comment-claims-unmerged-pr`'s own 0.85/0.5 bar exactly — NOT
`review-comment-claims-unmerged-pr`'s lower 0.55/0.85 bar for an
editable surface.** A Slack channel message is posted once and stands,
the same "post once and stands" shape `mention-claims-unmerged-pr`'s/
`linear-comment-claims-unmerged-pr`'s own 0.85/0.5 bar holds — not
`review-comment-claims-unmerged-pr`'s bar, which exists because a GitHub
review comment can be edited after posting; a Slack channel message
cannot be un-said the same way a tweet, a mention, or a Linear comment
cannot. Age-gated by hours since the message's own `ts`: a claim checked
within 24 hours of posting might still be a race (the PR actually
merging moments after the message went out) rather than a settled
public overclaim (0.5, below the confidence bar, shown as a weighed
coincidence, not hidden). At or past 24 hours with the named PR still
unmerged, it is unambiguous (flat 0.85). The check itself is objective:
the claimed PR's own live `merged`/`state` fields, verified against
`ListPullRequests`, not a guess about which tracker the poster meant.
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/slack-message-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture messages'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`#dev-updates`'s
message `SLK-4101`'s claim about #601, confidence 0.85, its own
duplicated "ships #601 ... via #601" claim deduplicated to a single
candidate, not two) and weighs one coincidence in the tail
(`#dev-updates`'s message `SLK-4102`'s claim about #603, confidence 0.5,
posted a few hours before the pinned test clock), while correctly
excluding `#bugs`'s message `SLK-4103`'s claim about #602 (true —
merged), `#random`'s message `SLK-4104`'s claim about #999 (no such PR
exists), and `#general`'s message `SLK-4105` (no claim phrase at all,
just a bare "#605" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/slack-message-claims-unmerged-pr/recipe.json
```
