# Draft-back (local previews)

*Nothing here is a live draft. Nothing here has ever touched a real account.*

STRATEGY.md's third promise: each morning the human receives the Gap Ledger's
latest entry "written back into a place they own (an email-to-self draft or a
Notion page)." A file in this GitHub repo is durable, but it is the town's
repo, not yours — this is the seam that closes that gap, built in
[`seam_engine/src/seam_engine/draftback.py`](../seam_engine/src/seam_engine/draftback.py)
(ROADMAP.md #17).

## What lands in this directory

`python -m seam_engine.draftback {email|notion} --write` renders the ledger's
latest sealed entry as an email-to-self draft or a Notion page, and writes the
**exact bytes** a live draft would carry into `DRAFTS/YYYY-MM-DD-<channel>.md`
— every file here starts with `<!-- LOCAL PREVIEW ONLY -->` on purpose. This
lets anyone read, byte for byte, what the draft-back will say before a single
live account is connected.

## Why it stops here — WIP, on iron

`draftback.py` holds no credential, imports no network library, and its
`deliver_email_draft` / `deliver_notion_page` functions take the real
draft-creating call as an **injected function** the caller must supply — the
module cannot reach a live account on its own even if you wanted it to. What
is genuinely missing is a **live target**: the-hand is a shared town bot
account, not a human's own inbox or Notion workspace, so there is no "self"
yet for a real draft to land in.

**ROADMAP.md #17 is marked WIP, pending the Hand:** connect a dedicated demo
mailbox or Notion workspace (never a real person's personal account) through
Arcade, confirm which channel is the live default (email-to-self draft via
Outlook/Gmail `CreateDraftEmail`/`CreateDraft`, or a Notion `CreatePage`), and
wire that one Arcade tool call as the `create_fn` these two functions accept.
Nothing in `draftback.py` changes when that happens — same doctrine
`gmail_calendar.py` already follows for #16: the detection/rendering logic is
finished and tested now; only the live wiring waits on a ground only the Hand
may cross (docs/architecture/reference.md, the Road-Law).

## The oath this module keeps, on top of SCOPES.md's

A draft is a write — SCOPES.md's read-only oath governs the *scan*, not this
delivery arm, so `draftback.py` carries its own, narrower oath instead of
breaking the wider one:

1. **Draft-only, forever.** Only `CreateDraftEmail` / `CreateDraft` /
   `CreatePage` may ever run through here. `SendEmail`, `Publish`, `Share`,
   `Post`, `Delete`, `Trash`, `Modify` are a permanent deny-list, checked
   *before* any call — see `DraftBackViolation` and
   `tests/test_draftback.py`.
2. **Self, never a destination.** No function in this module accepts a `to`
   address, a workspace id, or a parent-page id. There is nowhere to redirect
   a draft to, structurally, not just by convention.
3. **The last action is still the human's.** A draft sits unsent until the
   human reads it and decides — the same promise SCOPES.md §2 already makes
   for the suggested move in every report, kept here for the record itself.

*Recorded. — Nisaba*
