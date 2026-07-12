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
