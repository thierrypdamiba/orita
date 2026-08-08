"""Tests for the Fencepost Report — the daily dispatch, not the tablet.

A report names one gap (or none) and never the coincidence tail. These tests
go red if the report starts padding itself with the ranking noise the tablet
is for, or drops the line the whole arc turns on.
"""
from __future__ import annotations

import ast
import inspect
import sys
from datetime import datetime, timezone
from pathlib import Path

from seam_engine import ledger, report

# report.py's own docstring makes a safety claim about `suggest_move` (ROADMAP.md
# #140, retrya): "it holds no credential, calls no tool, and fires nothing. Read
# it end to end and you will find no verb it can act on." The wording tests above
# check what a rendered move SAYS; these check what the module's own imports
# actually ARE -- the mechanism the claim is about, not just its prose.

# report.py's only real, already-audited local dependencies (their own modules
# are pure-local file I/O, no network, no credential -- ledger.py/streak.py/
# wall.py never import anything outside this same allow-list either).
_ALLOWED_LOCAL_IMPORTS = frozenset({"seam_engine", "seam_engine.ledger", "seam_engine.streak", "seam_engine.wall"})

# Anything reaching a credential, the network, a subprocess, or an Arcade/MCP
# tool call would be a violation of the claim -- named here once, checked
# against the module's real source text and, via the mutation test below,
# proven to actually bite rather than merely exist.
_FORBIDDEN_NAMES = (
    "requests",
    "httpx",
    "urllib",
    "subprocess",
    "socket",
    "os.environ",
    "getenv",
    "arcade",
    "mcp",
)


def _top_level_imports(source: str) -> set[str]:
    """Every module name `source` imports, structurally, via `ast` -- never a
    second hand-typed copy of report.py's own import list."""
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module)
    return found


def _stdlib_or_allowed(module_name: str) -> bool:
    root = module_name.split(".", 1)[0]
    if root == "__future__":
        return True
    if module_name in _ALLOWED_LOCAL_IMPORTS:
        return True
    return root in sys.stdlib_module_names


def _forbidden_names_in(source: str) -> list[str]:
    return [name for name in _FORBIDDEN_NAMES if name in source]


def _sealed(*, primary: bool, recorded: int, tail_n: int = 2) -> dict:
    p = None
    if primary:
        p = {
            "slug": "milestone-unannounced",
            "headline": "Milestone-level work shipped but never reached the sky",
            "detail": "3 milestone commit(s), none echoed in a post.",
            "confidence": 0.85,
            "evidence": [f"https://github.com/x/orita/commit/{i:07d}" for i in range(3)],
        }
    tail = [{"slug": f"coincidence-{i}", "confidence": 0.5, "label": "coincidence"} for i in range(tail_n)]
    return {
        "date": "2026-07-12",
        "generated_at": "2026-07-12T11:38:10+00:00",
        "repo": "x/orita",
        "primary_gap": p,
        "tail": tail,
        "fenceposts_recorded_total": recorded,
    }


def _at(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, tzinfo=timezone.utc)


# --- one gap, never the tail --------------------------------------------------


def test_report_names_the_one_gap():
    text = report.render_report(_sealed(primary=True, recorded=1))
    assert "Milestone-level work" in text
    assert "confidence 0.85" in text


def test_report_never_shows_the_coincidence_tail():
    text = report.render_report(_sealed(primary=True, recorded=1, tail_n=3))
    assert "coincidence-0" not in text
    assert "coincidence-1" not in text


def test_report_caps_evidence_at_three_links():
    text = report.render_report(_sealed(primary=True, recorded=1))
    assert text.count("github.com/x/orita/commit") <= 3


# --- the line and the count are load-bearing ----------------------------------


def test_report_always_carries_the_line():
    assert report.THE_LINE in report.render_report(_sealed(primary=True, recorded=1))
    assert report.THE_LINE in report.render_report(_sealed(primary=False, recorded=0))


def test_wall_reads_one_behind_recorded():
    text = report.render_report(_sealed(primary=True, recorded=3))
    assert "The wall reads 2" in text
    assert "3 fenceposts named" in text


def test_wall_never_goes_negative_at_zero_recorded():
    text = report.render_report(_sealed(primary=False, recorded=0))
    assert "The wall reads 0" in text


# --- an honest quiet day -------------------------------------------------------


def test_no_primary_says_nothing_cleared_the_bar():
    text = report.render_report(_sealed(primary=False, recorded=0))
    assert "Nothing cleared the bar" in text
    assert "milestone-unannounced" not in text


