# mention-claims-unfixed-issue

The forty-seventh real recipe. The missing mention-side leg of the
claims-unfixed-issue family alongside
[`../readme-claims-unfixed-issue/`](../readme-claims-unfixed-issue/),
[`../release-claims-unfixed-issue/`](../release-claims-unfixed-issue/),
[`../milestone-claims-unfixed-issue/`](../milestone-claims-unfixed-issue/),
and [`../tweet-claims-unfixed-issue/`](../tweet-claims-unfixed-issue/) — all
four already check whether a real GitHub closing-keyword claim ("fixes #N" /
"closes #N" / "resolves #N") made on a text surface the town itself
controls (its own README, its own release notes, its own milestone
descriptions, its own tweets) actually holds against the issue tracker.
None of them ever read the one surface those four never touch: a
**stranger's own mention** of the account. The same tweet-vs-mention split
[`../mention-dangling-reference/`](../mention-dangling-reference/) already
opened against
[`../own-tweet-dangling-reference/`](../own-tweet-dangling-reference/) for
the dangling-reference family, applied here to a claims-X seam instead.

**The seam it watches:** a mortal mentions the connected account on X using
a real GitHub closing-keyword phrase against an issue number — "so glad you
finally fixed #2101!", "heard you resolves #2103 with that hotfix" — but
issue #N is still open. A mention is exactly as permanent and public as a
tweet once posted, and nothing on X's side (or GitHub's) ever checks a
stranger's own claim against the issue tracker's real state. Two fixtures,
no live account —
[`../../fixtures/mention_claims_unfixed_issue/mentions.json`](../../fixtures/mention_claims_unfixed_issue/mentions.json)
and
[`.../issues.json`](../../fixtures/mention_claims_unfixed_issue/issues.json)
— shaped like what `GetMyMentions` and `ListIssues` would actually return.
`GetMyMentions` has sat cleared on `SCOPES.md`'s oath table since founding
(first used by mention-dangling-reference, the eighteenth real recipe);
`ListIssues` is used by nearly every recipe in this engine. No new scope is
asked for anywhere in this recipe.

A claimed issue that doesn't exist at all is excluded here, named not
hidden — that broken reference belongs to
[`../dangling-issue-reference/`](../dangling-issue-reference/)'s /
`mention-dangling-reference`'s own seam, not this one's. A claimed issue
that IS closed is excluded too — the claim was simply true. A mention with
no closing-keyword phrase at all (a bare "see #N" follow-up, or no `#N` at
all) never becomes a candidate either — it never claims anything about a
second record, so there is no seam to weigh.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim — the
same shared grammar `tweet-claims-unfixed-issue`,
`release-claims-unfixed-issue`, `commit-closes-keyword-issue-still-open`,
and `issue-closed-never-released` already import from there — rather than a
fifth independently retyped copy of the identical pattern. "Closing #N"
(present participle) never matches either tense here either, same as
everywhere else this grammar is used.

**Confidence mirrors `tweet-claims-unfixed-issue`'s own 0.85/0.5 bar
exactly — not a discounted copy of it.** Age-gated by hours since the
mention's own `created_at`: a claim checked within 24 hours of posting
might still be a race (the real fix landing moments after the mention went
out) rather than a settled public overclaim (0.5, below the confidence
bar, shown as a weighed coincidence, not hidden). At or past 24 hours with
the named issue still open, it is unambiguous (flat 0.85). This is
deliberately NOT `mention-dangling-reference`'s own flat, discounted 0.75 —
that recipe's lower score accounts for a mortal's own uncertain grasp of
the repo's number space (they may simply be numbering an entirely
different tracker in their own head). That uncertainty doesn't apply here:
the check this recipe makes is objective, the claimed issue's own live
`state` field verified against `ListIssues`, not the mortal's guess. A
mortal cannot be "wrong about the number space" and still land a real,
existing issue number attached to a real closing-keyword claim. See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/mention-claims-unfixed-issue/detector.py
```

Run bare like this it uses the real wall clock, so the fixture mentions'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`M-2101`'s claim about
#2101, confidence 0.85, posted ~52 hours before the pinned test clock, and
its own duplicated "fixed #2101 ... closed #2101" claim deduplicated to a
single candidate, not two) and weighs one coincidence in the tail
(`M-2102`'s claim about #2103, confidence 0.5, 4 hours old at the pinned
test clock), while correctly excluding `M-2103`'s claim about #2102 (true —
closed), `M-2104`'s claim about #2999 (no such issue —
dangling-issue-reference's/mention-dangling-reference's own seam), and
`M-2105` (no closing-keyword claim at all, just a bare "#2105" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/mention-claims-unfixed-issue/recipe.json
```
