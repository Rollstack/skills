"""Checks against Rollstack's real server. Off by default: ROLLSTACK_LIVE=1 turns them on.

They cover what a mocked answer can't: that the reference the plugin was written from is still what the server
lists, and that the client's requests are ones the server accepts.

The server answers a request only when it carries a key: without one it neither lists its tools nor opens a session.
So the two checks that read an answer need ROLLSTACK_API_KEY, a Rollstack API key with every scope, made by an owner
or admin so that it is shown listMembers, and are skipped without it. The two that send a wrong key need no account.
"""

from __future__ import annotations

import json
import os

import pytest

from rollstack_client.mcp import RollstackClient, RollstackError
from update_fixture import FIXTURE, KEY_VARIABLE, ReferenceUnavailable, current, key_to_set

LIVE = os.environ.get("ROLLSTACK_LIVE") == "1"
pytestmark = pytest.mark.skipif(not LIVE, reason="set ROLLSTACK_LIVE=1 to call Rollstack")

SAVED = json.loads(FIXTURE.read_text())["tools"]
NOT_A_KEY = "rsk_not_a_real_key"

# The key is read where it is sent and never bound to a name here, so no report of a failure can show it
needs_a_key = pytest.mark.skipif(
    LIVE and not os.environ.get(KEY_VARIABLE, "").strip(), reason=f"set {KEY_VARIABLE} to {key_to_set(SAVED)}"
)


@needs_a_key
def test_the_reference_has_not_changed():
    try:
        listed = current(SAVED)
    except ReferenceUnavailable as error:
        # The server lists for a key only the tools it may call. A list that leaves out one of the plugin's tools
        # can't say that nothing changed, so it fails here with the scope the key lacks rather than pass in part
        pytest.fail(str(error), pytrace=False)

    now = {tool["name"]: tool for tool in listed}
    added = [name for name in now if name not in {tool["name"] for tool in SAVED}]
    assert not added, f"Rollstack's server has new tools, {', '.join(added)}: run tests/update_fixture.py and review"
    for tool in SAVED:
        assert now[tool["name"]] == tool, f"{tool['name']} changed on Rollstack's server: run tests/update_fixture.py and review"


def test_a_tool_call_reaches_rollstack_and_a_wrong_key_is_refused():
    with pytest.raises(RollstackError) as raised:
        RollstackClient(NOT_A_KEY).call_tool("listReports", {"query": {"limit": 1}})

    assert (raised.value.status, raised.value.code) == (401, "api-key-invalid")


def test_the_key_check_refuses_a_wrong_key():
    with pytest.raises(RollstackError) as raised:
        RollstackClient(NOT_A_KEY).get_me()

    assert (raised.value.status, raised.value.code) == (401, "api-key-invalid")


@needs_a_key
def test_a_session_can_be_opened_if_the_server_ever_asks_for_one():
    # The server opens a session only for a key it accepts, so this is the client as it runs: with a real key
    headers = RollstackClient(os.environ[KEY_VARIABLE])._open_session()

    assert headers["MCP-Protocol-Version"] == "2025-06-18"