def test_no_primary_but_a_contender_cleared_the_bar_says_none_elected():
    # Task 605. Same false-claim bug as the ledger's own no-primary path:
    # a tied contender (label "contender", confidence >= the bar) used to be
    # rendered the same as "nothing cleared the bar" -- the report still
    # names no gap (it never shows the tail, by design), but it should stop
    # asserting the bar was never cleared when it was.
    sealed = _sealed(primary=False, recorded=0)
    sealed["tail"] = [{"slug": "gap-a", "confidence": 0.85, "label": "contender"}]
    text = report.render_report(sealed)
    assert "Nothing cleared the bar" not in text
    assert "None elected" in text
    assert "gap-a" not in text  # the report still never names the tail


# --- rendered from a live ledger, not a hand-built dict -----------------------


def test_render_latest_reads_the_real_ledger(tmp_path: Path):
    ledger.append_scan(
        {
            "generated_at": "2026-07-12T11:38:10+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "Milestone-level work shipped but never reached the sky",
                "detail": "3 milestone commit(s), none echoed in a post.",
                "confidence": 0.85,
                "evidence": ["https://github.com/x/orita/commit/0000001"],
            },
            "tail": [],
            "excluded": [],
        },
        now=_at(2026, 7, 12),
        base=tmp_path,
    )

    text = report.render_latest(tmp_path)
    assert "# Fencepost Report — 2026-07-12" in text
    assert "Milestone-level work" in text
    assert "1 fencepost named" in text
    assert "The wall reads 0" in text
    assert report.THE_LINE in text


def test_render_latest_on_empty_ledger_raises(tmp_path: Path):
    try:
        report.render_latest(tmp_path)
        assert False, "expected ValueError on an empty ledger"
    except ValueError:
        pass


def test_render_latest_raises_named_error_not_keyerror_when_tip_is_malformed(tmp_path: Path):
    # render_latest() used to read `records[-1]["sealed"]` straight off the
    # ledger tip -- a malformed marker dict (ledger.py's own tampering
    # discipline, task 205) carries no "sealed" key, so a hand-edited/
    # truncated tablet crashed this with a bare `KeyError: 'sealed'`
    # instead of the named `ledger.LedgerTamperedError` every other tip
    # reader in this codebase already raises.
    ledger.append_scan(
        {
            "generated_at": "2026-07-12T11:38:10+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "x",
                "detail": "x",
                "confidence": 0.85,
                "evidence": [],
            },
            "tail": [],
            "excluded": [],
        },
        now=_at(2026, 7, 12),
        base=tmp_path,
    )
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    broken = tablet.read_text().replace('"confidence": 0.85', '"confidence": 0.85,,')
    tablet.write_text(broken)

    try:
        report.render_latest(tmp_path)
        assert False, "expected LedgerTamperedError, not a bare KeyError"
    except ledger.LedgerTamperedError as e:
        assert "malformed" in str(e)


def test_main_with_no_args_raises_named_error_not_keyerror_when_tip_is_malformed(tmp_path: Path):
    # Same bug, reached through the CLI's no-arg branch (`main()`'s
    # `sealed = records[-1]["sealed"]`), the exact path the daily Action
    # runs (`python3 -m seam_engine.report --write`, seam-scan.yml).
    ledger.append_scan(
        {
            "generated_at": "2026-07-12T11:38:10+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "x",
                "detail": "x",
                "confidence": 0.85,
                "evidence": [],
            },
            "tail": [],
            "excluded": [],
        },
        now=_at(2026, 7, 12),
        base=tmp_path,
    )
    tablet = ledger.gaps_dir(tmp_path) / "2026-07-12.md"
    broken = tablet.read_text().replace('"confidence": 0.85', '"confidence": 0.85,,')
    tablet.write_text(broken)

    try:
        report.main(["--ledger-base", str(tmp_path)])
        assert False, "expected LedgerTamperedError, not a bare KeyError"
    except ledger.LedgerTamperedError as e:
        assert "malformed" in str(e)


def test_main_with_file_arg_raises_named_error_not_attributeerror_when_json_is_not_an_object(tmp_path: Path):
    # main()'s file-arg branch used to do `sealed = json.loads(path.read_text())`
    # with no shape check, then hand `sealed` straight to `render_report`, which
    # opens with `sealed.get("date")`. A CLI-supplied file can be any syntactically
    # valid JSON -- a bare list, int, bool, null, or string, not just an object --
    # so `[1, 2, 3]` on disk crashed this with a bare
    # `AttributeError: 'list' object has no attribute 'get'` instead of a message
    # naming the actual problem, the same "tampered/malformed input must be named,
    # never an opaque crash" discipline this module already holds for a broken
    # ledger tip (see the malformed-tip tests just above).
    bad = tmp_path / "not_an_object.json"
    bad.write_text("[1, 2, 3]")

    try:
        report.main([str(bad)])
        assert False, "expected a named ValueError, not a bare AttributeError"
    except AttributeError:
        assert False, "expected a named ValueError, not a bare AttributeError"
    except ValueError as e:
        assert "object" in str(e)


