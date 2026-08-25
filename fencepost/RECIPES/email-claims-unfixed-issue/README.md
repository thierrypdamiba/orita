# email-claims-unfixed-issue

The ninety-third real recipe, and the first to read `gmail` at all. Every
one of the 92 recipes before it declared a `toolkit` of `github`,
`github+x`, `x+github`, `slack+github`, `linear+github`, or
`github+google_calendar` — grepped, not assumed (`python3 -c "..."` over
every `RECIPES/*/recipe.json`'s own `toolkit` field, zero hits for
`gmail` anywhere). This recipe proposes `gmail+github`, the same way
[`../../seam_engine/src/seam_engine/gmail_calendar.py`](../../seam_engine/src/seam_engine/gmail_calendar.py)
proposed `gmail`/`google_calendar` before either had a live scope —
[`../../CONTRIBUTING.md`](../../CONTRIBUTING.md)'s own "New toolkits"
section sanctions exactly this. `SCOPES.md`'s own "Gmail (v0.2)" row has
sat on the cleared oath table since ROADMAP.md #16, cited by
`slack-message-claims-unfixed-issue`, `linear-comment-claims-unfixed-
issue`, and `milestone-deadline-no-calendar-event` each time one of them
opened a different new toolkit — but until this recipe, nothing under
`RECIPES/` had ever actually declared it.

**The seam it watches:** the Gmail-side twin of
[`../mention-claims-unfixed-issue/`](../mention-claims-unfixed-issue/) (the
X-mention leg), [`../slack-message-claims-unfixed-issue/`](../slack-message-claims-unfixed-issue/)
(the Slack-channel leg), and [`../linear-comment-claims-unfixed-issue/`](../linear-comment-claims-unfixed-issue/)
(the Linear-comment leg) of the `claims-unfixed-issue` family. An inbound
email uses a real GitHub closing-keyword phrase against an issue number —
"heads up, fixes #4101 and closes #4101 again, should be all set now",
"resolves #4103 with the migration script, nice" — but issue #N is still
open. An email sitting in a connected inbox is exactly as durable and
readable-later as a tweet, a mention, a Slack message, or a Linear
comment once received, and nothing on Gmail's side (or GitHub's) ever
checks an inbox claim against the issue tracker's real state. Two
fixtures, no live mailbox —
[`../../fixtures/email_claims_unfixed_issue/emails.json`](../../fixtures/email_claims_unfixed_issue/emails.json)
and
[`.../issues.json`](../../fixtures/email_claims_unfixed_issue/issues.json)
— shaped like what a real `ListEmails`/`ListIssues` read would return.

`ListIssues` is already cleared on `SCOPES.md`'s oath table under the
`github` row. `ListEmails` is not a new scope — it has sat on `SCOPES.md`'s
"Gmail (v0.2)" row since ROADMAP.md #16 — but this is the first recipe to
actually declare it, and it clears `seam_engine.recipes.validate_recipe`'s
oath the same way every other scope in this engine does: it matches the
allowed `List*` prefix and contains none of the forbidden write words.
See `SCOPES.md`'s own WIP note for `gmail_calendar.py`: the-hand gateway's
connected Google account carries `gmail.readonly` among its granted OAuth
scopes, but exposes zero Gmail-capable tools on the live gateway today —
the identical "connected upstream, not wired into the gateway" shape
`SCOPES.md`'s Slack and Linear WIP notes each already document for their
own toolkit. This recipe is fixture-only, MOCK ONLY, and never attempts a
live network call.

A claimed issue that doesn't exist at all is excluded here, named not
hidden — that broken reference is a future email-side dangling-reference
recipe's own seam, not this one's. A claimed issue that IS closed is
excluded too — the claim was simply true. An email with no
closing-keyword phrase at all (a bare "see #N" mention, or no `#N` at all)
never becomes a candidate either — it never claims anything about a
second record, so there is no seam to weigh. Nothing in this recipe's own
`headline`/`detail` text ever names or grades whoever sent the email —
`CONTRIBUTING.md`'s "No grading, ever" law, same as every recipe in this
engine.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim — the
same shared grammar fifteen sibling recipes already import directly
(`commit-closes-keyword-issue-still-open`,
`commit-closes-keyword-issue-closed-not-planned`,
`commit-closes-keyword-pr-still-open`, `issue-closed-never-released`,
`issue-closed-pr-still-open`, `issue-comment-claims-unfixed-issue`,
`linear-comment-claims-unfixed-issue`, `mention-claims-unfixed-issue`,
`merged-pr-issue-still-open`, `merged-pr-pr-still-open`,
`milestone-claims-unfixed-issue`, `release-claims-unfixed-issue`,
`review-comment-claims-unfixed-issue`, `slack-message-claims-unfixed-issue`,
`tweet-claims-unfixed-issue`) — rather than a sixteenth independently
retyped copy of the identical pattern. "Closing #N" (present participle)
never matches either tense here either, same as everywhere else this
grammar is used.

**Confidence holds `mention-claims-unfixed-issue`'s/`slack-message-claims-
unfixed-issue`'s/`linear-comment-claims-unfixed-issue`'s own 0.85/0.5 bar
exactly — not an independently re-reasoned number just because the
toolkit is new.** Age-gated by hours since the email's own `received_at`:
a claim checked within 24 hours of the email landing might still be a
race (the real fix landing moments after the email went out) rather than
a settled overclaim (0.5, below the confidence bar, shown as a weighed
coincidence, not hidden). At or past 24 hours with the named issue still
open, it is unambiguous (flat 0.85). The check itself is objective: the
claimed issue's own live `state` field, verified against `ListIssues`, not
a guess about which tracker the sender meant. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/email-claims-unfixed-issue/detector.py
```

Run bare like this it uses the real wall clock, so the fixture emails'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`EML-4101`'s claim
about #4101, confidence 0.85, its own duplicated "fixes #4101 ... closes
#4101" claim deduplicated to a single candidate, not two) and weighs one
coincidence in the tail (`EML-4102`'s claim about #4103, confidence 0.5,
received a few hours before the pinned test clock), while correctly
excluding `EML-4103`'s claim about #4102 (true — closed), `EML-4104`'s
claim about #4999 (no such issue exists), and `EML-4105` (no
closing-keyword claim at all, just a bare "#4105" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/email-claims-unfixed-issue/recipe.json
```
