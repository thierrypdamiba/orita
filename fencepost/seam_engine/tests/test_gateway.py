"""Tests for gateway.py — the capabilities string is a request, and a

request that asks Arcade's tool matcher for a write is a broken oath even
if no write tool is ever named directly. These tests exercise the pure
`is_read_only_capabilities` law, then hold the town's own constant to it.

Task 152 adds a second, previously-untested relationship: the capabilities
string is also a *floor*. It must name a covering keyword for every tool
`consent.REQUIRED_SCOPES` will later demand a scope-confirm name verbatim,
or a real forker who pastes it exactly into Arcade's Gateway Assistant
could provision a gateway that can never pass its own onboarding consent
gate. `test_connect_doctrine.py` only ever proved the string is quoted
verbatim in CONNECT.md/connect.html — never that its own content is
complete against the scopes it will be judged by.
"""
from __future__ import annotations

import pytest

from seam_engine.consent import REQUIRED_SCOPES
from seam_engine.gateway import (
    READ_ONLY_CAPABILITIES,
    gateway_url,
    is_read_only_capabilities,
    required_scopes_covered_by_capabilities,
)

# The real, live pre-task-152 string — reconstructed from the actual git
# history, not invented — used only by the mutation test below to prove the
# new coverage check would have caught the real historical gap.
_PRE_TASK_152_CAPABILITIES = (
    "Read-only seam reconciliation: list and read GitHub commit history, "
    "releases, issues, and pull requests, and read a connected user's own "
    "X (Twitter) tweet history and mentions — solely to compare the two "
    "timelines and surface gaps between what shipped and what was "
    "announced. Never create, update, merge, label, delete, post, reply, "
    "send, or modify anything on any connected account."
)


def test_the_towns_own_capabilities_string_is_read_only():
    assert is_read_only_capabilities(READ_ONLY_CAPABILITIES)


def test_read_only_string_of_gets_and_lists_passes():
    text = "List and read GitHub commits and releases to compare timelines."
    assert is_read_only_capabilities(text)


@pytest.mark.parametrize(
    "text",
    [
        "Post updates to X and create GitHub issues when a gap is found.",
        "Send an email summarizing the report.",
        "Merge the pull request once the gap is confirmed.",
        "Delete stale draft events on the calendar.",
        "Reply to mentions with the daily report.",
        "Publish the daily summary to a public Notion page automatically.",
        "Share the dashboard with everyone on the team.",
    ],
)
def test_an_unnegated_write_ask_fails_the_law(text: str):
    assert not is_read_only_capabilities(text)


def test_write_verbs_cover_the_sibling_forbidden_verb_vocabularies():
    """gateway._WRITE_VERBS claims to mirror draftback.FORBIDDEN_DELIVERY_ACTIONS
    and recipes._FORBIDDEN_VERBS (recipes.py's own comment says so). Both
    siblings forbid Publish/Share; this pins that gateway.py can't silently
    drift back out of step with them.
    """
    from seam_engine import gateway

    assert "publish" in gateway._WRITE_VERBS
    assert "share" in gateway._WRITE_VERBS


def test_a_negated_write_verb_does_not_fail_the_law():
    text = "Read commits and releases. Never create, post, or send anything."
    assert is_read_only_capabilities(text)


def test_negation_does_not_launder_an_unrelated_later_sentence():
    # The "never" in the first sentence must not cover a genuine ask that
    # follows in an unrelated sentence — negation scope stays per-clause.
    text = "Never touch the calendar. Post the daily report to X."
    assert not is_read_only_capabilities(text)


@pytest.mark.parametrize(
    "text",
    [
        # A negation cue that trails the verb in the SAME clause must not
        # launder it — the cue negates something else entirely ("trust
        # automation blindly"), not the "Post" ask that precedes it.
        "Post the daily report to X, but never trust automation blindly.",
        "Share the private dashboard with everyone, though we never "
        "publicized it before.",
        "Create an issue automatically, not that anyone asked for caution.",
    ],
)
def test_negation_does_not_launder_a_verb_earlier_in_the_same_clause(text: str):
    assert not is_read_only_capabilities(text)


@pytest.mark.parametrize(
    "text",
    [
        # A comma splicing two independent asks together must not let the
        # first ask's negation launder the second, unrelated one — the
        # comma-joined sibling of the semicolon/period cases above.
        "Never trash old drafts, delete the connected account entirely.",
        "Never trash a, delete b, remove c.",
        "Never touch the calendar, post the daily report to X.",
    ],
)
def test_negation_does_not_launder_an_unrelated_clause_across_a_comma(text: str):
    assert not is_read_only_capabilities(text)


