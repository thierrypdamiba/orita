# slack-message-claims-unfixed-issue

The sixty-seventh real recipe, and the first to read a toolkit besides
`github`/`x` at all. Every one of the 66 recipes before it declared a
`toolkit` of `github`, `github+x`, or `x+github` — grepped, not assumed
(`python3 -c "..."` over every `RECIPES/*/recipe.json`'s own `toolkit`
field, zero hits for anything else). This recipe proposes `slack+github`,
the same way [`../../seam_engine/src/seam_engine/gmail_calendar.py`](../../seam_engine/src/seam_engine/gmail_calendar.py)
proposed `gmail`/`google_calendar` before either had a live scope —
[`../../CONTRIBUTING.md`](../../CONTRIBUTING.md)'s own "New toolkits"
section sanctions exactly this.

**The seam it watches:** the Slack-side twin of
[`../mention-claims-unfixed-issue/`](../mention-claims-unfixed-issue/) (the
X-mention leg of the claims-unfixed-issue family). A message posted to a
Slack channel uses a real GitHub closing-keyword phrase against an issue
number — "heads up, fixes #3101 and closes #3101 again, should be all set
now", "resolves #3103 with the migration script, nice" — but issue #N is
still open. A message sitting in a Slack channel is exactly as durable and
readable-later as a tweet or a mention once posted, and nothing on
Slack's side (or GitHub's) ever checks a channel claim against the issue
tracker's real state. Two fixtures, no live workspace —
[`../../fixtures/slack_message_claims_unfixed_issue/messages.json`](../../fixtures/slack_message_claims_unfixed_issue/messages.json)
and
[`.../issues.json`](../../fixtures/slack_message_claims_unfixed_issue/issues.json)
— shaped like what a real `SearchChannelMessages`/`ListIssues` read would
return.

`ListIssues` is already cleared on `SCOPES.md`'s oath table under the
`github` row. `SearchChannelMessages` is the new scope this recipe asks
for — it clears `seam_engine.recipes.validate_recipe`'s oath the same way
every other scope in this engine does: it matches the allowed `Search*`
prefix and contains none of the forbidden write words. See `SCOPES.md`'s
own WIP note: the-hand gateway holds a real, live, upstream `arcade-slack`
connection today, but exposes zero Slack-capable tools on the live
gateway — the identical "connected upstream, not wired into the gateway"
shape `SCOPES.md`'s Gmail/Calendar WIP note already documents for a
different toolkit. This recipe is fixture-only, MOCK ONLY, and never
attempts a live network call.

A claimed issue that doesn't exist at all is excluded here, named not
hidden — that broken reference is a future Slack-side dangling-reference
recipe's own seam, not this one's. A claimed issue that IS closed is
excluded too — the claim was simply true. A message with no
closing-keyword phrase at all (a bare "see #N" mention, or no `#N` at all)
never becomes a candidate either — it never claims anything about a
second record, so there is no seam to weigh. Nothing in this recipe's own
`headline`/`detail` text ever names or grades whoever posted the message —
`CONTRIBUTING.md`'s "No grading, ever" law, same as every recipe in this
engine.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim — the
same shared grammar thirteen sibling recipes already import directly
(`commit-closes-keyword-issue-still-open`,
`commit-closes-keyword-issue-closed-not-planned`,
`commit-closes-keyword-pr-still-open`, `issue-closed-never-released`,
`issue-closed-pr-still-open`, `issue-comment-claims-unfixed-issue`,
`mention-claims-unfixed-issue`, `merged-pr-issue-still-open`,
`merged-pr-pr-still-open`, `milestone-claims-unfixed-issue`,
`release-claims-unfixed-issue`, `review-comment-claims-unfixed-issue`,
`tweet-claims-unfixed-issue`) — rather than a fourteenth independently
retyped copy of the identical pattern. "Closing #N" (present participle)
never matches either tense here either, same as everywhere else this
grammar is used.

**Confidence holds `mention-claims-unfixed-issue`'s/
`tweet-claims-unfixed-issue`'s own 0.85/0.5 bar exactly — not an
independently re-reasoned number just because the toolkit is new.**
Age-gated by hours since the message's own `ts`: a claim checked within 24
hours of posting might still be a race (the real fix landing moments
after the message went out) rather than a settled public overclaim (0.5,
below the confidence bar, shown as a weighed coincidence, not hidden). At
or past 24 hours with the named issue still open, it is unambiguous (flat
0.85). The check itself is objective: the claimed issue's own live `state`
field, verified against `ListIssues`, not a guess about which tracker the
poster meant. See `recipe.json`'s `confidence_notes` for the full
reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/slack-message-claims-unfixed-issue/detector.py
```

Run bare like this it uses the real wall clock, so the fixture messages'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`SLK-3101`'s claim
about #3101, confidence 0.85, its own duplicated "fixes #3101 ... closes
#3101" claim deduplicated to a single candidate, not two) and weighs one
coincidence in the tail (`SLK-3102`'s claim about #3103, confidence 0.5,
posted a few hours before the pinned test clock), while correctly
excluding `SLK-3103`'s claim about #3102 (true — closed), `SLK-3104`'s
claim about #3999 (no such issue exists), and `SLK-3105` (no
closing-keyword claim at all, just a bare "#3105" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/slack-message-claims-unfixed-issue/recipe.json
```
