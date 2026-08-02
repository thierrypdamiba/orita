# star-milestone-not-announced

The thirty-first real recipe, and the first to read `CountStargazers` —
on `SCOPES.md`'s oath table since the first day, alongside
`GetLatestRelease` and `ListMilestones`, but never exercised by a shipped
recipe until now.

**The seam it watches:** a repository's live star count crosses a
round-number milestone (10, 100, 1000, ...) — a real, screenshotable,
one-line fact — but no tweet from the connected X account ever announces
it. Neither side alone shows the gap: the count alone says nothing about
what was said elsewhere, and a tweet history alone can't be checked
against a number it never names. Only the single HIGHEST milestone the
live count has crossed is ever considered — a repo sitting at 267 stars
crossed 250, not 100 or 50 too, and only the biggest round number actually
earns the announcement.

Two fixtures, no live account —
[`../../fixtures/star_milestone_not_announced/stargazers.json`](../../fixtures/star_milestone_not_announced/stargazers.json)
and
[`../../fixtures/star_milestone_not_announced/tweets.json`](../../fixtures/star_milestone_not_announced/tweets.json)
— shaped like what `CountStargazers`/`GetUserTweets` would actually
return, both already on `SCOPES.md`'s cleared oath table. No new scope is
asked for anywhere in this recipe.

Unlike every prior recipe in the "shipped but not tweeted" family
(`release-not-tweeted`, `milestone-closed-not-tweeted`,
`merged-pr-not-tweeted`, `issue-closed-not-tweeted`), this one carries no
age-gate: `CountStargazers` returns a live snapshot, not a timestamped
crossing event, so there is no "may simply not have tweeted yet" grace
window to compute — a crossed-and-silent milestone is either announced or
it is not, at flat confidence 0.85. See `recipe.json`'s `confidence_notes`
for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/star-milestone-not-announced/detector.py
```

The shipped fixture (267 stars, no tweet naming 250) elects the primary
gap for real:

```json
{
  "slug": "star-milestone-250-not-announced",
  "headline": "250 stars, never announced",
  "confidence": 0.85
}
```
