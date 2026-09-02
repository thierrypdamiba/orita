# email-claims-unmerged-pr

The ninety-ninth real recipe, and the third to read `gmail` (after
[`../email-claims-unfixed-issue/`](../email-claims-unfixed-issue/), the
ninety-third, and [`../email-dangling-reference/`](../email-dangling-reference/),
the ninety-eighth). The twelfth leg of the `claims-unmerged-pr` family:
[`../commit-claims-unmerged-pr/`](../commit-claims-unmerged-pr/),
[`../readme-claims-unmerged-pr/`](../readme-claims-unmerged-pr/),
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/),
[`../milestone-claims-unmerged-pr/`](../milestone-claims-unmerged-pr/),
[`../issue-body-claims-unmerged-pr/`](../issue-body-claims-unmerged-pr/),
[`../issue-comment-claims-unmerged-pr/`](../issue-comment-claims-unmerged-pr/),
[`../review-comment-claims-unmerged-pr/`](../review-comment-claims-unmerged-pr/),
and [`../tweet-claims-unmerged-pr/`](../tweet-claims-unmerged-pr/) each check
a "shipped it" claim the town made about ITSELF, somewhere it fully
controls; [`../mention-claims-unmerged-pr/`](../mention-claims-unmerged-pr/),
[`../slack-message-claims-unmerged-pr/`](../slack-message-claims-unmerged-pr/),
and [`../linear-comment-claims-unmerged-pr/`](../linear-comment-claims-unmerged-pr/)
check the identical claim against three inbound surfaces the town does not
control. None of those eleven ever read an inbound email — this recipe is
that twelfth leg, the Gmail-side twin of the three inbound ones, the same
"twin the inbound siblings, not the town-controlled ones" shape
[`../email-claims-unfixed-issue/`](../email-claims-unfixed-issue/) already
drew for the sibling `claims-unfixed-issue` family.

**The seam it watches:** a claim phrase ("ships #N" / "includes #N" /
"merges #N" / "via #N", case-insensitive) inside an inbound email's own
body names a pull request by number — "heads up, ships #5101 and includes
#5101 again, should be all set now", "merges #5103 with the migration
script, nice" — but PR #N never actually merged. An email sitting in a
connected inbox is exactly as durable and readable-later as a tweet, a
mention, a Slack message, or a Linear comment once received, and nothing
on Gmail's side (or GitHub's) ever checks an inbox claim against the PR
tracker's real state. Two fixtures, no live mailbox —
[`../../fixtures/email_claims_unmerged_pr/emails.json`](../../fixtures/email_claims_unmerged_pr/emails.json)
and
[`.../pulls.json`](../../fixtures/email_claims_unmerged_pr/pulls.json) —
shaped like what a real `ListEmails`/`ListPullRequests` read would return.

`ListPullRequests` is already cleared on `SCOPES.md`'s oath table under
the `github` row. `ListEmails` is not a new scope — it has sat on
`SCOPES.md`'s "Gmail (v0.2)" row since ROADMAP.md #16, and
`email-claims-unfixed-issue`/`email-dangling-reference` already declare
it — but this recipe asks for nothing new. See `SCOPES.md`'s own WIP note
for `gmail_calendar.py`: the-hand gateway's connected Google account
carries `gmail.readonly` among its granted OAuth scopes, but exposes zero
Gmail-capable tools on the live gateway today — the identical "connected
upstream, not wired into the gateway" shape `SCOPES.md`'s Slack and
Linear WIP notes each already document for their own toolkit. This
recipe is fixture-only, MOCK ONLY, and never attempts a live network
call.

A claimed PR that doesn't exist at all is excluded here, named not hidden
— that broken reference is
[`../email-dangling-reference/`](../email-dangling-reference/)'s own
seam, not this one's. A claimed PR that IS merged is excluded too — the
claim was simply true. An email with no claim phrase at all (a bare
"see #N" mention, or no `#N` at all) never becomes a candidate either —
it never claims anything about a second record, so there is no seam to
weigh. Nothing in this recipe's own `headline`/`detail` text ever names
or grades whoever sent the email — `CONTRIBUTING.md`'s "No grading,
ever" law, same as every recipe in this engine.

Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim — the same
shared "ships/includes/merges/via #N" grammar every `claims-unmerged-pr`
sibling already imports from there — rather than a twelfth independently
retyped copy of the identical pattern.

**Confidence holds `mention-claims-unmerged-pr`'s/`slack-message-claims-
unmerged-pr`'s/`linear-comment-claims-unmerged-pr`'s own 0.85/0.5 bar
exactly — not an independently re-reasoned number just because the
toolkit is new.** Age-gated by hours since the email's own `received_at`:
a claim checked within 24 hours of the email landing might still be a
race (the real merge landing moments after the email went out) rather
than a settled overclaim (0.5, below the confidence bar, shown as a
weighed coincidence, not hidden). At or past 24 hours with the named PR
still unmerged, it is unambiguous (flat 0.85). The check itself is
objective: the claimed PR's own live `state`/`merged` fields, verified
against `ListPullRequests`, not a guess about which tracker the sender
meant. See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/email-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture emails'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`EML-5101`'s claim
about #5101, confidence 0.85, its own duplicated "ships #5101 ...
includes #5101" claim deduplicated to a single candidate, not two), while
weighing one coincidence in the tail (`EML-5102`'s claim about #5103,
confidence 0.5, received a few hours before the pinned test clock) and
correctly excluding `EML-5103`'s claim about #5102 (true — merged),
`EML-5104`'s claim about #5999 (no such PR exists), and `EML-5105` (no
claim phrase at all, just a bare "#5105" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/email-claims-unmerged-pr/recipe.json
```
