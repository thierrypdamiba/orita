# slack-message-dangling-reference

The seventy-fifth real recipe, and the tenth leg of the dangling-reference
family: [`../dangling-issue-reference/`](../dangling-issue-reference/)
watches commit messages, [`../mention-dangling-reference/`](../mention-dangling-reference/)
watches X mentions, [`../release-note-dangling-reference/`](../release-note-dangling-reference/)
watches release notes, [`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)
watches issue/PR opening bodies, [`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)
watches milestone descriptions, [`../own-tweet-dangling-reference/`](../own-tweet-dangling-reference/)
watches the town's own tweets, [`../review-comment-dangling-reference/`](../review-comment-dangling-reference/)
watches a PR's own inline review comments,
[`../issue-comment-dangling-reference/`](../issue-comment-dangling-reference/)
watches the ordinary issue/PR timeline conversation, and
[`../linear-comment-dangling-reference/`](../linear-comment-dangling-reference/)
watches a comment left on Linear. None of the nine ever read a message
posted to a Slack channel.

**Why this recipe exists:** [`../slack-message-claims-unfixed-issue/`](../slack-message-claims-unfixed-issue/)'s
own `detector.py` docstring named this seam and deliberately left it open:
*"That broken reference belongs to a future Slack-side dangling-reference
recipe, not this one."* This is that recipe.

**The seam it watches:** every bare `#N` reference inside a Slack channel
message's own text -- not just a closing-keyword claim like its sibling
`slack-message-claims-unfixed-issue`, but any reference at all ("same
root cause as #N", "blocked on #N", "the fix landed in #N") -- checked
against BOTH the live issue list and the live PR list. GitHub shares one
number sequence between issues and pull requests, so a reference must be
checked against both lists or it would misfire on a perfectly good
reference to a merged PR -- the exact crying-wolf failure Ògún's law calls
fatal. Three fixtures, no live workspace --
[`../../fixtures/slack_message_dangling_reference/messages.json`](../../fixtures/slack_message_dangling_reference/messages.json),
[`.../issues.json`](../../fixtures/slack_message_dangling_reference/issues.json),
and [`.../pulls.json`](../../fixtures/slack_message_dangling_reference/pulls.json)
-- shaped like what a real `SearchChannelMessages`/`ListIssues`/`ListPullRequests`
read would return.

Reuses `seam_engine.references.referenced_numbers` verbatim -- the one
shared `#N`-extraction grammar `dangling-issue-reference` and its eight
prior dangling-reference siblings already import from the same place, the
same cross-repo `owner/repo#N` exclusion every sibling already holds.

`ListIssues`/`ListPullRequests` are already cleared on `SCOPES.md`'s oath
table under the `github` row. `SearchChannelMessages` is the same scope
`slack-message-claims-unfixed-issue` already asks for -- it clears
`seam_engine.recipes.validate_recipe`'s oath the same way every other
scope in this engine does. See `SCOPES.md`'s own WIP note: the-hand
gateway holds a real, live, upstream `arcade-slack` connection today, but
exposes zero Slack-capable tools on the live gateway -- the identical
"connected upstream, not wired into the gateway" shape `SCOPES.md`'s
Gmail/Calendar and Linear WIP notes already document for two other
toolkits. This recipe is fixture-only, MOCK ONLY, and never attempts a
live network call.

A reference matching a real issue or PR is excluded here, named not
hidden -- the reference was simply good. A message with no `#N` reference
at all never becomes a candidate either -- it never claims anything about
a second record, so there is no seam to weigh. Nothing in this recipe's
own `headline`/`detail` text ever names or grades whoever posted the
message -- `CONTRIBUTING.md`'s "No grading, ever" law, same as every
recipe in this engine.

**Confidence holds `issue-comment-dangling-reference`'s and
`linear-comment-dangling-reference`'s own 0.85/0.55 edit-grace-window bar
exactly (24 hours) -- not an independently re-reasoned number just
because the toolkit is new again.** A Slack message, like an ordinary
GitHub issue comment or a Linear comment and unlike an immutable X
mention, is a text surface its author can still edit at any time: a
reference caught within 24 hours of the message's own `ts` may simply not
have been fixed (or corrected) yet, scoring the lower bar (0.55, below
the confidence bar, shown as a weighed coincidence, not hidden); at or
past 24 hours it is unambiguous (flat 0.85). See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/slack-message-dangling-reference/detector.py
```

Run bare like this it uses the real wall clock, so the fixture messages'
ages will drift as real time passes -- expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`#dev-updates`'s
message `SLK-D-9001`'s reference to #6301, confidence 0.85) and weighs
one coincidence in the tail (`#eng-notes`'s message `SLK-D-9002`'s
reference to #6302, confidence 0.55, posted a few hours before the pinned
test clock), while correctly excluding `#bugs`'s message `SLK-D-9003`'s
reference to #6210 (a real open issue) and `#bugs`'s message `SLK-D-9004`'s
reference to #6220 (a real merged PR), and producing no candidate at all
for `#random`'s message `SLK-D-9005` (no `#N` reference whatsoever).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/slack-message-dangling-reference/recipe.json
```
