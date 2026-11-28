# notion-page-claims-unfixed-issue

The hundred-and-sixteenth real recipe, and the first Notion leg of the
claims-unfixed-issue family:
[`../release-claims-unfixed-issue/`](../release-claims-unfixed-issue/)
watches a release body's own closing-keyword claim, and
[`../tweet-claims-unfixed-issue/`](../tweet-claims-unfixed-issue/) watches
the identical shape one platform over, against a tweet from the
connected X account. Neither has ever read a page written in Notion.
[`../notion-page-dangling-reference/`](../notion-page-dangling-reference/)
(ROADMAP.md #2729, the hundred-fifteenth real recipe) opened Notion as a
read source, but only for the dangling-reference family -- no claims-*
family has ever had a Notion leg before this one.

**Why this recipe exists:** issue [#7](https://github.com/thierrypdamiba/orita/issues/7),
"good first issue: write a seam recipe nobody's built yet" -- the same
standing invitation `notion-page-dangling-reference` answered for Notion
reads in general. This closes the specific gap left after that task:
Notion could be read, but only checked against dangling `#N` mentions,
never against its own "I fixed this" claims.

**The seam it watches:** a closing-keyword phrase (`fixes #N` / `closes
#N` / `resolves #N`, both tenses) inside a Notion page's own title+body
text names a GitHub issue by number. If that issue does not exist at
all, that's `notion-page-dangling-reference`'s own seam, not this one's
-- excluded here, named not hidden. If it exists and is closed, the
page's claim was simply true -- excluded, named not hidden. If it exists
and is still open, the page's own durable written record disagrees with
reality: that is the gap. Two fixtures, no live workspace --
[`../../fixtures/notion_page_claims_unfixed_issue/pages.json`](../../fixtures/notion_page_claims_unfixed_issue/pages.json)
and
[`.../issues.json`](../../fixtures/notion_page_claims_unfixed_issue/issues.json)
-- shaped like what a real `SearchPages`/`ListIssues` read would return.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim -- the
same shared grammar `release-claims-unfixed-issue`,
`tweet-claims-unfixed-issue`, `commit-closes-keyword-issue-still-open`,
and `issue-closed-never-released` already import from there.

**No new scope asked for.** `SearchPages` and `ListIssues` both already
sit cleared on [`../../SCOPES.md`](../../SCOPES.md)'s table --
`SearchPages` was added by `notion-page-dangling-reference` in the prior
task. This recipe is fixture-only, MOCK ONLY, same WIP shape every other
non-GitHub/X toolkit in this engine already carries: the-hand's live
gateway exposes zero Notion-read tools today.

A claimed issue that doesn't exist at all is excluded here, named not
hidden -- that broken reference belongs to `notion-page-dangling-
reference`'s own seam, not this one's. A claimed issue that IS closed is
excluded too -- the claim was simply true. Only the issue tracker is
checked, not the PR tracker, by design, mirroring the family's existing
release-vs-tweet split between claims-unfixed-issue (issues) and
claims-unmerged-pr (PRs); a future `notion-page-claims-unmerged-pr` would
be the PR-side twin, left for whoever answers issue #7 next.

**Confidence holds `notion-page-dangling-reference`'s and
`issue-comment-claims-unfixed-issue`'s own 0.85/0.55 edit-grace-window
bar exactly (24 hours) -- not the 0.85/0.5 bar
`linear-comment-claims-unfixed-issue` and
`slack-message-claims-unfixed-issue` use for their own editable
surfaces** (a pre-existing inconsistency between those two detectors and
their own dangling-reference siblings, left alone here -- that drift
belongs to those recipes to resolve, not a reason to pick a third number
for this one). A Notion page, like an ordinary GitHub issue comment, is
a text surface its author can still edit at any time: a claim checked
within 24 hours of the page's own `last_edited_at` may simply not have
been fixed yet, scoring the lower bar (0.55, below the confidence bar,
shown as a weighed coincidence, not hidden); at or past 24 hours it is
unambiguous (flat 0.85). See `recipe.json`'s `confidence_notes` for the
full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/notion-page-claims-unfixed-issue/detector.py
```

Run bare like this it uses the real wall clock, so the fixture pages'
ages will drift as real time passes -- expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (the page
`NTN-C-9101`'s claim that `#1101` is fixed, confidence 0.85) and weighs
one coincidence in the tail (the page `NTN-C-9102`'s claim that `#1103`
is resolved, confidence 0.55, edited a few hours before the pinned test
clock), while correctly excluding `NTN-C-9103`'s true claim about the
already-closed `#1102`, `NTN-C-9104`'s claim naming the nonexistent
`#1999`, and producing no candidate at all for `NTN-C-9105` (no
closing-keyword claim whatsoever).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/notion-page-claims-unfixed-issue/recipe.json
```