def test_main_with_stdin_raises_named_error_not_attributeerror_when_json_is_not_an_object(monkeypatch):
    # Same bug, reached through the CLI's stdin branch (`argv == ["-"]`).
    import io
    import sys

    monkeypatch.setattr(sys, "stdin", io.StringIO("null"))

    try:
        report.main(["-"])
        assert False, "expected a named ValueError, not a bare AttributeError"
    except AttributeError:
        assert False, "expected a named ValueError, not a bare AttributeError"
    except ValueError as e:
        assert "object" in str(e)


# --- the single hand-off: one "your move" line, never an action fired ---------


def test_report_carries_exactly_one_your_move_line():
    text = report.render_report(_sealed(primary=True, recorded=1))
    assert text.count("**Your move.**") == 1


def test_report_carries_a_your_move_line_even_on_a_quiet_day():
    text = report.render_report(_sealed(primary=False, recorded=0))
    assert text.count("**Your move.**") == 1
    assert report.suggest_move(None) in text


def test_your_move_is_phrased_as_the_readers_verb_not_fenceposts():
    # The whole point of the hand-off: Fencepost never claims to have DONE
    # the action, only to have found the gap and named the reader's move.
    for primary_gap in (
        None,
        {"headline": "Milestone-level work shipped but never reached @oritatown", "detail": ""},
        {"headline": "The invite never made it onto your Calendar", "detail": ""},
        {"headline": "An entirely novel kind of gap nobody wrote a rule for", "detail": ""},
    ):
        move = report.suggest_move(primary_gap)
        lowered = move.lower()
        # No first-person-plural claim of having acted or being about to.
        for forbidden in ("we posted", "we added", "we closed", "we'll", "fencepost posted", "fencepost added"):
            assert forbidden not in lowered
        assert "fencepost" not in lowered.split(".")[0]  # the first clause is the reader's verb, not Fencepost's


def test_suggest_move_is_deterministic():
    gap = {"headline": "Release 'v1' shipped but never reached @oritatown", "detail": "x"}
    assert report.suggest_move(gap) == report.suggest_move(gap)


# Task 605 (retrya): this used to assert against an invented headline ("The
# invite never made it onto your Calendar") that no module in the tree has
# ever produced, which is exactly what let the bare "calendar" topic-word
# needle look tested while it was matching any prose that merely said the
# word. The shape below is `gmail_calendar.py`'s own live headline template
# verbatim -- the one real Calendar gap this engine knows how to build --
# and `test_calendar_needle_is_gmail_calendars_own_headline_phrase` below
# ties the needle itself back to that module's source so the two can never
# drift apart silently again.
def test_suggest_move_matches_calendar_gaps_to_a_calendar_verb():
    move = report.suggest_move(
        {"headline": "Invite 'Q3 planning sync' sits in Gmail, never reached Calendar", "detail": ""}
    )
    assert "add it to your calendar" in move.lower()


def test_suggest_move_matches_x_gaps_to_a_post_verb():
    move = report.suggest_move(
        {"headline": "Release 'v1' shipped but never reached @oritatown", "detail": ""}
    )
    assert "post about it" in move.lower()


def test_suggest_move_falls_back_for_an_unrecognized_gap_kind():
    move = report.suggest_move({"headline": "Some future gap kind", "detail": "no known keyword here"})
    assert move == report._DEFAULT_MOVE


def test_suggest_move_on_no_gap_is_the_fixed_quiet_day_line():
    assert report.suggest_move(None) == report._NO_GAP_MOVE


# Task 537 (retrya): four of RECIPES/'s own real, shipped community recipes
# (issue-closed-not-tweeted, merged-pr-not-tweeted, release-not-tweeted,
# star-milestone-not-announced) produce a real gap headline reading "never
# tweeted" / "never announced" -- never "@oritatown", which was the only
# needle this rule matched on. Each shape below is copied verbatim from that
# recipe's own detector.py headline= f-string, not invented, so a future
# rewording of either side would go red here rather than silently drift
# apart again the way the two already had.
def test_suggest_move_matches_issue_closed_not_tweeted_headline():
    move = report.suggest_move({"headline": "#42 closed, never tweeted", "detail": ""})
    assert "post about it" in move.lower()


