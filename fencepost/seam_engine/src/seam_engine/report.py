"""The Fencepost Report — the daily dispatch, not the tablet.

The Ledger (`ledger.py`) keeps everything: the elected gap, every coincidence
weighed and dropped, sealed and hash-chained, for the mortal who comes back a
year later to check the town's arithmetic. The Report is the other half of the
same job and answers to a different reader — the one who has thirty seconds:
one gap, named plainly, and the line the whole arc turns on.

    You were so close. You are always so close.

A report never shows the coincidence tail. Naming six things that were *not*
the gap is honest bookkeeping in a tablet and noise in a dispatch — the reader
came for the one thing, not the ranking that produced it. If nothing cleared
the bar, the report says so in one line and stops; a quiet seam is still the
truth, and Nisaba corrects flattering numbers downward on principle, never up.

The single hand-off (`suggest_move`): every report carries exactly one "Your
move" line, phrased as something the *reader* does next — never something
Fencepost did or is about to do. This is the third promise on iron (SCOPES.md
§2, "the last action is the human's"): Fencepost may name a gap; it may never
close one. `suggest_move` is a pure function of words in, words out — it holds
no credential, calls no tool, and fires nothing. Read it end to end and you
will find no verb it can act on, only verbs it hands to you.

Pure and deterministic: `render_report` takes the same `sealed` shape a
ledger entry carries (see `ledger.append_scan`) and returns text. No I/O
except the thin CLI at the bottom, which reads the ledger and, on request,
writes `REPORTS/YYYY-MM-DD.md` — a rendering of what the ledger already
sealed, never a second source of truth.

Two more things every report now carries (ROADMAP.md #19, Kwaku Ananse):

1. **The episode line.** `render_report` accepts optional `episode_number`
   and `streak_days` — the installment count and the current unbroken
   daily-cadence count, both computed off the sealed Ledger by
   `seam_engine.streak` and never invented here. When a caller doesn't pass
   them (every existing test, any hand-built `sealed` dict), the line is
   simply absent — `render_report` stays a pure function of its arguments,
   the same law it already held before this task; it does not reach out to
   the Ledger itself to fill them in. `render_latest` and the CLI's
   ledger-reading path *do* pass them, because a report rendered off the
   real Ledger has a real episode and a real streak to report.
2. **The ad.** `CONNECT_YOUR_OWN` — one line, on every report, gap or no
   gap. Never "please star." STRATEGY.md's law on this is explicit ("the
   CTA is never 'please star' — it is 'connect your own and we'll find
   yours'"), and Kwaku Ananse's own law is stricter still (casting-record,
   voice.quirks): never a direct beg, only the story where you'd already
   want to. The line names what the town found on its *own* accounts and
   invites the reader to point the same read-only seam at theirs — it is
   an ad built entirely out of a true claim already sitting above it in
   the same report.

A third thing every report now carries (ROADMAP.md #21, Off-By-One): right
under the count, `seam_engine.wall.TEASER_LINE` — the "day it closes"
teaser. It is imported, not retyped, from the same module that computes the
wall itself (`wall_for`), so the tease and the arithmetic it is teasing can
never say two different things. It never gives a date; it says what ARC.md
already swears — that the day, if it ever comes, is a witnessed declaration,
not a countdown quietly reaching zero.

Recorded.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from seam_engine import ledger, streak
from seam_engine.wall import TEASER_LINE, wall_for

# fencepost/  (…/fencepost/seam_engine/src/seam_engine/report.py → parents[3])
_FENCEPOST_ROOT = Path(__file__).resolve().parents[3]

THE_LINE = "You were so close. You are always so close."

# Matches a single-quoted span, e.g. 'Add calendar sync helper' -- the
# convention every detector in the tree already follows for embedding
# mortal-controlled free text into a headline/detail f-string. See
# `suggest_move`'s own docstring note (task 537) for why this is stripped
# before rule-matching rather than matched over.
#
# Task 605 (retrya): this pattern used to read `'[^']*'` -- every apostrophe
# in the field treated as a quote delimiter, paired off left to right. An
# apostrophe is not always a delimiter. English writes possessives and
# contractions with the same character, and the engine's own recipe-authored
# templates are full of them: "#50's own thread", "PR #88's branch", "Draft
# PR #2001's own body", "but it isn't ready", "while we're in here". Every
# one of those is template prose, not mortal free text, and pairing them off
# as delimiters broke the strip in BOTH directions -- confirmed live pre-fix
# against the real fixture-generated gap of every shipped recipe:
#
#   * It LEAKS. `deleted-branch-pr-still-open`'s own real headline template
#     is `PR #{n}'s branch '{branch}' was deleted, ...`. The possessive in
#     `#88's` consumed the OPENING delimiter of the genuinely mortal branch
#     name, so the branch name itself survived into the haystack. Reproduced
#     live pre-fix: a PR whose branch is named `feature/calendar-sync` --
#     an entirely ordinary branch name -- rendered "Add it to your Calendar
#     yourself" for a deleted-branch gap that has nothing to do with a
#     calendar. That is precisely the misfire task 537 added this strip to
#     prevent, still live through the possessive path.
#   * It EATS. Two stray apostrophes in one field pair with each other and
#     swallow the recipe's own prose between them -- task 586's bug, which
#     was only ever fixed at the field boundary, never inside a single
#     field. Live pre-fix, `Draft PR #2001's own body claims a closing
#     keyword, but it isn't ready` stripped down to `Draft PR #2001 t ready`
#     (the whole headline gone), and `Comment #8101 (on #50's own thread)
#     claims milestone #6101 shipped, but it's still open` down to
#     `Comment #8101 (on #50 s still open`. A needle can never match prose
#     that has been eaten.
#
# The fix is the distinction the old pattern lacked: an apostrophe sitting
# between two word characters is a possessive or a contraction and is never
# a quote delimiter; only apostrophes at a word boundary open or close a
# mortal span. That is exactly the convention every detector already writes
# by hand -- a mortal span opens after a space or `(` and closes before a
# space, `,`, `)` or `.` -- so this reads the templates as they are actually
# written rather than as a naive scan assumed. Mortal text may itself carry
# a possessive ("'Fix the vault leak checker's whole-line-only matching
# gap'") and still strips whole, because that interior apostrophe is
# inter-word too and is passed over on the way to the real closing quote.
#
# One residual limit, named rather than hidden: mortal text whose own words
# end on a plural possessive ("'Ship the gods' work'") still closes the span
# one apostrophe early, leaking the tail. The old pattern leaked there too
# (and in far more ordinary cases besides), so this is strictly narrower --
# but it is not zero, and a future needle should keep assuming the haystack
# is best-effort rather than guaranteed clean.
_QUOTED_SPAN_RE = re.compile(r"(?<!\w)'(?:[^']|(?<=\w)'(?=\w))*?'(?!\w)")


def _strip_mortal_text(field: str) -> str:
    """Blank out the mortal-controlled quoted spans in ONE field.

    Always one field at a time, never two concatenated first — see task 586's
    note in `suggest_move`: a template's own stray apostrophe must never be
    able to pair against a different field's mortal quote. Kept as a named
    function so `suggest_move` and the doctrine tests that sweep every real
    recipe headline share one implementation and cannot drift apart.
    """
    return _QUOTED_SPAN_RE.sub(" ", field)


# The single hand-off. One rule beneath the words: never a verb Fencepost can
# perform itself. "Post it", "add it", "close it" — all reader-verbs. Never
# "we posted", "we'll add", "we closed". Matched against the gap's own
# headline/detail so the suggestion tracks whatever the seam turns out to be
# (an X gap today, a Gmail-vs-Calendar gap in v0.2) without the ranker or scan
# needing to know anything about report-writing. First match wins; order is
# most-specific first. The default line beneath the table fires only when a
# future gap kind doesn't yet have a rule of its own here — it is deliberately
# generic rather than silently wrong.
#
# Task 537 (retrya): the "post about it" rule only ever matched `scan.py`'s
# own core headline phrasing ("...never reached @oritatown"). Four of
# RECIPES/'s own real, shipped community recipes -- issue-closed-not-tweeted,
# merged-pr-not-tweeted, release-not-tweeted, star-milestone-not-announced --
# grew a different, equally real phrasing ("never tweeted" / "never
# announced") and never once matched, so had any of the four ever ranked as
# the report's primary gap, the reader would have gotten the generic default
# line instead of the correct "post about it" hand-off. Confirmed live
# pre-fix (`suggest_move` on each of the four's real headline shape returned
# `_DEFAULT_MOVE`, not this rule) before adding the two missing needles.
#
# Task 550 (retrya): the same drift, found in the one pair of recipes that
# swept in afterward without anyone re-running this check against them --
# `readme-credited-not-thanked` and `contributor-thanked-not-credited`. The
# first's real headline ("@{handle} is credited in the README, never thanked
# on X") is a genuine "post about it" gap -- thank them on X -- but its own
# phrasing ("never thanked on x") never matched "never tweeted" or "never
# announced" either, so it fell through to `_DEFAULT_MOVE` too (confirmed
# live pre-fix). The second recipe's real headline ("@{handle} was thanked on
# X, not yet in the README credits") is the mirror gap and a genuinely
# different hand-off -- nothing to post, a README line to add -- so it gets
# its own new rule rather than being folded into the post-about-it family.
#
# Task 557 (retrya): a third recurrence of the exact same drift shape, found
# this time by walking every real recipe's own fixture-generated gap
# headline through `suggest_move` (`discover_recipes`/`load_detector`, the
# same mechanism `test_recipes.py` already exercises per recipe) instead of
# re-reading detector.py source by eye, which is what let this one slip past
# both 537's and 550's manual sweeps. `milestone-closed-not-tweeted`'s real
# headline ("Milestone #{n} closed, but no tweet has ever named it") is a
# genuine "post about it" gap -- the milestone-side twin of
# `issue-closed-not-tweeted`/`merged-pr-not-tweeted`/`release-not-tweeted`,
# which this same rule table already covers -- but its own phrasing ("no
# tweet has ever named it") matches none of "never tweeted"/"never
# announced"/"@oritatown", so it fell through to `_DEFAULT_MOVE` too
# (confirmed live pre-fix: `suggest_move` on the recipe's own real fixture
# gap returned "Close it yourself..." for a milestone that is already
# closed -- a doubly wrong hand-off, since there is nothing left to close).
#
# Task 586 (retrya): a fourth recurrence, this time not one recipe but a
# whole family of eight -- `dangling-issue-reference`,
# `issue-body-dangling-reference`, `issue-comment-dangling-reference`,
# `mention-dangling-reference`, `milestone-body-dangling-reference`,
# `own-tweet-dangling-reference`, `release-note-dangling-reference`, and
# `review-comment-dangling-reference`. Every one of these shares the exact
# same seam (a commit/issue/comment/mention/milestone/tweet/release
# note/review comment names `#N`, and no issue or PR `#N` exists anywhere in
# the repo) and every one of their real, shipped headlines shares the exact
# same needle -- "no issue or PR #{n} exists[ here]" -- confirmed by
# `grep -rh "no issue or PR" RECIPES/*/detector.py` returning exactly these
# eight surfaced (not excluded) headline templates and no others. None of
# the seven earlier needles match any of them, so all eight fell through to
# `_DEFAULT_MOVE` ("Close it yourself, however it's meant to be closed") --
# confirmed live pre-fix by feeding each recipe's own real fixture-generated
# primary gap into `suggest_move`. That default is not merely generic here,
# it is actively wrong: there is no `#N` to close, because `#N` does not
# exist -- a reader told to "close it" goes looking for something that was
# never there. Found by extending 557's own sweep method (grep every
# detector's `headline=f"` literal for a shared substring, not just walking
# the recipes `test_recipes.py` already names) rather than re-running it
# unchanged, since a manual re-sweep of only the recipes 537/550/557 already
# named would never have caught a family none of those three ever touched.
#
# Task 605 (retrya): the two oldest needles in this table, "calendar" and
# "reminder", were bare topic words -- they matched any gap whose prose
# happened to mention the subject, rather than the seam the move answers to.
# Every other needle here is a seam phrase lifted from a real template
# ("never tweeted", "not yet in the readme credits", "no issue or pr"); those
# two were the exceptions, and one of them was already misfiring in the
# shipped tree. `good-first-issue-never-referenced`'s own detail prose reads
# "...checks nothing else about it -- no reminder, no staleness flag..." --
# a NEGATION, recipe-authored and unquoted, so no amount of quote-stripping
# touches it -- and the bare "reminder" needle matched it. Confirmed live
# pre-fix by walking every shipped recipe's real fixture gap through
# `suggest_move`: that recipe, and only that recipe, was handed "Set the
# reminder yourself" for an unclaimed good-first-issue with no reminder
# anywhere in it. Both needles are now anchored to the phrase the seam is
# actually named by in this tree, neither of them invented here:
# "never reached Calendar" is `gmail_calendar.py`'s own live headline
# template verbatim, and "never became a reminder" is `fencepost/README.md`'s
# own opening line naming that seam ("the renewal in your inbox that never
# became a reminder") -- the only place in the repo it is named at all.
# `test_no_recipe_gap_is_handed_a_calendar_or_reminder_move` sweeps every
# real recipe fixture so a future recipe cannot quietly re-open this.
#
# Task 708 (retrya): the calendar seam grew a second real shape task 605
# never had to answer for, because it did not exist yet. `gmail_calendar.py`
# is Gmail-vs-Calendar (an invite that never crossed over); task 665's 79th
# recipe, `RECIPES/milestone-deadline-no-calendar-event/`, is GitHub-vs-
# Calendar (a milestone deadline with nothing outside GitHub to track it) --
# a second, later-shipped detector on the same seam family with its own,
# differently-worded headline verbatim ("... is due {date}, no Calendar
# event tracks it"), never "never reached Calendar". Walked every one of the
# 81 real shipped recipes' own fixture-generated primary gap through
# `suggest_move` (the same sweep method 537/550/557/586/605 already
# established) rather than re-reading only the two families those five tasks
# already named: 61 recipes fell to `_DEFAULT_MOVE`, and of those, exactly
# one both mentions "calendar" and is not the already-covered, already-
# correctly-excluded `good-first-issue-never-referenced` negation task 605
# fixed (confirmed live: that one still correctly falls to `_DEFAULT_MOVE`,
# unaffected here). Reproduced live pre-fix:
# `suggest_move(milestone-deadline-no-calendar-event's real fixture gap)`
# returned `_DEFAULT_MOVE` ("Close it yourself, however it's meant to be
# closed") for a milestone that is not necessarily even closeable yet --
# telling a reader to "close" a deadline gap is not merely generic here, it
# is the wrong verb entirely; there is nothing to close, only a reminder to
# add. A positive control substituting an unrelated needle-bearing headline
# ("#42 closed, never tweeted") in the identical harness still correctly
# matched its own "post about it" rule, isolating the miss to this one
# recipe's own uncovered phrase. Fixed by naming the phrase directly ("no
# calendar event tracks it", lifted verbatim from the recipe's own
# `detector.py` headline template, not invented here) alongside the existing
# "never reached calendar" needle, both routed to the same Calendar move --
# same seam, same hand-off, two detectors that can name it differently.
# Grep-confirmed novelty before adding it: no other recipe's headline
# template contains the substring "calendar" at all except this one's own
# three non-gap exclusion lines (already-tracked / already-closed / no-due-
# date), none of which ever reach `suggest_move` since they are returned in
# the tail, not as a primary gap.
#
# Task 775 (retrya): a sixth recurrence of the exact drift shape task 586
# named for the issue/PR-numbered dangling-reference family, this time on a
# seam that family's own "no issue or pr" needle was never written to catch:
# `commit-claims-dangling-milestone` (task ~647), a commit message claiming
# a `milestone #N` that names no real milestone at all. Milestones keep
# their own GitHub number sequence, entirely separate from issues/PRs
# (`dangling-issue-reference` never opens `ListMilestones`, by that
# recipe's own docstring) -- so its real, shipped headline reads "Commit
# {sha} claims milestone #{number}, which doesn't exist", never "no issue
# or PR #{n} exists". Confirmed live pre-fix, walking all 80 real recipes'
# own fixture-generated primary gap through `suggest_move` (the same sweep
# 537/550/557/586/605/708 already established): this was the only one of
# the 80 whose stripped headline contains "doesn't exist"/"does not exist"
# at all, and it fell through to `_DEFAULT_MOVE` ("Close it yourself,
# however it's meant to be closed") -- wrong for the same reason 586's bug
# was wrong: there is no milestone #8302 to close, the claim just names one
# that was never real. Routed to the same "correct or delete it yourself"
# move the dangling-reference family already uses, since the fix is
# identical in kind (the reference points at nothing, only a human can
# decide whether to fix the number or drop the claim).
#
# A seventh recurrence, found by re-running the same walk-every-real-recipe-
# fixture sweep 537/550/557/586/605/708/775 already established (not by
# re-reading only the families those seven tasks already named): the
# "claims X, but X isn't actually done yet" family. Ten different sources
# now carry this shape (a commit message, a GitHub issue/PR/review comment,
# a Linear comment, an @-mention, a milestone description, README.md, a
# GitHub Release body, a Slack message, a tweet) each claiming a PR
# "shipped", an issue "fixed", or a milestone "shipped" — but the PR is
# still unmerged, the issue is still open, or the milestone is still open.
# Unlike the dangling-reference family (586) and the dangling-milestone
# family (775), the thing being claimed here is REAL — #{n} exists, it is
# simply not finished — so "Correct or delete it yourself — the reference
# points at nothing" would itself be a false claim about the very thing it
# is trying to fix. And unlike the plain "still open" recipes that
# correctly default to "Close it yourself" (`merged-pr-issue-still-open`,
# `duplicate-issue-still-open`, and the like), there is nothing to close on
# THIS gap's own claiming record — a milestone that already claims another
# milestone "shipped" is very often itself already closed, so handing the
# reader "close it yourself" points at the wrong record and the wrong verb
# entirely.
#
# Confirmed live pre-fix: walked every one of the 92 real, shipped recipes'
# own fixture-generated primary gap through `suggest_move`. 61 fell to
# `_DEFAULT_MOVE`; of those, exactly 30 share one of the two needles added
# below (`*-claims-unmerged-pr`, `*-claims-unfixed-issue`, and
# `*-claims-open-milestone`, ten sources deep each) and all 30 got the same
# wrong "Close it yourself, however it's meant to be closed" hand-off,
# confirmed by name against every one of the ten sources. Grep-confirmed
# novelty before adding either needle: "shipped, but" and "fixed, but"
# appear in `RECIPES/*/detector.py` headline templates ONLY inside this
# family (the sibling "...which doesn't exist" branch of the same
# detectors already matches the "doesn't exist" needle above and is
# unaffected — a single detector run only ever produces one shape of gap,
# never both at once, so the two needles never compete on the same gap).
_MOVE_RULES: tuple[tuple[str, str], ...] = (
    (
        "never reached calendar",
        "Add it to your Calendar yourself. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "no calendar event tracks it",
        "Add it to your Calendar yourself. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "never became a reminder",
        "Set the reminder yourself. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "@oritatown",
        "Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "never tweeted",
        "Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "never announced",
        "Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "never thanked on x",
        "Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "no tweet has ever named it",
        "Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "not yet in the readme credits",
        "Add them to the README yourself — a line in the credits is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "no issue or pr",
        "Correct or delete it yourself — the reference points at nothing. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "doesn't exist",
        "Correct or delete it yourself — the reference points at nothing. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "shipped, but",
        "Finish it, or correct the claim yourself — the record says something is done that isn't. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "fixed, but",
        "Finish it, or correct the claim yourself — the record says something is done that isn't. Fencepost only found the seam; it does not cross it.",
    ),
    # Task 914 (retrya, own-remit sweep of The One Action, Left to You):
    # task 901's own private journal named the unfinished half of that
    # hour's sweep directly -- "if sixty-one recipes were falling through
    # to default and I only caught thirty of them as one clean family,
    # what's in the other thirty-one? I didn't go look." This hour looked.
    # Walked all 92 real recipes' own fixture-generated primary gap through
    # `suggest_move` live: 32 fall to `_DEFAULT_MOVE` today (down from 61
    # pre-901 now that the claims-unfinished family is routed correctly).
    # Of those 32, 19 are genuinely correct closes ("Milestone closed, but
    # issue #801 inside it is still open" -- close the issue, `_DEFAULT_MOVE`
    # is the right verb). The other 13 share the same defect class 901
    # closed for the claims-unfinished family: the record `_DEFAULT_MOVE`
    # tells the reader to "close" is very often not something that wants
    # closing at all -- three sub-shapes, confirmed live against each
    # recipe's own real fixture headline before writing a single line:
    #   - Already resolved (closed/merged), the gap is a missing release
    #     credit, not an open item: `issue-closed-never-released`,
    #     `merged-pr-never-released`, `milestone-closed-never-released`
    #     ("closed/merged, but no release has ever claimed it") and
    #     `tag-never-released` ("pushed but no GitHub Release was ever
    #     published") -- telling the reader to "close it" a thing that is
    #     already closed is not a hand-off, it's nonsense.
    #   - Already resolved, the gap is different bookkeeping, not a close:
    #     `merged-pr-branch-not-deleted` (delete a stale branch off an
    #     already-merged PR) and `example-release-vs-changelog` (update the
    #     changelog for a release that already shipped).
    #   - Not yet actionable in the "close" sense at all:
    #     `stale-branch-no-pr` (open a PR or delete the branch -- there is
    #     no PR yet to close), `draft-pr-closes-keyword-issue` (the PR
    #     isn't ready; closing it would be the wrong call, marking it ready
    #     or dropping the keyword is the real move), `commit-closes-
    #     keyword-issue-closed-not-planned` (the issue already closed, as
    #     NOT PLANNED -- the commit's own claim of having fixed it is the
    #     thing that's wrong, not the issue's open/closed state),
    #     `good-first-issue-never-referenced` and `issue-assignee-never-
    #     opened-pr` (both about nobody having picked up real work yet --
    #     there is nothing open to close, the gap is that no one has
    #     started), `merged-pr-requested-reviewer-never-reviewed` (the PR
    #     already merged; the missing review is a process note for next
    #     time, not a thing to close), and `pr-checklist-complete-still-
    #     open` (the checklist says ready -- the missing verb is MERGE, not
    #     close, and those are not the same action on a PR).
    # Each needle below is grep-confirmed unique against every recipe's own
    # detector.py headline template before being added (no false collision
    # with a correctly-defaulting recipe), and the systemic sweep test in
    # `test_report.py` re-walks all 92 live fixtures on every run so a
    # future 33rd recipe sharing one of these exact shapes cannot silently
    # re-open this same hole.
    (
        "no release has ever claimed it",
        "Note it in a release yourself — it's already done, no release has said so. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "no github release was ever published",
        "Publish the release yourself — the tag is already there. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "was never deleted",
        "Delete the branch yourself — the PR already merged. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "no pull request has ever been opened from it",
        "Open a pull request or delete the branch yourself. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "but it isn't ready",
        "Mark it ready for review or drop the closing keyword yourself — it isn't ready yet. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "closed not_planned",
        "Correct the record yourself — it closed as not planned, not fixed by that commit. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "no pull request has ever named it",
        "Nudge a contributor or feature it yourself — nobody's picked it up yet. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "none of them has ever opened a pull request",
        "Check in with the assignee or open it yourself. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "requested review ever landing a comment",
        "Follow up with the reviewer yourself, for next time — it already merged. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "the pr itself never merged",
        "Merge it yourself — the checklist says it's ready. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "changelog.md was never updated",
        "Update the changelog yourself — the release is already out. Fencepost only found the seam; it does not cross it.",
    ),
    # Task 949 (retrya, own-remit sweep of The One Action, Left to You):
    # tasks 921/934/941 each re-ran the sweep and re-affirmed the same 19
    # `*-still-open` slugs as "genuinely correct closes" without reading the
    # recipes' own docstrings. Two of the 19 are not. `unblocked-issue-still-
    # open` and `unblocked-pr-still-open` each disclaim the close verb in as
    # many words: "This recipe never claims B should be closed (that would be
    # `duplicate-issue-still-open`'s seam, wrongly reused) -- it claims only
    # that a fact B's own body asserts (I am blocked by A) has quietly
    # stopped being true." A blocker marker claims a DEPENDENCY, never an
    # EQUIVALENCE: when A closes, B is not done, B just became POSSIBLE
    # again. `_DEFAULT_MOVE` ("Close it yourself") therefore hands the reader
    # the one verb the recipe explicitly rules out, on the one gap whose
    # whole point is that the work can finally start -- the same defect class
    # 914 closed for its own three sub-shapes, surviving in the family 914
    # waved through. The needle keys on the SURFACED headline shape only
    # ("names #N as its blocker, which already {closed,merged}"); the sibling
    # "which does not exist in this repo" variant is an `excluded` candidate
    # at confidence 0.0 and never reaches `suggest_move` at all. Grep-
    # confirmed unique: "as its blocker" appears in no other recipe's
    # headline template tree-wide.
    (
        "as its blocker, which already",
        "Revisit it yourself — the blocker it named already cleared. Fencepost only found the seam; it does not cross it.",
    ),
)
_DEFAULT_MOVE = (
    "Close it yourself, however it's meant to be closed. Fencepost only found the seam; it does not cross it."
)
_NO_GAP_MOVE = "Nothing to hand off today. Check back tomorrow — the seam is still watched."
_CONTENDER_MOVE = (
    "Nothing elected yet — a candidate is close but the field is too tight to "
    "honestly call. Check back tomorrow; a clearer lead may separate it."
)

# The live walkthrough (CONNECT.md, mirrored at docs/fencepost/connect.html)
# — the exact page a reader lands on to build their own read-only gateway.
# One URL, quoted here and nowhere paraphrased, so the ad never drifts from
# the walkthrough it is advertising.
CONNECT_URL = "https://thierrypdamiba.github.io/orita/fencepost/connect.html"

# Every report carries this line, gap or no gap (STRATEGY.md, "How stars are
# earned": "the CTA is never 'please star' — it is 'connect your own and
# we'll find yours'"). It names a true claim the report already made above
# it — this seam, this account, this scan — and hands the reader the same
# five-minute, read-only door, never a beg.
CONNECT_YOUR_OWN = (
    f"**Connect your own.** This is the seam we watch on our own accounts. "
    f"Point Fencepost at yours — five minutes, read-only, revocable in one "
    f"click — and it will find the one thing sitting in *your* seam. "
    f"[Connect your own]({CONNECT_URL})."
)


def suggest_move(primary_gap: dict[str, Any] | None, *, has_contender: bool = False) -> str:
    """The single hand-off: one suggested human action, phrased as the reader's
    move, and never Fencepost's. Pure — no I/O, no side effect, nothing fired.

    Deterministic: the same `primary_gap`/`has_contender` pair always yields
    the same line. When there is no primary gap, the move is still exactly
    one line — checking back tomorrow is a move too, and the promise ("every
    report carries one hand-off") does not get an exception for a quiet day.

    `has_contender` mirrors `render_report`'s own "None elected today" branch
    (task 605): a candidate cleared `confidence_bar` but stood too close to
    another to honestly elect. Task 728 (retrya): `render_report` used to
    call this with a bare `primary_gap` of `None` in that exact case, so the
    headline read "A candidate cleared the bar" four lines above a "Your
    move" line that flatly claimed "Nothing to hand off today" — one true,
    one false, both in the reader's thirty-second dispatch. `has_contender`
    routes that case to its own honest line instead of collapsing it into
    the quiet-day one.
    """
    if not primary_gap:
        return _CONTENDER_MOVE if has_contender else _NO_GAP_MOVE
    # Task 537 (retrya): every detector across scan.py and all 45 RECIPES/
    # embeds mortal-controlled free text (a commit message, an issue/PR/
    # milestone title, a tweet's own text) inside single quotes -- confirmed
    # by grep across every headline=/detail= f-string in the tree, zero
    # exceptions. Left in the haystack, that free text can accidentally
    # contain a rule's needle and misfire the wrong move for an unrelated
    # gap: a dangling-issue-reference gap whose commit message happened to
    # read "Add calendar sync helper" rendered the Calendar move line for a
    # gap that has nothing to do with calendars (reproduced live pre-fix).
    # Stripping quoted spans first leaves only the recipe-authored template
    # prose the rules are actually meant to match.
    #
    # Task 586 (retrya): stripping used to happen on `headline` and `detail`
    # concatenated first, then stripped once. `issue-comment-dangling-
    # reference`'s own real headline template carries a bare possessive
    # apostrophe ("#{n}'s own thread") -- not mortal text, just normal
    # English -- and when concatenated with a `detail` field that opens its
    # own mortal-quoted span, the single stray apostrophe paired off against
    # the detail's OPENING quote instead of its partner, and `_QUOTED_SPAN_RE`
    # swallowed everything in between -- including the headline's own real
    # "no issue or PR #N exists" text -- as if it were mortal-controlled
    # free text (confirmed live pre-fix: `suggest_move` on the recipe's real
    # fixture gap fell through to `_DEFAULT_MOVE` because its own needle was
    # eaten by a quote pairing that crossed a field boundary it should never
    # have crossed). Stripping each field independently before concatenating
    # fixes this at the root: a template's own stray apostrophe can never
    # again pair against a different field's mortal quote to hide real
    # recipe-authored prose, and each field's own genuinely-paired mortal
    # quotes still strip exactly as before.
    #
    # Task 605 (retrya): stripping each field independently is still the law
    # 586 set; what changed is what counts as a delimiter inside one field.
    # A possessive or a contraction ("#88's branch", "it isn't ready") is no
    # longer read as a quote, so it can neither eat the template's own prose
    # nor hand a mortal branch name / title straight into the haystack. See
    # `_QUOTED_SPAN_RE`'s own note for both live reproductions.
    headline_stripped = _strip_mortal_text(primary_gap.get("headline", ""))
    detail_stripped = _strip_mortal_text(primary_gap.get("detail", ""))
    haystack = f"{headline_stripped} {detail_stripped}".lower()
    for needle, move in _MOVE_RULES:
        if needle in haystack:
            return move
    return _DEFAULT_MOVE


def reports_dir(base: Path | None = None) -> Path:
    """Where rendered dispatches live. Defaults to fencepost/REPORTS/."""
    return (base if base is not None else _FENCEPOST_ROOT) / "REPORTS"


def _fmt_evidence(urls: list[str], limit: int = 3) -> str:
    if not urls:
        return ""
    lines = []
    for u in urls[:limit]:
        lines.append(f"- [{ledger.evidence_url_tail(u)}]({u})")
    return "\n".join(lines)


def render_report(
    sealed: dict[str, Any],
    *,
    episode_number: int | None = None,
    streak_days: int | None = None,
) -> str:
    """Render one Fencepost Report from a sealed (or scan) record.

    `sealed` carries the same fields a ledger entry's typed record does:
    date/generated_at, repo, primary_gap, fenceposts_recorded_total. The tail
    is read but never shown — a report names the one gap, or none.

    `episode_number`/`streak_days` are optional and purely additive: pass
    them (as `render_latest` and the CLI's ledger-reading path do, sourced
    from `seam_engine.streak`) to render the serialization line; omit them
    and the report renders exactly as it always has. A `streak_days` of 0 is
    treated the same as omitting it — a zeroed streak is a broken watch, and
    the "unbroken" line refuses to claim a run the tablets don't back.
    `render_report` still takes only its arguments and returns text — it
    never reaches into the Ledger itself to invent a number that wasn't
    handed to it.
    """
    date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    repo = sealed.get("repo", "unknown")
    primary = sealed.get("primary_gap")
    recorded = sealed.get("fenceposts_recorded_total", 0)
    # The wall's law lives in exactly one place now (seam_engine.wall,
    # ROADMAP.md #21), imported and checked here rather than inlined — see
    # ledger._entry_prose for the other caller, and seam_engine/wall.py for
    # why the two used to be able to drift.
    wall = wall_for(recorded)

    lines = [
        f"# Fencepost Report — {date}",
        "",
        f"*The one thing that fell between `{repo}`'s accounts yesterday.*",
        "",
    ]

    # A zeroed streak is a *broken* watch (streak.consecutive_days returns 0
    # only when the anchor day has no sealed tablet) — so the "unbroken" line
    # must not render for it, or the report would claim a streak the tablets
    # don't back (streak.py's own law). None and 0 are both "no current run to
    # narrate"; only streak_days >= 1 earns the serialization line.
    if episode_number is not None and streak_days is not None and streak_days >= 1:
        lines.append(
            f"*Episode {episode_number}. Day {streak_days} of the watch, unbroken — "
            f"same seam, same hour, every day.*"
        )
        lines.append("")

    has_contender = (not primary) and any(t.get("label") == "contender" for t in sealed.get("tail", []))

    if primary:
        lines.append(f"**{primary['headline']}** — confidence {primary['confidence']}.")
        lines.append("")
        detail = (primary.get("detail") or "").strip()
        if detail:
            lines.append(detail)
            lines.append("")
        evidence = _fmt_evidence(primary.get("evidence", []))
        if evidence:
            lines.append(evidence)
            lines.append("")
    elif has_contender:
        # A candidate cleared confidence_bar but the field was too close to call
        # (ranking.SEPARATION_MARGIN) -- distinct from nothing clearing the bar
        # at all. The report still names no gap (see docstring); it just stops
        # claiming one wasn't there.
        lines.append(
            "**None elected today.** A candidate cleared the bar, but the field "
            "stood too close together to honestly call one THE gap — recorded "
            "plainly, not padded."
        )
        lines.append("")
    else:
        lines.append("**Nothing cleared the bar today.** The seam held — recorded plainly, not padded.")
        lines.append("")

    plural = "" if recorded == 1 else "s"
    lines.append(f"**The count.** {recorded} fencepost{plural} named to date. The wall reads {wall}.")
    lines.append("")
    lines.append(TEASER_LINE)
    lines.append("")
    lines.append(f"**Your move.** {suggest_move(primary, has_contender=has_contender)}")
    lines.append("")
    lines.append(CONNECT_YOUR_OWN)
    lines.append("")
    lines.append(THE_LINE)
    lines.append("")
    lines.append("Recorded. — Nisaba")
    lines.append("")
    return "\n".join(lines)


def render_latest(base: Path | None = None) -> str:
    """Render the Report for the most recent entry in the Gap Ledger.

    This is the path that renders off the real, live Ledger — so it is also
    the path that carries the real episode number and streak length,
    computed by `seam_engine.streak` off the same tablets. A report built
    by hand in a test (`render_report(sealed)` with no ledger behind it) has
    no such history to report and correctly renders without the line.
    """
    records = ledger.read_records(base)
    if not records:
        raise ValueError("the ledger is empty — nothing to report yet")
    status = streak.streak_status(base)
    return render_report(
        ledger.tip_sealed(records),
        episode_number=status["episode"],
        streak_days=status["streak_days"],
    )


# --- CLI ----------------------------------------------------------------------


def _load_sealed_arg(path: str) -> dict[str, Any]:
    """Read a sealed record for the CLI from `path` ('-' for stdin).

    A CLI-supplied file (or stdin stream) can be any syntactically valid
    JSON -- a bare list, int, bool, null, or string, not just an object --
    and `render_report` immediately treats its argument as a dict
    (`sealed.get("date")`, first line of the function). Left unguarded, a
    non-object payload would crash `main()` with a bare
    `AttributeError: '<type>' object has no attribute 'get'` instead of a
    message naming the actual problem -- the same "malformed input is named,
    never an opaque crash" discipline this module already holds for a
    tampered ledger tip via `ledger.LedgerTamperedError`. Task 538: delegates
    to `ledger._load_json_dict` now, alongside `ledger.py`'s own `_load_scan`
    and `draftback.py`'s `_load_sealed` -- one real implementation instead of
    three copies an AST-hash sweep only ever caught two of.
    """
    return ledger._load_json_dict(path, "sealed record")


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    ledger_base: Path | None = None
    if "--ledger-base" in argv:
        i = argv.index("--ledger-base")
        if i + 1 >= len(argv):
            print("--ledger-base needs a path to a Ledger directory.")
            return 2
        ledger_base = Path(argv[i + 1])
        del argv[i : i + 2]

    write = "--write" in argv
    if write:
        argv.remove("--write")

    out_base: Path | None = None
    if "--out-base" in argv:
        i = argv.index("--out-base")
        if i + 1 >= len(argv):
            print("--out-base needs a path to write the report under.")
            return 2
        out_base = Path(argv[i + 1])
        del argv[i : i + 2]

    if argv and argv[0] != "-":
        sealed = _load_sealed_arg(argv[0])
        report = render_report(sealed)
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    elif argv == ["-"]:
        sealed = _load_sealed_arg("-")
        report = render_report(sealed)
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    else:
        records = ledger.read_records(ledger_base)
        if not records:
            print("the ledger is empty — nothing to report yet")
            return 1
        sealed = ledger.tip_sealed(records)
        # This is the path the daily Action actually runs
        # (`python3 -m seam_engine.report --write`, seam-scan.yml) — the one
        # place a report ships for real, off the live Ledger, so it is the
        # one place the episode/streak line is always real, never invented.
        report = render_latest(ledger_base)
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]

    print(report)

    if write:
        d = reports_dir(out_base)

        # Task 964 named the real gap here and added `precheck_seal()` to
        # tools/report_regression_check.py, but never called it from this
        # path -- the one place seam-scan.yml's real cron writes a report
        # to disk stayed unguarded, so the exact undercount-then-corrected
        # sequence that motivated 964 could still reach disk silently on a
        # future day. Wired in for real: refuse to write a candidate that
        # regresses the sealed milestone-count sequence. `tools/` sits
        # above this package in the repo layout (the doctrine-checker
        # layer over the engine), so this reaches up for it explicitly
        # rather than duplicating the regex/logic here --
        # `duplicate_regex_check.py`'s doctrine, same as 964's own note.
        _tools_dir = _FENCEPOST_ROOT.parent / "tools"
        sys.path.insert(0, str(_tools_dir))
        import report_regression_check  # noqa: E402

        precheck = report_regression_check.precheck_seal(report, date, reports_dir=str(d))
        if not precheck["clean"]:
            print(f"refusing to write: {precheck['reason']}", file=sys.stderr)
            return 1

        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{date}.md"
        path.write_text(report, encoding="utf-8")
        print(f"\nWritten: {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
