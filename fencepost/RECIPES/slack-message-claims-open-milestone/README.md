# slack-message-claims-open-milestone

The sixty-ninth real recipe. The Slack source's second `claims-X` leg,
alongside [`../slack-message-claims-unfixed-issue/`](../slack-message-claims-unfixed-issue/)
(task 599, the sixty-seventh real recipe, and the first recipe under
`RECIPES/` to read a toolkit besides `github`/`x` at all). That recipe
proved the closing-keyword claim leg for a Slack channel message against
the issue tracker; this recipe proves the milestone-claim leg against the
milestone tracker instead -- the identical check
[`../mention-claims-open-milestone/`](../mention-claims-open-milestone/)
(the forty-eighth) already runs against X's own mentions, applied here to
the Slack channel-message surface `slack-message-claims-unfixed-issue`
already opened, not a new pattern independently invented for the
occasion. A third leg, `slack-message-claims-unmerged-pr`, remains open
for a future hour -- this recipe closes one cell of that grid, not all
three.

**The seam it watches:** a message posted to a Slack channel uses a
`milestone #N` claim phrase against a milestone number — "big one --
milestone #4301 finally shipped and milestone #4301 confirmed again,
thanks all", "heard milestone #4303 is done with that quiet cut, nice" —
but milestone #N is still open. A message sitting in a Slack channel is
exactly as durable and readable-later as a tweet or a mention once
posted, and nothing on Slack's side (or GitHub's) ever checks a channel
claim against the milestone tracker's real state. Two fixtures, no live
workspace —
[`../../fixtures/slack_message_claims_open_milestone/messages.json`](../../fixtures/slack_message_claims_open_milestone/messages.json)
and
[`.../milestones.json`](../../fixtures/slack_message_claims_open_milestone/milestones.json)
— shaped like what a real `SearchChannelMessages`/`ListMilestones` read
would return.

`ListMilestones` is already cleared on `SCOPES.md`'s oath table under the
`github` row, used by every milestone-claim recipe already in this
engine. `SearchChannelMessages` is the scope `slack-message-claims-
unfixed-issue` already cleared through `seam_engine.recipes.
validate_recipe`'s oath — this recipe asks for nothing new. See
`SCOPES.md`'s own WIP note: the-hand gateway holds a real, live, upstream
`arcade-slack` connection today, but exposes zero Slack-capable tools on
the live gateway — the identical "connected upstream, not wired into the
gateway" shape `SCOPES.md`'s Gmail/Calendar WIP note already documents
for a different toolkit. This recipe is fixture-only, MOCK ONLY, and
never attempts a live network call.

A claimed milestone that doesn't exist at all is excluded here, named not
hidden — that broken reference is a future Slack-side dangling-reference
recipe's own seam, not this one's. A claimed milestone that IS closed is
excluded too — the claim was simply true. A message with no `milestone
#N` claim phrase at all (a bare "see #N" mention, or no `#N` at all)
never becomes a candidate either — it never claims anything about a
second record, so there is no seam to weigh. Nothing in this recipe's own
`headline`/`detail` text ever names or grades whoever posted the message
— `CONTRIBUTING.md`'s "No grading, ever" law, same as every recipe in
this engine.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim
— the same shared grammar `milestone-closed-never-released`,
`release-claims-open-milestone`, `milestone-closed-not-tweeted`,
`tweet-claims-open-milestone`, and `mention-claims-open-milestone`
already import from there — rather than a sixth independently retyped
copy of the identical pattern.

**Confidence holds `slack-message-claims-unfixed-issue`'s own 0.85/0.5
bar exactly — not an independently re-reasoned number just because the
claim names a milestone instead of an issue.** A Slack channel message is
posted once and stands, the same "post once and stands" shape
`mention-claims-open-milestone`'s/`tweet-claims-open-milestone`'s own
0.85/0.5 bar holds — not `review-comment-claims-open-milestone`'s lower
0.55/0.85 bar, which exists because a review comment can be edited after
posting; a Slack message cannot be un-said the same way a tweet or a
mention cannot. Age-gated by hours since the message's own `ts`: a claim
checked within 24 hours of posting might still be a race (the milestone
actually closing out moments after the message went out) rather than a
settled public overclaim (0.5, below the confidence bar, shown as a
weighed coincidence, not hidden). At or past 24 hours with the named
milestone still open, it is unambiguous (flat 0.85). The check itself is
objective: the claimed milestone's own live `state` field, verified
against `ListMilestones`, not a guess about which tracker the poster
meant. See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/slack-message-claims-open-milestone/detector.py
```

Run bare like this it uses the real wall clock, so the fixture messages'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`SLK-4101`'s claim
about milestone #4301, confidence 0.85, its own duplicated "milestone
#4301 shipped ... milestone #4301 confirmed" claim deduplicated to a
single candidate, not two) and weighs one coincidence in the tail
(`SLK-4102`'s claim about milestone #4303, confidence 0.5, posted a few
hours before the pinned test clock), while correctly excluding
`SLK-4103`'s claim about milestone #4302 (true — closed), `SLK-4104`'s
claim about milestone #4999 (no such milestone exists), and `SLK-4105`
(no `milestone #N` claim phrase at all, just a bare "#4105" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/slack-message-claims-open-milestone/recipe.json
```