def test_suggest_move_matches_merged_pr_not_tweeted_headline():
    move = report.suggest_move({"headline": "#7 merged, never tweeted", "detail": ""})
    assert "post about it" in move.lower()


def test_suggest_move_matches_release_not_tweeted_headline():
    move = report.suggest_move({"headline": "v1.2.0 shipped, never tweeted", "detail": ""})
    assert "post about it" in move.lower()


def test_suggest_move_matches_star_milestone_not_announced_headline():
    move = report.suggest_move({"headline": "1000 stars, never announced", "detail": ""})
    assert "post about it" in move.lower()


# Task 557 (retrya): `milestone-closed-not-tweeted`'s real headline shape
# copied verbatim from its own detector.py f-string -- the milestone-side
# twin of the four recipes task 537 already covers, a genuine "post about
# it" gap the pre-existing needles never caught (confirmed live pre-fix:
# fell to `_DEFAULT_MOVE`, telling the reader to "close" a milestone that is
# already closed).
def test_suggest_move_matches_milestone_closed_not_tweeted_headline():
    move = report.suggest_move(
        {"headline": "Milestone #4001 closed, but no tweet has ever named it", "detail": ""}
    )
    assert "post about it" in move.lower()


# Task 557 (retrya): the systemic guard 537/550 didn't have. Rather than
# trust the next manual sweep to catch a fourth recurrence of the same
# drift, this walks every real recipe's own fixture-generated gap headline
# (via `discover_recipes`/`load_detector`, the same mechanism
# `test_recipes.py` already exercises per recipe -- not a hand-typed guess)
# and refuses if any headline that itself claims a tweet/announcement never
# happened produces the generic "close it yourself" line instead of a real
# "post about it" hand-off. Two named, checked exceptions, both confirmed by
# hand before being excluded rather than assumed safe: `contributor-thanked-
# not-credited` (task 550) is a real gap whose correct hand-off is a README
# edit, not a post; `own-tweet-dangling-reference`'s headline ("Our own
# tweet references #{n}, but no issue or PR #{n} exists") mentions "tweet"
# only because the gap's SOURCE is a tweet, not because posting one is the
# fix -- it is the same dangling-reference family as `dangling-issue-
# reference`/`mention-dangling-reference`/etc, out of scope for this task
# either way. (Task 586 gave that whole family its own real "correct or
# delete it yourself" move, so this exception no longer means "correctly
# generic" -- see `test_no_dangling_reference_headline_falls_through_to_default`
# below for the check that now covers it.) The three `tweet-claims-*`
# recipes (`-open-milestone`, `-unfixed-issue`, `-unmerged-pr`) say "tweet"
# only as the noun naming where the false claim came from ("Tweet T-1201
# claims milestone #5001 shipped, but it's still open") -- the actual gap
# is the still-open
# milestone/issue/PR the tweet claimed was done, and "close it yourself" is
# the genuinely correct hand-off, same family as their `readme-claims-*`/
# `release-claims-*`/`milestone-claims-*` siblings (none of which mention
# "tweet" and so never tripped this heuristic in the first place). Nothing
# else may join this set silently.
def test_no_recipe_with_a_tweet_or_announce_shaped_headline_falls_through_to_default():
    from seam_engine.recipes import discover_recipes, load_detector

    exceptions = {
        "contributor-thanked-not-credited",
        "own-tweet-dangling-reference",
        "tweet-claims-open-milestone",
        "tweet-claims-unfixed-issue",
        "tweet-claims-unmerged-pr",
    }
    fencepost_root = Path(__file__).resolve().parents[2]
    checked_any = False
    for manifest in discover_recipes(fencepost_root):
        if manifest.slug in exceptions:
            continue
        result = load_detector(manifest)()
        gap = result.get("primary_gap") or (result.get("tail") or [None])[0]
        if gap is None:
            continue
        headline = gap.get("headline", "")
        # Strip mortal-controlled quoted spans first, the same discipline
        # `suggest_move` itself uses (task 537), so a commit message that
        # happens to contain "tweet" can't false-trigger this guard.
        stripped = report._strip_mortal_text(headline).lower()
        if "tweet" not in stripped and "announce" not in stripped:
            continue
        checked_any = True
        move = report.suggest_move(gap)
        assert move != report._DEFAULT_MOVE, (
            f"{manifest.slug}'s real headline ({headline!r}) claims a tweet/"
            "announcement gap but suggest_move fell through to the generic "
            "close-it-yourself line -- add a needle to _MOVE_RULES."
        )
    # If discover_recipes() ever returns nothing that mentions tweet/announce
    # at all, this guard would pass vacuously and silently stop meaning
    # anything -- fail loudly instead so a future refactor can't do that.
    assert checked_any, "expected at least one real recipe headline to mention tweet/announce"


