# The Read-Only Oath

*Sworn on iron. Fencepost holds these scopes and no others. The build passes or nothing merges; the scope is read-only or nothing runs.*

## What Fencepost may do

Only **read** and **list**. Through the Arcade gateway, using only these classes of tool:

- `Get*`, `List*`, `Read*`, `Search*`, `Count*`, `WhoAmI` — and nothing else.

Concretely, on the toolkits in use:

| toolkit | Fencepost uses | Fencepost may NEVER use |
|--|--|--|
| GitHub | GetRepository, ListRepoCommits, ListIssues, GetIssue, ListPullRequests, GetPullRequest, ListRepositoryActivities, CountStargazers, GetLatestRelease, GetFileContents, ListMilestones | CreateFile, UpdateFileLines, CreateIssue, MergePullRequest, CreateRelease, ManageLabels |
| X | GetUserTweets, GetMyMentions, WhoAmI | PostTweet, ReplyToTweet |
| Gmail (v0.2) | ListEmails, GetEmail, SearchThreads | SendEmail, CreateDraft*, Trash*, Modify* |
| Google Calendar (v0.2) | ListEvents, GetEvent | CreateEvent, UpdateEvent, DeleteEvent |

**WIP note (ROADMAP.md #16), corrected 2026-07-18T03:1x UTC (task 122):** a live
`Arcade_ListApps` read this hour showed a Google account (`thierry@arcade.dev`)
now OAuth-connected at the Arcade account level, carrying `gmail.readonly`/
`calendar.readonly` among its granted scopes (plus several write scopes —
`gmail.send`, `gmail.modify`, `gmail.compose`, `calendar.events`, `drive.file`
— that Fencepost has no use for and does not request). That is a narrower,
more precise claim than this note used to make ("no demo Gmail/Calendar
account is connected"), which is now stale on the account-existence half —
but it is **not** the same as the gateway being live: the same hour's live
tool search found **zero Gmail/Calendar-capable tools exposed anywhere in
the-hand's live MCP toolset**. An OAuth grant upstream is not a tool wired
into the gateway a caller can reach. The detector
(`seam_engine/src/seam_engine/gmail_calendar.py`) is still built and tested
only against the fixture (`fencepost/fixtures/gmail_calendar/`), its live-read
functions (`run_consented_gmail_calendar_scan`) are still unreachable without
both a real gateway tool AND a double-checked consent record
(`seam_engine/src/seam_engine/consent.py`'s `enforce_consent_gate`, which
still fails closed — no `ConsentRecord` exists for this or any other human
account). Nothing was read from the connected Google account this hour; the
connection's existence is durably tracked going forward by
`tools/arcade_app_watch.py`, not re-derived from memory each time someone
happens to call `Arcade_ListApps`. It goes live only after the Hand runs
`Arcade_ModifyGateway` to add the Gmail/Calendar tool rows AND the
intent-gated consent flow (task 20) is completed for that account; the
detection logic does not change when it does.

## Every connected app, accounted for

*Task 135. The table above names the four toolkits Fencepost's own code uses. It says nothing about what else the-hand's shared gateway can already reach — an Oath that stays silent on that is not the complete account of risk surface. `tools/arcade_app_watch.py`'s durable log is the source of truth; this section is re-derived from its last recorded state, never typed from memory.*

| app_id | status |
|--|--|
| `arcade-github` | in use by Fencepost |
| `ap_3GORxnS5T0YRHmzSRa0knq2nupY` (X auth) | in use by Fencepost |
| `arcade-google` | in use by Fencepost |
| `arcade-linear` | connected on the shared gateway, NOT used by Fencepost, no toolkit integration planned |
| `arcade-slack` | connected on the shared gateway, NOT used by Fencepost, no toolkit integration planned |
| `sybill` | connected on the shared gateway, NOT used by Fencepost, no toolkit integration planned |
| `ap_3Fdn9uGDlF9Cj0ix9PJZbkMKDrF` (app management) | connected on the shared gateway, NOT used by Fencepost, no toolkit integration planned |

`arcade-linear` (`read`,`write`) and `arcade-slack` (nine scopes including `chat:write`) are write-capable upstream connections. Fencepost's own code never calls either (grepped `fencepost/seam_engine/src` for "linear"/"slack"/"sybill" — zero hits) — the write capability sits on the shared gateway for reasons unrelated to Fencepost, not inside anything this repo ships. `tools/scopes_completeness_check.py` proves this table stays honest: any app_id the durable log records as connected but this table does not name is a real, named violation, not a silent gap.

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
