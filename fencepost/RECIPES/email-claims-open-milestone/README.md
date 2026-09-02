# email-claims-open-milestone

The hundredth real recipe, and the fourth to read `gmail` (after
[`../email-claims-unfixed-issue/`](../email-claims-unfixed-issue/), the
ninety-third, [`../email-dangling-reference/`](../email-dangling-reference/),
the ninety-eighth, and [`../email-claims-unmerged-pr/`](../email-claims-unmerged-pr/),
the ninety-ninth). The one leg the `claims-open-milestone` family had never
grown since `gmail` became a live toolkit in this engine:
[`../commit-claims-open-milestone/`](../commit-claims-open-milestone/),
[`../issue-body-claims-open-milestone/`](../issue-body-claims-open-milestone/),
[`../issue-comment-claims-open-milestone/`](../issue-comment-claims-open-milestone/),
[`../linear-comment-claims-open-milestone/`](../linear-comment-claims-open-milestone/),
[`../mention-claims-open-milestone/`](../mention-claims-open-milestone/),
[`../milestone-claims-open-milestone/`](../milestone-claims-open-milestone/),
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/),
[`../release-claims-open-milestone/`](../release-claims-open-milestone/),
[`../review-comment-claims-open-milestone/`](../review-comment-claims-open-milestone/),
[`../slack-message-claims-open-milestone/`](../slack-message-claims-open-milestone/),
and [`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/) all
already check the identical "milestone #N" claim grammar against eleven
other text surfaces, every one of them wired up before `gmail` was ever a
live toolkit here at all. This recipe is that twelfth leg, applied to the
Gmail surface [`../email-claims-unfixed-issue/`](../email-claims-unfixed-issue/)
already opened — the same "twin the inbound siblings" shape that recipe
already drew for the `claims-unfixed-issue` family, drawn here one more
time for the milestone-claim family instead.

**The seam it watches:** a claim phrase ("milestone #N", case-insensitive)
inside an inbound email's own body names a milestone by number — "big one
— milestone #4501 finally shipped and milestone #4501 confirmed again,
thanks all" — but milestone #N is still open. An email sitting in a
connected inbox is exactly as durable and readable-later as a Linear
comment, a Slack message, a tweet, or a mention once received, and
nothing on Gmail's side (or GitHub's) ever checks an inbox claim against
the milestone tracker's real state. Two fixtures, no live mailbox —
[`../../fixtures/email_claims_open_milestone/emails.json`](../../fixtures/email_claims_open_milestone/emails.json)
and
[`.../milestones.json`](../../fixtures/email_claims_open_milestone/milestones.json)
— shaped like what a real `ListEmails`/`ListMilestones` read would return.

`ListMilestones` is already cleared on `SCOPES.md`'s oath table under the
`github` row, used by every milestone-claim recipe in this engine.
`ListEmails` is not a new scope — it has sat on `SCOPES.md`'s "Gmail
(v0.2)" row since ROADMAP.md #16, and `email-claims-unfixed-issue`/
`email-dangling-reference`/`email-claims-unmerged-pr` already declare it
— but this recipe asks for nothing new. See `SCOPES.md`'s own WIP note
for `gmail_calendar.py`: the-hand gateway's connected Google account
carries `gmail.readonly` among its granted OAuth scopes, but exposes zero
Gmail-capable tools on the live gateway today — the identical "connected
upstream, not wired into the gateway" shape `SCOPES.md`'s Slack and
Linear WIP notes each already document for their own toolkit. This
recipe is fixture-only, MOCK ONLY, and never attempts a live network
call.

A claimed milestone that doesn't exist at all is excluded here, named
not hidden — that broken reference is
[`../email-dangling-reference/`](../email-dangling-reference/)'s own
seam, not this one's (a bare `#N` and a `milestone #N` claim phrase name
different number spaces). A claimed milestone that IS closed is excluded
too — the claim was simply true. An email with no claim phrase at all (a
bare "see #N" mention, or no `#N` at all) never becomes a candidate
either — it never claims anything about a second record, so there is no
seam to weigh. Nothing in this recipe's own `headline`/`detail` text ever
names or grades whoever sent the email — `CONTRIBUTING.md`'s "No
grading, ever" law, same as every recipe in this engine.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim
— the same shared "milestone #N" grammar twelve sibling recipes already
import from there — rather than a thirteenth independently retyped copy
of the identical pattern.

**Confidence holds `linear-comment-claims-open-milestone`'s/
`email-claims-unmerged-pr`'s own 0.85/0.5 bar exactly — not an
independently re-reasoned number just because the toolkit is new.**
Age-gated by hours since the email's own `received_at`: a claim checked
within 24 hours of the email landing might still be a race (the
milestone actually closing out moments after the email went out) rather
than a settled overclaim (0.5, below the confidence bar, shown as a
weighed coincidence, not hidden). At or past 24 hours with the named
milestone still open, it is unambiguous (flat 0.85). The check itself is
objective: the claimed milestone's own live `state` field, verified
against `ListMilestones`, not a guess about which tracker the sender
meant. See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/email-claims-open-milestone/detector.py
```

Run bare like this it uses the real wall clock, so the fixture emails'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture, pinned at the test suite's own clock, it elects
one primary gap (`EML-4501`'s claim about milestone #4501, confidence
0.85, its own duplicated "milestone #4501 ... milestone #4501" claim
deduplicated to a single candidate, not two), while weighing one
coincidence in the tail (`EML-4502`'s claim about milestone #4503,
confidence 0.5, received a few hours before the pinned test clock) and
correctly excluding `EML-4503`'s claim about milestone #4502 (true —
closed), `EML-4504`'s claim about milestone #4999 (no such milestone
exists), and `EML-4505` (no claim phrase at all, just a bare "#4505"
mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/email-claims-open-milestone/recipe.json
```