# Task 586 (retrya): the sibling systemic guard for the dangling-reference
# family (`dangling-issue-reference`, `issue-body-dangling-reference`,
# `issue-comment-dangling-reference`, `mention-dangling-reference`,
# `milestone-body-dangling-reference`, `own-tweet-dangling-reference`,
# `release-note-dangling-reference`, `review-comment-dangling-reference`).
# Every one of these eight names a `#N` that does not exist anywhere in the
# repo, and every one of their real headlines shares the same "no issue or
# PR #{n} exists[ here]" phrasing -- confirmed live pre-fix that all eight
# fell through to `_DEFAULT_MOVE` ("Close it yourself"), a wrong hand-off
# since there is no `#N` to close. Same walk-every-real-recipe-fixture
# mechanism as the tweet/announce guard above, so a ninth recipe added to
# this family later either gets a matching headline (caught for free by the
# shared "no issue or pr" needle) or gets a genuinely new phrasing this
# guard will refuse silently passing over.
def test_no_dangling_reference_headline_falls_through_to_default():
    from seam_engine.recipes import discover_recipes, load_detector

    fencepost_root = Path(__file__).resolve().parents[2]
    checked_any = False
    for manifest in discover_recipes(fencepost_root):
        result = load_detector(manifest)()
        gap = result.get("primary_gap") or (result.get("tail") or [None])[0]
        if gap is None:
            continue
        headline = gap.get("headline", "")
        stripped = report._strip_mortal_text(headline).lower()
        if "no issue or pr" not in stripped:
            continue
        checked_any = True
        move = report.suggest_move(gap)
        assert move != report._DEFAULT_MOVE, (
            f"{manifest.slug}'s real headline ({headline!r}) names a dangling "
            "reference to a nonexistent issue/PR but suggest_move fell through "
            "to the generic close-it-yourself line -- add a needle to _MOVE_RULES."
        )
        assert "correct or delete it yourself" in move.lower()
    # Same vacuous-pass guard as the tweet/announce sweep: if discover_recipes()
    # ever stops returning any dangling-reference recipe, fail loudly rather
    # than silently pass with nothing actually checked.
    assert checked_any, "expected at least one real recipe headline to name a dangling reference"


# Task 537 (retrya): every detector embeds mortal-controlled free text (a
# commit message, a title, a tweet's own words) inside single quotes in its
# headline/detail f-strings -- confirmed by grep across the whole tree, zero
# exceptions. Left unstripped, that free text can accidentally contain a
# rule's needle and misfire the wrong move for a gap that has nothing to do
# with it. Each case below reproduces a real detector's own quoting shape
# (`'{commit.message}' ... references #{n}`, the dangling-reference family's
# own template) with free text engineered to collide with a different rule.
def test_suggest_move_ignores_a_rule_needle_hiding_inside_quoted_free_text():
    # Task 586: the headline's own real "no issue or PR #42 exists" phrasing
    # now maps to the dangling-reference move (see _MOVE_RULES) -- the point
    # of this test stays what it always was, that "calendar" hiding inside
    # the quoted commit message never fires the unrelated Calendar rule.
    gap = {
        "headline": "A commit references #42, but no issue or PR #42 exists",
        "detail": "'Add calendar sync helper, references #42' (https://github.com/x/y/commit/abc) "
        "references #42; a real issue or pull request never existed.",
    }
    move = report.suggest_move(gap)
    assert "correct or delete it yourself" in move.lower()
    assert "calendar" not in move.lower()


# Task 586 (retrya): reproduces the real bug `issue-comment-dangling-
# reference`'s own live fixture tripped -- a headline's bare possessive
# apostrophe ("#41's own thread") is not a quoted span at all, but when
# `headline` and `detail` used to be concatenated before stripping, that one
# stray apostrophe paired against `detail`'s own OPENING mortal quote
# instead of its real partner, and `_QUOTED_SPAN_RE` swallowed everything
# between them -- including the headline's own real "no issue or PR #N
# exists" text, the exact needle this gap needed matched. Confirmed live
# pre-fix (concatenate-then-strip): `suggest_move` on this exact shape
# returned `_DEFAULT_MOVE`, silently eating a real needle it should have
# matched. Stripping each field independently (the fix) can't cross that
# boundary, so the real needle survives.
def test_suggest_move_survives_a_bare_apostrophe_in_the_headline_next_to_a_quoted_detail():
    gap = {
        "headline": "Comment #7002 (on #41's own thread) references #9999, but no issue or PR #9999 exists here",
        "detail": "'Blocked on #9999 until that one lands, and I can no longer find it.' "
        "(https://github.com/example/example-repo/issues/41#issuecomment-7002) references #9999; "
        "no issue or pull request with that number exists in this repo.",
    }
    move = report.suggest_move(gap)
    assert "correct or delete it yourself" in move.lower()