@pytest.mark.parametrize(
    "text",
    [
        # A contrastive/causal conjunction ("since", "though", "because", ...)
        # reverses or breaks negation scope exactly the way a comma splice
        # already does above -- but with no comma present, `_split_clauses`
        # used to leave the whole sentence as one clause, and the earlier
        # "never" (which negates something else entirely) was read as
        # covering the later, unrelated, genuinely unnegated write ask.
        # Reproduced live pre-fix: `is_read_only_capabilities` on each of
        # these returned True.
        "It will never merely watch idly since it will actually create new issues automatically.",
        "The tool will never sit idle though it will happily publish updates to the public feed.",
        "We will never act carelessly because we will actually delete stale branches automatically.",
    ],
)
def test_negation_does_not_launder_a_verb_across_a_contrastive_conjunction_with_no_comma(text: str):
    assert not is_read_only_capabilities(text)


@pytest.mark.parametrize(
    "text",
    [
        # A genuine bare, comma-separated enumeration of write verbs
        # sharing one trailing object must stay covered by a single
        # leading negation — this must not regress into false positives.
        "Read commits and releases. Never create, post, or send anything.",
        "Never create, update, merge, label, delete, post, reply, send, "
        "or modify anything on any connected account.",
    ],
)
def test_a_bare_verb_enumeration_stays_covered_by_one_leading_negation(text: str):
    assert is_read_only_capabilities(text)


@pytest.mark.parametrize(
    "text",
    [
        # Task 694: an unrelated word that merely CONTAINS a negation cue
        # as a substring ("casino " contains "no ", "piano " contains
        # "no ") used to launder a real, unnegated write ask sitting right
        # after it in the same clause — the old check was `cue in before`
        # plain containment, not a word-boundary match. Reproduced live
        # pre-fix: both of these returned True.
        "Reads data from a casino ledger and create new records on the account.",
        "Reads sheet piano archives and delete old drafts on the account.",
        "Checks the volcano monitoring feed and post updates automatically.",
    ],
)
def test_negation_cue_does_not_match_inside_an_unrelated_word(text: str):
    assert not is_read_only_capabilities(text)


@pytest.mark.parametrize(
    "text",
    [
        # Task 694: the only negative contraction the old cue tuple
        # recognized was the one hardcoded "won't" — every other `n't`
        # contraction failed to register as negation at all. Reproduced
        # live pre-fix: all three of these returned False (judged as
        # asking for a write) despite being genuinely negated.
        "This doesn't create anything on any connected account.",
        "It isn't going to delete anything on the account.",
        "It can't modify anything on any connected account.",
    ],
)
def test_any_nt_contraction_counts_as_negation_not_only_wont(text: str):
    assert is_read_only_capabilities(text)


def test_a_leading_bare_verb_enumeration_with_a_contraction_still_covers_the_list():
    # The `_LEADING_CUE_RE` sibling of the fix above: a bare enumerated
    # verb list introduced by a contraction with no leading subject, the
    # same shape the existing "Never create, update, ..." test already
    # covers for "never".
    text = "Doesn't create, update, merge, or delete anything on any connected account."
    assert is_read_only_capabilities(text)


def test_gateway_url_builds_the_real_arcade_mcp_url():
    assert gateway_url("my-fencepost") == "https://api.arcade.dev/mcp/my-fencepost"


@pytest.mark.parametrize("bad_slug", ["", "has space", "has/slash"])
def test_gateway_url_rejects_malformed_slugs(bad_slug: str):
    with pytest.raises(ValueError):
        gateway_url(bad_slug)


# --- Task 152: the capabilities string is a floor, not just a ceiling ------


def test_required_scopes_is_a_real_nontrivial_family():
    # Same non-vacuous-family guard task 147/148's doctrine tests hold —
    # a broken import or an emptied REQUIRED_SCOPES would make every
    # coverage assertion below vacuously true.
    assert len(REQUIRED_SCOPES.get("github", ())) >= 5
    assert len(REQUIRED_SCOPES.get("x", ())) >= 2


def test_the_towns_own_capabilities_string_covers_every_required_scope():
    missing = required_scopes_covered_by_capabilities(READ_ONLY_CAPABILITIES)
    assert missing == {}, (
        f"READ_ONLY_CAPABILITIES is missing a covering keyword for: {missing} "
        "— a forker who pastes this string could provision a gateway unable "
        "to satisfy consent.REQUIRED_SCOPES"
    )


