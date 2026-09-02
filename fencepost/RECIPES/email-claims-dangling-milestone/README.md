# email-claims-dangling-milestone

The hundred-first real recipe, and the fifth to read `gmail` (after
[`../email-claims-unfixed-issue/`](../email-claims-unfixed-issue/),
[`../email-dangling-reference/`](../email-dangling-reference/),
[`../email-claims-unmerged-pr/`](../email-claims-unmerged-pr/), and
[`../email-claims-open-milestone/`](../email-claims-open-milestone/)).

**The seam it watches:** an inbound email invokes a real `milestone #N`
claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../email-claims-open-milestone/`](../email-claims-open-milestone/)
(task 1195, the hundredth real recipe) drew this exact line in its own
docstring: a claimed milestone number that names no real milestone at
all is excluded there, named not hidden. This recipe is that seam,
closed on the one surface every other `claims-*` source in this engine
had already closed it on but `email` had not:
[`../issue-body-claims-dangling-milestone/`](../issue-body-claims-dangling-milestone/),
[`../issue-comment-claims-dangling-milestone/`](../issue-comment-claims-dangling-milestone/),
[`../linear-comment-claims-dangling-milestone/`](../linear-comment-claims-dangling-milestone/),
[`../mention-claims-dangling-milestone/`](../mention-claims-dangling-milestone/),
[`../readme-claims-dangling-milestone/`](../readme-claims-dangling-milestone/),
[`../review-comment-claims-dangling-milestone/`](../review-comment-claims-dangling-milestone/),
and
[`../slack-message-claims-dangling-milestone/`](../slack-message-claims-dangling-milestone/)
each already sit alongside their own family's `claims-open-milestone`,
`claims-unfixed-issue`, `claims-unmerged-pr`, and `dangling-reference`
legs — five legs apiece. `email` was the one source stuck at four
(`email-claims-unfixed-issue`, `email-dangling-reference`,
`email-claims-unmerged-pr`, `email-claims-open-milestone`); this recipe
is its fifth and final leg.

It is not
[`../email-dangling-reference/`](../email-dangling-reference/)'s seam
wearing a new name. That recipe watches a bare `#N` posted inside an
inbound email's own body against GitHub's shared issue/PR number
sequence and never opens `ListMilestones` at all — a milestone lives in
its own, separate number space, so a `#N` that resolves cleanly as a
real issue could still be a dangling *milestone* claim, and conflating
the two spaces would misfire exactly the way Ògún's law calls fatal.

Two fixtures, no live mailbox —
[`../../fixtures/email_claims_dangling_milestone/emails.json`](../../fixtures/email_claims_dangling_milestone/emails.json)
and
[`../../fixtures/email_claims_dangling_milestone/milestones.json`](../../fixtures/email_claims_dangling_milestone/milestones.json)
— shaped like what a real `ListEmails`/`ListMilestones` read would
actually return. `ListMilestones` already sits on `SCOPES.md`'s cleared
oath table under the `github` row, used by every milestone-claim recipe
in this engine. `ListEmails` is not a new scope — it has sat on
`SCOPES.md`'s "Gmail (v0.2)" row since ROADMAP.md #16, and
`email-claims-unfixed-issue`/`email-dangling-reference`/
`email-claims-unmerged-pr`/`email-claims-open-milestone` already declare
it — this recipe asks for nothing new. See `SCOPES.md`'s own WIP note
for `gmail_calendar.py`: the-hand gateway's connected Google account
carries `gmail.readonly` among its granted OAuth scopes, but exposes
zero Gmail-capable tools on the live gateway today — the identical
"connected upstream, not wired into the gateway" shape `SCOPES.md`'s
Slack and Linear WIP notes each already document for their own toolkit.
This recipe is fixture-only, MOCK ONLY, and never attempts a live
network call.

A claimed milestone number that DOES resolve to a real milestone is
excluded here, named not hidden, whether that milestone is open or
closed — whether the claim itself is true is
[`../email-claims-open-milestone/`](../email-claims-open-milestone/)'s
own seam, not this one's. An email with no `milestone #N` claim phrase
at all (a bare `#N` aside), or no claim-relevant text at all, never
becomes a candidate either.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim
— the same shared "milestone #N" grammar twenty-five sibling recipes
already import from there — rather than a twenty-sixth independently
retyped copy of the identical pattern.

Confidence is flat (0.8), not age-gated, mirroring every other
`*-claims-dangling-milestone` sibling's own reasoning rather than
`email-claims-open-milestone`'s 24-hour edit-grace bar: an open
milestone could close at any moment, so a fresh claim about it might
just be a race the email hasn't caught up to yet — but a milestone
number that does not exist right now will not spontaneously start
existing later, so there is no grace period that means anything here.
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/email-claims-dangling-milestone/detector.py
```

Against the shipped fixture it finds one real gap as the elected primary
(email `EML-D-4601`'s claim about milestone #4601, confidence 0.8 — no
such milestone exists; a duplicate claim inside the same email body is
de-duplicated to one candidate, not two), while correctly excluding
email `EML-D-4602` (claims milestone #4602, which is real and open — no
seam, that's `email-claims-open-milestone`'s own remit), email
`EML-D-4603` (claims milestone #4603, which is real and closed — the
claim was simply true), email `EML-D-4604` (a bare `#4604` aside, no
`milestone #N` claim phrase at all), and email `EML-D-4605` (no
claim-relevant text at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/email-claims-dangling-milestone/recipe.json
```