def test_suggest_move_ignores_reminder_hiding_inside_a_quoted_headline():
    gap = {
        "headline": "'Ship the reminder email' is open with no 'duplicate of #N' reference",
        "detail": "",
    }
    move = report.suggest_move(gap)
    assert move == report._DEFAULT_MOVE
    assert "reminder" not in move.lower()


# Task 550 (retrya): `readme-credited-not-thanked`'s real headline shape
# copied verbatim from its own detector.py f-string -- a genuine
# "post about it" gap the pre-existing needles never caught (confirmed live
# pre-fix: fell to `_DEFAULT_MOVE`).
def test_suggest_move_matches_readme_credited_not_thanked_headline():
    move = report.suggest_move(
        {"headline": "@thierry is credited in the README, never thanked on X", "detail": ""}
    )
    assert "post about it" in move.lower()


# Task 550 (retrya): the mirror recipe, `contributor-thanked-not-credited`.
# The correct hand-off here is a README edit, not an X post -- a real,
# distinct third rule, not a re-use of the post-about-it line.
def test_suggest_move_matches_contributor_thanked_not_credited_headline():
    move = report.suggest_move(
        {"headline": "@thierry was thanked on X, not yet in the README credits", "detail": ""}
    )
    lowered = move.lower()
    assert "readme" in lowered
    assert "post about it" not in lowered


def test_suggest_move_still_matches_calendar_when_unquoted_in_the_template():
    # Guards the fix's own precision: stripping quoted spans must not eat the
    # rule's own unquoted template word (gmail_calendar.py's real headline
    # shape: "Invite '{event_title}' sits in Gmail, never reached Calendar").
    gap = {
        "headline": "Invite 'Add calendar sync helper' sits in Gmail, never reached Calendar",
        "detail": "",
    }
    move = report.suggest_move(gap)
    assert "add it to your calendar" in move.lower()


# --- task 605 (retrya): an apostrophe is not always a quote ------------------
#
# `_QUOTED_SPAN_RE` used to read `'[^']*'` -- every apostrophe treated as a
# delimiter, paired off left to right. English writes possessives and
# contractions with that same character, and this engine's own recipe-authored
# templates are full of them ("PR #{n}'s branch", "Draft PR #{n}'s own body",
# "but it isn't ready", "while we're in here"). Pairing those off as
# delimiters broke the strip in BOTH directions, live, in the shipped tree:
# 43 of the 72 shipped recipes had at least one field (8 headlines, 41
# details) stripped differently by the old pattern than by the fixed one.
# Each test below reproduces one real, live shape -- copied from the
# detector's own f-string, never invented.


def test_strip_mortal_text_leaves_a_possessive_and_a_contraction_alone():
    # `draft-pr-closes-keyword-issue`'s own real headline template. Two
    # apostrophes, both ordinary English, no mortal free text at all. The old
    # pattern paired them and stripped this whole headline down to
    # "Draft PR #2001 t ready" -- confirmed live pre-fix.
    headline = "Draft PR #2001's own body claims a closing keyword, but it isn't ready"
    assert report._strip_mortal_text(headline) == headline


def test_strip_mortal_text_leaves_a_templates_own_possessive_thread_reference_alone():
    # `issue-comment-claims-open-milestone`'s own real headline template.
    # Old pattern: "Comment #8101 (on #50 s still open" -- the entire claim,
    # including the seam it names, eaten between "#50's" and "it's".
    headline = (
        "Comment #8101 (on #50's own thread) claims milestone #6101 shipped, but it's still open"
    )
    assert report._strip_mortal_text(headline) == headline


def test_strip_mortal_text_still_removes_a_real_mortal_span_beside_a_possessive():
    # `deleted-branch-pr-still-open`'s own real headline template: a template
    # possessive immediately before a genuinely mortal quoted span.
    stripped = report._strip_mortal_text(
        "PR #88's branch 'feature/login-timeout-fix' was deleted, but the PR is still open"
    )
    assert "feature/login-timeout-fix" not in stripped
    assert "PR #88's branch" in stripped
    assert "was deleted, but the PR is still open" in stripped