def test_coverage_check_defaults_to_the_real_live_constants():
    # No args at all — proves the function checks the real module-level
    # READ_ONLY_CAPABILITIES against the real live consent.REQUIRED_SCOPES,
    # not just whatever the caller happens to hand it.
    assert required_scopes_covered_by_capabilities() == {}


def test_real_pre_task_152_string_would_have_failed_the_coverage_check():
    # Mutation-based hand-verification: reconstruct the actual pre-fix
    # string from git history and prove today's checker would have flagged
    # the real historical gap, not a synthetic one. Checked against the
    # live REQUIRED_SCOPES (default), so GetFileContents -- added by task
    # 371, after this pre-152 string was written -- correctly shows up
    # missing too: this string never named it either. ListTags -- added by
    # task 653, for tag-never-released -- shows up missing the same way:
    # this pre-152 string predates it by months and never says "tag"
    # anywhere. ListReleases (added the same task) does NOT show up missing
    # here -- this string already says "releases" for GetLatestRelease's
    # own sake, and "release" is ListReleases's keyword too; one shared
    # word genuinely covers both tools, correctly, not a checker gap.
    missing = required_scopes_covered_by_capabilities(_PRE_TASK_152_CAPABILITIES)
    assert missing == {
        "github": [
            "CountStargazers", "GetFileContents", "GetRepository", "ListMilestones",
            "ListRepositoryActivities", "ListReviewCommentsInARepository", "ListTags",
        ],
        "x": ["WhoAmI"],
    }


def test_missing_a_keyword_for_one_tool_is_reported_precisely():
    text = "Read GitHub issues and pull requests. Never write anything."
    missing = required_scopes_covered_by_capabilities(
        text, required_scopes={"github": frozenset({"ListIssues", "GetRepository"})}
    )
    assert missing == {"github": ["GetRepository"]}


def test_full_coverage_for_a_synthetic_toolkit_reports_no_gap():
    text = "Read repository metadata and issues, never anything else."
    missing = required_scopes_covered_by_capabilities(
        text, required_scopes={"github": frozenset({"GetRepository", "ListIssues"})}
    )
    assert missing == {}


# --- Task 372: a tool with NO keyword entry must never silently "pass" ----


def test_a_required_scope_with_no_keyword_entry_at_all_is_reported_missing():
    # The real historical bug: keywords.get(tool, "") defaulted an unmapped
    # tool to "", and "" is a substring of every string, so the coverage
    # check silently treated "we never even tried to check this" the same
    # as "checked and covered". A tool this synthetic toolkit has never
    # heard of must be reported as a gap, not pass by accident.
    text = "Read repository metadata and issues, never anything else."
    missing = required_scopes_covered_by_capabilities(
        text,
        required_scopes={
            "github": frozenset({"GetRepository", "ListIssues", "SomeBrandNewTool"})
        },
    )
    assert missing == {"github": ["SomeBrandNewTool"]}


def test_getfilecontents_was_the_real_live_instance_of_the_bug():
    # Task 371 added GetFileContents to consent.REQUIRED_SCOPES["github"]
    # for the fifth recipe and never touched gateway.py. Reconstruct the
    # real pre-372 shape (the keyword entry absent, the capabilities string
    # not naming file access) and prove today's function reports it missing
    # -- the pre-fix function, run against this same input, returned {}.
    pre_372_capabilities = (
        "Read-only seam reconciliation: list and read GitHub repository "
        "metadata, commit history, releases, issues, pull requests, "
        "repository activity, and stargazer counts, and read a connected "
        "user's own X (Twitter) tweet history, mentions, and account "
        "identity — solely to compare the two timelines and surface gaps "
        "between what shipped and what was announced. Never create, update, "
        "merge, label, delete, post, reply, send, or modify anything on any "
        "connected account."
    )
    missing = required_scopes_covered_by_capabilities(pre_372_capabilities)
    assert "github" in missing
    assert "GetFileContents" in missing["github"]


def test_the_live_capabilities_string_now_names_file_contents():
    assert "file contents" in READ_ONLY_CAPABILITIES.lower()


def test_getfilecontents_now_has_a_real_keyword_entry():
    from seam_engine.gateway import _SCOPE_KEYWORDS

    assert "GetFileContents" in _SCOPE_KEYWORDS["github"]
    assert _SCOPE_KEYWORDS["github"]["GetFileContents"]  # non-empty, real phrase


def test_the_extended_capabilities_string_still_holds_the_read_only_law():
    # The fix that closed the coverage gap must not have reopened the
    # write-verb gap is_read_only_capabilities already guards.
    assert is_read_only_capabilities(READ_ONLY_CAPABILITIES)
