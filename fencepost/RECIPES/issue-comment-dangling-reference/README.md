# issue-comment-dangling-reference

The fifty-third real recipe, and an eighth leg of the dangling-reference
family alongside [`../dangling-issue-reference/`](../dangling-issue-reference/)
(the fourth real recipe, commit messages),
[`../mention-dangling-reference/`](../mention-dangling-reference/) (the
eighteenth, X mentions),
[`../release-note-dangling-reference/`](../release-note-dangling-reference/)
(the twenty-third, release notes),
[`../issue-body-dangling-reference/`](../issue-body-dangling-reference/) (the
thirty-fourth, issue and PR opening bodies),
[`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)
(the forty-first, milestone descriptions),
[`../own-tweet-dangling-reference/`](../own-tweet-dangling-reference/) (the
forty-second, the town's own tweets), and
[`../review-comment-dangling-reference/`](../review-comment-dangling-reference/)
(the forty-fourth, a pull request's own inline review comments). None of the
seven ever read the ordinary **timeline conversation** — the comments a
human or a bot leaves on an issue or pull request's own discussion thread,
not anchored to any diff line, a genuinely different GitHub object from both
the opening body `issue-body-dangling-reference` covers and the inline
review thread `review-comment-dangling-reference` covers.

**The seam it watches:** the same blind spot every sibling recipe already
proved, now on the one text surface GitHub visits more than almost any
other. "Same root cause as #501" or "blocked on #N" gets typed into an
ordinary issue or PR comment constantly — on either object, since GitHub's
own issue-comments endpoint is shared between issues and pull requests (a
PR is a special issue under the hood, which is why this recipe's own
`issue_number` field can name either one) — and GitHub renders every `#N`
there as a clickable link with no check that it resolves to anything. A
`#N` inside a comment's own body is checked against BOTH the issue list and
the PR list — GitHub shares one number sequence between them, so checking
only one would misfire on a perfectly good reference to a merged PR sitting
inside an issue's own comment thread, exactly the crying-wolf failure
Ogun's law calls fatal.

**The honest gap this recipe names, not hides:** unlike its closest sibling
`review-comment-dangling-reference` (whose `ListReviewCommentsInARepository`
scope is a real, live, read-only tool on the-hand gateway today), no live
tool shaped like "list ordinary issue/PR comments" is exposed on the-hand
gateway as of this recipe's own merge — checked live the same hour this
recipe was written. `recipe.json` therefore declares only the two scopes
that ARE already cleared on `SCOPES.md`'s oath table (`ListIssues`,
`ListPullRequests`) — it does not invent or claim a third scope the Oath
never swore to, which `seam_engine.recipes.validate_recipe`'s own check 3/3
would refuse on sight regardless. `SCOPES.md` carries this recipe's own WIP
note, the identical "detection logic is real today, the live read waits on
the Hand's gateway" shape `gmail_calendar.py` already carries for a
different toolkit entirely. The detector's own logic does not change one
line the day a live tool appears; only the loader swaps from a fixture to a
real call.

Three fixture lists, no live account —
[`../../fixtures/issue_comment_dangling_reference/issue_comments.json`](../../fixtures/issue_comment_dangling_reference/issue_comments.json),
[`.../issues.json`](../../fixtures/issue_comment_dangling_reference/issues.json),
and
[`.../pulls.json`](../../fixtures/issue_comment_dangling_reference/pulls.json)
— shaped like what a live issue-comments read plus `ListIssues` and
`ListPullRequests` would actually return.

A cross-repo reference (`owner/repo#N`) is never even extracted as a
candidate — that names a different repo's own number space on purpose. A
comment with no body at all never becomes a candidate either — it never
claims anything about a second record, so there is no seam to weigh. This
recipe imports `seam_engine.references.referenced_numbers` rather than
writing an eighth copy of the same extraction regex — the same "one law,
not an eighth copy of it" discipline this whole family already pays for.

**Confidence mirrors `review-comment-dangling-reference`, `issue-body-
dangling-reference`, and `milestone-body-dangling-reference` exactly, for
the same reason.** An ordinary comment, like a review comment, an issue/PR
body, or a milestone description, is a text surface its own author can
still edit at any time, and a typo'd `#N` gets corrected in the ordinary
course of conversation constantly, so this recipe age-gates against the
comment's own `updated_at`: a dangling reference touched less than 24 hours
ago scores 0.55 (may still get fixed), one that has sat untouched for at
least 24 hours scores 0.85 (nobody is coming back for it). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/issue-comment-dangling-reference uv run python ../RECIPES/issue-comment-dangling-reference/detector.py
```

Against its own fixture it elects exactly one primary gap (comment #7002's
stale reference to "#9999", 24+ hours since its own last update, confidence
0.85) and weighs one coincidence in the tail (comment #7003's fresh
reference to "#8888", 2 hours since its own last update, confidence 0.55).
It correctly excludes comment #7001's reference to the real issue #501,
comment #7006's reference to the real PR #510, a cross-repo reference
(`arcadeai/gasstation#42` in comment #7005), a comment with no body at all
(#7004), and a comment whose body carries no `#N` reference (#7007).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-comment-dangling-reference/recipe.json
```