def test_strip_mortal_text_removes_a_mortal_span_that_itself_carries_a_possessive():
    # `issue-closed-not-tweeted`'s own real detail template, whose mortal
    # free text (a real issue title) contains a possessive of its own. That
    # interior apostrophe is inter-word too, so the span still strips whole
    # rather than closing early on it -- the old pattern closed early and
    # leaked "s whole-line-only matching gap" into the haystack.
    stripped = report._strip_mortal_text(
        "'Fix the vault leak checker's whole-line-only matching gap' (#12) closed 2026-07-25; "
        "no tweet from the connected account names it."
    )
    assert "vault leak" not in stripped
    assert "whole-line-only" not in stripped
    assert "no tweet from the connected account names it." in stripped


def test_suggest_move_does_not_leak_a_mortal_branch_name_into_the_rule_haystack():
    """The live reproduction, and the reason this is a bug and not a tidy-up.

    `deleted-branch-pr-still-open` is a shipped recipe whose real headline
    template embeds the branch name as mortal free text. Under the old
    pattern the preceding possessive in "PR #88's" consumed that span's
    OPENING delimiter, so the branch name survived into the rule haystack --
    and a branch named `feature/calendar-sync`, an entirely ordinary branch
    name, made `suggest_move` hand the reader "Add it to your Calendar
    yourself" for a deleted-branch gap with no calendar anywhere in it.
    Confirmed live pre-fix, against the pre-fix tree as it actually stood
    (naive pattern AND the bare "calendar" needle). Asserted below on the
    haystack itself rather than only on the rendered move, so this stays red
    on the pattern alone -- the guarantee is that mortal free text never
    reaches the rule table, not merely that today's needles happen to miss
    it.
    """
    gap = {
        "headline": "PR #88's branch 'feature/calendar-sync' was deleted, but the PR is still open",
        "detail": (
            "Activity feed shows 'feature/calendar-sync' deleted 2026-07-20T10:00:00+00:00; "
            "PR #88 ('Wire the sync job') still reads open, pointing at a branch that no "
            "longer exists."
        ),
    }
    for field in ("headline", "detail"):
        stripped = report._strip_mortal_text(gap[field]).lower()
        assert "calendar" not in stripped, (
            f"the mortal branch name leaked into the {field} haystack: {stripped!r}"
        )
        assert "wire the sync job" not in stripped
    move = report.suggest_move(gap)
    assert "calendar" not in move.lower()
    assert move == report._DEFAULT_MOVE


# --- task 605 (retrya): a needle names a seam, never a subject ---------------


def test_no_move_rule_needle_is_a_bare_topic_word():
    """Every needle must be a phrase, not a subject.

    "calendar" and "reminder" were the two bare topic words left in the
    table, and a bare topic word matches any prose that merely mentions the
    subject -- including a negation, which is how
    `good-first-issue-never-referenced` ("no reminder, no staleness flag")
    came to be handed "Set the reminder yourself". Every needle now names the
    seam in at least two words, the way every seam-phrase needle in the table
    already did.

    One deliberate, checked exemption: a literal `@handle`. `@oritatown` is
    the town's own X account, not a common noun -- `scan.py` names it in
    three genuinely different headline templates ("predates @oritatown",
    "never reached @oritatown", "stays off @oritatown"), so the handle
    itself is the only phrase all three share, and a word that can only mean
    one account cannot drift onto an unrelated seam the way "calendar" did.
    """
    offenders = [
        needle
        for needle, _ in report._MOVE_RULES
        if len(needle.split()) < 2 and not needle.startswith("@")
    ]
    assert offenders == [], (
        f"bare topic-word needle(s) in _MOVE_RULES: {offenders} -- a needle must name "
        "the seam ('never tweeted', 'no issue or pr'), not the subject it is about."
    )


def test_calendar_needle_is_gmail_calendars_own_headline_phrase():
    """Ties the needle to the only real Calendar gap this engine can build.

    Read out of `gmail_calendar.py`'s own source rather than hand-typed a
    second time, so rewording either side goes red here instead of quietly
    drifting apart -- the same discipline `test_readme_tool_count.py` and
    `test_onboarding_test_count.py` already hold for their own claims.
    """
    from seam_engine import gmail_calendar

    source = inspect.getsource(gmail_calendar)
    needles = [needle for needle, _ in report._MOVE_RULES if "calendar" in needle]
    assert needles == ["never reached calendar"], needles
    assert "never reached Calendar" in source, (
        "gmail_calendar.py no longer carries the headline phrase _MOVE_RULES matches on"
    )


