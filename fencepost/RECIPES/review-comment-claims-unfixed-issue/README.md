# review-comment-claims-unfixed-issue

The fifty-fourth real recipe. The missing review-comment-side leg of the
claims-unfixed-issue family alongside
[`../readme-claims-unfixed-issue/`](../readme-claims-unfixed-issue/),
[`../release-claims-unfixed-issue/`](../release-claims-unfixed-issue/),
[`../milestone-claims-unfixed-issue/`](../milestone-claims-unfixed-issue/),
[`../tweet-claims-unfixed-issue/`](../tweet-claims-unfixed-issue/), and
[`../mention-claims-unfixed-issue/`](../mention-claims-unfixed-issue/) —
those five already check whether a real GitHub closing-keyword claim
("fixes #N" / "closes #N" / "resolves #N") holds against the issue
tracker, but every one of them reads either a surface the town itself
controls (its own README, release notes, milestone descriptions, tweets)
or a stranger's inbound X mention. None of them ever read a GitHub-native
surface at all. This recipe reuses
[`../review-comment-dangling-reference/`](../review-comment-dangling-reference/)'s
own live `ListReviewCommentsInARepository` scope and fixture shape — that
recipe asked only whether a review comment's `#N` reference exists; this
one asks the claims-X family's sharper question of the identical surface:
does the claim actually hold.

**The seam it watches:** a pull request's own inline code review comment
invokes a real GitHub closing-keyword phrase against an issue number —
"this also fixes #2101 while we're in here", "I think this resolves
#2103 too" — but issue #N is still open. The seam is sharper here than on
any of this family's other five legs: a closing keyword only ever
auto-closes an issue when GitHub reads it in a pull request's own BODY or
a commit message that lands on the default branch
([`../commit-closes-keyword-issue-still-open/`](../commit-closes-keyword-issue-still-open/)'s
and
[`../merged-pr-issue-still-open/`](../merged-pr-issue-still-open/)'s own
seam) — it has never once, in GitHub's history, honored a closing keyword
typed into an ordinary review comment. A reviewer's inline "fixes #N" was
never going to close anything regardless of whether the parent PR merges,
which makes a false claim here more durable, not less, than one on a
surface that at least could have triggered a real auto-close. Two
fixtures, no live account —
[`../../fixtures/review_comment_claims_unfixed_issue/review_comments.json`](../../fixtures/review_comment_claims_unfixed_issue/review_comments.json)
and
[`.../issues.json`](../../fixtures/review_comment_claims_unfixed_issue/issues.json)
— shaped like what `ListReviewCommentsInARepository` and `ListIssues`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared
oath table (`ListReviewCommentsInARepository` live since
`review-comment-dangling-reference`, the forty-fourth real recipe;
`ListIssues` used by nearly every recipe in this engine). No new scope is
asked for anywhere in this recipe.

A claimed issue that doesn't exist at all is excluded here, named not
hidden — that broken reference belongs to
[`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)'s
/ `review-comment-dangling-reference`'s own seam, not this one's. A
claimed issue that IS closed is excluded too — the claim was simply true.
A review comment with no closing-keyword phrase at all (a bare "same root
cause as #N" aside, or no `#N` at all) never becomes a candidate, and
neither does a review comment with no body at all — neither claims
anything about a second record, so there is no seam to weigh. Deliberately
checks only the issue list, never the PR list — the identical scope every
sibling `*-claims-unfixed-issue` recipe already holds itself to; a
closing-keyword claim naming a real pull request is a future
`review-comment-claims-unmerged-pr`'s own remit, not this one's.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim — the
same shared grammar `mention-claims-unfixed-issue`,
`tweet-claims-unfixed-issue`, `release-claims-unfixed-issue`,
`commit-closes-keyword-issue-still-open`, and `issue-closed-never-released`
already import from there — rather than a sixth independently retyped
copy of the identical pattern. "Closing #N" (present participle, Iron
Rule #8's own prescribed safe form) never matches either tense here
either, same as everywhere else this grammar is used.

**Confidence is age-gated off the review comment's own `updated_at`,
mirroring `review-comment-dangling-reference`'s own 0.55/0.85 bar rather
than `mention-claims-unfixed-issue`'s/`tweet-claims-unfixed-issue`'s
0.5/0.85 one.** A review comment, like an issue/PR body or a milestone
description, is a text surface its own author can edit at any time —
unlike a mention or a tweet, posted once and standing, there is a real
"may simply not have caught up yet" grace period that means something
here. A claim checked within 24 hours of the comment's own last update
scores 0.55 (below the confidence bar, shown as a weighed coincidence,
not hidden); at or past 24 hours it scores 0.85 (unambiguous — nobody is
coming back to fix it). See `recipe.json`'s `confidence_notes` for the
full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/review-comment-claims-unfixed-issue/detector.py
```

Run bare like this it uses the real wall clock, so the fixture comments'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (review comment 9101's
claim about #2101 on PR #201, confidence 0.85, last updated well past the
24h bar) and weighs two coincidences in the tail (comment 9102's claim
about #2103 on PR #202, and comment 9107's duplicated "fixes #2101 ...
closes #2101" claim on PR #207, both confidence 0.55, both updated inside
the 24h window at the pinned test clock), while correctly excluding
comment 9103's claim about #2102 (true — closed), comment 9104's claim
about #2999 (no such issue —
issue-body-dangling-reference's/review-comment-dangling-reference's own
seam), comment 9105 (no closing-keyword claim at all, just a bare "#2105"
aside), and comment 9106 (no body at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/review-comment-claims-unfixed-issue/recipe.json
```
