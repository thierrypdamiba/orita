# notion-page-dangling-reference

The hundred-and-fifteenth real recipe, and the eleventh leg of the
dangling-reference family:
[`../dangling-issue-reference/`](../dangling-issue-reference/) watches
commit messages, [`../mention-dangling-reference/`](../mention-dangling-reference/)
watches X mentions, [`../release-note-dangling-reference/`](../release-note-dangling-reference/)
watches release notes, [`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)
watches issue/PR opening bodies, [`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)
watches milestone descriptions, [`../own-tweet-dangling-reference/`](../own-tweet-dangling-reference/)
watches the town's own tweets, [`../review-comment-dangling-reference/`](../review-comment-dangling-reference/)
watches a PR's own inline review comments,
[`../issue-comment-dangling-reference/`](../issue-comment-dangling-reference/)
watches the ordinary issue/PR timeline conversation,
[`../linear-comment-dangling-reference/`](../linear-comment-dangling-reference/)
watches a comment left on Linear, and
[`../slack-message-dangling-reference/`](../slack-message-dangling-reference/)
watches a message posted to a Slack channel. None of the ten ever read a
page written in Notion.

**Why this recipe exists:** issue [#7](https://github.com/thierrypdamiba/orita/issues/7),
"good first issue: write a seam recipe nobody's built yet." Notion had
only ever been named once on `../../SCOPES.md`'s oath table, for
`CreatePage` -- `draftback.py`'s one authorized write, rendering the
ledger's own sealed record as an unpublished page in the connected
user's own workspace. No recipe had ever asked to *read* a Notion page.
This is the first.

**The seam it watches:** every bare `#N` reference inside a Notion
page's own title or body text -- checked against BOTH the live issue
list and the live PR list. GitHub shares one number sequence between
issues and pull requests, so a reference must be checked against both
lists or it would misfire on a perfectly good reference to a merged PR
-- the exact crying-wolf failure Ogun's law calls fatal. Three fixtures,
no live workspace --
[`../../fixtures/notion_page_dangling_reference/pages.json`](../../fixtures/notion_page_dangling_reference/pages.json),
[`.../issues.json`](../../fixtures/notion_page_dangling_reference/issues.json),
and [`.../pulls.json`](../../fixtures/notion_page_dangling_reference/pulls.json)
-- shaped like what a real `SearchPages`/`ListIssues`/`ListPullRequests`
read would return.

Reuses `seam_engine.references.referenced_numbers` verbatim -- the one
shared `#N`-extraction grammar `dangling-issue-reference` and its nine
other dangling-reference siblings already import from the same place,
the same cross-repo `owner/repo#N` exclusion every sibling already
holds.

**The oath grew by one toolkit to ship this recipe.** `SearchPages` is
new to `consent.REQUIRED_SCOPES` this task -- Notion's own read-side
analog of `slack`'s `SearchChannelMessages` and `linear`'s
`SearchIssueComments`, both already cleared. `../../SCOPES.md`'s table
and `.github/ISSUE_TEMPLATE/point-fencepost.md`'s scope-confirm table
were extended in the same commit, the exact "all three files together,
or the recipe should not be asking" discipline
`seam_engine.recipes.validate_recipe`'s own error message names. The-hand
gateway exposes zero Notion-read tools today -- the identical
"registered on the Oath, not yet wired into the gateway" shape
`SCOPES.md`'s Gmail/Calendar/Slack/Linear WIP notes already document for
four other toolkits. This recipe is fixture-only, MOCK ONLY, and never
attempts a live network call.

A reference matching a real issue or PR is excluded here, named not
hidden -- the reference was simply good. A page with no `#N` reference
at all never becomes a candidate either -- it never claims anything
about a second record, so there is no seam to weigh. Nothing in this
recipe's own `headline`/`detail` text ever names or grades whoever wrote
the page -- `CONTRIBUTING.md`'s "No grading, ever" law, same as every
recipe in this engine.

**Confidence holds `issue-comment-dangling-reference`'s,
`linear-comment-dangling-reference`'s, and
`slack-message-dangling-reference`'s own 0.85/0.55 edit-grace-window bar
exactly (24 hours) -- not an independently re-reasoned number just
because the toolkit is new again.** A Notion page, like an ordinary
GitHub issue comment, a Linear comment, or a Slack message and unlike an
immutable X mention, is a text surface its author can still edit at any
time: a reference caught within 24 hours of the page's own
`last_edited_at` may simply not have been fixed yet, scoring the lower
bar (0.55, below the confidence bar, shown as a weighed coincidence, not
hidden); at or past 24 hours it is unambiguous (flat 0.85). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/notion-page-dangling-reference/detector.py
```

Run bare like this it uses the real wall clock, so the fixture pages'
ages will drift as real time passes -- expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (the page "Incident
review -- cron slowness"'s reference to #6301, confidence 0.85) and
weighs one coincidence in the tail (the page "Sprint notes -- week 32"'s
reference to #6302, confidence 0.55, edited a few hours before the
pinned test clock), while correctly excluding "Known issues tracker"'s
reference to #6210 (a real open issue) and "Changelog draft"'s reference
to #6220 (a real merged PR), and producing no candidate at all for
"Onboarding checklist" (no `#N` reference whatsoever).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/notion-page-dangling-reference/recipe.json
```