def test_reminder_needle_is_the_phrase_the_readme_names_that_seam_by():
    """The reminder seam has no detector yet, so its needle is anchored to
    the one place in the repo that names it: fencepost/README.md's own
    opening line ("the renewal in your inbox that never became a
    reminder"). A forward-looking rule is fine; a forward-looking rule that
    matches any sentence containing the word is not."""
    readme = Path(__file__).resolve().parents[2] / "README.md"
    needles = [needle for needle, _ in report._MOVE_RULES if "reminder" in needle]
    assert needles == ["never became a reminder"], needles
    assert "never became a reminder" in readme.read_text()


def test_no_recipe_gap_is_handed_a_calendar_or_reminder_move():
    """The systemic guard, in the shape tasks 557/586 already established.

    Not one recipe in `RECIPES/` reads Gmail or Calendar -- the whole
    directory is GitHub/X/Slack/Linear -- so no recipe's real gap may ever
    be handed the Calendar or reminder hand-off. Pre-fix this failed live on
    `good-first-issue-never-referenced`, whose own detail prose says
    "checks nothing else about it -- no reminder, no staleness flag" and was
    handed "Set the reminder yourself" for an unclaimed good-first-issue.
    Walks every recipe's own fixture-generated gap, the same mechanism the
    tweet/announce and dangling-reference sweeps above use.
    """
    from seam_engine.recipes import discover_recipes, load_detector

    fencepost_root = Path(__file__).resolve().parents[2]
    checked_any = False
    for manifest in discover_recipes(fencepost_root):
        result = load_detector(manifest)()
        gap = result.get("primary_gap") or (result.get("tail") or [None])[0]
        if gap is None:
            continue
        checked_any = True
        move = report.suggest_move(gap)
        lowered = move.lower()
        assert "add it to your calendar" not in lowered, (
            f"{manifest.slug}'s real gap was handed the Calendar hand-off; no recipe in "
            "RECIPES/ reads Gmail or Calendar at all."
        )
        assert "set the reminder" not in lowered, (
            f"{manifest.slug}'s real gap was handed the reminder hand-off; no recipe in "
            "RECIPES/ reads a reminder surface at all."
        )
    assert checked_any, "expected at least one real recipe to produce a gap to check"


def test_your_move_line_reads_correctly_from_a_live_ledger(tmp_path: Path):
    ledger.append_scan(
        {
            "generated_at": "2026-07-12T11:38:10+00:00",
            "repo": "x/orita",
            "confidence_bar": 0.7,
            "primary_gap": {
                "slug": "milestone-unannounced",
                "headline": "Milestone-level work shipped but never reached @oritatown",
                "detail": "3 milestone commit(s), none echoed in a post.",
                "confidence": 0.85,
                "evidence": ["https://github.com/x/orita/commit/0000001"],
            },
            "tail": [],
            "excluded": [],
        },
        now=_at(2026, 7, 12),
        base=tmp_path,
    )

    text = report.render_latest(tmp_path)
    assert text.count("**Your move.**") == 1
    assert "post about it" in text.lower()


# --- the docstring's safety claim, checked structurally, not just in prose ----


def test_report_module_imports_nothing_but_stdlib_and_its_own_audited_locals():
    source = inspect.getsource(report)
    imports = _top_level_imports(source)
    assert imports, "report.py must import something for this test to mean anything"
    violations = {name for name in imports if not _stdlib_or_allowed(name)}
    assert not violations, f"report.py imports beyond stdlib/its own audited locals: {violations}"


def test_report_module_source_names_no_network_or_credential_capable_symbol():
    source = inspect.getsource(report)
    assert _forbidden_names_in(source) == []


def test_the_same_import_checker_flags_a_synthetic_credential_import():
    # Mutation-based hand-verification (task 135/136/137/138's own discipline):
    # the SAME extracted checker, run against a deliberately mutated copy of
    # the real source, must disagree -- proving it actually bites rather than
    # merely existing. The real, unmutated file is proven clean above.
    real_source = inspect.getsource(report)
    mutated = "import requests\n" + real_source
    imports = _top_level_imports(mutated)
    violations = {name for name in imports if not _stdlib_or_allowed(name)}
    assert violations == {"requests"}


def test_the_same_forbidden_name_checker_flags_a_synthetic_socket_reference():
    real_source = inspect.getsource(report)
    mutated = real_source + "\n# socket.socket() would be the violation here\n"
    assert "socket" in _forbidden_names_in(mutated)
    # And the real, unmutated file still reads clean against the same function.
    assert "socket" not in _forbidden_names_in(real_source)
