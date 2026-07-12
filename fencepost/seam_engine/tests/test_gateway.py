"""Tests for gateway.py — the capabilities string is a request, and a

request that asks Arcade's tool matcher for a write is a broken oath even
if no write tool is ever named directly. These tests exercise the pure
`is_read_only_capabilities` law, then hold the town's own constant to it.
"""
from __future__ import annotations

import pytest

from seam_engine.gateway import (
    READ_ONLY_CAPABILITIES,
    gateway_url,
    is_read_only_capabilities,
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
    ],
)
def test_an_unnegated_write_ask_fails_the_law(text: str):
    assert not is_read_only_capabilities(text)


def test_a_negated_write_verb_does_not_fail_the_law():
    text = "Read commits and releases. Never create, post, or send anything."
    assert is_read_only_capabilities(text)


def test_negation_does_not_launder_an_unrelated_later_sentence():
    # The "never" in the first sentence must not cover a genuine ask that
    # follows in an unrelated sentence — negation scope stays per-clause.
    text = "Never touch the calendar. Post the daily report to X."
    assert not is_read_only_capabilities(text)


def test_gateway_url_builds_the_real_arcade_mcp_url():
    assert gateway_url("my-fencepost") == "https://api.arcade.dev/mcp/my-fencepost"


@pytest.mark.parametrize("bad_slug", ["", "has space", "has/slash"])
def test_gateway_url_rejects_malformed_slugs(bad_slug: str):
    with pytest.raises(ValueError):
        gateway_url(bad_slug)
