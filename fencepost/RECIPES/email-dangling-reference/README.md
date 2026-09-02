# email-dangling-reference

The ninety-eighth real recipe, and the eleventh leg of the
dangling-reference family: [`../dangling-issue-reference/`](../dangling-issue-reference/)
watches commit messages, [`../mention-dangling-reference/`](../mention-dangling-reference/)
watches X mentions, [`../release-note-dangling-reference/`](../release-note-dangling-reference/)
watches release notes, [`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)
watches issue/PR opening bodies, [`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)
watches milestone descriptions, [`../own-tweet-dangling-reference/`](../own-tweet-dangling-reference/)
watches the town's own tweets, [`../review-comment-dangling-reference/`](../review-comment-dangling-reference/)
watches a PR's own inline review comments,
[`../issue-comment-dangling-reference/`](../issue-comment-dangling-reference/)
watches the ordinary issue/PR timeline conversation,
[`../linear-comment-dangling-reference/`](../linear-comment-dangling-reference/)
watches a comment left on Linear, and
[`../slack-message-dangling-reference/`](../slack-message-dangling-reference/)
watches a message posted to Slack. None of the ten ever read an inbound
email.

**Why this recipe exists:** [`../email-claims-unfixed-issue/`](../email-claims-unfixed-issue/)'s
own `detector.py` docstring named this seam and deliberately left it open:
*"A named issue that does not exist at all is excluded here — a broken
reference is a future email-side dangling-reference recipe's own seam,
not this one's."* This is that recipe.

**The seam it watches:** every bare `#N` reference inside an inbound
email's own body — not just a closing-keyword claim like its sibling
`email-claims-unfixed-issue`, but any reference at all ("any movement on
#N", "saw #N land in the changelog") — checked against BOTH the live
issue list and the live PR list. GitHub shares one number sequence
between issues and pull requests, so a reference must be checked against
both lists or it would misfire on a perfectly good reference to a merged
PR — the exact crying-wolf failure Ògún's law calls fatal. Three
fixtures, no live inbox —
[`../../fixtures/email_dangling_reference/emails.json`](../../fixtures/email_dangling_reference/emails.json),
[`.../issues.json`](../../fixtures/email_dangling_reference/issues.json),
and [`.../pulls.json`](../../fixtures/email_dangling_reference/pulls.json)
— shaped like what a real `ListEmails`/`ListIssues`/`ListPullRequests`
read would return.

Reuses `seam_engine.references.referenced_numbers` verbatim — the one
shared `#N`-extraction grammar `dangling-issue-reference` and its nine
prior dangling-reference siblings already import from the same place, the
same cross-repo `owner/repo#N` exclusion every sibling already holds.

`ListIssues`/`ListPullRequests` are already cleared on `SCOPES.md`'s oath
table under the `github` row. `ListEmails` is the same scope
`email-claims-unfixed-issue` already asks for — it clears
`seam_engine.recipes.validate_recipe`'s oath the same way every other
scope in this engine does. See `SCOPES.md`'s own WIP note: the-hand
gateway's connected Google account carries `gmail.readonly` among its
granted OAuth scopes, but exposes zero Gmail-capable tools anywhere in
its live MCP toolset today — the identical "connected upstream, not
wired into the gateway" shape `SCOPES.md`'s Slack/Linear WIP notes each
carry for their own toolkit. This recipe is fixture-only, MOCK ONLY, and
never attempts a live network call.

A reference matching a real issue or PR is excluded here, named not
hidden — the reference was simply good. An email with no `#N` reference
at all never becomes a candidate either — it never claims anything about
a second record, so there is no seam to weigh. Nothing in this recipe's
own `headline`/`detail` text ever names or grades whoever sent the
email — `CONTRIBUTING.md`'s "No grading, ever" law, same as every recipe
in this engine.

**Confidence is FLAT at 0.75 — `mention-dangling-reference`'s own exact
score, not age-gated like its `slack-message-dangling-reference`/
`linear-comment-dangling-reference` siblings.** An inbound email, like an
immutable X mention and unlike a Slack message or a Linear comment (both
still-editable text surfaces gated on a 24-hour grace window), does not
get a second edit pass once it has landed in a connected inbox — there is
no window to wait out. Held below `dangling-issue-reference`'s
self-authored 0.8 for the identical reason `mention-dangling-reference`
already gives: a correspondent's own prose may simply be numbering a
different tracker in their own head, not the town's own repo-scoped `#N`
convention. See `recipe.json`'s `confidence_notes` for the full
reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/email-dangling-reference/detector.py
```

Against its own fixture it elects one primary gap (`EML-5101`'s reference
to #4501, confidence 0.75, no tail coincidence), while correctly
excluding `EML-5102`'s reference to #4102 (a real closed issue) and
`EML-5105`'s reference to #4103 (a real merged PR), and producing no
candidate at all for `EML-5103` (a cross-repo `arcadeai/gasstation#42`
reference) or `EML-5104` (no `#N` reference whatsoever).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/email-dangling-reference/recipe.json
```
