# readme-star-count-stale

The hundred-thirteenth real recipe (ROADMAP.md #1647). The README's own
hardcoded prose star-count claim ("900+ stars", "⭐ 900 GitHub stars") has
fallen behind the live count.

**The seam it watches:** a README written once, by hand, often says
something like "⭐ 900 GitHub stars and counting" — a real, true sentence
the day it was typed. Nothing on GitHub's side or the README's own side
ever comes back to check it again. `GetFileContents` alone shows what the
README currently says; `CountStargazers` alone shows what the live count
currently is — only holding both at once shows the gap between a claim
that used to be true and a live number that has since moved past it.

Distinct from the closest sibling,
[`../star-milestone-not-announced/`](../star-milestone-not-announced/):
that recipe watches whether a crossed round-number star threshold (10, 100,
1000, ...) ever got announced in a tweet — an EVENT that may or may not
have been spoken. This recipe watches a different seam entirely: a number
already written down, in prose, inside the README itself, that the live
count has since outgrown — a STATEMENT that used to be true and quietly
stopped being. A repo can satisfy the sibling recipe (a live tweet
announcing a crossed milestone) while this recipe's own gap sits
unaddressed underneath it (the README still says an old, smaller number),
and vice versa — neither implies the other.

A trailing `+` on a claimed number ("900+ stars") is read as an at-least
claim, not an exact one. It is not exempted outright — a claim that has
genuinely gone stale is still surfaced even with a `+` — but it does mean
a live count only slightly above the claimed floor is still a true
statement, not a gap. The staleness floor itself is `max(25, 5%)` of the
claimed number, so a one- or two-star drift between a README edit and a
live re-read is treated as ordinary clock skew, never crying wolf over
noise (Ogun's law).

Two fixtures, no live account —
[`../../fixtures/readme_star_count_stale/readme.json`](../../fixtures/readme_star_count_stale/readme.json)
and
[`../../fixtures/readme_star_count_stale/stargazers.json`](../../fixtures/readme_star_count_stale/stargazers.json)
— shaped like what `GetFileContents`/`CountStargazers` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table. No new
scope is asked for anywhere in this recipe.

Confidence is flat 0.7 on a surfaced gap — a real drift is unambiguous
once past the staleness floor, but a hand-typed prose number carries more
ordinary slack than a structured field like a tag or a manifest version,
so it sits below `manifest-version-never-tagged`'s own 0.75. A claim that
already matches or exceeds the live count is excluded at confidence 0.0 —
either the claim is still true, or it overclaims, and overclaiming is a
different, separate gap this recipe does not attempt to judge.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/readme-star-count-stale/detector.py
```

It finds one real gap in its own fixture as the elected primary
(`README.md` claiming 900 stars against a live count of 1400, confidence
0.7), while correctly excluding `docs/community.md` (claims "1380+", live
count 1400 is only 20 past it — under the staleness floor, still
effectively true) and `NOTES.md` (makes no star-count claim at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/readme-star-count-stale/recipe.json
```
