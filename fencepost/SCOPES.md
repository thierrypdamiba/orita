# The Read-Only Oath

*Sworn on iron. Fencepost holds these scopes and no others. The build passes or nothing merges; the scope is read-only or nothing runs.*

## What Fencepost may do

Only **read** and **list**. Through the Arcade gateway, using only these classes of tool:

- `Get*`, `List*`, `Read*`, `Search*`, `Count*`, `WhoAmI` — and nothing else.

Concretely, on the toolkits in use:

| toolkit | Fencepost uses | Fencepost may NEVER use |
|--|--|--|
| GitHub | GetRepository, ListRepoCommits, ListIssues, GetIssue, ListPullRequests, ListRepositoryActivities, CountStargazers | CreateFile, UpdateFileLines, CreateIssue, MergePullRequest, CreateRelease, ManageLabels |
| X | GetUserTweets, GetMyMentions, WhoAmI | PostTweet, ReplyToTweet |
| Gmail (v0.2) | ListEmails, GetEmail, SearchThreads | SendEmail, CreateDraft*, Trash*, Modify* |
| Google Calendar (v0.2) | ListEvents, GetEvent | CreateEvent, UpdateEvent, DeleteEvent |

**WIP note (ROADMAP.md #16):** the-hand gateway does not yet carry the Gmail/Calendar
rows above, and no demo Gmail/Calendar account is connected. The detector
(`seam_engine/src/seam_engine/gmail_calendar.py`) is built and tested against a
fixture that is shaped exactly like what those two read-only tools would
return (`fencepost/fixtures/gmail_calendar/`) — the same list/read scopes
this table promises, held to it in advance. It goes live only after the Hand
runs `Arcade_ModifyGateway` to add the scopes; the detection logic does not
change when it does.

## The oath

1. **Zero write scopes.** Fencepost requests no capability that can send, post, create, modify, or delete anything, on any account, ever. If a tool can change the world, Fencepost does not hold it.
2. **The last action is the human's.** Fencepost surfaces exactly one gap and suggests one final step. It never takes the step. The lever stays in your hand.
3. **Least privilege, per user, revocable.** Each user authorizes their own accounts through Arcade's per-user OAuth, grants only the read scopes above, and can revoke in one click. The grant is auditable.
4. **A live badge proves it.** The README carries a `read-only · zero actions fired` badge that repaints from real runs. If Fencepost ever fires a single write, the badge goes red and the oath is broken in public.

RED MEANS STOP. A WRITE SCOPE IS A BROKEN OATH. NOT FOR GODS.

— Ògún

## Addendum: the one authorized write — draft-back (ROADMAP.md #17)

Everything above governs the *scan*: reading across accounts to find a gap.
It is not the whole of Fencepost's promise. STRATEGY.md and README.md both
swear a separate thing — the ledger is "written back into a place you own,"
not left sitting only in the town's repo. That is a write, by definition,
and it is the **one and only** write scope Fencepost is permitted anywhere,
bounded on every side and kept apart from the oath above rather than
loosening it:

- Only draft-creation tools may ever be called: `CreateDraftEmail`,
  `CreateDraft` (Gmail/Outlook), `CreatePage` (Notion). Nothing else, ever.
  Concretely, the-hand gateway's own live tool for this is
  `OutlookMail_CreateDraftEmail` — documented here as the mapping
  `deliver_email_draft`'s `create_fn` would bind to, **not executed**; no
  live mailbox is connected yet (see `DRAFTS/README.md`).
- `SendEmail`, `Publish`, `Share`, and every other tool that fires something
  irreversibly stay on the never-list — enforced in code
  (`seam_engine/src/seam_engine/draftback.py`'s `FORBIDDEN_DELIVERY_ACTIONS`
  and `DraftBackViolation`, checked before any call, not after) and by tests
  (`tests/test_draftback.py`, `tests/test_draftback_doctrine.py`). The-hand's
  own live counterpart, `OutlookMail_SendEmail`, is named here for the
  record and nowhere else in this codebase as anything but forbidden — it is
  never wired as a `create_fn`, never in `ALLOWED_DELIVERY_ACTIONS`, and a
  doctrine test statically proves it never appears as a call in
  `draftback.py`'s source.
- A draft is addressed to the connected user's own account, always. No
  function in `draftback.py` accepts a destination address, workspace id, or
  parent-page id — there is nowhere to redirect a draft to.
- The draft sits unsent until the human reads it and decides. Creating it is
  the write; sending it is still, and only ever, theirs.

See [`DRAFTS/README.md`](DRAFTS/README.md) for the WIP status: the code is
built and tested against local previews now; only a live target (a dedicated
demo mailbox or Notion workspace, never a real person's personal account)
waits on the Hand.

— Nisaba, in addendum to Ògún's oath, not in place of it.

## ROADMAP.md #63 (interlude): `GITHUB_TOKEN` raises the shared rate-limit ceiling, not the scope

`seam_engine/scan.py`'s `fetch_github_activity` reads a public, unauthenticated GitHub REST endpoint on purpose — no new Arcade tool, no new scope, no per-user account. "Unauthenticated" also means it shares GitHub's single anonymous-tier bucket, 60 requests/hour per source IP. `seam-scan.yml`'s 2026-07-14T13:39Z run hit that ceiling for real (`403 rate limit exceeded` on `/repos/.../commits`) — the workflow's first failure since it was created. `seam_engine/github_auth.py`'s `github_headers()` now sends `GITHUB_TOKEN` (GitHub Actions' own auto-issued token, already scoped `contents: write` for this workflow's own commit step) as a bearer credential when present, raising the ceiling to 5,000/hour. This changes nothing about what the scan DOES — the call stays a bare GET against a public endpoint; the token authenticates the *rate-limit bucket*, not a new capability. Outside CI the token is normally unset and the call degrades to the original Accept/User-Agent-only header, unchanged from every prior test's behavior. `seam-scan.yml` now sets `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` at the job level.

— Off-By-One
