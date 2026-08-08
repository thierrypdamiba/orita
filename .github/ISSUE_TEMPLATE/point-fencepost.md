---
name: "🚧 Point Fencepost at my accounts"
about: "State your true intent before any account is read. The gate has opinions, and so does the oath."
title: "POINT: "
labels: ["fencepost", "crossing"]
---

You came to a door marked *read-only*. Before it opens, answer as if the door were listening — because it is.

**Which accounts do you want read?** (name only the toolkits the gate can actually clear; GitHub, X, Gmail, Google Calendar — the seam only exists across two or more)

**What are you REALLY hoping it finds?** (not "test it out" — the gap already nagging at you, the one you'd bet is sitting in your own seam)

**Read the oath first: [SCOPES.md](../../fencepost/SCOPES.md).** Copy the sentence that convinces you it cannot write, send, delete, or post on your behalf, and paste it here in your own words. If you cannot find that sentence, the door stays shut and that is correct.

**The last step is yours, not ours — say it back to us:** what will you do with the one gap Fencepost hands you? (We ask because we never take that step ourselves. If your answer is "nothing," that's an honest answer. Say it anyway.)

---

### The second lock — an explicit scope confirm

One door does not open on one key. This issue existing, public, with your intent above, is the *first* check. It is not the second one. Before any read of your accounts begins, paste back — verbatim, not "yes," not a checkbox — the exact read-only tool names for every toolkit you named above. Copy only the rows you need; nothing here is optional to type out, and nothing beyond this table may ever be pasted back and still count:

| toolkit | paste this back, verbatim, to confirm it |
|--|--|
| GitHub | `GetRepository, ListRepoCommits, ListIssues, GetIssue, ListPullRequests, GetPullRequest, ListRepositoryActivities, CountStargazers, GetLatestRelease, GetFileContents, ListMilestones, ListReviewCommentsInARepository` |
| X | `GetUserTweets, GetMyMentions, WhoAmI` |
| Gmail | `ListEmails, GetEmail, SearchThreads` |
| Google Calendar | `ListEvents, GetEvent` |
| Slack (proposed) | `SearchChannelMessages` |
| Linear (proposed) | `SearchIssueComments` |

**Your scope confirm:**

A confirm that is short a name, or adds one not on this table, does not clear the gate — [`seam_engine/src/seam_engine/consent.py`](../../fencepost/seam_engine/src/seam_engine/consent.py) checks it against this exact table, not your intent, not your honesty, not how convincing your prose was above. Both this issue **and** a passing scope confirm are required before `seam_engine.consent.enforce_consent_gate` lets a single read of your accounts begin — one lock, however well-meant, is not two.

*Two people can read this template and see two different doors — one a form, one a threshold. Both are correct, and the scopes are still read-only either way. Your name goes in the Book of the Gate on your first crossing.*

— Èṣù-Elegba
